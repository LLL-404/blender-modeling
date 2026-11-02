# -*- coding: utf-8 -*-
# 生成一具 MPFB 基础人体并导出 OBJ（供 build_characters_mpfb.py 使用）。
# 跑法：blender --background --python "D:/G/github/实用工具/Blender建模/stardust/gen_human.py"
# 产物：tools/blender/mpfb/human.obj（约 1.9MB，19k 顶点）
#
# 口径：MPFB 以扩展方式安装（Blender 5.2 的 addons 目录不再接受 legacy 插件），
#      模块名 bl_ext.user_default.mpfb；宏参数走 HumanService.create_human。

import bpy
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mpfb", "human.obj")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")
print("[mpfb] addon enabled")

from bl_ext.user_default.mpfb.services.humanservice import HumanService  # noqa: E402

macro = {
    "gender": 0.5, "age": 0.3, "muscle": 0.45, "weight": 0.45,
    "proportions": 0.5, "height": 0.5, "cupsize": 0.45, "firmness": 0.5,
    "race": {"asian": 0.6, "caucasian": 0.3, "african": 0.1},
}
obj = HumanService.create_human(macro_detail_dict=macro, scale=0.1)
print("[mpfb] human verts", len(obj.data.vertices), "dims", tuple(round(v, 3) for v in obj.dimensions))

bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.wm.obj_export(filepath=OUT, export_materials=False, export_selected_objects=True)
print("[mpfb] exported", OUT, os.path.getsize(OUT))
