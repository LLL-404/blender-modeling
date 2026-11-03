# -*- coding: utf-8 -*-
# 星尘道具 glb 导出（HD-2D 化）：从 stardust_props.blend 逐道具导出游戏用模型。
# 产物：assets/models/<name>.glb（1 Blender 单位=1 格；Y-up 由导出器转换）
# 跑法：blender --background stardust_props.blend --python export_props_glb.py
# 约定：只导不透明本体；Shadow_*/scorch 地贴装饰不导（3D 世界有真实阴影，半透明地贴会穿帮）。
import bpy
import os

GAME = os.environ.get("STARDUST_DIR", r"D:\G\game\games\stardust")
OUT_DIR = os.path.join(GAME, "assets", "models")
os.makedirs(OUT_DIR, exist_ok=True)

# 道具 -> 本体对象名前缀（与 build_props.py 命名对齐；Shadow_*/scorch 一律不导）
PROPS = {
    "observatory": ["obs_"],
    "ship": ["ship_"],
    "stall": ["stall_"],
    "lamp": ["lamp_"],
}


def set_vis(prefixes):
    for o in bpy.context.scene.objects:
        vis = any(o.name.startswith(p) for p in prefixes)
        o.hide_render = not vis
        o.hide_viewport = not vis
        o.hide_set(not vis) if hasattr(o, "hide_set") else None


def main():
    for name, prefixes in PROPS.items():
        set_vis(prefixes)
        # 仅选中本体参与导出
        bpy.ops.object.select_all(action="DESELECT")
        count = 0
        for o in bpy.context.scene.objects:
            if not o.hide_render and o.type == "MESH":
                o.select_set(True)
                count += 1
        path = os.path.join(OUT_DIR, name + ".glb")
        bpy.ops.export_scene.gltf(filepath=path, use_selection=True, export_format="GLB", export_apply=True)
        print("[exported]", name, "meshes=", count, "->", path)
    print("[done] assets/models")


main()
