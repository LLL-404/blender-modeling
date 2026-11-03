# -*- coding: utf-8 -*-
# 星尘 Blender 道具批量建模+渲染脚本（--background 批处理）
# 产物：render_src/<name>.png（2048 宽正交渲染，透明底；后处理 ÷4 到游戏像素）
# 后处理（降采样/量化/底对齐）由 tools/post_props.gd 完成
import bpy
import math
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import build_portraits as bp  # noqa: E402  （D5/D6 渲染助手复用 bp 轴；导入即建 RAW_DIR 契约目录）

GAME = os.environ.get("STARDUST_DIR", r"D:\G\game\games\stardust")
BLEND_PATH = os.path.join(GAME, "tools", "blender", "stardust_props.blend")
OUT_DIR = os.path.join(GAME, "tools", "blender", "render_src")
os.makedirs(OUT_DIR, exist_ok=True)
EL = 35.0  # 相机仰角（度）
RES_X = 2048

# 调色板（对齐游戏内配色）
C_STONE = (0.47, 0.49, 0.56, 1)      # 767a90 石板灰蓝
C_STONE_D = (0.36, 0.38, 0.45, 1)    # 深石
C_TEAL = (0.16, 0.72, 0.66, 1)       # 3fa8a0 青
C_TEAL_D = (0.16, 0.44, 0.42, 1)
C_GOLD = (0.95, 0.72, 0.30, 1)       # d8b868 金
C_GOLD_L = (1.0, 0.91, 0.66, 1)      # ffe9a8 亮金
C_WOOD = (0.64, 0.48, 0.30, 1)       # 8a6a48
C_WOOD_D = (0.43, 0.29, 0.20, 1)     # 6e4a34
C_WOOD_L = (0.74, 0.60, 0.40, 1)
C_DARK = (0.10, 0.08, 0.13, 1)       # 1a1420
C_NIGHT = (0.07, 0.09, 0.16, 1)      # 12182a
C_SHADOW = (0.04, 0.05, 0.09, 0.14)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
        try:
            sc.render.engine = eng
            print("[engine]", eng)
            break
        except Exception:
            continue
    sc.render.film_transparent = True
    bp.render_output((RES_X, 512), samples=32)   # D6：输出设置单源（res_y 默认 512 系现状）
    sc.view_settings.view_transform = "Standard"  # AgX 会去饱和，像素风要 Standard
    sc.view_settings.look = "None"
    print("[view]", sc.view_settings.view_transform)
    # 环境光（film_transparent 下不可见，只参与照明）
    w = bpy.data.worlds.new("W")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.62, 0.62, 0.68, 1)
    bg.inputs[1].default_value = 0.55


def mat(name, color, rough=0.75, metal=0.0, emit=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = color
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit > 0:
        try:
            b.inputs["Emission Color"].default_value = color
            b.inputs["Emission Strength"].default_value = emit
        except Exception:
            pass
    for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
        try:
            setattr(m, attr, val)
        except Exception:
            pass
    return m


def add(kind, name, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), material=None, verts=24, smooth=False):
    # torus/circle 操作器不收 scale 参数，先按基础参数创建再手动缩放
    if kind == "cube":
        bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot, scale=scale)
    elif kind == "cyl":
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, location=loc, rotation=rot, scale=scale)
    elif kind == "sph":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, location=loc, rotation=rot, scale=scale)
    elif kind == "torus":
        bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.055, major_segments=28, minor_segments=10,
                                         location=loc, rotation=rot)
    elif kind == "circle":
        bpy.ops.mesh.primitive_circle_add(vertices=verts, fill_type="NGON", radius=1.0, location=loc, rotation=rot)
    elif kind == "ico":
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, location=loc, rotation=rot, scale=scale)
    obj = bpy.context.active_object
    obj.name = name
    if kind in ("torus", "circle"):
        obj.scale = scale
    if material:
        obj.data.materials.append(material)
    if smooth:
        obj.data.shade_smooth()
    return obj


def hide_all():
    for o in bpy.context.scene.objects:
        o.hide_render = True
        o.hide_viewport = True


def show(objs):
    for o in objs:
        o.hide_render = False
        o.hide_viewport = False


