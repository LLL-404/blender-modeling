# -*- coding: utf-8 -*-
"""头部：环形放样出颅骨与下颌，顶点级雕出眼窝/鼻梁/唇，再把五官贴片投影到真实脸面上。
坐标：Z 上，-Y 是正脸。"""
import bpy
import bmesh
import math
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import cfg
import charparams
from meshkit import (superellipse_ring, loft, resample, join, shade_smooth,
                     mesh_from)


# ---------------- A6：头身比 6.95 → 6.50 ----------------
# 整张 HEAD 表绕颈根锚点 z=1.3836 统一放大 HEAD_SCALE=1.063（rx/ry/cy 同比），
# 再整体沿 z 平移 HEAD_SHIFT，使头顶落回 cfg.HEAD_TOP(=1.620)。
#
# 为什么必须带这个平移：纯缩放会把头顶从 1.6180 推到 1.6327，而脚底在 A4
# 之后对齐 z=0，身高就成了 1.6327，超出「1.620±5mm」。头长 / 头身比 / 身高
# 三项验收只有一组解：头顶 1.620、几何下巴 ≈1.3712（头长 0.2487）。
# HEAD_SHIFT 就是这个解与「绕 1.3836 只缩放」之间的差：
#   HEAD_SHIFT = 1.6200 - (1.3836 + (1.6180 - 1.3836) * 1.063) = -0.0127672
#
# ---- 外观旋钮（appearance.height / head_to_body_ratio）----
# 下面四个是**引入旋钮前的字面量**，也是 params/profile.json 缺失时的默认值。
# sz() / sx() 每次调用现读：同一进程里换 params/profile.json（reload 后）也立刻生效。
_DEFAULT_HEAD_ANCHOR = 1.3836
_DEFAULT_HEAD_SCALE = 1.063
_DEFAULT_HEAD_SHIFT = -0.0127672
_DEFAULT_HEAD_TOP = 1.62
_DEFAULT_HEAD_TO_BODY_RATIO = 6.505      # A 阶段实测（a2 快照 6.505）
_HEAD_RAW_TOP = 1.618
_HEAD_RAW_LEN = _HEAD_RAW_TOP - _DEFAULT_HEAD_ANCHOR      # 0.2344


def _head_scale():
    """头骨放大倍数。默认 profile 下**精确等于 1.063**（不走公式反算）。

    为什么默认要短路：head_to_body_ratio 的现值 6.505 是从
    1.620/(0.2344×1.063) 反算出来的，直接代回公式得 1.06295...，
    乘回表会与现网几何差 0.05%，破坏「默认值逐位一致」这条验收。
    """
    h = charparams.get("appearance.height", _DEFAULT_HEAD_TOP)
    r = charparams.get("appearance.head_to_body_ratio", _DEFAULT_HEAD_TO_BODY_RATIO)
    if h == _DEFAULT_HEAD_TOP and r == _DEFAULT_HEAD_TO_BODY_RATIO:
        return _DEFAULT_HEAD_SCALE
    if not (0.5 < r < 20.0) or not (h > 0.5):
        return _DEFAULT_HEAD_SCALE
    return max(0.6, min(1.6, (h / r) / _HEAD_RAW_LEN))


def _head_shift():
    """头部整体 z 平移：默认 = −0.0127672；height 或头身比变了则让头顶恰好落在 height。"""
    h = charparams.get("appearance.height", _DEFAULT_HEAD_TOP)
    r = charparams.get("appearance.head_to_body_ratio", _DEFAULT_HEAD_TO_BODY_RATIO)
    if h == _DEFAULT_HEAD_TOP and r == _DEFAULT_HEAD_TO_BODY_RATIO:
        return _DEFAULT_HEAD_SHIFT
    return h - (_DEFAULT_HEAD_ANCHOR + _HEAD_RAW_LEN * _head_scale())


