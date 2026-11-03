# -*- coding: utf-8 -*-
r"""D 阶段探针：刘海分组 / 后发束沟壑 / 翻领 / 卷边 / 裙褶相位。

同一进程 import hair / outfit 现场构建，**不渲染**；像素部分直接读
`out/` 里已有的 m4 图（所以先跑过 m4_hair.py，否则像素项报 SKIP）。

用法（工作目录 人物建模/）：
    "D:/Program Files/Blender Foundation/Blender 5.2/blender.exe" \
        -b --factory-startup --python _stageD/d_probe.py
    python _stageD/d_probe.py        # 只做像素部分（几何项 SKIP）

口径纪律（和 DESIGN §4.1 / §1.4 一致）：
  · `_strand(widths, thick)` 的 widths / thick 都是**半径**，全宽 = 2×。
  · 刘海"组间缝"用**顶点级 x 排序找断开**，不用按缕名猜分组。
  · 读图必须按 `[::-1]` 翻转：Blender 的 Image.pixels 是 bottom-up，
    PIL 是 top-down；不翻转时全图分位看不出问题，但 ROI 会上下颠倒
    （c_probe.py:75-99 已踩过）。
"""
import os
import sys
import math

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))
OUT = os.path.join(HERE, "out")

try:
    import bpy
    HAS_BPY = True
except ImportError:
    HAS_BPY = False

import numpy as np

if not HAS_BPY:
    try:
        from PIL import Image
    except ImportError:
        Image = None


def out(tag, text):
    print(f"[dprobe] {tag}: {text}")


SKIRT_CY_D = 0.006   # 与 outfit.SKIRT_CY 一致（探针独立常量）


def mm(v):
    return "-" if v is None else f"{v * 1000:+.1f}"


# ================================================================ 像素工具

VIEWS = {
    "m4_face_front": dict(w=620, h=780, ortho=0.32, zc=1.4956, frontal=True),
    "m4_face_side": dict(w=620, h=780, ortho=0.32, zc=1.4956, frontal=False),
    "m5_body_front": dict(w=560, h=900, ortho=1.80, zc=0.86, frontal=True),
    "m4_face_back": dict(w=620, h=780, ortho=0.42, zc=1.40, frontal=True),
}

# 皮肤 toon 三档显示色（与 c_probe.py:66-70 同源，C 阶段未改 base/ramp）
SKIN_TIERS = [(198, 175, 191), (235, 202, 196), (247, 224, 211)]
TIER_DIST = 38.0


def read_rgb(name):
    if not name.endswith(".png"):
        name += ".png"
    path = os.path.join(OUT, name)
    if not os.path.exists(path):
        return None, path
    if HAS_BPY:
        im = bpy.data.images.load(path)
        w, h = im.size
        buf = np.empty(w * h * 4, dtype=np.float32)
        im.pixels.foreach_get(buf)
        # 8-bit sRGB PNG 的 pixels 已是 sRGB 编码值，×255 即可；必须 [::-1] 翻行
        a = (np.clip(buf.reshape(h, w, 4)[:, :, :3], 0.0, 1.0) * 255.0 + 0.5
             ).astype(np.uint8)[::-1]
        bpy.data.images.remove(im)
        return a, path
    if Image is None:
        return None, path
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8), path


def lum_of(a):
    af = a.astype(np.float32)
    return 0.2126 * af[:, :, 0] + 0.7152 * af[:, :, 1] + 0.0722 * af[:, :, 2]


def fg_mask(a):
    """前景判据。背景 = 四角中**亮度最低**那一角。

    不能用四角中位数：背面机位下左右下角是肩膀皮肤（185,165,180）/
    （249,226,210），中位背景会落到皮肤色上，暗背景 (53,60,75) 反而被判成前景
    （实测整幅 334k 像素里选中了 290k，指标全废）。
    """
    pts = [a[:8, :8].reshape(-1, 3), a[:8, -8:].reshape(-1, 3),
           a[-8:, :8].reshape(-1, 3), a[-8:, -8:].reshape(-1, 3)]
    lum = lambda c: 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    bg = min((np.median(p.astype(np.float32), axis=0) for p in pts), key=lum)
    return np.abs(a.astype(np.float32) - bg).max(axis=2) > 18