def setup_lights():
    ld = bpy.data.lights.new("SunL", type="SUN")
    ld.energy = 4.6
    ld.angle = math.radians(12)
    so = bpy.data.objects.new("SunL", ld)
    bpy.context.collection.objects.link(so)
    so.rotation_euler = (math.radians(38), 0, math.radians(-28))
    fd = bpy.data.lights.new("Fill", type="AREA")
    fd.energy = 260
    fd.size = 7
    fo = bpy.data.objects.new("Fill", fd)
    bpy.context.collection.objects.link(fo)
    fo.location = (2.5, -6, 4.2)
    fo.rotation_euler = (math.radians(52), 0, math.radians(22))


def setup_cam():
    cd = bpy.data.cameras.new("Cam")
    cd.type = "ORTHO"
    cd.ortho_scale = 6.0
    cam = bpy.data.objects.new("Cam", cd)
    bpy.context.collection.objects.link(cam)
    d = 20.0
    el = math.radians(EL)
    cam.location = (0, -d * math.cos(el), d * math.sin(el))
    cam.rotation_euler = (math.radians(90 - EL), 0, 0)
    bpy.context.scene.camera = cam
    return cam


def shadow_decal(tag, sx, sy):
    return add("circle", "Shadow_" + tag, loc=(0, 0.05, 0.006), scale=(sx, sy, 1),
               material=mat("M_Shadow", C_SHADOW, rough=1.0), verts=28)


# ---------- 各道具建模（原点=地面接触中心，-Y 朝镜头=正面） ----------

def build_observatory():
    o = []
    o.append(shadow_decal("obs", 1.9, 1.5))
    o.append(add("cyl", "obs_base", loc=(0, 0, 1.05), scale=(1.5, 1.5, 1.05), material=mat("M_Stone", C_STONE), smooth=True))
    o.append(add("torus", "obs_trim", loc=(0, 0, 2.08), scale=(1.52, 1.52, 1.5), material=mat("M_Gold", C_GOLD, rough=0.4, metal=0.5)))
    o.append(add("cyl", "obs_neck", loc=(0, 0, 2.35), scale=(1.05, 1.05, 0.28), material=mat("M_StoneD", C_STONE_D), smooth=True))
    o.append(add("sph", "obs_dome", loc=(0, 0, 2.45), scale=(1.35, 1.35, 1.15), material=mat("M_Teal", C_TEAL, rough=0.45), smooth=True))
    # 穹顶观测缝：嵌入的暗色窄板
    o.append(add("cube", "obs_slit", loc=(0, -1.06, 2.75), rot=(math.radians(-18), 0, 0), scale=(0.16, 0.42, 0.95), material=mat("M_Dark", C_DARK)))
    # 望远镜从缝里探出
    o.append(add("cyl", "obs_tube", loc=(0, -1.52, 3.02), rot=(math.radians(118), 0, 0), scale=(0.09, 0.09, 1.0),
               material=mat("M_GoldD", C_GOLD, rough=0.35, metal=0.7), smooth=True))
    # 门与石阶
    o.append(add("cube", "obs_door", loc=(0, -1.54, 0.66), scale=(0.46, 0.08, 0.66), material=mat("M_WoodD", C_WOOD_D)))
    o.append(add("cube", "obs_step", loc=(0, -1.62, 0.08), scale=(0.6, 0.34, 0.08), material=mat("M_StoneD", C_STONE_D)))
    # 穹顶星徽
    o.append(add("ico", "obs_star", loc=(0, 0, 3.72), scale=(0.14, 0.14, 0.14), material=mat("M_Glow", C_GOLD_L, emit=4.0)))
    return o


