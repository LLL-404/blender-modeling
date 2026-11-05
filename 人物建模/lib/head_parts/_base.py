# -*- coding: utf-8 -*-
"""头部 L2 拆分的共享层：常量、坐标映射、几何工具。

phase 1（2026-11-05）：把 `lib/head.py` 里被所有部件共用的东西挪到这里，
数值一字未改。`head.py` 保持门面，外部 `from head import HEAD/sz/...` 全部照旧。

CAGE_GROW_X / CAGE_GROW_Y 故意**不放在这里**：`scripts/probe_cage.py` 会在运行时
改 `head.CAGE_GROW_X` 再调 `head.head_cage()`，状态必须留在门面里。
"""
import math

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import cfg
import charparams
from meshkit import (superellipse_ring, loft, resample, join, shade_smooth,
                     mesh_from, select_only)

# ---------------- 头身比缩放基准（原 head.py:29-35）----------------
_DEFAULT_HEAD_ANCHOR = 1.3836
_DEFAULT_HEAD_SCALE = 1.063
_DEFAULT_HEAD_SHIFT = -0.0127672
_DEFAULT_HEAD_TOP = 1.62
_DEFAULT_HEAD_TO_BODY_RATIO = 6.505
_HEAD_RAW_TOP = 1.618
_HEAD_RAW_LEN = _HEAD_RAW_TOP - _DEFAULT_HEAD_ANCHOR      # 0.2344


def _head_scale():
    """头骨放大倍数。默认 profile 下**精确等于 1.063**（不走公式反算）。"""
    h = charparams.get("appearance.height", _DEFAULT_HEAD_TOP)
    r = charparams.get("appearance.head_to_body_ratio", _DEFAULT_HEAD_TO_BODY_RATIO)
    if h == _DEFAULT_HEAD_TOP and r == _DEFAULT_HEAD_TO_BODY_RATIO:
        return _DEFAULT_HEAD_SCALE
    if not (0.5 < r < 20.0) or not (h > 0.5):
        return _DEFAULT_HEAD_SCALE
    return max(0.6, min(1.6, (h / r) / _HEAD_RAW_LEN))


def _head_shift():
    """头部整体 z 平移：默认 = −0.0127672；height 或头身比变了则让头顶恰好落在 height。"""
    h = charparams.get("appearance.height", _DEFAULT_HEAD_TOP)
    r = charparams.get("appearance.head_to_body_ratio", _DEFAULT_HEAD_TO_BODY_RATIO)
    if h == _DEFAULT_HEAD_TOP and r == _DEFAULT_HEAD_TO_BODY_RATIO:
        return _DEFAULT_HEAD_SHIFT
    return h - (_DEFAULT_HEAD_ANCHOR + _HEAD_RAW_LEN * _head_scale())


def sz(z):
    """A6 之前的绝对 z → 放大后头骨上的 z。

    `look.py` 里有一份完全相同的副本（不能互相 import），改这里必须同步那边。
    """
    return (_DEFAULT_HEAD_ANCHOR + (z - _DEFAULT_HEAD_ANCHOR) * _head_scale()
            + _head_shift())


def sx(v):
    """x/y 方向的长度、半径、中线偏移同比放大。"""
    return v * _head_scale()


# ---------------- 头骨截面表（原 head.py:81-121）----------------
HEAD_RAW = [
    (1.384, 0.011, 0.048, 0.020, -0.010, 2.00),
    (1.392, 0.022, 0.057, 0.030, -0.008, 2.00),
    (1.402, 0.035, 0.060, 0.046, -0.006, 2.00),
    (1.414, 0.047, 0.061, 0.058, -0.004, 2.05),
    (1.428, 0.059, 0.061, 0.073, -0.002, 2.05),
    (1.444, 0.072, 0.061, 0.083, 0.000, 2.10),
    (1.460, 0.083, 0.061, 0.091, 0.000, 2.10),
    (1.472, 0.089, 0.061, 0.097, 0.000, 2.10),
    (1.490, 0.095, 0.061, 0.102, 0.000, 2.10),
    (1.508, 0.097, 0.061, 0.104, 0.000, 2.10),
    (1.528, 0.097, 0.060, 0.102, 0.000, 2.10),
    (1.548, 0.095, 0.058, 0.098, 0.000, 2.10),
    (1.568, 0.090, 0.054, 0.090, 0.000, 2.10),
    (1.586, 0.082, 0.048, 0.080, 0.000, 2.05),
    (1.600, 0.070, 0.040, 0.068, 0.000, 2.00),
    (1.611, 0.052, 0.029, 0.052, 0.000, 2.00),
    (1.618, 0.028, 0.016, 0.030, 0.000, 2.00),
]


def head_rows():
    """放大后的头骨截面表（外观旋钮在此生效）。"""
    w = charparams.get("appearance.head_width_scale", 1.0)
    f = charparams.get("appearance.face_width_scale", 1.0)
    return [(sz(z), sx(rx) * w, sx(ryf) * f, sx(ryb) * f, sx(cy) * w, p)
            for z, rx, ryf, ryb, cy, p in HEAD_RAW]


HEAD = head_rows()

