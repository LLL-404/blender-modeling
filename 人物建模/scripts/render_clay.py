# -*- coding: utf-8 -*-
"""白模几何证据：无描边、无 bloom、无 alpha 的中性灰渲染。

为什么必须单独出（2026-11-05）
----------------------------
彩渲的 3.5px 黑描边会盖住轮廓缺口，三渲二硬色阶会盖住表面起伏，
alpha 发片会盖住头骨与耳朵。判几何形状不能看彩渲。
`m1_body.py` 是唯一用了 clay() 的入口；face/hair/outfit 此前全是彩渲。
本脚本给头脸部位补四张白模图，作为 L2 合同的几何证据。

用法（项目根下）：
    "D:/Program Files/Blender Foundation/Blender 5.2/blender.exe" \
        -b --factory-startup --python-exit-code 1 --python scripts/render_clay.py

产物：out/clay_face_front.png / _side / _34 / _eye_closeup
"""
import math
import os
import sys

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "lib"))

import head as headmod
import mats as matsmod
import shots

bpy.ops.wm.read_factory_settings(use_empty=True)
shots.setup_studio()
shots.world(color=(0.035, 0.045, 0.070), strength=1.0)

M = matsmod.set_all()
h = headmod.build(M)

# 中性灰：一个材质覆盖所有网格；线稿对象不参与几何复核，隐藏。
clay = bpy.data.materials.new("clay_review")
clay.use_nodes = True
p = clay.node_tree.nodes["Principled BSDF"]
p.inputs["Base Color"].default_value = (0.52, 0.50, 0.49, 1.0)
p.inputs["Roughness"].default_value = 0.62
for ob in bpy.data.objects:
    if ob.type != 'MESH':
        continue
    if ob.name.startswith("FaceLines"):
        ob.hide_render = True
        continue
    ob.data.materials.clear()
    ob.data.materials.append(clay)

sc = bpy.context.scene
sc.render.film_transparent = False
sc.view_settings.view_transform = 'Standard'
sc.view_settings.look = 'None'

eye_z = headmod.EYE_Z
views = [
    ("front", (0.0, -2.0, eye_z), (0.0, 0.0, eye_z - 0.02), 0.30, 620, 780),
    ("side", (2.0, 0.0, eye_z), (0.0, 0.0, eye_z - 0.02), 0.30, 620, 780),
    ("34", (1.15, -1.65, eye_z + 0.01), (0.0, 0.0, eye_z - 0.02), 0.30, 620, 780),
    ("eye_closeup", (0.0, -2.0, eye_z), (0.0, 0.0, eye_z), 0.105, 760, 480),
]

for name, loc, tgt, ortho, w, hgt in views:
    shots.set_res(w, hgt)
    cam = shots.camera("clay_" + name, loc, tgt, ortho_scale=ortho)
    shots.render(cam, "clay_face_%s.png" % name)
    print("[clay] %-12s ortho=%.3f res=%dx%d" % (name, ortho, w, hgt))

print("[clay] done -> out/clay_face_*.png")
