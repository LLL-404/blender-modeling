# -*- coding: utf-8 -*-
"""几何量测探针（通用版）：在 headless Blender 里对已绑定的角色做可复现验收。

放在项目内（如 <项目>/_probe/），不参与建模，不被任何 m*.py 引用。

用法：
    blender -b 角色.blend --python scripts/geometry_probe.py -- \
        --objects Body Outfit Head Hair \
        --arm Rig \
        --slice Body:0.688:0.700 --slice Body:0.740:0.752 \
        --front Head:1.44:1.47 \
        --clearance Body:Outfit:1.10:1.22 \
        --poses rest wave walk reach

无参数时打印默认四个物体的 bbox + 权重归一性，是最安全的默认行为。

关键约定（这两条是踩过的坑，改动前先读）：
  1. 判断分叉用 (x,y) 平面「膨胀 + 连通分量」，不要按 x 排序看间隙。
  2. 体素重网格后顶点间距约 5mm，裸栅格会假阳性，必须膨胀 r≈3mm。
"""
import bpy
import sys

DEFAULT_OBJECTS = ("Body", "Outfit", "Head", "Hair")


# ---------------- 基础 ----------------

def world_cos(ob, evaluated=True):
    """返回物体顶点世界坐标。evaluated=True 时含修改器/骨骼变形。"""
    dg = bpy.context.evaluated_depsgraph_get()
    if evaluated:
        o = ob.evaluated_get(dg)
        me = o.to_mesh()
        cos = [o.matrix_world @ v.co for v in me.vertices]
        o.to_mesh_clear()
        return cos
    return [ob.matrix_world @ v.co for v in ob.data.vertices]


def bbox(cos):
    return (min(c.x for c in cos), max(c.x for c in cos),
            min(c.y for c in cos), max(c.y for c in cos),
            min(c.z for c in cos), max(c.z for c in cos))


def print_bbox(tag, cos):
    x0, x1, y0, y1, z0, z1 = bbox(cos)
    print(f"[probe] {tag}: x[{x0:+.4f},{x1:+.4f}] y[{y0:+.4f},{y1:+.4f}] "
          f"z[{z0:+.4f},{z1:+.4f}] n={len(cos)}")


def slice_bounds(cos, z0, z1, xmin=None):
    """z 切片内的 x/y 范围。xmin 用于只取单侧（如只看右手 x>0.15）。"""
    sel = [c for c in cos if z0 <= c.z <= z1 and (xmin is None or c.x > xmin)]
    if not sel:
        return None
    return (min(c.x for c in sel), max(c.x for c in sel),
            min(c.y for c in sel), max(c.y for c in sel), len(sel))


def front_y(cos, z0, z1, xmax=0.003):
    """面中线最靠前的 y（正面朝 -Y 时越靠前 y 越小）。用于鼻子前伸量测。

    ⚠️ 必须传「头」的顶点：身体物体的 z 通常只到颈部，用错会得到 n=0。
    """
    sel = [c.y for c in cos if abs(c.x) < xmax and z0 <= c.z <= z1 and c.y < 0]
    return (min(sel), len(sel)) if sel else (None, 0)


# ---------------- 分叉检测 ----------------

