# -*- coding: utf-8 -*-
"""L2 部件 4/8：眉弓（壳上位移）+ 眉毛贴片。"""
import math
from mathutils import Vector

from . import _base as B


def cage_delta(x, y, z, r, da, zr, z_brow):
    """原 head.py:270-272。"""
    dx = dy = dz = 0.0
    if zr == z_brow and B._band(da, 0.0, 46.0, soft=16.0) > 0.0:
        dy -= 0.0016 * B._band(da, 0.0, 46.0, soft=16.0)
    return dx, dy, dz


def sculpt_deltas(x, y, z):
    """原 head.py:318-320。"""
    if y < -0.02:
        return [-0.0034 * B.g(x / 0.048) * B.g((z - B.sz(1.5275)) / 0.0110)]
    return []


def make_brow(side, mats, bvh):
    """原 head.py:476-494。"""
    s = side
    cx = B.eye_x() * s
    z0 = B.sz(1.5300)
    # phase 2：眉毛横向跨度随眼宽缩放，否则眼放大后眉毛显得短。
    bw = B.EYE_W
    a, b = [], []
    n = 22
    for i in range(n):
        t = i / (n - 1)
        x = cx + (-1.290323 * bw + 2.688172 * bw * t) * s
        z = z0 + 0.0055 * math.sin(math.pi * t) - 0.0070 * t
        th = (0.0012 + 0.0023 * math.sin(math.pi * (t ** 0.75))) * (1.0 - 0.45 * t)
        a.append(Vector((x, 0, z)))
        b.append(Vector((x, 0, z + th)))
    ob = B.band(a, b, f"brow_{s}", mats["brow"])
    B.conform(ob, bvh, 0.0016)
    return ob
