# -*- coding: utf-8 -*-
r"""B 阶段挑刺式复算（Evaluator 韦衡）。**不改任何 lib/m*/cfg**。

两种模式（自动判别）：
  1) "D:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python _stageB/accept_b.py        -> built 模式（按 m5_rig 顺序自建 + bind_all(side_lock=True)）
  2) "D:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b 美女.blend \
        --python _stageB/accept_b.py        -> loaded 模式（验证重开后的状态；不保存）

不复用 _stageB/b_probe.py 的任何函数/结论，指标全部独立实现。
输出 [accb] key=value + _stageB/logs/accept_b_<mode>.json。
"""
import os
import sys
import json
import math

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import cfg                       # noqa: E402
import rig                       # noqa: E402
from meshkit import dump_stats    # noqa: E402

LOG_DIR = os.path.join(HERE, "_stageB", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
REC = {}

POSES_VIEWS = {
    "rest": ((2.3, -2.5, 1.0), (0, 0, 0.86)),
    "wave": ((1.2, -3.2, 1.15), (0, 0, 1.00)),
    "walk": ((2.6, -2.2, 1.0), (0, 0, 0.86)),
    "reach": ((1.8, -2.9, 1.15), (0, 0, 0.98)),
}


def p(key, val, note=""):
    REC[key] = val
    print(f"[accb] {key}={val}" + (f"   # {note}" if note else ""))


def mm(v, nd=2):
    return None if v is None else round(v * 1000.0, nd)


# ---------------------------------------------------------------- 建/取场景

if bpy.data.objects.get("Rig") is not None:
    mode = "loaded"
    b = bpy.data.objects["Body"]
    cloth = bpy.data.objects["Outfit"]
    h = bpy.data.objects.get("Head")
    hair = bpy.data.objects.get("Hair")
    hands = bpy.data.objects.get("Hands")
    arm = bpy.data.objects["Rig"]
else:
    mode = "built"
    import shots
    import look
    import head as headmod
    import body as bodymod
    import hair as hairmod
    import outfit as outfitmod

    shots.reset()
    shots.setup_studio()
    shots.world(color=(0.035, 0.045, 0.070), strength=1.0)
    for name, energy, size in (("key", 70, 0.45), ("fill", 6, 3.0), ("rim", 55, 1.0)):
        ob = bpy.data.objects[name]
        ob.data.energy = energy
        ob.data.size = size
    bpy.data.objects["key"].location = (-1.15, -2.1, 2.05)
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

p("mode", mode)
p("objects", [f"{o.name}:{o.type}" for o in bpy.data.objects])
for ob in (b, cloth, h, hair, hands):
    if ob is not None:
        p(f"stats_{ob.name}", {"verts": len(ob.data.vertices),
                               "faces": len(ob.data.polygons)})

# ---------------------------------------------------------------- 工具


def wmap(ob):
    idx = {g.index: g.name for g in ob.vertex_groups}
    return [{(idx[g.group]): g.weight for g in v.groups} for v in ob.data.vertices]


def weight_sum_bad(ob, tol=0.02):
    bad, mn, mx = 0, 9.0, 0.0
    for v in ob.data.vertices:
        s = sum(g.weight for g in v.groups)
        mn = min(mn, s)
        mx = max(mx, s)
        if abs(s - 1.0) > tol:
            bad += 1
    return bad, mn, mx


def eval_mesh(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    mw = ev.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    norms = [pg.normal.copy() for pg in me.polygons]
    ev.to_mesh_clear()
    return pts, norms


def rest_pts(ob):
    mw = ob.matrix_world
    return [mw @ v.co for v in ob.data.vertices]


def bbox(pts):
    return (min(p.x for p in pts), max(p.x for p in pts),
            min(p.y for p in pts), max(p.y for p in pts),
            min(p.z for p in pts), max(p.z for p in pts))


# ---------------------------------------------------------------- 1. 骨架

bones = [bn.name for bn in arm.data.bones]
fingers = [n for n in bones if rig.is_finger(n)]
p("bones_total", len(bones))
p("bones_fingers", len(fingers))
p("bones_hand_names", sorted([n for n in bones if rig.is_arm_bone(n) and
                              n.split(".")[0].startswith(("palm", "index", "middle",
                                                          "ring", "pinky"))]))
p("old_hand_bones_present", [n for n in ("hand.L", "hand.R") if n in bones])
for suf in (".L", ".R"):
    bs = sorted(n for n in bones if n.endswith(suf) and
                n.split(".")[0].startswith(("palm", "index", "middle", "ring", "pinky")))
    p(f"bones_hand{suf}", {"n": len(bs), "names": bs})
p("bones_26_check", {"palm": len([n for n in bones if n.startswith("palm")]),
                     "finger": len(fingers),
                     "sum": len([n for n in bones if n.startswith("palm")]) + len(fingers)})

# ---------------------------------------------------------------- 2. Hands 顶点组 ↔ 骨名 一一对应

hs = hands
vgn = sorted(g.name for g in hs.vertex_groups)
p("hands_vgroups_n", len(vgn))
p("hands_modifiers", [(m.name, m.type, m.object.name if getattr(m, "object", None) else None)
                      for m in hs.modifiers])
p("hands_parent", hs.parent.name if hs.parent else None)
mapping = {}
for suf in (".L", ".R"):
    bset = {n for n in bones if n.endswith(suf) and
            n.split(".")[0].startswith(("palm", "index", "middle", "ring", "pinky"))}
    gset = {n for n in vgn if n.endswith(suf)}
    mapping[suf] = {"bones": sorted(bset), "groups": sorted(gset),
                    "equal": bset == gset,
                    "missing_groups": sorted(bset - gset),
                    "extra_groups": sorted(gset - bset),
                    "n": len(gset)}
p("hands_group_bone_map", mapping)
# 每个组是否有顶点、每骨是否被使用
gw = wmap(hs)
used = {}
for w in gw:
    for n in w:
        used[n] = used.get(n, 0) + 1
p("hands_group_used_verts", {k: used.get(k, 0) for k in vgn})
p("hands_vertices_without_group",
  sum(1 for w in gw if not w))

# ---------------------------------------------------------------- 3. B1（裙摆主导骨）

cw = wmap(cloth)
skirt_idx = [i for i, v in enumerate(cloth.data.vertices) if v.co.z < 1.040]
lead = {}
arm_weight_total = 0.0
verts_with_arm = 0
for i in skirt_idx:
    w = cw[i]
    if not w:
        lead["none"] = lead.get("none", 0) + 1
        continue
    top = max(w.items(), key=lambda kv: kv[1])[0]
    lead[top] = lead.get(top, 0) + 1
    aw = sum(v for n, v in w.items() if rig.is_arm_bone(n))
    arm_weight_total += aw
    if aw > 1e-6:
        verts_with_arm += 1
arm_led = sum(n for bn, n in lead.items() if rig.is_arm_bone(bn))
p("B1_denominator_outfit_z_lt_1.04", len(skirt_idx),
  "分母 = Outfit 顶点中 z<1.04 的子集")
p("B1_outfit_total_verts", len(cloth.data.vertices))
p("B1_arm_led", arm_led)
p("B1_arm_led_pct", round(100.0 * arm_led / max(1, len(skirt_idx)), 3))
p("B1_lead_bones", sorted(lead.items(), key=lambda t: -t[1]))
p("B1_lead_outside_hips_spine_chest",
  sorted({bn for bn in lead if bn not in ("hips", "spine", "chest")}))
p("B1_verts_with_any_arm_weight", verts_with_arm)
p("B1_mean_arm_weight_on_skirt", round(arm_weight_total / max(1, len(skirt_idx)), 5))
# 裙子上各骨的权重均值（看是否只剩髋/脊柱）
mean_w = {}
for i in skirt_idx:
    for n, v in cw[i].items():
        mean_w[n] = mean_w.get(n, 0.0) + v
p("B1_skirt_mean_weights", {k: round(v / max(1, len(skirt_idx)), 4)
                            for k, v in sorted(mean_w.items(), key=lambda t: -t[1])})
# 对照：Body 的 z<1.04 子集（说明「分母口径」的差别）
bw = wmap(b)
body_z = [i for i, v in enumerate(b.data.vertices) if v.co.z < 1.04]
b_arm = 0
for i in body_z:
    w = bw[i]
    if w:
        top = max(w.items(), key=lambda kv: kv[1])[0]
        if rig.is_arm_bone(top):
            b_arm += 1
p("B1_body_z_lt_1.04", {"n": len(body_z), "arm_led": b_arm,
                        "pct": round(100.0 * b_arm / max(1, len(body_z)), 2)},
  "仅作分母口径对照：Body 在该带本来就有前臂顶点")

# ---------------------------------------------------------------- 4. B2（左右串权）

r_side = {n for n in bones if n.endswith(".R")}
l_side = {n for n in bones if n.endswith(".L")}
leaks = []
mx_opp = 0.0
for v, w in zip(b.data.vertices, bw):
    if not w:
        continue
    if v.co.x > 0.030:
        s = sum(w.get(n, 0.0) for n in r_side)
        if s > 0.10:
            leaks.append((v.index, v.co.x, v.co.z))
        mx_opp = max(mx_opp, s)
    elif v.co.x < -0.030:
        s = sum(w.get(n, 0.0) for n in l_side)
        if s > 0.10:
            leaks.append((v.index, v.co.x, v.co.z))
        mx_opp = max(mx_opp, s)
p("B2_denominator_body_verts", len(b.data.vertices))
p("B2_leak_n", len(leaks))
p("B2_leak_pct", round(100.0 * len(leaks) / max(1, len(b.data.vertices)), 4))
p("B2_max_opposite_weight_beyond30mm", round(mx_opp, 5))
# 放宽阈值看余量：>0.02 / >0.05
for thr in (0.02, 0.05):
    n = 0
    for v, w in zip(b.data.vertices, bw):
        if not w:
            continue
        if v.co.x > 0.030 and sum(w.get(n_, 0.0) for n_ in r_side) > thr:
            n += 1
        elif v.co.x < -0.030 and sum(w.get(n_, 0.0) for n_ in l_side) > thr:
            n += 1
    p(f"B2_leak_gt{thr}", n)
# 中轴带（|x|<=30mm，被 side_lock 豁免）的最大对侧权重 —— 说明豁免带里确实还有对侧权重
band_opp = 0.0
band_n = 0
for v, w in zip(b.data.vertices, bw):
    if abs(v.co.x) <= 0.030 and w:
        s = min(sum(w.get(n, 0.0) for n in r_side),
                sum(w.get(n, 0.0) for n in l_side))
        band_opp = max(band_opp, s)
        if s > 0.10:
            band_n += 1
p("B2_midband_max_opposite_weight", round(band_opp, 5))
p("B2_midband_n_gt0.10", band_n, "|x|<=30mm 豁免带，设计上允许两侧混合")

# ---------------------------------------------------------------- 5. 权重和

for ob in (b, cloth, hs, hair, h):
    if ob is None:
        continue
    bad, mn, mx = weight_sum_bad(ob)
    p(f"weightsum_{ob.name}", {"bad": bad, "n": len(ob.data.vertices),
                               "min": round(mn, 5), "max": round(mx, 5)})

# ---------------------------------------------------------------- 6. 姿势：位移 / 投影位移

restc = {o.name: rest_pts(o) for o in (b, cloth, hs, hair, h) if o is not None}


def cam_basis(loc, target):
    f = (Vector(target) - Vector(loc)).normalized()
    r = f.cross(Vector((0.0, 0.0, 1.0))).normalized()
    u = r.cross(f).normalized()
    return f, r, u


pose_stat = {}
for pose in ("wave", "walk", "reach"):
    rig.apply_pose(arm, pose)
    bpy.context.view_layer.update()
    f, r, u = cam_basis(*POSES_VIEWS[pose])
    row = {}
    for ob, label in ((b, "Body"), (cloth, "Outfit"), (hs, "Hands"), (hair, "Hair")):
        if ob is None:
            continue
        pts, _ = eval_mesh(ob)
        r0 = restc[ob.name]
        d = [pts[i] - r0[i] for i in range(len(pts))]
        mag = sorted(x.length for x in d)
        proj = sorted(abs(x.dot(r)) for x in d)   # 屏幕水平方向位移
        b0, b1 = bbox(r0), bbox(pts)
        c0 = [Vector((b0[0], b0[2], b0[4])), Vector((b0[1], b0[2], b0[4])),
              Vector((b0[0], b0[3], b0[4])), Vector((b0[1], b0[3], b0[4])),
              Vector((b0[0], b0[2], b0[5])), Vector((b0[1], b0[2], b0[5])),
              Vector((b0[0], b0[3], b0[5])), Vector((b0[1], b0[3], b0[5]))]
        c1 = [Vector((b1[0], b1[2], b1[4])), Vector((b1[1], b1[2], b1[4])),
              Vector((b1[0], b1[3], b1[4])), Vector((b1[1], b1[3], b1[4])),
              Vector((b1[0], b1[2], b1[5])), Vector((b1[1], b1[2], b1[5])),
              Vector((b1[0], b1[3], b1[5])), Vector((b1[1], b1[3], b1[5]))]
        row[label] = {"bbox_corner_delta_mm": mm(max((q - w).length for q, w in zip(c0, c1))),
                      "max_mm": mm(mag[-1]), "p95_mm": mm(mag[int(0.95 * (len(mag) - 1))]),
                      "mean_mm": mm(sum(mag) / len(mag)),
                      "proj_x_max_mm": mm(proj[-1]),
                      "proj_x_mean_mm": mm(sum(proj) / len(proj)),
                      "n_proj_gt20mm": sum(1 for q in proj if q > 0.020)}
    # 相机方位/仰角
    loc, tgt = POSES_VIEWS[pose]
    az = math.degrees(math.atan2(loc[0], -loc[1]))
    el = math.degrees(math.atan2(loc[2] - tgt[2], math.hypot(loc[0], loc[1])))
    row["camera"] = {"az_deg": round(az, 2), "el_deg": round(el, 2),
                     "forward": [round(v, 4) for v in f]}
    pose_stat[pose] = row
p("pose_displacement", pose_stat)

# 相机之间的夹角
cam_ang = {}
names = list(POSES_VIEWS)
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        f1 = cam_basis(*POSES_VIEWS[names[i]])[0]
        f2 = cam_basis(*POSES_VIEWS[names[j]])[0]
        d = max(-1.0, min(1.0, f1.dot(f2)))
        cam_ang[f"{names[i]}-{names[j]}"] = round(math.degrees(math.acos(d)), 2)
p("camera_pair_angles_deg", cam_ang)

# ---------------------------------------------------------------- 7. B1 副作用：walk 下裙摆 vs 腿

rig.apply_pose(arm, "rest")
bpy.context.view_layer.update()
rest_b, _ = eval_mesh(b)
rest_c, _ = eval_mesh(cloth)
rig.apply_pose(arm, "walk")
bpy.context.view_layer.update()
walk_b, _ = eval_mesh(b)
walk_c, _ = eval_mesh(cloth)


def region_stats(r0, r1, pred):
    mags = [ (r1[i] - r0[i]).length for i in range(len(r0)) if pred(i) ]
    if not mags:
        return None
    mags.sort()
    return {"n": len(mags), "max_mm": mm(mags[-1]),
            "p95_mm": mm(mags[int(0.95 * (len(mags) - 1))]),
            "mean_mm": mm(sum(mags) / len(mags))}


# 裙子：z 0.65~1.05 全裙
skirt_all = region_stats(rest_c, walk_c, lambda i: 0.65 <= rest_c[i].z <= 1.05)
skirt_hem = region_stats(rest_c, walk_c, lambda i: 0.65 <= rest_c[i].z <= 0.78)
skirt_waist = region_stats(rest_c, walk_c, lambda i: 0.95 <= rest_c[i].z <= 1.05)
# 腿：Body z 0.42~0.87 且 |x|>0.03（大腿/小腿）
leg = region_stats(rest_b, walk_b, lambda i: 0.42 <= rest_b[i].z <= 0.87
                   and abs(rest_b[i].x) > 0.03)
leg_hidden = region_stats(rest_b, walk_b, lambda i: 0.65 <= rest_b[i].z <= 0.87
                          and abs(rest_b[i].x) > 0.03)
leg_visible = region_stats(rest_b, walk_b, lambda i: 0.10 <= rest_b[i].z < 0.65
                           and abs(rest_b[i].x) > 0.03)
p("B1_sideeffect_walk_skirt", skirt_all)
p("B1_sideeffect_walk_skirt_hem", skirt_hem)
p("B1_sideeffect_walk_skirt_waist", skirt_waist)
p("B1_sideeffect_walk_leg_all", leg)
p("B1_sideeffect_walk_leg_hidden_gt0.65", leg_hidden)
p("B1_sideeffect_walk_leg_visible_lt0.65", leg_visible)
if skirt_all and leg_visible:
    p("B1_sideeffect_ratio_skirt_over_leg",
      round(skirt_all["mean_mm"] / max(1e-6, leg["mean_mm"]), 4),
      "裙摆平均位移 / 腿平均位移（walk）")

# ---------------------------------------------------------------- 8. 极端姿势：B2 过杀（撕裂）检验

INNER = {"x": 0.030, "z": (0.70, 0.80), "y": (-0.05, 0.05)}


def inner_pred(p0):
    return (abs(p0.x) < INNER["x"] and INNER["z"][0] <= p0.z <= INNER["z"][1]
            and INNER["y"][0] <= p0.y <= INNER["y"][1])


def apply_extreme():
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    # 左腿外展 35°（+x 方向）、右腿内收 15°（也向 +x，形成交叉）
    rig.rot_bone(arm, "thigh.L", 'Y', -35)
    rig.rot_bone(arm, "thigh.R", 'Y', -15)
    bpy.context.view_layer.update()


REGIONS = {
    "crotch_task(|x|<30,z.70-.80,|y|<.05)":
        lambda q: abs(q.x) < 0.030 and 0.70 <= q.z <= 0.80 and -0.05 <= q.y <= 0.05,
    "cutline(20<|x|<55,z.70-.80,|y|<.12)":
        lambda q: 0.020 < abs(q.x) < 0.055 and 0.70 <= q.z <= 0.80 and abs(q.y) <= 0.12,
}
EXT_POSES = {
    "cross_35_15": [("thigh.L", 'Y', -35), ("thigh.R", 'Y', -15)],
    "cross_60_30": [("thigh.L", 'Y', -60), ("thigh.R", 'Y', -30)],
}


def reset_pose():
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)


def apply_extreme(key="cross_35_15"):
    """临时极端姿势（只在本脚本内存里，绝不写回 rig.POSES / m5_rig.py）。
    两条腿都往 +x 摆，形成交叉；sign 约定：R_y(θ)(0,0,-1)=(-sinθ,0,-cosθ)。"""
    reset_pose()
    for bn, ax, deg in EXT_POSES[key]:
        rig.rot_bone(arm, bn, ax, deg)
    bpy.context.view_layer.update()


def apply_finger_bend():
    """临时屈指：wave 只转 palm、指骨无局部旋转，整只手是刚体，
    边长比恒为 1.0 —— 该指标在 wave 下没有区分度，必须另造姿势才测得出软过渡。"""
    reset_pose()
    rig.rot_bone(arm, "index_proximal.L", 'X', -45)
    rig.rot_bone(arm, "index_middle.L", 'X', -30)
    bpy.context.view_layer.update()


def extreme_stats(ob, pose_key):
    reset_pose()
    bpy.context.view_layer.update()
    r0, _ = eval_mesh(ob)
    rn = [pg.normal.copy() for pg in ob.data.polygons]
    apply_extreme(pose_key)
    e0, en = eval_mesh(ob)
    out = {}
    for rk, pred in REGIONS.items():
        ratios, angles = [], []
        for e in ob.data.edges:
            i, j = e.vertices
            if not (pred(r0[i]) and pred(r0[j])):
                continue
            l0 = (r0[i] - r0[j]).length
            l1 = (e0[i] - e0[j]).length
            if l0 > 1e-4:                       # 忽略 0.1mm 级短边，避免比值爆炸
                ratios.append(l1 / l0)
            d0, d1 = e0[i] - r0[i], e0[j] - r0[j]
            if d0.length > 1e-6 and d1.length > 1e-6:
                c = max(-1.0, min(1.0, d0.normalized().dot(d1.normalized())))
                angles.append(math.degrees(math.acos(c)))
        nf = tot = 0
        for pi, pg in enumerate(ob.data.polygons):
            if all(pred(r0[v]) for v in pg.vertices):
                tot += 1
                if rn[pi].dot(en[pi]) < 0:
                    nf += 1
        ratios.sort()
        out[rk] = {"n_edges": len(ratios),
                   "max_ratio": round(max(ratios), 3) if ratios else None,
                   "p95_ratio": round(ratios[int(0.95 * (len(ratios) - 1))], 3) if ratios else None,
                   "min_ratio": round(min(ratios), 3) if ratios else None,
                   "n_ratio_gt5": sum(1 for r in ratios if r > 5.0),
                   "n_ratio_lt0.2": sum(1 for r in ratios if r < 0.2),
                   "n_edges_disp_gt90deg": sum(1 for a in angles if a > 90.0),
                   "n_faces": tot, "normal_flip_faces": nf}
    return out


p("B2_extreme_poses", {k: [f"{a} {b} {c}deg" for a, b, c in v] for k, v in EXT_POSES.items()})
p("B2_extreme_regions", list(REGIONS))
p("B2_extreme_side_lock_on", {k: extreme_stats(b, k) for k in EXT_POSES})

# 关掉 side_lock 重绑 Body 再测（只在内存里）
for g in list(b.vertex_groups):
    b.vertex_groups.remove(g)
for m in list(b.modifiers):
    if m.type == 'ARMATURE':
        b.modifiers.remove(m)
b.parent = None
body_bones = [n for n, *_ in rig.BONES if not rig.is_finger(n)]
rig.weight_nearest_banded(b, arm, body_bones, power=4.0, keep=3,
                          allow=rig.body_allow, side_lock=False)
p("B2_extreme_side_lock_off", {k: extreme_stats(b, k) for k in EXT_POSES})

# 恢复 side_lock=True（与 m5_rig 一致）
for g in list(b.vertex_groups):
    b.vertex_groups.remove(g)
for m in list(b.modifiers):
    if m.type == 'ARMATURE':
        b.modifiers.remove(m)
b.parent = None
rig.weight_nearest_banded(b, arm, body_bones, power=4.0, keep=3,
                          allow=rig.body_allow, side_lock=True)
bw = wmap(b)
restc[b.name] = rest_pts(b)

# ---------------------------------------------------------------- 9. B3 指尖 vs distal tail

reset_pose()
rig.apply_pose(arm, "wave")
bpy.context.view_layer.update()
hc, _ = eval_mesh(hs)
tips = {}
worst_min = 0.0
for suf in (".L", ".R"):
    for fname in ("index", "middle", "ring", "pinky"):
        bn = f"{fname}_distal{suf}"
        if bn not in arm.pose.bones or bn not in hs.vertex_groups:
            tips[bn] = "MISSING"
            continue
        gi = hs.vertex_groups[bn].index
        idxs = [v.index for v in hs.data.vertices
                if any(g.group == gi and g.weight > 0.5 for g in v.groups)]
        tail = arm.matrix_world @ arm.pose.bones[bn].tail
        head = arm.matrix_world @ arm.pose.bones[bn].head
        ds = sorted((hc[i] - tail).length for i in idxs)
        if not ds:
            tips[bn] = "EMPTY GROUP"
            continue
        tips[bn] = {"n": len(idxs), "min_mm": mm(ds[0]), "max_mm": mm(ds[-1]),
                    "bone_len_mm": mm((tail - head).length)}
        worst_min = max(worst_min, ds[0])
p("B3_fingertip_dist_to_tail_wave", tips)
p("B3_worst_min_dist_mm", mm(worst_min))

rig.apply_pose(arm, "rest")
bpy.context.view_layer.update()
hc0, _ = eval_mesh(hs)
tips_rest = {}
for suf in (".L", ".R"):
    for fname in ("index", "middle", "ring", "pinky"):
        bn = f"{fname}_distal{suf}"
        if bn not in hs.vertex_groups:
            continue
        gi = hs.vertex_groups[bn].index
        idxs = [v.index for v in hs.data.vertices
                if any(g.group == gi and g.weight > 0.5 for g in v.groups)]
        if not idxs:
            continue
        tail = arm.matrix_world @ arm.pose.bones[bn].tail
        ds = sorted((hc0[i] - tail).length for i in idxs)
        tips_rest[bn] = {"min_mm": mm(ds[0]), "max_mm": mm(ds[-1])}
p("B3_fingertip_dist_to_tail_rest", tips_rest)

# ---------------------------------------------------------------- 10. 手部边长畸变


def hand_edge_ratio(pose_fn):
    rig.apply_pose(arm, "rest")
    bpy.context.view_layer.update()
    r0, _ = eval_mesh(hs)
    pose_fn()
    p1, _ = eval_mesh(hs)
    er = []
    for e in hs.data.edges:
        i, j = e.vertices
        l0 = (r0[i] - r0[j]).length
        l1 = (p1[i] - p1[j]).length
        if l0 > 1e-4:
            er.append(l1 / l0)
    er.sort()
    return {"n": len(er), "max": round(max(er), 3),
            "p95": round(er[int(0.95 * (len(er) - 1))], 3),
            "min": round(min(er), 3), "n_gt1.5": sum(1 for r in er if r > 1.5),
            "n_lt0.6": sum(1 for r in er if r < 0.6)}


p("B3_hand_edge_ratio_wave", hand_edge_ratio(lambda: rig.apply_pose(arm, "wave")))
p("B3_hand_edge_ratio_fingerbend", hand_edge_ratio(apply_finger_bend),
  "临时姿势：index_proximal.L -45° + index_middle.L -30°（wave 下该指标恒为 1.0，无区分度）")

# ---------------------------------------------------------------- 11. 腕部接缝（固定 rest 腕部顶点索引）


def wrist_seam():
    reset_pose()
    bpy.context.view_layer.update()
    hp, _ = eval_mesh(hs)
    idx = [i for i, q in enumerate(hp) if 0.812 <= q.z <= 0.824 and abs(q.x) > 0.15]
    res = {"n_fixed_verts": len(idx)}
    for pose in ("rest", "wave"):
        if pose == "rest":
            reset_pose()
        else:
            rig.apply_pose(arm, pose)
        bpy.context.view_layer.update()
        bp, _ = eval_mesh(b)
        hp2, _ = eval_mesh(hs)
        bvh = BVHTree.FromPolygons(bp, [tuple(pg.vertices) for pg in b.data.polygons])
        inside, outs = 0, []
        for i in idx:
            q = hp2[i]
            loc, nor, _, dist = bvh.find_nearest(q)
            if loc is None:
                continue
            if (q - loc).dot(nor) < 0:
                inside += 1
            else:
                outs.append(dist)
        res[pose] = {"inside": inside, "outside": len(outs),
                     "gap_min_mm": mm(min(outs)) if outs else None,
                     "gap_max_mm": mm(max(outs)) if outs else None}
    return res


p("wrist_seam_fixed_indices", wrist_seam(),
  "固定 rest 腕部 (z 0.812~0.824) 顶点索引；inside=仍插在前臂体积内")

# ---------------------------------------------------------------- 12. B1 副作用之二：腿是否穿出裙（径向法）


def poke(pose):
    rig.apply_pose(arm, pose)
    bpy.context.view_layer.update()
    bp, _ = eval_mesh(b)
    cp, _ = eval_mesh(cloth)
    SEG = cfg.RING_SEG
    rings = {}
    for q in cp:
        if q.z > 1.045 or q.z < 0.63:
            continue
        ang = int(((math.atan2(q.y - 0.006, q.x) + math.pi) / (2.0 * math.pi)) * SEG) % SEG
        k = round(q.z, 3)
        r = math.hypot(q.x, q.y - 0.006)
        rings.setdefault(k, {}).setdefault(ang, 0.0)
        rings[k][ang] = max(rings[k][ang], r)
    ks = sorted(rings)

    def skirt_r(z, ang):
        if not ks:
            return None
        if z <= ks[0]:
            return rings[ks[0]].get(ang)
        if z >= ks[-1]:
            return rings[ks[-1]].get(ang)
        for a, bb in zip(ks, ks[1:]):
            if a <= z <= bb:
                ra, rb = rings[a].get(ang), rings[bb].get(ang)
                if ra is None or rb is None:
                    return ra if rb is None else rb
                t = (z - a) / (bb - a)
                return ra * (1 - t) + rb * t
        return None

    n = n_out = 0
    worst = 0.0
    for q in bp:
        if not (0.66 <= q.z <= 1.03 and 0.03 < abs(q.x) < 0.16):
            continue
        ang = int(((math.atan2(q.y - 0.006, q.x) + math.pi) / (2.0 * math.pi)) * SEG) % SEG
        rs = skirt_r(q.z, ang)
        if rs is None:
            continue
        n += 1
        r = math.hypot(q.x, q.y - 0.006)
        if r > rs + 0.0005:
            n_out += 1
            worst = max(worst, r - rs)
    return {"n_body_verts": n, "outside(poke)": n_out, "max_poke_mm": mm(worst)}


p("B1_poke_rest", poke("rest"), "径向法：Body 腿区 r 与裙面同 z/同角度半径比较")
p("B1_poke_walk", poke("walk"))

# ---------------------------------------------------------------- 13. 收尾

rig.apply_pose(arm, "rest")
out_json = os.path.join(LOG_DIR, f"accept_b_{mode}.json")


def _san(o):
    if isinstance(o, dict):
        return {k: _san(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_san(v) for v in o]
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, Vector):
        return [round(v, 6) for v in o]
    return o


with open(out_json, "w", encoding="utf-8") as f:
    json.dump(_san(REC), f, ensure_ascii=False, indent=1)
print(f"[accb] done -> {out_json}")