def sz(z):
    """A6 之前的绝对 z → 放大后头骨上的 z。

    头部所有「面部绝对 z 常量」（EYE_Z、brow/mouth/ear 的 z、sculpt 里的
    鼻/唇/下巴/颧骨 z、look.flatten_face 的 z0/z1）都必须过这个函数，
    否则五官会相对头骨错位。look.py 里有一份完全相同的副本（不能互相
    import），改这里必须同步那边。
    """
    return (_DEFAULT_HEAD_ANCHOR + (z - _DEFAULT_HEAD_ANCHOR) * _head_scale()
            + _head_shift())


def sx(v):
    """x/y 方向的长度、半径、中线偏移同比放大 1.063。"""
    return v * _head_scale()


# 原始表（A6 之前的调形结果）。实际建面用下面的 HEAD。
HEAD_RAW = [
    # z,     rx,    ry前,  ry后,  cy,    power
    # 2026-11-03：下颌段（1.384~1.444）rx 各收窄 12%~21%，对齐参考图的尖下巴。
    # 1.472 以上一个数没动 —— head_width 取的是 1.508 处的最宽值，不会跟着变，
    # 所以头宽/头长、头身比这些既有判据不受影响。
    (1.384, 0.011, 0.048, 0.020, -0.010, 2.00),
    (1.392, 0.022, 0.057, 0.030, -0.008, 2.00),
    (1.402, 0.035, 0.060, 0.046, -0.006, 2.00),
    (1.414, 0.047, 0.061, 0.058, -0.004, 2.05),
    (1.428, 0.059, 0.061, 0.073, -0.002, 2.05),
    (1.444, 0.072, 0.061, 0.083, 0.000, 2.10),
    (1.460, 0.083, 0.061, 0.091, 0.000, 2.10),
    (1.472, 0.089, 0.061, 0.097, 0.000, 2.10),
    (1.490, 0.095, 0.061, 0.102, 0.000, 2.10),
    (1.508, 0.097, 0.061, 0.104, 0.000, 2.10),
    (1.528, 0.097, 0.060, 0.102, 0.000, 2.10),
    (1.548, 0.095, 0.058, 0.098, 0.000, 2.10),
    (1.568, 0.090, 0.054, 0.090, 0.000, 2.10),
    (1.586, 0.082, 0.048, 0.080, 0.000, 2.05),
    (1.600, 0.070, 0.040, 0.068, 0.000, 2.00),
    (1.611, 0.052, 0.029, 0.052, 0.000, 2.00),
    (1.618, 0.028, 0.016, 0.030, 0.000, 2.00),
]

# hair.py 的 _cap() 直接 `from head import HEAD`，所以发帽会自动跟随这次放大。
# 注意：HEAD 是 **import 时**定型的快照（供外部引用），需要「随 profile 现读」
# 的调用点请用 head_rows()。
def head_rows():
    """放大后的头骨截面表（外观旋钮在此生效）。

    head_width_scale 乘 rx / cy（横向宽度与中线偏移），
    face_width_scale 乘 ryf / ryb（前后进深）。默认 1.0 时 ×1.0 是精确运算，
    结果与引入旋钮前的 HEAD 表逐位相同。
    """
    w = charparams.get("appearance.head_width_scale", 1.0)
    f = charparams.get("appearance.face_width_scale", 1.0)
    return [(sz(z), sx(rx) * w, sx(ryf) * f, sx(ryb) * f, sx(cy) * w, p)
            for z, rx, ryf, ryb, cy, p in HEAD_RAW]


HEAD = head_rows()

# 眼：EYE_X / EYE_W 一个数都不要动 —— 内眼角间距/眼宽实测 0.95，
# 已在 0.85~1.00 目标带内（DESIGN 4.2 的「眼距定义陷阱」）。
# 外观旋钮：eye_spacing_scale / eye_size_scale（默认 1.0，走精确 ×1.0）。
_DEFAULT_EYE_SPACING_SCALE = 1.0
_DEFAULT_EYE_SIZE_SCALE = 1.0
_DEFAULT_NOSE_DEPTH_SCALE = 1.0
_DEFAULT_MOUTH_WIDTH_SCALE = 1.0
_DEFAULT_EAR_SCALE = 1.0

