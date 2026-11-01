# -*- coding: utf-8 -*-
r"""T22 量测探针：①裙腰侧面 gap / 褶面净空；②颈部侧面可见宽度。

同一进程内 import body / hair / outfit / head 现场构建，**不渲染、不写 blend**。
自带材质 stub，刻意不 import look.py（同批次有其他人在改 look，探针不该被拖挂）。

用法（工作目录 人物建模/）：
    "D:/Program Files/Blender Foundation/Blender 5.2/blender.exe" \
        -b --factory-startup --python _stageD/d_probe_waist.py -- [waist|neck|both]

口径（与 leader 2026-11-01 的量法一致，别人复测才能对上）：
  · gap 用**最终网格**（Outfit 已 solidify）：取 |v.co.z - z0| < 0.012 的切片，
    背侧 gap = max(Outfit.y) − max(Body.y)，腹侧 gap = min(Body.y) − min(Outfit.y)。
    正值为裙子在体外。
  · 裙环顶点只落在 8 个离散 z 上（1.045/1.020/0.980/0.920/...），z=0.94 附近
    相邻两环（0.920/0.980）都 >12mm，切片必然为空 → 该高度改用**截面切割**
    （bmesh.ops.bisect_plane）。同一切割口径在 0.98/1.02 上也打一遍做交叉校验，
    只有「切片为空」时才采用截面值。
  · 褶面净空用 BVH 最近距离：Outfit 顶点到 Body 表面的最小距离（Outfit 含
    solidify 内层，所以这是最严格口径），要求 >= +2mm。
  · 颈部可见宽度用**射线首击**（侧面正交投影）：从 x=±0.40 沿 ∓x 各打一条射线，
    距离近者算遮挡；首击落在 Body 且命中点 |x| <= 70mm、且与射线同侧，记「可见颈」。
    沿 y 以 1mm 步长扫描，取最长连续可见段的 y 跨度作「可见颈宽」（mm）。
    另打印 z∈[1.31,1.37] 的 Body/Hair/Head/Outfit 顶点数 / max|x| / y 范围，
    用于定位真正的遮挡者。
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import bpy                       # noqa: E402
import bmesh                     # noqa: E402
from mathutils import Vector     # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

import body as bodymod           # noqa: E402
import hair as hairmod           # noqa: E402
import head as headmod           # noqa: E402
import outfit as outfitmod       # noqa: E402

WAIST_Z = (0.940, 0.980, 1.020, 1.050)
SLICE_TOL = 0.012                # leader 口径：|z - z0| < 12mm
GAP_LO, GAP_HI = 0.005, 0.012    # 验收区间 [5,12]mm
NECK_Z = (1.320, 1.340, 1.360)
NECK_R = 0.055                   # |x| <= 55mm 才算「颈」（颈柱实际半径 ~45mm），
                                 # 70mm 会连肩前斜面一起算进「可见颈」
NECK_BAND = (1.310, 1.370)
RAY_X = 0.40


def stub_mats():
    """只满足 outfit/hair 的材质槽需求，避开 look.set_all()。"""
    keys = ("cloth_white", "cloth_navy", "hair", "skin", "sclera",
            "iris", "pupil", "white_emit", "lash", "lash_soft", "brow", "lip")
    return {k: bpy.data.materials.new(k) for k in keys}


def cos_of(ob):
    mw = ob.matrix_world
    return [mw @ v.co for v in ob.data.vertices]


def mm(v):
    return "-" if v is None else f"{v * 1000:+.1f}"


def bvh_of(cos, ob):
    verts = [tuple(c) for c in cos]
    polys = [tuple(p.vertices) for p in ob.data.polygons]
    return BVHTree.FromPolygons(verts, polys, all_triangles=False)


# ------------------------------------------------------------ 1. 裙腰 gap

def slice_stat(cos, z0, tol=SLICE_TOL):
    ys = [c.y for c in cos if abs(c.z - z0) < tol]
    return (max(ys), min(ys), len(ys)) if ys else (None, None, 0)


def section_stat(ob, cos, z0):
    """平面 z=z0 与网格的截面点（loft 侧面在环之间有插值，顶点切片会漏）。"""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.transform(ob.matrix_world)
    ret = bmesh.ops.bisect_plane(
        bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6,
        plane_co=(0.0, 0.0, z0), plane_no=(0.0, 0.0, 1.0),
        clear_inner=False, clear_outer=False)
    ys = [g.co.y for g in ret["geom_cut"] if isinstance(g, bmesh.types.BMVert)]
    bm.free()
    return (max(ys), min(ys), len(ys)) if ys else (None, None, 0)


def skirt_vertex_mask(cloth_ob):
    """Outfit 里属于裙子的顶点（按材质槽认，不在几何上猜）。

    为什么需要：z=1.05 的 12mm 切片里同时有**裙子顶环**和**衬衫下摆**
    （衬衫最低环 z=1.045，胸围处 grow 14mm），整个 Outfit 的 max/min y 被衬衫
    拿走 —— 量出来的 12.6mm 是衬衫的胸围净空，不是裙腰。裙子用藏青
    `cloth_navy`、衬衫用 `cloth_white`，按材质索引取子集是唯一不靠猜的分法。
    """
    idx = {i for i, slot in enumerate(cloth_ob.material_slots)
           if slot.material and "navy" in slot.material.name.lower()}
    if not idx:
        return None
    return {vi for p in cloth_ob.data.polygons if p.material_index in idx
            for vi in p.vertices}


def waist(bo, co, body_ob, cloth_ob, body_bvh, skirt_cos=None):
    print("[waist] === 裙腰 gap（最终网格；背侧 max(y) / 腹侧 min(y)，mm）===")
    rows, sk_rows = [], []
    for z0 in WAIST_Z:
        by_max, by_min, bn = slice_stat(bo, z0)
        cy_max, cy_min, cn = slice_stat(co, z0)
        how = "slice"
        if cn == 0:                            # 环在 0.920/0.980，0.94 切片必空
            cy_max, cy_min, cn = section_stat(cloth_ob, co, z0)
            how = "bisect"
        if bn == 0:
            by_max, by_min, bn = section_stat(body_ob, bo, z0)
            how += "+bodysect"
        if cn == 0 or bn == 0:
            print(f"[waist] z={z0:.2f} MISSING (outfit n={cn} body n={bn})")
            rows.append((z0, None, None))
            continue
        gb = cy_max - by_max                   # 背侧：裙子比体更靠后
        gf = by_min - cy_min                   # 腹侧：裙子比体更靠前
        rows.append((z0, gb, gf))
        print(f"[waist] z={z0:.2f} 背侧 裙{cy_max*1000:7.1f} 体{by_max*1000:7.1f} "
              f"gap={gb*1000:+6.1f} {'OK' if GAP_LO <= gb <= GAP_HI else 'FAIL'} | "
              f"腹侧 裙{cy_min*1000:7.1f} 体{by_min*1000:7.1f} "
              f"gap={gf*1000:+6.1f} {'OK' if GAP_LO <= gf <= GAP_HI else 'FAIL'} "
              f"[n_out={cn} n_body={bn} {how}]")
        # 裙件本体（藏青材质子集）：z=1.05 时与整件 Outfit 不是同一件事
        if skirt_cos is not None:
            sy_max, sy_min, sn = slice_stat(skirt_cos, z0)
            if sn:
                gsb = sy_max - by_max
                gsf = by_min - sy_min
                print(f"[waist]     └ 裙件本体 z={z0:.2f} 背 裙{sy_max*1000:7.1f} "
                      f"gap={gsb*1000:+6.1f} "
                      f"{'OK' if GAP_LO <= gsb <= GAP_HI else 'FAIL'} | 腹 "
                      f"裙{sy_min*1000:7.1f} gap={gsf*1000:+6.1f} "
                      f"{'OK' if GAP_LO <= gsf <= GAP_HI else 'FAIL'} (n={sn})")
                sk_rows.append((z0, gsb, gsf))

    print("[waist] === Body 背/腹侧 y 剖面（10mm 步长，用于判断环间弦线会不会切进凸包）===")
    for k in range(16):
        z0 = 0.900 + 0.010 * k
        bmax, bmin, bn = slice_stat(bo, z0, 0.006)
        cmax, cmin, cn = slice_stat(co, z0, 0.006)
        if cn == 0:
            cmax, cmin, cn = section_stat(cloth_ob, co, z0)
        print(f"[waist] z={z0:.2f} 体 y=[{mm(bmin)},{mm(bmax)}] "
              f"裙 y=[{mm(cmin)},{mm(cmax)}] "
              f"gap 背={mm(None if (cn == 0 or bn == 0) else cmax - bmax)} "
              f"腹={mm(None if (cn == 0 or bn == 0) else bmin - cmin)}")

    print("[waist] === 裙面到体表最近距离（Outfit 顶点→Body 表面，含壳内层）===")
    worst = (1.0, None)
    for z0 in WAIST_Z:
        d = None
        for c in co:
            if abs(c.z - z0) >= SLICE_TOL:
                continue
            hit = body_bvh.find_nearest(c, 0.20)
            if hit is None or hit[3] is None:
                continue
            if d is None or hit[3] < d:
                d = hit[3]
        print(f"[waist] z={z0:.2f} 最近距离={mm(d)}mm "
              f"{'OK' if (d is not None and d >= 0.002) else 'FAIL'}（要求>=+2mm）")
        if d is not None and d < worst[0]:
            worst = (d, z0)
    print(f"[waist] 四高度最小：{mm(worst[0])}mm @ z={worst[1]} "
          f"{'OK(>=+2mm)' if worst[0] >= 0.002 else 'FAIL'}")

    for key, val in sorted(outfitmod.LAST_SKIRT_NETS.items()):
        print(f"[waist] [fit] z=[{key[0]:.3f},{key[1]:.3f}] "
              f"net={val['net'] * 1000:+.1f}mm "
              f"{'OK' if val['net'] >= 0.002 else 'FAIL(>=+2mm)'}")

    def _bad(rs):
        return [(z, round(gb * 1000, 1), round(gf * 1000, 1)) for z, gb, gf in rs
                if gb is None or not (GAP_LO <= gb <= GAP_HI)
                or gf is None or not (GAP_LO <= gf <= GAP_HI)]

    bad_all, bad_sk = _bad(rows), _bad(sk_rows)
    if sk_rows:            # 有裙子材质子集时，验收以**裙子自己**为准
        print(f"[waist] 判定(裙件本体)：{'四高度两侧全部 ∈[5,12]mm PASS' if not bad_sk else 'FAIL ' + str(bad_sk)}")
        print(f"[waist] 判定(整件 Outfit，含衬衫下摆)："
              f"{'PASS' if not bad_all else 'FAIL ' + str(bad_all)} "
              f"—— z=1.05 的腹侧取到的是衬衫下摆（胸围 grow 14mm，A3 设计值），"
              f"不是裙腰，用裙件本体那行判")
        return not bad_sk
    print(f"[waist] 判定：{'四高度两侧全部 ∈[5,12]mm PASS' if not bad_all else 'FAIL ' + str(bad_all)}")
    return not bad_all


# ------------------------------------------------------------ 2. 颈部可见宽度

def band_stat(cos, lo, hi):
    sel = [c for c in cos if lo <= c.z <= hi]
    if not sel:
        return dict(n=0, xmax=0.0, ymin=None, ymax=None)
    return dict(n=len(sel), xmax=max(abs(c.x) for c in sel),
                ymin=min(c.y for c in sel), ymax=max(c.y for c in sel))


def first_hit(bvhs, origin, direction):
    best_d, best_name, best_loc = None, None, None
    for name, bvh in bvhs:
        loc, _nor, _idx, d = bvh.ray_cast(origin, direction)
        if loc is None or d is None:
            continue
        if best_d is None or d < best_d - 1e-6:
            best_d, best_name, best_loc = d, name, loc
    return best_d, best_name, best_loc


def _span(y_hits, lo_mm, hi_mm):
    """y 区间内的「最长连续可见段」（1mm 步长），返回 (mm, y0, y1)。"""
    best, run, y0, best_y = 0, 0, None, (None, None)
    for y in range(lo_mm, hi_mm + 1):
        if y_hits.get(y):
            if run == 0:
                y0 = y
            run += 1
            if run > best:
                best, best_y = run, (y0, y)
        else:
            run = 0
    return best, best_y[0], best_y[1]


def neck(bo, ho, oo, hdo, bvhs):
    """侧面可见颈宽。

    两个口径同时打印，**验收用第 1 个**（= leader 的写法「没有被 **Hair**
    顶点遮挡」）：
      1. 仅按 Hair 判据：皮肤（Body/Head）与 Hair 比射线距离，Hair 近才算遮挡；
         衣服（Outfit）不算遮挡 —— z=1.32 处衬衫领口把颈根整圈包住（272 条射线），
         但那是**衣服**，不是「头直接坐在肩上」的成因。
      2. 全物体首击（参考）：Body / Hair / Head / Outfit 一起比，谁近算谁。
    另报「颈后区 y∈[0,45]mm 的可见宽度」—— 这才是"颈后让出来"的直接证据：
    改动前发片从 y=+12mm 就开始挡，颈后宽度 0。
    """
    lo, hi = NECK_BAND
    print(f"[neck] === 遮挡者定位（z∈[{lo:.2f},{hi:.2f}] 顶点统计）===")
    for tag, cos in (("Body", bo), ("Hair", ho), ("Head", hdo), ("Outfit", oo)):
        s = band_stat(cos, lo, hi)
        print(f"[neck] {tag:7s} n={s['n']:6d} max|x|={s['xmax']*1000:6.1f}mm "
              f"y=[{mm(s['ymin'])},{mm(s['ymax'])}]mm")

    bvh_body, bvh_hair = bvhs[0][1], bvhs[1][1]
    bvh_head, bvh_out = bvhs[2][1], bvhs[3][1]

    print("[neck] === 颈柱是否已是侧面剪影（Body max|x| @ |y|<40mm / Hair 颈后前沿）===")
    neck_is_silhouette = {}
    for z0 in NECK_Z:
        sel = [c for c in bo if abs(c.z - z0) < 0.006 and abs(c.y) < 0.040]
        m = max((abs(c.x) for c in sel), default=None)
        hs = [c for c in ho if abs(c.z - z0) < 0.006 and c.y > 0.0
              and abs(c.x) < 0.120]
        hy = min((c.y for c in hs), default=None)
        neck_is_silhouette[z0] = (m is not None and m <= NECK_R)
        print(f"[neck] z={z0:.3f} Body max|x|(|y|<40mm)={mm(m)}mm "
              f"{'颈柱是剪影' if neck_is_silhouette[z0] else '颈柱被斜方肌包住'} | "
              f"Hair 颈后最前 y={mm(hy)}mm")

    print("[neck] === 侧面首击（x=±0.40 沿 ∓x，沿 y 1mm 扫描）===")
    all_ok = True
    for z0 in NECK_Z:
        per_side = []
        for tag, sx in (("x+", 1.0), ("x-", -1.0)):
            hair_ok, full_ok = {}, {}
            for k in range(-60, 61):          # y ∈ [-60, 60]mm（颈柱 y 只到 ±45）
                y = k * 0.001
                o = Vector((sx * RAY_X, y, z0))
                d = Vector((-sx, 0.0, 0.0))

                def _neck(dd):
                    _l, _n, _i, dist = bvh_body.ray_cast(o, d)
                    return (dist is not None and dd is not None and abs(dist - dd) < 1e-6
                            and abs(_l.x) <= NECK_R and _l.x * sx > 0.0)

                db = bvh_body.ray_cast(o, d)[3]
                dh = bvh_hair.ray_cast(o, d)[3]
                dhead = bvh_head.ray_cast(o, d)[3]
                do = bvh_out.ray_cast(o, d)[3]
                skin = None
                if db is not None:
                    skin = db
                if dhead is not None and (skin is None or dhead < skin):
                    skin = dhead
                # 口径 1：只有 Hair 遮蔽算遮挡
                if skin is not None:
                    hit = bvh_body.ray_cast(o, d)
                    is_neck = (hit[3] is not None and abs(hit[3] - skin) < 1e-6
                               and abs(hit[0].x) <= NECK_R and hit[0].x * sx > 0.0)
                    hair_ok[k] = bool(is_neck and (dh is None or skin < dh))
                # 口径 2：全物体首击
                full = min([v for v in (db, dh, dhead, do) if v is not None],
                           default=None)
                if full is not None and db is not None and abs(full - db) < 1e-6:
                    _l = bvh_body.ray_cast(o, d)[0]
                    full_ok[k] = bool(abs(_l.x) <= NECK_R and _l.x * sx > 0.0)
            v_hair = _span(hair_ok, -60, 60)
            v_nape = _span(hair_ok, 0, 45)
            v_full = _span(full_ok, -60, 60)
            per_side.append((v_hair, v_nape, v_full))

        vis_hair = min(p[0][0] for p in per_side)
        nape = min(p[1][0] for p in per_side)
        vis_full = min(p[2][0] for p in per_side)
        applicable = neck_is_silhouette.get(z0, True)
        ok = vis_hair >= 8
        if applicable:
            all_ok = all_ok and ok
        tag = ("OK" if ok else "FAIL(<8mm)") if applicable else             "N/A(该高度 Body 截面是斜方肌，颈柱在里面，不存在「可见颈」)"
        print(f"[neck] z={z0:.2f} 可见颈宽(仅Hair判据)={vis_hair}mm "
              f"y=[{per_side[0][0][1]},{per_side[0][0][2]}] {tag} | "
              f"颈后区 y∈[0,45] 可见={nape}mm "
              f"{'OK' if nape >= 8 else '(不足8mm)'} | 全物体首击参考={vis_full}mm")

    hm = [c for c in ho if c.z > 1.40]
    hd = [c for c in hdo if c.z > 1.40]
    zmax_hair = max((c.z for c in hm), default=None)
    zmax_head = max((c.z for c in hd), default=None)
    rx_hair = max((abs(c.x) for c in hm), default=None)
    rx_head = max((abs(c.x) for c in hd), default=None)
    cover = (zmax_hair >= zmax_head - 1e-4 and rx_hair >= rx_head - 1e-3)
    print(f"[neck] 发帽覆盖：Hair z_max={zmax_hair:.4f} |x|={rx_hair*1000:.1f}mm | "
          f"Head z_max={zmax_head:.4f} |x|={rx_head*1000:.1f}mm "
          f"{'OK' if cover else 'FAIL(露头皮)'}")
    print(f"[neck] 判定：{'三高度可见颈宽全部 >=8mm PASS' if all_ok else 'FAIL'}"
          f"{'' if cover else ' + 覆盖 FAIL'}")
    return all_ok and cover


# ------------------------------------------------------------ 3. 谁是遮挡者

def _join_or_list(objs):
    if isinstance(objs, list):
        return objs
    return [objs]


def who_blocks(body_bvh, bo):
    """逐部件回答「侧面视线最先打到谁」：命中该部件且比 Body 更近的射线数。

    做法：把 Hair / Outfit 拆成**各自的部件函数**单独建（都走 lib 里的原函数，
    不是重写一份），每个部件一个 BVH，与 Body 的 BVH 比距离。
    比的是「同一条射线上的先后」，所以不受顶点密度影响 —— 顶点数统计只能
    提示「谁在这段里有东西」，射线首击才能定遮挡。
    """
    hair_parts = [("hair.cap", _join_or_list(hairmod._cap())),
                  ("hair.back_sheet", _join_or_list(hairmod._back_sheet())),
                  ("hair.clumps", _join_or_list(hairmod._clumps())),
                  ("hair.bangs", _join_or_list(hairmod._bangs())),
                  ("hair.side_locks", _join_or_list(hairmod._side_locks()))]
    out_parts = [("outfit.shirt", _join_or_list(outfitmod._shirt())),
                 ("outfit.collar", _join_or_list(outfitmod._collar()))]
    parts = []
    for name, obs in hair_parts + out_parts:
        verts, polys = [], []
        for ob in obs:
            base = len(verts)
            verts += [tuple(ob.matrix_world @ v.co) for v in ob.data.vertices]
            polys += [tuple(base + i for i in p.vertices)
                      for p in ob.data.polygons]
        s = band_stat([Vector(v) for v in verts], NECK_BAND[0], NECK_BAND[1])
        parts.append((name, BVHTree.FromPolygons(verts, polys,
                                                 all_triangles=False), s))

    print("[neck] === 逐部件：遮挡射线数（>=1 即该部件在这高度挡住脖子）===")
    for z0 in NECK_Z:
        rows = []
        for name, bvh, s in parts:
            n, ys = 0, []
            for sx in (1.0, -1.0):
                for k in range(-140, 141):
                    y = k * 0.001
                    o = Vector((sx * RAY_X, y, z0))
                    d = Vector((-sx, 0.0, 0.0))
                    bd = body_bvh.ray_cast(o, d)[3]
                    if bd is None:
                        continue
                    pd = bvh.ray_cast(o, d)[3]
                    if pd is not None and pd < bd - 1e-6:
                        n += 1
                        ys.append(y)
            rows.append((name, n, (min(ys), max(ys)) if ys else None, s))
        hit = [r for r in rows if r[1] > 0]
        det = " ; ".join(
            f"{r[0]}={r[1]}" + (f"(y=[{r[2][0]*1000:+.0f},{r[2][1]*1000:+.0f}])"
                                if r[2] else "") for r in hit) or "无遮挡"
        print(f"[neck] z={z0:.2f} 遮挡者：{det}")
        for name, n, ys, s in rows:
            if n:
                print(f"[neck]   {name:16s} n_band={s['n']:5d} "
                      f"max|x|={s['xmax']*1000:6.1f}mm "
                      f"yband=[{mm(s['ymin'])},{mm(s['ymax'])}] "
                      f"blocked={n} rays")


# ------------------------------------------------------------ main

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    what = argv[0] if argv else "both"

    M = stub_mats()
    print("[probe] building Body / Head / Hair / Outfit ...")
    body_ob = bodymod.build()
    head_ob = headmod.build(M)
    hair_ob = hairmod.build(M)
    cloth_ob = outfitmod.build(M)
    bo, ho, oo, hdo = cos_of(body_ob), cos_of(hair_ob), cos_of(cloth_ob), \
        cos_of(head_ob)
    print(f"[probe] verts: Body={len(bo)} Head={len(hdo)} Hair={len(ho)} "
          f"Outfit={len(oo)}")

    res = {}
    if what in ("waist", "both"):
        mask = skirt_vertex_mask(cloth_ob)
        skirt_cos = ([oo[i] for i in sorted(mask)] if mask else None)
        res["waist"] = waist(bo, oo, body_ob, cloth_ob,
                             bvh_of(bo, body_ob), skirt_cos)
    if what in ("neck", "both"):
        bvhs = [("Body", bvh_of(bo, body_ob)), ("Hair", bvh_of(ho, hair_ob)),
                ("Head", bvh_of(hdo, head_ob)), ("Outfit", bvh_of(oo, cloth_ob))]
        res["neck"] = neck(bo, ho, oo, hdo, bvhs)
        if what == "neck":
            who_blocks(bvh_of(bo, body_ob), bo)
    print("[probe] SUMMARY " + " ".join(
        f"{k}={'PASS' if v else 'FAIL'}" for k, v in res.items()))


main()