# -*- coding: utf-8 -*-
"""bapi · 拍摄层：世界、地面、灯光、正交/透视机位、渲染、环绕。

约定（沿用主线工程）：**Z 轴向上，-Y 是正面**。所以正面机位在 -Y 侧，
看向 +Y；`angle=0` 即正脸。

机位写死、可复用，是「仔细」的物理前提：同一机位两版之间才能直接叠图
对比。随手改机位，等于每次都在新的坐标系里判断。
"""

import math
import os

import bpy
from mathutils import Vector

from . import mat as matmod
from . import mesh as meshmod
from . import obj as objmod
from . import env as envmod


# ---------------------------------------------------------------- 世界与地面

def world(color=(0.035, 0.037, 0.045), strength=1.0, name="bapi_world"):
    """设世界背景。渲染剪影时把 color 设成纯黑、strength=0。"""
    w = bpy.data.worlds.get(name) or bpy.data.worlds.new(name)
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes.get("Background")
    if bg is None:
        bg = nt.nodes.new("ShaderNodeBackground")
        out = nt.nodes.get("World Output") or nt.nodes.new("ShaderNodeOutputWorld")
        nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    matmod.socket_set(bg.inputs["Color"], color)
    bg.inputs["Strength"].default_value = strength
    return w


def floor(size=6.0, color=(0.22, 0.22, 0.24), z=0.0, name="floor"):
    """一块方形地面。放脚下让接触阴影可见——没有地面的模型看起来是飘的。"""
    h = size / 2.0
    verts = [(-h, -h, z), (h, -h, z), (h, h, z), (-h, h, z)]
    ob = meshmod.from_verts_faces(verts, [(0, 1, 2, 3)], name, smooth=False)
    m = matmod.principled("floor_mat", base_color=color, roughness=0.85)
    matmod.assign(ob, m)
    return ob


# ---------------------------------------------------------------- 灯光

def look_at(ob, target):
    """让对象的 -Z 指向 target（相机/灯光的默认朝向）。"""
    loc = Vector(ob.location)
    d = Vector(target) - loc
    if d.length < 1e-9:
        return ob
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return ob


def area(name="area", loc=(2.0, -3.0, 3.0), target=(0.0, 0.0, 1.0),
         energy=300.0, size=2.0, color=(1.0, 0.97, 0.92), shape='SQUARE'):
    """面光源。size 越大影子越软。"""
    ld = bpy.data.lights.new(name, 'AREA')
    ld.energy = energy
    ld.shape = shape
    ld.size = size
    ld.color = color[:3]
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    objmod.link(ob)
    look_at(ob, target)
    return ob


def sun(name="sun", target=(0.0, 0.0, 1.0), direction=(-0.4, 0.6, -1.0),
        energy=3.0, angle=0.2, color=(1.0, 0.98, 0.95)):
    """平行光。direction 是光的传播方向（从光源射向场景）。"""
    ld = bpy.data.lights.new(name, 'SUN')
    ld.energy = energy
    ld.angle = angle
    ld.color = color[:3]
    ob = bpy.data.objects.new(name, ld)
    ob.location = Vector(target) - Vector(direction).normalized() * 5.0
    objmod.link(ob)
    look_at(ob, target)
    return ob


def three_point(target=(0.0, 0.0, 1.0), scale=1.0, key=300.0, fill=80.0, rim=200.0):
    """三点布光：主光(-Y 偏右) + 补光(-Y 偏左) + 轮廓光(+Y 后方)。

    返回 (key, fill, rim) 三个灯对象，方便后续微调。
    """
    k = area("key", loc=(1.6 * scale, -3.0 * scale, 2.6 * scale), target=target,
             energy=key, size=2.2 * scale, color=(1.0, 0.97, 0.92))
    f = area("fill", loc=(-2.2 * scale, -2.2 * scale, 1.4 * scale), target=target,
             energy=fill, size=3.0 * scale, color=(0.85, 0.9, 1.0))
    r = area("rim", loc=(-0.6 * scale, 3.0 * scale, 2.2 * scale), target=target,
             energy=rim, size=1.6 * scale, color=(1.0, 0.95, 0.88))
    return k, f, r


# ---------------------------------------------------------------- 相机

def _camera(name, loc, target, ortho_scale=None, lens=50.0):
    cd = bpy.data.cameras.new(name)
    if ortho_scale is not None:
        cd.type = 'ORTHO'
        cd.ortho_scale = ortho_scale
    else:
        cd.type = 'PERSP'
        cd.lens = lens
    ob = bpy.data.objects.new(name, cd)
    ob.location = loc
    objmod.link(ob)
    look_at(ob, target)
    return ob


def camera_ortho(name="cam_ortho", target=(0.0, 0.0, 0.9), angle=0.0,
                 distance=4.0, scale=1.9, height=None):
    """正交机位。angle 单位度，0=正面(-Y)，90=右侧(+X)，180=背面(+Y)。

    正交渲染没有透视收缩，两个版本可以直接叠图 diff——做形状核对时
    比透视机位可靠得多。
    """
    a = math.radians(angle)
    t = Vector(target) if height is None else Vector((target[0], target[1], height))
    loc = Vector((t.x + distance * math.sin(a),
                  t.y - distance * math.cos(a),
                  t.z))
    return _camera(name, loc, t, ortho_scale=scale)


