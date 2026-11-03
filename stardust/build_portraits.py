# -*- coding: utf-8 -*-
# 星尘立绘 3渲2 管线：Blender 低模胸像 -> 正交渲染 -> Godot 后处理成 128x192 像素立绘
#
# 跑法（脚本 2026-11-01 迁至 Blender建模仓，产物仍落游戏工程）：
#   blender --background --python "D:/G/github/实用工具/Blender建模/stardust/build_portraits.py"            # 全部 3 人 x 3 表情
#   blender --background --python "D:/G/github/实用工具/Blender建模/stardust/build_portraits.py" -- lila normal   # 单张调试
#   godot --headless --path . -s res://tools/portrait/post_portrait.gd -- --quantize
#   godot --headless --path . --import
#   godot --headless --path . -s res://tools/preview_portraits.gd
#
# 产物：tools/portrait/raw/<id>.png（normal）+ <id>_smile.png + <id>_sad.png
#
# 口径（踩过的坑）：
#   · Base Color 必须是**线性**值：palette.gd 的十六进制是 sRGB，直接喂会整体发白（第一版就栽这）
#   · view_transform=Standard（AgX 压饱和）
#   · film_transparent + 自发光背板渐变，背景可量化
#   · 正交相机正面 0°，像素立绘不要透视
#   · read_factory_settings 会清场景，材质缓存必须同步清（StructRNA removed）

import bpy
import math
import os
import sys

GAME = os.environ.get("STARDUST_DIR", r"D:\G\game\games\stardust")
RAW_DIR = os.path.join(GAME, "tools", "portrait", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

RES_X, RES_Y = 768, 1152
ORTHO = 1.70
CAM_Z = 1.30
SAMPLES = 32


# ---------------- 描边（inverted hull） ----------------
_OUTLINE_MAT = None


def outline_material():
    """反向外壳描边材质：近黑、无高光、背面剔除（只留轮廓）。"""
    global _OUTLINE_MAT
    if _OUTLINE_MAT is not None:
        try:
            _OUTLINE_MAT.name  # 缓存失效检测（read_factory_settings 后会抛）
            return _OUTLINE_MAT
        except Exception:
            _OUTLINE_MAT = None
    m = bpy.data.materials.new("M_Outline")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.012, 0.010, 0.020, 1.0)
    b.inputs["Roughness"].default_value = 1.0
    try:
        b.inputs["Specular IOR Level"].default_value = 0.0
    except Exception:
        pass
    m.use_backface_culling = True
    _OUTLINE_MAT = m
    return m


def add_outline(obj, thickness=0.012, min_size=0.05):
    """Solidify 反向外壳：负厚度 + 翻法线 + 材质偏移到黑色槽。
    太小的零件（眼睛高光等）跳过，否则描边会把它吞掉。"""
    if obj.type != "MESH" or len(obj.data.materials) == 0:
        return
    if len(obj.data.materials) > 1:
        # 多头材质对象（身体）不能用 Solidify 偏移：material_offset 是相对量，
        # 会把外壳指到相邻材质槽（实测脸被衣服色壳盖住）。这类对象跳过描边。
        return
    dim = max(obj.dimensions)
    if dim < min_size:
        return
    obj.data.materials.append(outline_material())
    mod = obj.modifiers.new("Outline", "SOLIDIFY")
    mod.thickness = -thickness
    mod.offset = 1.0
    mod.use_flip_normals = True
    mod.material_offset = 1
    mod.use_rim = False


def apply_outlines(thickness=0.012, min_size=0.05, skip_names=("Backdrop", "HoodCut")):
    """给场景里所有可见网格加描边。skip_names 里的（背板/布尔切割体）不动。"""
    for o in list(bpy.data.objects):
        if o.type != "MESH" or o.hide_render or o.name in skip_names:
            continue
        add_outline(o, thickness, min_size)


def _s2l(u):
    return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4


def hexc(h, a=1.0):
    """sRGB 十六进制 -> 线性 RGBA（Blender 的 Base Color 走线性空间）。"""
    h = h.lstrip("#")
    return (_s2l(int(h[0:2], 16) / 255.0), _s2l(int(h[2:4], 16) / 255.0), _s2l(int(h[4:6], 16) / 255.0), a)


