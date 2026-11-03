# -*- coding: utf-8 -*-
"""M7：全向补视角复核（顶 / 底 / 左 / 后）。

为什么单独一支：m2~m5 的 27 个命名机位全部是平视（仰角 +0°~+4°），
m6 的 16 环绕也只有 +2°。于是**下半球和正顶从来没有被渲染过** ——
下颌底面、腋下、袖口内壁、颅顶收口这些位置出问题，现有判据一律看不见。
本脚本按正交补全补齐：±x/±y/±z 每个方向至少一台，另加斜上/斜下各一台。

产物：
  out/m7_aux_<name>.png     每个机位一张
  out/m7_aux_sheet.png      拼版
  out/m7_aux_stats.json     cov / dark / black（与 m6 同口径，便于合并判定）

用法：
  blender -b --factory-startup --python m7_aux.py
  blender -b --factory-startup --python m7_aux.py -- --blend X.blend --nool
    --blend  指定源文件，默认 美女.blend
    --nool   渲染前隐藏所有反法线描边壳（看裸几何）
"""
import bpy
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import shots

OUT = os.path.join(HERE, "out")
DEFAULT_BLEND = os.path.join(HERE, "美女.blend")
COLS = 4

# 补视角的价值全在「能不能互相比较」，所以照明必须统一。
# 场景原三点光固定在世界坐标（key 在左前、rim 在正后），从左侧看就是纯背光：
# 实测 p50=0.570，而正前是 0.876 —— 同一个发色差 0.3，肉眼看是两种颜色，
# 没法判「左右对称」。因此每个机位在相机位置挂一盏**同功率**面光（相机灯），
# 让任何方向都有一份等价的正向照明，三点光继续负责立体感。
# 功率取 14W / size 3.0：实测足以把左侧 p50 抬到 0.80 以上，又不至于压掉
# shadow 档（压掉就看不出「暗部是不是破面」了）。
CAM_LIGHT_ENERGY = 14.0
CAM_LIGHT_SIZE = 3.0


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = {"blend": DEFAULT_BLEND, "nool": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--blend" and i + 1 < len(argv):
            o["blend"] = argv[i + 1]
            i += 2
        elif a == "--nool":
            o["nool"] = True
            i += 1
        else:
            i += 1
    return o


def hide_outline():
    """关掉反法线描边壳的渲染。

    描边不是独立对象，而是**每个网格上挂的 Solidify 修改器**（名字 'Outline'，
    offset=+1、靠 material_offset 把新面指到 outline 材质槽）。所以不能按
    「材质名含 outline」去 hide 对象 —— 那样会把整个人藏掉（实测 cov=0，
    七张全空）。正确做法是关掉该修改器的 show_render。
    """
    n = 0
    for ob in bpy.data.objects:
        if ob.type != 'MESH':
            continue
        for m in ob.modifiers:
            if m.type == 'SOLIDIFY' and m.name == "Outline":
                m.show_render = False
                n += 1
    return n


def add_cam_light(cam):
    """在相机位置挂一盏同功率面光，朝相机看的方向照（等价于相机灯）。"""
    ld = bpy.data.lights.new("aux_cam_%s" % cam.name, 'AREA')
    ld.energy = CAM_LIGHT_ENERGY
    ld.size = CAM_LIGHT_SIZE
    ob = bpy.data.objects.new("aux_cam_%s" % cam.name, ld)
    bpy.context.collection.objects.link(ob)
    ob.location = cam.location
    ob.rotation_euler = cam.rotation_euler      # 面光朝 -Z，与相机同向
    return ob


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
        return {"cov": 0.0, "dark": 1.0, "black": 1.0, "p50": 0.0}
    lum = a[:, :, :3][mask].mean(axis=1)
    return {
        "cov": round(cov, 4),
        "dark": round(float((lum < 0.02).mean()), 4),
        "black": round(float((lum < 0.005).mean()), 4),
        "p50": round(float(np.quantile(lum, 0.50)), 4),
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


def main():
    o = parse_args()
    if not os.path.exists(o["blend"]):
        print("[M7] 源文件不存在：%s" % o["blend"])
        return 2
    bpy.ops.wm.open_mainfile(filepath=o["blend"])

    floor = bpy.data.objects.get("floor")
    if floor is not None:
        floor.hide_render = True          # 正顶视时地板会糊满整幅画面
    n_ol = hide_outline() if o["nool"] else 0

    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'

    paths, rows = [], []
    # --nool 的产物加后缀，两种模式共存，便于直接并排对比「是描边还是几何」
    suffix = "_nool" if o["nool"] else ""
    for name, v in shots.AUX_VIEWS.items():
        shots.set_res(v["w"], v["h"])
        cam = shots.camera(name, v["loc"], (0, 0, v["zc"]),
                           ortho_scale=v["ortho"])
        light = add_cam_light(cam)
        p = shots.render(cam, "m7_aux_%s%s.png" % (name[len("aux_"):], suffix))
        paths.append(p)
        bpy.data.objects.remove(cam, do_unlink=True)
        bpy.data.objects.remove(light, do_unlink=True)
        rows.append({"name": name, "file": os.path.basename(p)})

    for r, p in zip(rows, paths):
        r.update(stats(p))
        print("[M7] %-22s cov=%.4f dark=%.4f black=%.4f p50=%.3f"
              % (r["name"], r["cov"], r["dark"], r["black"], r["p50"]))

    sheet = grid(paths, "m7_aux_sheet%s.png" % suffix)
    print("[M7] sheet %s" % sheet)

    report = os.path.join(OUT, "m7_aux_stats%s.json" % suffix)
    with open(report, "w", encoding="utf-8") as f:
        json.dump({"blend": os.path.basename(o["blend"]), "nool": o["nool"],
                   "hidden_outline": n_ol, "views": rows},
                  f, ensure_ascii=False, indent=2)
    print("[M7] report %s" % report)

    # 断言语义：只判「相机没拍空」和「没有大面积纯黑」。不判暗像素比例 ——
    # 顶/仰视本来就会拍到背光面，用 m6 的 0.12 阈值会全红。暗部是否真的是
    # 破面，交给缩略图目视 + 需要时开 --nool 复看。
    fails = []
    for r in rows:
        if r["cov"] <= 0.02:
            fails.append("%s 覆盖率 %.4f（空图？相机没对准）" % (r["name"], r["cov"]))
        if r["black"] > 0.45:
            fails.append("%s 纯黑占比 %.3f（>0.45，几乎全黑，检查灯光或面法向）"
                         % (r["name"], r["black"]))
    for m in fails:
        print("[assert] FAIL %s" % m)
    print("[assert] summary: %d failed" % len(fails))
    if fails:
        return 1
    print("[done] M7 aux views %d" % len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
