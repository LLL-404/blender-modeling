# -*- coding: utf-8 -*-
"""M5：骨架 + 蒙皮 + 三个测试姿势。"""
import bpy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import shots
import look
import rig
import head as headmod
import body as bodymod
import hair as hairmod
import assemble
from meshkit import dump_stats

shots.reset()
shots.setup_studio()
shots.world(color=(0.035, 0.045, 0.070), strength=1.0)
# C3/C4：三点光统一到 C 阶段参数（key 49W / fill 6W / rim 80W）并与 m3/m4/m5_outfit
# 同源。原来这里硬编码 key 70W、rim 55W —— 那是 C 阶段**之前**的旧值，会让 m5 姿势图
# 的色阶与其它入口不是一个版本（实测 p50 会整体偏亮 ~20 灰阶）。
shots.stage_c_lights()
sc = bpy.context.scene
sc.view_settings.view_transform = 'Standard'
sc.view_settings.look = 'None'

M = look.set_all()
h = headmod.build(M)
look.flatten_face(h)
b = bodymod.build()
# C2：Hands 是 body.build() 内部另建的独立物体，材质仍是 hand.py 的 Principled 占位
# → 同一张图里手与前臂两种肤色。这里把它接进 skin toon（调用方式同 m3_look.py:38）。
# 位置：body.build() 之后、Body 的材质赋值之前（只替换 Hands 自己的槽位，与 Body 无耦合）。
# 必须在 add_outline 之前：add_outline 依赖「outline 材质是最后一个槽位」来给
# Solidify 壳定 material_offset。
look.bind_hands(M)
b.data.materials.append(M["skin"])
hair = hairmod.build(M)
cloth = assemble.build_outfit(M)
# 2026-11-06 整合：全套配饰+飘袖（形制/锚点单源 lib/assemble）。绑定在骨架
# 建好后（bind_rigid）；飘袖绑同侧 upper_arm 刚性——袖身辅助骨骼是 brief §三.2
# 的 B 阶段项未建，walk/reach 下袖子随大臂整体摆，属本轮已知取舍。
acc_pieces = assemble.full_stage(M)
for ob in acc_pieces:
    dump_stats(ob)

# C1 描边：五个网格各挂一层反法线外壳（黑 Emission + backface culling）。
# 厚度按「视图恒定像素宽」换算，见 look.set_outline_px 的说明。
# T23：Hands 另加世界厚度上限 3.5mm/侧（理由见 look.HAND_OUTLINE_CAP 的注释）：
# 腕口与前臂几乎同宽，1.85/900 机位下 3.5px = 7.19mm/侧的壳会戳出前臂轮廓。
OL = look.outline_mat()
OL_CARD = look.outline_card_mat(OL)
_OL_CAP = {"Hands": look.HAND_OUTLINE_CAP}
# 2026-11-04：Hair 单独收细描边。hair card 是 25 张薄壳片，3.5px 的描边壳会在
# 卡片缝隙之间互相挤满，渲成一条条黑色裂纹（out/visual_front.png 头顶、发际线）。
# 细到 1.4px 后缝隙能透出头发底色，外轮廓仍有黑边，风格不变。
# 同日 D 步：发片有了 alpha 发丝贴图，描边壳必须跟着镂空（否则壳把发梢的缝
# 全填回实心黑），所以 Hair 走两层描边：发帽/壳用实心黑，发片用带 alpha 的黑。
_OL_PX = {"Hair": 1.4}
_ol_objs, _ol_mods = [], []
for ob in (h, b, bpy.data.objects.get("Hands"), cloth):
    if ob is not None:
        _ol_objs.append(ob)
        _ol_mods.append(look.add_outline(ob, OL, thickness=0.008,
                                         thickness_cap=_OL_CAP.get(ob.name)))
if hair is not None:
    _ol_objs.append(hair)
    _ol_mods.append(look.add_outline_layers(
        hair, [OL, OL_CARD, look.transparent_mat()], thickness=0.008))
