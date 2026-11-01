# -*- coding: utf-8 -*-
"""A3/A5 几何量测：衬衫净空 / 袖口闭合与半径 / 呆毛粗细 / 裙摆净空。

同一进程内 import body / outfit / hair 现场构建，**不渲染、不写 blend**。
自带材质 stub，刻意不 import look.py —— 同批次有其他生成者正在改 look，
probe 不该被它的中间状态拖挂。

用法（工作目录 人物建模/）：
    "D:/Program Files/Blender Foundation/Blender 5.2/blender.exe" \
        -b --factory-startup --python _stageA/a4_fit_probe.py

口径说明（和 DESIGN.md §5.6 保持一致，别人复测才能对上）：
  · 正面朝 -Y，y 越小越靠前。净空 margin = body_y − cloth_y，正值为安全。
  · 衬衫带位取 DESIGN.md 的三个 z 带：1.10-1.14 / 1.14-1.18 / 1.18-1.22。
  · 中线取 x≈0，另取 x≈±40mm 两处，每带报三处里的**最小值**。
  · 报的是衬衫顶点里最靠前（min y）的那个，即 solidify 后的外表面，与
    rig_probe.py:149-155 完全相同，基线 10.3/10.2/8.5mm 就是这个口径。
"""
import bpy
import bmesh
import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import body as bodymod        # noqa: E402
import hair as hairmod        # noqa: E402
import outfit as outfitmod    # noqa: E402


# ---------------------------------------------------------------- 基础工具

def stub_mats():
    """只满足 outfit/hair 的材质槽需求，避开 look.set_all()。"""
    out = {}
    for key in ("cloth_white", "cloth_navy", "hair"):
        out[key] = bpy.data.materials.new(key)
    return out


def cos_of(ob):
    mw = ob.matrix_world
    return [mw @ v.co for v in ob.data.vertices]


def front_y(cos, lo, hi, xc=0.0, tol=0.004):
    """z 带内、x≈xc 的顶点里最靠前（y 最小）的 y；没有点返回 None。"""
    sel = [c.y for c in cos
           if lo <= c.z <= hi and abs(c.x - xc) <= tol and c.y < 0.0]
    return min(sel) if sel else None


def _mm(v):
    return "-" if v is None else f"{v * 1000.0:+.1f}"


# ---------------------------------------------------------------- 构建

print("[probe] building Body ...")
body = bodymod.build()

print("[probe] building Hair ...")
MATS = stub_mats()
hair = hairmod.build(MATS)

print("[probe] building Outfit ...")
cloth = outfitmod.build(MATS)

bcos = cos_of(body)
ccos = cos_of(cloth)
hcos = cos_of(hair)
print(f"[probe] built: Body verts={len(bcos)} Outfit verts={len(ccos)} "
      f"Hair verts={len(hcos)}")


# ---------------------------------------------------------------- 1. 衬衫净空

X_SAMPLES = ((0.000, 0.004), (-0.040, 0.012), (+0.040, 0.012))
SHIRT_BANDS = ((1.100, 1.140), (1.140, 1.180), (1.180, 1.220))

print("[probe] --- shirt clearance (body_y - shirt_y, min over x=0/±40mm) ---")
for lo, hi in SHIRT_BANDS:
    rows = []
    for xc, tol in X_SAMPLES:
        by = front_y(bcos, lo, hi, xc, tol)
        cy = front_y(ccos, lo, hi, xc, tol)
        rows.append((xc, by, cy, None if (by is None or cy is None) else by - cy))
    bad = [r for r in rows if r[3] is None]
    if bad:
        print(f"[probe] shirt z[{lo:.3f},{hi:.3f}] MISSING samples="
              f"{[(r[0], _mm(r[1]), _mm(r[2])) for r in bad]}")
        continue
    xw, _, _, mw = min(rows, key=lambda r: r[3])
    detail = " ".join(f"x={r[0]*1000:+.0f}:{_mm(r[3])}" for r in rows)
    flag = "OK" if mw >= 0.010 else "FAIL(<10mm)"
    print(f"[probe] shirt z[{lo:.3f},{hi:.3f}] min_margin={_mm(mw)}mm "
          f"at x={xw*1000:+.0f} | {detail} | {flag}")

