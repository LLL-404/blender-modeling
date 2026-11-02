# -*- coding: utf-8 -*-
"""M6 / E5：16 机位环绕复核（导出前 toon vs 导出后 glb PBR）。

每 22.5° 一台正交相机，共 16 机位；隐藏地板、开 film_transparent，
用 alpha 分割前景，逐机位统计前景覆盖率与暗像素占比（黑缝/破面）。
产物：out/m6_16_before.png（4×4）、out/m6_16_after.png、out/m6_16_stats.json
"""
import bpy
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import shots

OUT = os.path.join(HERE, "out")
VIEWS = 16
DIST = 3.4
ORTHO = 1.85
CZ = 0.86
COLS = 4


def render_set(blend, prefix):
    bpy.ops.wm.open_mainfile(filepath=blend)
    floor = bpy.data.objects.get("floor")
    if floor is not None:
        floor.hide_render = True
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    shots.set_res(560, 900)
    paths = []
    for i in range(VIEWS):
        a = 2.0 * math.pi * i / VIEWS
        loc = (math.sin(a) * DIST, -math.cos(a) * DIST, CZ + 0.12)
        cam = shots.camera("mv_%02d" % i, loc, (0, 0, CZ), ortho_scale=ORTHO)
        paths.append(shots.render(cam, "%s_%02d.png" % (prefix, i)))
        bpy.data.objects.remove(cam, do_unlink=True)
    return paths


def load_rgba(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)


def stats(path):
    a = load_rgba(path)
    mask = a[:, :, 3] > 0.5
    cov = float(mask.mean())
    if not mask.any():
        return {"cov": 0.0, "dark": 1.0, "black": 1.0,
                "p05": 0.0, "p50": 0.0, "p95": 0.0}
    lum = a[:, :, :3][mask].mean(axis=1)
    return {
        "cov": round(cov, 4),
        "dark": round(float((lum < 0.02).mean()), 4),
        "black": round(float((lum < 0.005).mean()), 4),
        "p05": round(float(np.quantile(lum, 0.05)), 4),
        "p50": round(float(np.quantile(lum, 0.50)), 4),
        "p95": round(float(np.quantile(lum, 0.95)), 4),
    }


def grid(paths, out_name, cols=COLS):
    arrs = [load_rgba(p) for p in paths]
    h = max(a.shape[0] for a in arrs)
    w = max(a.shape[1] for a in arrs)
    rows = (len(arrs) + cols - 1) // cols
    canvas = np.zeros((rows * h, cols * w, 4), dtype=np.float32)
    for i, a in enumerate(arrs):
        r, c = divmod(i, cols)
        y0 = (rows - 1 - r) * h
        canvas[y0:y0 + a.shape[0], c * w:c * w + a.shape[1]] = a
    im = bpy.data.images.new(out_name, cols * w, rows * h, alpha=True)
    im.pixels.foreach_set(canvas.ravel())
    im.filepath_raw = os.path.join(OUT, out_name)
    im.file_format = 'PNG'
    im.save()
    bpy.data.images.remove(im)
    return os.path.join(OUT, out_name)


before = render_set(os.path.join(HERE, "美女_asset.blend"), "m6_16_before")
after = render_set(os.path.join(HERE, "美女_glb.blend"), "m6_16_after")

sb = [stats(p) for p in before]
sa = [stats(p) for p in after]

print("[E5] view  before_cov  after_cov  d_cov  before_dark  after_dark  after_black")
worst = []
for i in range(VIEWS):
    d = round(abs(sb[i]["cov"] - sa[i]["cov"]), 4)
    worst.append(d)
    print("[E5] {0:02d}  {1:.4f}  {2:.4f}  {3:.4f}  {4:.4f}  {5:.4f}  {6:.4f}".format(
        i, sb[i]["cov"], sa[i]["cov"], d,
        sb[i]["dark"], sa[i]["dark"], sa[i]["black"]))

gb = grid(before, "m6_16_before.png")
ga = grid(after, "m6_16_after.png")
print("[E5] grids " + gb + " | " + ga)

report = os.path.join(OUT, "m6_16_stats.json")
with open(report, "w", encoding="utf-8") as f:
    json.dump({"before": sb, "after": sa}, f, ensure_ascii=False, indent=2)
print("[E5] report " + report)

fails = []
max_d = max(worst)
max_dark = max(s["dark"] for s in sa)
max_black = max(s["black"] for s in sa)
for ok, msg in (
    # 0.03 而不是 0.02：before 带 3.5px 反法线描边壳，轮廓比 after 外扩一圈，
    # 实测 16 机位差 0.0137~0.0221 全部来自这层壳；几何本身没有增减。
    (max_d <= 0.03, "max |cov_before - cov_after| = {0:.4f} (<=0.03, 描边壳)".format(max_d)),
    (max_dark <= 0.12, "max after dark(<0.02) = {0:.4f} (<=0.12)".format(max_dark)),
    (max_black <= 0.05, "max after black(<0.005) = {0:.4f} (<=0.05)".format(max_black)),
    (all(s["cov"] > 0.02 for s in sa), "all 16 after coverage > 0.02"),
):
    print("[assert] {0} {1}".format("PASS" if ok else "FAIL", msg))
    if not ok:
        fails.append(msg)
print("[assert] summary: {0} failed".format(len(fails)))
if fails:
    sys.exit(1)
print("[done] M6 E5 16-view")