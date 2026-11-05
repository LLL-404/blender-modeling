# -*- coding: utf-8 -*-
"""L2 部件 7/8：眼（眼窝位移 + 眼球/虹膜/睫毛贴片）。

phase 1 保持「平面 fan 贴壳」不变；phase 3 才改成眼球 + 眼睑实体。
"""
import math

import bpy
from mathutils import Vector

from . import _base as B
from meshkit import join, select_only

# phase 3（2026-11-05）：给眼睛补 y 方向体积。
# 拆分前所有五官都是 `y = y_hit − d` 的平面贴片，侧面是贴纸。
# 这里加两样静态实体（BOSS 决策 A：不绑眼睑骨/形态键）：
#   · 眼球：扁椭球，位于眼窝后方，最前点与脸面齐平，不穿出
#   · 上/下眼睑：平面带 conform 到脸面后 Solidify 出厚度
LID_THICK = 0.0012          # 1.2mm，对应合同 gauge lid_thickness ≥ 0.8mm
EYEBALL_DEPTH = 0.0080      # 眼球 y 半径（前后进深）
LID_FRONT_OFFSET = 0.0006

# 2026-11-05 phase 3 第一次尝试：**失败，已停用**。
# 做法：在原有 5 层平面 fan 之上再叠眼球椭球 + 上下眼睑 Solidify 壳。
# 白模 out/clay_face_eye_closeup.png 显示一堆互相穿插的纸片；
# 彩渲 out/m3_face_front.png 眼周出现碎玻璃状白色锯齿。
# 根因（数学）：所有贴片共享同一个 y(x,z) = y_hit(x,z) − d_i，
# d 只差 0.6~3.8mm；再叠一个有厚度的实体，多个近共面曲面在同一 (x,z)
# 上争深度 → z-fighting，描边壳再把这些碎片勾成黑边。
# 正确方向：不能「叠」，要「换表示」——去掉平面 sclera fan，
# 用球面 S = {(x,y,z) | ((x−cx)/R)² + ((y−cy)/R)² + ((z−cz)/R)² = 1}
# 当眼白，把 iris/pupil/高光投到这个球面的 BVH 上；眼睑用球面参数域
# (θ, φ) 的带，不是沿 +Y 射线投到颅骨。这一步留到下一轮，不在这里加补丁。
ENABLE_VOLUME = False


def _face_y(bvh, x, z):
    hit = bvh.ray_cast(Vector((x, -0.5, z)), Vector((0, 1, 0)))
    return hit[0].y if hit[0] is not None else -0.061


def make_eyeball(side, mats, bvh, cx, cz, w, hu, hd):
    """扁椭球眼球：最前点 y = 脸面 y，向后填进眼窝。"""
    yc = _face_y(bvh, cx, cz) + EYEBALL_DEPTH
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=1.0,
                                         location=(cx, yc, cz))
    ob = bpy.context.object
    ob.name = "eyeball_%s" % side
    ob.scale = (w * 1.05, EYEBALL_DEPTH, (hu + hd) * 0.60)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.data.materials.append(mats["sclera"])
    return ob


def make_lid(side, mats, bvh, upper, cx, cz, w, hu, hd):
    """有厚度的上/下眼睑壳：先生成 XZ 平面带 → conform 到脸面 → Solidify。"""
    n = 26
    s = side
    a, b = [], []
    for i in range(n):
        t = math.pi * i / (n - 1)
        c, sn = math.cos(t), math.sin(t)
        x = cx + w * c
        z = cz + (hu * sn if upper else -hd * sn) + 0.24 * w * c
        a.append(Vector((x, 0, z + w * 0.010)))
        b.append(Vector((x, 0, z)))
    tag = "upper" if upper else "lower"
    ob = B.band(a, b, "lid_%s_%s" % (tag, s), mats["skin"])
    B.conform(ob, bvh, LID_FRONT_OFFSET)
    m = ob.modifiers.new("lid_thick", 'SOLIDIFY')
    m.thickness = LID_THICK
    m.offset = 0.0
    select_only(ob)
    bpy.ops.object.modifier_apply(modifier=m.name)
    return ob


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

    # phase 3 静态实体暂时停用（ENABLE_VOLUME=False，原因见模块顶部）。
    # 保留函数是为了不丢掉这次失败的结论；启用前必须先换表示法。
    if ENABLE_VOLUME:
        parts.append(make_eyeball(s, mats, bvh, cx, cz, w, hu, hd))
        parts.append(make_lid(s, mats, bvh, True, cx, cz, w, hu, hd))
        parts.append(make_lid(s, mats, bvh, False, cx, cz, w, hu, hd))

    return join(parts, name=f"eye_{s}")
