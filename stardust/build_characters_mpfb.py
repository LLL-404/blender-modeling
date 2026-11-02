# -*- coding: utf-8 -*-
# 星尘角色全身（WIP，未接入游戏）：MPFB/MakeHuman 基础人体（CC0）+ 程序化头发/五官 -> 四向渲染
#
# ⚠️ 状态：管线跑通、人体轮廓正确，但**背面后脑露头皮**（头的前后深度 > 发球半径），
#    且脸部在 64px 下过小。游戏当前仍使用 build_characters.py（锥台版）产出的帧表。
#    下一步：按头网格实测 depth 定发球 y 半径，或直接用 MPFB 的 hair 资产。
#
# 为什么换：锥台/球体拼出来的是方块玩偶。真人体拓扑有肩线、手臂、手、脚踝，
# 64px 下轮廓直接不一样。
#
# 资产：tools/blender/mpfb/human.obj（由 gen_human.py 用 MPFB2 生成，19k 顶点，CC0）
#      MPFB2 以扩展方式装在 Blender 5.2：bl_ext.user_default.mpfb
#
# 跑法（脚本 2026-11-01 迁至 Blender建模仓，产物仍落游戏工程）：
#   blender --background --python "D:/G/github/实用工具/Blender建模/stardust/gen_human.py"     # 首次/换体型时生成人体
#   blender --background --python "D:/G/github/实用工具/Blender建模/stardust/build_characters_mpfb.py"            # 四人四向
#   blender --background --python "D:/G/github/实用工具/Blender建模/stardust/build_characters_mpfb.py" -- lila    # 单人
#   godot --headless --path . -s res://tools/char_sheet.gd
#
# 产物：tools/blender/render_body/<id>_<view>.png（256x384 透明底，四向；游戏工程内）
#       assets/sprites/characters/<id>.png（256x64 帧表，由 char_sheet.gd 合成）

import bpy
import math
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import build_portraits as bp  # noqa: E402

BASE_OBJ = r"D:\G\game\games\stardust\tools\blender\mpfb\human.obj"
OUT_DIR = r"D:\G\game\games\stardust\tools\blender\render_body"
os.makedirs(OUT_DIR, exist_ok=True)

RES_X, RES_Y = 256, 384
ORTHO = 3.0
CAM_Z = 1.5
SAMPLES = 24

C_SKIN = bp.C_SKIN
C_WHITE = bp.C_WHITE
C_EYE = bp.C_EYE
C_GOLD = bp.C_GOLD
C_GOLD_L = bp.C_GOLD_L
C_GOLD_D = bp.C_GOLD_D
C_ROSE = bp.C_ROSE
C_ROSE_D = bp.C_ROSE_D
C_PINK = bp.C_PINK
C_PINK_D = bp.C_PINK_D
C_BLUE = bp.C_BLUE
C_BLUE_D = bp.C_BLUE_D
C_ICE = bp.C_ICE

VIEWS = [("down", 0), ("up", 180), ("left", 90), ("right", -90)]

SPECS = {
    "lila": dict(h=1.65, hair="long", hair_c=C_GOLD, hair_d=C_GOLD_D,
                 cloth=C_ROSE, cloth_d=C_ROSE_D, accent=C_GOLD_L, shoe=C_ROSE_D),
    "orin": dict(h=1.80, hair="hood", hair_c=C_GOLD_D, hair_d=C_GOLD_D,
                 cloth=C_BLUE, cloth_d=C_BLUE_D, accent=C_ICE, shoe=C_BLUE_D),
    "mia": dict(h=1.55, hair="twin", hair_c=C_PINK_D, hair_d=C_PINK_D,
                cloth=C_GOLD, cloth_d=C_GOLD_D, accent=C_PINK, shoe=C_GOLD_D),
    "player": dict(h=1.70, hair="short", hair_c=bp.hexc("2a3550"), hair_d=bp.hexc("1a2030"),
                   cloth=bp.hexc("3fa8a0"), cloth_d=bp.hexc("2d7a74"), accent=C_GOLD_L,
                   shoe=bp.hexc("2d7a74")),
}


def scene_setup():
    bp.reset()
    sc = bpy.context.scene
    sc.render.resolution_x = RES_X
    sc.render.resolution_y = RES_Y
    sc.render.image_settings.color_mode = "RGBA"
    try:
        sc.eevee.taa_render_samples = SAMPLES
    except Exception:
        pass
    cd = bpy.data.cameras.new("Cam")
    cd.type = "ORTHO"
    cd.ortho_scale = ORTHO
    cam = bpy.data.objects.new("Cam", cd)
    cam.location = (0, -6.0, CAM_Z)
    cam.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.collection.objects.link(cam)
    sc.camera = cam
    return cam


