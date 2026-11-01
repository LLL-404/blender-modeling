# -*- coding: utf-8 -*-
"""M4：头发验收。发帽/后发片/刘海/侧发/呆毛。"""
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
dump_stats(h)
b = bodymod.build()
b.data.materials.append(M["skin"])
look.bind_hands(M)          # C2：Hands 接进 skin toon
hair = hairmod.build(M)
dump_stats(hair)

# C1 描边（构造与 m3_look 完全一致，厚度按视图换算成恒定像素宽）
OL = look.outline_mat()
_ol_objs, _ol_mods = [], []
for ob in (h, b, bpy.data.objects.get("Hands"), hair):
    if ob is not None:
        _ol_objs.append(ob)
        _ol_mods.append(look.add_outline(ob, OL, thickness=0.008))


def _set_outline(ortho, res_y):
    look.set_outline_px(_ol_objs, _ol_mods, ortho, res_y, base_px=3.5)


look.bloom(threshold=0.88, size=8)

shots.set_res(620, 780)
# A6 后头骨中心 1.4956；正视/侧视相机压到完全水平，c_probe 才能精确反投影。
cams = {
    "front": shots.camera("c1", (0, -2.0, 1.4956), (0, 0, 1.4956), ortho_scale=0.32),
    "q34": shots.camera("c2", (1.05, -1.72, 1.55), (0, 0, 1.4956), ortho_scale=0.32),
    "side": shots.camera("c3", (2.0, 0.0, 1.4956), (0, 0, 1.4956), ortho_scale=0.32),
    # D2 专用：后发束是沿 x 并排的纵向条，侧面机位（沿 x 看）会把 7 条互相
    # 遮住，量不到沟壑；必须从背后正对看。ortho 0.42 覆盖后脑 208mm。
    "back": shots.camera("c6", (0, 2.2, 1.45), (0, 0, 1.40), ortho_scale=0.42),
}
for name, cam in cams.items():
    _set_outline(0.42 if name == "back" else 0.32, 780)
    shots.render(cam, f"m4_face_{name}.png")

shots.set_res(560, 820)
cam = shots.camera("c4", (0, -3.4, 1.10), (0, 0, 1.02), ortho_scale=1.02)
_set_outline(1.02, 820)
shots.render(cam, "m4_upper.png")

shots.set_res(560, 900)
cam = shots.camera("c5", (2.3, -2.5, 1.0), (0, 0, 0.86), ortho_scale=1.78)
_set_outline(1.78, 900)
shots.render(cam, "m4_body_q34.png")

import sheet
out = shots.ensure_out()
sheet.sheet(out, ["m4_face_front.png", "m4_face_q34.png", "m4_face_side.png"], "m4_face.png")
sheet.sheet(out, ["m4_upper.png", "m4_body_q34.png"], "m4_body.png")
print("[done] M4")