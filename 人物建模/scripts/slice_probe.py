# -*- coding: utf-8 -*-
"""切片探针：把当前颅骨沿 z 切成一叠真实横截面轮廓。

只读：不渲染、不保存 .blend、不改模型。产物 `out/slices.json` 交给
`scripts/slice_math.py` 做傅里叶描述子与缺陷检测。

为什么是这个对象
----------------
`head_base()+sculpt()` 就是 `HEAD_RAW` 17 行手写截面表经过 loft +
高斯解剖位移之后的**真实网格**。切它能直接量出「手写参数」与「实际形状」
差多少 —— 这是 14 条宏观比例 spec 从来没量过的东西。不含眼/眉/嘴/耳，
每层保证单一闭合轮廓。

用法：
    "D:/Program Files/Blender Foundation/Blender 5.2/blender.exe" \
        -b --factory-startup --python-exit-code 1 --python scripts/slice_probe.py
    # 可选：-- 96   指定层数
"""
import json
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import head as headmod              # noqa: E402
import head_parts._base as B        # noqa: E402

OUT = os.path.join(HERE, "out", "slices.json")
N_DEFAULT = 96


def _args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    return int(argv[0]) if argv and argv[0].isdigit() else N_DEFAULT


def _crosses(a, b, z):
    """半开区间规则：共享边上的交点只被一个面算一次。"""
    return (a.z < z <= b.z) or (b.z < z <= a.z)


def _contour(z, verts, faces):
    pts = []
    for f in faces:
        hit = []
        n = len(f)
        for i in range(n):
            a, b = verts[f[i]], verts[f[(i + 1) % n]]
            if _crosses(a, b, z):
                t = (z - a.z) / (b.z - a.z)
                hit.append((a.x + t * (b.x - a.x), a.y + t * (b.y - a.y)))
        pts.extend(hit[:2] if len(hit) > 2 else hit)
    # 去重（相邻面共用边）
    uniq = {}
    for x, y in pts:
        uniq[(round(x, 7), round(y, 7))] = (x, y)
    pts = list(uniq.values())
    if len(pts) < 3:
        return None
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    # 颅骨截面相对中心星形 → 按方位角排序即得闭合轮廓
    pts.sort(key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
    area = 0.5 * abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][1]
                         - pts[(i + 1) % len(pts)][0] * pts[i][1]
                         for i in range(len(pts))))
    per = sum(math.hypot(pts[(i + 1) % len(pts)][0] - pts[i][0],
                         pts[(i + 1) % len(pts)][1] - pts[i][1])
              for i in range(len(pts)))
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return {
        "z": z, "n": len(pts), "cx": cx, "cy": cy,
        "w": max(xs) - min(xs), "d": max(ys) - min(ys),
        "xmin": min(xs), "xmax": max(xs), "ymin": min(ys), "ymax": max(ys),
        "area": area, "perimeter": per,
        "sym_x": abs(max(xs) + min(xs)),
        "pts": [[round(x, 7), round(y, 7)] for x, y in pts],
    }


def _raw_at(rows, z):
    """把 17 行手写截面表线性插值到 z，用于「手写 vs 实测」对照。"""
    if z <= rows[0][0]:
        return list(rows[0])
    if z >= rows[-1][0]:
        return list(rows[-1])
    for i in range(len(rows) - 1):
        a, b = rows[i], rows[i + 1]
        if a[0] <= z <= b[0]:
            t = (z - a[0]) / (b[0] - a[0])
            return [a[j] + t * (b[j] - a[j]) for j in range(len(a))]
    return list(rows[-1])


def main():
    n = _args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    skull = headmod.head_base()
    headmod.sculpt(skull)
    verts = [v.co.copy() for v in skull.data.vertices]
    faces = [list(p.vertices) for p in skull.data.polygons]
    zmin, zmax = min(v.z for v in verts), max(v.z for v in verts)
    rows = B.head_rows()

    slices, empty = [], []
    for i in range(n):
        # 落在层间，避开顶点平面，避免退化解
        z = zmin + (zmax - zmin) * (i + 0.37) / n
        c = _contour(z, verts, faces)
        if c is None:
            empty.append(z)
            continue
        raw = _raw_at(rows, z)
        c["raw"] = {"rx": raw[1], "ryf": raw[2], "ryb": raw[3],
                    "cy": raw[4], "p": raw[5]}
        c["d_w_raw"] = c["w"] - 2.0 * raw[1]
        c["d_d_raw"] = c["d"] - (raw[2] + raw[3])
        slices.append(c)

    doc = {
        "source": "head_base()+sculpt()（纯颅骨，不含五官/耳）",
        "blender": bpy.app.version_string,
        "z_range": [zmin, zmax], "n_requested": n, "n_ok": len(slices),
        "n_empty": len(empty),
        "mesh": {"v": len(verts), "f": len(faces)},
        "raw_rows": len(rows),
        "raw_table": [list(r) for r in rows],
        "slices": slices,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print("[slice] mesh v=%d f=%d  z=[%.5f, %.5f]  slices=%d (empty=%d)"
          % (len(verts), len(faces), zmin, zmax, len(slices), len(empty)))
    for key in ("area", "w", "d", "d_w_raw", "d_d_raw"):
        vals = [c[key] for c in slices]
        print("[slice] %-9s min=%.6f max=%.6f" % (key, min(vals), max(vals)))
    print("[slice] -> out/slices.json")


if __name__ == "__main__":
    main()