def camera_persp(name="cam_persp", target=(0.0, 0.0, 0.9), angle=0.0,
                 distance=4.0, lens=85.0, height=None):
    """透视机位。人像用 85mm 以上，短焦会把人脸拉变形。"""
    a = math.radians(angle)
    t = Vector(target) if height is None else Vector((target[0], target[1], height))
    loc = Vector((t.x + distance * math.sin(a),
                  t.y - distance * math.cos(a),
                  t.z))
    return _camera(name, loc, t, lens=lens)


def closeup(name, center, scale=0.15, angle=0.0, distance=2.0, ortho=True):
    """部位特写。center 是世界坐标的点，scale 是正交宽度（米）。

    例：眼睛特写 scale=0.06（6cm 视野）、鼻子 0.05、整头 0.28。
    512×512 下 6cm 视野 ≈ 0.12mm/px，上眼睑 3mm 的厚度差能看清。
    """
    c = Vector(center)
    if ortho:
        return camera_ortho(name, target=c, angle=angle,
                            distance=distance, scale=scale)
    return camera_persp(name, target=c, angle=angle, distance=distance,
                        lens=100.0)


# ---------------------------------------------------------------- 渲染

def setup(w=800, h=1000, samples=32, transparent=False, view='Standard'):
    """一次把渲染设置调好：分辨率、采样、色彩管理、透明背景。"""
    envmod.resolution(w, h)
    envmod.engine("BLENDER_EEVEE")
    envmod.eevee(samples=samples)
    sc = bpy.context.scene
    sc.view_settings.view_transform = view
    sc.render.film_transparent = transparent
    sc.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'
    return sc


def render(path, cam=None, w=None, h=None, samples=None, transparent=None):
    """渲染一帧并写盘。返回 (路径, 字节数)。

    必须用 ops——`bpy.ops.render.render` 没有数据层替代；`-b --factory-startup`
    下实测稳定（selftest 连跑 4 张 turnaround 全部落盘）。
    """
    sc = bpy.context.scene
    if cam is not None:
        sc.camera = cam
    if sc.camera is None:
        raise RuntimeError("render: 场景里没有相机")
    if w or h:
        sc.render.resolution_x = w or sc.render.resolution_x
        sc.render.resolution_y = h or sc.render.resolution_y
    if samples:
        sc.eevee.taa_render_samples = samples
    if transparent is not None:
        sc.render.film_transparent = transparent

    envmod.out_dir(os.path.dirname(os.path.abspath(path)))
    sc.render.filepath = os.path.abspath(path)
    bpy.ops.render.render(write_still=True)

    size = os.path.getsize(path) if os.path.exists(path) else 0
    return path, size


def turnaround(prefix, target=(0.0, 0.0, 0.9), angles=(0, 90, 180, 270),
               w=600, h=900, scale=1.9, samples=32, out_dir=None):
    """固定高度、固定正交尺度，绕 Z 转一圈。

    同一组参数下重跑，四张图可以逐像素叠差——这是判断「这轮改动到底
    动了哪里」最直接的手段。
    """
    d = out_dir or envmod.out_dir()
    paths = []
    setup(w, h, samples)
    for a in angles:
        cam = camera_ortho("cam_turn_%d" % a, target=target, angle=a,
                           distance=4.0, scale=scale)
        p, _ = render(os.path.join(d, "%s_%03d.png" % (prefix, a)), cam)
        paths.append(p)
    return paths


# ---------------------------------------------------------------- 落盘

def save_blend(path):
    """另存 .blend。会改变当前文件的路径。"""
    envmod.out_dir(os.path.dirname(os.path.abspath(path)))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(path))
    return path


def export_gltf(path, yup=True, apply_modifiers=True, selection_only=False):
    """导出 glTF 2.0（.glb）。

    坑：glTF 不认 toon / Shader to RGB 这类节点树，导出后材质会退化。
    需要「能在外部编辑器里正确显示」时，先把材质换成 Principled。
    """
    envmod.out_dir(os.path.dirname(os.path.abspath(path)))
    bpy.ops.export_scene.gltf(
        filepath=os.path.abspath(path),
        export_format='GLB',
        export_yup=yup,
        export_apply=apply_modifiers,
        use_selection=selection_only,
    )
    return path


def render_views(prefix, shots, out_dir=None, w=512, h=512, samples=32):
    """批量出图。shots 是 [(名字, 相机), ...] 或 [(名字, 相机, w, h), ...]。"""
    d = out_dir or envmod.out_dir()
    out = []
    setup(w, h, samples)
    for item in shots:
        name, cam = item[0], item[1]
        iw = item[2] if len(item) > 2 else w
        ih = item[3] if len(item) > 3 else h
        p, n = render(os.path.join(d, "%s_%s.png" % (prefix, name)), cam,
                      w=iw, h=ih)
        out.append((name, p, n))
    return out