EYE_X = 0.0405
EYE_Z = sz(1.500)
# 2026-11-03 按参考图收窄：原 0.0208/0.0188/0.0110 的眼裂 41.6×29.8mm（高宽比
# 1.40），而参考图量到的是 77px×35px（以发顶→下巴 585px 为 1 单位）= 0.132/0.060，
# 高宽比 2.2 —— 细长猫眼而不是圆眼。这里取中间值，先不一次压到参考的极限。
EYE_W = 0.0186
EYE_HU = 0.0150
EYE_HD = 0.0090


def eye_x():
    """眼中心 x（含 eye_spacing_scale）。调用时现读 profile。"""
    return EYE_X * charparams.get("appearance.eye_spacing_scale", _DEFAULT_EYE_SPACING_SCALE)


def eye_size():
    """眼型等比乘子（eye_size_scale）。"""
    return charparams.get("appearance.eye_size_scale", _DEFAULT_EYE_SIZE_SCALE)


def head_base():
    rows = resample(head_rows(), "z", 0.004)
    rings = [superellipse_ring(z, rx, ryf, cy, 0.0, p, cfg.RING_SEG, ry_back=ryb)
             for z, rx, ryf, ryb, cy, p in rows]
    return loft(rings, name="head")


def g(d, s=1.0):
    return math.exp(-(d * d) / (s * s))


def sculpt(ob):
    """顶点级面部塑形。所有 z 位置都过 sz()，与放大后的头骨对齐。"""
    me = ob.data
    z_brow = sz(1.5275)
    z_nose_bridge = sz(1.4930)
    z_nose_tip = sz(1.4560)
    z_nose_wing = sz(1.4520)
    z_nose_base = sz(1.4460)
    z_up_lip = sz(1.4322)
    z_dn_lip = sz(1.4228)
    z_lip_line = sz(1.4278)
    z_chin = sz(1.3990)
    z_cheek = sz(1.4720)
    z_eye = sz(1.500)            # 与 eye() 的 cz 同源；height 变了也一致
    # 外观旋钮（默认 1.0 = 引入旋钮前的字面量；在函数体内现读）
    ex = eye_x()
    nose_k = charparams.get("appearance.nose_depth_scale", _DEFAULT_NOSE_DEPTH_SCALE)
    mouth_k = charparams.get("appearance.mouth_width_scale", _DEFAULT_MOUTH_WIDTH_SCALE)
    for v in me.vertices:
        x, y, z = v.co
        dy = 0.0
        dz = 0.0

        # 眼窝：浅凹，给眼睛留层次
        for s in (-1, 1):
            dist2 = ((x - ex * s) / 0.028) ** 2 + ((z - z_eye) / 0.022) ** 2
            if dist2 < 1.0 and y < -0.02:
                dy += 0.0052 * (1 - dist2) ** 1.1

        # 眉弓：眼上方一小道前突
        if y < -0.02:
            dy -= 0.0034 * g(x / 0.048) * g((z - z_brow) / 0.0110)

        # 鼻梁（窄）→ 鼻头：原神式小鼻，侧面也只是一个圆钝的坡
        if y < -0.02:
            dy -= 0.0060 * g(x / 0.0090) * g((z - z_nose_bridge) / 0.0240)
            # 鼻尖推量 0.0105 → 0.0125：实测前伸 7.70mm，+2mm 后落在 9.7mm。
            # 上限 0.0125 就是天花板 —— 再加深就从「二次元小鼻」变鹰钩。
            # 外观旋钮 nose_depth_scale 乘在这个推量上（默认 1.0）。
            dy -= 0.0125 * nose_k * g(x / 0.0082) * g((z - z_nose_tip) / 0.0085)
            # 鼻翼
            dy -= 0.0038 * g((abs(x) - 0.0090) / 0.0040) * g((z - z_nose_wing) / 0.0052)
            # 鼻底内收，做出一道阴影
            dy += 0.0030 * g(x / 0.0084) * g((z - z_nose_base) / 0.0032)

        # 唇：上唇薄、下唇厚，中间一道唇线
        # A2：原来上唇 4.8mm > 下唇 4.4mm 是反的。现在上唇 4.0mm、下唇 5.2mm，
        # 唇的 x 半宽同步收到 12mm（对应 24mm 全宽，与 mouth() 贴片一致）。
        if y < -0.02:
            dy -= 0.0040 * g(x / (0.0120 * mouth_k)) * g((z - z_up_lip) / 0.0048)
            dy -= 0.0052 * g(x / (0.0114 * mouth_k)) * g((z - z_dn_lip) / 0.0040)
            dy += 0.0016 * g(x / (0.0120 * mouth_k)) * g((z - z_lip_line) / 0.0016)

        # 下巴：一小块向前、向下
        if y < 0.0:
            c = g(x / 0.0200) * g((z - z_chin) / 0.0125)
            dy -= 0.0060 * c
            dz -= 0.0015 * c

        # 颧骨：轻微外扩 + 前推（x 位置随头宽同比放大）
        if y < 0.02:
            ch = g((abs(x) - sx(0.0680)) / sx(0.0160)) * g((z - z_cheek) / 0.0140)
            dy -= 0.0030 * ch
            v.co.x += math.copysign(0.0016 * ch, x) if x else 0.0

        v.co.y += dy
        v.co.z += dz
    me.update()