def set_view(cam, yaw_deg):
    yaw = math.radians(yaw_deg)
    r = 6.0
    cam.location = (math.sin(yaw) * r, -math.cos(yaw) * r, CAM_Z)
    cam.rotation_euler = (math.radians(90), 0, yaw)
    for name, energy, ang, pitch, rel in (
        ("Key", 1.55, 18, 58, -32),
        ("Fill", 0.75, 50, 72, 46),
        ("Rim", 0.9, 12, 118, 168),
    ):
        o = bpy.data.objects.get(name)
        if o is None:
            d = bpy.data.lights.new(name, "SUN")
            d.energy = energy
            d.angle = math.radians(ang)
            o = bpy.data.objects.new(name, d)
            bpy.context.collection.objects.link(o)
        o.rotation_euler = (math.radians(pitch), 0, math.radians(rel) + yaw)


def import_base(height):
    """导入人体：转 Z 朝上、缩到目标身高、脚底贴 0、水平居中。"""
    bpy.ops.wm.obj_import(filepath=BASE_OBJ)
    obj = bpy.context.selected_objects[0]
    obj.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    zs = [(obj.matrix_world @ v.co).z for v in obj.data.vertices]
    k = height / (max(zs) - min(zs))
    obj.scale = (k, k, k)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    xs = [(obj.matrix_world @ v.co).x for v in obj.data.vertices]
    ys = [(obj.matrix_world @ v.co).y for v in obj.data.vertices]
    zs = [(obj.matrix_world @ v.co).z for v in obj.data.vertices]
    obj.location = (-(min(xs) + max(xs)) / 2, -(min(ys) + max(ys)) / 2, -min(zs))
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    return obj


def stylize_head(obj, s):
    """真人 7.5 头身 → 游戏 5.5 头身：颈以上按比例放大，再整体缩回目标身高。"""
    scale = s["h"] / 1.65
    neck = 1.40 * scale
    for v in obj.data.vertices:
        if v.co.z > neck:
            t = v.co.z - neck
            v.co.z = neck + t * 1.26
            v.co.x *= 1.30
            v.co.y *= 1.24
    zs = [v.co.z for v in obj.data.vertices]
    k = s["h"] / (max(zs) - min(zs))
    for v in obj.data.vertices:
        v.co *= k
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    zs = [v.co.z for v in obj.data.vertices]
    ox = -(min(xs) + max(xs)) / 2
    oy = -(min(ys) + max(ys)) / 2
    oz = -min(zs)
    for v in obj.data.vertices:
        v.co.x += ox
        v.co.y += oy
        v.co.z += oz


def paint_body(obj, s):
    """按面心高度/横向位置分材质：头与手=皮肤、脚=鞋、下摆=深色、其余=衣服。"""
    me = obj.data
    me.materials.clear()
    skin = bp.m_of(s.get("skin", C_SKIN))
    cloth = bp.m_of(s["cloth"])
    cloth_d = bp.m_of(s["cloth_d"])
    shoe = bp.m_of(s["shoe"])
    for m in (skin, cloth, cloth_d, shoe):
        me.materials.append(m)
    scale = s["h"] / 1.65
    for poly in me.polygons:
        c = poly.center
        if c.z > 1.30 * scale:
            poly.material_index = 0
        elif abs(c.x) > 0.30 and c.z > 0.72 * scale:
            poly.material_index = 0            # 手臂与手
        elif c.z < 0.075 * scale:
            poly.material_index = 3            # 鞋
        elif c.z < 0.45 * scale:
            poly.material_index = 2            # 腿/裙摆
        else:
            poly.material_index = 1            # 上身衣服


def head_metrics(obj, s):
    zs = [(obj.matrix_world @ v.co).z for v in obj.data.vertices]
    top = max(zs)
    cut = top - 0.13 * s["h"]
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices if (obj.matrix_world @ v.co).z >= cut]
    xs = [p.x for p in pts]
    zz = [p.z for p in pts]
    hz = (min(zz) + max(zz)) / 2
    hr = max((max(xs) - min(xs)) / 2, (max(zz) - min(zz)) / 2)
    return hz, hr


