# -*- coding: utf-8 -*-
# 星尘角色全身低模：Blender 建模 -> 四向正交渲染 -> Godot 合帧表
#
# 跑法（脚本 2026-11-01 迁至 Blender建模仓，产物仍落游戏工程）：
#   blender --background --python "D:/G/github/实用工具/Blender建模/stardust/build_characters.py"                # 三人四向
#   blender --background --python "D:/G/github/实用工具/Blender建模/stardust/build_characters.py" -- lila        # 单个角色
#   godot --headless --path . -s res://tools/char_sheet.gd                          # 合 256x64 帧表
#
# 产物：tools/blender/render_body/<id>_<view>.png（256x384，透明底；游戏工程内）
#       assets/sprites/characters/<id>.png（256x64 四向帧表，Godot 侧覆盖槽）
#
# 口径：
#   · 复用 build_portraits 的图元/材质/色板（同一套色，避免两套画法）
#   · 正交 3.0 世界单位高、相机 z=1.5；256x384 -> /4 -> 64x96 -> 取底部 64 行 = 64x64
#     （32 px/单位，脚底正好落在帧底边，与 PixelArt.build_character_sheet 口径一致）
#   · 四向顺序固定 下/上/左/右（与 Sprite3D.hframes=4 的 frame 索引一致）
#   · 光照随相机偏航一起转，否则背面视图全黑

import bpy
import math
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import build_portraits as bp  # noqa: E402

OUT_DIR = r"D:\G\game\games\stardust\tools\blender\render_body"
os.makedirs(OUT_DIR, exist_ok=True)

RES_X, RES_Y = 256, 384
ORTHO = 3.0
CAM_Z = 1.5
SAMPLES = 24

C_SKIN = bp.C_SKIN
C_OUTLINE = bp.C_OUTLINE
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
C_STONE = bp.hexc("8f93a8")

# 四向：名字 / 相机偏航（度，绕 Z）——0=正面(下)，180=背面(上)，-90=左侧，90=右侧
VIEWS = [("down", 0), ("up", 180), ("left", 90), ("right", -90)]


def scene_setup():
    bp.reset()
    sc = bpy.context.scene
    bp.render_output((RES_X, RES_Y), samples=SAMPLES)   # D6：输出设置单源（bp 轴）
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = ORTHO
    cam = bpy.data.objects.new("Cam", cam_data)
    cam.location = (0, -6.0, CAM_Z)
    cam.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.collection.objects.link(cam)
    sc.camera = cam
    return cam


def set_view(cam, yaw_deg):
    """相机绕世界 Z 旋转到指定偏航；灯光跟着转，保证每面受光一致。"""
    yaw = math.radians(yaw_deg)
    r = 6.0
    cam.location = (math.sin(yaw) * r, -math.cos(yaw) * r, CAM_Z)
    cam.rotation_euler = (math.radians(90), 0, yaw)
    for name, energy, ang, pitch, rel in bp.LIGHT_SPECS:   # D11：灯表单源（bp 轴）
        o = bpy.data.objects.get(name)
        if o is None:
            d = bpy.data.lights.new(name, "SUN")
            d.energy = energy
            d.angle = math.radians(ang)
            o = bpy.data.objects.new(name, d)
            bpy.context.collection.objects.link(o)
        o.rotation_euler = (math.radians(pitch), 0, math.radians(rel) + yaw)


