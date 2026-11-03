# -*- coding: utf-8 -*-
"""bapi · 环境层：清场、引擎、色彩管理、输出路径。

设计原则：能用 `bpy.data` 就不碰 `bpy.ops`。
`bpy.ops` 依赖 context，在 `-b` 下会 poll 失败；全包的 ops 调用只有四处
（`env.reset()` 清场、`shot.render()` 渲染、`shot.save_blend()` 落盘、
`shot.export_gltf()` 导出），都是数据层确实没有替代的入口，且都已实测可用。
"""

import os

import bpy

# 仓库根（BlenderAPI/ 的上一级），产物默认落在它的 out/ 下
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(ROOT, "out")


def version():
    """返回 '5.2.2 LTS' 这类字符串。"""
    return bpy.app.version_string


def reset(empty=True):
    """清空场景。empty=True 时连默认立方体/灯光/相机都不建。"""
    bpy.ops.wm.read_factory_settings(use_empty=empty)
    return bpy.context.scene


def clear_data(keep_materials=False):
    """删掉所有孤立数据块。reset 之后一般不需要，改模型时用得上。"""
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                 bpy.data.lights, bpy.data.armatures):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)
    if not keep_materials:
        for m in list(bpy.data.materials):
            if m.users == 0:
                bpy.data.materials.remove(m)


def engine(name="BLENDER_EEVEE"):
    """设置渲染引擎。5.2 实测枚举只有 BLENDER_EEVEE。"""
    sc = bpy.context.scene
    sc.render.engine = name
    return sc


def eevee(samples=48, raytracing=None):
    """EEVEE 采样与光追开关。

    注意：5.2 已无 `use_gtao`，AO 走 raytracing 或世界设置。
    """
    e = bpy.context.scene.eevee
    if hasattr(e, "taa_render_samples"):
        e.taa_render_samples = samples
    if raytracing is not None and hasattr(e, "use_raytracing"):
        e.use_raytracing = raytracing
    return e


def color_standard():
    """Standard 视图变换：二次元需要干净色阶，不要 filmic/AgX 的压缩。"""
    vs = bpy.context.scene.view_settings
    vs.view_transform = 'Standard'
    if hasattr(vs, "look"):
        vs.look = 'None'


def resolution(w, h, percent=100):
    r = bpy.context.scene.render
    r.resolution_x = w
    r.resolution_y = h
    r.resolution_percentage = percent
    r.image_settings.file_format = 'PNG'
    return r


def out_dir(path=None, create=True):
    d = path or DEFAULT_OUT
    if create:
        os.makedirs(d, exist_ok=True)
    return d


def frame(start=1, end=1):
    sc = bpy.context.scene
    sc.frame_start = start
    sc.frame_end = end
    sc.frame_set(start)
    return sc
