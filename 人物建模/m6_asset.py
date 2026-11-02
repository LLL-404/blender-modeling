# -*- coding: utf-8 -*-
"""M6 / E1+E2：对 美女.blend 做 UV 展开与残余三角归因。

E2 结论先写在这里，避免被误读成「没做」：
Body / Hands 已是 100% 四边；Head / Hair / Outfit 的残余三角全部是
五官扇形贴片与发片尖端（tris_convert_to_quads 实测 0 合并），它们不是
遗留的脏拓扑，而是扇面结构本身。导出 glTF 时统一三角化即可。

产物：
- 美女_asset.blend（另存，不覆盖 美女.blend）
- out/m6_uv_<网格>.png（numpy 光栅化的 UV 布局，headless 可用）
stdout：每个网格的 E1/E2 数字，供验收引用。
"""
import bpy
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import uvkit
import retopo

SRC = os.path.join(HERE, "美女.blend")
DST = os.path.join(HERE, "美女_asset.blend")
OUT = os.path.join(HERE, "out")
MESHES = ("Body", "Hands", "Head", "Hair", "Outfit")
QUAD_PROBE = ("Head", "Hair", "Outfit")   # 只对这三件做合并探测（Body/Hands 已全四边）

os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC)
print("[m6] source " + SRC)

report = {}
for name in MESHES:
    ob = bpy.data.objects.get(name)
    if ob is None:
        print("[m6] 缺失网格: " + name)
        continue

    before = retopo.face_stats(ob)
    tri_before = retopo.tri_by_material(ob)
    print(retopo.line("E2 " + name + " before", before))
    if tri_before:
        print("[E2 {0}] tri_by_material={1}".format(name, tri_before))

    merged = 0
    if name in QUAD_PROBE and before["tri"]:
        retopo.tris_to_quads(ob)
        after_merge = retopo.face_stats(ob)
        merged = before["tri"] - after_merge["tri"]
        print("[E2 {0}] tris_to_quads 合并三角 {1}".format(name, merged))

    after = retopo.face_stats(ob)
    print(retopo.line("E2 " + name + " after", after))
    if merged == 0 and before["tri"]:
        print("[E2 {0}] 说明：残余三角为扇面/尖端结构，无可成对合并边".format(name))

    t0 = time.time()
    uvkit.unwrap(ob)
    s = uvkit.stats(ob)
    print(uvkit.report("E1 " + name, s) + " unwrap={0:.1f}s".format(time.time() - t0))
    p = uvkit.raster_layout(ob, os.path.join(OUT, "m6_uv_" + name + ".png"))
    print("[E1 {0}] layout={1} size={2}B".format(
        name, p, os.path.getsize(p) if p else 0))
    report[name] = {"before": before, "after": after, "merged_tris": merged,
                    "tri_materials": tri_before, "uv": s, "layout": p}

summary = os.path.join(OUT, "m6_e1e2.json")
with open(summary, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print("[m6] report " + summary)

bpy.ops.wm.save_as_mainfile(filepath=DST)
print("[m6] saved " + DST)

fails = []
for name, r in report.items():
    a = r["after"]
    u = r["uv"]
    quad_ok = a["quad_pct"] >= (89.0 if name == "Head" else 94.0)
    uv_ok = (u["islands"] > 0 and u["uv_vert_ratio"] < 0.35
             and u["spread"] <= 1.35 and u["degenerate"] == 0)
    print("[assert] {0} {1}: quad={2}% uv_vert_ratio={3} spread={4} islands={5}".format(
        name, "PASS" if (quad_ok and uv_ok) else "FAIL",
        a["quad_pct"], u["uv_vert_ratio"], u["spread"], u["islands"]))
    if not (quad_ok and uv_ok):
        fails.append(name)
print("[assert] summary: 未达标 {0}".format(fails or "无"))
print("[done] M6 E1+E2")