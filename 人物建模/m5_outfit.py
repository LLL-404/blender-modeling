# -*- coding: utf-8 -*-
"""M5 第一步：服装上身验收。"""
import bpy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import shots
import look
import head as headmod
import body as bodymod
import hair as hairmod
import outfit as outfitmod
from meshkit import dump_stats

shots.reset()
shots.setup_studio()
shots.world(color=(0.035, 0.045, 0.070), strength=1.0)
shots.stage_c_lights()   # C3/C4：key 49W（70×0.7）、rim 80W，见 shots.py 常量
sc = bpy.context.scene
sc.view_settings.view_transform = 'Standard'
sc.view_settings.look = 'None'

M = look.set_all()
h = headmod.build(M)
look.flatten_face(h)
b = bodymod.build()
b.data.materials.append(M["skin"])
look.bind_hands(M)          # C2：Hands 接进 skin toon
hair = hairmod.build(M)
cloth = outfitmod.build(M)
dump_stats(h)
dump_stats(hair)
dump_stats(cloth)

# C1 描边（Body/Head/Hands/Hair/Outfit 全挂，厚度按视图换算成恒定像素宽）
OL = look.outline_mat()
_ol_objs, _ol_mods = [], []
for ob in (h, b, bpy.data.objects.get("Hands"), hair, cloth):
    if ob is not None:
        _ol_objs.append(ob)
        _ol_mods.append(look.add_outline(ob, OL, thickness=0.008))


def _set_outline(ortho, res_y):
    look.set_outline_px(_ol_objs, _ol_mods, ortho, res_y, base_px=3.5)


look.bloom(threshold=0.88, size=8)

shots.set_res(620, 780)
# A6 后头骨中心 1.4956；正视相机压到完全水平（c_probe 反投影要用）。
for name, loc in (("front", (0, -2.0, 1.4956)), ("q34", (1.05, -1.72, 1.55))):
    cam = shots.camera("c" + name, loc, (0, 0, 1.4956), ortho_scale=0.32)
    _set_outline(0.32, 780)
    shots.render(cam, f"m5_face_{name}.png")

shots.set_res(560, 900)
for name, loc in (("front", (0, -3.4, 0.86)), ("q34", (2.3, -2.5, 1.0)),
                  ("side", (3.4, 0.0, 0.86))):
    cam = shots.camera("b" + name, loc, (0, 0, 0.86), ortho_scale=1.80)
    _set_outline(1.80, 900)
    shots.render(cam, f"m5_body_{name}.png")

import sheet
out = shots.ensure_out()
sheet.sheet(out, ["m5_face_front.png", "m5_face_q34.png"], "m5_face.png")
sheet.sheet(out, ["m5_body_front.png", "m5_body_q34.png", "m5_body_side.png"], "m5_body.png")
print("[done] M5 outfit")