# -*- coding: utf-8 -*-
"""头部：环形放样出颅骨与下颌，顶点级雕出眼窝/鼻梁/唇，再把五官贴片投影到真实脸面上。

坐标：Z 上，-Y 是正脸。

2026-11-05 phase 1（L2 拆分）
---------------------------
本文件降级为**门面**：共享数值搬去 `head_parts/_base.py`，八个部件各自的数学
搬去 `head_parts/{skull,jaw,cheek,brow,nose,lips,eye,ear}.py`。这里只负责：

  1. 按原顺序把各部件返回的顶点增量累加（浮点顺序与拆分前完全一致）；
  2. 拼装 Head；
  3. 对外保持原 API（`HEAD` / `sz` / `head_rows` / `CAGE_GROW_X` / `ear` / ...）。

验收：`scripts/head_baseline.py` 的 Head 顶点 hash 必须与拆分前逐位一致。
"""
import math

import charparams
from meshkit import join, shade_smooth

from head_parts import _base as B
from head_parts import (skull, jaw, cheek, brow as brow_mod, nose, lips,
                        eye as eye_mod, ear as ear_mod)

# ---- 共享常量/工具：原样 re-export，外部 `from head import ...` 全部照旧 ----
_DEFAULT_HEAD_ANCHOR = B._DEFAULT_HEAD_ANCHOR
_DEFAULT_HEAD_SCALE = B._DEFAULT_HEAD_SCALE
_DEFAULT_HEAD_SHIFT = B._DEFAULT_HEAD_SHIFT
_DEFAULT_HEAD_TOP = B._DEFAULT_HEAD_TOP
_DEFAULT_HEAD_TO_BODY_RATIO = B._DEFAULT_HEAD_TO_BODY_RATIO
_HEAD_RAW_TOP = B._HEAD_RAW_TOP
_HEAD_RAW_LEN = B._HEAD_RAW_LEN
_head_scale = B._head_scale
_head_shift = B._head_shift
sz = B.sz
sx = B.sx
HEAD_RAW = B.HEAD_RAW
head_rows = B.head_rows
HEAD = B.HEAD
EYE_X = B.EYE_X
EYE_Z = B.EYE_Z
EYE_W = B.EYE_W
EYE_HU = B.EYE_HU
EYE_HD = B.EYE_HD
eye_x = B.eye_x
eye_size = B.eye_size
_DEFAULT_EYE_SPACING_SCALE = B._DEFAULT_EYE_SPACING_SCALE
_DEFAULT_EYE_SIZE_SCALE = B._DEFAULT_EYE_SIZE_SCALE
_DEFAULT_NOSE_DEPTH_SCALE = B._DEFAULT_NOSE_DEPTH_SCALE
_DEFAULT_MOUTH_WIDTH_SCALE = B._DEFAULT_MOUTH_WIDTH_SCALE
_DEFAULT_EAR_SCALE = B._DEFAULT_EAR_SCALE
CAGE_STEP = B.CAGE_STEP
CAGE_SEG = B.CAGE_SEG
CAGE_SUBDIV = B.CAGE_SUBDIV
g = B.g
_band = B._band
make_bvh = B.make_bvh
conform = B.conform
almond = B.almond
fan = B.fan
band = B.band
circle = B.circle

# 细分收缩补偿：probe_cage.py 实测 x 0.98596 / y 0.97735 / z 1.00001 的倒数。
# 故意留在本模块 —— probe_cage 会在运行时改这两个变量再调 head_cage()。
CAGE_GROW_X = 1.01424
CAGE_GROW_Y = 1.02318


def head_cage():
    """稀疏控制笼（实现在 skull 部件，grow 从本模块读）。"""
    return skull.head_cage(CAGE_GROW_X, CAGE_GROW_Y)


def subdivide(ob, levels=CAGE_SUBDIV):
    return skull.subdivide(ob, levels)


