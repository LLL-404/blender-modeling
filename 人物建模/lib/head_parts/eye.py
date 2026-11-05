# -*- coding: utf-8 -*-
"""L2 部件 7/8：眼（phase 3 第二次尝试：换表示法，不叠实体）。

第一次尝试（已回退）在 5 层平面 fan 上叠眼球+眼睑，结果近共面 z-fighting。
根因：所有贴片 `y = y_hit − d_i`，d 只差 0.6~3.8mm。

本次改法（docs/数学模型与灵敏度.md §5.1 的工程落地）
----------------------------------------------------
定义**一张共享曲面** S(x,z)，所有层都在它上面取深度：

    S(x,z) = y_hit(x,z) − LIFT − BULGE·exp(−((x−cx)/w)² − ((z−cz)/h)²)

  · 眼白：S 的前表面 + 后表面(S+BACK_DEPTH) + 侧边封口 = 一个封闭透镜实体，
    不再用平面 fan，也不再单独叠眼球。
  · 虹膜/瞳孔/高光：以 S 为基准各减一个**显式常量** δ（0.5/0.8/1.0mm），
    深度差是设计出来的，不是各层各自 conform 抢出来的。
  · 上/下眼睑：沿 almond 弧的带，前层 S−LID_FRONT、后层 S+LID_THICK，
    四条边封口 = 有厚度的实体壳。
  · 睫毛/下眼缘线稿：同样用 S−δ 定位。

严格球面 S={((x−cx)/R)²+...=1} 与眼窝的 5.2mm 高斯凹陷不兼容
（球冠边缘会退到颅骨后面被吃掉），所以采用「脸面 + 高斯凸冠」的共享曲面：
数学性质一样（单一参数化、显式深度层），且始终贴在眼窝里。

BOSS 决策 A：只做静态实体，不绑眼睑骨/形态键。
"""
import math

import bmesh
import bpy
from mathutils import Vector

from . import _base as B
from meshkit import join

# ---- 共享曲面的深度层（单位 m；所有层互斥，不出现近共面竞争）----
SURFACE_LIFT = 0.0018      # 整张眼面比眼窝前移
BULGE = 0.0012             # 中心额外凸冠（球面感）
BACK_DEPTH = 0.0060        # 眼白实体后表面深度
# 层间深度必须大于「S 的分片线性插值误差」。BULGE=1.2mm 的凸冠用单个
# 三角 fan 近似时误差可达 ~1mm，所以第一版 δ=0.3~1.0mm 会让虹膜局部穿到
# 眼白后面，白模渲成扇形斑块。改成同心环精确采样 S + 把 δ 拉到 1~2.4mm。
IRIS_DELTA = 0.0012
PUPIL_DELTA = 0.0018
HILITE_DELTA = 0.0024
LASH_DELTA = 0.0028
# 眼睑必须整体在眼白（S−0.0002）之前：前层 S−0.0020、后层 S−0.0008。
LID_FRONT = 0.0020
LID_THICK = 0.0012         # 1.2mm，对应合同 gauge lid_thickness ≥ 0.8mm
LID_W = 0.0026             # 眼睑带在 z 方向的宽度

ENABLE_VOLUME = True


def _face_y(bvh, x, z):
    hit = bvh.ray_cast(Vector((x, -0.5, z)), Vector((0, 1, 0)))
    return hit[0].y if hit[0] is not None else -0.061


def _surface(bvh, cx, cz, w, hu, hd):
    """返回共享曲面 S(x,z)。所有部件必须只用这一个函数取 y。"""
    hz = (hu + hd) * 0.60

    def S(x, z):
        bulge = BULGE * B.g((x - cx) / w) * B.g((z - cz) / hz)
        return _face_y(bvh, x, z) - SURFACE_LIFT - bulge

    return S