def build_ship():
    o = []
    o.append(shadow_decal("ship", 1.5, 1.2))
    # 焦痕
    o.append(add("circle", "ship_scorch", loc=(0, 0.05, 0.012), scale=(1.2, 1.0, 1), material=mat("M_Scorch", (0.09, 0.10, 0.08, 0.38)), verts=28))
    o.append(add("sph", "ship_hull", loc=(0, 0.05, 0.72), rot=(math.radians(-14), math.radians(20), 0),
               scale=(1.28, 0.98, 0.78), material=mat("M_Hull", C_TEAL, rough=0.4, metal=0.25), smooth=True))
    # 舷侧金环
    o.append(add("torus", "ship_band", loc=(0, -0.1, 0.8), scale=(1.3, 1.0, 0.7),
               material=mat("M_Gold", C_GOLD, rough=0.4, metal=0.5)))
    o.append(add("sph", "ship_canopy", loc=(0.14, -0.34, 1.5), rot=(math.radians(-20), 0, 0),
               scale=(0.42, 0.34, 0.26), material=mat("M_Canopy", C_NIGHT, rough=0.2), smooth=True))
    # 座舱金环
    o.append(add("torus", "ship_canopy_ring", loc=(0.14, -0.3, 1.42), scale=(0.44, 0.36, 0.9),
               material=mat("M_Gold", C_GOLD, rough=0.4, metal=0.5)))
    # 尾翼（后上方的青色立板+金边）
    o.append(add("cube", "ship_fin", loc=(-1.0, 0.5, 1.42), rot=(0, math.radians(-26), math.radians(-10)),
               scale=(0.055, 0.3, 0.5), material=mat("M_HullD", C_TEAL_D, rough=0.5)))
    o.append(add("cube", "ship_fin_edge", loc=(-1.06, 0.42, 1.68), rot=(0, math.radians(-26), math.radians(-10)),
               scale=(0.05, 0.28, 0.06), material=mat("M_Gold", C_GOLD, rough=0.4, metal=0.5)))
    # 舱门（虚掩，贴在左前舷面上）
    o.append(add("cube", "ship_door", loc=(-0.66, -0.78, 0.56), rot=(math.radians(32), 0, math.radians(-18)),
               scale=(0.32, 0.05, 0.4), material=mat("M_Dark", C_DARK)))
    # 尾喷口
    o.append(add("cyl", "ship_nozzle", loc=(0.62, 1.02, 0.78), rot=(math.radians(-68), 0, 0), scale=(0.16, 0.16, 0.3),
               material=mat("M_GoldD", C_GOLD, metal=0.6, rough=0.4), smooth=True))
    # 天线+微光信标
    o.append(add("cyl", "ship_ant", loc=(0.7, 0.45, 1.35), rot=(math.radians(14), 0, 0), scale=(0.025, 0.025, 0.5), material=mat("M_GoldD", C_GOLD, metal=0.6), smooth=True))
    o.append(add("ico", "ship_beacon", loc=(0.76, 0.52, 1.62), scale=(0.075, 0.075, 0.075), material=mat("M_Glow", C_GOLD_L, emit=5.0)))
    # 散落碎片
    o.append(add("cube", "ship_deb1", loc=(1.35, -0.55, 0.1), rot=(0, 0, math.radians(28)), scale=(0.2, 0.14, 0.1), material=mat("M_HullD", C_TEAL_D, metal=0.2)))
    o.append(add("cube", "ship_deb2", loc=(-1.5, -0.3, 0.09), rot=(0, 0, math.radians(-16)), scale=(0.16, 0.12, 0.09), material=mat("M_Gold", C_GOLD, metal=0.4)))
    return o


