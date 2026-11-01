# -*- coding: utf-8 -*-
"""临时诊断脚本：m5_rig 基线几何取证。

用途：为 DESIGN.md 附录提供可复现的量化基线（姿势是否真的驱动网格、
权重和是否归一、手部分叉数、鼻子前伸量、胸-衬衫净空、脚趾分叉）。
不参与建模，不被任何 m*.py 引用。

用法（在 人物建模/ 下）：
    "D:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b 美女.blend --python _probe/rig_probe.py
"""
import bpy
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))
import rig  # noqa: E402


def world_cos(ob, ev=True):
    dg = bpy.context.evaluated_depsgraph_get()
    if ev:
        o = ob.evaluated_get(dg)
        me = o.to_mesh()
        cos = [o.matrix_world @ v.co for v in me.vertices]
        o.to_mesh_clear()
        return cos
    return [ob.matrix_world @ v.co for v in ob.data.vertices]


def bb(cos):
    return (min(c.x for c in cos), max(c.x for c in cos),
            min(c.y for c in cos), max(c.y for c in cos),
            min(c.z for c in cos), max(c.z for c in cos))


def pbox(tag, cos):
    x0, x1, y0, y1, z0, z1 = bb(cos)
    print(f"[probe] {tag}: x[{x0:+.4f},{x1:+.4f}] y[{y0:+.4f},{y1:+.4f}] "
          f"z[{z0:+.4f},{z1:+.4f}] n={len(cos)}")


def x_segments(cos, lo, hi, side=1, gap=0.0025, xmin=None):
    sel = sorted(c.x for c in cos
                 if lo <= c.z <= hi and (c.x * side > 0)
                 and (xmin is None or abs(c.x) > xmin))
    if not sel:
        return 0, None, None, 0
    segs = 1
    for a, b in zip(sel, sel[1:]):
        if b - a > gap:
            segs += 1
    return segs, min(sel), max(sel), len(sel)


def front_y(cos, lo, hi, xmax=0.003):
    sel = [c.y for c in cos if abs(c.x) < xmax and lo <= c.z <= hi and c.y < 0]
    return (min(sel), len(sel)) if sel else (None, 0)