# ---------------- 眼：绝对常量（原 head.py:123-149）----------------
_DEFAULT_EYE_SPACING_SCALE = 1.0
_DEFAULT_EYE_SIZE_SCALE = 1.0
_DEFAULT_NOSE_DEPTH_SCALE = 1.0
_DEFAULT_MOUTH_WIDTH_SCALE = 1.0
_DEFAULT_EAR_SCALE = 1.0

# ---- phase 2（2026-11-05）：尺寸参数归一化 ----
# 头按 6.5 头身放大到 0.2583m 后，五官仍是按旧头（0.2161m）写的绝对常量，
# 相对缩小 15%，眼距比 1.177 直接 FAIL。所有横向尺寸改为「占名义头骨宽的比例」，
# 换头身比时自动跟随；只有 y 向雕刻深度保留 mm。
def head_unit():
    """名义头骨宽（解析量，不含耳/颧骨外扩）：2 × max(rx of head_rows())。"""
    return 2.0 * max(r[1] for r in head_rows())


_U = head_unit()

# 眼中心位置按 BOSS 2026-11-05 决策保持绝对不动（不随头缩放）。
# 这是合同里唯一保留绝对值的尺寸参数：眼距比修复只靠放大眼宽，不内移眼中心。
# 注意：将来再换头身比时需同步重算下面的眼宽系数，否则眼距比会再漂。
EYE_X = 0.0405
EYE_Z = sz(1.500)
# 眼宽系数 0.098070（半宽）对应全宽/头宽 0.19614，比原来的 0.17390 放大 12.8%：
#   (2×0.189326 − 0.19614) / 0.19614 = 0.930 → 内眼角/眼宽 落进 0.85~1.00
EYE_W = 0.098070 * _U
EYE_HU = 0.079089 * _U       # 眼高同比放大，保持眼裂高宽比 0.645
EYE_HD = 0.047453 * _U
# 嘴半宽：目标 12.6% 头宽（旧设计比例），当前 10.69%
MOUTH_HALF_W = 0.063000 * _U

# 眼内容随眼宽同比例缩放的基准（原 EYE_W 绝对值 0.0186 时的各常量 ÷ 0.0186）
EYE_IRIS_R = 0.709677
EYE_PUPIL_R = 0.322581
EYE_IRIS_DZ = 0.118280
EYE_HI1_DX = 0.258065
EYE_HI1_DZ = 0.483871
EYE_HI1_R = 0.215054
EYE_HI2_DX = 0.236559
EYE_HI2_DZ = 0.333333
EYE_HI2_R = 0.107527
EYE_LASH_DZ = 0.086022
EYE_LASH_DX = 0.048387
EYE_LASH_TH0 = 0.107527
EYE_LASH_TH1 = 0.333333
EYE_LOW_DZ = 0.048387


def eye_x():
    return EYE_X * charparams.get("appearance.eye_spacing_scale", _DEFAULT_EYE_SPACING_SCALE)


def eye_size():
    return charparams.get("appearance.eye_size_scale", _DEFAULT_EYE_SIZE_SCALE)


# ---------------- 控制笼常量（原 head.py:170-172）----------------
CAGE_STEP = 0.018
CAGE_SEG = 24
CAGE_SUBDIV = 2

# ---------------- 数学与几何工具（原 head.py:204-211, 285-286, 361-409）----------------
def g(d, s=1.0):
    return math.exp(-(d * d) / (s * s))


def _band(t, lo, hi, soft=12.0):
    """[lo,hi] 内为 1，两侧各 soft 度内 smoothstep 衰减到 0。"""
    if t < lo - soft or t > hi + soft:
        return 0.0
    if lo <= t <= hi:
        return 1.0
    u = (t - (lo - soft)) / soft if t < lo else ((hi + soft) - t) / soft
    return u * u * (3.0 - 2.0 * u)


def make_bvh(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bvh = BVHTree.FromBMesh(bm)
    bm.free()
    return bvh


def conform(ob, bvh, depth=0.0015):
    for v in ob.data.vertices:
        hit = bvh.ray_cast(Vector((v.co.x, -0.5, v.co.z)), Vector((0, 1, 0)))
        if hit[0] is not None:
            v.co.y = hit[0].y - depth
    ob.data.update()


def almond(w, hu, hd, tilt, n=48):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        z = (hu if s >= 0 else hd) * s
        pts.append(Vector((w * c, 0.0, z + tilt * w * c)))
    return pts


def fan(pts, name, mat):
    n = len(pts)
    cx = sum(p.x for p in pts) / n
    cz = sum(p.z for p in pts) / n
    verts = [(cx, 0.0, cz)] + [(p.x, 0.0, p.z) for p in pts]
    faces = [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)]
    ob = mesh_from(verts, faces, name)
    ob.data.materials.append(mat)
    return ob


def band(a, b, name, mat):
    n = len(a)
    verts = [(p.x, 0.0, p.z) for p in a] + [(p.x, 0.0, p.z) for p in b]
    faces = [(i, i + 1, n + i + 1, n + i) for i in range(n - 1)]
    ob = mesh_from(verts, faces, name)
    ob.data.materials.append(mat)
    return ob


def circle(cx, cz, r, segs=32):
    return [Vector((cx + r * math.cos(2 * math.pi * i / segs), 0.0,
                    cz + r * math.sin(2 * math.pi * i / segs))) for i in range(segs)]
