# -*- coding: utf-8 -*-
"""L2 部件 5/8：鼻（鼻梁/鼻尖/鼻翼/鼻底，壳上高斯位移）。"""
from . import _base as B

# phase 3：把字面量提升为可调参数（默认值与拆分前逐位相同），供
# scripts/sensitivity.py 做 ±10% 雅可比扫描。
BRIDGE_H = 0.0060
TIP_FWD = 0.0125
WING_OUT = 0.0038
BASE_INDENT = 0.0030
SIGMA_BRIDGE_X = 0.0090
SIGMA_BRIDGE_Z = 0.0240
SIGMA_TIP_X = 0.0082
SIGMA_TIP_Z = 0.0085
SIGMA_WING = 0.0040
SIGMA_WING_Z = 0.0052
SIGMA_BASE_X = 0.0084
SIGMA_BASE_Z = 0.0032


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
        dy.append(-BRIDGE_H * B.g(x / SIGMA_BRIDGE_X) * B.g((z - z_bridge) / SIGMA_BRIDGE_Z))
        dy.append(-TIP_FWD * nose_k * B.g(x / SIGMA_TIP_X) * B.g((z - z_tip) / SIGMA_TIP_Z))
        dy.append(-WING_OUT * B.g((abs(x) - SIGMA_BRIDGE_X) / SIGMA_WING)
                  * B.g((z - z_wing) / SIGMA_WING_Z))
        dy.append(BASE_INDENT * B.g(x / SIGMA_BASE_X) * B.g((z - z_base) / SIGMA_BASE_Z))
    return dy
