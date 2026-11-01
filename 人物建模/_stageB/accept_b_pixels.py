# -*- coding: utf-8 -*-
"""B4 像素差异复核（纯 Pillow）。严格复刻 m5_rig.py:111-125 的算法：
gray = RGB 三通道均值（0~1，sRGB 编码），step=4 抽样，阈值 12/255。

输出 [pxb] key=value + _stageB/logs/accept_b_pixels.json。
"""
import os
import json
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out")
LOG = os.path.join(HERE, "_stageB", "logs", "accept_b_pixels.json")
os.makedirs(os.path.dirname(LOG), exist_ok=True)
REC = {}


def p(k, v, note=""):
    REC[k] = v
    print(f"[pxb] {k}={v}" + (f"   # {note}" if note else ""))


def gray(path, step=4):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255.0
    g = a[:, :, :3].mean(axis=2)
    return g[::step, ::step]


def diff(g1, g2, thr=12.0 / 255.0):
    if g1.shape != g2.shape:
        return -1.0, None
    d = np.abs(g1 - g2) > thr
    return float(d.mean()), d


def fg_mask(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    bg = np.median(np.concatenate([a[:, :5, :], a[:, -5:, :]], axis=1), axis=1)
    d = np.sqrt(((a - bg[:, None, :]) ** 2).sum(-1))
    return d > 25


poses = ("rest", "wave", "walk", "reach")
paths = {n: os.path.join(OUT, f"m5_pose_{n}.png") for n in poses}
for n in poses:
    p(f"exists_{n}", os.path.getsize(paths[n]) if os.path.exists(paths[n]) else 0)

G = {n: gray(paths[n]) for n in poses}
p("gray_shape", list(G["rest"].shape))

pairs = []
for i in range(len(poses)):
    for j in range(i + 1, len(poses)):
        a, b = poses[i], poses[j]
        d, mask = diff(G[a], G[b])
        pairs.append((a, b, d))
        p(f"diff_{a}_vs_{b}_pct", round(d * 100, 2))
        if mask is not None:
            h = mask.shape[0]
            bands = np.array_split(np.arange(h), 9)
            prof = [round(float(mask[bd].mean()) * 100, 2) for bd in bands]
            p(f"rowprofile_{a}_vs_{b}", prof, "自上而下 9 条横带的变化像素占比(%)")

# 阈值敏感度：rest vs walk 在多个阈值下的结果（证明这条判据的稳定性）
sens = {}
for thr in (6, 8, 12, 16, 20, 24):
    d, _ = diff(G["rest"], G["walk"], thr=thr / 255.0)
    sens[str(thr)] = round(d * 100, 2)
p("restwalk_threshold_sensitivity_pct", sens, "|dgray| > thr/255 的像素占比")
allp = [t[2] for t in pairs]
p("diff_min_pct", round(min(allp) * 100, 2))
p("diff_max_pct", round(max(allp) * 100, 2))
p("all_pairs_ge_15", all(x >= 0.15 for x in allp))

# 前景占比与包围盒（确认四张图的取景没有把角色裁掉）
for n in poses:
    m = fg_mask(paths[n])
    ys, xs = np.where(m)
    if len(ys) == 0:
        p(f"fg_{n}", "EMPTY")
        continue
    p(f"fg_{n}", {"frac": round(float(m.mean()), 4),
                  "bbox": [int(xs.min()), xs.max(), int(ys.min()), ys.max()],
                  "size": [m.shape[1], m.shape[0]],
                  "touch": {"l": int(xs.min()) <= 1, "r": int(xs.max()) >= m.shape[1] - 2,
                            "t": int(ys.min()) <= 1, "b": int(ys.max()) >= m.shape[0] - 2}})

# rest vs walk 的差异集中在哪：小腿/脚 vs 裙区
m4 = fg_mask(paths["rest"])
ys, xs = np.where(m4)
y0, y1 = int(ys.min()), int(ys.max())
_, dmask = diff(G["rest"], G["walk"])
p("restwalk_bbox", [int(xs.min()), int(xs.max()), y0, y1])
for lo, hi, tag in ((0.0, 0.33, "top"), (0.33, 0.66, "mid"),
                    (0.66, 0.80, "skirt_hem_band"), (0.80, 1.0, "legs_feet")):
    a0 = int(y0 + (y1 - y0) * lo)
    a1 = int(y0 + (y1 - y0) * hi)
    if dmask is not None and a1 > a0:
        p(f"restwalk_diff_{tag}", round(float(dmask[a0 // 4:a1 // 4].mean()) * 100, 2),
          f"y {a0}~{a1}（step=4 抽样后的行）")


def _san(o):
    if isinstance(o, dict):
        return {k: _san(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_san(v) for v in o]
    if isinstance(o, np.generic):
        return o.item()
    return o


with open(LOG, "w", encoding="utf-8") as f:
    json.dump(_san(REC), f, ensure_ascii=False, indent=1)
print("[pxb] done")