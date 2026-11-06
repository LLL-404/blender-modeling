# -*- coding: utf-8 -*-
"""配饰件套 + 雪纺飘袖（设定书 §三.2-3，落差表 #4/#5 → spec/角色设定-银发旗袍-v1.md）。

件套（设定书 §三.3 / §三.2 原文口径）：
  1. 蝶形发饰：左右对称两片，深蓝底 + 均匀蓝波点，根部银色星形底座（实体建模）；
  2. 墨镜：大框运动款，镜框黑色亮面，镜片蓝紫渐变半透明，架在头顶发顶处；
  3. 领部饰件：立领中心盘扣下挂水滴形灰色吊坠，金属包边；
  4. 雪纺飘袖：上臂金色手环固定、向下垂落的宽袖，袖口不规则毛边，整体半透明。

坐标：Z 上，-Y 是正脸（与 head/body/hair 同约定）。单位米。

---------------------------------------------------------------- 锚点假设（honestNotes 单源，整合工程师必读）
本模块**不读** qipao / 新马尾（并行开发中），全部锚点要么从 head/body 现有几何
派生，要么是写死的假设。假设逐条列在这里，改锚点只改本节常量或调用参：

A1 蝶饰  位置=耳上方侧发区（锚 z=1.575，法向抬升后中心 z≈1.606），「发面」=
         颅面(head_rows 插值 rx) + HAIR_T。HAIR_T=10mm 是**假设的发厚**（v1 发帽
         外扩 7mm，v2 马尾未定）；马尾落地后若蝶饰陷进发丝/悬空，调 HAIR_T 或
         butterfly_pair(centre_z=..., out=...)。星形底座贴发面，正面视角被
         翅/结遮挡（根部件，侧下视角可见）——特写见 out/_v2_acc_bow_zoom.png。
A2 墨镜  「发顶面」= 颅顶 + HAIR_T；镜框下沿落在发面（GLASSES_POS y=-0.050、
         z=1.660、后仰 64°），按正顶视/斜上视/正脸渲染校过（out/_v2_acc_*.png）。
         真发壳比假设厚/薄时整组平移 sunglasses(pos=Vector(...)) 即可。
         镜片蓝端在上、紫端在下（brief 未规定方向，占位取上蓝下紫）。
A3 吊坠  立领盘扣**坐标是假设**（qipao 并行开发、接口未定）：盘扣中心取
         (0, -0.044, 1.334)——前颈面 y 由 body.neck() 路径推算为 -0.0297（z=1.33 处），
         再加 ~14mm 假设的领面/盘扣厚。旗袍接线时用 pendant(anchor=Vector(...))
         重锚。隔离渲染（out/_v2_acc_pendant_iso.png）确认形制与法线；场景内偏暗
         是颈底接触阴影，C 阶段灯光口径处理。
A4 飘袖  臂表锚 = body.arm() 路径表（body.py `zs/xs/rs`）在 z=1.108 处的线性插值：
         x=0.180、r=0.0373（**voxel+smooth 之前**的值）。融合后臂面实测
         （selftest 探针 [accprobe]）p50≈37.7mm，手环内径 ARM_BAND_R=40.8mm
         （+3.1mm 净空）。袖根环内缘距躯干面（TORSO z≈1.108 rx≈0.1336）约 6mm，
         body 的体素/平滑参数若变大会穿——调 sleeve_pair(center_out=...)。
         袖身 2~3 段辅助骨骼（brief §三.2 绑定要求）属 B 阶段，本轮不建；
         袖是开口网格（毛边），法线只做了一致性、未做朝向复核（黑雪纺双向
         渲染本轮无视觉差），C 阶段换材质时须复核。

---------------------------------------------------------------- 材质 TODO（C 阶段）
本轮全部是**占位材质**（设定书 §四 的三渲二材质规范未实施）：
  - 飘袖：纯黑 Principled + alpha 0.26 + BLENDED，双面（不剔背面）。§四 写
    「透明度 30%」歧义；**0.26 是按双层合成反解的**（开口网格双面渲染，
    a_eff = 1-(1-a)² → 0.45 观感），旧值 0.45 实际合成 0.70、读作不透明；
    「褶皱阴影柔和、不接受投影」未做。
  - 蝶饰波点：Voronoi F1 硬阈值程序化点阵（Object 坐标=世界坐标，cell 4.2mm /
    点径 ~2.5mm），不是贴图；C 阶段换 §四 正式材质时需重做。
  - 镜片渐变：Generated Y → ColorRamp(蓝→紫) 占位；§四 的「环境反射 20%、
    镜片边缘亮边」未做。
  - 金属件（星形底座/手环/包边）：普通 metallic 1.0，无 §四 的硬边高光/黑描边。
描边壳未加（整合时由 look.add_outline 统一处理）。

面数预算：配饰+飘袖 ≤3000（本轮口径），实测 1886（蝶饰 312×2 / 墨镜 434 /
吊坠 284 / 袖+手环 272×2），build_all() 打印 [acc] faces TOTAL。
"""
import math
import random

