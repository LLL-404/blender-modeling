# -*- coding: utf-8 -*-
"""B 阶段量测（不渲染）：权重分布 / 左右串权 / 骨数 / 顶点组 / 手是否跟姿势动。

两种运行模式，自动判别：
  1. `blender -b --factory-startup --python _stageB/b_probe.py`
     —— 场景为空，本脚本自己按 m5_rig 的同一序列构建并绑定（走的也是 rig.bind_all，
        所以与 m5_rig 不会漂移）。
  2. `blender -b 美女.blend --python _stageB/b_probe.py`
     —— 场景里已有 Rig，直接量已保存的结果（验证 blend 重开后的状态）。

环境变量 BPROBE_SIDE_LOCK=0 可关闭 B2 的左右侧向约束（默认为开，与 m5_rig.py 一致）。

关键口径（写死在这，避免以后漂移）：
  * B1 指标量的是 **Outfit（裙子）** 的 z<1.04 顶点，主导骨 = 该顶点权重最大的组。
    （Body 在 z<1.04 本来就有前臂顶点，被手臂骨主导是正确的，不能混在一起量。）
  * B2 指标量 **Body**：|x|>30mm 的顶点里，对侧骨权重和 >0.10 的记为一次串权。
  * 「手是否跟姿势走」只用 depsgraph evaluated bbox 的位移证明，不用跨机位像素差。
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "lib"))

import bpy
from mathutils import Vector

import rig

SIDE_LOCK = os.environ.get("BPROBE_SIDE_LOCK", "1") == "1"


# ---------------- 构建（仅 factory-startup 模式） ----------------

def build_scene():
    import shots
    import look
    import head as headmod
    import body as bodymod
    import hair as hairmod
    import assemble

    shots.reset()
    shots.setup_studio()
    M = look.set_all()
    h = headmod.build(M)
    look.flatten_face(h)
    b = bodymod.build()
    b.data.materials.append(M["skin"])
    hair = hairmod.build(M)
    # 2026-11-06 判定层修复：形制分发单源 lib/assemble（profile outfit.style，
    # env OUTFIT_STYLE 可覆写）——探针原来写死 lib/outfit.build（衬衫），在 v2
    # 默认形制（挂脖旗袍）下量的是**未被使用的回退形制**；R2 的裙摆判据只对
    # 有裙摆的形制有意义（见 R2 段的形制分支）。
    cloth = assemble.build_outfit(M)
    global OUTFIT_STYLE
    OUTFIT_STYLE = assemble.outfit_style()
    arm = rig.build_armature()
    hands = bpy.data.objects.get("Hands")
    rig.bind_all(b, cloth, h, hair, hands, arm, side_lock=SIDE_LOCK)
    return b, cloth, h, hair, hands, arm


OUTFIT_STYLE = "shirt"   # built 场景由 build_scene() 落；loaded 场景（美女.blend）无分支


if bpy.data.objects.get("Rig") is not None:
    mode = "loaded(美女.blend)"
    body = bpy.data.objects["Body"]
    cloth = bpy.data.objects["Outfit"]
    hairob = bpy.data.objects.get("Hair")
    handsob = bpy.data.objects.get("Hands")
    arm = bpy.data.objects["Rig"]
else:
    mode = "built"
    body, cloth, headob, hairob, handsob, arm = build_scene()

print(f"[bprobe] mode={mode} side_lock={SIDE_LOCK}")


# ---------------- 工具 ----------------

def wmap(ob):
    names = {g.index: g.name for g in ob.vertex_groups}
    out = []
    for v in ob.data.vertices:
        out.append({names[g.group]: g.weight for g in v.groups})
    return out


def weight_sum_bad(ob):
    bad, mn, mx = 0, 9.0, 0.0
    for v in ob.data.vertices:
        s = sum(g.weight for g in v.groups)
        mn = min(mn, s)
        mx = max(mx, s)
        if abs(s - 1.0) > 0.02:
            bad += 1
    return bad, mn, mx


def eval_cos(ob):
    """depsgraph 求值后的世界坐标（含骨架形变）。"""
    dg = bpy.context.evaluated_depsgraph_get()
    oe = ob.evaluated_get(dg)
    me = oe.to_mesh()
    mw = oe.matrix_world
    cos = [mw @ v.co for v in me.vertices]
    oe.to_mesh_clear()
    return cos


def bbox(cos):
    xs = [c.x for c in cos]
    ys = [c.y for c in cos]
    zs = [c.z for c in cos]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def bbox_corners(bb):
    x0, x1, y0, y1, z0, z1 = bb
    return [Vector((x0, y0, z0)), Vector((x1, y0, z0)), Vector((x0, y1, z0)),
            Vector((x1, y1, z0)), Vector((x0, y0, z1)), Vector((x1, y0, z1)),
            Vector((x0, y1, z1)), Vector((x1, y1, z1))]


def bbox_delta(ob):
    """rest → wave 的 evaluated bbox 位移（角点最大位移，正值 = 真的动了）。"""
    rig.apply_pose(arm, "rest")
    bpy.context.view_layer.update()
    c0 = bbox_corners(bbox(eval_cos(ob)))
    rig.apply_pose(arm, "wave")
    bpy.context.view_layer.update()
    c1 = bbox_corners(bbox(eval_cos(ob)))
    return max((a - b).length for a, b in zip(c0, c1)), bbox(eval_cos(ob))


# ---------------- 1. 骨架与顶点组 ----------------

bones = [b.name for b in arm.data.bones]
fingers = [n for n in bones if rig.is_finger(n)]
print(f"[bprobe] bones={len(bones)} fingers={len(fingers)} (验收 >=45)")
for suf in (".L", ".R"):
    vgs = [g.name for g in handsob.vertex_groups if g.name.endswith(suf)] if handsob else []
    bone_side = [n for n in bones if n.endswith(suf) and n.split(".")[0].startswith(
        ("palm", "index", "middle", "ring", "pinky"))]
    print(f"[bprobe] vgroups_hand{suf}: object={len(vgs)} bones={len(bone_side)} "
          f"(验收 >=13) {'PASS' if len(vgs) >= 13 else 'FAIL'}")
    missing = [n for n in bone_side if handsob and n not in [g.name for g in handsob.vertex_groups]]
    if missing:
        print(f"[bprobe] WARN vgroup missing for bones{suf}: {missing}")

# ---------------- 2. B1：裙摆主导骨 ----------------

cw = wmap(cloth)
skirt_total = 0
lead = {}
for v, w in zip(cloth.data.vertices, cw):
    if v.co.z < 1.040:
        skirt_total += 1
        top = max(w.items(), key=lambda kv: kv[1])[0] if w else "none"
        lead[top] = lead.get(top, 0) + 1
arm_led = sum(n for b, n in lead.items() if rig.is_arm_bone(b))
print(f"[bprobe] B1 skirt z<1.04 total={skirt_total} arm_led={arm_led} "
      f"({100.0 * arm_led / max(1, skirt_total):.2f}%) (验收 <=5%) "
      f"{'PASS' if skirt_total and arm_led / skirt_total <= 0.05 else 'FAIL'}")
print(f"[bprobe] B1 skirt lead_bones={sorted(lead.items(), key=lambda t: -t[1])}")
bad_set = {b for b in lead if b not in rig.HIP_BONES}
print(f"[bprobe] B1 skirt lead_outside_hipspinechest={sorted(bad_set)} "
      f"{'PASS' if not bad_set else 'FAIL'}")

# ---------------- 3. B2：左右串权 ----------------

bw = wmap(body)
r_side = {n for n in bones if n.endswith(".R")}
l_side = {n for n in bones if n.endswith(".L")}
leak, leak_z = 0, []
for v, w in zip(body.data.vertices, bw):
    if v.co.x > 0.030 and sum(w.get(n, 0.0) for n in r_side) > 0.10:
        leak += 1
        leak_z.append(v.co.z)
    if v.co.x < -0.030 and sum(w.get(n, 0.0) for n in l_side) > 0.10:
        leak += 1
        leak_z.append(v.co.z)
npct = 100.0 * leak / max(1, len(body.data.vertices))
zm = f"z_median={sorted(leak_z)[len(leak_z) // 2]:.3f}" if leak_z else "z_median=-"
print(f"[bprobe] B2 cross_side_leak Body={leak}/{len(body.data.vertices)} "
      f"({npct:.2f}%) {zm} (验收 <=0.2%) {'PASS' if npct <= 0.2 else 'FAIL'}")

# ---------------- 4. 权重和 ----------------

for ob in (body, cloth, handsob, hairob):
    if ob is None:
        continue
    bad, mn, mx = weight_sum_bad(ob)
    print(f"[bprobe] weightsum {ob.name}: bad={bad}/{len(ob.data.vertices)} "
          f"min={mn:.4f} max={mx:.4f} {'PASS' if bad == 0 else 'FAIL'}")

# ---------------- 5. Hands 是否挂上骨架 ----------------

if handsob is None:
    print("[bprobe] Hands: MISSING FAIL")
else:
    mods = [(m.name, m.type, getattr(m, "object", None) and m.object.name)
            for m in handsob.modifiers]
    has_arm = any(m.type == 'ARMATURE' for m in handsob.modifiers)
    print(f"[bprobe] Hands modifiers={mods} parent={handsob.parent.name if handsob.parent else None}")
    print(f"[bprobe] Hands has_ARMATURE={'PASS' if has_arm else 'FAIL'} "
          f"parent_ok={'PASS' if handsob.parent == arm else 'FAIL'}")

# ---------------- 6. 跟姿势动：depsgraph bbox Δ ----------------

for ob, label in ((body, "Body"), (handsob, "Hands")):
    if ob is None:
        continue
    d, bb1 = bbox_delta(ob)
    print(f"[bprobe] pose_delta {label}: rest->wave bbox_corner_max_delta="
          f"{d * 1000:.3f}mm (验收 >50mm) {'PASS' if d > 0.05 else 'FAIL'}")
    print(f"[bprobe] wave bbox {label} x[{bb1[0]:+.4f},{bb1[1]:+.4f}] "
          f"y[{bb1[2]:+.4f},{bb1[3]:+.4f}] z[{bb1[4]:+.4f},{bb1[5]:+.4f}]")

# ---------------- 7. 指尖 vs 远节骨 tail 误差（wave 姿势） ----------------

if handsob is not None and any(m.type == 'ARMATURE' for m in handsob.modifiers):
    rig.apply_pose(arm, "wave")
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    oe = handsob.evaluated_get(dg)
    me = oe.to_mesh()
    mw = oe.matrix_world
    ecos = [mw @ v.co for v in me.vertices]
    oe.to_mesh_clear()
    worst = 0.0
    for suf, side in ((".L", 1), (".R", -1)):
        for fname in ("index", "middle", "ring", "pinky"):
            bname = f"{fname}_distal{suf}"
            if bname not in arm.pose.bones:
                print(f"[bprobe] fingertip {bname}: MISSING BONE FAIL")
                continue
            gi = handsob.vertex_groups[bname].index
            idxs = [v.index for v in handsob.data.vertices
                    if any(g.group == gi and g.weight > 0.5 for g in v.groups)]
            if not idxs:
                print(f"[bprobe] fingertip {bname}: EMPTY GROUP FAIL")
                continue
            tail = arm.matrix_world @ arm.pose.bones[bname].tail
            ds = [(ecos[i] - tail).length for i in idxs]
            dmin, dmax = min(ds), max(ds)
            worst = max(worst, dmin)
            print(f"[bprobe] fingertip {bname}: n={len(idxs)} "
                  f"dist_to_tail min={dmin * 1000:.2f}mm max={dmax * 1000:.2f}mm")
    print(f"[bprobe] fingertip worst_min_dist={worst * 1000:.2f}mm "
          f"(验收 <=5mm) {'PASS' if worst <= 0.005 else 'FAIL'}")
    rig.apply_pose(arm, "rest")
    bpy.context.view_layer.update()

# ---------------- 8. A1 指尖分叉判据（B 阶段版，按新顶点组名复现） ----------------
# a1_hand_probe.py 用的是旧的「每指 1 组」(index_L)；B3 把粒度改成 3 段后组名变成
# index_proximal.L / _middle / _distal，旧脚本会取不到组。这里用新组名复现同一判据，
# 保证 A1 的「四指各自独立成峰」在 B 阶段仍然可测：
#   * 每指把 3 段的顶点并起来，取该指最末 5mm 的切片，投影 (x,y) 算连通分量（须 >=1）；
#   * 4 指合并再算一次（须 =4，证明四峰互不连通）。
# 口径与 A1 一致：r=3mm 圆盘膨胀 + 8 邻域，cell=0.5mm（裸栅格会把连续面切成假阳性）。
import numpy as _np


def _components(points, cell=0.0005, dilate=0.0030):
    if not points:
        return 0, 0
    xs = _np.array([p[0] for p in points])
    ys = _np.array([p[1] for p in points])
    r = int(round(dilate / cell))
    pad = r + 2
    i0, j0 = int(_np.floor(xs.min() / cell)), int(_np.floor(ys.min() / cell))
    nx = int(_np.ceil(xs.max() / cell)) - i0 + 1 + 2 * pad
    ny = int(_np.ceil(ys.max() / cell)) - j0 + 1 + 2 * pad
    grid = _np.zeros((nx, ny), dtype=bool)
    grid[_np.floor(xs / cell).astype(int) - i0 + pad,
         _np.floor(ys / cell).astype(int) - j0 + pad] = True
    dil = grid.copy()
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            if dx or dy:
                if dx * dx + dy * dy <= r * r:
                    dil |= _np.roll(_np.roll(grid, dx, 0), dy, 1)
    seen = _np.zeros_like(dil)
    cnt = 0
    for i in range(nx):
        if not dil[i].any():
            continue
        for j in range(ny):
            if not dil[i, j] or seen[i, j]:
                continue
            cnt += 1
            seen[i, j] = True
            st = [(i, j)]
            while st:
                a, b = st.pop()
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        aa, bb = a + da, b + db
                        if 0 <= aa < nx and 0 <= bb < ny and dil[aa, bb] and not seen[aa, bb]:
                            seen[aa, bb] = True
                            st.append((aa, bb))
    return cnt, len(points)


if handsob is not None:
    rig.apply_pose(arm, "rest")
    bpy.context.view_layer.update()
    hg = {g.index: g.name for g in handsob.vertex_groups}
    for suf in (".L", ".R"):
        tips = {}
        for fname in ("index", "middle", "ring", "pinky"):
            gi = [k for k, v in hg.items() if v.startswith(fname + "_") and v.endswith(suf)]
            if not gi:
                print(f"[bprobe] A1 tip5 {fname}{suf}: NO GROUP FAIL")
                continue
            idx = [v.index for v in handsob.data.vertices
                   if any(g.group in gi and g.weight > 0.5 for g in v.groups)]
            zl = min(handsob.data.vertices[i].co.z for i in idx)
            sel = [handsob.data.vertices[i].co for i in idx
                   if handsob.data.vertices[i].co.z <= zl + 0.005]
            tips[fname] = sel
            nc, np_ = _components([(c.x, c.y) for c in sel])
            print(f"[bprobe] A1 tip5 {fname}{suf}: n={len(idx)} tip5={len(sel)} "
                  f"xy_components={nc} {'PASS' if nc >= 1 else 'FAIL'}")
        if len(tips) == 4:
            nc, np_ = _components([(c.x, c.y) for g in tips.values() for c in g])
            print(f"[bprobe] A1 tip5_merged{suf}: xy_components={nc} pts={np_} "
                  f"(验收 =4) {'PASS' if nc == 4 else 'FAIL'}")

# =====================================================================
# 返工量测（R1~R4）。全部用 depsgraph evaluated mesh，不用像素差。
# =====================================================================

def eval_mesh(ob):
    """返回 (cos, edge_lengths, poly_normals)，均为世界坐标/世界法线。"""
    dg = bpy.context.evaluated_depsgraph_get()
    oe = ob.evaluated_get(dg)
    me = oe.to_mesh()
    mw = oe.matrix_world
    r3 = mw.to_3x3()
    cos = [mw @ v.co for v in me.vertices]
    el = [(cos[e.vertices[0]] - cos[e.vertices[1]]).length for e in me.edges]
    nors = [(r3 @ p.normal).normalized() for p in me.polygons]
    oe.to_mesh_clear()
    return cos, el, nors


def pose_and_update(name):
    rig.apply_pose(arm, name)
    bpy.context.view_layer.update()


# ---------------- R1：关键骨位移（几何判据，替代被机位污染的像素差） ----------------

KEY_BONES = ("palm.L", "palm.R", "foot.L", "foot.R", "head")
pose_and_update("rest")
rest_tail = {b: (arm.matrix_world @ arm.pose.bones[b].tail).copy()
             for b in KEY_BONES if b in arm.pose.bones}
print("[bprobe] R1 keybone_disp (rest 为基准，位移 = |pose tail - rest tail|)")
r1_ok = {}
for pose in ("wave", "walk", "reach"):
    pose_and_update(pose)
    disp = {}
    for b, p0 in rest_tail.items():
        p1 = arm.matrix_world @ arm.pose.bones[b].tail
        disp[b] = (p1 - p0).length
    mx = max(disp.values())
    r1_ok[pose] = mx >= 0.100
    print(f"[bprobe] R1 {pose}: " + " ".join(f"{b}={d * 1000:.1f}mm" for b, d in disp.items())
          + f" | max={mx * 1000:.1f}mm (验收 >=100mm) {'PASS' if mx >= 0.1 else 'FAIL'}")
print(f"[bprobe] R1 summary {'PASS' if all(r1_ok.values()) else 'FAIL'} {r1_ok}")

# ---------------- R2：裙摆跟随与穿模 ----------------

LEG_LEAD = {"hips", "spine", "thigh.L", "thigh.R", "shin.L", "shin.R",
            "foot.L", "foot.R", "toe.L", "toe.R"}


def hem_and_leak(pose):
    """hem 位移 vs 腿位移；以及 Body 腿/臀顶点越出裙面的数量/最大值。

    越出口径（写死，避免漂移）：
      * 裙面半径按 (z 桶 5mm, 角度扇区 5°) 索引取最大径向距离 r；
      * 腿/臀顶点取 Body 中 z∈[0.60,1.05] 且 |x|<0.17（排除手臂）；
      * 局部裙半径取相邻 z 桶 × 相邻 3 个扇区的最大值；
      * 越出量 = r_body − r_skirt，>0.5mm 记为一次越出。
    """
    pose_and_update(pose)
    rest_pose = pose == "rest"
    ccos, _, _ = eval_mesh(cloth)
    bcos, _, _ = eval_mesh(body)

    # 裙面索引
    NB_ANG = 72
    gmax = {}
    for c in ccos:
        kz = int(c.z / 0.005)
        ka = int((math.atan2(c.y, c.x) + math.pi) / (2 * math.pi) * NB_ANG) % NB_ANG
        r = math.hypot(c.x, c.y)
        gmax[(kz, ka)] = max(gmax.get((kz, ka), 0.0), r)

    leak, worst = 0, 0.0
    dbg = []
    for vi, c in enumerate(bcos):
        if not (0.60 <= c.z <= 1.05):
            continue
        # 只统计腿/臀骨主导的顶点 —— 用 |x|<0.17 会把上臂（x≈0.169）也框进来，
        # 实测那条正是最大的 58.5mm 假阳性来源。
        wv = bw[vi] if vi < len(bw) else {}
        lead = max(wv.items(), key=lambda kv: kv[1])[0] if wv else ""
        if lead not in LEG_LEAD:
            continue
        kz = int(c.z / 0.005)
        ka = int((math.atan2(c.y, c.x) + math.pi) / (2 * math.pi) * NB_ANG) % NB_ANG
        rs = 0.0
        for dz in (-1, 0, 1):
            for da in (-1, 0, 1):
                rs = max(rs, gmax.get((kz + dz, (ka + da) % NB_ANG), 0.0))
        if rs <= 0:
            continue
        d = math.hypot(c.x, c.y) - rs
        if d > 0.0005:
            leak += 1
            worst = max(worst, d)
            dbg.append((d, c.x, c.y, c.z, rs))
    dbg.sort(reverse=True)
    return ccos, bcos, leak, worst, dbg[:6]


def mean_disp(cos0, cos1, zlo, zhi, lead_ok=None):
    ds = [(a - b).length for i, (a, b) in enumerate(zip(cos0, cos1))
          if zlo <= b.z <= zhi and (lead_ok is None or
                                    (bw[i] and max(bw[i].items(), key=lambda kv: kv[1])[0] in lead_ok))]
    return sum(ds) / len(ds) if ds else 0.0


pose_and_update("rest")
c_rest, b_rest, leak_rest, worst_rest, dbg_rest = hem_and_leak("rest")
c_walk, b_walk, leak_walk, worst_walk, dbg_walk = hem_and_leak("walk")
print(f"[bprobe] R2 debug top_leak rest="
      + " ".join(f"(d={d*1000:.1f} x={x:.3f} y={y:.3f} z={z:.3f} rsk={rs:.3f})"
                  for d, x, y, z, rs in dbg_rest[:4]))
hem_disp = mean_disp(c_walk, c_rest, 0.0, 0.75)
# 腿位移取「与 hem 同一高度带」（z 0.60~0.78）：裙摆在 z 0.65~0.75，
# 拿裙摆去比整条腿（含膝下/脚踝）的位移是不公平比较，会把 ratio 压低一半。
leg_disp = mean_disp(b_walk, b_rest, 0.60, 0.78, lead_ok=LEG_LEAD)
leg_disp_full = mean_disp(b_walk, b_rest, 0.0, 0.78, lead_ok=LEG_LEAD)
print(f"[bprobe] R2 leg_disp same-band(z 0.60~0.78)={leg_disp * 1000:.2f}mm "
      f"full-leg(z<0.78)={leg_disp_full * 1000:.2f}mm (仅对照)")
ratio = hem_disp / leg_disp if leg_disp > 0 else 0.0
if OUTFIT_STYLE == "shirt":
    print(f"[bprobe] R2 hem_disp(z<0.75)={hem_disp * 1000:.2f}mm leg_disp={leg_disp * 1000:.2f}mm "
          f"ratio={ratio * 100:.2f}% (验收 >=20%) {'PASS' if ratio >= 0.20 else 'FAIL'}")
    print(f"[bprobe] R2 leak rest: n={leak_rest} worst={worst_rest * 1000:.2f}mm")
    print(f"[bprobe] R2 leak walk: n={leak_walk} worst={worst_walk * 1000:.2f}mm "
          f"(验收 <=5 个且 <=2mm) "
          f"{'PASS' if leak_walk <= 5 and worst_walk <= 0.002 else 'FAIL'}")
else:
    # 2026-11-06：裙摆跟随/越出判据只对「有裙摆」的形制（衬衫+A字裙回退）有意义；
    # 挂脖旗袍是直筒+双侧开衩——腿部经开衩外露是设计特征，越出判据不适用。
    # 旗袍的形制/净空验收在 qipao.build 自带的 [qipao][form]/[qipao][fit]（build
    # 日志）与 A4 服装净空探针。测量数字照打，只去判定标记（归 SKIP 类）。
    print(f"[bprobe] R2 hem_disp(z<0.75)={hem_disp * 1000:.2f}mm leg_disp={leg_disp * 1000:.2f}mm "
          f"ratio={ratio * 100:.2f}% (裙摆跟随判据仅衬衫形制适用)")
    print(f"[bprobe] R2 leak rest: n={leak_rest} worst={worst_rest * 1000:.2f}mm")
    print(f"[bprobe] R2 leak walk: n={leak_walk} worst={worst_walk * 1000:.2f}mm "
          f"(越出判据仅衬衫形制适用；qipao 形制验收见 [qipao][fit] 净空)")

# ---------------- R3：交叉姿势应变（B2 过杀检测） ----------------

# 绕 Y 轴正角会把向下的腿转向 -x：左腿外展（离中轴→+x）要 -35，
# 右腿内收（靠中轴→+x）也是 -15 —— 两腿同向摆，形成交叉。
CROSS_LO = [("thigh.L", 'Y', -35), ("thigh.R", 'Y', -15)]
CROSS_HI = [("thigh.L", 'Y', -60), ("thigh.R", 'Y', -30)]


def apply_custom(items):
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    for bone, axis, deg in items:
        rig.rot_bone(arm, bone, axis, deg)
    bpy.context.view_layer.update()


pose_and_update("rest")
cos_rest, el_rest, nor_rest = eval_mesh(body)
# 胯部区域：两端点都落在 |x|∈[20,55]mm 且 z∈[0.70,1.05]
HIP_X = (0.020, 0.055)
HIP_Z = (0.70, 1.05)
hip_edges = [e.index for e in body.data.edges
             if all(HIP_X[0] <= abs(cos_rest[i].x) <= HIP_X[1]
                    and HIP_Z[0] <= cos_rest[i].z <= HIP_Z[1]
                    for i in e.vertices)]
print(f"[bprobe] R3 hip_region edges={len(hip_edges)}/{len(body.data.edges)}")
for tag, items in (("35/15", CROSS_LO), ("60/30", CROSS_HI)):
    apply_custom(items)
    _, el_cur, nor_cur = eval_mesh(body)
    ratios = [el_cur[i] / el_rest[i] for i in hip_edges if el_rest[i] > 1e-9]
    ratios_sorted = sorted(ratios)
    mx = ratios_sorted[-1]
    n5 = sum(1 for x in ratios if x > 5.0)
    flips = [i for i, (a, b) in enumerate(zip(nor_rest, nor_cur)) if a.dot(b) < 0.0]
    flip = len(flips)
    if flips:
        fz = [cos_rest[v].z for i in flips for v in body.data.polygons[i].vertices]
        fx = [cos_rest[v].x for i in flips for v in body.data.polygons[i].vertices]
        print(f"[bprobe] R3 {tag} flip_region x[{min(fx):+.3f},{max(fx):+.3f}] "
              f"z[{min(fz):.3f},{max(fz):.3f}]")
    thr = 3.0 if tag == "35/15" else 4.0
    print(f"[bprobe] R3 cross {tag}: max_edge_ratio={mx:.3f} edges>5x={n5} "
          f"normal_flips={flip} (验收 max<={thr:.0f}x 且 flips=0) "
          f"{'PASS' if mx <= thr and flip == 0 else 'FAIL'}")
pose_and_update("rest")

# ---------------- R4：屈指应变（B3 硬折检测） ----------------

def finger_bend(prox=45, mid=30):
    items = []
    for suf, sgn in ((".L", 1), (".R", -1)):
        for f in ("index", "middle", "ring", "pinky"):
            items.append((f"{f}_proximal{suf}", 'Y', sgn * prox))
            items.append((f"{f}_middle{suf}", 'Y', sgn * mid))
    return items


if handsob is not None:
    pose_and_update("rest")
    _, el_rest_h, _ = eval_mesh(handsob)
    apply_custom(finger_bend(45, 30))
    _, el_cur_h, _ = eval_mesh(handsob)
    raw = sorted(((c / r, i) for i, (c, r) in enumerate(zip(el_cur_h, el_rest_h))
                  if r > 1e-9), reverse=True)
    rr = [x[0] for x in raw][::-1]
    n_edges = len(rr)
    p95 = rr[int(n_edges * 0.95)]
    mx = rr[-1]
    mn = rr[0]
    n15 = sum(1 for x in rr if x > 1.5)
    print(f"[bprobe] R4 finger_bend 45/30: edges={n_edges} "
          f"p95={p95:.3f} max={mx:.3f} min={mn:.3f} edges>1.5x={n15} "
          f"(验收 p95<=1.5 max<=2.5 min>=0.6) "
          f"{'PASS' if p95 <= 1.5 and mx <= 2.5 and mn >= 0.6 else 'FAIL'}")
    for ra, ei in raw[:2] + raw[-3:]:
        e = handsob.data.edges[ei]
        va, vb = handsob.data.vertices[e.vertices[0]], handsob.data.vertices[e.vertices[1]]
        ga = [handsob.vertex_groups[g.group].name for g in va.groups]
        gb = [handsob.vertex_groups[g.group].name for g in vb.groups]
        print(f"[bprobe] R4 worst edge#{ei} ratio={ra:.2f} len_rest={el_rest_h[ei] * 1000:.3f}mm "
              f"A={tuple(round(c, 3) for c in va.co)}{ga} B={tuple(round(c, 3) for c in vb.co)}{gb}")
    pose_and_update("rest")

print("[bprobe] done")