def build_stall():
    o = []
    o.append(shadow_decal("stall", 1.7, 1.1))
    wood, wood_d = mat("M_Wood", C_WOOD), mat("M_WoodD", C_WOOD_D)
    for i, (px, py) in enumerate([(-1.02, -0.55), (1.02, -0.55), (-1.02, 0.55), (1.02, 0.55)]):
        o.append(add("cyl", "stall_post%d" % i, loc=(px, py, 0.66), scale=(0.06, 0.06, 0.66), material=wood_d, smooth=True))
    # 柜台
    o.append(add("cube", "stall_counter", loc=(0, -0.42, 0.34), scale=(1.0, 0.14, 0.34), material=wood))
    o.append(add("cube", "stall_board", loc=(0, -0.42, 0.55), scale=(1.06, 0.2, 0.05), material=mat("M_Gold", C_GOLD, rough=0.5)))
    # 条纹雨棚（金/青相间，微前倾）
    for i in range(7):
        fx = -0.93 + i * 0.31
        c = C_GOLD if i % 2 == 0 else C_TEAL
        o.append(add("cube", "stall_awn%d" % i, loc=(fx, 0.02, 1.32), rot=(math.radians(10), 0, 0),
                     scale=(0.155, 0.78, 0.045), material=mat("M_Aw%d" % (i % 2), c, rough=0.85)))
    # 棚顶脊（雨棚后上沿）
    o.append(add("cube", "stall_ridge", loc=(0, -0.4, 1.46), rot=(math.radians(10), 0, 0), scale=(1.09, 0.05, 0.035), material=wood_d))
    # 货品：干花瓶与果实碗
    o.append(add("cyl", "stall_vase", loc=(-0.55, -0.35, 0.48), scale=(0.09, 0.09, 0.14), material=mat("M_TealD", C_TEAL_D), smooth=True))
    o.append(add("ico", "stall_flower", loc=(-0.55, -0.35, 0.66), scale=(0.1, 0.1, 0.08), material=mat("M_Glow", C_GOLD_L, emit=1.6)))
    o.append(add("sph", "stall_bowl", loc=(0.5, -0.36, 0.45), scale=(0.14, 0.12, 0.07), material=mat("M_TealD", C_TEAL_D, rough=0.4), smooth=True))
    # 侧边木箱
    o.append(add("cube", "stall_crate", loc=(1.28, 0.1, 0.18), rot=(0, 0, math.radians(14)), scale=(0.2, 0.2, 0.18), material=mat("M_WoodL", C_WOOD_L)))
    return o


def build_lamp():
    o = []
    o.append(shadow_decal("lamp", 0.3, 0.3))
    o.append(add("cyl", "lamp_base", loc=(0, 0, 0.06), scale=(0.2, 0.2, 0.06), material=mat("M_Dark", C_DARK), smooth=True))
    o.append(add("cyl", "lamp_post", loc=(0, 0, 0.75), scale=(0.045, 0.045, 0.75), material=mat("M_Dark", C_DARK), smooth=True))
    o.append(add("cyl", "lamp_cap", loc=(0, 0, 1.52), scale=(0.14, 0.14, 0.04), material=mat("M_Dark", C_DARK)))
    o.append(add("ico", "lamp_star", loc=(0, 0, 1.4), scale=(0.16, 0.16, 0.16), material=mat("M_Glow", C_GOLD_L, emit=3.4), smooth=True))
    # 挂臂小星饰
    o.append(add("ico", "lamp_dot", loc=(0.1, -0.1, 1.22), scale=(0.045, 0.045, 0.045), material=mat("M_Glow", C_GOLD_L, emit=1.6)))
    return o


PROPS = [
    ("observatory", build_observatory, 2560, 35.0),
    ("ship", build_ship, 2048, 28.0),
    ("stall", build_stall, 2048, 35.0),
    ("lamp", build_lamp, 2048, 35.0),
]


def world_bbox(objs):
    from mathutils import Vector
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            p = o.matrix_world @ Vector(c)
            lo.x = min(lo.x, p.x)
            lo.y = min(lo.y, p.y)
            lo.z = min(lo.z, p.z)
            hi.x = max(hi.x, p.x)
            hi.y = max(hi.y, p.y)
            hi.z = max(hi.z, p.z)
    return lo, hi


def render_to(name, res_y):
    sc = bpy.context.scene
    sc.render.resolution_y = res_y
    bp.render_still(os.path.join(OUT_DIR, name + ".png"))   # D5：落盘单源（bp 轴）
    print("[rendered]", name)


def main():
    reset()
    setup_lights()
    cam = setup_cam()
    for name, fn, res_y, el_deg in PROPS:
        hide_all()
        objs = fn()
        show(objs)
        d = 20.0
        el = math.radians(el_deg)
        cam.location = (0, -d * math.cos(el), d * math.sin(el))
        cam.rotation_euler = (math.radians(90 - el_deg), 0, 0)
        lo, hi = world_bbox(objs)
        proj_h = (hi.z - lo.z) * math.cos(el) + (hi.y - lo.y) * math.sin(el)
        proj_w = hi.x - lo.x
        need = max(proj_w, proj_h) * 1.28
        cam.data.ortho_scale = need
        print("[frame]", name, "scale=%.2f" % need, "h=%.2f" % (hi.z - lo.z))
        render_to(name, res_y)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    print("[saved]", BLEND_PATH)


main()
