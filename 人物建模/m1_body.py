# -*- coding: utf-8 -*-
"""M1：身体素模，四视图验比例 + 手部近景（A1 的肉眼/像素核对入口）。"""
import bpy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import cfg
import shots
import look
import body as bodymod
from meshkit import dump_stats

shots.reset()
shots.setup_studio()

b = bodymod.build()
dump_stats(b)

# 手是独立物体（DESIGN §2.4.1）：不 join 进 Body，否则会被 5mm 体素糊成一根。
hands = bpy.data.objects.get("Hands")
if hands is not None:
    dump_stats(hands)
    hands.data.materials.clear()   # 丢掉 A 阶段占位皮肤，素模统一走 clay
    shots.clay(hands)

# 比例参考线：地面到头顶
print(f"[ratio] height={cfg.HEIGHT} head={cfg.HEAD_TOP - cfg.CHIN_Z:.3f} "
      f"heads={(cfg.HEAD_TOP / (cfg.HEAD_TOP - cfg.CHIN_Z)):.2f}")

shots.clay(b)
paths = shots.turnaround("m1_body")
import sheet
sheet.sheet(shots.ensure_out(), ["m1_body_front.png", "m1_body_side.png",
                                 "m1_body_back.png", "m1_body_q34.png"], "m1_sheet.png")

# ---- 手部近景：正交 scale 0.16，对着右手（side=-1，x=-0.232）z≈0.79 ----
# 掌心朝身体内侧，所以从外侧看得到的是手背；机位取「外侧 + 略偏正面」的 3/4，
# 既能数清 4 根手指的分叉，也能看到拇指的分离与指缝深度。
shots.set_res(620, 900)
# 机位角度是「指缝可见度」与「背景干净度」的取舍，算过两轮才定：
#   视线 x 分量越大 → 手指沿 y 的张开在屏幕上投影越完整（指缝越宽），
#   但同时同侧大腿会从手旁边挤进正交视野（不穿模，只是脏背景）。
#   view=(0.717,0.687,-0.059) 时 4 指的 y 间距 16.7~17.5mm 投到屏幕上约 12mm，
#   扣掉手指直径 8mm 后指缝 ≈4mm（24px），大腿只在画面右缘留一小条。
cam_hand = shots.camera("cam_hand",
                        (-0.949, -0.675, 0.845),
                        (-0.232, 0.012, 0.786),
                        ortho_scale=0.16)
hand_png = shots.render(cam_hand, "m1_hand.png")
print("[render] m1_hand ->", hand_png)

# ---- T23：同一机位再出一张「带描边壳」的近景 ----
# m1_body 走的是 clay 素模（不挂描边），所以 m1_hand.png 上量不到描边壳造成的腕部
# 横断（实测素模腕部横带内横向暗段 0px）。这张图补上 C1 的同一套壳，用于：
#   1) 腕部横带内不应出现横向暗断（量测脚本已归档：Tools/一次性存档/人物建模-T23修复手活-20261101/wrist_probe.py）；
#   2) 指缝描边必须还在（4 根手指之间 3 条黑缝）。
# Hands 必须用薄壳（look.HAND_OUTLINE_CAP=3.5mm/侧）：腕口与前臂几乎同宽，
# 全身机位 6.92mm/侧 的壳会戳出前臂轮廓 +0.54mm，形成「手腕断了」的黑圈。
# 近景 0.16/900（0.178mm/px）下 3.5px 只有 0.62mm，本来就低于上限，外观不变。
OL = look.outline_mat()
_ol_objs, _ol_mods = [], []
for ob in (b, hands):
    if ob is not None:
        _ol_objs.append(ob)
        _ol_mods.append(look.add_outline(
            ob, OL, thickness=0.008,
            thickness_cap=(look.HAND_OUTLINE_CAP if ob is hands else None)))
look.set_outline_px(_ol_objs, _ol_mods, 0.16, 900, base_px=3.5,
                    per_obj_cap={"Hands": look.HAND_OUTLINE_CAP})
hand_png2 = shots.render(cam_hand, "m1_hand_outline.png")
print("[render] m1_hand_outline ->", hand_png2)

print("[done]", paths)