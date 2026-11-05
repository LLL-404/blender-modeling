# -*- coding: utf-8 -*-
"""只读探针：量头骨与 Body 颈柱在同一批 z 高度上的截面，定位头颈接缝。

不渲染、不保存 .blend、不改模型。产物 `out/neck_joint.json`。

用法：
    "D:/Program Files/Blender Foundation/Blender 5.2/blender.exe" \
        -b --factory-startup --python-exit-code 1 --python scripts/probe_neck_joint.py

背景
----
`lib/body.py:neck()` 用「颈柱顶 = 头骨第一环 z + 8mm」把脖子插进头里，
保证 z 方向不露缝；`lib/appearance.py` 的 `head_body_gap` 也只量 z 间隙。
但两者是**两个独立对象**（Body 走 5mm 体素重网格，Head 走控制笼+细分），
从来没有融合，截面形状也不匹配 —— 这条探针量的是「同一高度的横截面差」，
补上只量 z 间隙的判据盲区。
"""
import json
import os
import sys

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "lib"))

import body as bodymod   # noqa: E402
import head as headmod   # noqa: E402

OUT = os.path.join(ROOT, "out", "neck_joint.json")


def section_bbox(ob, z):
    """平面 z 与网格求交，返回交点包围盒（mm）。半开区间避免共享边重复。"""
    verts = [v.co.copy() for v in ob.data.vertices]
    faces = [list(p.vertices) for p in ob.data.polygons]
    pts = []
    for f in faces:
        hit = []
        for i in range(len(f)):
            a, b = verts[f[i]], verts[f[(i + 1) % len(f)]]
            if (a.z < z <= b.z) or (b.z < z <= a.z):
                t = (z - a.z) / (b.z - a.z)
                hit.append((a.x + t * (b.x - a.x), a.y + t * (b.y - a.y)))
        pts.extend(hit[:2] if len(hit) > 2 else hit)
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return {
        "n": len(pts),
        "w": round((max(xs) - min(xs)) * 1000.0, 2),
        "d": round((max(ys) - min(ys)) * 1000.0, 2),
        "xmin": round(min(xs) * 1000.0, 2), "xmax": round(max(xs) * 1000.0, 2),
        "ymin": round(min(ys) * 1000.0, 2), "ymax": round(max(ys) * 1000.0, 2),
    }


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    h = headmod.head_base()
    headmod.sculpt(h)
    b = bodymod.build()

    hz = [v.co.z for v in h.data.vertices]
    bz = [v.co.z for v in b.data.vertices]
    neck_band = [v.co.z for v in b.data.vertices
                 if abs(v.co.x) < 0.09 and abs(v.co.y) < 0.09]
    gap_mm = (min(hz) - max(neck_band)) * 1000.0

    zs = [1.4180, 1.4217, 1.4240, 1.4270, 1.4309, 1.4340,
          1.4380, 1.4450, 1.4550, 1.4700]
    rows = []
    for z in zs:
        a, c = section_bbox(h, z), section_bbox(b, z)
        rows.append({
            "z_mm": round(z * 1000.0, 2),
            "head": a, "body_neck": c,
            "d_w_mm": round(c["w"] - a["w"], 2) if a and c else None,
            "d_d_mm": round(c["d"] - a["d"], 2) if a and c else None,
        })

    doc = {
        "source": "head_base()+sculpt() vs body.build()（当前工作树）",
        "blender": bpy.app.version_string,
        "head_z_mm": [round(min(hz) * 1000, 2), round(max(hz) * 1000, 2)],
        "body_z_mm": [round(min(bz) * 1000, 2), round(max(bz) * 1000, 2)],
        "neck_top_z_mm": round(max(neck_band) * 1000, 2),
        "head_body_gap_mm": round(gap_mm, 2),
        "note": "负值 = 颈柱插进头骨；这只判 z 间隙，判不出截面形状是否匹配",
        "rows": rows,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)

    print("[joint] head z=[%.2f, %.2f] mm ; body z=[%.2f, %.2f] mm ; neck top=%.2f mm"
          % (doc["head_z_mm"][0], doc["head_z_mm"][1],
             doc["body_z_mm"][0], doc["body_z_mm"][1],
             doc["neck_top_z_mm"]))
    print("[joint] head_body_gap = %+.2f mm (negative = inserted, no visible gap)"
          % gap_mm)
    print("  z(mm)   HEAD w/d(mm)   NECK w/d(mm)   d_w     d_d")
    for r in rows:
        a, c = r["head"], r["body_neck"]
        print("  %7.2f   %-14s %-14s %7s %7s" % (
            r["z_mm"],
            "none" if a is None else "%.1f/%.1f" % (a["w"], a["d"]),
            "none" if c is None else "%.1f/%.1f" % (c["w"], c["d"]),
            "—" if r["d_w_mm"] is None else "%+.1f" % r["d_w_mm"],
            "—" if r["d_d_mm"] is None else "%+.1f" % r["d_d_mm"]))
    print("[joint] -> out/neck_joint.json")


if __name__ == "__main__":
    main()
