# -*- coding: utf-8 -*-
"""场景、灯光、相机、出图。"""
import bpy
import math
import os
from mathutils import Vector

import optio

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")

# ---------------- C 阶段灯参数（m3/m4/m5 统一从这里读，别再各自硬编码） ----------------
# C3 色阶重标定：key 70W → 49W（0.7×）→ 35W（0.5×）。原来 70W 下皮肤 p50=229.7、
# p95−p50 只有 0.3，95% 像素挤在 light 档；降 key 让 mid 档吃到样本。
KEY_ENERGY = 49.0
FILL_ENERGY = 6.0
# C4 轮廓光：55W → 80W（DESIGN §2.4.5）。实测这一档在正/侧机位不足以在
# 轮廓上形成可测亮带，见 _stageC/c_probe.py 的 rim 输出与交付总结。
RIM_ENERGY = 80.0

# T18 像素段：rim 灯方位。半径与高度沿用 C4 收口的实测位置 (-2.2, 2.0, 2.2)，
# 其余三个方位按同一半径 R=hypot(2.2,2.0)=2.974、同一高度 2.2 摆放，
# 只改方位角，避免「把灯挪远/挪高」混进方位对比里。
RIM_R = math.hypot(2.2, 2.0)
RIM_Z = 2.2
RIM_AZIMUTH = "back_left"      # 现网 default（C4 收口实测位置）
RIM_AZIMUTHS = {
    "back":       (0.0, RIM_R),
    "back_left":  (-2.2, 2.0),     # C4 收口实测位置（现网默认）
    "left":       (-RIM_R, 0.0),
    "back_right": (2.2, 2.0),
}


def stage_c_lights(key=None, fill=None, rim=None):
    """把 m3/m4/m5 的三点光统一成 C 阶段参数。返回实际生效的 (key, fill, rim)。"""
    # T18：key / rim 功率与 rim 方位都可注入；默认值 = 调用方给的值（即现网常量），
    # 没有 opt/best.json 时行为逐位不变。
    vals = {
        "key": KEY_ENERGY if key is None else key,
        "fill": FILL_ENERGY if fill is None else fill,
        "rim": RIM_ENERGY if rim is None else rim,
    }
    vals["key"] = optio.param("key_energy", vals["key"])
    vals["rim"] = optio.param("rim_energy", vals["rim"])
    az = optio.param("rim_azimuth", RIM_AZIMUTH)
    if az not in RIM_AZIMUTHS:
        az = RIM_AZIMUTH
    for name, energy in vals.items():
        ob = bpy.data.objects.get(name)
        if ob is not None:
            ob.data.energy = energy
    key_ob = bpy.data.objects.get("key")
    if key_ob is not None:
        key_ob.location = (-1.15, -2.1, 2.05)
        key_ob.data.size = 0.45
    fill_ob = bpy.data.objects.get("fill")
    if fill_ob is not None:
        fill_ob.data.size = 3.0
    rim_ob = bpy.data.objects.get("rim")
    if rim_ob is not None:
        rim_ob.data.size = 0.8   # C4：DESIGN 备选「size 0.8」，收窄光源让轮廓边更锐
        # C4 收口：rim 原来在人物**正后方** (0.8, 2.4, 2.0)，正/侧机位看到的是
        # 人物正面，轮廓边缘是掠射面 —— 实测亮带 0px。这里移到**左后上方**，
        # 让朝向相机的左侧轮廓能被照亮（验收对象改为深色区域：头发/藏青裙）。
        rx, ry = RIM_AZIMUTHS[az]
        rim_ob.location = (rx, ry, RIM_Z)
        look_at(rim_ob, (0.0, 0.0, 1.20))
    print(f"[lights] key={vals['key']}W fill={vals['fill']}W rim={vals['rim']}W")
    return vals["key"], vals["fill"], vals["rim"]


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'
    sc.unit_settings.system = 'METRIC'
    return sc


def ensure_out():
    os.makedirs(OUT, exist_ok=True)
    return OUT


def world(color=(0.055, 0.058, 0.065), strength=1.0):
    sc = bpy.context.scene
    w = bpy.data.worlds.new("W") if not sc.world else sc.world
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*color, 1.0)
    bg.inputs[1].default_value = strength


def floor(size=12.0, color=(0.16, 0.16, 0.17)):
    me = bpy.data.meshes.new("floor")
    s = size / 2
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    me.update()
    ob = bpy.data.objects.new("floor", me)
    bpy.context.collection.objects.link(ob)
    mat = bpy.data.materials.new("floor_mat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = 0.9
    ob.data.materials.append(mat)
    return ob


def area_light(name, loc, target, energy=200.0, size=1.5, color=(1, 1, 1)):
    d = bpy.data.lights.new(name, 'AREA')
    d.energy = energy
    d.size = size
    d.color = color
    ob = bpy.data.objects.new(name, d)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    look_at(ob, target)
    return ob


def look_at(ob, target):
    d = (Vector(target) - ob.location)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def camera(name, loc, target, ortho_scale=None, lens=85.0):
    cd = bpy.data.cameras.new(name)
    if ortho_scale:
        cd.type = 'ORTHO'
        cd.ortho_scale = ortho_scale
    else:
        cd.lens = lens
    ob = bpy.data.objects.new(name, cd)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    look_at(ob, target)
    return ob


def setup_studio():
    world(color=(0.030, 0.032, 0.038), strength=1.0)
    floor(color=(0.12, 0.12, 0.13))
    area_light("key", (-1.6, -2.0, 2.3), (0, 0, 1.15), energy=140, size=1.8,
               color=(1.0, 0.97, 0.93))
    area_light("fill", (2.2, -1.6, 1.4), (0, 0, 1.0), energy=45, size=2.4,
               color=(0.86, 0.92, 1.0))
    area_light("rim", (0.8, 2.4, 2.0), (0, 0, 1.25), energy=160, size=1.2,
               color=(0.85, 0.92, 1.0))


def set_res(w, h, samples=48):
    sc = bpy.context.scene
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    if hasattr(sc, "eevee"):
        sc.eevee.taa_render_samples = samples


def render(cam, filename):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.filepath = os.path.join(ensure_out(), filename)
    bpy.ops.render.render(write_still=True)
    print(f"[render] {sc.render.filepath}")
    return sc.render.filepath


def clay(ob, color=(0.52, 0.50, 0.49), rough=0.62):
    mat = bpy.data.materials.new("clay")
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    ob.data.materials.append(mat)
    return mat


def turnaround(prefix, center_z=0.85, dist=3.4, ortho=1.78, res=(620, 900),
               views=(("front", 0), ("side", 90), ("back", 180), ("q34", 35))):
    """环绕出图。角度 0 = 正面（相机在 -Y）。"""
    sc = bpy.context.scene
    set_res(*res)
    paths = []
    for name, deg in views:
        a = math.radians(deg)
        loc = (math.sin(a) * dist, -math.cos(a) * dist, center_z + 0.12)
        cam = camera(f"cam_{name}", loc, (0, 0, center_z), ortho_scale=ortho)
        paths.append(render(cam, f"{prefix}_{name}.png"))
        bpy.data.objects.remove(cam, do_unlink=True)
    return paths