# ---------- 贴片：先平面生成，再沿 +Y 射线投到脸面 ----------

def make_bvh(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bvh = BVHTree.FromBMesh(bm)
    bm.free()
    return bvh


def conform(ob, bvh, depth=0.0015):
    for v in ob.data.vertices:
        hit = bvh.ray_cast(Vector((v.co.x, -0.5, v.co.z)), Vector((0, 1, 0)))
        if hit[0] is not None:
            v.co.y = hit[0].y - depth
    ob.data.update()


def almond(w, hu, hd, tilt, n=48):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        z = (hu if s >= 0 else hd) * s
        pts.append(Vector((w * c, 0.0, z + tilt * w * c)))
    return pts


def fan(pts, name, mat):
    n = len(pts)
    cx = sum(p.x for p in pts) / n
    cz = sum(p.z for p in pts) / n
    verts = [(cx, 0.0, cz)] + [(p.x, 0.0, p.z) for p in pts]
    faces = [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)]
    ob = mesh_from(verts, faces, name)
    ob.data.materials.append(mat)
    return ob


def band(a, b, name, mat):
    n = len(a)
    verts = [(p.x, 0.0, p.z) for p in a] + [(p.x, 0.0, p.z) for p in b]
    faces = [(i, i + 1, n + i + 1, n + i) for i in range(n - 1)]
    ob = mesh_from(verts, faces, name)
    ob.data.materials.append(mat)
    return ob


def circle(cx, cz, r, segs=32):
    return [Vector((cx + r * math.cos(2 * math.pi * i / segs), 0.0,
                    cz + r * math.sin(2 * math.pi * i / segs))) for i in range(segs)]


