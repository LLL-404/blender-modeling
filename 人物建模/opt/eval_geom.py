# -*- coding: utf-8 -*-
"""opt/eval_geom.py —— 单次几何评估（在 Blender 进程内跑）。

职责：给一组参数，重建整个角色几何（不渲染、不存 blend），量出
「裙腰净空 / 屈指边长比 / 腕部台阶 / 权重健康度」四类指标，算出一个标量 score，
并把「参数 + 指标 + score」追加写进 opt/trials.jsonl。

口径纪律（每一条都是踩过坑之后写死的，别随手改）：
  * 每次评估**必须**从头重建：`shots.reset()` 内部就是
    `bpy.ops.wm.read_factory_settings(use_empty=True)`，绝不复用上一轮场景
    （复用会让材质/顶点组/骨骼残留，指标无从归因）。
  * 构建顺序照 m5_rig.py：look.set_all → head.build → flatten_face → body.build
    → look.bind_hands → hair.build → outfit.build → rig.build_armature → rig.bind_all。
    **不渲染、不存 blend**（绝不碰共享的 美女.blend）。
  * 屈指边长比先按「rest 边长 < 1mm 的边」过滤：2mm 体素 remesh 会产生 0.18~0.6mm
    的退化边，它们长度比的分母只有零点几毫米，会把 max 污染成 30× 量级。
  * 裙腰 net 直接取 `outfit.LAST_SKIRT_NETS`（outfit.build 内部 assert_skirt_clearance
    已经算过一遍），省掉重复构建躯干参数面；取不到时才复算一遍兜底。
  * 进程内只用 numpy，**不 import scipy**。

用法（工作目录 人物建模/）：
    blender -b --factory-startup --python opt/eval_geom.py            # 默认参数
    blender -b --factory-startup --python opt/eval_geom.py -- \
        --params '{"skirt_margin":0.004,"skirt_inner_mode":"valley"}'
    # 也可以被 opt/search.py import：evaluate(params, index=..., label=...)
"""
import argparse
import json
import math
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, ROOT, os.path.join(ROOT, "lib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np          # noqa: E402  (Blender 自带 numpy)
import bpy                  # noqa: E402

import optio                # noqa: E402  (lib/optio.py)
import space_geom           # noqa: E402  (opt/space_geom.py)

TRIALS_PATH = os.path.join(HERE, "trials.jsonl")

# ---------------- 判定门限（与任务书一致，集中在此便于复核） ----------------
HARD = {
    "skirt_net_min": 0.002,          # 米：裙腰四段 net 全部 >= +2mm
    "wrist_step": 0.003,             # 米：腕部径向台阶（宽、厚两向）
    "skirt_arm_led_pct": 5.0,        # %：裙摆 z<1.04 手臂骨主导比例
    "cross_side_leak_pct": 0.2,      # %：Body 左右串权
}
SOFT = {
    "loose_free_mm": 8.0,            # 裙腰 net 超 8mm 开始罚（防麻袋）
    "finger_min": 0.6,               # 屈指 min 边长比目标
    "finger_p95": 1.5,
    "finger_max": 2.5,
}
FINGER_REST_MIN = 0.001              # 米：rest 边长 <1mm 的边不计入比值统计

# walk 姿势下「腿/臀顶点越出裙面」的口径（与 _stageB/b_probe.py:372-424 逐字一致）。
# 为什么它是硬约束：这是 B 阶段**已经达标**的判据，参数搜索把裙腰收紧会让它退化
# （实测 margin 5mm + peak 口径下 worst=4.11mm/2 个顶点），不能为了 soft 分而牺牲。
LEG_LEAD = {"hips", "spine", "thigh.L", "thigh.R", "shin.L", "shin.R",
            "foot.L", "foot.R", "toe.L", "toe.R"}
NB_ANG = 72
LEAK_MAX_N = 5          # b_probe 判据：越出顶点数 <= 5
LEAK_MAX_MM = 2.0       # 且最大越出量 <= 2mm


# ================================================================ 构建

def build_scene():
    """按 m5_rig.py 的顺序重建一整套几何 + 骨架绑定，返回对象字典。"""
    import shots
    import look
    import head as headmod
    import body as bodymod
    import hair as hairmod
    import outfit as outfitmod
    import rig

    shots.reset()                       # = read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.view_settings.view_transform = 'Standard'

    M = look.set_all()
    h = headmod.build(M)
    look.flatten_face(h)
    b = bodymod.build()
    look.bind_hands(M)                  # Hands 是 body.build() 内另建的独立物体
    b.data.materials.append(M["skin"])
    hair = hairmod.build(M)
    cloth = outfitmod.build(M)

    arm = rig.build_armature()
    hands = bpy.data.objects.get("Hands")
    rig.bind_all(b, cloth, h, hair, hands, arm, side_lock=True)
    return {"body": b, "cloth": cloth, "head": h, "hair": hair,
            "hands": hands, "arm": arm}


# ================================================================ 几何小工具

def world_cos(ob):
    mw = ob.matrix_world
    return [mw @ v.co for v in ob.data.vertices]


def eval_mesh(ob):
    """depsgraph 求值后的 (世界坐标, 边长, 顶点数)。"""
    dg = bpy.context.evaluated_depsgraph_get()
    oe = ob.evaluated_get(dg)
    me = oe.to_mesh()
    mw = oe.matrix_world
    cos = [mw @ v.co for v in me.vertices]
    el = [(cos[e.vertices[0]] - cos[e.vertices[1]]).length for e in me.edges]
    n = len(me.vertices)
    oe.to_mesh_clear()
    return cos, el, n


def drop(ob):
    if ob is None:
        return
    me = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    if me is not None:
        try:
            bpy.data.meshes.remove(me)
        except Exception:
            pass


def band_extent(cos, zlo, zhi, cx, cy, xmax=None):
    """带内顶点相对轴心 (cx, cy) 的最大 |Δx| / |Δy|，返回 (dx, dy, n)。

    与 _stageA/a1_hand_probe.py 的口径逐字一致，便于两边数字直接对照。
    """
    mx = my = 0.0
    n = 0
    for c in cos:
        if not (zlo <= c.z <= zhi):
            continue
        if xmax is not None and abs(c.x - cx) > xmax:
            continue
        n += 1
        mx = max(mx, abs(c.x - cx))
        my = max(my, abs(c.y - cy))
    return mx, my, n


# ================================================================ 指标

def skirt_net_metrics(outfitmod):
    """裙腰四段 net（米）—— 优先取 build 时 assert_skirt_clearance 的实测值。"""
    bands = list(outfitmod.SKIRT_WAIST_BANDS)
    d = outfitmod.LAST_SKIRT_NETS
    if any(b not in d for b in bands):
        # 兜底：build 之外单独跑一遍 _skirt(solid=False)，它内部会重填 LAST_SKIRT_NETS
        sk = None
        try:
            sk = outfitmod._skirt(solid=False)
        finally:
            drop(sk)
        d = outfitmod.LAST_SKIRT_NETS
    nets = [d[b]["net"] if b in d else None for b in bands]
    rows = [d[b]["row"] if b in d else None for b in bands]
    return nets, rows


def wrist_metrics(body_cos, hand_cos, handmod):
    """腕部径向台阶（米），宽(y)/厚(x)两向，取左右手最大值。"""
    wz, wx, wy = handmod.WRIST_Z, handmod.WRIST_X, handmod.WRIST_Y
    lo, hi = wz - 0.005, wz + 0.005
    out = {"x": 0.0, "y": 0.0, "detail": {}}
    for side, tag in ((-1, "R"), (1, "L")):
        ax, ay, an = band_extent(body_cos, lo, hi, wx * side, wy, xmax=0.040)
        px, py, pn = band_extent([c for c in hand_cos if c.x * side > 0.02],
                                 lo, hi, wx * side, wy)
        sx, sy = ax - px, ay - py
        out["x"] = max(out["x"], sx)
        out["y"] = max(out["y"], sy)
        out["detail"][tag] = {"step_x_mm": sx * 1000, "step_y_mm": sy * 1000,
                              "forearm_n": an, "palm_n": pn}
    return out


def weight_metrics(body, cloth, hands):
    """权重健康度：权重和 bad 计数 / 裙摆手臂骨主导比例 / Body 左右串权比例。"""
    def sum_bad(ob):
        bad = 0
        for v in ob.data.vertices:
            s = sum(g.weight for g in v.groups)
            if abs(s - 1.0) > 0.02:
                bad += 1
        return bad

    bad = {"Body": sum_bad(body), "Outfit": sum_bad(cloth),
           "Hands": sum_bad(hands)}

    import rig
    cnames = {g.index: g.name for g in cloth.vertex_groups}
    skirt_total = arm_led = 0
    for v in cloth.data.vertices:
        if v.co.z >= 1.040:
            continue
        skirt_total += 1
        if not v.groups:
            continue
        top = max(v.groups, key=lambda g: g.weight)
        if rig.is_arm_bone(cnames[top.group]):
            arm_led += 1

    lset = {g.index for g in body.vertex_groups if g.name.endswith(".L")}
    rset = {g.index for g in body.vertex_groups if g.name.endswith(".R")}
    bnames = {g.index: g.name for g in body.vertex_groups}
    leak = 0
    leads = []
    for v in body.data.vertices:
        grp = list(v.groups)
        leads.append(bnames[max(grp, key=lambda g: g.weight).group] if grp else "")
        if v.co.x > 0.030:
            if sum(g.weight for g in grp if g.group in rset) > 0.10:
                leak += 1
        elif v.co.x < -0.030:
            if sum(g.weight for g in grp if g.group in lset) > 0.10:
                leak += 1

    n_body = len(body.data.vertices) or 1
    return {"bad": bad,
            "wsum_bad": bad["Body"] + bad["Outfit"] + bad["Hands"],
            "skirt_verts": skirt_total,
            "skirt_arm_led": arm_led,
            "skirt_arm_led_pct": 100.0 * arm_led / max(1, skirt_total),
            "leak": leak,
            "cross_side_leak_pct": 100.0 * leak / n_body,
            "leads": leads}


def hem_leak_metric(rig, arm, cloth, body, leads, pose="walk"):
    """walk 姿势下腿/臀顶点越出裙面的数量与最大越出量（米）。

    口径与 _stageB/b_probe.py 的 hem_and_leak 一致：
      裙面半径按 (z 桶 5mm, 角度扇区 5°) 取最大径向 r；Body 顶点取 z∈[0.60,1.05]
      且主骨属于 LEG_LEAD；局部裙半径取相邻 z 桶 × 相邻 3 扇区的最大值；
      越出量 = r_body − r_skirt，>0.5mm 记一次。
    """
    rig.apply_pose(arm, pose)
    bpy.context.view_layer.update()
    ccos, _, _ = eval_mesh(cloth)
    bcos, _, _ = eval_mesh(body)
    rig.apply_pose(arm, "rest")
    bpy.context.view_layer.update()

    gmax = {}
    for c in ccos:
        kz = int(c.z / 0.005)
        ka = int((math.atan2(c.y, c.x) + math.pi) / (2.0 * math.pi) * NB_ANG) % NB_ANG
        r = math.hypot(c.x, c.y)
        gmax[(kz, ka)] = max(gmax.get((kz, ka), 0.0), r)

    n, worst = 0, 0.0
    for vi, c in enumerate(bcos):
        if not (0.60 <= c.z <= 1.05):
            continue
        if vi >= len(leads) or leads[vi] not in LEG_LEAD:
            continue
        kz = int(c.z / 0.005)
        ka = int((math.atan2(c.y, c.x) + math.pi) / (2.0 * math.pi) * NB_ANG) % NB_ANG
        rs = 0.0
        for dz in (-1, 0, 1):
            for da in (-1, 0, 1):
                rs = max(rs, gmax.get((kz + dz, (ka + da) % NB_ANG), 0.0))
        if rs <= 0.0:
            continue
        d = math.hypot(c.x, c.y) - rs
        if d > 0.0005:
            n += 1
            worst = max(worst, d)
    return n, worst


def apply_custom(rig, arm, items):
    """清空姿势后按 [(骨名, 轴, 度)] 施加世界轴旋转（与 b_probe 的 R4 同口径）。"""
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    for bone, axis, deg in items:
        rig.rot_bone(arm, bone, axis, deg)
    bpy.context.view_layer.update()


def finger_bend_metrics(rig, arm, hands):
    """屈指 45°/30° 下的手部边长比（rest 边长 >=1mm 的边才算）。

    姿势只在**本脚本内**临时构造，不写回 m5_rig.py（那是共享产物入口）。
    """
    rig.apply_pose(arm, "rest")
    bpy.context.view_layer.update()
    _, el_rest, _ = eval_mesh(hands)
    items = []
    for suf, sgn in ((".L", 1), (".R", -1)):
        for f in ("index", "middle", "ring", "pinky"):
            items.append((f"{f}_proximal{suf}", 'Y', sgn * 45))
            items.append((f"{f}_middle{suf}", 'Y', sgn * 30))
    apply_custom(rig, arm, items)
    _, el_cur, _ = eval_mesh(hands)
    rig.apply_pose(arm, "rest")
    bpy.context.view_layer.update()

    ratios = sorted(c / r for c, r in zip(el_cur, el_rest) if r >= FINGER_REST_MIN)
    n = len(ratios)
    if n == 0:
        return {"n": 0, "min": None, "p95": None, "max": None,
                "gt1_5": 0, "lt0_6": 0}
    return {"n": n,
            "min": ratios[0],
            "p95": ratios[min(n - 1, int(n * 0.95))],
            "max": ratios[-1],
            "gt1_5": sum(1 for r in ratios if r > 1.5),
            "lt0_6": sum(1 for r in ratios if r < 0.6)}


# ================================================================ 打分

def score_of(m):
    """score = 1e6·硬违规数 + 软代价（越小越好）。"""
    hard = 0
    nets = m["skirt_net_mm"]
    if any(x is None for x in nets) or min(nets) < HARD["skirt_net_min"] * 1000:
        hard += 1
    if m["wsum_bad"] != 0:
        hard += 1
    if max(m["wrist_step_x_mm"], m["wrist_step_y_mm"]) > HARD["wrist_step"] * 1000:
        hard += 1
    if m["skirt_arm_led_pct"] > HARD["skirt_arm_led_pct"]:
        hard += 1
    if m["cross_side_leak_pct"] > HARD["cross_side_leak_pct"]:
        hard += 1
    # 回归护栏：walk 姿势腿/臀越出裙面（B 阶段已达标，搜索不许把它弄坏）
    if (m.get("leak_walk_n", 0) > LEAK_MAX_N
            or m.get("leak_walk_worst_mm", 0.0) > LEAK_MAX_MM):
        hard += 1

    loose = sum(max(0.0, x - SOFT["loose_free_mm"]) for x in nets
                if x is not None) / 1000.0
    fmin = max(0.0, SOFT["finger_min"] - (m["finger_min"] or 0.0)) ** 2 * 4000.0
    fp95 = max(0.0, (m["finger_p95"] or 0.0) - SOFT["finger_p95"]) ** 2 * 400.0
    fmax = max(0.0, (m["finger_max"] or 0.0) - SOFT["finger_max"]) ** 2 * 400.0
    return hard, loose + fmin + fp95 + fmax


# ================================================================ 单次评估

def _p(key, value, fmt="{:.4f}"):
    print("[eval] " + key + "=" + (fmt.format(value) if isinstance(value, float)
                                   else str(value)))


def evaluate(params, index=None, label="", write=True):
    """评估一组参数。返回 {"params","metrics","hard","soft","score","t",...}。

    params=None 表示**不注入**，直接走 opt/best.json（用于验证注入链路真的生效）；
    其余情况用进程内 override（搜索器用），不会碰盘上的 best.json。

    构建/量测过程中任何异常都不会中断搜索：记 traceback 首末行 + score=1e9。
    """
    t0 = time.time()
    injection = "override" if params is not None else "best.json"
    if params is None:
        optio.reload()
        params = {d["key"]: optio.param(d["key"], d["default"])
                  for d in space_geom.DIMS}
    rec = {"i": index, "label": label, "params": dict(params),
           "injection": injection}
    metrics = {}
    err = None
    try:
        if injection == "override":
            optio.set_overrides(params)
        else:
            optio.set_overrides(None)     # 明确关掉进程内注入，走 best.json
            optio.reload()
        S = build_scene()

        import outfit as outfitmod
        import hand as handmod
        import rig as rigmod

        nets, rows = skirt_net_metrics(outfitmod)
        bcos = world_cos(S["body"])
        hcos = world_cos(S["hands"])
        wst = wrist_metrics(bcos, hcos, handmod)
        wm = weight_metrics(S["body"], S["cloth"], S["hands"])
        fb = finger_bend_metrics(rigmod, S["arm"], S["hands"])
        lk_n, lk_w = hem_leak_metric(rigmod, S["arm"], S["cloth"], S["body"],
                                    wm["leads"])

        nets_mm = [None if x is None else round(x * 1000, 3) for x in nets]
        metrics = {
            "skirt_net_mm": nets_mm,
            "skirt_net_min_mm": round(min(x for x in nets_mm if x is not None), 3),
            "skirt_loose_mm": round(sum(max(0.0, x - SOFT["loose_free_mm"])
                                        for x in nets_mm if x is not None), 3),
            "wrist_step_x_mm": round(wst["x"] * 1000, 3),
            "wrist_step_y_mm": round(wst["y"] * 1000, 3),
            "wsum_bad": wm["wsum_bad"],
            "wsum_bad_detail": wm["bad"],
            "skirt_arm_led_pct": round(wm["skirt_arm_led_pct"], 3),
            "cross_side_leak_pct": round(wm["cross_side_leak_pct"], 3),
            "leak_walk_n": lk_n,
            "leak_walk_worst_mm": round(lk_w * 1000, 3),
            "finger_edges": fb["n"],
            "finger_min": None if fb["min"] is None else round(fb["min"], 4),
            "finger_p95": None if fb["p95"] is None else round(fb["p95"], 4),
            "finger_max": None if fb["max"] is None else round(fb["max"], 4),
            "finger_gt1_5": fb["gt1_5"],
            "finger_lt0_6": fb["lt0_6"],
            "wrist_detail": wst["detail"],
            "skirt_rows_mm": [[[round(x * 1000, 2), round(v * 1000, 2)] for x, v in (r or [])]
                              for r in rows],
        }
        hard, soft = score_of(metrics)
        score = 1e6 * hard + soft
    except Exception:
        tb = traceback.format_exc()
        lines = [ln for ln in tb.strip().splitlines() if ln.strip()]
        err = {"head": lines[0] if lines else "",
               "tail": lines[-1] if lines else ""}
        hard, soft, score = 5, 0.0, 1e9
        print(f"[eval] error=1 traceback_head={err['head']}")
        print(f"[eval] traceback_tail={err['tail']}")

    dt = time.time() - t0
    rec.update({"metrics": metrics, "hard": hard, "soft": round(soft, 6),
                "score": round(score, 6), "t": round(dt, 2)})
    if err:
        rec["error"] = err

    _print_eval(rec)
    if write:
        append_trial(rec)
    return rec


def _print_eval(rec):
    """指标全部打印成 `[eval] key=value` 单行（search 的日志靠这个前缀抓）。"""
    for k, v in rec["params"].items():
        _p("param_" + k, v)
    m = rec["metrics"]
    if m:
        for i, x in enumerate(m["skirt_net_mm"]):
            _p(f"skirt_net_{i}", None if x is None else x, "{:+.2f}")
        _p("skirt_net_min", m["skirt_net_min_mm"], "{:+.2f}")
        _p("skirt_loose_mm", m["skirt_loose_mm"], "{:.2f}")
        _p("finger_min", m["finger_min"], "{:.4f}")
        _p("finger_p95", m["finger_p95"], "{:.4f}")
        _p("finger_max", m["finger_max"], "{:.4f}")
        _p("finger_edges", m["finger_edges"], "{}")
        _p("finger_gt1_5", m["finger_gt1_5"], "{}")
        _p("wrist_step_x", m["wrist_step_x_mm"], "{:+.2f}")
        _p("wrist_step_y", m["wrist_step_y_mm"], "{:+.2f}")
        _p("wsum_bad", m["wsum_bad"], "{}")
        _p("skirt_arm_led_pct", m["skirt_arm_led_pct"], "{:.2f}")
        _p("cross_side_leak_pct", m["cross_side_leak_pct"], "{:.3f}")
        _p("leak_walk_n", m["leak_walk_n"], "{}")
        _p("leak_walk_worst", m["leak_walk_worst_mm"], "{:+.2f}")
    _p("hard", rec["hard"], "{}")
    _p("soft", rec["soft"], "{:.4f}")
    _p("score", rec["score"], "{:.4f}")
    _p("t", rec["t"], "{:.2f}")


def append_trial(rec):
    os.makedirs(os.path.dirname(TRIALS_PATH), exist_ok=True)
    with open(TRIALS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")


# ================================================================ CLI

def _args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(prog="eval_geom")
    ap.add_argument("--params", default=None,
                    help="JSON 字符串；缺省用 space_geom.defaults()")
    ap.add_argument("--i", type=int, default=0)
    ap.add_argument("--label", default="cli")
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--use-best", action="store_true",
                    help="不注入任何参数，直接读 opt/best.json（验证注入链路）")
    return ap.parse_args(argv)


def main():
    a = _args()
    space_geom.verify_defaults()
    if a.use_best and a.params:
        print("[eval] --use-best 与 --params 互斥，按 --use-best 执行")
    if a.params and not a.use_best:
        params = json.loads(a.params)
    elif a.use_best:
        params = None
    else:
        params = space_geom.defaults()
    rec = evaluate(params, index=a.i, label=a.label, write=not a.no_write)
    print("[eval] done " + json.dumps(
        {"score": rec["score"], "params": rec["params"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()