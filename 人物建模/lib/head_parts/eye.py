# -*- coding: utf-8 -*-
"""L2 部件 7/8：眼（眼窝位移 + 眼球/虹膜/睫毛贴片）。

phase 1 保持「平面 fan 贴壳」不变；phase 3 才改成眼球 + 眼睑实体。
"""
import math
from mathutils import Vector

from . import _base as B
from meshkit import join


def socket_deltas(x, y, z, ex):
    """原 head.py:312-316 的两眼眼窝凹陷。返回 dy 序列，顺序不可改。"""
    dy = []
    z_eye = B.sz(1.500)
    for s in (-1, 1):
        dist2 = ((x - ex * s) / 0.028) ** 2 + ((z - z_eye) / 0.022) ** 2
        if dist2 < 1.0 and y < -0.02:
            dy.append(0.0052 * (1 - dist2) ** 1.1)
    return dy


def make_eye(side, mats, bvh):
    """原 head.py:412-473。"""
    s = side
    k = B.eye_size()
    cx, cz = B.eye_x() * s, B.sz(1.500)
    w, hu, hd = B.EYE_W * k, B.EYE_HU * k, B.EYE_HD * k
    shape = [Vector((p.x + cx, 0, p.z + cz))
             for p in B.almond(w, hu, hd, 0.24 * s)]
    parts = []
    w_ob = B.fan(shape, f"sclera_{s}", mats["sclera"])
    B.conform(w_ob, bvh, 0.0012)
    parts.append(w_ob)

    # phase 2：虹膜/瞳孔/高光的尺寸随眼宽 w 同比例缩放（w 已含 eye_size_scale k）。
    # 拆分前 w=0.0186 时，下面每个系数都精确还原原来的绝对常量。
    iris = B.fan(B.circle(cx, cz + w * B.EYE_IRIS_DZ, w * B.EYE_IRIS_R),
                 f"iris_{s}", mats["iris"])
    B.conform(iris, bvh, 0.0024)
    parts.append(iris)

    pupil = B.fan(B.circle(cx, cz + w * B.EYE_IRIS_DZ, w * B.EYE_PUPIL_R),
                  f"pupil_{s}", mats["pupil"])
    B.conform(pupil, bvh, 0.0030)
    parts.append(pupil)

    hi1 = B.fan(B.circle(cx - w * B.EYE_HI1_DX * s, cz + w * B.EYE_HI1_DZ,
                         w * B.EYE_HI1_R, 20),
                f"hi1_{s}", mats["white_emit"])
    B.conform(hi1, bvh, 0.0038)
    parts.append(hi1)

    hi2 = B.fan(B.circle(cx + w * B.EYE_HI2_DX * s, cz - w * B.EYE_HI2_DZ,
                         w * B.EYE_HI2_R, 16),
                f"hi2_{s}", mats["white_emit"])
    B.conform(hi2, bvh, 0.0038)
    parts.append(hi2)

    # 上睫毛：外缘抬起、内缘压到眼白上，形成有厚度的上眼睑
    n = 26
    a_pts, b_pts = [], []
    for i in range(n):
        t = math.pi * i / (n - 1)
        c, sn = math.cos(t), math.sin(t)
        x = cx + w * c
        z = cz + hu * sn + 0.24 * w * c
        th = w * (B.EYE_LASH_TH0 + B.EYE_LASH_TH1 * max(0.0, c * s))
        a_pts.append(Vector((x, 0, z + w * B.EYE_LASH_DZ)))
        b_pts.append(Vector((x - w * B.EYE_LASH_DX * s, 0, z - th)))
    lash = B.band(a_pts, b_pts, f"lash_{s}", mats["lash"])
    B.conform(lash, bvh, 0.0034)
    parts.append(lash)

    # 下眼缘细线
    a2, b2 = [], []
    for i in range(n):
        t = math.pi * i / (n - 1)
        c, sn = math.cos(t), math.sin(t)
        x = cx + w * c
        z = cz - hd * sn + 0.24 * w * c
        a2.append(Vector((x, 0, z)))
        b2.append(Vector((x, 0, z - w * B.EYE_LOW_DZ)))
    low = B.band(a2, b2, f"lowline_{s}", mats["lash_soft"])
    B.conform(low, bvh, 0.0020)
    parts.append(low)

    return join(parts, name=f"eye_{s}")
