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
# 机位单源：数值读 shots.VIEWS（D15），勿在本文件改数。
v = shots.VIEWS["m2_face_front"]
shots.set_res(v["w"], v["h"])
cams = {}
for name, cid in (("face_front", "c1"), ("face_34", "c2"), ("face_side", "c3")):
    v = shots.VIEWS["m2_" + name]
    cams[name] = shots.camera(cid, v["loc"], (0, 0, v["zc"]), ortho_scale=v["ortho"])
for name, cam in cams.items():
    shots.render(cam, f"m2_{name}.png")

# 全身
v = shots.VIEWS["m2_body"]
shots.set_res(v["w"], v["h"])
cam = shots.camera("c4", v["loc"], (0, 0, v["zc"]), ortho_scale=v["ortho"])
shots.render(cam, "m2_body.png")
v = shots.VIEWS["m2_body_q34"]
cam2 = shots.camera("c5", v["loc"], (0, 0, v["zc"]), ortho_scale=v["ortho"])
shots.render(cam2, "m2_body_q34.png")

import sheet
sheet.sheet(shots.ensure_out(),
            ["m2_face_front.png", "m2_face_34.png", "m2_face_side.png"], "m2_face.png")
sheet.sheet(shots.ensure_out(),
            ["m2_body.png", "m2_body_q34.png"], "m2_full.png")
print("[done]")