def surface_for(bvh, side):
    """对外导出：给 `face_detail.py` 的眼周线稿用同一张 S，避免各贴各的。

    返回值是 `(S(x,z), cx, cz, w, hu, hd)`，参数口径与 `make_eye_volume` 完全一致。
    线稿必须调这个而不是自己 conform 到颅骨 BVH —— 颅骨 BVH 比 S 靠后
    1.8~3.0mm，直接贴会在眼周留下细碎白点（v0.19.0 遗留）。
    """
    s = side
    k = B.eye_size()
    cx, cz = B.eye_x() * s, B.sz(1.500)
    w, hu, hd = B.EYE_W * k, B.EYE_HU * k, B.EYE_HD * k
    return _surface(bvh, cx, cz, w, hu, hd), cx, cz, w, hu, hd


def _recalc(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def _eyeball_shell(outline, S, cx, cz, name, mat):
    """封闭透镜实体：前表面 = S 的**同心环精确采样**，后表面 = S + BACK_DEPTH。

    单个三角 fan 近似 S 会有 ~1mm 误差（BULGE 凸冠非线性），
    与虹膜 δ 同量级 → 局部穿插。三环采样把误差压到一个环内。
    """
    n = len(outline)
    verts = [(cx, S(cx, cz) - 0.0002, cz)]
    rings = []
    for t in (0.35, 0.70, 1.0):
        rings.append(len(verts))
        for p in outline:
            x = cx + (p.x - cx) * t
            z = cz + (p.z - cz) * t
            verts.append((x, S(x, z) - 0.0002, z))
    back_c = len(verts)
    verts.append((cx, S(cx, cz) + BACK_DEPTH, cz))
    back_o = len(verts)
    for p in outline:
        verts.append((p.x, S(p.x, p.z) + BACK_DEPTH, p.z))
    r0, r1, r2 = rings
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append((0, r0 + i, r0 + j))
        faces.append((r0 + i, r1 + i, r1 + j, r0 + j))
        faces.append((r1 + i, r2 + i, r2 + j, r1 + j))
        faces.append((back_c, back_o + j, back_o + i))
        faces.append((r2 + i, r2 + j, back_o + j, back_o + i))
    ob = B.mesh_from(verts, faces, name)
    ob.data.materials.append(mat)
    _recalc(ob)
    for poly in ob.data.polygons:
        poly.use_smooth = True
    return ob


def _disc(cx, cz, r, S, delta, name, mat, segs=32):
    """贴在共享曲面 S 上的圆盘（虹膜/瞳孔/高光），δ 是显式深度。

    2026-11-05 试过给圆盘也加同心环精确采样，想消掉白模里的扇形亮斑，
    **实测无效已回退**：斑块的根因不是插值误差，而是虹膜半径
    `w*EYE_IRIS_R ≈ 14.9mm` 大于眼裂下高 `EYE_HD ≈ 10.2mm`，圆盘下缘
    超出 almond 轮廓约 2.2mm，超出部分贴在眼窝上形成一条弧。
    要消掉得做「虹膜被眼睑裁切」（多边形裁剪），属于新的表示法改动，
    不在此轮叠加。见 docs/数学模型与灵敏度.md §5.3。
    """
    pts = B.circle(cx, cz, r, segs)
    verts = [(cx, S(cx, cz) - delta, cz)]
    verts += [(p.x, S(p.x, p.z) - delta, p.z) for p in pts]
    faces = [(0, 1 + i, 1 + (i + 1) % segs) for i in range(segs)]
    ob = B.mesh_from(verts, faces, name)
    ob.data.materials.append(mat)
    for poly in ob.data.polygons:
        poly.use_smooth = True
    return ob


def _lid(arc, S, upper, name, mat):
    """沿 almond 弧的有厚度眼睑壳，四条边全封口。"""
    n = len(arc)
    dz = LID_W if upper else -LID_W
    a, b, a2, b2 = [], [], [], []
    for p in arc:
        x, z = p.x, p.z
        zo = z + dz
        ya = S(x, z) - LID_FRONT
        yb = S(x, zo) - LID_FRONT
        a.append((x, ya, z))
        b.append((x, yb, zo))
        a2.append((x, ya + LID_THICK, z))
        b2.append((x, yb + LID_THICK, zo))
    verts = a + b + a2 + b2           # a=0..n-1, b=n.., a2=2n.., b2=3n..
    faces = []
    for i in range(n - 1):
        j = i + 1
        faces.append((i, j, n + j, n + i))
        faces.append((2 * n + i, 3 * n + i, 3 * n + j, 2 * n + j))
        faces.append((i, 2 * n + i, 2 * n + j, j))
        faces.append((n + i, n + j, 3 * n + j, 3 * n + i))
    faces.append((0, n, 3 * n, 2 * n))
    faces.append((n - 1, 2 * n + n - 1, 3 * n + n - 1, 2 * n - 1))
    ob = B.mesh_from(verts, faces, name)
    ob.data.materials.append(mat)
    _recalc(ob)
    for poly in ob.data.polygons:
        poly.use_smooth = True
    return ob


def _set_band_y(ob, S, delta):
    """把 XZ 平面带的所有顶点按共享曲面定位（不再 conform 到颅骨）。"""
    for v in ob.data.vertices:
        v.co.y = S(v.co.x, v.co.z) - delta
    ob.data.update()
    return ob


def socket_deltas(x, y, z, ex):
    """原 head.py:312-316 的两眼眼窝凹陷。返回 dy 序列，顺序不可改。"""
    dy = []
    z_eye = B.sz(1.500)
    for s in (-1, 1):
        dist2 = ((x - ex * s) / 0.028) ** 2 + ((z - z_eye) / 0.022) ** 2
        if dist2 < 1.0 and y < -0.02:
            dy.append(0.0052 * (1 - dist2) ** 1.1)
    return dy


def make_eye_volume(side, mats, bvh):
    """共享曲面版：所有层用同一个 S(x,z)，深度差为显式常量。"""
    s = side
    k = B.eye_size()
    cx, cz = B.eye_x() * s, B.sz(1.500)
    w, hu, hd = B.EYE_W * k, B.EYE_HU * k, B.EYE_HD * k
    S = _surface(bvh, cx, cz, w, hu, hd)

    outline = [Vector((p.x + cx, 0, p.z + cz))
               for p in B.almond(w, hu, hd, 0.24 * s)]
    parts = [_eyeball_shell(outline, S, cx, cz, "eyeball_%s" % s, mats["sclera"])]

    parts.append(_disc(cx, cz + w * B.EYE_IRIS_DZ, w * B.EYE_IRIS_R, S,
                       IRIS_DELTA, "iris_%s" % s, mats["iris"]))
    parts.append(_disc(cx, cz + w * B.EYE_IRIS_DZ, w * B.EYE_PUPIL_R, S,
                       PUPIL_DELTA, "pupil_%s" % s, mats["pupil"]))
    parts.append(_disc(cx - w * B.EYE_HI1_DX * s, cz + w * B.EYE_HI1_DZ,
                       w * B.EYE_HI1_R, S, HILITE_DELTA, "hi1_%s" % s,
                       mats["white_emit"], 20))
    parts.append(_disc(cx + w * B.EYE_HI2_DX * s, cz - w * B.EYE_HI2_DZ,
                       w * B.EYE_HI2_R, S, HILITE_DELTA, "hi2_%s" % s,
                       mats["white_emit"], 16))

    # 上/下睫毛与下眼缘：线稿层，也用 S 定位
    n = 26
    upper_arc, lower_arc = [], []
    la, lb, low_a, low_b = [], [], [], []
    for i in range(n):
        t = math.pi * i / (n - 1)
        c, sn = math.cos(t), math.sin(t)
        x = cx + w * c
        zu = cz + hu * sn + 0.24 * w * c
        zl = cz - hd * sn + 0.24 * w * c
        th = w * (B.EYE_LASH_TH0 + B.EYE_LASH_TH1 * max(0.0, c * s))
        upper_arc.append(Vector((x, 0, zu)))
        lower_arc.append(Vector((x, 0, zl)))
        la.append(Vector((x, 0, zu + w * B.EYE_LASH_DZ)))
        lb.append(Vector((x - w * B.EYE_LASH_DX * s, 0, zu - th)))
        low_a.append(Vector((x, 0, zl)))
        low_b.append(Vector((x, 0, zl - w * B.EYE_LOW_DZ)))
    parts.append(_set_band_y(B.band(la, lb, "lash_%s" % s, mats["lash"]), S, LASH_DELTA))
    parts.append(_set_band_y(B.band(low_a, low_b, "lowline_%s" % s,
                                    mats["lash_soft"]), S, LASH_DELTA))

    # 眼睑实体（上/下），前层 S−LID_FRONT、后层 +LID_THICK
    parts.append(_lid(upper_arc, S, True, "lid_upper_%s" % s, mats["skin"]))
    parts.append(_lid(lower_arc, S, False, "lid_lower_%s" % s, mats["skin"]))

    return join(parts, name="eye_%s" % s)


def make_eye_flat(side, mats, bvh):
    """拆分前的 5 层平面 fan 实现（保留作回退对照）。"""
    s = side
    k = B.eye_size()
    cx, cz = B.eye_x() * s, B.sz(1.500)
    w, hu, hd = B.EYE_W * k, B.EYE_HU * k, B.EYE_HD * k
    shape = [Vector((p.x + cx, 0, p.z + cz))
             for p in B.almond(w, hu, hd, 0.24 * s)]
    parts = []
    w_ob = B.fan(shape, "sclera_%s" % s, mats["sclera"])
    B.conform(w_ob, bvh, 0.0012)
    parts.append(w_ob)
    iris = B.fan(B.circle(cx, cz + w * B.EYE_IRIS_DZ, w * B.EYE_IRIS_R),
                 "iris_%s" % s, mats["iris"])
    B.conform(iris, bvh, 0.0024)
    parts.append(iris)
    pupil = B.fan(B.circle(cx, cz + w * B.EYE_IRIS_DZ, w * B.EYE_PUPIL_R),
                  "pupil_%s" % s, mats["pupil"])
    B.conform(pupil, bvh, 0.0030)
    parts.append(pupil)
    hi1 = B.fan(B.circle(cx - w * B.EYE_HI1_DX * s, cz + w * B.EYE_HI1_DZ,
                         w * B.EYE_HI1_R, 20), "hi1_%s" % s, mats["white_emit"])
    B.conform(hi1, bvh, 0.0038)
    parts.append(hi1)
    hi2 = B.fan(B.circle(cx + w * B.EYE_HI2_DX * s, cz - w * B.EYE_HI2_DZ,
                         w * B.EYE_HI2_R, 16), "hi2_%s" % s, mats["white_emit"])
    B.conform(hi2, bvh, 0.0038)
    parts.append(hi2)
    n = 26
    a_pts, b_pts, a2, b2 = [], [], [], []
    for i in range(n):
        t = math.pi * i / (n - 1)
        c, sn = math.cos(t), math.sin(t)
        x = cx + w * c
        z = cz + hu * sn + 0.24 * w * c
        th = w * (B.EYE_LASH_TH0 + B.EYE_LASH_TH1 * max(0.0, c * s))
        a_pts.append(Vector((x, 0, z + w * B.EYE_LASH_DZ)))
        b_pts.append(Vector((x - w * B.EYE_LASH_DX * s, 0, z - th)))
        z = cz - hd * sn + 0.24 * w * c
        a2.append(Vector((x, 0, z)))
        b2.append(Vector((x, 0, z - w * B.EYE_LOW_DZ)))
    lash = B.band(a_pts, b_pts, "lash_%s" % s, mats["lash"])
    B.conform(lash, bvh, 0.0034)
    parts.append(lash)
    low = B.band(a2, b2, "lowline_%s" % s, mats["lash_soft"])
    B.conform(low, bvh, 0.0020)
    parts.append(low)
    return join(parts, name="eye_%s" % s)


def make_eye(side, mats, bvh):
    return make_eye_volume(side, mats, bvh) if ENABLE_VOLUME else \
        make_eye_flat(side, mats, bvh)