def xy_components(cos, lo, hi, side=1, cell=0.0020, xmin=0.02, r=0.0030):
    """把 z 切片投影到 (x,y) 网格做连通分量。

    两个必须注意的点（踩过）：
    1. 不能按 x 排序看间隙——闭合环在 x 方向天然断成两段，会误报。
    2. 必须对每个点做 r=3mm 膨胀。体素重网格后顶点间距约 5mm，裸栅格
       会把同一张连续面切成十几块（基线实测误报 17~103 个分量）。
    """
    pts = [(c.x * side, c.y) for c in cos
           if lo <= c.z <= hi and c.x * side > xmin]
    if not pts:
        return 0, 0
    steps = int(round(r / cell))
    keys = set()
    for x, y in pts:
        cx0, cy0 = int(x // cell), int(y // cell)
        for dx in range(-steps, steps + 1):
            for dy in range(-steps, steps + 1):
                keys.add((cx0 + dx, cy0 + dy))
    seen = set()
    comps = 0
    for k in keys:
        if k in seen:
            continue
        comps += 1
        stack = [k]
        seen.add(k)
        while stack:
            cx, cy = stack.pop()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nk = (cx + dx, cy + dy)
                    if nk in keys and nk not in seen:
                        seen.add(nk)
                        stack.append(nk)
    return comps, len(pts)


arm = bpy.data.objects["Rig"]
body = bpy.data.objects["Body"]
cloth = bpy.data.objects["Outfit"]

# ---------- 1. rest 全局包围盒 ----------
rig.apply_pose(arm, "rest")
for n in ("Body", "Outfit", "Head", "Hair"):
    pbox("rest_" + n, world_cos(bpy.data.objects[n]))

# ---------- 2. 四种姿势是否真的驱动了网格 ----------
for pose in ("rest", "wave", "walk", "reach"):
    rig.apply_pose(arm, pose)
    hn = arm.matrix_world @ arm.pose.bones["palm.L"].tail
    x0, x1, y0, y1, z0, z1 = bb(world_cos(body))
    print(f"[probe] pose={pose} handL_tail=({hn.x:+.4f},{hn.y:+.4f},{hn.z:+.4f}) "
          f"body_x[{x0:+.4f},{x1:+.4f}] body_z[{z0:+.4f},{z1:+.4f}]")

# ---------- 3. 权重和归一性 ----------
rig.apply_pose(arm, "rest")
for n in ("Body", "Outfit"):
    ob = bpy.data.objects[n]
    bad = 0
    mn, mx = 9.0, 0.0
    for v in ob.data.vertices:
        s = sum(g.weight for g in v.groups)
        mn = min(mn, s)
        mx = max(mx, s)
        if abs(s - 1.0) > 0.02:
            bad += 1
    print(f"[probe] weightsum {n}: bad={bad}/{len(ob.data.vertices)} "
          f"min={mn:.4f} max={mx:.4f}")

# ---------- 4. 手部分叉（手指数量代理指标） ----------
cos = world_cos(body, ev=False)
hcos = world_cos(bpy.data.objects["Head"], ev=False)
for lo, hi, tag in ((0.688, 0.700, "hand_tip"), (0.740, 0.752, "hand_palm")):
    segs, a, b, n = x_segments(cos, lo, hi, side=1, gap=0.0025, xmin=0.15)
    comps, m = xy_components(cos, lo, hi, side=1, cell=0.0020, xmin=0.15)
    print(f"[probe] {tag} z[{lo},{hi}] n={n} x_span=({a},{b}) "
          f"x_segments(不可信)={segs} xy_components={comps} pts={m}")

# ---------- 5. 鼻子前伸量（必须用 Head 顶点，Body 只到颈部） ----------
for lo, hi, tag in ((1.440, 1.470, "nose_tip"), (1.470, 1.520, "nose_bridge"),
                    (1.520, 1.570, "forehead")):
    y, n = front_y(hcos, lo, hi, xmax=0.003)
    print(f"[probe] {tag} z[{lo},{hi}] mid_front_y={y} n={n}")

# ---------- 6. 胸-衬衫净空 ----------
# 正面朝 -Y：y 越小越靠前。安全余量 = body_y - shirt_y > 0。
ccos = world_cos(cloth, ev=False)
for lo, hi in ((1.100, 1.140), (1.140, 1.180), (1.180, 1.220)):
    by, _ = front_y(cos, lo, hi, xmax=0.030)
    cy, _ = front_y(ccos, lo, hi, xmax=0.030)
    if by is not None and cy is not None:
        print(f"[probe] chest z[{lo},{hi}] body_y={by:+.4f} shirt_y={cy:+.4f} "
              f"margin(body-shirt)={by - cy:+.4f} {'穿模' if by - cy < 0 else '安全'}")

# ---------- 7. 脚趾分叉 ----------
for lo, hi, tag in ((0.008, 0.020, "toe"), (0.040, 0.070, "instep")):
    comps, m = xy_components(cos, lo, hi, side=1, cell=0.0020, xmin=0.02)
    segs, a, b, n = x_segments(cos, lo, hi, side=1, gap=0.0025, xmin=0.02)
    print(f"[probe] {tag} z[{lo},{hi}] n={n} x_span=({a},{b}) "
          f"x_segments(不可信)={segs} xy_components={comps} pts={m}")

# ---------- 8. 比例量测 ----------
hb = bb(hcos)
bodyb = bb(cos)
hairb = bb(world_cos(bpy.data.objects["Hair"], ev=False))
top = hb[5]
bottom = bodyb[4]
head_len = top - 1.375
print(f"[probe] ratio top(head skull)={top:+.4f} foot_bottom={bottom:+.4f} "
      f"stature={top - bottom:.4f} head_len={head_len:.4f} "
      f"heads={((top - bottom) / head_len):.2f}")
print(f"[probe] ratio hair_z_max={hairb[5]:+.4f} (呆毛高出头顶 {hairb[5] - top:+.4f})")
print(f"[probe] ratio head_width={hb[1] - hb[0]:.4f} head_depth={hb[3] - hb[2]:.4f}")
print(f"[probe] ratio foot_below_floor={bottom:+.4f} (负值=脚陷进 z=0 地板)")

# ---------- 9. 串权与裙摆跟随 ----------
def group_weights(ob):
    names = {g.index: g.name for g in ob.vertex_groups}
    out = []
    for v in ob.data.vertices:
        out.append({names[g.group]: g.weight for g in v.groups})
    return out

bw = group_weights(body)
# B3 之后 hand.L/R 已被 palm.L/R + 24 根指骨取代（指骨不影响 Body 权重）
r_side = {"thigh.R", "shin.R", "foot.R", "toe.R", "upper_arm.R", "forearm.R",
          "palm.R", "shoulder.R"}
l_side = {"thigh.L", "shin.L", "foot.L", "toe.L", "upper_arm.L", "forearm.L",
          "palm.L", "shoulder.L"}
leak = 0
leak_z = []
for v, w in zip(body.data.vertices, bw):
    if v.co.x > 0.030 and sum(w.get(n, 0.0) for n in r_side) > 0.10:
        leak += 1
        leak_z.append(v.co.z)
    if v.co.x < -0.030 and sum(w.get(n, 0.0) for n in l_side) > 0.10:
        leak += 1
        leak_z.append(v.co.z)
if leak_z:
    leak_z.sort()
    print(f"[probe] cross_side_leak Body: {leak}/{len(body.data.vertices)} "
          f"({100.0 * leak / len(body.data.vertices):.2f}%) "
          f"z_range=[{leak_z[0]:.3f},{leak_z[-1]:.3f}] z_median={leak_z[len(leak_z) // 2]:.3f}")
else:
    print(f"[probe] cross_side_leak Body: 0/{len(body.data.vertices)}")

cw = group_weights(cloth)
skirt = {}
skirt_total = 0
for v, w in zip(cloth.data.vertices, cw):
    if v.co.z < 1.040:
        skirt_total += 1
        top = max(w.items(), key=lambda kv: kv[1])[0] if w else "none"
        skirt[top] = skirt.get(top, 0) + 1
arm_lead = sum(n for b, n in skirt.items()
               if b.startswith(("hand.", "palm.", "forearm.", "upper_arm.", "shoulder.")))
print(f"[probe] skirt_dominant_bone(z<1.04): total={skirt_total} "
      f"arm_led={arm_lead} ({100.0 * arm_lead / max(1, skirt_total):.1f}%) "
      f"{sorted(skirt.items(), key=lambda t: -t[1])}")

print("[probe] done")