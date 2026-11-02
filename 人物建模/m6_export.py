# -*- coding: utf-8 -*-
"""M6 / E4：剥离描边壳 → 单 PBR 材质 → 导出 glb → 回读校验与出图。

产物：
- out/美女.glb（骨架 + 蒙皮 + UV + basecolor 贴图）
- out/m6_before_export.png（导出前：原三渲二 + 描边）
- out/m6_glb_readback.png（回读后：glb 自带 PBR 材质）
- out/m6_asset_compare.png（左右对比）
- out/m6_e4.json
"""
import bpy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import asset
import sheet
import shots

SRC = os.path.join(HERE, "美女_asset.blend")
OUT = os.path.join(HERE, "out")
GLB = os.path.join(OUT, "美女.glb")
MESHES = ("Body", "Hands", "Head", "Hair", "Outfit")

bpy.ops.wm.open_mainfile(filepath=SRC)
print("[m6] source " + SRC)

# ---------- 导出前：原三渲二渲染 ----------
cam = bpy.data.objects.get("cam_rest")
shots.set_res(560, 900)
before = shots.render(cam, "m6_before_export.png")
print("[E4] before " + before)

# ---------- 剥离描边壳 + 换 PBR ----------
removed = {}
for name in MESHES:
    ob = bpy.data.objects.get(name)
    if ob is None:
        continue
    alb = os.path.join(OUT, "tex_" + name + "_basecolor.png")
    if not os.path.exists(alb):
        print("[E4] 缺少色板贴图: " + alb)
        continue
    removed[name] = asset.to_single_pbr(ob, alb)
    print("[E4] {0} 移除修改器={1} 材质={2}".format(
        name, removed[name], [m.name for m in ob.data.materials]))

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "美女_glb.blend"))
print("[m6] saved 美女_glb.blend")

objs = [bpy.data.objects.get(n) for n in MESHES]
objs.append(bpy.data.objects.get("Rig"))
glb = asset.export_glb(GLB, [o for o in objs if o is not None])
print("[E4] glb={0} size={1}B".format(glb, os.path.getsize(glb) if glb else 0))

# ---------- 回读 ----------
report = asset.readback(GLB)
print("[E4] readback " + json.dumps(report, ensure_ascii=False))

sc = bpy.context.scene
sc.view_settings.view_transform = 'Standard'
shots.setup_studio()
shots.set_res(560, 900)
cam2 = shots.camera("cam_glb", (2.3, -2.5, 1.0), (0, 0, 0.86), ortho_scale=1.85)
after = shots.render(cam2, "m6_glb_readback.png")
print("[E4] after " + after)

sheet.sheet(OUT, [os.path.basename(before), os.path.basename(after)],
            "m6_asset_compare.png")

weights = {}
for name in MESHES:
    ob = next((o for o in bpy.data.objects
               if o.type == "MESH" and o.name == name), None)
    if ob is not None:
        weights[name] = asset.weights_ok(ob)
print("[E4] weights " + json.dumps(weights))

summary = os.path.join(OUT, "m6_e4.json")
with open(summary, "w", encoding="utf-8") as f:
    json.dump({"removed": removed, "glb": glb,
               "glb_bytes": os.path.getsize(GLB) if glb else 0,
               "readback": report, "weights": weights}, f, ensure_ascii=False, indent=2)
print("[m6] report " + summary)

# ---------- 断言 ----------
fails = []


def check(ok, msg):
    print("[assert] {0} {1}".format("PASS" if ok else "FAIL", msg))
    if not ok:
        fails.append(msg)


check(glb is not None and os.path.getsize(GLB) > 500000,
      "glb exists ({0} B)".format(os.path.getsize(GLB) if glb else 0))
check(len(report["meshes"]) == 5, "meshes={0} (==5)".format(len(report["meshes"])))
check(sum(v["bones"] for v in report["armatures"].values()) == 45,
      "bones={0} (==45)".format(sum(v["bones"] for v in report["armatures"].values())))
for name, m in report["meshes"].items():
    check(bool(m["uv"]) and bool(m["materials"]) and m["armature_mod"],
          "{0} uv={1} mat={2} armature={3}".format(
              name, m["uv"], m["materials"], m["armature_mod"]))
for name, (bad, total) in weights.items():
    check(bad == 0, "{0} weightsum bad={1}/{2}".format(name, bad, total))
check(os.path.exists(os.path.join(OUT, "m6_asset_compare.png")),
      "compare png exists")

print("[assert] summary: {0} failed".format(len(fails)))
if fails:
    print("[assert] FAILED: " + json.dumps(fails, ensure_ascii=False))
    sys.exit(1)
print("[done] M6 E4")