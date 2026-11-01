# -*- coding: utf-8 -*-
"""同机位四姿势图的像素差异（与 m5_rig 的算法一致：RGB 均值、step=4、阈值 12/255）。"""
import os
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(HERE, "_stageB", "tmp")
poses = ("rest", "wave", "walk", "reach")


def gray(name):
    a = np.asarray(Image.open(os.path.join(TMP, f"samecam_{name}.png")).convert("RGB"),
                   dtype=np.float32) / 255.0
    return a.mean(axis=2)[::4, ::4]


G = {n: gray(n) for n in poses}
out = {}
for i in range(len(poses)):
    for j in range(i + 1, len(poses)):
        a, b = poses[i], poses[j]
        d = float((np.abs(G[a] - G[b]) > 12.0 / 255.0).mean())
        out[f"{a}_vs_{b}"] = round(d * 100, 2)
        print(f"[samecam_px] diff_{a}_vs_{b}={d * 100:.2f}%")
vals = list(out.values())
print(f"[samecam_px] min={min(vals):.2f}% max={max(vals):.2f}% all_ge_15={all(v >= 15 for v in vals)}")
print(f"[samecam_px] summary={out}")