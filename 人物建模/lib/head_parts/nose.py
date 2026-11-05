# -*- coding: utf-8 -*-
"""L2 部件 5/8：鼻（鼻梁/鼻尖/鼻翼/鼻底，壳上高斯位移）。"""
from . import _base as B


def sculpt_deltas(x, y, z, nose_k):
    """原 head.py:322-332。4 个 dy 增量的顺序不可改。

    nose_k = appearance.nose_depth_scale（默认 1.0）。
    """
    dy = []
    if y < -0.02:
        z_bridge = B.sz(1.4930)
        z_tip = B.sz(1.4560)
        z_wing = B.sz(1.4520)
        z_base = B.sz(1.4460)
        dy.append(-0.0060 * B.g(x / 0.0090) * B.g((z - z_bridge) / 0.0240))
        dy.append(-0.0125 * nose_k * B.g(x / 0.0082) * B.g((z - z_tip) / 0.0085))
        dy.append(-0.0038 * B.g((abs(x) - 0.0090) / 0.0040) * B.g((z - z_wing) / 0.0052))
        dy.append(0.0030 * B.g(x / 0.0084) * B.g((z - z_base) / 0.0032))
    return dy