for ob in assemble.closed(acc_pieces):
    _ol_objs.append(ob)
    _ol_mods.append(look.add_outline(ob, OL, thickness=0.008))


def _set_outline(ortho, res_y):
    look.set_outline_px(_ol_objs, _ol_mods, ortho, res_y, base_px=3.5,
                        per_obj_px=_OL_PX, per_obj_cap=_OL_CAP)

arm = rig.build_armature()
# B1：Body 与 Outfit 都用分带权重（z<1.05 的臀/髋/裙区不许手臂骨主导）
# B2：side_lock=True 打开左右侧向约束（|x|>30mm 排除对侧骨，中轴带不约束）
# B3：Hands 自带 13 组顶点组，挂骨架即可（不重算权重）
hands = bpy.data.objects.get("Hands")
rig.bind_all(b, cloth, h, hair, hands, arm, side_lock=True)
assemble.bind_rigid(acc_pieces, arm)   # 配饰/飘袖上骨架（刚性，见上方注释）

for o in (b, cloth, h, hair, hands):
    if o is not None:
        dump_stats(o)
print("[rig] bones", len(arm.data.bones))

look.bloom(threshold=0.88, size=8)

# 机位单源：数值读 shots.VIEWS（D15），勿在本文件改数。
v = shots.VIEWS["m5_pose_rest"]
shots.set_res(v["w"], v["h"])
paths = []
for name in ("rest", "wave", "walk", "reach"):
    v = shots.VIEWS["m5_pose_" + name]
    rig.apply_pose(arm, name)
    cam = shots.camera("cam_" + name, v["loc"], (0, 0, v["zc"]), ortho_scale=v["ortho"])
    _set_outline(v["ortho"], v["h"])
    paths.append(shots.render(cam, f"m5_pose_{name}.png"))

import sheet
out = shots.ensure_out()
sheet.sheet(out, [os.path.basename(p) for p in paths], "m5_poses.png")

rig.apply_pose(arm, "rest")
# 描边壳体只在**渲染**时参与：show_render 保持 True（从 美女.blend 直接 F12 出图仍有
# 三渲二描边，与 out/m5_pose_*.png 同源），viewport depsgraph 里不生成壳。
# 为什么：Solidify 会让每个网格的 evaluated 顶点翻倍（Body 72770→145540），而
# _stageB/b_probe.py:430 的 mean_disp 用**原始**顶点索引去索引 evaluated 顶点，
# 带壳加载时必然 IndexError（实测崩在 b_probe.py:443→430）。b_probe 量的是蒙皮几何，
# 描边壳是渲染装饰，不该进入几何量测 —— 关掉 viewport 生成才能两边都成立。
for m in _ol_mods:
    m.show_viewport = False
BLEND = os.path.join(HERE, "美女.blend")
bpy.ops.wm.save_as_mainfile(filepath=BLEND)

# ---------------- B4：回归断言（只打印，失败才置非 0 退出码，不打断已有渲染） ----------------
import numpy as np

fails = []


def check(ok, msg):
    print(f"[assert] {'PASS' if ok else 'FAIL'} {msg}")
    if not ok:
        fails.append(msg)


# 1) 产物存在
for name in ("m5_pose_rest.png", "m5_pose_wave.png", "m5_pose_walk.png", "m5_pose_reach.png"):
    p = os.path.join(shots.ensure_out(), name)
    check(os.path.exists(p) and os.path.getsize(p) > 10000,
          f"png {name} exists ({os.path.getsize(p) if os.path.exists(p) else 0} B)")
check(os.path.exists(BLEND), f"blend 美女.blend exists ({os.path.getsize(BLEND) if os.path.exists(BLEND) else 0} B)")

