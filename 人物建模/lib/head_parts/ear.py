# -*- coding: utf-8 -*-
"""L2 部件 8/8：耳（独立椭球 + 耳轮/耳甲雕形）。"""
import math

import bpy

from . import _base as B

# phase 3：可调参数（默认值与拆分前逐位相同）。
EAR_RY = 0.0190
EAR_RZ = 0.0230
EAR_THICK = 0.0052
RIM_OUT = 0.0028
CONCHA_IN = 0.0042
RIM_CENTER = 0.82
RIM_SIGMA = 0.22
CONCHA_SIGMA = 0.42


def make_ear(side, mats):
    """原 head.py:516-562。

    局部坐标基准：transform_apply 后 v.co 以耳中心为原点，
    ly=v.co.y/ry、lz=v.co.z/rz，r∈[0,1]。不要再减世界坐标（D0 bug）。
    """
    s = side
    k = B.charparams.get("appearance.ear_scale", B._DEFAULT_EAR_SCALE)
    cx, cy, cz = B.sx(0.0935) * s, B.sx(0.010), B.sz(1.492)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, radius=1.0,
                                         location=(cx, cy, cz))
    ob = bpy.context.object
    ob.name = f"ear_{s}"
    ry, rz = EAR_RY * k, EAR_RZ * k
    ob.scale = (EAR_THICK * k, ry, rz)
    ob.rotation_euler = (math.radians(8), 0.0, math.radians(-14 * s))
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    for v in ob.data.vertices:
        ly = v.co.y / ry
        lz = v.co.z / rz
        r = math.hypot(ly, lz)
        rim = math.exp(-((r - RIM_CENTER) / RIM_SIGMA) ** 2)
        concha = math.exp(-(r / CONCHA_SIGMA) ** 2)
        v.co.x += s * (RIM_OUT * rim - CONCHA_IN * concha)
    ob.data.update()
    ob.data.materials.append(mats["skin"])
    bpy.ops.object.shade_smooth()
    return ob
