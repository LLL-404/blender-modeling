# -*- coding: utf-8 -*-
"""M3：原神风着色验收。软色阶 + 脸部法线扁平化 + 泛光。"""
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
dump_stats(h)

b = bodymod.build()
b.data.materials.append(M["skin"])
# C2：Hands 是 body.build() 内部另建的独立物体，材质仍是 hand.py 的
# Principled 占位 → 同图里手与前臂两种肤色。这里把它接进 skin toon。
look.bind_hands(M)

# C4 收口：轮廓光的验收对象是**深色区域**（头发 z 1.40~1.62 / 藏青裙 z 0.65~1.05），
# 深色底上 rim 亮带才有对比度（白衬衫/皮肤已在 light 档 227，加不亮）。所以 m3 这个
# 入口必须把 Hair / Outfit 也建出来 —— 之前它只有 Head+Body。
hair = hairmod.build(M)
cloth = outfitmod.build(M)
dump_stats(hair)
dump_stats(cloth)

# C1 描边：Body / Head / Hands 各挂一层反法线外壳。
# 厚度按「视图恒定像素宽」换算（见 look.set_outline_px）：固定 0.005~0.008m
# 在全身 1.98mm/px 上只有 1~4px，在脸部特写 0.385mm/px 上会变成 13~20px 粗黑框。
# Head 里 join 了眼睛/眉毛/唇贴片，Solidify 会给贴片也加壳 —— 见 c_probe 的
# face-interior 暗像素对比，所以 Head 给同一线宽但单独列在 _OL_PX 里便于回退。
# T23：Hands 另加**世界厚度上限**。腕口（y 半宽 14.62mm）与前臂（14.45mm）几乎同宽，
# 全身机位 3.5px 换算成 6.92mm/侧的壳会戳出前臂轮廓 +0.54mm，在腕部留下一圈黑断痕。
# 限到 3.5mm/侧后手壳整体落进前臂壳（6.79mm/侧）之内；近景 0.62mm 不受影响。
OL = look.outline_mat()
_OL_PX = {"Head": 3.5}
_OL_CAP = {"Hands": look.HAND_OUTLINE_CAP}
_ol_objs, _ol_mods = [], []
for ob in (h, b, bpy.data.objects.get("Hands"), hair, cloth):
    if ob is not None:
        _ol_objs.append(ob)
        _ol_mods.append(look.add_outline(ob, OL, thickness=0.008,
                                         thickness_cap=_OL_CAP.get(ob.name)))


def _set_outline(ortho, res_y):
    look.set_outline_px(_ol_objs, _ol_mods, ortho, res_y, base_px=3.5,
                        per_obj_px=_OL_PX, per_obj_cap=_OL_CAP)


look.bloom(threshold=0.88, size=8)

# 机位单源：数值读 shots.VIEWS（D15），勿在本文件改数。
v = shots.VIEWS["m3_face_front"]
shots.set_res(v["w"], v["h"])
# A6 后头骨 z 区间 [1.3712, 1.6200]，中心 1.4956。
cams = {}
for name, cid in (("front", "c1"), ("q34", "c2"), ("side", "c3")):
    v = shots.VIEWS["m3_face_" + name]
    cams[name] = shots.camera(cid, v["loc"], (0, 0, v["zc"]), ortho_scale=v["ortho"])
for name, cam in cams.items():
    v = shots.VIEWS["m3_face_" + name]
    _set_outline(v["ortho"], v["h"])
    shots.render(cam, f"m3_face_{name}.png")

v = shots.VIEWS["m3_upper"]
shots.set_res(v["w"], v["h"])
cam = shots.camera("c4", v["loc"], (0, 0, v["zc"]), ortho_scale=v["ortho"])
_set_outline(v["ortho"], v["h"])
shots.render(cam, "m3_upper.png")

v = shots.VIEWS["m3_body_q34"]
shots.set_res(v["w"], v["h"])
cam = shots.camera("c5", v["loc"], (0, 0, v["zc"]), ortho_scale=v["ortho"])
_set_outline(v["ortho"], v["h"])
shots.render(cam, "m3_body_q34.png")

# 正对全身机位：手/前臂 ROI 需要「镜头沿 +Y」才能精确反投影到世界坐标。
# 参数与 m5_body_front 一致（560×900 / ortho 1.80 / 中心 z 0.86），这样
# C2 的手部判据可以只在 m3 这一路入口上验证，不必去动 m5_outfit.py。
v = shots.VIEWS["m3_body_front"]
cam = shots.camera("c6", v["loc"], (0, 0, v["zc"]), ortho_scale=v["ortho"])
_set_outline(v["ortho"], v["h"])
shots.render(cam, "m3_body_front.png")

import sheet
out = shots.ensure_out()
sheet.sheet(out, ["m3_face_front.png", "m3_face_q34.png", "m3_face_side.png"], "m3_face.png")
sheet.sheet(out, ["m3_upper.png", "m3_body_q34.png"], "m3_body.png")
print("[done] M3")