# 实体网格过 voxel 会收缩，补一条参数面口径的保守值：
# 参数面（TORSO 环 + sculpt_torso，未体素化）与衬衫环层（solidify 之前）比较。
try:
    param = bodymod.torso()
    bodymod.sculpt_torso(param)
    pcos = [v.co.copy() for v in param.data.vertices]
    me = param.data
    bpy.data.objects.remove(param, do_unlink=True)
    bpy.data.meshes.remove(me)
    print("[probe] --- shirt clearance (parametric surface, before solidify) ---")
    for lo, hi in SHIRT_BANDS:
        rows = []
        for xc, tol in X_SAMPLES:
            py = front_y(pcos, lo, hi, xc, tol)
            cy = front_y(ccos, lo, hi, xc, tol)
            rows.append((xc, py, cy, None if (py is None or cy is None) else py - cy))
        rows = [r for r in rows if r[3] is not None]
        if not rows:
            continue
        xw, _, _, mw = min(rows, key=lambda r: r[3])
        print(f"[probe] param z[{lo:.3f},{hi:.3f}] min_margin={_mm(mw)}mm "
              f"at x={xw*1000:+.0f}")
except Exception as exc:  # 参数面只是旁证，失败不拖垮 probe
    print(f"[probe] param-surface clearance skipped: {exc!r}")


# ---------------------------------------------------------------- 2. 袖口

SEG = 40   # 与 outfit._sleeve() 里 tube(seg=40) 一致


def _unit(v):
    ln = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / ln for x in v]


def _sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def _dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def _mean(pts):
    n = len(pts)
    return [sum(p[i] for p in pts) / n for i in range(3)]


def _perp_radius(pts, center, axis):
    """各点到「过 center、方向 axis 的直线」的垂直距离。"""
    out = []
    for p in pts:
        d = _sub(p, center)
        along = _dot(d, axis)
        perp = [d[i] - along * axis[i] for i in range(3)]
        out.append(math.sqrt(sum(x * x for x in perp)))
    return out


