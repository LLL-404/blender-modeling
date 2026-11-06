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
dump_stats(h)
b = bodymod.build()
b.data.materials.append(M["skin"])
look.bind_hands(M)          # C2：Hands 接进 skin toon
hair = hairmod.build(M)
dump_stats(hair)
# 2026-11-06 整合：头部锚定配饰（蝶饰×2 + 墨镜）——锚点落定单源 lib/assemble
# （A1 蝶饰实测悬 1.4mm 不重锚；A2 墨镜重锚到发帽冠部，推导见 assemble.py）。
acc_pieces = assemble.hair_stage(M)
for ob in acc_pieces:
    dump_stats(ob)

# C1 描边（构造与 m3_look 完全一致，厚度按视图换算成恒定像素宽）
OL = look.outline_mat()
OL_CARD = look.outline_card_mat(OL)
_ol_objs, _ol_mods = [], []
for ob in (h, b, bpy.data.objects.get("Hands")):
    if ob is not None:
        _ol_objs.append(ob)
        _ol_mods.append(look.add_outline(ob, OL, thickness=0.008))
# 2026-11-04：与 m5_rig 同步 —— 发片有 alpha 贴图，描边壳也要跟着镂空。
_ol_objs.append(hair)
_ol_mods.append(look.add_outline_layers(
        hair, [OL, OL_CARD, look.transparent_mat()], thickness=0.008))
for ob in assemble.closed(acc_pieces):
    _ol_objs.append(ob)
    _ol_mods.append(look.add_outline(ob, OL, thickness=0.008))


# 2026-11-04：与 m5_rig 同步 —— hair card 是薄壳片，3.5px 描边会把卡片缝隙
# 挤成黑色裂纹，Hair 单独收细到 1.4px。
_OL_PX = {"Hair": 1.4}


def _set_outline(ortho, res_y):
    look.set_outline_px(_ol_objs, _ol_mods, ortho, res_y, base_px=3.5,
                        per_obj_px=_OL_PX)


look.bloom(threshold=0.88, size=8)

# 机位单源：数值读 shots.VIEWS（D15），勿在本文件改数。
v = shots.VIEWS["m4_face_front"]
shots.set_res(v["w"], v["h"])
# A6 后头骨中心 1.4956；正视/侧视相机压到完全水平，c_probe 才能精确反投影。
# D2 专用 back 机位：后发束是沿 x 并排的纵向条，侧面机位（沿 x 看）会把 7 条互相
# 遮住，量不到沟壑；必须从背后正对看。ortho 0.42 覆盖后脑 208mm。
cams = {}
for name, cid in (("front", "c1"), ("q34", "c2"), ("side", "c3"), ("back", "c6")):
    v = shots.VIEWS["m4_face_" + name]
    cams[name] = shots.camera(cid, v["loc"], (0, 0, v["zc"]), ortho_scale=v["ortho"])
for name, cam in cams.items():
    v = shots.VIEWS["m4_face_" + name]
    _set_outline(v["ortho"], v["h"])
    shots.render(cam, f"m4_face_{name}.png")

v = shots.VIEWS["m4_upper"]
shots.set_res(v["w"], v["h"])
cam = shots.camera("c4", v["loc"], (0, 0, v["zc"]), ortho_scale=v["ortho"])
_set_outline(v["ortho"], v["h"])
shots.render(cam, "m4_upper.png")

v = shots.VIEWS["m4_body_q34"]
shots.set_res(v["w"], v["h"])
cam = shots.camera("c5", v["loc"], (0, 0, v["zc"]), ortho_scale=v["ortho"])
_set_outline(v["ortho"], v["h"])
shots.render(cam, "m4_body_q34.png")

import sheet
out = shots.ensure_out()
sheet.sheet(out, ["m4_face_front.png", "m4_face_q34.png", "m4_face_side.png"], "m4_face.png")
sheet.sheet(out, ["m4_upper.png", "m4_body_q34.png"], "m4_body.png")
print("[done] M4")