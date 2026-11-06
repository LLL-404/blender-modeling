# -*- coding: utf-8 -*-
"""M5 第一步：服装上身验收。

v2（2026-11-05）：服装形制双轨——默认挂脖旗袍（lib/qipao.py，设定书§三.1）；
环境变量 OUTFIT_STYLE=shirt 回退旧衬衫+A字裙（lib/outfit.py，逐位原样）。
v2 整合（2026-11-06）：形制口径改读 params/profile.json 的 outfit.style
（环境变量仍是最高优先级，回退路径不变），分发单源在 lib/assemble.py；
本入口同时挂全套配饰+飘袖（锚点落定同在 lib/assemble.py）。
"""
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
import assemble

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
cloth = assemble.build_outfit(M)
acc_pieces = assemble.full_stage(M)
for ob in acc_pieces:
    dump_stats(ob)
dump_stats(h)
dump_stats(hair)
dump_stats(cloth)

# C1 描边（Body/Head/Hands/Hair/Outfit + 闭合配饰全挂，厚度按视图换算成恒定像素宽）
OL = look.outline_mat()
_ol_objs, _ol_mods = [], []
for ob in (h, b, bpy.data.objects.get("Hands"), hair, cloth):
    if ob is not None:
        _ol_objs.append(ob)
        _ol_mods.append(look.add_outline(ob, OL, thickness=0.008))
for ob in assemble.closed(acc_pieces):
    _ol_objs.append(ob)
    _ol_mods.append(look.add_outline(ob, OL, thickness=0.008))


def _set_outline(ortho, res_y):
    look.set_outline_px(_ol_objs, _ol_mods, ortho, res_y, base_px=3.5)


look.bloom(threshold=0.88, size=8)

# 机位单源：数值读 shots.VIEWS（D15），勿在本文件改数。
v = shots.VIEWS["m5_face_front"]
shots.set_res(v["w"], v["h"])
# A6 后头骨中心 1.4956；正视相机压到完全水平（c_probe 反投影要用）。
for name in ("front", "q34"):
    v = shots.VIEWS["m5_face_" + name]
    cam = shots.camera("c" + name, v["loc"], (0, 0, v["zc"]), ortho_scale=v["ortho"])
    _set_outline(v["ortho"], v["h"])
    shots.render(cam, f"m5_face_{name}.png")

v = shots.VIEWS["m5_body_front"]
shots.set_res(v["w"], v["h"])
for name in ("front", "q34", "side"):
    v = shots.VIEWS["m5_body_" + name]
    cam = shots.camera("b" + name, v["loc"], (0, 0, v["zc"]), ortho_scale=v["ortho"])
    _set_outline(v["ortho"], v["h"])
    shots.render(cam, f"m5_body_{name}.png")

import sheet
out = shots.ensure_out()
sheet.sheet(out, ["m5_face_front.png", "m5_face_q34.png"], "m5_face.png")
sheet.sheet(out, ["m5_body_front.png", "m5_body_q34.png", "m5_body_side.png"], "m5_body.png")
print("[done] M5 outfit")