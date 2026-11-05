# -*- coding: utf-8 -*-
"""L2 部件 6/8：嘴唇（壳上高斯位移）+ 唇线贴片。"""
import math
from mathutils import Vector

from . import _base as B


def sculpt_deltas(x, y, z, mouth_k):
    """原 head.py:334-340。3 个 dy 增量的顺序不可改。

    mouth_k = appearance.mouth_width_scale（默认 1.0）。
    """
    dy = []
    if y < -0.02:
        # phase 2：嘴半宽随头骨宽缩放（MOUTH_HALF_W），唇厚仍是 mm（雕刻深度）。
        mw = B.MOUTH_HALF_W * mouth_k
        z_up = B.sz(1.4322)
        z_dn = B.sz(1.4228)
        z_line = B.sz(1.4278)
        dy.append(-0.0040 * B.g(x / mw) * B.g((z - z_up) / 0.0048))
        dy.append(-0.0052 * B.g(x / (mw * 0.95)) * B.g((z - z_dn) / 0.0040))
        dy.append(0.0016 * B.g(x / mw) * B.g((z - z_line) / 0.0016))
    return dy


def make_mouth(mats, bvh):
    """原 head.py:497-513。"""
    z0 = B.sz(1.4305)
    k = B.charparams.get("appearance.mouth_width_scale", B._DEFAULT_MOUTH_WIDTH_SCALE)
    a, b = [], []
    n = 18
    for i in range(n):
        t = i / (n - 1)
        x = (-B.MOUTH_HALF_W + 2.0 * B.MOUTH_HALF_W * t) * k
        z = z0 - 0.0013 * math.sin(math.pi * t)
        a.append(Vector((x, 0, z)))
        b.append(Vector((x, 0, z - 0.0018 - 0.0016 * math.sin(math.pi * t))))
    ob = B.band(a, b, "mouth", mats["lip"])
    B.conform(ob, bvh, 0.0018)
    return ob
