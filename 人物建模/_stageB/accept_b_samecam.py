# -*- coding: utf-8 -*-
"""B4 归因专用：四个姿势用**同一台相机**（rest 的机位）重渲，隔离「换机位」这一变量。

只写 _stageB/tmp/，绝不碰 out/m5_pose_*.png（那是共享产物）与 美女.blend。
运行：
  "D:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
      --python _stageB/accept_b_samecam.py
"""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import shots
import look
import rig
import head as headmod
import body as bodymod
import hair as hairmod
import outfit as outfitmod

TMP = os.path.join(HERE, "_stageB", "tmp")
os.makedirs(TMP, exist_ok=True)

shots.reset()
shots.setup_studio()
shots.world(color=(0.035, 0.045, 0.070), strength=1.0)
for name, energy, size in (("key", 70, 0.45), ("fill", 6, 3.0), ("rim", 55, 1.0)):
    ob = bpy.data.objects[name]
    ob.data.energy = energy
    ob.data.size = size
bpy.data.objects["key"].location = (-1.15, -2.1, 2.05)
sc = bpy.context.scene
sc.view_settings.view_transform = 'Standard'
sc.view_settings.look = 'None'

M = look.set_all()
h = headmod.build(M)
look.flatten_face(h)
b = bodymod.build()
b.data.materials.append(M["skin"])
hair = hairmod.build(M)
cloth = outfitmod.build(M)
arm = rig.build_armature()
hands = bpy.data.objects.get("Hands")
rig.bind_all(b, cloth, h, hair, hands, arm, side_lock=True)

look.bloom(threshold=0.88, size=8)
shots.set_res(560, 900)
# 唯一相机 = rest 机位（与 m5_rig 的 rest 视图完全一致）
cam = shots.camera("cam_fixed", (2.3, -2.5, 1.0), (0, 0, 0.86), ortho_scale=1.85)
sc.camera = cam

for name in ("rest", "wave", "walk", "reach"):
    rig.apply_pose(arm, name)
    sc.render.filepath = os.path.join(TMP, f"samecam_{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"[samecam] saved {sc.render.filepath}")

print("[samecam] done")