def skin_mask(a):
    af = a.astype(np.float32)
    d = np.minimum.reduce([np.sqrt(((af - np.array(c, np.float32)) ** 2).sum(axis=2))
                           for c in SKIN_TIERS])
    m = d < TIER_DIST
    # 粉色（头发）不算皮肤。头发的亮面 (250,193,206) 到皮肤档 (247,224,211)
    # 的欧氏距离只有 31，落在 38 的阈值内 —— 头顶整片会被误判成皮肤，
    # D1 bangs forehead_cover 因此报出 4.4%（分母里 skin 占 96%）。
    # 发色的 R−G 稳定在 53~58，皮肤只有 23~33，用 R−G 分得干净。
    m &= (af[:, :, 0] - af[:, :, 1]) <= 45.0
    return m


def hair_mask(a):
    """头发 = 前景 且 非皮肤色。

    不要再加 `lum < 180`：C4 的天使环把额头一带的头发打成了紫白
    (217,203,240)、亮度 209，用亮度阈值会把它整片漏掉（实测覆盖率
    从 ~100% 掉到 53%，分母里皮肤像素反而占了一半）。
    """
    return fg_mask(a) & (~skin_mask(a))


def roi_mask(view, shape, xr, zr):
    h, w = shape[:2]
    v = VIEWS[view]
    s = v["h"] / float(v["ortho"])
    px0 = int(round(v["w"] / 2.0 + xr[0] * s))
    px1 = int(round(v["w"] / 2.0 + xr[1] * s))
    py0 = int(round(v["h"] / 2.0 - (zr[1] - v["zc"]) * s))
    py1 = int(round(v["h"] / 2.0 - (zr[0] - v["zc"]) * s))
    m = np.zeros((h, w), dtype=bool)
    m[max(0, py0):min(h, py1 + 1), max(0, px0):min(w, px1 + 1)] = True
    return m


# ================================================================ 几何工具

def cos_of(ob):
    mw = ob.matrix_world
    return [mw @ v.co for v in ob.data.vertices]


def drop(*obs):
    for ob in obs:
        me = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.meshes.remove(me)


def x_segments(cos, gap=0.0010):
    """把顶点 x 投影排序后按 >gap 断开，返回 [(x_lo, x_hi), ...]。"""
    xs = sorted(c.x for c in cos)
    segs = [[xs[0], xs[0]]]
    for x in xs[1:]:
        if x - segs[-1][1] > gap:
            segs.append([x, x])
        else:
            segs[-1][1] = x
    return segs


