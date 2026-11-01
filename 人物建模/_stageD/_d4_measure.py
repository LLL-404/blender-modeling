# -*- coding: utf-8 -*-
"""D4 量测：袖筒（solidify 后）与卷边的同轴同面半径。

口径：以袖筒末端 tip 为原点、袖轴为法向，取沿轴 ±5mm 内的顶点，
算「垂轴半径」的最大值。这才是肉眼可见的凸出基准 ——
DESIGN §1.5 里的 47mm 是**环层**（solidify 之前）半径，
solidify 之后袖筒外表面还要再往外 1~2mm。

用法（工作目录 人物建模/）：
    blender -b --factory-startup --python _stageD/_d4_measure.py
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import bpy
from mathutils import Vector

import outfit as om


def radial_max(ob, tip, axis, span=0.006):
    mw = ob.matrix_world
    cos = [mw @ v.co for v in ob.data.vertices]
    rad = []
    for c in cos:
        d = c - tip
        if abs(d.dot(axis)) <= span:
            rad.append((d - d.dot(axis) * axis).length)
    return (max(rad) if rad else None), len(rad)


def main():
    s = 1
    tip = Vector((0.169 * s, 0.006, 1.110))
    axis = Vector((-0.075 * s, 0.050, -0.996)).normalized()

    for solid in (False, True):
        ob = om._sleeve(s, solid=solid, cuff=False)
        r, n = radial_max(ob, tip, axis)
        print(f"[d4] sleeve solid={solid}: r_max="
              f"{'-' if r is None else f'{r * 1000:.2f}'}mm n={n}")
        me = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.meshes.remove(me)

    cuff = om._cuff_ring(s)
    r, n = radial_max(cuff, tip, axis)
    print(f"[d4] cuff ring:           r_max="
          f"{'-' if r is None else f'{r * 1000:.2f}'}mm n={n}")
    # 沿轴分段看造型（内端 / 中段 / 外缘）
    mw = cuff.matrix_world
    cos = [mw @ v.co for v in cuff.data.vertices]
    for lo, hi, tag in ((-0.009, -0.005, "inner"), (-0.005, 0.001, "mid"),
                        (0.001, 0.004, "outer")):
        band = []
        for c in cos:
            d = c - tip
            t = d.dot(axis)
            if lo <= t < hi:
                band.append((d - t * axis).length)
        if band:
            print(f"[d4] cuff {tag:5s} (t∈[{lo * 1000:+.0f},{hi * 1000:+.0f}]mm): "
                  f"r_max={max(band) * 1000:.2f}mm n={len(band)}")
    me = cuff.data
    bpy.data.objects.remove(cuff, do_unlink=True)
    bpy.data.meshes.remove(me)
    print("[d4] done")


if __name__ == "__main__":
    main()