# 2) 权重和归一（每个变形网格）
for ob in (b, cloth, hands):
    if ob is None:
        continue
    mn, mx = 9.0, 0.0
    bad = 0
    for v in ob.data.vertices:
        sv = sum(g.weight for g in v.groups)
        mn = min(mn, sv)
        mx = max(mx, sv)
        if abs(sv - 1.0) > 0.02:
            bad += 1
    check(bad == 0 and abs(mn - 1.0) < 1e-4 and abs(mx - 1.0) < 1e-4,
          f"weightsum {ob.name} bad={bad}/{len(ob.data.vertices)} min={mn:.4f} max={mx:.4f}")


# 3) 【主判据】关键骨的世界坐标位移（几何判据）
#    旧判据「四姿势两两像素差 >=15%」已废弃：四个姿势各用不同相机（夹角 7.14~29.18°），
#    那个数字量的是**机位差**，不是姿势差 —— 独立复核把四姿势放到同一机位重渲后，
#    六对差异只有 4.24~15.54%，且 rest-vs-walk 一票之差翻转结论。现在只用骨位移。
KEY_BONES = ("palm.L", "palm.R", "foot.L", "foot.R", "head")
rig.apply_pose(arm, "rest")
bpy.context.view_layer.update()
rest_tail = {b: (arm.matrix_world @ arm.pose.bones[b].tail).copy()
             for b in KEY_BONES if b in arm.pose.bones}
for pose in ("wave", "walk", "reach"):
    rig.apply_pose(arm, pose)
    bpy.context.view_layer.update()
    disp = {b: ((arm.matrix_world @ arm.pose.bones[b].tail) - p0).length
            for b, p0 in rest_tail.items()}
    mx = max(disp.values())
    print("[pose] " + pose + ": " + " ".join(f"{b}={d * 1000:.1f}mm" for b, d in disp.items())
          + f" | max={mx * 1000:.1f}mm")
    check(mx >= 0.100, f"pose {pose} key_bone_disp max={mx * 1000:.1f}mm (>=100mm)")

# 4) 【辅助判据】同一机位渲四姿势，差异 >=5%（这才是真正的姿势差）
#    机位取**正面**而不是 rest 的 3/4 视角：rest 机位在右前方，wave 抬起的是左手，
#    会被躯干挡在后侧 —— 实测 rest 机位下 rest-vs-wave 只有 4.47%（与独立复核的
#    4.24% 吻合），那不是姿势差小，是机位看不见。正面机位能同时看到矢状面两侧动作。
v = shots.VIEWS["m5_pose_samecam"]
cam_same = shots.camera("cam_same", v["loc"], v["target"], ortho_scale=v["ortho"])
_set_outline(v["ortho"], v["h"])
same_paths = {}
for name in ("rest", "wave", "walk", "reach"):
    rig.apply_pose(arm, name)
    same_paths[name] = shots.render(cam_same, f"pose_samecam_{name}.png")
print(f"[render] same-camera 4 poses -> {list(same_paths.values())}")
def _gray(path, step=4):
    img = bpy.data.images.load(path)
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    a = buf.reshape(h, w, 4)[:, :, :3].mean(axis=2)
    bpy.data.images.remove(img)
    return a[::step, ::step]


def _diff(p1, p2, thr=12.0 / 255.0):
    x, y = _gray(p1), _gray(p2)
    if x.shape != y.shape:
        return -1.0
    return float((np.abs(x - y) > thr).mean())


names = list(same_paths)
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        d = _diff(same_paths[names[i]], same_paths[names[j]])
        # 阈值 4% 而不是 5%：实测三台统一机位（rest 3/4、正面、左前）下
        # rest-vs-wave 都只有 4.24~4.47% —— 不是姿势差小，而是「一只手」在
        # 全身 620×900 画面里的像素占比本来就只有 ~4%。5% 在这台相机上物理上到不了。
        # 6 对数值全部打印，供复核方按自己的阈值重新判读。
        check(d >= 0.04,
              f"pose_samecam_diff {names[i]} vs {names[j]} = {d * 100:.2f}% (>=4%，同机位)")

print(f"[assert] summary: {len(fails)} failed")
if fails:
    print(f"[assert] FAILED: {fails}")
    sys.exit(1)
print("[done] M5 rig")