import bpy
from mathutils import Vector

import cfg
import head as headmod
from meshkit import mesh_from, join, shade_smooth, recalc_normals, loft


# ================================================================ 锚点常量（假设见文件头 A1~A4）
HAIR_T = 0.010          # A1/A2：假设的发厚（发面 = 颅面 + 此值）
BOW_Z = 1.575           # A1：蝶饰锚高度（耳顶 sz(1.492)+23mm 之上；中心 z 还要加法向抬升）
BOW_OUT = 0.002         # A1：蝶饰中心在发面之外的悬浮量（星形底座插进发丝）
BOW_DIR = (0.96, 0.06, 0.26)   # A1：蝶饰面法向（±x 为主、微前倾上翘），side 乘 x

PENDANT_ANCHOR = Vector((0.0, -0.044, 1.334))   # A3：盘扣中心（假设，待 qipao 重锚；-y=领面外）

GLASSES_POS = Vector((0.0, -0.050, 1.660))      # A2：镜桥基点（世界；-y 调到镜框下沿落在发面）
GLASSES_TILT = 64.0     # A2：镜面后仰角（度，0=像戴着眼上那样竖直，90=平躺头顶）

# A4：body.arm() 表（body.py 的 zs/xs/rs）在 ARM_BAND_Z 的线性插值（voxel 前）。
ARM_BAND_Z = 1.108
ARM_X = 0.180
ARM_R = 0.0373
ARM_DIR = (-0.227, -0.017, 0.974)   # 臂轴单位向（肩→腕方向，从 body.arm 表差分）

ANCHORS = {
    "bow": dict(z=BOW_Z, out=BOW_OUT, hair_t=HAIR_T, dir=BOW_DIR),
    "sunglasses": dict(pos=tuple(GLASSES_POS), tilt_deg=GLASSES_TILT, hair_t=HAIR_T),
    "pendant": dict(anchor=tuple(PENDANT_ANCHOR), basis="假设盘扣，待 qipao 重锚"),
    "sleeve": dict(band_z=ARM_BAND_Z, arm_x=ARM_X, arm_r=ARM_R,
                   source="body.arm() zs/xs/rs 在 z=1.108 的插值（voxel 前）"),
}


# ================================================================ 头表插值（学 hair._row_at，不 import hair）
def _row_at(rows, z):
    """按 z 在 head_rows 里线性插值一行 (z, rx, ryf, ryb, cy, power)。"""
    if z <= rows[0][0]:
        return rows[0]
    if z >= rows[-1][0]:
        return rows[-1]
    for a, b in zip(rows, rows[1:]):
        if a[0] <= z <= b[0]:
            w = (z - a[0]) / max(1e-9, b[0] - a[0])
            return [a[i] + (b[i] - a[i]) * w for i in range(5)] + [b[5]]
    return rows[-1]


def _closed_catmull(ctrl, n):
    """闭合 Catmull-Rom：ctrl=[Vector]（不重复首点）→ 均匀采样 n 点。"""
    m = len(ctrl)
    out = []
    for k in range(n):
        s = k / float(n) * m
        i = int(s)
        f = s - i
        p0 = ctrl[(i - 1) % m]
        p1 = ctrl[i % m]
        p2 = ctrl[(i + 1) % m]
        p3 = ctrl[(i + 2) % m]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * f +
                          (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f +
                          (-p0 + 3 * p1 - 3 * p2 + p3) * f * f * f))
    return out