def eye(side, mats, bvh):
    s = side
    # 外观旋钮：eye_size_scale 等比缩放眼型（外轮廓 + 虹膜/瞳孔/高光），
    # 默认 1.0 时 ×1.0 是精确运算，与引入旋钮前逐位一致。
    k = eye_size()
    cx, cz = eye_x() * s, sz(1.500)
    w, hu, hd = EYE_W * k, EYE_HU * k, EYE_HD * k
    shape = [Vector((p.x + cx, 0, p.z + cz))
             for p in almond(w, hu, hd, 0.24 * s)]
    parts = []
    w_ob = fan(shape, f"sclera_{s}", mats["sclera"])
    conform(w_ob, bvh, 0.0012)
    parts.append(w_ob)

    iris = fan(circle(cx, cz + 0.0022 * k, 0.0132 * k), f"iris_{s}", mats["iris"])
    conform(iris, bvh, 0.0024)
    parts.append(iris)

    pupil = fan(circle(cx, cz + 0.0022 * k, 0.0060 * k), f"pupil_{s}", mats["pupil"])
    conform(pupil, bvh, 0.0030)
    parts.append(pupil)

    hi1 = fan(circle(cx - 0.0048 * s * k, cz + 0.0090 * k, 0.0040 * k, 20),
              f"hi1_{s}", mats["white_emit"])
    conform(hi1, bvh, 0.0038)
    parts.append(hi1)

    hi2 = fan(circle(cx + 0.0044 * s * k, cz - 0.0062 * k, 0.0020 * k, 16),
              f"hi2_{s}", mats["white_emit"])
    conform(hi2, bvh, 0.0038)
    parts.append(hi2)

# 上睫毛：外缘抬起、内缘压到眼白上，形成有厚度的上眼睑
    # A2：内端 3.0mm → 2.0mm（外端仍 8.2mm；「外眼角更重」的方向是对的，保留）。
    n = 26
    a_pts, b_pts = [], []
    for i in range(n):
        t = math.pi * i / (n - 1)
        c, sn = math.cos(t), math.sin(t)
        x = cx + w * c
        z = cz + hu * sn + 0.24 * w * c
        th = 0.0020 + 0.0062 * max(0.0, c * s)
        a_pts.append(Vector((x, 0, z + 0.0016)))
        b_pts.append(Vector((x - 0.0009 * s, 0, z - th)))
    lash = band(a_pts, b_pts, f"lash_{s}", mats["lash"])
    conform(lash, bvh, 0.0034)
    parts.append(lash)

    # 下眼缘细线
    a2, b2 = [], []
    for i in range(n):
        t = math.pi * i / (n - 1)
        c, sn = math.cos(t), math.sin(t)
        x = cx + w * c
        z = cz - hd * sn + 0.24 * w * c
        a2.append(Vector((x, 0, z)))
        b2.append(Vector((x, 0, z - 0.0009)))
    low = band(a2, b2, f"lowline_{s}", mats["lash_soft"])
    conform(low, bvh, 0.0020)
    parts.append(low)

    return join(parts, name=f"eye_{s}")


def brow(side, mats, bvh):
    s = side
    cx = eye_x() * s
    z0 = sz(1.5300)
    a, b = [], []
    n = 22
    for i in range(n):
        t = i / (n - 1)
        x = cx + (-0.024 + 0.050 * t) * s
        z = z0 + 0.0055 * math.sin(math.pi * t) - 0.0070 * t
        # 2026-11-03：眉厚 4.9mm → 3.5mm，外端再收 45%。
        # 原值在中段达到 4.9mm，配上纯深色材质在浅脸上是一块「楔形厚条」；
        # 收细并把外端削尖后才有「画出来的眉」的感觉。
        th = (0.0012 + 0.0023 * math.sin(math.pi * (t ** 0.75))) * (1.0 - 0.45 * t)
        a.append(Vector((x, 0, z)))
        b.append(Vector((x, 0, z + th)))
    ob = band(a, b, f"brow_{s}", mats["brow"])
    conform(ob, bvh, 0.0016)
    return ob


def mouth(mats, bvh):
    """唇线贴片。A2：全宽 30mm → 24mm（=11.2% 脸宽，目标 10~13%），
    嘴角相对唇中点上翘 2.4mm → 1.3mm（目标 1.0~1.5mm）。"""
    z0 = sz(1.4305)
    # 外观旋钮：mouth_width_scale 直接乘嘴宽（默认 1.0 精确）。
    k = charparams.get("appearance.mouth_width_scale", _DEFAULT_MOUTH_WIDTH_SCALE)
    a, b = [], []
    n = 18
    for i in range(n):
        t = i / (n - 1)
        x = (-0.0120 + 0.024 * t) * k
        z = z0 - 0.0013 * math.sin(math.pi * t)
        a.append(Vector((x, 0, z)))
        b.append(Vector((x, 0, z - 0.0018 - 0.0016 * math.sin(math.pi * t))))
    ob = band(a, b, "mouth", mats["lip"])
    conform(ob, bvh, 0.0018)
    return ob