def xy_components(cos, z0, z1, side=1, cell=0.0020, xmin=0.02, r=0.0030):
    """z 切片投影到 (x,y) 栅格后数连通分量（8 邻域）。

    单根管 → 1；5 根手指 → ≥4；脚趾 → ≥2。
    必须膨胀 r：体素重网格顶点间距≈5mm，裸栅格会把连续面切碎成几十块。
    不能用「按 x 排序看间隙」：闭合环在 x 方向天然断成两段。
    """
    pts = [(c.x * side, c.y) for c in cos
           if z0 <= c.z <= z1 and c.x * side > xmin]
    if not pts:
        return 0, 0
    steps = max(1, int(round(r / cell)))
    keys = set()
    for x, y in pts:
        cx0, cy0 = int(x // cell), int(y // cell)
        for dx in range(-steps, steps + 1):
            for dy in range(-steps, steps + 1):
                keys.add((cx0 + dx, cy0 + dy))
    seen, comps = set(), 0
    for k in keys:
        if k in seen:
            continue
        comps += 1
        stack, seen = [k], seen | {k}
        while stack:
            cx, cy = stack.pop()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nk = (cx + dx, cy + dy)
                    if nk in keys and nk not in seen:
                        seen.add(nk)
                        stack.append(nk)
    return comps, len(pts)


# ---------------- 绑定健康 ----------------

def weight_sum_check(ob):
    bad, mn, mx = 0, 9.0, 0.0
    for v in ob.data.vertices:
        s = sum(g.weight for g in v.groups)
        mn, mx = min(mn, s), max(mx, s)
        if abs(s - 1.0) > 0.02:
            bad += 1
    print(f"[probe] weightsum {ob.name}: bad={bad}/{len(ob.data.vertices)} "
          f"min={mn:.4f} max={mx:.4f}")


def group_weights(ob):
    names = {g.index: g.name for g in ob.vertex_groups}
    return [{names[g.group]: g.weight for g in v.groups} for v in ob.data.vertices]


def dominant_bone_report(ob, z0=None, z1=None):
    """统计某 z 区间内每个顶点的主导骨，暴露「权重无语义」问题。

    典型病：裙摆被手/前臂骨主导（因为裙摆外侧在手旁边）。
    """
    ws = group_weights(ob)
    tally, total = {}, 0
    for v, w in zip(ob.data.vertices, ws):
        if z0 is not None and v.co.z < z0:
            continue
        if z1 is not None and v.co.z > z1:
            continue
        total += 1
        top = max(w.items(), key=lambda kv: kv[1])[0] if w else "none"
        tally[top] = tally.get(top, 0) + 1
    arm_led = sum(n for b, n in tally.items()
                  if b.startswith(("hand.", "forearm.", "upper_arm.", "shoulder.")))
    print(f"[probe] dominant_bone {ob.name} z[{z0},{z1}]: total={total} "
          f"arm_led={arm_led} ({100.0 * arm_led / max(1, total):.1f}%) "
          f"{sorted(tally.items(), key=lambda t: -t[1])}")


# ---------------- 姿势驱动 ----------------

def pose_drive_report(arm, obj, poses):
    """验证姿势是否真的驱动了网格（不靠看图）。

    需要项目里的 rig 模块提供 apply_pose(arm, name)；否则手动设
    pose_bones[...].rotation_quaternion 后调用 view_layer.update()。
    """
    try:
        import rig
    except ImportError:
        print("[probe] pose_drive: 未找到 rig 模块，跳过（可手动 apply pose）")
        return
    for p in poses:
        rig.apply_pose(arm, p)
        b = bbox(world_cos(obj))
        hn = arm.matrix_world @ arm.pose.bones["hand.L"].tail
        print(f"[probe] pose={p} hand.L_tail=({hn.x:+.4f},{hn.y:+.4f},{hn.z:+.4f}) "
              f"body_x[{b[0]:+.4f},{b[1]:+.4f}] body_z[{b[4]:+.4f},{b[5]:+.4f}]")


# ---------------- 净空 / 穿模 ----------------

def clearance_report(inner, outer, z0, z1, xmax=0.03, bands=3):
    """逐 z 带比较 inner 与 outer 的最前 y，判断是否穿出。

    ⚠️ 符号约定：正面朝 -Y，y 越小越靠前。
       margin = inner_y - outer_y > 0  ⇒ inner 在 outer 之后 ⇒ 安全。
    """
    ci, co = world_cos(inner, False), world_cos(outer, False)
    step = (z1 - z0) / bands
    for k in range(bands):
        a, b = z0 + step * k, z0 + step * (k + 1)
        iy, _ = front_y(ci, a, b, xmax)
        oy, _ = front_y(co, a, b, xmax)
        if iy is None or oy is None:
            print(f"[probe] clearance z[{a:.2f},{b:.2f}] 无样本（检查 xmax 或物体）")
            continue
        m = iy - oy
        print(f"[probe] clearance z[{a:.2f},{b:.2f}] inner_y={iy:+.4f} "
              f"outer_y={oy:+.4f} margin={m:+.4f} {'穿模' if m < 0 else '安全'}")


# ---------------- 参数解析 ----------------

def parse_args(argv):
    """极简解析：--k v1 v2 或多值 --k a:b:c。避免依赖 argparse。"""
    opt = {"objects": list(DEFAULT_OBJECTS), "arm": None,
           "slice": [], "front": [], "clearance": [], "poses": []}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--arm" and i + 1 < len(argv):
            opt["arm"] = argv[i + 1]
            i += 2
        elif a in ("--slice", "--front", "--clearance") and i + 1 < len(argv):
            opt[a[2:]].append(argv[i + 1].split(":"))
            i += 2
        elif a in ("--objects", "--poses"):
            key = a[2:]
            vals, i = [], i + 1
            while i < len(argv) and not argv[i].startswith("--"):
                vals.append(argv[i])
                i += 1
            if vals:
                opt[key] = vals
        else:
            i += 1
    return opt


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opt = parse_args(argv)

    # 1) 包围盒 + 权重
    for n in opt["objects"]:
        ob = bpy.data.objects.get(n)
        if ob is None:
            print(f"[probe] 缺少物体 {n}")
            continue
        print_bbox(f"bbox_{n}", world_cos(ob))
        if ob.vertex_groups:
            weight_sum_check(ob)

    # 2) z 切片（含分叉）
    for parts in opt["slice"]:
        n, z0, z1 = parts[0], float(parts[1]), float(parts[2])
        ob = bpy.data.objects.get(n)
        if ob is None:
            continue
        cos = world_cos(ob, False)
        comps, pts = xy_components(cos, z0, z1)
        print(f"[probe] slice {n} z[{z0},{z1}] bounds={slice_bounds(cos, z0, z1)} "
              f"xy_components={comps} pts={pts}")

    # 3) 面中线前伸（鼻子等）
    for parts in opt["front"]:
        n, z0, z1 = parts[0], float(parts[1]), float(parts[2])
        ob = bpy.data.objects.get(n)
        if ob is None:
            continue
        y, cnt = front_y(world_cos(ob, False), z0, z1)
        print(f"[probe] front {n} z[{z0},{z1}] mid_front_y={y} n={cnt}")

    # 4) 净空
    for parts in opt["clearance"]:
        n_in, n_out, z0, z1 = parts[0], parts[1], float(parts[2]), float(parts[3])
        a, b = bpy.data.objects.get(n_in), bpy.data.objects.get(n_out)
        if a and b:
            clearance_report(a, b, z0, z1)

    # 5) 姿势驱动
    if opt["arm"] and opt["poses"]:
        arm = bpy.data.objects.get(opt["arm"])
        target = bpy.data.objects.get(opt["objects"][0])
        if arm and target:
            pose_drive_report(arm, target, opt["poses"])

    # 6) 主导骨（仅在被指定时跑，避免刷屏）
    print("[probe] done")


main()