def build_face(hz, hr, s):
    eye = bp.m_of(C_EYE)
    white = bp.m_of(C_WHITE)
    ey = -hr * 0.82
    ex = hr * 0.34
    for sx in (-1, 1):
        bp.add_sphere("Sclera%d" % sx, (sx * ex, ey, hz + hr * 0.10),
                      (hr * 0.22, 0.010, hr * 0.16), white, 12, 8)
        bp.add_sphere("Iris%d" % sx, (sx * ex, ey - 0.008, hz + hr * 0.09),
                      (hr * 0.13, 0.008, hr * 0.12), eye, 12, 8)
    bp.add_sphere("Mouth", (0, ey - 0.004, hz - hr * 0.55),
                  (hr * 0.15, 0.006, hr * 0.05), bp.m_of(s["cloth_d"]), 10, 6)
    bp.add_sphere("Nose", (0, ey - hr * 0.08, hz - hr * 0.10),
                  (hr * 0.09, hr * 0.09, hr * 0.08), bp.m_of(s.get("skin", C_SKIN)), 10, 6)


def build_hair(hz, hr, s):
    hair = bp.m_of(s["hair_c"])
    hair_d = bp.m_of(s["hair_d"])
    accent = bp.m_of(s["accent"], rough=0.55, emit=0.12)
    top = hz + hr * 0.78
    # 头盖发：所有发型共用，盖住颅顶与后脑（只靠 HairBack 会在背面露头皮）
    if s["hair"] != "hood":
        bp.add_sphere("HairCap", (0, hr * 0.12, hz + hr * 0.30),
                      (hr * 1.16, hr * 1.16, hr * 0.98), hair, 20, 12)

    if s["hair"] == "long":
        bp.add_sphere("HairBack", (0, hr * 0.24, hz + 0.02), (hr * 1.30, hr * 1.26, hr * 1.28), hair, 20, 12)
        bp.add_sphere("HairTop", (0, 0, top - hr * 0.16), (hr * 1.10, hr * 1.10, hr * 0.60), hair, 20, 12)
        for i, bx in enumerate((-0.62, 0.0, 0.62)):
            bp.add_sphere("Fringe%d" % i, (bx * hr, -hr * 0.86, top - hr * 0.16),
                          (hr * 0.34, hr * 0.26, hr * 0.26), hair, 16, 10)
        for sx in (-1, 1):
            bp.add_box("Lock%d" % sx, (sx * hr * 0.95, hr * 0.10, hz - hr * 1.4),
                       (hr * 0.30, hr * 0.46, hr * 2.2), hair, (0, 0, sx * math.radians(3)), hr * 0.10)
        for ang in (0.0, math.radians(90)):
            bp.add_box("Star", (-hr * 0.78, -hr * 0.92, top - hr * 0.42),
                       (hr * 0.20, 0.006, hr * 0.055), accent, (0, ang, 0), 0.002)
    elif s["hair"] == "hood":
        hood = bp.add_sphere("Hood", (0, hr * 0.10, hz + 0.02), (hr * 1.30, hr * 1.30, hr * 1.34),
                             bp.m_of(s["cloth"]), 20, 12)
        cut = bp.add_sphere("HoodCut", (0, -hr * 1.15, hz - 0.01), (hr * 0.98, hr * 0.90, hr * 1.00),
                            bp.m_of(s["cloth"]), 16, 10)
        b = hood.modifiers.new("Cut", "BOOLEAN")
        b.operation = "DIFFERENCE"
        b.object = cut
        cut.hide_render = True
        cut.hide_viewport = True
        bp.add_cone("HoodTip", (0, hr * 0.42, hz + hr * 1.34), hr * 0.30, 0.0, hr * 0.70,
                    bp.m_of(s["cloth"]), (math.radians(-14), 0, 0), 12)
        bp.add_box("Cape", (0, hr * 0.30, hz - hr * 2.6), (hr * 3.0, hr * 1.4, hr * 2.4),
                   bp.m_of(s["cloth_d"]), bevel=hr * 0.3)
        bp.add_box("HoodRim", (0, -hr * 0.80, hz + hr * 0.92), (hr * 1.35, hr * 0.22, hr * 0.12),
                   accent, bevel=0.004)
        bp.add_box("Bang", (0, -hr * 0.88, hz + hr * 0.52), (hr * 1.10, hr * 0.22, hr * 0.18),
                   hair, bevel=0.004)
    elif s["hair"] == "short":
        bp.add_sphere("HairBack", (0, hr * 0.22, hz + 0.02), (hr * 1.26, hr * 1.22, hr * 1.24), hair, 20, 12)
        bp.add_sphere("HairTop", (0, 0, top - hr * 0.20), (hr * 1.08, hr * 1.08, hr * 0.58), hair, 20, 12)
        bp.add_box("Fringe", (0, -hr * 0.90, top - hr * 0.30), (hr * 1.42, hr * 0.24, hr * 0.28),
                   hair, bevel=hr * 0.05)
    else:
        bp.add_sphere("HairBack", (0, hr * 0.24, hz + 0.02), (hr * 1.30, hr * 1.26, hr * 1.28), hair, 20, 12)
        bp.add_sphere("HairTop", (0, 0, top - hr * 0.18), (hr * 1.10, hr * 1.10, hr * 0.58), hair, 20, 12)
        for i in range(5):
            x = (-0.55 + i * 0.275) * hr
            bp.add_sphere("Bang%d" % i, (x, -hr * 0.92, top - hr * 0.24),
                          (hr * 0.22, hr * 0.26, hr * 0.28), hair, 14, 8)
        for sx in (-1, 1):
            bp.add_sphere("Tail%dA" % sx, (sx * hr * 1.25, hr * 0.40, hz + hr * 0.02),
                          (hr * 0.36, hr * 0.36, hr * 0.52), hair, 16, 10)
            bp.add_sphere("Tail%dB" % sx, (sx * hr * 1.38, hr * 0.40, hz - hr * 0.58),
                          (hr * 0.28, hr * 0.28, hr * 0.42), hair, 16, 10)
            bp.add_cyl("Band%d" % sx, (sx * hr * 1.10, hr * 0.40, hz + hr * 0.30),
                       hr * 0.18, hr * 0.12, accent, (0, math.radians(90), 0), 10)