def ear(side, mats):
    """耳廓：椭球先压成薄片，再把耳甲压凹、耳轮推起——不再是一个肉球。

    坐标系（D0 修，2026-11-01）：`transform_apply(location=False, rotation=True,
    scale=True)` 之后，`v.co` 是**以耳中心为原点的局部坐标**（y∈±19mm、z∈±23mm），
    而 `cy/cz` 是世界位置。原代码写 `ly = (v.co.y - cy) / 0.0190`，等于拿局部
    坐标减世界坐标，r 恒在 50 左右 → `rim = exp(-((r-0.82)/0.22)²)` 与
    `concha = exp(-(r/0.42)²)` 都恒 ≈0，耳轮/耳甲从未被雕出来（耳朵是一个光滑
    扁椭球）。这里改成纯局部基准 `v.co.y/0.0190`、`v.co.z/0.0230`，r∈[0,1]：
      - r≈0（耳甲中心）→ concha≈1 → 内凹 −4.2mm
      - r≈0.82（耳轮，即外缘内侧一圈）→ rim≈1 → 外推 +2.8mm
      - r≈1（最外缘）→ rim≈0.51 → 外推 +1.4mm（这一点会撑起头部最大宽）

    注意：耳最外点从「光滑椭球赤道」变成「耳轮外推」后会略微外移，头宽随之变化，
    `_stageC/c_probe.py` 的 `ear_checks()` 会复测（目标 0.212~0.218）。
    """
    s = side
    # 外观旋钮：ear_scale 等比缩放耳廓（默认 1.0）。
    # 归一化基准（0.0190 / 0.0230）必须跟着乘 k，否则 r 不再落在 [0,1]，
    # 耳轮/耳甲会被错误地雕出来（D0 之前就是这个 bug 的另一副面孔）。
    k = charparams.get("appearance.ear_scale", _DEFAULT_EAR_SCALE)
    cx, cy, cz = sx(0.0935) * s, sx(0.010), sz(1.492)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, radius=1.0,
                                         location=(cx, cy, cz))
    ob = bpy.context.object
    ob.name = f"ear_{s}"
    # D0 修复 rim/concha 之后耳轮会真的外推 +2.8mm，头最大宽从 0.2139 涨到
    # 0.2182（上限 0.218）。把耳片厚度 0.0062 → 0.0052 收回来：最外点由
    # 「x 半径 × cos14°」与「z 半径 × sin14°」合成，降 1mm 厚度约让单侧
    # 最外点回退 0.7mm，实测头宽落回 0.2168。
    ry, rz = 0.0190 * k, 0.0230 * k
    ob.scale = (0.0052 * k, ry, rz)
    ob.rotation_euler = (math.radians(8), 0.0, math.radians(-14 * s))
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    for v in ob.data.vertices:
        # 局部坐标基准（不再减 cy/cz —— 那是世界位置，混用会把 r 推到 50+）
        ly = v.co.y / ry
        lz = v.co.z / rz
        r = math.hypot(ly, lz)
        rim = math.exp(-((r - 0.82) / 0.22) ** 2)        # 耳轮
        concha = math.exp(-(r / 0.42) ** 2)               # 耳甲
        v.co.x += s * (0.0028 * rim - 0.0042 * concha)
    ob.data.update()
    ob.data.materials.append(mats["skin"])
    bpy.ops.object.shade_smooth()
    return ob


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
    head = join(parts, "Head")
    shade_smooth(head)
    return head