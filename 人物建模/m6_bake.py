# -*- coding: utf-8 -*-
"""M6 / E3：色板贴图 + AO 烘焙 + 法线一致性。

输入 美女_asset.blend（E1+E2 产物，已带 UV），输出：
- out/tex_<网格>_basecolor.png（1024，按材质槽填 UV 岛）
- out/tex_<网格>_ao.png（512，Cycles AO pass）
- out/m6_e3.json
环境变量 M6_ONLY 可限定网格（逗号分隔），默认五个全做。
"""
import bpy
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import bake

SRC = os.path.join(HERE, "美女_asset.blend")
OUT = os.path.join(HERE, "out")
MESHES = ("Body", "Hands", "Head", "Hair", "Outfit")
only = [s.strip() for s in (os.environ.get("M6_ONLY") or "").split(",") if s.strip()]
if only:
    MESHES = tuple(s for s in MESHES if s in only)

os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC)
print("[m6] source " + SRC)
print("[m6] meshes " + ",".join(MESHES))

report = {}
for name in MESHES:
    ob = bpy.data.objects.get(name)
    if ob is None or ob.type != "MESH":
        print("[m6] 跳过 " + name)
        continue

    t0 = time.time()
    nrm = bake.normals_report(ob)
    print("[E3 {0}] normals faces={1} flipped_fixed={2} ({3:.1f}s)".format(
        name, nrm["faces"], nrm["flipped"], time.time() - t0))

    t0 = time.time()
    alb = bake.palette_atlas(ob, os.path.join(OUT, "tex_" + name + "_basecolor.png"), 1024)
    print("[E3 {0}] basecolor={1} size={2}B ({3:.1f}s)".format(
        name, alb, os.path.getsize(alb) if alb else 0, time.time() - t0))

    t0 = time.time()
    ao = bake.bake_ao(ob, os.path.join(OUT, "tex_" + name + "_ao.png"), 512, 8)
    print("[E3 {0}] ao={1} size={2}B ({3:.1f}s)".format(
        name, ao, os.path.getsize(ao) if ao else 0, time.time() - t0))

    report[name] = {"normals": nrm, "basecolor": alb, "ao": ao}

bpy.context.scene.render.engine = 'BLENDER_EEVEE'
bpy.ops.wm.save_as_mainfile(filepath=SRC)
print("[m6] saved " + SRC)

summary = os.path.join(OUT, "m6_e3.json")
with open(summary, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print("[m6] report " + summary)

fails = []
for name, r in report.items():
    ok = (r["basecolor"] and os.path.getsize(r["basecolor"]) > 5000 and
          r["ao"] and os.path.getsize(r["ao"]) > 5000)
    print("[assert] {0} {1}: basecolor={2}B ao={3}B flipped_fixed={4}".format(
        name, "PASS" if ok else "FAIL",
        os.path.getsize(r["basecolor"]) if r["basecolor"] else 0,
        os.path.getsize(r["ao"]) if r["ao"] else 0, r["normals"]["flipped"]))
    if not ok:
        fails.append(name)
print("[assert] summary: 未达标 {0}".format(fails or "无"))
print("[done] M6 E3")