# ================================================================ 几何基元
def _loop_tube(path, radii, seg, name, up=(0.0, 0.0, 1.0)):
    """闭合路径放样管（meshkit.tube 的闭环版）。

    path: [Vector] 闭合（不重复首点）；radii: 标量或与 path 等长的 (rx, ry)。
    rx = 截面在路径平面内的半宽，ry = 沿路径法向的半厚。
    """
    pts = [Vector(p) for p in path]
    n = len(pts)
    ref = Vector(up).normalized()
    if isinstance(radii, (int, float)):
        radii = [(radii, radii)] * n
    elif radii and isinstance(radii[0], (int, float)):
        radii = [tuple(radii)] * n          # 单个 (rx, ry) → 每点同截面
    rings = []
    for i in range(n):
        t = (pts[(i + 1) % n] - pts[i - 1])
        if t.length < 1e-9:
            t = Vector((0, 0, 1))
        t.normalize()
        ax = t.cross(ref).normalized()
        ay = ax.cross(t).normalized()
        rx, ry = radii[i]
        ring = [pts[i] + ax * (rx * math.cos(2 * math.pi * k / seg))
                + ay * (ry * math.sin(2 * math.pi * k / seg))
                for k in range(seg)]
        rings.append(ring)
    verts, faces = [], []
    for r in rings:
        verts.extend(r)
    for i in range(n):
        a = i * seg
        b = ((i + 1) % n) * seg
        for k in range(seg):
            k2 = (k + 1) % seg
            faces.append((a + k, a + k2, b + k2, b + k))
    return mesh_from(verts, faces, name)


def _star_base(name, centre, a1, a2, normal, r_out, r_in, thick, seg_pt=5):
    """五角星板（银色星形底座）。a1/a2 = 星板面内轴，normal = 板法向。"""
    a1, a2, n = Vector(a1), Vector(a2), Vector(normal).normalized()
    verts, faces = [], []
    for s in (-1.0, 1.0):
        for i in range(seg_pt * 2):
            r = r_out if i % 2 == 0 else r_in
            a = math.pi * i / seg_pt
            p = (Vector(centre) + a1 * (r * math.cos(a)) + a2 * (r * math.sin(a))
                 + n * (s * thick * 0.5))
            verts.append(p)
    m = seg_pt * 2
    for i in range(m):
        j = (i + 1) % m
        faces.append((i, j, m + j, m + i))
    faces.append(tuple(range(m - 1, -1, -1)))
    faces.append(tuple(range(m, 2 * m)))
    ob = mesh_from(verts, faces, name)
    return ob


def _blob(name, loc, radius, scale, rotation=(0.0, 0.0, 0.0), seg=10, rings=6):
    """低面数椭球（蝶饰中心结）。"""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings,
                                         radius=radius, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.scale = scale
    ob.rotation_euler = rotation
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return ob


def _rebase(ob, anchor):
    """把网格平移成「以 anchor 为物体原点」：之后旋转/缩放物体都绕自身锚点。

    整合工程师移动/旋转配饰时不会绕世界原点打转；B 阶段绑骨时 offset 也有语义。
    """
    anchor = Vector(anchor)
    for v in ob.data.vertices:
        v.co -= anchor
    ob.data.update()
    ob.location = anchor
    return ob


# ================================================================ 材质（占位，C 阶段重做，见文件头）
_MAT = {}


def _alpha(mat, a):
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Alpha"].default_value = a
    # Blender 4.2+ EEVEE Next 用 surface_render_method；旧 API 兜底（DESIGN §2.3-8 枚举试探）
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = 'BLENDED'
    if hasattr(mat, "blend_method"):
        try:
            mat.blend_method = 'BLEND'
        except Exception:
            pass
    mat.use_backface_culling = False
    return mat