# ---------------- 体型参数 ----------------
SPECS = {
    "lila": dict(
        h=1.65, leg=0.74, torso=0.50, head_r=0.148, shoulder=0.185,
        hair="long", hair_c=C_GOLD, hair_d=C_GOLD_D, cloth=C_ROSE, cloth_d=C_ROSE_D,
        accent=C_GOLD_L, skin=C_SKIN, skirt=True, foot=C_ROSE_D,
    ),
    "orin": dict(
        h=1.80, leg=0.82, torso=0.54, head_r=0.152, shoulder=0.205,
        hair="hood", hair_c=C_GOLD_D, hair_d=C_GOLD_D, cloth=C_BLUE, cloth_d=C_BLUE_D,
        accent=C_ICE, skin=C_SKIN, skirt=False, foot=C_BLUE_D,
    ),
    "player": dict(
        h=1.70, leg=0.78, torso=0.50, head_r=0.146, shoulder=0.195,
        hair="short", hair_c=bp.hexc("2a3550"), hair_d=bp.hexc("1a2030"), cloth=bp.hexc("3fa8a0"),
        cloth_d=bp.hexc("2d7a74"), accent=C_GOLD_L, skin=C_SKIN, skirt=False, foot=bp.hexc("2d7a74"),
    ),
    "mia": dict(
        h=1.55, leg=0.68, torso=0.46, head_r=0.145, shoulder=0.175,
        hair="twin", hair_c=C_PINK_D, hair_d=C_PINK_D, cloth=C_GOLD, cloth_d=C_GOLD_D,
        accent=C_PINK, skin=C_SKIN, skirt=True, foot=C_GOLD_D,
    ),
}


def build_body(s):
    skin = bp.m_of(s["skin"])
    cloth = bp.m_of(s["cloth"])
    cloth_d = bp.m_of(s["cloth_d"])
    accent = bp.m_of(s["accent"], rough=0.55, emit=0.12)
    leg, torso, hr = s["leg"], s["torso"], s["head_r"]
    hip = leg
    top = leg + torso

    # 脚
    for sx in (-1, 1):
        bp.add_box("Foot%d" % sx, (sx * 0.075, -0.03, 0.035), (0.10, 0.20, 0.07), bp.m_of(s["foot"]), bevel=0.015)
    # 腿（下细上粗）
    for sx in (-1, 1):
        bp.add_cone("Leg%d" % sx, (sx * 0.075, 0.0, hip * 0.5), 0.048, 0.072, hip, skin, verts=12)
    # 裙 / 长袍
    if s["skirt"]:
        bp.add_cone("Skirt", (0, 0, hip - 0.02), 0.235, 0.145, 0.30, cloth, verts=16, smooth=False)
    else:
        bp.add_cone("Coat", (0, 0, hip + 0.10), 0.225, 0.155, 0.62, cloth_d, verts=16, smooth=False)
    # 躯干
    bp.add_cone("Torso", (0, 0, hip + torso * 0.5), 0.145, 0.185, torso, cloth, verts=16, smooth=False)
    # 胸前饰线
    bp.add_box("Collar", (0, -0.145, top - 0.06), (0.20, 0.03, 0.026), accent, bevel=0.006)
    # 肩
    for sx in (-1, 1):
        bp.add_sphere("Shoulder%d" % sx, (sx * (s["shoulder"] - 0.01), 0, top - 0.035),
                      (0.075, 0.070, 0.068), cloth, 16, 10)
    # 手臂
    for sx in (-1, 1):
        bp.add_cone("Arm%d" % sx, (sx * (s["shoulder"] + 0.005), 0.0, top - 0.235),
                    0.036, 0.052, 0.40, cloth, (0, math.radians(sx * 3), 0), 12)
        bp.add_sphere("Hand%d" % sx, (sx * (s["shoulder"] + 0.022), 0.0, top - 0.445),
                      (0.040, 0.040, 0.043), skin, 12, 8)
    # 脖子
    bp.add_cyl("Neck", (0, 0, top + 0.045), 0.048, 0.10, skin, verts=12)
    # 头（蛋形收下巴）
    hz = top + 0.10 + hr
    head = bp.add_sphere("Head", (0, 0, hz), (hr, hr * 0.92, hr * 1.08), skin)
    t = head.modifiers.new("Taper", "SIMPLE_DEFORM")
    t.deform_method = "TAPER"
    t.factor = -0.26
    t.deform_axis = "Z"
    # 耳朵
    for sx in (-1, 1):
        bp.add_sphere("Ear%d" % sx, (sx * hr * 0.95, 0.0, hz - 0.01), (0.018, 0.024, 0.034), skin, 10, 6)
    return hz, hr


