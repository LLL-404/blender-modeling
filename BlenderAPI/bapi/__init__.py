# -*- coding: utf-8 -*-
"""bapi —— headless Blender 程序化建模封装层。

设计原则
--------
1. **能用 `bpy.data` 就不碰 `bpy.ops`。**
   ops 依赖 context，在 `-b` 下会 poll 失败或静默返回 `{'CANCELLED'}`。
   整个包里只有四处用 ops：`env.reset()`、`shot.render()`、`shot.save_blend()`、
   `shot.export_gltf()`，都实测可用（其余全部走 `bpy.data` / `bmesh`）。
2. **参数不存在就报错，不静默忽略。**
   socket 名、修改器属性都随版本漂移；写错了要能立刻看见。
3. **每个封装都能被断言。**
   返回位移量、粗糙度、面数这类可测的值，而不是只返回对象本身。

用法
----
    import sys
    sys.path.insert(0, r"...\\BlenderAPI")
    import bapi

    bapi.env.reset()
    ob = bapi.mesh.sphere(0.5, name="head")
    bapi.mod.subsurf(ob, 2)
    bapi.mat.assign(ob, bapi.mat.principled("skin", base_color=(0.9, 0.7, 0.6)))

模块
----
    env     清场、引擎、色彩管理、输出路径
    obj     创建/链接/合并/变换/包围盒
    mesh    截面放样、管状扫掠、球柱面体、法线修复
    mod     修改器、烘焙进网格、体素重网格
    mat     Principled 短名映射、sRGB、诊断材质、三渲二
    shot    世界/地面/灯光/机位/渲染/环绕
    sculpt  headless 下的「笔刷」：位移场、平滑、压平、收拢
"""

__version__ = "0.1.0"

from . import env      # noqa: F401
from . import obj      # noqa: F401
from . import mesh     # noqa: F401
from . import mod      # noqa: F401
from . import mat      # noqa: F401
from . import shot     # noqa: F401
from . import sculpt   # noqa: F401

__all__ = ["env", "obj", "mesh", "mod", "mat", "shot", "sculpt", "__version__"]


def info():
    """一行环境摘要，脚本开头打出来便于事后对账。"""
    import bpy
    sc = bpy.context.scene
    return {
        "bapi": __version__,
        "blender": bpy.app.version_string,
        "engine": sc.render.engine,
        "objects": len(bpy.data.objects),
        "binary": bpy.app.binary_path,
    }
