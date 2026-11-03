# -*- coding: utf-8 -*-
"""blender-rig 共享层（D1-D6 抽取，2026-11-03）。

收编 preview_anim.py / stress_test.py 的近克隆段，并承接 rig_buildings.py 的
清场与顶点极值（两者保留原函数签名，内部转调本模块）：
  D1 工厂清场 reset_scene          D2 EEVEE 引擎回退 pick_engine
  D3 世界包围盒 world_bounds       D4 按包围盒架 TRACK_TO 相机 frame_on_bounds
  D5 渲染落盘 render_still         D6 渲染输出设置 setup_output
数值 = 抽取前各脚本字面值，逐位未动。灯表/世界色不在 D1-D6 范围，仍在各脚本内。
"""
import bpy
from mathutils import Vector

# D6：预览出图规格（preview_anim / stress_test 同值）
PREVIEW_RES = (560, 560)
PREVIEW_FORMAT = "PNG"
# D2：引擎回退列表。首位 = 两脚本抽取前的直赋值 'BLENDER_EEVEE'（当前 Blender 5.2
# 上语义正确），回退只在其不可用时兜底，happy path 行为不变。
ENGINE_PREF = ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH")
# D4：机位乘子（preview_anim 现值 zoom=3.6、(0.55, 1.0, 0.35)；stress_test 用
# offset=(0.55, 1.0, 0.30) × zoom=4.0 = 抽取前字面 (2.2, -4.0, 1.2)，见各自调用点）
CAM_OFFSET = (0.55, 1.0, 0.35)
CAM_ZOOM = 3.6


def pick_engine(pref=ENGINE_PREF):
    """D2：按回退列表挑第一个可用的渲染引擎，返回引擎名（全不可用返回 None）。"""
    sc = bpy.context.scene
    for eng in pref:
        try:
            sc.render.engine = eng
            return eng
        except Exception:
            continue
    return None


def setup_output(res, fmt=PREVIEW_FORMAT, samples=None):
    """D6：分辨率/格式输出设置。res=(w, h)；返回 Scene。"""
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.image_settings.file_format = fmt
    if samples is not None:
        try:
            sc.eevee.taa_render_samples = samples
        except Exception:
            pass
    return sc


def reset_scene(res=None, fmt=PREVIEW_FORMAT, engine_pref=ENGINE_PREF, fps=None):
    """D1：工厂清场（顺走 D2 引擎回退 + D6 输出设置 + fps）。返回 Scene。

    res=None / engine_pref=() 时跳过对应步骤——rig_buildings 的清场即此用法
    （它抽取前就不动引擎与分辨率，只设 fps）。
    """
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    if engine_pref:
        pick_engine(engine_pref)
    if res is not None:
        setup_output(res, fmt=fmt)
    if fps is not None:
        sc.render.fps = fps
    return sc


def world_bounds(objs):
    """D3：世界包围盒（bound_box 八角），返回 (lo, hi) 两个 Vector。"""
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector((min(lo[i], w[i]) for i in range(3)))
            hi = Vector((max(hi[i], w[i]) for i in range(3)))
    return lo, hi


def world_z_range(objs):
    """顶点级世界 z 极值（rig_buildings 蒙皮分带用；比 world_bounds 精确，勿混用）。"""
    zs = []
    for o in objs:
        mw = o.matrix_world
        for v in o.data.vertices:
            zs.append((mw @ v.co).z)
    return min(zs), max(zs)


def frame_on_bounds(center, radius, offset=CAM_OFFSET, zoom=CAM_ZOOM, target=None):
    """D4：按包围盒中心/半径架 TRACK_TO 相机并设为场景相机，返回 Cam 对象。

    相机位置 = center + radius*zoom*(offset[0], -offset[1], offset[2])。
    target=None 时自动建 "T" 空物体盯 center；两脚本的灯也要 TRACK_TO 该空物体，
    故可自建后经 target= 传入（见 preview_anim / stress_test）。
    """
    r = radius
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    bpy.context.collection.objects.link(cam)
    cam.location = center + Vector((r * zoom * offset[0], -r * zoom * offset[1],
                                    r * zoom * offset[2]))
    if target is None:
        target = bpy.data.objects.new("T", None)
        bpy.context.collection.objects.link(target)
        target.location = center
    con = cam.constraints.new(type='TRACK_TO')
    con.target = target
    con.track_axis = 'TRACK_NEGATIVE_Z'
    con.up_axis = 'UP_Y'
    bpy.context.scene.camera = cam
    return cam


def render_still(filepath):
    """D5：渲染落盘（filepath + write_still），返回写入路径。"""
    sc = bpy.context.scene
    sc.render.filepath = filepath
    bpy.ops.render.render(write_still=True)
    return filepath
