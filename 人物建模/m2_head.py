# -*- coding: utf-8 -*-
"""M2：头 + 五官，头像是验收点。"""
import bpy
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import cfg
import shots
import mats
import head as headmod
import body as bodymod
from meshkit import dump_stats, join

shots.reset()
shots.setup_studio()

M = mats.set_all()
h = headmod.build(M)
dump_stats(h)

b = bodymod.build()
b.data.materials.append(M["skin"])

sc = bpy.context.scene
sc.render.film_transparent = False

# 头部特写。A6 后头骨的 z 区间是 [1.3712, 1.6200]（中心 1.4956），
# 相机目标从原来的 1.502 下移到 1.4956，否则脸会偏出画面下缘。
shots.set_res(600, 760)
cams = {
    "face_front": shots.camera("c1", (0, -2.0, 1.499), (0, 0, 1.4956), ortho_scale=0.30),
    "face_34": shots.camera("c2", (1.05, -1.72, 1.55), (0, 0, 1.4956), ortho_scale=0.30),
    "face_side": shots.camera("c3", (2.0, 0.0, 1.499), (0, 0, 1.4956), ortho_scale=0.30),
}
for name, cam in cams.items():
    shots.render(cam, f"m2_{name}.png")

# 全身
shots.set_res(560, 900)
cam = shots.camera("c4", (0, -3.4, 0.97), (0, 0, 0.85), ortho_scale=1.78)
shots.render(cam, "m2_body.png")
cam2 = shots.camera("c5", (2.3, -2.5, 1.0), (0, 0, 0.86), ortho_scale=1.78)
shots.render(cam2, "m2_body_q34.png")

import sheet
sheet.sheet(shots.ensure_out(),
            ["m2_face_front.png", "m2_face_34.png", "m2_face_side.png"], "m2_face.png")
sheet.sheet(shots.ensure_out(),
            ["m2_body.png", "m2_body_q34.png"], "m2_full.png")
print("[done]")
