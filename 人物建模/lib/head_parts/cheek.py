# -*- coding: utf-8 -*-
"""L2 部件 3/8：颧骨。"""
from . import _base as B

CHEEK_OUT_CAGE = 0.0022
CHEEK_FWD = 0.0030
CHEEK_DX = 0.0016


def cage_delta(x, y, z, r, da, zr, z_cheek):
    """原 head.py:264-268。"""
    dx = dy = dz = 0.0
    if zr == z_cheek and B._band(da, 28.0, 76.0) > 0.0:
        k = CHEEK_OUT_CAGE * B._band(da, 28.0, 76.0)
        dx += k * x / r
        dy += k * y / r
    return dx, dy, dz


def sculpt_deltas(x, y, z):
    """原 head.py:348-352。返回 (dy 序列, dx)；颧骨会横向外扩。"""
    if y < 0.02:
        ch = B.g((abs(x) - B.sx(0.0680)) / B.sx(0.0160)) * B.g((z - B.sz(1.4720)) / 0.0140)
        ddx = CHEEK_DX * ch if x > 0 else (-CHEEK_DX * ch if x < 0 else 0.0)
        return [-CHEEK_FWD * ch], ddx
    return [], 0.0