def build_face(hz, hr, s):
    eye = bp.m_of(C_EYE)
    white = bp.m_of(C_WHITE)
    ey = -hr * 0.90
    ex = hr * 0.40
    for sx in (-1, 1):
        bp.add_sphere("Sclera%d" % sx, (sx * ex, ey, hz + 0.008),
                      (hr * 0.20, 0.012, hr * 0.16), white, 12, 8)
        bp.add_sphere("Iris%d" % sx, (sx * ex, ey - 0.010, hz + 0.006),
                      (hr * 0.12, 0.010, hr * 0.12), eye, 12, 8)
    bp.add_sphere("Mouth", (0, ey - 0.006, hz - hr * 0.42),
                  (hr * 0.16, 0.008, hr * 0.05), bp.m_of(s["cloth_d"]), 10, 6)
    # 鼻尖：侧视轮廓的辨识点（64px 下约 1-2 像素，但没有它侧脸就是一颗球）
    bp.add_sphere("Nose", (0, ey - hr * 0.10, hz - hr * 0.14),
                  (hr * 0.10, hr * 0.10, hr * 0.09), bp.m_of(C_SKIN), 10, 6)


def build_hair(hz, hr, s):
    hair = bp.m_of(s["hair_c"])
    hair_d = bp.m_of(s["hair_d"])
    accent = bp.m_of(s["accent"], rough=0.55, emit=0.12)
    top = hz + hr * 0.78

    if s["hair"] == "long":
        bp.add_sphere("HairBack", (0, hr * 0.14, hz + 0.01), (hr * 1.12, hr * 1.02, hr * 1.18), hair, 20, 12)
        bp.add_sphere("HairTop", (0, 0, top - hr * 0.18), (hr * 1.10, hr * 1.10, hr * 0.72), hair, 20, 12)
        # 两侧长发到胸
        for sx in (-1, 1):
            bp.add_box("Lock%d" % sx, (sx * hr * 0.92, 0.01, hz - hr * 1.5),
                       (hr * 0.34, hr * 0.52, hr * 2.2), hair, bevel=hr * 0.12)
        # 刘海：一整条额前发 + 两侧斜落碎发
        bp.add_box("Fringe", (0, -hr * 0.90, top - hr * 0.30),
                   (hr * 1.55, hr * 0.30, hr * 0.42), hair, bevel=hr * 0.06)
        for sx in (-1, 1):
            bp.add_cone("Bang%d" % sx, (sx * hr * 0.78, -hr * 0.80, top - hr * 0.55),
                        hr * 0.26, hr * 0.05, hr * 0.75, hair,
                        (math.radians(-6), 0, sx * math.radians(14)), 6)
        # 星饰（贴在左侧发面）
        for ang in (0.0, math.radians(90)):
            bp.add_box("Star", (-hr * 0.72, -hr * 0.92, top - hr * 0.42),
                       (hr * 0.20, 0.006, hr * 0.055), accent, (0, ang, 0), 0.002)
    elif s["hair"] == "hood":
        hood = bp.add_sphere("Hood", (0, hr * 0.12, hz + 0.02), (hr * 1.30, hr * 1.30, hr * 1.36), bp.m_of(s["cloth"]), 20, 12)
        cut = bp.add_sphere("HoodCut", (0, -hr * 1.22, hz - 0.02), (hr * 1.05, hr * 0.95, hr * 1.05), bp.m_of(s["cloth"]), 16, 10)
        b = hood.modifiers.new("Cut", "BOOLEAN")
        b.operation = "DIFFERENCE"
        b.object = cut
        cut.hide_render = True
        cut.hide_viewport = True
        # 帽尖 + 披风肩
        bp.add_cone("HoodTip", (0, hr * 0.45, hz + hr * 1.42), hr * 0.32, 0.0, hr * 0.75, bp.m_of(s["cloth"]),
                    (math.radians(-14), 0, 0), 12)
        bp.add_box("Cape", (0, hr * 0.25, hz - hr * 2.4), (hr * 3.1, hr * 1.3, hr * 2.2), bp.m_of(s["cloth_d"]), bevel=hr * 0.3)
        bp.add_box("HoodRim", (0, -hr * 0.86, hz + hr * 0.95), (hr * 1.35, hr * 0.22, hr * 0.14), accent, bevel=0.004)
        bp.add_box("Bang", (0, -hr * 0.92, hz + hr * 0.55), (hr * 1.15, hr * 0.24, hr * 0.20), hair, bevel=0.004)
    elif s["hair"] == "short":
        bp.add_sphere("HairBack", (0, hr * 0.16, hz + 0.02), (hr * 1.10, hr * 1.08, hr * 1.14), hair, 20, 12)
        bp.add_sphere("HairTop", (0, 0, top - hr * 0.22), (hr * 1.06, hr * 1.06, hr * 0.66), hair, 20, 12)
        bp.add_box("Fringe", (0, -hr * 0.92, top - hr * 0.34), (hr * 1.45, hr * 0.26, hr * 0.34), hair, bevel=hr * 0.05)
        for sx in (-1, 1):
            bp.add_cone("Side%d" % sx, (sx * hr * 0.92, -hr * 0.55, hz + hr * 0.05),
                        hr * 0.16, hr * 0.04, hr * 0.55, hair, (0, 0, sx * math.radians(10)), 6)
    else:
        bp.add_sphere("HairBack", (0, hr * 0.20, hz + 0.01), (hr * 1.14, hr * 1.14, hr * 1.18), hair, 20, 12)
        bp.add_sphere("HairTop", (0, 0, top - hr * 0.20), (hr * 1.08, hr * 1.08, hr * 0.70), hair, 20, 12)
        # 齐刘海一排
        for i in range(5):
            x = (-0.55 + i * 0.275) * hr
            bp.add_cone("Bang%d" % i, (x, -hr * 0.95, top - hr * 0.22), hr * 0.22, hr * 0.05, hr * 0.45, hair,
                        (math.radians(-4), 0, 0), 6)
        # 双马尾
        for sx in (-1, 1):
            bp.add_sphere("Tail%dA" % sx, (sx * hr * 1.22, hr * 0.42, hz + hr * 0.02), (hr * 0.34, hr * 0.34, hr * 0.50), hair, 16, 10)
            bp.add_sphere("Tail%dB" % sx, (sx * hr * 1.34, hr * 0.42, hz - hr * 0.58), (hr * 0.26, hr * 0.26, hr * 0.40), hair, 16, 10)
            bp.add_cyl("Band%d" % sx, (sx * hr * 1.08, hr * 0.42, hz + hr * 0.30), hr * 0.18, hr * 0.12,
                       accent, (0, math.radians(90), 0), 10)


def build(pid):
    s = SPECS[pid]
    hz, hr = build_body(s)
    build_face(hz, hr, s)
    build_hair(hz, hr, s)


def render_all(pid):
    cam = scene_setup()
    build(pid)
    # 64px 帧表下描边是可读性关键：0.03 世界单位 ≈ 1px（32px/单位）
    bp.apply_outlines(thickness=0.030, min_size=0.12)
    for view, yaw in VIEWS:
        set_view(cam, yaw)
        bp.render_still(os.path.join(OUT_DIR, "%s_%s.png" % (pid, view)))   # D5：落盘单源
        print("[body]", pid, view, "yaw", yaw)


if __name__ == "__main__":
    argv = sys.argv
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    jobs = args[:1] if args else ["lila", "orin", "mia", "player"]
    for pid in jobs:
        render_all(pid)
    print("[done] body views ->", OUT_DIR)
