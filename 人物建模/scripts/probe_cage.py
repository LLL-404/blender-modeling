# -*- coding: utf-8 -*-
"""控制笼 vs 原放样壳：量细分收缩，验证 CAGE_GROW_X/Y 是否补到位。

用法（headless）：
    blender -b --factory-startup --python scripts/probe_cage.py

为什么要有这个探针
------------------
Catmull-Clark 会把控制笼往内收，收多少取决于环距/段数/曲率，不能凭经验拍一个
「1.05」。这里把四件事放在同一把尺子上量：

    BASE       原实现：59 环 × 48 段放样壳（改造前的基准）
    CAGE       稀疏控制笼，未细分、未补偿
    SUBD_RAW   裸笼（grow=1）+ 2 级细分 → 用它的跨度比反算补偿系数
    SUBD_FP    用 lib/head.py 里的 CAGE_GROW_X/Y 补偿后细分 → 应落回 BASE

判据只有一条：**SUBD_FP 的跨度与 BASE 相差 < 0.3%**。超了就是补偿没算对。
"""
import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import cfg                      # noqa: E402
import head                     # noqa: E402
from meshkit import loft, resample, superellipse_ring  # noqa: E402

OUT = os.path.join(HERE, "out")
AXES = ("x", "y", "z")


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def bbox(ob):
    vs = [v.co for v in ob.data.vertices]
    box = {ax: [min(getattr(v, ax) for v in vs), max(getattr(v, ax) for v in vs)]
           for ax in AXES}
    return {"bbox": box, "verts": len(ob.data.vertices),
            "faces": len(ob.data.polygons)}


def span(rec):
    return {ax: rec["bbox"][ax][1] - rec["bbox"][ax][0] for ax in AXES}


def fmt(name, rec):
    sp = span(rec)
    return "%-14s verts=%5d faces=%5d  span=%s  z=[%.5f,%.5f]" % (
        name, rec["verts"], rec["faces"],
        {k: round(v, 6) for k, v in sp.items()},
        rec["bbox"]["z"][0], rec["bbox"]["z"][1])


def base_shell():
    """改造前的实现，逐字复刻，作为基准。"""
    rows = resample(head.head_rows(), "z", 0.004)
    rings = [superellipse_ring(z, rx, ryf, cy, 0.0, p, cfg.RING_SEG, ry_back=ryb)
             for z, rx, ryf, ryb, cy, p in rows]
    return loft(rings, name="base")


reset()
rec_base = bbox(base_shell())
print("[cage] " + fmt("BASE", rec_base))

saved_grow = (head.CAGE_GROW_X, head.CAGE_GROW_Y)

reset()
head.CAGE_GROW_X = head.CAGE_GROW_Y = 1.0
rec_cage = bbox(head.head_cage())
print("[cage] " + fmt("CAGE(grow=1)", rec_cage))

reset()
head.CAGE_GROW_X = head.CAGE_GROW_Y = 1.0
cage = head.head_cage()
head.subdivide(cage)
rec_raw = bbox(cage)
print("[cage] " + fmt("SUBD_RAW", rec_raw))

head.CAGE_GROW_X, head.CAGE_GROW_Y = saved_grow
reset()
cage = head.head_cage()
head.subdivide(cage)
rec_fp = bbox(cage)
print("[cage] " + fmt("SUBD_FP", rec_fp))

sp_base, sp_raw, sp_fp = span(rec_base), span(rec_raw), span(rec_fp)
ratio = {ax: sp_raw[ax] / sp_base[ax] for ax in AXES}
grow = {ax: 1.0 / ratio[ax] for ax in AXES}
err = {ax: sp_fp[ax] / sp_base[ax] - 1.0 for ax in AXES}
worst = max(abs(v) for v in err.values())

print("[cage] 裸笼收缩比 = " + json.dumps(
    {k: round(v, 5) for k, v in ratio.items()}, ensure_ascii=False))
print("[cage] 反算补偿   = " + json.dumps(
    {k: round(v, 5) for k, v in grow.items()}, ensure_ascii=False))
print("[cage] 补偿后残差 = " + json.dumps(
    {k: "%+.4f%%" % (v * 100) for k, v in err.items()}, ensure_ascii=False))
print("[cage] 判定：最大残差 %.4f%%（要求 <0.3%%）→ %s" % (
    worst * 100, "PASS" if worst < 0.003 else "FAIL"))

os.makedirs(OUT, exist_ok=True)
p = os.path.join(OUT, "cage_probe.json")
with open(p, "w", encoding="utf-8") as f:
    json.dump({
        "base": rec_base, "cage": rec_cage, "subd_raw": rec_raw,
        "subd_compensated": rec_fp,
        "raw_ratio_subd_over_base": {k: round(v, 6) for k, v in ratio.items()},
        "suggested_grow": {k: round(v, 5) for k, v in grow.items()},
        "applied_grow": {"x": saved_grow[0], "y": saved_grow[1]},
        "residual": {k: round(v, 6) for k, v in err.items()},
        "verdict": "PASS" if worst < 0.003 else "FAIL",
        "cage_step": head.CAGE_STEP, "cage_seg": head.CAGE_SEG,
        "cage_subdiv": head.CAGE_SUBDIV,
    }, f, ensure_ascii=False, indent=2)
print("[cage] report " + p)
print("[done] cage probe")