C_OUTLINE = hexc("1a1420")
C_NIGHT_DEEP = hexc("1e2840")
C_SKIN = hexc("e8c8a8")
C_SKIN_SH = hexc("c9a284")
C_GOLD = hexc("e8b04a")
C_GOLD_L = hexc("ffe9a8")
C_GOLD_D = hexc("d8b868")
C_ROSE = hexc("d86078")
C_ROSE_D = hexc("a84460")
C_PINK = hexc("e58fc0")
C_PINK_D = hexc("c05a8a")
C_BLUE = hexc("5a7cc0")
C_BLUE_D = hexc("4a6ac0")
C_ICE = hexc("9ad8ff")
C_WHITE = hexc("f4f0e8")
C_EYE = hexc("2a2030")

_MAT_CACHE = {}


# ---------------- 渲染输出/落盘助手（D6/D5 单源，2026-11-03） ----------------
# build_characters.py / build_characters_mpfb.py / build_props.py 的输出设置块
# 与落盘三行都转调这里；本文件是 stardust 侧的复用轴。
def render_output(res, samples=None):
    """渲染输出设置：分辨率/百分比/格式/色彩模式/采样。res=(w, h)。返回 Scene。

    samples=None 时不动 taa_render_samples。
    """
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    if samples is not None:
        try:
            sc.eevee.taa_render_samples = samples
        except Exception:
            pass
    return sc


def render_still(filepath):
    """渲染落盘（filepath + write_still），返回写入路径。"""
    sc = bpy.context.scene
    sc.render.filepath = filepath
    bpy.ops.render.render(write_still=True)
    return filepath


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _MAT_CACHE.clear()
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
        try:
            sc.render.engine = eng
            print("[engine]", eng)
            break
        except Exception:
            continue
    sc.render.film_transparent = True
    render_output((RES_X, RES_Y), samples=SAMPLES)   # D6：输出设置单源
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    w = bpy.data.worlds.new("W")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.28, 0.30, 0.38, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.22