def build_clothes(pid, s):
    """服装轮廓：紧身人体外面套一层，64px 下靠剪影区分角色，不靠贴图细节。"""
    cloth = bp.m_of(s["cloth"])
    cloth_d = bp.m_of(s["cloth_d"])
    accent = bp.m_of(s["accent"], rough=0.55, emit=0.12)
    h = s["h"]
    if pid in ("lila", "mia"):
        # 连衣裙：腰到小腿的锥台 + 腰带
        bp.add_cone("Skirt", (0, 0, h * 0.44), h * 0.20, h * 0.135, h * 0.30, cloth,
                    verts=16, smooth=False)
        bp.add_cyl("Belt", (0, 0, h * 0.585), h * 0.145, h * 0.03, accent, verts=16)
        # 短袖
        for sx in (-1, 1):
            bp.add_sphere("Sleeve%d" % sx, (sx * h * 0.115, 0, h * 0.72),
                          (h * 0.075, h * 0.07, h * 0.075), cloth, 14, 8)
    elif pid == "orin":
        # 长外套：躯干到膝的锥台 + 立领
        bp.add_cone("Coat", (0, 0, h * 0.56), h * 0.155, h * 0.125, h * 0.36, cloth_d,
                    verts=16, smooth=False)
        bp.add_cyl("Collar", (0, 0, h * 0.79), h * 0.075, h * 0.05, accent, verts=14)
    else:
        # 旅人：短外套 + 围巾
        bp.add_cone("Jacket", (0, 0, h * 0.66), h * 0.165, h * 0.14, h * 0.24, cloth,
                    verts=16, smooth=False)
        bp.add_cyl("Scarf", (0, 0, h * 0.79), h * 0.085, h * 0.045, accent, verts=14)


def build(pid):
    s = SPECS[pid]
    obj = import_base(s["h"])
    stylize_head(obj, s)
    paint_body(obj, s)
    hz, hr = head_metrics(obj, s)
    print("[head]", pid, "z=%.3f r=%.3f" % (hz, hr))
    build_clothes(pid, s)
    build_face(hz, hr, s)
    build_hair(hz, hr, s)


def render_all(pid):
    cam = scene_setup()
    build(pid)
    bp.apply_outlines(thickness=0.020, min_size=0.10)
    for view, yaw in VIEWS:
        set_view(cam, yaw)
        bpy.context.scene.render.filepath = os.path.join(OUT_DIR, "%s_%s.png" % (pid, view))
        bpy.ops.render.render(write_still=True)
        print("[body]", pid, view)


if __name__ == "__main__":
    argv = sys.argv
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    jobs = args[:1] if args else ["lila", "orin", "mia", "player"]
    for pid in jobs:
        render_all(pid)
    print("[done] body views ->", OUT_DIR)
