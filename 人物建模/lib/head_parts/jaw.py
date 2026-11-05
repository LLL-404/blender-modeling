# -*- coding: utf-8 -*-
"""L2 部件 2/8：下颌角 + 下巴。

phase 1：把 cage_sculpt() 与 sculpt() 里属于下颌的位移搬进来，
返回增量而不直接改顶点 —— 门面按原顺序逐个累加，保证浮点结果逐位一致。
"""
from . import _base as B

JAW_INSET = 0.0032
CHIN_FWD_CAGE = 0.0045
CHIN_DOWN_CAGE = 0.0020
CHIN_FWD = 0.0060
CHIN_DOWN = 0.0015


def cage_delta(x, y, z, r, da, zr, z_jaw, z_chin):
    """原 head.py:252-262。返回 (dx, dy, dz)。"""
    dx = dy = dz = 0.0
    if zr == z_jaw and B._band(da, 52.0, 98.0) > 0.0:
        k = JAW_INSET * B._band(da, 52.0, 98.0)
        dx -= k * x / r
        dy -= k * y / r
    if zr == z_chin and B._band(da, 0.0, 38.0, soft=14.0) > 0.0:
        k = B._band(da, 0.0, 38.0, soft=14.0)
        dy -= CHIN_FWD_CAGE * k
        dz -= CHIN_DOWN_CAGE * k
    return dx, dy, dz


def sculpt_deltas(x, y, z):
    """原 head.py:342-346。返回 (dy 序列, dz 序列)；顺序不可改。"""
    if y < 0.0:
        c = B.g(x / 0.0200) * B.g((z - B.sz(1.3990)) / 0.0125)
        return [-CHIN_FWD * c], [-CHIN_DOWN * c]
    return [], []