def mat(name, color, rough=0.92, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = color
    b.inputs["Roughness"].default_value = rough
    try:
        b.inputs["Specular IOR Level"].default_value = 0.0
    except Exception:
        pass
    if emit > 0:
        try:
            b.inputs["Emission Color"].default_value = color
            b.inputs["Emission Strength"].default_value = emit
        except Exception:
            pass
    return m


def m_of(color, rough=0.92, emit=0.0):
    key = (color, rough, emit)
    if key not in _MAT_CACHE:
        _MAT_CACHE[key] = mat("M_%02x%02x%02x_%d_%d" % (
            int(color[0] * 255), int(color[1] * 255), int(color[2] * 255),
            int(rough * 100), int(emit * 100)), color, rough, emit)
    return _MAT_CACHE[key]


def add_sphere(name, loc, scale, material, segs=32, rings=16, smooth=True):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=rings, radius=1.0, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    if smooth:
        bpy.ops.object.shade_smooth()
    return o


def add_box(name, loc, scale, material, rot=(0, 0, 0), bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    o.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    if bevel > 0:
        b = o.modifiers.new("Bevel", "BEVEL")
        b.width = bevel
        b.segments = 3
    return o


def add_cone(name, loc, r1, r2, depth, material, rot=(0, 0, 0), verts=24, smooth=True):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=depth, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    if smooth:
        bpy.ops.object.shade_smooth()
    return o


def add_cyl(name, loc, radius, depth, material, rot=(0, 0, 0), verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return o


def backdrop():
    bpy.ops.mesh.primitive_plane_add(size=6.0, location=(0, 1.4, 1.3), rotation=(math.radians(90), 0, 0))
    o = bpy.context.active_object
    o.name = "Backdrop"
    m = bpy.data.materials.new("M_Backdrop")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    tex = nt.nodes.new("ShaderNodeTexCoord")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = C_OUTLINE
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = C_NIGHT_DEEP
    nt.links.new(tex.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Y"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    o.data.materials.append(m)
    return o


# ---------------- 三点太阳灯表（D11 单源，2026-11-03） ----------------
# build_characters.py / build_characters_mpfb.py 的 set_view() 转抄此表，勿再各写一份。
# (name, energy, angle_deg, pitch_deg, rel_deg)——pitch/rel 为绕 x / 绕 z 的欧拉角（度）。
LIGHT_SPECS = (
    ("Key", 1.55, 18, 58, -32),
    ("Fill", 0.75, 50, 72, 46),
    ("Rim", 0.9, 12, 118, 168),
)


def lights():
    for name, energy, ang, pitch, rel in LIGHT_SPECS:
        d = bpy.data.lights.new(name, "SUN")
        d.energy = energy
        d.angle = math.radians(ang)
        o = bpy.data.objects.new(name, d)
        o.rotation_euler = (math.radians(pitch), 0, math.radians(rel))
        bpy.context.collection.objects.link(o)


def camera():
    cd = bpy.data.cameras.new("Cam")
    cd.type = "ORTHO"
    cd.ortho_scale = ORTHO
    cam = bpy.data.objects.new("Cam", cd)
    cam.location = (0, -4.0, CAM_Z)
    cam.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam


# ---------------- 角色骨架 ----------------
HEAD_Z = 1.60
HEAD_R = 0.300


def build_body(skin, cloth, cloth_d, accent):
    # 肩胸：锥台（上窄下宽），压扁 y 向，8 边给硬边
    torso = add_cone("Torso", (0, 0.04, 0.80), 0.56, 0.42, 0.64, cloth,
                     rot=(0, 0, math.radians(22.5)), verts=8, smooth=False)
    torso.scale = (1.0, 0.62, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    b = torso.modifiers.new("Bevel", "BEVEL")
    b.width = 0.06
    b.segments = 2
    # 胸前饰线（一条横带；斜板会在肩侧露补丁，弃用）
    add_box("CollarLine", (0, -0.245, 1.08), (0.34, 0.045, 0.035), accent, bevel=0.008)
    # 脖子
    add_cyl("Neck", (0, 0.02, 1.25), 0.105, 0.22, skin)
    # 头：蛋形（底部收窄出下巴，避免球+下巴两截接缝）
    head = add_sphere("Head", (0, 0.0, HEAD_Z), (HEAD_R * 1.02, HEAD_R * 0.94, HEAD_R * 0.99), skin)
    taper = head.modifiers.new("Taper", "SIMPLE_DEFORM")
    taper.deform_method = "TAPER"
    taper.factor = -0.18
    taper.deform_axis = "Z"
    # 耳朵
    for sx in (-1, 1):
        add_sphere("Ear%d" % sx, (sx * 0.30, 0.02, HEAD_Z - 0.03), (0.042, 0.055, 0.085), skin, 16, 8)


def build_face(expr, eye_col, brow_col, mouth_col, blush_col):
    ez = HEAD_Z + 0.045
    ex = 0.115
    ey = -0.272
    open_k = {"normal": 1.0, "smile": 0.40, "sad": 0.76}[expr]
    brow_rot = {"normal": 0.0, "smile": -0.10, "sad": 0.15}[expr]
    brow_dz = {"normal": 0.0, "smile": 0.018, "sad": -0.012}[expr]

    for side, sx in (("L", -1), ("R", 1)):
        add_sphere("Sclera" + side, (sx * ex, ey, ez), (0.056, 0.026, 0.050 * open_k),
                   m_of(C_WHITE), 24, 12)
        add_sphere("Iris" + side, (sx * ex, ey - 0.018, ez - 0.004),
                   (0.041, 0.018, 0.042 * open_k), eye_col, 24, 12)
        if expr != "smile":
            add_sphere("Spark" + side, (sx * ex - 0.013, ey - 0.030, ez + 0.014),
                       (0.010, 0.008, 0.010), m_of(C_WHITE), 12, 6)
        add_box("Lash" + side, (sx * ex, ey - 0.014, ez + 0.054 * open_k),
                (0.118, 0.024, 0.012), m_of(C_OUTLINE), (0, 0, sx * -0.05))
        add_box("Brow" + side, (sx * ex, ey - 0.012, ez + 0.098 + brow_dz),
                (0.104, 0.022, 0.013), brow_col, (0, 0, sx * -brow_rot))
        add_sphere("Blush" + side, (sx * 0.200, ey + 0.026, ez - 0.082),
                   (0.046, 0.010, 0.022), blush_col, 16, 8)

    mz = HEAD_Z - 0.130
    if expr == "smile":
        add_sphere("Mouth", (0, ey - 0.006, mz), (0.062, 0.012, 0.022), mouth_col, 20, 10)
        add_box("MouthUp", (0, ey - 0.008, mz + 0.016), (0.100, 0.012, 0.010), mouth_col)
    elif expr == "sad":
        add_sphere("Mouth", (0, ey - 0.006, mz), (0.040, 0.012, 0.018), mouth_col, 20, 10)
        add_box("MouthDown", (0, ey - 0.008, mz - 0.014), (0.055, 0.012, 0.009), mouth_col)
    else:
        add_sphere("Mouth", (0, ey - 0.006, mz), (0.034, 0.010, 0.013), mouth_col, 20, 10)

    add_sphere("Nose", (0, ey - 0.010, HEAD_Z - 0.080), (0.018, 0.014, 0.014),
               m_of(C_SKIN_SH), 12, 6)


def bangs(hair, hair_d, accent, style):
    """刘海：圆润额发（球体拼接），不用锥体——锥体在 128px 下会变成一排尖刺。"""
    if style == "part":
        # 中分：三球额发 + 两侧斜落，发际线落在眉上
        for i, bx in enumerate((-0.185, 0.0, 0.185)):
            add_sphere("Fringe%d" % i, (bx, -0.262, HEAD_Z + 0.20),
                       (0.135, 0.105, 0.115), hair, 20, 12)
        for sx in (-1, 1):
            add_sphere("BangSide%d" % sx, (sx * 0.255, -0.185, HEAD_Z + 0.04),
                       (0.080, 0.095, 0.185), hair, 16, 10)
        add_box("Part", (0, -0.285, HEAD_Z + 0.26), (0.012, 0.025, 0.10), hair_d)
    elif style == "hood":
        add_box("Bang", (0, -0.250, HEAD_Z + 0.24), (0.34, 0.075, 0.10), hair)
    else:
        # 齐刘海：一排短球，下缘齐眉
        for i in range(5):
            x = -0.24 + i * 0.12
            add_sphere("Bang%d" % i, (x, -0.265, HEAD_Z + 0.21),
                       (0.078, 0.09, 0.10), hair, 16, 10)


def side_locks(hair, hair_d, style):
    if style == "none":
        return
    for sx in (-1, 1):
        if style == "long":
            add_box("Lock%d" % sx, (sx * 0.278, 0.03, 1.30), (0.095, 0.16, 0.66), hair,
                    (0, 0, sx * math.radians(3)), 0.04)
        else:
            add_box("Lock%d" % sx, (sx * 0.280, -0.02, 1.40), (0.105, 0.16, 0.42), hair,
                    (0, 0, sx * math.radians(3)), 0.04)


def star(color, loc, r):
    """四角星：两块薄板交叉，尖端朝上下左右。"""
    for ang in (0.0, math.radians(90)):
        add_box("Star", loc, (r * 2.0, 0.018, r * 0.30), color, (0, ang, 0), 0.006)


def hair_lila(hair, hair_d, accent):
    add_sphere("HairBack", (0, 0.085, HEAD_Z + 0.01), (0.365, 0.365, 0.395), hair, 32, 16)
    add_sphere("HairTop", (0, 0.02, HEAD_Z + 0.24), (0.335, 0.335, 0.155), hair, 32, 16)
    bangs(hair, hair_d, accent, "part")
    side_locks(hair, hair_d, "long")
    star(accent, (-0.250, -0.330, HEAD_Z + 0.175), 0.042)


def hair_orin(hair, cloth, cloth_d, accent):
    hood = add_sphere("Hood", (0, 0.035, HEAD_Z + 0.04), (0.395, 0.395, 0.415), cloth, 32, 16)
    cutter = add_sphere("HoodCut", (0, -0.315, HEAD_Z - 0.03), (0.295, 0.255, 0.295), cloth, 24, 12)
    boo = hood.modifiers.new("Cut", "BOOLEAN")
    boo.operation = "DIFFERENCE"
    boo.object = cutter
    cutter.hide_render = True
    cutter.hide_viewport = True
    add_cone("HoodTip", (0, 0.12, HEAD_Z + 0.44), 0.10, 0.0, 0.24, cloth, (math.radians(-14), 0, 0), 16)
    add_box("Cape", (0, 0.12, 0.88), (1.00, 0.42, 0.70), cloth_d, bevel=0.12)
    bangs(hair, hair, accent, "hood")
    add_box("HoodRim", (0, -0.20, HEAD_Z + 0.30), (0.40, 0.07, 0.045), accent, bevel=0.01)
    star(accent, (0, -0.245, 0.98), 0.045)


def hair_mia(hair, hair_d, accent, cloth):
    add_sphere("HairBack", (0, 0.07, HEAD_Z + 0.01), (0.350, 0.350, 0.355), hair, 32, 16)
    add_sphere("HairTop", (0, 0.02, HEAD_Z + 0.13), (0.325, 0.325, 0.25), hair, 32, 16)
    bangs(hair, hair_d, accent, "full")
    side_locks(hair, hair_d, "short")
    for sx in (-1, 1):
        add_sphere("Tail%dA" % sx, (sx * 0.415, 0.03, HEAD_Z + 0.01), (0.135, 0.135, 0.19), hair, 20, 12)
        add_sphere("Tail%dB" % sx, (sx * 0.455, 0.03, HEAD_Z - 0.17), (0.105, 0.105, 0.15), hair, 20, 12)
        add_cyl("Band%d" % sx, (sx * 0.372, 0.03, HEAD_Z + 0.10), 0.068, 0.05, accent,
                (0, math.radians(90), 0), 16)
    add_box("CollarTrim", (0, -0.205, 1.06), (0.36, 0.06, 0.05), accent, bevel=0.01)


SPECS = {
    "lila": dict(hair=C_GOLD, hair_d=C_GOLD_D, cloth=C_ROSE, cloth_d=C_ROSE_D,
                 accent=C_GOLD_L, eye=C_EYE, brow=C_GOLD_D, mouth=C_ROSE_D, blush=C_ROSE),
    "orin": dict(hair=C_GOLD_D, hair_d=C_GOLD_D, cloth=C_BLUE, cloth_d=C_BLUE_D,
                 accent=C_ICE, eye=C_EYE, brow=C_GOLD_D, mouth=C_ROSE_D, blush=C_ROSE),
    "mia": dict(hair=C_PINK_D, hair_d=C_PINK_D, cloth=C_GOLD, cloth_d=C_GOLD_D,
                accent=C_PINK, eye=C_EYE, brow=C_PINK_D, mouth=C_ROSE_D, blush=C_PINK),
}


def build(pid, expr):
    s = SPECS[pid]
    skin = m_of(C_SKIN)
    cloth = m_of(s["cloth"])
    cloth_d = m_of(s["cloth_d"])
    hair = m_of(s["hair"])
    hair_d = m_of(s["hair_d"])
    accent = m_of(s["accent"], rough=0.55, emit=0.15)
    eye = m_of(s["eye"])
    brow = m_of(s["brow"])
    mouth = m_of(s["mouth"])
    blush = m_of(s["blush"], rough=0.95)

    build_body(skin, cloth, cloth_d, accent)
    if pid == "lila":
        hair_lila(hair, hair_d, accent)
    elif pid == "orin":
        hair_orin(hair, cloth, cloth_d, accent)
    else:
        hair_mia(hair, hair_d, accent, cloth)
    build_face(expr, eye, brow, mouth, blush)


def render(pid, expr):
    reset()
    backdrop()
    lights()
    camera()
    build(pid, expr)
    apply_outlines(thickness=0.010, min_size=0.06)
    suffix = "" if expr == "normal" else "_" + expr
    path = render_still(os.path.join(RAW_DIR, "%s%s.png" % (pid, suffix)))   # D5：落盘单源
    print("[render]", pid, expr, "->", path)


if __name__ == "__main__":
    argv = sys.argv
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    jobs = []
    if len(args) >= 2:
        jobs = [(args[0], args[1])]
    else:
        for pid in ("lila", "orin", "mia"):
            for expr in ("normal", "smile", "sad"):
                jobs.append((pid, expr))
    for pid, expr in jobs:
        render(pid, expr)
    print("[done] portraits ->", RAW_DIR)