def _dots(mat, cell=0.0042, dot_r=0.30):
    """深蓝底 + 均匀蓝波点：Voronoi F1 距离硬阈值（世界坐标点阵，占位）。"""
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = 'F1'
    vor.inputs["Scale"].default_value = 1.0 / cell
    math = nt.nodes.new("ShaderNodeMath")
    math.operation = 'LESS_THAN'
    math.inputs[1].default_value = dot_r
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.030, 0.055, 0.235, 1.0)   # 深蓝底
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (0.10, 0.30, 0.95, 1.0)      # 蓝波点
    nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
    nt.links.new(vor.outputs["Distance"], math.inputs[0])
    nt.links.new(math.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    return mat


def _lens_gradient(mat):
    """镜片蓝紫渐变（Generated Y，占位）。

    为什么用 Y 不用 Z：Generated 逐轴归一化到物体 bbox，墨镜架在头顶时
    bbox 的 z 被镜腿拉长，镜面只占 z 的顶端 —— Z 渐变会把整片镜挤进一个色端。
    方向口径：架顶 64° 后仰时局部 +y = 世界后上 = 镜框「上沿」。Generated
    Y=0 是局部 -y（=前下=镜片下沿）→ 端点 0 给紫、0.38 给蓝 = 上蓝下紫。
    """
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.02
    ramp.color_ramp.elements[0].color = (0.45, 0.20, 0.90, 1.0)      # 紫（下沿）
    ramp.color_ramp.elements[1].position = 0.38
    ramp.color_ramp.elements[1].color = (0.08, 0.22, 0.85, 1.0)      # 蓝（上沿）
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Y"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    return mat


def materials():
    """配饰占位材质集（惰性创建，重入复用）。C 阶段整体替换（见文件头 TODO）。"""
    import mats as matsmod

    def _mk(key, fn):
        if key not in _MAT or not _MAT.get(key):
            m = matsmod.simple(key, (0.5, 0.5, 0.5))
            fn(m)
            _MAT[key] = m
        return _MAT[key]

    return {
        "bow": _mk("acc_bow_dots", lambda m: _dots(_alpha_but_opaque(m))),
        "silver": _mk("acc_silver",
                      lambda m: _set(m, (0.82, 0.84, 0.88), 0.22, 1.0)),
        "gold": _mk("acc_gold",
                    lambda m: _set(m, (0.83, 0.62, 0.18), 0.28, 1.0)),
        "frame": _mk("acc_frame_black",
                     lambda m: _set(m, (0.012, 0.012, 0.014), 0.12, 0.0)),
        "lens": _mk("acc_lens_grad", lambda m: _alpha(_lens_gradient(m), 0.55)),
        "chiffon": _mk("acc_chiffon_black",
                       # 半透明观感 = 两层叠加后的合成值。袖是开口网格、双面渲染，
                       # 同一像素过两次 alpha：a_eff = 1-(1-a)²。旧值 a=0.45 合成
                       # 0.698 → 渲染读作不透明深灰（复核 finding #6）。要 0.45 的观感
                       # 单层应取 a = 1-√(1-0.45) = 0.258，这里取 0.26。
                       lambda m: _alpha(_set(m, (0.015, 0.015, 0.018), 0.62, 0.0),
                                        0.26)),
        "pendant": _mk("acc_pendant_gray",
                       lambda m: _set(m, (0.48, 0.49, 0.52), 0.35, 0.15)),
    }


def _set(mat, color, rough, metallic):
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    return mat


def _alpha_but_opaque(mat):
    """蝶饰本体不透明，但走统一入口便于 C 阶段一处改。"""
    mat.use_backface_culling = False
    return mat


# ================================================================ 1. 蝶形发饰
# 蝶饰局部约定：centre = 蝶饰中心（世界），n = 面法向（离头），u = 面内「上」，
# w = n×u（面内横向，翅膀沿 ±w 展开）。
_WING_L = 0.0205      # 单翅展开长（中心→翼尖）
_WING_W = 0.0064      # 缎带面内半宽
_WING_T = 0.0026      # 缎带法向半厚（薄一点才有「缎带」感，厚了像充气球）
_KNOT_R = 0.0078      # 中心结半径
_STAR_RO = 0.0095     # 星形底座外接半径（大于中心结，角尖从结后露出）
_STAR_RI = 0.0042     # 星形底座内径
_STAR_T = 0.0030      # 星形底座厚


def _bow_frame(side):
    """蝶饰的锚点与面内坐标架（A1 假设：颅面 + 发厚，法向 BOW_DIR）。"""
    rows = headmod.head_rows()
    row = _row_at(rows, BOW_Z)
    r_skull = row[1]                       # 该高度颅面半宽（x 向）
    n = Vector((BOW_DIR[0] * side, BOW_DIR[1], BOW_DIR[2])).normalized()
    centre = Vector((0.0, row[4], BOW_Z)) + n * (r_skull + HAIR_T + BOW_OUT)
    u = (Vector((0, 0, 1)) - n * n.z).normalized()     # 面内「上」= 世界 z 的面内投影
    w = n.cross(u).normalized()                         # 面内横向（≈±y）
    return centre, n, u, w


def _wing_path(centre, u, w, n, side_out):
    """单个翅环的闭合路径控制点（面内坐标 (w, u) + 沿 n 的微翘）。

    形状：从中心结出发的泪滴环——根窄、中段鼓、翼尖收圆，读作「蝶形结的翅」。
    """
    s = side_out
    L = _WING_L

    def P(dw, du, dn):
        return centre + w * (dw * s) + u * du + n * dn

    ctrl = [
        P(0.0035, 0.004, 0.0000),
        P(0.0110, 0.0115, 0.0018),
        P(0.0175, 0.0080, 0.0030),
        P(L, 0.0000, 0.0022),
        P(0.0170, -0.0075, 0.0008),
        P(0.0095, -0.0100, -0.0008),
        P(0.0035, -0.004, 0.0000),
    ]
    return ctrl


def butterfly(side, mats=None, centre_z=None, out=None):
    """一片蝶形发饰（side=-1 左 / +1 右）。返回 join 后的单物体，原点=蝶饰中心。"""
    m = materials()   # 配饰材质单源（景材质 dict 无配饰槽，传 M 也不吃）
    global BOW_Z, BOW_OUT
    z0, o0 = BOW_Z, BOW_OUT
    if centre_z is not None:
        BOW_Z = centre_z
    if out is not None:
        BOW_OUT = out
    try:
        centre, n, u, w = _bow_frame(side)
    finally:
        BOW_Z, BOW_OUT = z0, o0

    parts = []
    # 两片翅：闭环放样缎带（面内宽 _WING_W、法向厚 _WING_T）
    for s in (-1, 1):
        ctrl = _wing_path(centre, u, w, n, s)
        path = _closed_catmull(ctrl, 12)
        wing = _loop_tube(path, (_WING_W, _WING_T), 10,
                          f"acc_bow_wing_{side}_{s}", up=tuple(n))
        wing.data.materials.append(m["bow"])
        shade_smooth(wing)
        parts.append(wing)
    # 中心结（低面数椭球，扁在面内）
    knot_n = _KNOT_R * 0.62
    knot = _blob(f"acc_bow_knot_{side}", tuple(centre + n * 0.0028), _KNOT_R,
                 (knot_n / _KNOT_R, 0.78, 0.90),
                 rotation=(0.0, 0.0, 0.0), seg=10, rings=6)
    knot.data.materials.append(m["bow"])
    shade_smooth(knot)
    parts.append(knot)
    # 银色星形底座：贴发面（翅/结的根部，前缘露出发面 1mm）
    star = _star_base(f"acc_bow_star_{side}", tuple(centre - n * 0.0010),
                      u, w, n, _STAR_RO, _STAR_RI, 0.0030)
    star.data.materials.append(m["silver"])
    parts.append(star)

    ob = join(parts, f"AccButterfly_{'L' if side < 0 else 'R'}")
    recalc_normals(ob)
    _rebase(ob, centre)
    print(f"[acc] butterfly {'L' if side < 0 else 'R'}: "
          f"centre=({centre.x:+.4f},{centre.y:+.4f},{centre.z:+.4f}) "
          f"faces={len(ob.data.polygons)}")
    return ob


def butterfly_pair(mats=None):
    return [butterfly(-1, mats), butterfly(1, mats)]


# ================================================================ 2. 运动墨镜
_LENS_HW = 0.0370     # 单镜片半宽（大框）
_LENS_HH = 0.0288     # 单镜片半高
_LENS_P = 2.4         # 超椭圆幂（>2 方一些 = 运动款）
_LENS_CX = 0.0415     # 镜片中心偏离镜桥 ±
_RIM_RX = 0.0024      # 镜框截面：面内半宽
_RIM_RY = 0.0036      # 镜框截面：法向半厚（镜框厚）


def _rim_path(cx, s=1.0, k=1.0):
    """单个镜框的闭合路径（局部坐标，镜面在 z=0 平面，-y 为「上」）。"""
    e = 2.0 / _LENS_P
    pts = []
    n = 16
    for i in range(n):
        a = 2 * math.pi * i / n
        c, si = math.cos(a), math.sin(a)
        pts.append(Vector((cx + s * _LENS_HW * k * math.copysign(abs(c) ** e, c),
                           _LENS_HH * k * math.copysign(abs(si) ** e, si),
                           0.0)))
    return pts


def sunglasses(mats=None, pos=None, tilt_deg=None):
    """运动墨镜（局部建好 → 整组旋转平移架到头顶，A2）。

    局部约定：镜面在 xy 平面、法向 +z（戴镜时 +z 指向脸前方），-y 为镜框「上」。
    返回单物体；物体 transform 就是锚点（整合工程师改 location/rotation 即移位）。
    """
    m = materials()   # 配饰材质单源（景材质 dict 无配饰槽，传 M 也不吃）
    parts = []
    for s in (-1, 1):
        path = _rim_path(s * _LENS_CX)
        rim = _loop_tube(path, (_RIM_RX, _RIM_RY), 10, f"acc_glasses_rim_{s}",
                         up=(0.0, 0.0, 1.0))
        rim.data.materials.append(m["frame"])
        shade_smooth(rim)
        parts.append(rim)
        # 镜片：内缩的 n-gon 薄片（渐变占位材质）
        lens_pts = _rim_path(s * _LENS_CX, k=0.93)
        lens = mesh_from([tuple(p) for p in lens_pts],
                         [tuple(range(len(lens_pts)))], f"acc_glasses_lens_{s}")
        for v in lens.data.vertices:
            v.co.z -= 0.0006
        lens.data.materials.append(m["lens"])
        parts.append(lens)
        # 镜腿：沿镜框外缘向后下折（架顶 64° 后仰时世界「后下」= 局部 -y/-z 象限）
        x0 = s * (_LENS_CX + _LENS_HW - 0.002)
        pts = [Vector((x0, -0.004, -0.002)), Vector((s * 0.087, -0.026, -0.014)),
               Vector((s * 0.084, -0.042, -0.032)), Vector((s * 0.070, -0.050, -0.052))]
        from meshkit import tube as _tube
        leg = _tube(pts, [(0.0022, 0.0026), (0.0022, 0.0026),
                          (0.0020, 0.0024), (0.0016, 0.0020)],
                    seg=8, name=f"acc_glasses_leg_{s}")
        leg.data.materials.append(m["frame"])
        shade_smooth(leg)
        parts.append(leg)
    # 鼻梁（运动款一体梁）
    from meshkit import tube as _tube
    bridge = _tube([Vector((-0.007, -0.006, 0.0015)), Vector((0.0, -0.009, 0.0035)),
                    Vector((0.007, -0.006, 0.0015))],
                   [(0.0022, 0.0026), (0.0025, 0.0030), (0.0022, 0.0026)],
                   seg=8, name="acc_glasses_bridge")
    bridge.data.materials.append(m["frame"])
    shade_smooth(bridge)
    parts.append(bridge)

    ob = join(parts, "AccSunglasses")
    recalc_normals(ob)
    shade_smooth(ob)
    # 架到头顶：局部 +z（镜面法向）→ 世界前上方；绕 X 后仰 GLASSES_TILT
    tilt = GLASSES_TILT if tilt_deg is None else tilt_deg
    p = GLASSES_POS if pos is None else Vector(pos)
    ob.rotation_euler = (math.radians(tilt), 0.0, 0.0)
    ob.location = p
    print(f"[acc] sunglasses: pos=({p.x:+.4f},{p.y:+.4f},{p.z:+.4f}) tilt={tilt:.0f}° "
          f"faces={len(ob.data.polygons)}")
    return ob


# ================================================================ 3. 水滴形吊坠 + 金属包边
_DROP_L = 0.036       # 水滴主体长
_DROP_R = 0.0105      # 水滴最大半径
_BAIL_R = 0.0042      # 挂环半径
_BEZEL_COVER = 0.42   # 包边盖住水滴上部的高度比例（金属包边）


def _drop_profile(t):
    """水滴轮廓：t∈[0,1]（0=顶部挂点、1=圆底）→ 半径。尖上圆下。"""
    if t < 0.62:
        return _DROP_R * (t / 0.62) ** 0.80
    return _DROP_R * math.sqrt(max(0.0, 1.0 - ((t - 0.62) / 0.38) ** 2)) ** 0.92


def pendant(mats=None, anchor=None):
    """水滴形灰吊坠 + 金属包边（A3 假设锚点，qipao 接线时 pendant(anchor=...) 重锚）。

    结构：挂环（bail）→ 金属包边（罩住水滴上部）→ 水滴灰石。原点=挂环顶（=盘扣下沿）。
    """
    m = materials()   # 配饰材质单源（景材质 dict 无配饰槽，传 M 也不吃）
    a = Vector(PENDANT_ANCHOR if anchor is None else anchor)
    parts = []

    # 挂环：小闭环，环面 ⊥ 脖颈表面（≈ xz 平面，法向 -y）
    bail_c = a + Vector((0, 0.0012, -_BAIL_R - 0.0012))
    bail_path = [bail_c + Vector((_BAIL_R * math.cos(2 * math.pi * i / 10),
                                  0.0, _BAIL_R * math.sin(2 * math.pi * i / 10)))
                 for i in range(10)]
    bail = _loop_tube(bail_path, (0.0013, 0.0013), 6, "acc_pendant_bail",
                      up=(0.0, 1.0, 0.0))
    bail.data.materials.append(m["silver"])
    shade_smooth(bail)
    parts.append(bail)

    # 水滴主体：沿 -z 放样（截面圆环，顶部收尖、底部圆）
    seg = 12
    ts = [0.06, 0.18, 0.34, 0.52, 0.70, 0.86, 1.0]
    rings = []
    for t in ts:
        z = a.z - 0.004 - t * _DROP_L
        r = max(0.0013, _drop_profile(t))
        rings.append([Vector((r * math.cos(2 * math.pi * k / seg),
                              a.y - 0.0008 + 0.0, z)) for k in range(seg)])
    drop = loft(rings, cap_start=True, cap_end=True, name="acc_pendant_drop")
    drop.data.materials.append(m["pendant"])
    shade_smooth(drop)
    parts.append(drop)

    # 金属包边：跟随水滴上部轮廓的闭环（口径比水滴大 12%，罩住上部 _BEZEL_COVER）。
    # 路径必须沿轮廓走（右缘下行→左缘上行闭合），不能左右锯齿——锯齿会让
    # 管架反复横穿水滴，渲染成一团乱麻（首轮实测）。
    n_pt = 8
    half = []
    for i in range(n_pt):
        t = (_BEZEL_COVER * i / (n_pt - 1))
        r = max(0.0022, _drop_profile(t)) * 1.12 + 0.0006
        z = a.z - 0.004 - t * _DROP_L
        half.append((r, z))
    bez_pts = ([Vector((r, a.y - 0.0008, z)) for r, z in half]
               + [Vector((-r, a.y - 0.0008, z)) for r, z in reversed(half)])
    bez = _loop_tube(bez_pts, (0.0016, 0.0016), 8, "acc_pendant_bezel",
                     up=(0.0, 1.0, 0.0))
    bez.data.materials.append(m["silver"])
    shade_smooth(bez)
    parts.append(bez)

    ob = join(parts, "AccPendant")
    # 法线朝向已按「吊坠隔离渲染」实测为外向（out/_v2_acc_pendant_iso.png，
    # 灰面受光正常）；环序沿 -z 放样在此处恰好出外向绕序，若改 loft 环序
    # 须重渲隔离图复核（normals_make_consistent 只保一致、不保朝外）。
    recalc_normals(ob)
    _rebase(ob, a)
    print(f"[acc] pendant: anchor=({a.x:+.4f},{a.y:+.4f},{a.z:+.4f}) "
          f"faces={len(ob.data.polygons)}")
    return ob


# ================================================================ 4. 雪纺飘袖 + 金手环
_SEG = 22              # 袖截面顶点数
_FOLD_K = 5            # 垂坠褶皱的角向波数
_BAND_SEG = 14         # 手环环向点数
_BAND_TUBE = 10        # 手环截面顶点数


def _arm_frame(side):
    """上臂锚（A4：body.arm 表插值）→ 手环中心 + 环面坐标架。"""
    d = Vector(ARM_DIR)
    if side > 0:
        d = Vector((-ARM_DIR[0], ARM_DIR[1], ARM_DIR[2]))
    d = d.normalized()
    c = Vector((side * ARM_X, 0.0035, ARM_BAND_Z))   # 臂轴上（不加外移——外移是袖环的事）
    u = d.cross(Vector((0, 1, 0)))
    if u.length < 1e-6:
        u = Vector((1, 0, 0))
    u.normalize()
    v = d.cross(u).normalized()
    return c, d, u, v


# 手环净空：ARM_R 是 body.arm 表的 voxel 前值；voxel+smooth 融合后臂面实测
# （selftest 探针 [accprobe] band_clearance）p50 ≈ 38.6mm → 手环内径取 p50+2.2mm。
ARM_BAND_R = 0.0408


def _armband(side, m):
    """金色手环：短闭环管，环面 ⊥ 臂轴。"""
    c, d, u, v = _arm_frame(side)
    r = ARM_BAND_R
    path = [c + u * (r * math.cos(2 * math.pi * i / _BAND_SEG))
            + v * (r * math.sin(2 * math.pi * i / _BAND_SEG))
            for i in range(_BAND_SEG)]
    ob = _loop_tube(path, (0.0042, 0.0042), _BAND_TUBE, f"acc_armband_{side}",
                    up=tuple(d))
    ob.data.materials.append(m["gold"])
    shade_smooth(ob)
    return ob, c, u, v, d


def _sleeve(side, m, band_c, band_u, band_v, band_d, center_out=0.008):
    """单侧雪纺飘袖：袖根收在手环上，向下垂坠放大，袖口不规则毛边（开口环）。"""
    rng = random.Random(cfg.SEED + 11 * (1 if side > 0 else -1))
    # 路径（side=+1 语义，x 乘 side 镜像）：沿臂外缘向下、微微后飘
    P = [(0.186 + center_out - 0.008, 0.004, 1.116),
         (0.190 + center_out, 0.007, 1.062),
         (0.203 + center_out, 0.012, 0.986),
         (0.217 + center_out, 0.016, 0.912),
         (0.228 + center_out, 0.019, 0.850),
         (0.234 + center_out, 0.020, 0.800)]
    RR = [(0.046, 0.044), (0.050, 0.048), (0.062, 0.064),
          (0.074, 0.080), (0.085, 0.093), (0.091, 0.101)]
    seg = _SEG
    rings = []
    frames = []
    n_pt = len(P)
    for i in range(n_pt):
        p = Vector((P[i][0] * side, P[i][1], P[i][2]))
        if i == 0:
            t = (Vector((P[1][0] * side, P[1][1], P[1][2])) - p)
        elif i == n_pt - 1:
            t = (p - Vector((P[i - 1][0] * side, P[i - 1][1], P[i - 1][2])))
        else:
            t = (Vector((P[i + 1][0] * side, P[i + 1][1], P[i + 1][2]))
                 - Vector((P[i - 1][0] * side, P[i - 1][1], P[i - 1][2])))
        t.normalize()
        ax = t.cross(Vector((0, 1, 0))).normalized()
        ay = ax.cross(t).normalized()
        tt = i / float(n_pt - 1)
        rx, ry = RR[i][0], RR[i][1]
        amp = 0.03 + 0.17 * tt ** 1.6             # 褶皱向袖口加深（占位节奏）
        phase = 0.7 + 0.35 * i + (0.9 if side < 0 else 0.0)
        ring = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            fold = 1.0 + amp * math.cos(_FOLD_K * a + phase) \
                 + 0.30 * amp * math.cos(2 * _FOLD_K * a - phase)
            ring.append(p + ax * (rx * fold * math.cos(a))
                        + ay * (ry * fold * math.sin(a)))
        rings.append(ring)
        frames.append(p)

    # 毛边：最后一环向下伸出的锯齿（开口、不等长）
    p_end = frames[-1]
    fringe = []
    for k in range(seg):
        jitter = 0.008 + 0.018 * rng.random()
        base = rings[-1][k]
        radial = (base - p_end)            # 顶点 k 的径向向量（长度=该点口径半径）
        fringe.append(p_end + radial * 0.97
                      + Vector((0.002 * side, 0.001, -jitter)))

    verts, faces = [], []
    for r in rings + [fringe]:
        verts.extend(r)
    n_ring = len(rings) + 1
    for i in range(n_ring - 1):
        a = i * seg
        b = (i + 1) * seg
        for k in range(seg):
            k2 = (k + 1) % seg
            faces.append((a + k, a + k2, b + k2, b + k))
    ob = mesh_from(verts, faces, f"acc_sleeve_{side}")
    ob.data.materials.append(m["chiffon"])
    recalc_normals(ob)
    return ob


def sleeve_pair(mats=None, center_out=0.008):
    """左右飘袖（袖+金手环各 join 成一件，原点=手环中心）。"""
    m = materials()   # 配饰材质单源（景材质 dict 无配饰槽，传 M 也不吃）
    out = {}
    for side in (-1, 1):
        band, c, u, v, d = _armband(side, m)
        sl = _sleeve(side, m, c, u, v, d, center_out=center_out)
        ob = join([band, sl], f"AccSleeve_{'L' if side < 0 else 'R'}")
        # 袖毛边开口 → 有向体积判据不适用，只做一致性；法线朝向在 C 阶段
        # 换三渲二材质时须复核（黑雪纺双向渲染，本轮视觉无差）。
        recalc_normals(ob)
        _rebase(ob, c)
        out[f"sleeve_{'L' if side < 0 else 'R'}"] = ob
        print(f"[acc] sleeve {'L' if side < 0 else 'R'}: band=({c.x:+.4f},"
              f"{c.y:+.4f},{c.z:+.4f}) faces={len(ob.data.polygons)}")
    return out


# ================================================================ 组装入口
def build_all(mats=None):
    """全部配饰 + 飘袖。返回 {名字: 物体}；并打印面数合计（预算 ≤3000）。

    mats 参数兼容「传 look.set_all() 景材质」的调用习惯，但配饰材质一律走
    materials() 单源（景材质 dict 里没有配饰槽）。
    """
    m = materials()   # 配饰材质单源（景材质 dict 无配饰槽，传 M 也不吃）
    pieces = {}
    for ob in butterfly_pair(m):
        pieces[ob.name] = ob
    pieces["AccSunglasses"] = sunglasses(m)
    pieces["AccPendant"] = pendant(m)
    pieces.update(sleeve_pair(m))
    total = sum(len(ob.data.polygons) for ob in pieces.values())
    for name, ob in pieces.items():
        print(f"[acc] faces {name}={len(ob.data.polygons)}")
    print(f"[acc] faces TOTAL={total} (预算 配饰+飘袖 ≤3000)")
    return pieces