def sleeve_mouth(side):
    """重建**未 solidify** 的袖筒，直接取 tube 的末端环。

    为什么不用 Outfit 里的袖子量：袖筒是斜的（轴与 z 夹角 ~28°），任何 z
    切片都会同时截到好几圈，PCA 主轴还会被 62→46mm 的锥度带偏。
    tube 的顶点排列是 ring0..ringN 各 SEG 点 + cap_start/cap_end 两个圆心，
    所以末端环就是 vs[-(SEG+2):-2]，零歧义。
    """
    ob = outfitmod._sleeve(side, solid=False, cuff=False)
    vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
    n = len(vs)
    if n < 2 * SEG + 2:
        print(f"[probe] sleeve {side}: verts={n} 太少，无法取环")
        return None
    ring = vs[-(SEG + 2):-2]
    prev = vs[-(2 * SEG + 2):-(SEG + 2)]
    c_last = _mean([[p.x, p.y, p.z] for p in ring])
    c_prev = _mean([[p.x, p.y, p.z] for p in prev])
    axis = _unit(_sub(c_last, c_prev))
    rad = _perp_radius([[p.x, p.y, p.z] for p in ring], c_last, axis)
    rad.sort()
    me = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me)
    return {"center": c_last, "axis": axis,
            "radius": rad[-1], "radius_med": rad[len(rad) // 2],
            "n": len(rad)}


def upper_arm_radius(bcos, mouth, side=1, xmin=0.135, band=0.005, rmax=0.070):
    """袖口平面上的上臂半径（Body 实测，垂直于**同一袖轴**）。

    只有严格同轴同面才能和袖口半径相减。DESIGN/任务里写的「上臂 45mm」
    是 body.arm() 在 z=1.220 处的参数半径；袖口实际落在上臂下段，
    该处手臂更细（~37.7mm），拿 45mm 去减会把 8mm 算成 15mm。
    xmin/rmax 是为了把躯干和肩部顶点挡在外面——z=1.11 处躯干 rx 已到 0.13。
    """
    axis, rc = mouth["axis"], mouth["center"]
    sel = []
    for c in bcos:
        if c.x * side <= xmin:
            continue
        d = _sub([c.x, c.y, c.z], rc)
        if abs(_dot(d, axis)) > band:
            continue
        perp = _perp_radius([[c.x, c.y, c.z]], rc, axis)[0]
        if perp > rmax:
            continue
        sel.append([c.x, c.y, c.z])
    if len(sel) < 8:
        return None, None
    rad = _perp_radius(sel, rc, axis)
    rad.sort()
    return rad[len(rad) // 2], rad[-1]


def boundary_edges(ob, region=None):
    """返回 (区域内边界边数, 全网格边界边数)。"""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    inner = total = 0
    for e in bm.edges:
        if not e.is_boundary:
            continue
        total += 1
        if region is None or all(region(v.co) for v in e.verts):
            inner += 1
    bm.free()
    return inner, total


MOUTHS = {}
for side, tag in ((1, "R(+x)"), (-1, "L(-x)")):
    mouth = sleeve_mouth(side)
    if mouth is None:
        continue
    MOUTHS[side] = mouth
    ar_med, ar_max = upper_arm_radius(bcos, mouth, side)
    cx, cy, cz = mouth["center"]
    cr = mouth["radius"]
    diff_med = None if ar_med is None else cr - ar_med
    ok = diff_med is not None and 0.007 <= diff_med <= 0.010
    print(f"[probe] cuff {tag}: center=({cx:+.4f},{cy:+.4f},{cz:+.4f}) "
          f"r={cr * 1000:.1f}mm r_med={mouth['radius_med'] * 1000:.1f}mm "
          f"ring_verts={mouth['n']} "
          f"axis=({mouth['axis'][0]:+.2f},{mouth['axis'][1]:+.2f},{mouth['axis'][2]:+.2f})")
    print(f"[probe] cuff {tag}: arm_r@cuff median={_mm(ar_med)}mm "
          f"max={_mm(ar_max)}mm | diff(vs median)={_mm(diff_med)}mm "
          f"| diff(vs 45mm 参数上臂)={(cr - 0.045) * 1000:+.1f}mm "
          f"| {'OK' if ok else 'FAIL(not in [7,10]mm)'}")

region = lambda co: co.z < 1.140 and co.x > 0.130   # 右袖口附近
inner, total = boundary_edges(cloth, region)
print(f"[probe] cuff boundary_edges: region={inner} whole_outfit={total} "
      f"{'OK' if inner == 0 else 'FAIL'}")

# 卷边环：在袖口附近的截面里找「比袖口更大的那一圈」= 卷边外表面
if 1 in MOUTHS:
    m = MOUTHS[1]
    sel = []
    for c in ccos:
        if c.x <= 0.13:
            continue
        d = _sub([c.x, c.y, c.z], m["center"])
        if abs(_dot(d, m["axis"])) <= 0.010:
            sel.append([c.x, c.y, c.z])
    if sel:
        rad = sorted(_perp_radius(sel, m["center"], m["axis"]))
        print(f"[probe] cuff ring: outfit r_max={rad[-1] * 1000:.1f}mm "
              f"(= 卷边外表面; 袖筒 {m['radius'] * 1000:.1f}mm, "
              f"凸出 {(rad[-1] - m['radius']) * 1000:+.1f}mm)")

# ---------------------------------------------------------------- 3. 呆毛

def ahoge_standalone():
    """同一代码路径重建呆毛（未 join），按 seg=10 逐环量 x/y 跨度。

    这是「全宽」的唯一无歧义口径：Hair 合并后按 z 取顶点会把弯曲的两段
    混在一起，量出来是轨迹跨度而不是发束粗细。
    """
    obs = hairmod._ahoge()
    if not obs:
        return None
    ob = obs[0]
    vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
    seg = 10
    # tube() 的 loft 会在两端各追加 1 个 cap 圆心顶点，必须剔掉再按环分组
    n_ring = (len(vs) // seg) * seg
    rings = [vs[i:i + seg] for i in range(0, n_ring, seg)]
    wx = [(max(p.x for p in r) - min(p.x for p in r), r[0].z) for r in rings]
    wy = [(max(p.y for p in r) - min(p.y for p in r), r[0].z) for r in rings]
    zmax = max(p.z for p in vs)
    zmin = min(p.z for p in vs)
    out = (max(wx), max(wy), zmin, zmax, len(vs), len(rings))
    me = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me)
    return out


ah = ahoge_standalone()
if ah is None:
    print("[probe] ahoge: 未构建出来")
else:
    (wx, zx), (wy, zy), zmin, zmax, n, nring = ah
    print(f"[probe] ahoge ring_width: x={wx * 1000:.2f}mm (z={zx:.4f}) "
          f"y(厚)={wy * 1000:.2f}mm | span z[{zmin:.4f},{zmax:.4f}] "
          f"verts={n} rings={nring} "
          f"{'OK' if wx <= 0.008 else 'FAIL(>8mm)'}")

# Hair 中的呆毛：取「z 最高的连通分量」，避免把发帽顶端算进来
def top_component(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    seen = set()
    best, best_z = [], -1e9
    for v in bm.verts:
        if v.index in seen:
            continue
        stack = [v]
        seen.add(v.index)
        comp = []
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for e in cur.link_edges:
                o = e.other_vert(cur)
                if o.index not in seen:
                    seen.add(o.index)
                    stack.append(o)
        zc = max(x.co.z for x in comp)
        if zc > best_z:
            best_z, best = zc, comp
    out = [(ob.matrix_world @ x.co) for x in best]
    bm.free()
    return out, best_z


comp, zc = top_component(hair)
xs = [c.x for c in comp]
ys = [c.y for c in comp]
above = [c for c in comp if c.z > 1.62]
if above:
    ax = [c.x for c in above]
    ay = [c.y for c in above]
    print(f"[probe] ahoge in Hair: z_max={zc:.4f} comp_verts={len(comp)} "
          f"z>1.62 verts={len(above)} x_span={(max(ax) - min(ax)) * 1000:.1f}mm "
          f"y_span={(max(ay) - min(ay)) * 1000:.1f}mm "
          f"(弯曲轨迹跨度，非发束粗细)")
else:
    print(f"[probe] ahoge in Hair: z_max={zc:.4f} comp_verts={len(comp)} "
          f"x_span={(max(xs) - min(xs)) * 1000:.1f}mm "
          f"y_span={(max(ys) - min(ys)) * 1000:.1f}mm")

head_zmax = max(c.z for c in cos_of(bpy.data.objects["Head"])) \
    if "Head" in bpy.data.objects else None
if head_zmax is None:
    import cfg  # noqa: E402
    head_zmax_ref = cfg.HEAD_TOP          # 未建头时用标称头顶 1.620
    ref_tag = "cfg.HEAD_TOP 标称"
else:
    head_zmax_ref = head_zmax
    ref_tag = "Head z_max 实测"
print(f"[probe] ahoge height_above_head: "
      f"{(zc - head_zmax_ref) * 1000:+.1f}mm（参考 {ref_tag} {head_zmax_ref:.4f}）")


# ---------------------------------------------------------------- 4. 裙腰/裙摆净空
#
# 四段与 outfit.assert_skirt_clearance() 的 SKIRT_WAIST_BANDS 一一对应，
# 验收要求 z 0.96~1.06 各段最小 net >= +2mm（正负都打印）。
# 口径：Body 最终网格 vs Outfit 最终网格（含 solidify 外表面），
# 所以比 outfit 内部 [fit] 的环层口径大约 2mm，两者不可混着比。

SKIRT_BANDS = ((0.920, 0.960), (0.960, 1.000),
               (1.000, 1.040), (1.040, 1.060))
print("[probe] --- skirt waist clearance (body_y - skirt_y, min over x) ---")
for lo, hi in SKIRT_BANDS:
    rows = []
    for xc, tol in X_SAMPLES:
        by = front_y(bcos, lo, hi, xc, tol)
        cy = front_y(ccos, lo, hi, xc, tol)
        rows.append((xc, None if (by is None or cy is None) else by - cy))
    rows = [r for r in rows if r[1] is not None]
    if not rows:
        print(f"[probe] skirt z[{lo:.3f},{hi:.3f}] MISSING")
        continue
    xw, mw = min(rows, key=lambda r: r[1])
    detail = " ".join(f"x={r[0]*1000:+.0f}:{_mm(r[1])}" for r in rows)
    flag = "OK" if mw >= 0.002 else "FAIL(<+2mm)"
    print(f"[probe] skirt z[{lo:.3f},{hi:.3f}] min_margin={_mm(mw)}mm "
          f"at x={xw*1000:+.0f} | {detail} | {flag}")

# ---------------------------------------------------------------- 5. 包围盒

def pbox(tag, cos):
    print(f"[probe] {tag}: x[{min(c.x for c in cos):+.4f},"
          f"{max(c.x for c in cos):+.4f}] "
          f"y[{min(c.y for c in cos):+.4f},{max(c.y for c in cos):+.4f}] "
          f"z[{min(c.z for c in cos):+.4f},{max(c.z for c in cos):+.4f}]")


pbox("Body", bcos)
pbox("Outfit", ccos)
pbox("Hair", hcos)
print("[probe] done")