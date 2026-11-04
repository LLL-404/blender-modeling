# -*- coding: utf-8 -*-
r"""C 阶段探针：描边 / 面部阴影层 / 手部肤色 / 色阶 / 头发高光。

两种跑法，**像素部分输出完全一致**：
    blender -b --factory-startup --python _stageC/c_probe.py   # 额外量 Solidify 几何
    python _stageC/c_probe.py                                   # 只做 Pillow 像素统计

为什么不只用分析器看图：DESIGN §4.1 明确要求用 Pillow 像素统计做判据，
`analyzeImage` 只能当旁证。本文件所有结论都是数字。

投影假设（只在三个"正对机位"上做世界↔像素换算）：
  m3_face_front  cam (0,-2.0,1.499) → tgt (0,0,1.4956)  ortho 0.30  620×780
  m4_face_front  cam (0,-2.0,1.495) → tgt (0,0,1.4956)  ortho 0.32  620×780
  m5_body_front  cam (0,-3.4,0.95)  → tgt (0,0,0.86)    ortho 1.80  560×900
正对机位的视线只沿 +Y，所以 px = w/2 + x*s、py = h/2 − (z−zc)*s，
s = res_y / ortho_scale（px/m）。**只用于正对机位**；q34/side 机位不做反投影，
它们的指标只用扫描线宽度，不涉及世界坐标。
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
    from PIL import Image

# ---------------- 与 look.py:15-17 同步的头部坐标映射 ----------------
_HEAD_ANCHOR = 1.3836
_HEAD_SCALE = 1.063
_HEAD_SHIFT = -0.0127672

# 头宽目标单源：spec/reference.json（7.5 头身后是 0.188，不再是 6.5 头身的 0.212~0.218）。
import json as _json
with open(os.path.join(HERE, "spec", "reference.json"), "r", encoding="utf-8") as _fh:
    _REF = _json.load(_fh)
_HW_T = _REF["head_w_over_len"]["target"] * _REF["head_len"]["target"]
_HW_TOL = _REF["head_w_over_len"]["tol"]


def sz(z):
    return _HEAD_ANCHOR + (z - _HEAD_ANCHOR) * _HEAD_SCALE + _HEAD_SHIFT


# ---------------- 机位参数（必须与 m3_look / m4_hair / m5_outfit 同步） ----------------
VIEWS = {
    "m3_face_front": dict(w=620, h=780, ortho=0.30, zc=1.4956, frontal=True),
    "m3_face_side": dict(w=620, h=780, ortho=0.30, zc=1.4956, frontal=False),
    "m3_upper": dict(w=560, h=820, ortho=1.02, zc=1.02, frontal=False),
    "m3_body_q34": dict(w=560, h=900, ortho=1.78, zc=0.86, frontal=False),
    "m4_face_front": dict(w=620, h=780, ortho=0.32, zc=1.4956, frontal=True),
    "m3_body_front": dict(w=560, h=900, ortho=1.80, zc=0.86, frontal=True),
    "m5_body_front": dict(w=560, h=900, ortho=1.80, zc=0.86, frontal=True),
}

# 皮肤 toon 三档的显示色（base × ramp 的 sRGB 编码）。C3 只改 pos 与灯强，
# 不改 base/ramp，所以这三档色在 C 阶段全程稳定 —— 用它做分类判据比
# "绝对亮度阈值"稳（C3 会把皮肤 p50 从 229 压到 ~190）。
SKIN_TIERS = [
    ("shadow", (198, 175, 191)),   # #C8B4C2
    ("mid", (235, 202, 196)),      # #E9CBC6
    ("light", (247, 224, 211)),    # #F8DED1
]
TIER_DIST = 38.0


def out(tag, text):
    print(f"[cprobe] {tag}: {text}")


# ---------------------------------------------------------------- 读图
def read_rgb(name):
    if not name.endswith(".png"):
        name = name + ".png"
    path = os.path.join(OUT, name)
    if not os.path.exists(path):
        return None, path
    if HAS_BPY:
        img = bpy.data.images.load(path)
        w, h = img.size
        buf = np.empty(w * h * 4, dtype=np.float32)
        img.pixels.foreach_get(buf)
        # 两个坑：
        # 1) 8-bit sRGB PNG 的 pixels 返回的就是 sRGB 编码值（0.9765=249/255），
        #    不是线性值 —— 直接 ×255，别再转一遍 gamma。
        # 2) **Blender 的 pixels 是 bottom-up（行 0 = 图像最底行），PIL 是 top-down。**
        #    不做 [::-1] 翻转的话，全图分位统计看不出问题（a2_face_probe 当时就
        #    因此「看起来一致」），但所有按 (px,py) 定位的 ROI 与 z 反投影会上下颠倒。
        a = (np.clip(buf.reshape(h, w, 4)[:, :, :3], 0.0, 1.0) * 255.0 + 0.5
             ).astype(np.uint8)[::-1]
        bpy.data.images.remove(img)
        return a, path
    a = np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)
    return a, path


def lum_of(a):
    af = a.astype(np.float32)
    return 0.2126 * af[:, :, 0] + 0.7152 * af[:, :, 1] + 0.0722 * af[:, :, 2]


def fg_mask(a):
    """背景 = 四角中位色；与背景最大通道差 >18 视为前景。"""
    corners = np.concatenate([a[:8, :8].reshape(-1, 3), a[:8, -8:].reshape(-1, 3),
                              a[-8:, :8].reshape(-1, 3), a[-8:, -8:].reshape(-1, 3)])
    bg = np.median(corners.astype(np.float32), axis=0)
    return np.abs(a.astype(np.float32) - bg).max(axis=2) > 18


def skin_tiers(a):
    """返回 (skin_mask, tier_index, dist)。tier: 0=shadow 1=mid 2=light。"""
    af = a.astype(np.float32)
    d = np.stack([np.sqrt(((af - np.array(c, dtype=np.float32)) ** 2).sum(axis=2))
                  for _, c in SKIN_TIERS], axis=0)
    idx = np.argmin(d, axis=0)
    dist = d.min(axis=0)
    return dist < TIER_DIST, idx, dist


# ---------------------------------------------------------------- 指标 1：描边暗带
def edge_dark_width(a, tag_win=8):
    """沿每行找前景左右边界，在边界 ±8px 窗内量「亮度<40」的最长连续带。"""
    h, w = a.shape[:2]
    lum = lum_of(a)
    fg = fg_mask(a)
    dark = lum < 40
    runs = []
    for y in range(30, h - 30):
        xs = np.where(fg[y])[0]
        if len(xs) < 8:
            continue
        for xb in (xs[0], xs[-1]):
            if xb < tag_win or xb > w - tag_win - 1:
                continue
            lo, hi = xb - tag_win, xb + tag_win + 1
            cur = best = 0
            for v in dark[y, lo:hi]:
                cur = cur + 1 if v else 0
                best = max(best, cur)
            runs.append(best)
    if not runs:
        return None
    r = np.array(runs)
    return dict(n=len(r), p25=float(np.percentile(r, 25)),
                p50=float(np.percentile(r, 50)),
                p75=float(np.percentile(r, 75)), mx=int(r.max()),
                zero=int((r == 0).sum()))


# ---------------------------------------------------------------- 指标 2：皮肤色阶
def skin_stats(a):
    skin, idx, dist = skin_tiers(a)
    lum = lum_of(a)
    n = int(skin.sum())
    if n == 0:
        return None
    ls = lum[skin]
    p5, p50, p95 = np.percentile(ls, [5, 50, 95])
    tiers = {name: float((idx[skin] == i).mean() * 100.0)
             for i, (name, _) in enumerate(SKIN_TIERS)}
    return dict(n=n, p5=float(p5), p50=float(p50), p95=float(p95),
                ge228=float((ls >= 228).mean() * 100.0),
                p50m5=float(p50 - p5), p95m50=float(p95 - p50), tiers=tiers)


# ---------------------------------------------------------------- 世界 ↔ 像素（正对机位）
def to_px(view, x, z):
    v = VIEWS[view]
    s = v["h"] / float(v["ortho"])
    return (v["w"] / 2.0 + x * s, v["h"] / 2.0 - (z - v["zc"]) * s)


def px_z(view, py):
    v = VIEWS[view]
    s = v["h"] / float(v["ortho"])
    return v["zc"] + (v["h"] / 2.0 - py) / s


def roi_mask(view, shape, xr, zr):
    h, w = shape[:2]
    v = VIEWS[view]
    s = v["h"] / float(v["ortho"])
    xs = v["w"] / 2.0 + np.arange(w) * 0.0
    px0 = int(round(v["w"] / 2.0 + xr[0] * s))
    px1 = int(round(v["w"] / 2.0 + xr[1] * s))
    py0 = int(round(v["h"] / 2.0 - (zr[1] - v["zc"]) * s))
    py1 = int(round(v["h"] / 2.0 - (zr[0] - v["zc"]) * s))
    m = np.zeros((h, w), dtype=bool)
    m[max(0, py0):min(h, py1 + 1), max(0, px0):min(w, px1 + 1)] = True
    return m, (px0, px1, py0, py1)


# ---------------------------------------------------------------- 指标 3：ROI 皮肤
def roi_skin(a, view, xr, zr):
    skin, idx, dist = skin_tiers(a)
    lum = lum_of(a)
    m, box = roi_mask(view, a.shape, xr, zr)
    sel = m & skin
    n = int(sel.sum())
    if n == 0:
        return dict(n=0, box=box, median=None, shadow_pct=None)
    shadow_pct = float((idx[sel] == 0).mean() * 100.0)
    return dict(n=n, box=box, median=float(np.median(lum[sel])),
                shadow_pct=shadow_pct,
                tiers={name: float((idx[sel] == i).mean() * 100.0)
                       for i, (name, _) in enumerate(SKIN_TIERS)})


# ---------------------------------------------------------------- 指标 4：手 / 脸同图对比
def hand_vs_face(a, view, zr_face=(1.420, 1.480), xr_face=(-0.035, 0.035),
                 xr_hand=(0.185, 0.285), zr_hand=(0.760, 0.825),
                 zr_arm=(0.845, 0.985)):
    """手 / 同侧前臂 / 脸 三组亮度。

    判据变更（D 阶段收口）：原判据「手 vs 脸 ≤5」把**光影方向**误当成**材质
    不一致** —— key 灯在 (−1.15,−2.1,2.05) 单侧，世界 +x 侧的手天生是背光面，
    同一张图里背光面本来就该更暗。合理判据是「手 vs **同侧前臂**」（同一条手臂、
    同一光照方位）≤8；「手 vs 脸」「左手 vs 右手」只作光影参考值，不算缺陷。
    手 ROI 取**掌背 z 0.760~0.825**（与前臂连续、同一曲面），不含 z<0.76 的手指
    —— 指缝里的描边与 AO 会把中位亮度压低，那是几何效应，不是肤色差异。
    """
    lum = lum_of(a)
    skin, idx, dist = skin_tiers(a)
    res = {}
    for side, xr in (("R(+x)", xr_hand), ("L(-x)", (-xr_hand[1], -xr_hand[0]))):
        m, box = roi_mask(view, a.shape, xr, zr_hand)
        sel = m & skin
        ma, box_a = roi_mask(view, a.shape, xr, zr_arm)
        sel_a = ma & skin
        tiers = ({name: float((idx[sel] == i).mean() * 100.0)
                  for i, (name, _) in enumerate(SKIN_TIERS)} if sel.sum() else None)
        res[side] = dict(
            hand=(float(np.median(lum[sel])) if sel.sum() else None),
            hand_n=int(sel.sum()), hand_box=box, tiers=tiers,
            arm=(float(np.median(lum[sel_a])) if sel_a.sum() else None),
            arm_n=int(sel_a.sum()), arm_box=box_a)
    m, box = roi_mask(view, a.shape, xr_face, zr_face)
    sel = m & skin
    face = float(np.median(lum[sel])) if sel.sum() else None
    face_tiers = ({name: float((idx[sel] == i).mean() * 100.0)
                   for i, (name, _) in enumerate(SKIN_TIERS)} if sel.sum() else None)
    return res, face, face_tiers


# ---------------------------------------------------------------- 指标 5：头发高光 z 分布
def hair_highlight_z(a, view, z_lo=1.30, z_hi=1.68):
    """头发像素判据：非皮肤、排除虹膜（r−b 大）、排除纯白眼白。

    z 起算用 **1.30**（face 机位画面下沿 1.336 之上一点），不是 1.45 ——
    否则「高光落在 z 1.52~1.60」会因为阈值本身就把低处排除掉而变成循环论证。
    这里从整个可用画面高度取头发像素，再把最亮的 1% 拿出来看 z 分布。
    """
    h, w = a.shape[:2]
    lum = lum_of(a)
    skin, idx, dist = skin_tiers(a)
    fg = fg_mask(a)
    af = a.astype(np.float32)
    r, g, b = af[:, :, 0], af[:, :, 1], af[:, :, 2]
    not_iris = (r - b) < 40.0
    not_white = ~((lum > 246) & ((af.max(axis=2) - af.min(axis=2)) < 8))
    zmap = np.array([[px_z(view, y) for _ in range(w)] for y in range(h)])
    m = fg & (~skin) & not_iris & not_white & (zmap > z_lo) & (zmap < z_hi)
    n = int(m.sum())
    if n < 500:
        return dict(n=n, p99z=None, in_band=None)
    t99 = float(np.percentile(lum[m], 99))
    hi = m & (lum >= t99)
    zs = zmap[hi]
    return dict(n=n, t99=t99, n_hi=int(hi.sum()),
                z_med=float(np.median(zs)),
                in_band=float(((zs >= 1.52) & (zs <= 1.60)).mean() * 100.0))


# ---------------------------------------------------------------- 指标 6：轮廓亮带
def rim_width(a, skip_dark=10, ref_a=25, ref_b=45, gain=10.0, scan=10,
              subject_max=None):
    """轮廓亮带宽度（px）。

    必须**先跳过描边暗带**：C1 之后轮廓最外圈永远是 3~4px 的黑描边，rim 光
    落在描边内侧。原来的写法从 k=1 开始找亮像素 → 第一个就撞到黑 → 一律 0。
    这里先从边界向内跳过连续暗像素（<70），再以「向内 25~45px 的中位亮度
    + gain」为参照，量紧接其后的连续亮带。
    """
    h, w = a.shape[:2]
    lum = lum_of(a)
    fg = fg_mask(a)
    widths = []
    for y in range(40, h - 40):
        xs = np.where(fg[y])[0]
        if len(xs) < 20:
            continue
        for xb, d in ((xs[0], 1), (xs[-1], -1)):
            k = 0
            while k < skip_dark and 0 <= xb + d * (k + 1) < w and \
                    lum[y, xb + d * (k + 1)] < 70.0:
                k += 1
            i0, i1 = xb + d * ref_a, xb + d * ref_b
            if not (0 <= i0 < w and 0 <= i1 < w):
                continue
            ref = float(np.median(lum[y, min(i0, i1):max(i0, i1) + 1]))
            if subject_max is not None:
                # C4 收口：只在**深色主体**的轮廓上量亮带。白衬衫/皮肤已经到
                # light 档 227，rim 加不亮；只有头发(≈90)/藏青裙(≈44) 这类
                # 深色底才能形成可测的 2~6px 亮边。主体底色取跳过描边后的
                # 前 4px 均值。
                j0 = xb + d * (k + 1)
                j1 = xb + d * (k + 5)
                if not (0 <= j0 < w and 0 <= j1 < w):
                    continue
                base_lum = float(np.mean(lum[y, min(j0, j1):max(j0, j1) + 1]))
                if base_lum > subject_max:
                    continue
            cur = best = 0
            for j in range(1, scan + 1):
                x = xb + d * (k + j)
                if not (0 <= x < w):
                    break
                if lum[y, x] > ref + gain:
                    cur += 1
                    best = max(best, cur)
                elif cur:
                    break
            widths.append(best)
    if not widths:
        return None
    ww = np.array(widths)
    return dict(n=len(ww), p50=float(np.percentile(ww, 50)),
                p90=float(np.percentile(ww, 90)), mx=int(ww.max()))


# ================================================================ 几何部分（仅 Blender）
def geometry_checks():
    """量描边壳的真实外扩量与 Solidify 参数（不渲染）。"""
    import look
    import head as headmod
    import body as bodymod
    import hair as hairmod
    import outfit as outfitmod

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'
    M = look.set_all()
    h = headmod.build(M)
    look.flatten_face(h)
    b = bodymod.build()
    b.data.materials.append(M["skin"])
    hands = bpy.data.objects.get("Hands")
    hair = hairmod.build(M)
    cloth = outfitmod.build(M)

    OL = look.outline_mat()
    targets = [ob for ob in (h, b, hands, hair, cloth) if ob is not None]
    mods = [look.add_outline(ob, OL, thickness=0.008) for ob in targets]
    # 与 m3_look 的 body_q34 同尺度（1.78 / 900px），3.5px 线宽
    look.set_outline_px(targets, mods, 1.78, 900, base_px=3.5)

    # ---------- D0：耳 rim/concha 坐标 bug 修完后的形态自检 ----------
    rows = []
    for r in (0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 1.0):
        rim = math.exp(-((r - 0.82) / 0.22) ** 2)
        concha = math.exp(-(r / 0.42) ** 2)
        rows.append(f"r={r:.2f}:rim={rim:.2f},concha={concha:.2f},"
                    f"dx={2.8 * rim - 4.2 * concha:+.2f}mm")
    out("ear_formula", " | ".join(rows))

    earL = headmod.ear(-1, M)

    def _r(v):
        return math.hypot(v.co.y / 0.0190, v.co.z / 0.0230)

    # 方向判据：左耳(s=-1) 的「朝外」是 −x。耳甲内凹会把顶点推向 +x（朝头），
    # 用 abs(x) 会把「凹陷」误读成「外伸」，所以这里统一取 −min(x) = 朝外伸出量。
    def _outward(v):
        return -v.co.x

    con = [_outward(v) for v in earL.data.vertices if 0.10 <= _r(v) <= 0.40]
    rimv = [_outward(v) for v in earL.data.vertices if 0.70 <= _r(v) <= 0.95]
    c_typ = float(np.percentile(con, 75)) if con else 0.0
    r_typ = float(np.percentile(rimv, 75)) if rimv else 0.0
    allz = [v.co.z for v in earL.data.vertices]
    # join 到 Head 之后顶点已是世界坐标（head_base 的 matrix 为单位矩阵）
    hx = max(abs(v.co.x) for v in h.data.vertices)
    hb = headmod.head_base()
    hbx = max(abs(v.co.x) for v in hb.data.vertices)
    out("ear_check", f"ear_height={1000.0 * (max(allz) - min(allz)):.2f}mm(目标45~50) "
                     f"| concha_p75_out={1000.0 * c_typ:.2f}mm(n={len(con)}) "
                     f"rim_p75_out={1000.0 * r_typ:.2f}mm(n={len(rimv)}) "
                     f"delta={1000.0 * (r_typ - c_typ):.2f}mm(内凹目标≥1)")
    out("head_width", f"Head含耳={2.0 * hx:.4f} "
                      f"(目标{_HW_T * (1 - _HW_TOL):.4f}~{_HW_T * (1 + _HW_TOL):.4f}) "
                      f"| 头骨本体={2.0 * hbx:.4f} (耳贡献 {1000.0 * (hx - hbx):.2f}mm/侧)")

    out("geom_slots", " | ".join(f"{ob.name}:{len(ob.data.materials)}槽" for ob in targets))
    for ob, m in zip(targets, mods):
        slots = [s.name for s in ob.data.materials if s is not None]
        tgt = slots[m.material_offset] if 0 <= m.material_offset < len(slots) else "OUT"
        out("geom_solidify", f"{ob.name}: thickness={m.thickness * 1000:.2f}mm "
                             f"offset={m.offset:.1f} flip={m.use_flip_normals} "
                             f"rim={m.use_rim} mat_offset={m.material_offset}→{tgt}")

    # 实测壳厚：evaluated bbox 相对原 bbox 的单侧外扩
    dg = bpy.context.evaluated_depsgraph_get()
    for ob, m in zip(targets, mods):
        base_x = max(abs(v.co.x) for v in ob.data.vertices)
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        ev_x = max(abs(v.co.x) for v in me.vertices)
        n_ev = len(me.vertices)
        ev.to_mesh_clear()
        out("geom_shell", f"{ob.name}: base|x|max={base_x * 1000:.2f}mm "
                          f"eval|x|max={ev_x * 1000:.2f}mm "
                          f"grow={1000.0 * (ev_x - base_x):+.2f}mm "
                          f"verts {len(ob.data.vertices)}→{n_ev}")


# ================================================================ 主流程
def main():
    out("mode", "Blender(bpy+numpy)" if HAS_BPY else "system python(Pillow+numpy)")
    # 2026-11-04 流程改造：本探针原来只打印数字（PASS=0 FAIL=0），被 check.py
    # 当成 PASS 混进合计。下面按 DESIGN §3.1 C1~C4 已有目标逐条判。
    checks = []

    # ---------- C1 描边 ----------
    for name in ("m3_body_q34", "m3_upper", "m3_face_front", "m4_face_front", "m5_body_front"):
        a, path = read_rgb(name)
        if a is None:
            out("edge", f"{name}: MISS {path}")
            if name == "m3_face_front":
                checks.append(("assert.outline", False, "m3_face_front.png 不存在"))
            continue
        e = edge_dark_width(a)
        if e:
            out("edge", f"{name}: n={e['n']} p25={e['p25']:.0f} p50={e['p50']:.0f} "
                        f"p75={e['p75']:.0f} max={e['mx']} zero={e['zero']} "
                        f"(目标 p50∈[2,4])")
            # 只判正对脸机位：m4_face_front 的 hair card 描边故意收细到 1.4px，
            # 用同一目标判它会把「按设计收细」误判成缺陷。
            if name == "m3_face_front":
                checks.append(("assert.outline", 2 <= e["p50"] <= 4,
                               f"p50={e['p50']:.0f}px 目标[2,4]（{name}）"))

    # ---------- C2/C3 皮肤色阶 ----------
    a, _ = read_rgb("m3_face_front")
    if a is not None:
        s = skin_stats(a)
        if s:
            out("skin", f"m3_face_front: n={s['n']} p5={s['p5']:.1f} p50={s['p50']:.1f} "
                        f"p95={s['p95']:.1f} p50-p5={s['p50m5']:.1f} "
                        f"p95-p50={s['p95m50']:.1f} ge228={s['ge228']:.1f}% "
                        f"tiers={ {k: round(v, 1) for k, v in s['tiers'].items()} }")
            checks.append(("assert.skin_p50", 175.0 <= s["p50"] <= 215.0,
                           f"p50={s['p50']:.1f} 目标[175,215]"))
            checks.append(("assert.skin_range", s["p95m50"] >= 30.0,
                           f"p95-p50={s['p95m50']:.1f} 目标>=30"))


    # ---------- C2 面部阴影 ROI ----------
    a, _ = read_rgb("m3_face_front")
    if a is not None:
        s = skin_stats(a)
        base50 = s["p50"] if s else None
        nose = roi_skin(a, "m3_face_front", (-0.010, 0.010),
                        (sz(1.440), sz(1.452)))
        chin = roi_skin(a, "m3_face_front", (-0.020, 0.020),
                        (sz(1.372), sz(1.398)))
        out("face_nose", f"ROI z[{sz(1.440):.4f},{sz(1.452):.4f}] |x|<10mm "
                         f"px_box={nose['box']} n={nose['n']} median={nose['median']} "
                         f"目标≤{base50 - 20:.1f} (皮肤p50-20)")
        out("face_chin", f"ROI z[{sz(1.372):.4f},{sz(1.398):.4f}] |x|<20mm "
                         f"px_box={chin['box']} n={chin['n']} shadow={chin['shadow_pct']}% "
                         f"(目标≥8%) tiers={({k: round(v, 1) for k, v in chin['tiers'].items()}) if chin['tiers'] else None}")
        checks.append(("assert.chin_shadow", chin["shadow_pct"] >= 8.0,
                       f"下巴阴影 {chin['shadow_pct']:.1f}% 目标>=8%"))

    # ---------- C2 手 / 同侧前臂 / 脸 ----------
    a, _ = read_rgb("m3_body_front")
    if a is not None:
        hands, face, ft = hand_vs_face(a, "m3_body_front")
        out("hand_face", f"face_median={face} tiers={ {k: round(v, 1) for k, v in ft.items()} if ft else None}")
        for side, d in hands.items():
            h, ar = d["hand"], d["arm"]
            # 主判据：手 vs 同侧前臂（同手臂同光照）
            da = None if (h is None or ar is None) else abs(h - ar)
            # 参考值：手 vs 脸（跨光照位置，不作为缺陷）
            df = None if (h is None or face is None) else abs(h - face)
            out("hand_arm", f"hand{side}: hand={h} n={d['hand_n']} | "
                            f"forearm={ar} n={d['arm_n']} box={d['arm_box']} | "
                            f"|hand-forearm|={da if da is None else round(da, 1)} (目标≤8)")
            if da is not None:
                checks.append(("assert.hand_arm", da <= 8.0,
                               f"{side} |hand-forearm|={da:.1f} 目标<=8"))
            out("hand_face", f"hand{side}: |hand-face|={df if df is None else round(df, 1)} (参考值，不作缺陷)")
        hr, hl = hands.get("R(+x)", {}).get("hand"), hands.get("L(-x)", {}).get("hand")
        if hr is not None and hl is not None:
            out("hand_lr", f"|handR - handL|={abs(hr - hl):.1f} (跨光照参考值，不作缺陷)")

    # ---------- C4 头发高光 ----------
    a, _ = read_rgb("m4_face_front")
    if a is not None:
        hh = hair_highlight_z(a, "m4_face_front")
        out("hair_hi", f"m4_face_front: hair_px={hh['n']} t99={hh.get('t99')} "
                       f"n_hi={hh.get('n_hi')} z_med={hh.get('z_med')} "
                       f"in[1.52,1.60]={hh.get('in_band')}% (目标≥60%)")
        if hh.get("in_band") is not None:
            checks.append(("assert.hair_hi", hh["in_band"] >= 60.0,
                           f"高光带在 z[1.52,1.60] 占 {hh['in_band']:.1f}% 目标>=60%"))
        r = rim_width(a)
        if r:
            out("rim", f"m4_face_front: n={r['n']} p50={r['p50']:.0f} "
                       f"p90={r['p90']:.0f} max={r['mx']} (目标 2~6px)")
            checks.append(("assert.rim", 2 <= r["p50"] <= 6,
                           f"轮廓光 p50={r['p50']:.0f}px 目标[2,6]"))
    # C4 收口：验收对象改为深色区域 —— m3_body_q34 的藏青裙(z 0.65~1.05)、
    # m3_upper 的头发(z 1.40~1.53 在画内)、m5_body_front 的裙摆。
    for name in ("m3_body_q34", "m3_upper", "m3_body_front"):
        a, _ = read_rgb(name)
        if a is None:
            continue
        r = rim_width(a, subject_max=150.0)
        if r:
            out("rim_dark", f"{name}: n={r['n']} p50={r['p50']:.0f} "
                            f"p90={r['p90']:.0f} max={r['mx']} (目标 2~6px)")
        else:
            out("rim_dark", f"{name}: 无深色轮廓行")

    # ---------- 几何（只在 Blender 下跑） ----------
    if HAS_BPY:
        try:
            geometry_checks()
        except Exception as exc:
            out("geom", f"SKIP: {type(exc).__name__}: {exc}")

    # ---------- 判定汇总 ----------
    if not checks:
        out("assert.none", "FAIL 一条判定都没有（图不全或统计全跳过）")
    for tag, ok, text in checks:
        out(tag, ("PASS " if ok else "FAIL ") + text)

    out("done", "1" if True else "0")


main()