# ---------------------------------------------------------------- 控制笼解剖位移
def cage_sculpt(ob):
    """按部件顺序累加控制笼位移，顺序与拆分前一致：jaw/chin → cheek → brow。

    在 314 个控制顶点上移一个点，细分后是整片区域平滑过渡的「转折」；
    在 5186 个细分顶点上做只是局部鼓包。
    """
    me = ob.data
    zs = sorted({round(v.co.z, 5) for v in me.vertices})

    def row(target, tol=0.012):
        best = min(zs, key=lambda q: abs(q - target))
        return best if abs(best - target) <= tol else None

    z_chin = row(sz(1.4040))
    z_jaw = row(sz(1.4400))
    z_cheek = row(sz(1.4720))
    z_brow = row(sz(1.5240))

    for v in me.vertices:
        x, y, z = v.co
        r = math.hypot(x, y)
        if r < 1e-6:
            continue
        zr = round(z, 5)
        da = abs(((math.degrees(math.atan2(y, x)) + 90.0 + 180.0) % 360.0) - 180.0)

        for dx, dy, dz in (jaw.cage_delta(x, y, z, r, da, zr, z_jaw, z_chin),
                           cheek.cage_delta(x, y, z, r, da, zr, z_cheek),
                           brow_mod.cage_delta(x, y, z, r, da, zr, z_brow)):
            v.co.x += dx
            v.co.y += dy
            v.co.z += dz
    me.update()
    print("[cage] 解剖位移：chin=%s jaw=%s cheek=%s brow=%s" % (
        z_chin, z_jaw, z_cheek, z_brow))


def head_base():
    cage = head_cage()
    cage_sculpt(cage)
    return subdivide(cage)


# ---------------------------------------------------------------- 顶点级面部塑形
def sculpt(ob):
    """按部件顺序累加顶点位移，顺序与拆分前一致：

        eye socket → brow → nose → lips → chin → cheek

    每个部件返回增量序列，逐个 `dy += e`；这样浮点加法结合顺序与
    拆分前的单循环完全相同，Head 顶点 hash 才能逐位一致。
    """
    me = ob.data
    ex = eye_x()
    nose_k = charparams.get("appearance.nose_depth_scale", _DEFAULT_NOSE_DEPTH_SCALE)
    mouth_k = charparams.get("appearance.mouth_width_scale", _DEFAULT_MOUTH_WIDTH_SCALE)
    for v in me.vertices:
        x, y, z = v.co
        dy = 0.0
        dz = 0.0
        dx = 0.0

        for e in eye_mod.socket_deltas(x, y, z, ex):
            dy += e
        for e in brow_mod.sculpt_deltas(x, y, z):
            dy += e
        for e in nose.sculpt_deltas(x, y, z, nose_k):
            dy += e
        for e in lips.sculpt_deltas(x, y, z, mouth_k):
            dy += e
        dy_seq, dz_seq = jaw.sculpt_deltas(x, y, z)
        for e in dy_seq:
            dy += e
        for e in dz_seq:
            dz += e
        dy_seq, ddx = cheek.sculpt_deltas(x, y, z)
        for e in dy_seq:
            dy += e
        dx += ddx

        v.co.y += dy
        v.co.z += dz
        v.co.x += dx
    me.update()


# ---------------------------------------------------------------- 部件贴片（对外 API）
def eye(side, mats, bvh):
    return eye_mod.make_eye(side, mats, bvh)


def brow(side, mats, bvh):
    return brow_mod.make_brow(side, mats, bvh)


def mouth(mats, bvh):
    return lips.make_mouth(mats, bvh)


def ear(side, mats):
    return ear_mod.make_ear(side, mats)


# ---------------------------------------------------------------- 拼装
def build(mats):
    h = head_base()
    sculpt(h)
    shade_smooth(h)
    h.data.materials.append(mats["skin"])
    bvh = make_bvh(h)

    parts = [h, mouth(mats, bvh)]
    for s in (-1, 1):
        parts.append(eye(s, mats, bvh))
        parts.append(brow(s, mats, bvh))
        parts.append(ear(s, mats))
    # 线稿独立成 FaceLines，不并入 Head（描边壳会吞掉 0.5~0.8mm 细线）。
    import face_detail
    lines = face_detail.build(mats, bvh)
    head = join(parts, "Head")
    shade_smooth(head)
    if lines:
        join(lines, "FaceLines")
    return head