def strand_rings(cos, seg):
    """tube() 的顶点 = 环×seg + cap_start/cap_end 两个圆心，末尾 2 个要剔掉。"""
    n_ring = (len(cos) // seg) * seg
    return [cos[i:i + seg] for i in range(0, n_ring, seg)]


# ================================================================ 几何：D1~D5

def geo_checks():
    import hair as hairmod
    import outfit as outfitmod

    def stub():
        m = {}
        for k in ("cloth_white", "cloth_navy", "hair", "skin"):
            m[k] = bpy.data.materials.new(k)
        return m

    M = stub()
    # 2026-11-03：发型分成三套（hair.style = long / bob / cards），D1/D2 这 5 条判据
    # 全部是照长发型写的 —— 分组刘海(bangs_groups)、后发束(clumps)、侧发、呆毛。
    # 鲍伯头与发卡是「整片/开缝曲面」，这些部件在几何里根本不存在，
    # 探针却照样去建临时对象来量，量出来的是模板默认值，与成品无关。
    # 所以 bob / cards 下这 5 条标 SKIP 并指向真正管用的口径（appearance.json 里的
    # bangs_bottom_z / bangs_over_eye / hair_back_ratio），不假装通过。
    bob = hairmod.charparams.get("hair.style", "long") in ("bob", "cards")

    # ---------------- D1 刘海 ----------------
    bangs = hairmod._bangs()
    bcos = []
    for ob in bangs:
        bcos += cos_of(ob)
    ztip = min(c.z for c in bcos)
    # 分组判据用「每缕的 x 包围盒」：顶点级排序在单缕内部也会出现 >1mm 的空隙
    # （tube 的环本身只有几个 x 值），会把一缕切成 3~4 段，实测 28 段全是假阳性。
    boxes = []
    for ob in bangs:
        cs = [ob.matrix_world @ v.co for v in ob.data.vertices]
        boxes.append((min(c.x for c in cs), max(c.x for c in cs)))
    drop(*bangs)
    boxes.sort()
    groups = [[boxes[0]]]
    gap_list = []
    for b in boxes[1:]:
        gap = b[0] - groups[-1][-1][1]
        if gap >= 0.0008:          # >=0.8mm 视为组间真缝（目标 1~2mm）
            gap_list.append(gap)
            groups.append([b])
        else:
            groups[-1].append(b)
    gspans = [(g[0][0], g[-1][1]) for g in groups]
    out("D1 bangs boxes", " ".join(
        f"[{a * 1000:+.1f},{b * 1000:+.1f}]" for a, b in boxes))
    if bob:
        out("D1 bangs groups", "SKIP（hair.style=bob：整片锯齿刘海，无 3 组分组）")
        out("D1 bangs gap_verdict", "SKIP（同上）")
        out("D1 bangs tip_z", "SKIP（同上；bob 的刘海高度见 appearance.json:bangs_bottom_z）")
    else:
        out("D1 bangs groups", f"groups={len(groups)} "
            f"sizes={[len(g) for g in groups]} "
            f"gaps=[{', '.join(mm(g) for g in gap_list)}]mm "
            f"spans=" + " ".join(f"[{a * 1000:+.1f},{b * 1000:+.1f}]" for a, b in gspans))
        ok_gap = (len(groups) == 3 and len(gap_list) == 2
                  and all(0.001 <= g <= 0.002 for g in gap_list))
        out("D1 bangs gap_verdict",
            f"{'OK' if ok_gap else 'FAIL'}（要求 3 组、每缝 1~2mm）")
        out("D1 bangs tip_z", f"min_z={ztip:.4f} {'OK' if 1.520 <= ztip <= 1.540 else 'FAIL'}"
            f"（要求 1.520~1.540，注意这是含半径的顶点 z，比 z_tip 略低）")

    # ---------------- D2 后发束 ----------------
    clumps = hairmod._clumps()
    back = hairmod._back_sheet()
    back_cos = cos_of(back)
    recs = []
    prof = []
    segs_z = []
    for ob in clumps:
        cs = cos_of(ob)
        seg_z = [c for c in cs if 1.285 <= c.z <= 1.315]
        if seg_z:
            segs_z.append((sum(c.x for c in seg_z) / len(seg_z),
                           max(c.y for c in seg_z)))
        rings = strand_rings(cs, 16)
        half_w = max((max(p.x for p in r) - min(p.x for p in r)) / 2.0 for r in rings)
        half_t = max((max(p.y for p in r) - min(p.y for p in r)) / 2.0 for r in rings)
        recs.append((half_w, half_t, ob.name))
        prof += [c for c in cs if 1.285 <= c.z <= 1.315]
    drop(*clumps)
    if bob:
        out("D2 clumps halfwidth", "SKIP（hair.style=bob：无后发束，发厚见 appearance.json:hair_back_ratio）")
        out("D2 clumps halfthick", "SKIP（同上）")
    elif recs:
        hw = [r[0] for r in recs]
        ht = [r[1] for r in recs]
        out("D2 clumps halfwidth", f"min={mm(min(hw))}mm max={mm(max(hw))}mm "
            f"n={len(recs)} "
            f"{'OK' if min(hw) >= 0.018 and max(hw) <= 0.024 else 'FAIL'}"
            f"（要求 18~24mm）")
        out("D2 clumps halfthick", f"min={mm(min(ht))}mm max={mm(max(ht))}mm "
            f"{'OK' if min(ht) >= 0.008 and max(ht) <= 0.010 else 'FAIL'}"
            f"（要求 8~10mm）")
    # 几何沟壑深度：z≈1.30 后脑横截面，把「发束+发片」按 x 分 2mm 箱取 max y，
    # y(x) 的峰谷差就是沟壑深度。像素标准差会被 toon 三阶色压平（阴影档是平色），
    # 所以几何量才是主证据。
    bed = [c for c in back_cos if 1.285 <= c.z <= 1.315]
    prof += bed
    if prof and len(segs_z) >= 3:
        # 沟壑 = 发束管顶 y 的中位数 − 相邻两缕**中点**处表面 y 的中位数。
        # 不要用「后脑整段 y(x) 的 max-min」：那会量到后脑边缘发片（y≈9mm）
        # 与发束（y≈114mm）的落差，报出 105mm 的假值。
        segs_z.sort()
        tops = sorted(t for _, t in segs_z)
        troughs = []
        for i in range(len(segs_z) - 1):
            mid = (segs_z[i][0] + segs_z[i + 1][0]) / 2.0
            cand = [c.y for c in prof if abs(c.x - mid) <= 0.004]
            if cand:
                troughs.append(max(cand))
        if troughs:
            peak_med = tops[len(tops) // 2]
            trough_med = sorted(troughs)[len(troughs) // 2]
            g = peak_med - trough_med
            out("D2 clumps groove_depth",
                f"peak_y={mm(peak_med)}mm trough_y={mm(trough_med)}mm "
                f"groove={mm(g)}mm n_strands={len(segs_z)} "
                f"{'OK' if g >= 0.004 else 'WARN(<4mm)'}")

    out("D2 back_sheet y_back",
        f"max_y={mm(max(c.y for c in back_cos))}mm")
    drop(back)
    # 不得露头皮：发帽顶端必须高过头骨、两侧必须包住头宽
    from head import HEAD
    head_zmax = max(r[0] for r in HEAD)
    head_xmax = max(r[1] for r in HEAD)
    cap = hairmod._cap()
    ccap = cos_of(cap)
    drop(cap)
    cap_z, cap_x = max(c.z for c in ccap), max(abs(c.x) for c in ccap)
    out("D2 cap coverage", f"hair_cap z_max={cap_z:.4f} x_max={mm(cap_x)}mm | "
        f"HEAD z_max={head_zmax:.4f} x_max={mm(head_xmax)}mm "
        f"{'OK(不露头皮)' if cap_z > head_zmax and cap_x > head_xmax else 'FAIL'}")

    # ---------------- D3 翻领 ----------------
    collar = outfitmod._collar()
    ccos = cos_of(collar)
    drop(collar)
    back_top = max((c.z for c in ccos if c.y > 0.015), default=None)
    # 「前」= V 缺口附近（|x|<=30mm 且在前侧）。只按 y<-0.015 会把
    # 两侧翼（a≈330°，z 已回升到 1.320）也当成前领口，V 深被量小 7mm。
    front = [(c.x, c.z) for c in ccos if c.y < -0.015 and abs(c.x) <= 0.030]
    front_low = min((z for _, z in front), default=None)
    front_top = max((z for _, z in front), default=None)
    out("D3 collar back_top",
        f"z={None if back_top is None else round(back_top, 4)} "
        f"(n={len(ccos)} verts)")
    out("D3 collar front_low",
        f"z={None if front_low is None else round(front_low, 4)} "
        f"(领根/折边最低) n_front={len(front)}")
    # 前中开口：|x|<6mm、前侧、z<1.33 的顶点必须为空（翻领前中不闭合）
    n_cfront = sum(1 for c in ccos if abs(c.x) < 0.006 and c.y < -0.02
                   and c.z < 1.330)
    out("D3 collar front_opening", f"前中 |x|<6mm 顶点数={n_cfront} "
        f"{'OK(开口)' if n_cfront == 0 else 'FAIL(前中闭合)'}")
    front_top = max((z for _, z in front), default=None)
    if back_top is not None and front_top is not None:
        # V 深按 DESIGN 口径 = 后领顶 − 前领顶（不是 − 领根，领根恒定 1.300 会把
        # 差值虚报成 38mm，那量的是"后领到肩"而不是 V 的深度）
        d = back_top - front_top
        out("D3 collar front_v_depth",
            f"后领顶={back_top:.4f} 前领顶={front_top:.4f} V深={mm(d)}mm "
            f"{'OK' if d >= 0.012 else 'FAIL'}（要求 >=12mm）")
        out("D3 collar back_above_front", f"{mm(d)}mm "
            f"{'OK' if d >= 0.008 else 'FAIL'}（要求后领 >= 前领+8mm）")

    # ---------------- D4/D5 需要整个 Outfit ----------------
    cloth = outfitmod.build(M)
    ccos2 = cos_of(cloth)

    # D4 卷边凸出 + 边界边数。
    # 口径（2026-11-01 修）：A5 拿「裸管 47mm（环层）」当基准，报出凸出 3.2mm；
    # 但 solidify 之后袖筒外表面是 48.34mm，真实可见凸出只有 1.65mm。
    # D4 的造型验收按可见凸出 = 卷边外表面 − 袖筒 solidify 后末端外表面。
    import bmesh
    from mathutils import Vector as _V
    SEG = 40
    tube_ob = outfitmod._sleeve(1, solid=False, cuff=False)   # 环层（A5 旧口径）
    vs = cos_of(tube_ob)
    ring = vs[-(SEG + 2):-2]
    cen = [sum(p[i] for p in ring) / len(ring) for i in range(3)]
    prev = vs[-(2 * SEG + 2):-(SEG + 2)]
    cen_p = [sum(p[i] for p in prev) / len(prev) for i in range(3)]
    axis = [cen[i] - cen_p[i] for i in range(3)]
    ln = math.sqrt(sum(a * a for a in axis)) or 1.0
    axis = [a / ln for a in axis]
    r_tube = max(math.sqrt(sum(((p[i] - cen[i]) - sum((p[j] - cen[j]) * axis[j]
                                                    for j in range(3)) * axis[i]) ** 2
                              for i in range(3))) for p in ring)
    drop(tube_ob)

    # 可见基准：同轴同面、solidify 之后的袖筒末端（tip ±6mm 带内的最大垂轴半径）
    _tip = _V((0.169, 0.006, 1.110))
    _ax = _V((-0.075, 0.050, -0.996)).normalized()
    sol_ob = outfitmod._sleeve(1, solid=True, cuff=False)
    _band = []
    for c in cos_of(sol_ob):
        d = c - _tip
        if abs(d.dot(_ax)) <= 0.006:
            _band.append((d - d.dot(_ax) * _ax).length)
    r_solid = max(_band) if _band else None
    drop(sol_ob)

    band = []
    for c in ccos2:
        if c.x <= 0.13:
            continue
        d = [c.x - cen[0], c.y - cen[1], c.z - cen[2]]
        if abs(sum(d[i] * axis[i] for i in range(3))) <= 0.010:
            perp = [d[i] - sum(d[j] * axis[j] for j in range(3)) * axis[i]
                    for i in range(3)]
            band.append(math.sqrt(sum(x * x for x in perp)))
    r_out = max(band) if band else None
    vis = None if (r_out is None or r_solid is None) else r_out - r_solid
    out("D4 cuff ring bulge",
        f"tube_r={mm(r_tube)}mm outfit_r_max={mm(r_out)}mm "
        f"sleeve_solid_r={mm(r_solid)}mm visible={mm(vis)}mm "
        f"(旧环层口径={mm(None if r_out is None else r_out - r_tube)}mm) "
        f"{'OK' if (vis is not None and 0.002 <= vis <= 0.004) else 'FAIL'}"
        f"（可见凸出要求 2~4mm）")
    # 造型验收：内缘厚、外缘薄，且都仍 >=2mm 可见
    # 分段必须对准 tube 的三个环（t = −10 / −4 / 0）：环间是**斜面**，
    # Solidify 在斜面上法线倾斜，径向只增约 0.6~0.7mm，取斜段会把
    # 「内缘厚」量成 1.9mm（实为 3.4mm）。这是口径陷阱，不是造型问题。
    segs = []
    for lo, hi, tag in ((-0.011, -0.008, "inner"), (-0.005, -0.003, "mid"),
                        (-0.001, 0.001, "outer")):
        b = []
        for c in ccos2:
            if c.x <= 0.13:
                continue
            d = [c.x - cen[0], c.y - cen[1], c.z - cen[2]]
            t = sum(d[i] * axis[i] for i in range(3))
            if lo <= t < hi:
                perp = [d[i] - t * axis[i] for i in range(3)]
                b.append(math.sqrt(sum(x * x for x in perp)))
        if b and r_solid is not None:
            segs.append((tag, max(b) - r_solid))
    if segs:
        detail = " ".join(f"{t}:{v * 1000:+.2f}" for t, v in segs)
        dmap = dict(segs)
        ok = (dmap.get("inner", 0) > dmap.get("outer", 0) + 0.0003
              and all(v >= 0.002 for _, v in segs))
        out("D4 cuff shape", f"{detail}mm "
            f"{'OK(内厚外薄)' if ok else 'FAIL'}（要求 inner>outer+0.3mm 且均>=2mm）")

    bm = bmesh.new()
    bm.from_mesh(cloth.data)
    n_bound = sum(1 for e in bm.edges if e.is_boundary)
    bm.free()
    out("D4 cuff boundary_edges", f"{n_bound} {'OK' if n_bound == 0 else 'FAIL'}")

    # D5 裙褶（2026-11-01 口径修正）：取**未 solidify 的裙摆单环**，按索引
    # 顺序（= _skirt 的角度顺序）做 DFT。22 次分量才是褶幅，2 次分量是椭圆
    # 本身，互不污染。
    # 旧口径（z 窗口 0.644~0.658 内排序后每褶 max-min）同时收进内外两层
    # （实测 264 = 132×2 个点）、每褶仅 6 点，差值里混着椭圆各向异性，
    # 报出 32.2mm 的假值 —— 典型的「量到的不是要量的东西」。
    skirt = outfitmod._skirt(solid=False)
    scos = cos_of(skirt)
    drop(skirt)
    seg = outfitmod.SKIRT_SEG
    pleats = 22
    if len(scos) >= seg:
        ring = scos[-seg:]                     # 最后一环 = 裙摆 z=0.650
        n = len(ring)
        rk = np.array([math.hypot(c.x, c.y - SKIRT_CY_D) for c in ring],
                      dtype=np.float64)
        kk = np.arange(n)
        th = 2.0 * np.pi * pleats * kk / n

        def _amp(order):
            c = np.sum(rk * np.exp(-2j * np.pi * order * kk / n)) * 2.0 / n
            return float(abs(c)), float(np.angle(c))

        a1, p1 = _amp(pleats)
        a2, p2 = _amp(2 * pleats)
        w = a1 * np.cos(th + p1) + a2 * np.cos(2.0 * th + p2)
        peak, trough = float(w.max()), float(w.min())
        out("D5 pleat peak_trough",
            f"seg={n} per_pleat={n / pleats:.1f} amp22={mm(a1)}mm "
            f"amp44={mm(a2)}mm peak={mm(peak)}mm trough={mm(trough)}mm "
            f"diff={mm(peak - trough)}mm "
            f"{'OK' if peak - trough >= 0.010 else 'FAIL'}（要求 >=10mm）")
        # 正面中线：|x| 最小、y 最前的顶点（a≈−90°）
        idx = min(range(n), key=lambda i: (abs(ring[i].x), ring[i].y))
        w_mid = float(w[idx])
        out("D5 pleat center_phase",
            f"mid_k={idx} a_mid={math.degrees(2 * math.pi * idx / n) - 360:.1f}deg "
            f"w_mid={mm(w_mid)}mm peak={mm(peak)}mm "
            f"delta={mm(peak - w_mid)}mm "
            f"{'OK(中线是峰)' if peak - w_mid <= 0.0015 else 'FAIL(中线不是峰)'}")
    else:
        out("D5 pleat peak_trough", "SKIP（裙子顶点数不足一环）")

    drop(cloth)


def rmid_is_peak(r_mid, r_max):
    """正面中线半径与全局峰值的差 < 1.5mm 即认为中线落在褶峰上。"""
    return (r_max - r_mid) <= 0.0015


# ================================================================ 像素：D1 刘海覆盖 / D2 沟壑

def pix_checks():
    a, path = read_rgb("m4_face_front")
    if a is None:
        out("D1 bangs forehead_cover", f"SKIP（缺 {path}，先跑 m4_hair.py）")
    else:
        # 额头 ROI：眉上沿 1.540 到发际线 1.580，|x|<60mm
        m = roi_mask("m4_face_front", a.shape, (-0.060, 0.060), (1.540, 1.580))
        hm = hair_mask(a) & m
        sm = skin_mask(a) & m
        # 分母是「额头区里 头发+皮肤」的像素，不是 fg（矩形 ROI 会把背景和
        # 两侧的侧发一起算进来，实测那样分母虚高 25 倍，覆盖率只剩 4%）
        den = int(hm.sum()) + int(sm.sum())
        cov = float(hm.sum()) / max(1, den) * 100.0
        out("D1 bangs forehead_cover", f"{cov:.1f}%（hair={int(hm.sum())}, "
            f"skin={int(sm.sum())}, den={den}）"
            f"{'OK' if cov >= 70.0 else 'FAIL'}（要求 >=70%）")

    # 必须用**背面**机位：后发束是沿 x 并排的纵向条，侧面机位沿 x 看会把
    # 7 条互相遮住（实测侧面 scan_diff_std 22.4，改完沟壑反而降到 19.5，
    # 指标根本没在量沟壑）。背面正对时，画面横向 = 世界 x，正好切到排列。
    a2, path2 = read_rgb("m4_face_back")
    if a2 is None:
        out("D2 clumps luminance_std", f"SKIP（缺 {path2}）")
        return
    hm2 = hair_mask(a2)
    h, w = a2.shape[:2]
    v = VIEWS["m4_face_back"]
    s = v["h"] / float(v["ortho"])
    py0 = int(round(v["h"] / 2.0 - (1.480 - v["zc"]) * s))
    py1 = int(round(v["h"] / 2.0 - (1.050 - v["zc"]) * s))
    py0, py1 = max(0, py0), min(h, py1 + 1)
    # 只取后脑宽度（|x|<105mm），不要把两侧肩膀和背景算进来
    s_px = v["h"] / float(v["ortho"])
    px0 = int(round(v["w"] / 2.0 - 0.105 * s_px))
    px1 = int(round(v["w"] / 2.0 + 0.105 * s_px))
    roi = np.zeros_like(hm2)
    roi[py0:py1, max(0, px0):min(w, px1 + 1)] = True
    sel = hm2 & roi
    if int(sel.sum()) < 200:
        out("D2 clumps luminance_std", f"SKIP（后发 ROI 头发像素仅 {int(sel.sum())}）")
        return
    lum = lum_of(a2)
    std_all = float(np.std(lum[sel]))
    diffs = []
    for r in range(py0, py1):
        cols = np.where(sel[r])[0]
        if len(cols) < 12:
            continue
        vals = lum[r, cols]
        diffs.append(np.std(np.diff(vals)))
    d_std = float(np.mean(diffs)) if diffs else 0.0
    # baseline 口径陷阱：9.99 是「D2 改前」（半宽 28 / 间距 26 / 厚 11）的背面
    # scan_diff_std。但那一版的 9.99 **不是沟壑**，而是相邻发束重叠 30mm 后
    # 交叠处隆起成峰造成的亮度跳变（DESIGN §1.4 原话「重叠过度、沟壑被填平」）。
    # 把重叠峰当沟壑基线，会让「减薄后沟壑更清晰、峰更少」被判成退化
    # （实测 7.69 < 12.99）。所以这条只作旁证，主证据是上面的几何 groove_depth。
    base = 9.99
    out("D2 clumps luminance_std", f"roi_std={std_all:.2f} "
        f"scan_diff_std={d_std:.2f} px={int(sel.sum())} rows={len(diffs)} "
        f"(改前基线={base:.2f}，1.3x={base * 1.3:.2f}；实测 {d_std / base:.2f}x "
        f"→ 未达像素判据，但基线含重叠峰伪信号，该判据失效；以 groove_depth 为准)")


def main():
    if HAS_BPY:
        geo_checks()
        pix_checks()
    else:
        pix_checks()
    out("done", "D probe finished")


if __name__ == "__main__":
    main()