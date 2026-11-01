# -*- coding: utf-8 -*-
"""A 阶段像素统计（纯 Pillow/numpy，系统 python）。不使用 analyzeImage 下结论。

运行（工作目录 人物建模/）：
  python _stageA/accept_pixels.py

输出 [px] key=value 并写 _stageA/logs/accept_pixels.json。
所有结论都来自像素算术；本脚本不「看图」。
"""
import os
import json
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out")
LOG = os.path.join(HERE, "_stageA", "logs", "accept_pixels.json")
os.makedirs(os.path.dirname(LOG), exist_ok=True)

REC = {}


def p(key, val, note=""):
    REC[key] = val
    print(f"[px] {key}={val}" + (f"   # {note}" if note else ""))


def load(name):
    return np.asarray(Image.open(os.path.join(OUT, name)).convert("RGB")).astype(np.float32)


def lum(a):
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def skin_mask(a):
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    return (r >= 180) & (g >= 160) & (b >= 140) & (r >= g) & (g >= b - 10)


def otsu(L):
    h, _ = np.histogram(L, bins=256, range=(0, 256))
    tot = h.sum()
    if tot == 0:
        return 128
    idx = np.arange(256)
    w0 = np.cumsum(h) / tot
    w1 = 1.0 - w0
    m0 = np.cumsum(h * idx) / np.maximum(np.cumsum(h), 1)
    m1 = (np.cumsum((h * idx)[::-1])[::-1] - h * idx) / np.maximum(
        np.cumsum(h[::-1])[::-1] - h, 1)
    var = w0 * w1 * (m0 - m1) ** 2
    return int(np.argmax(var))


def fg_by_row_border(a, tol=25.0, border=5):
    """前景 = 与「该行左右边框颜色」差异 > tol 的像素。

    背景世界与地面都是水平均匀的，逐行取左右边框颜色能同时吃掉「世界背景 + 地面」，
    不会把地板误判成角色。返回 bool mask。
    """
    L = a.shape[0]
    bg = np.median(np.concatenate([a[:, :border, :], a[:, -border:, :]], axis=1), axis=1)
    d = np.sqrt(((a - bg[:, None, :]) ** 2).sum(-1))
    return d > tol


def runs(mask_row, min_w=6, merge_gap=4):
    """一行 bool → [(start, width)] 的前景 run 列表。

    min_w=6：手指在屏幕上宽 19~40px，短于 6px 的都是抗锯齿碎片；
    merge_gap=4：相邻 run 的暗缝 <=4px 属同一根手指被高光劈开，合并。
    """
    out = []
    n = len(mask_row)
    i = 0
    while i < n:
        if mask_row[i]:
            j = i
            while j < n and mask_row[j]:
                j += 1
            if j - i >= min_w:
                if out and i - (out[-1][0] + out[-1][1]) <= merge_gap:
                    s0 = out[-1][0]
                    out[-1] = (s0, j - s0)
                else:
                    out.append((i, j - i))
            i = j
        else:
            i += 1
    return out


# ================================================================ m3_face_front
a = load("m3_face_front.png")
L = lum(a)
M = skin_mask(a)
skin_px = int(M.sum())
pct = [float(v) for v in np.percentile(L[M], [5, 50, 95])] if skin_px else [None] * 3
p("face_skin_px", skin_px)
p("face_skin_fraction", round(float(M.mean()), 4), "皮肤像素占全图比例")
p("face_skin_lum_p5_p50_p95", [round(v, 1) for v in pct])
p("face_skin_p50_minus_p5", round(pct[1] - pct[0], 1) if skin_px else None)
p("face_skin_p95_minus_p50", round(pct[2] - pct[1], 1) if skin_px else None)
p("face_image_size", [a.shape[1], a.shape[0]])

# 亮度台阶（竖向跳变）检测：列内相邻行 |Δlum|>25，按 y 聚成「横带」
ys, xs = np.where(M)
if len(ys):
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    p("face_skin_bbox", [x0, x1, y0, y1])
    events = []
    for x in range(x0, x1 + 1):
        col = L[:, x]
        cm = M[:, x]
        dy = np.abs(np.diff(col))
        for y in np.where((dy > 25) & cm[1:] & cm[:-1])[0]:
            events.append((x, int(y) + 1))
    p("face_step_events", len(events))
    if events:
        ymap = {}
        for x, y in events:
            ymap.setdefault(y, set()).add(x)
        ys_sorted = sorted(ymap.keys())
        bands = []
        cur = [ys_sorted[0]]
        for y in ys_sorted[1:]:
            if y - cur[-1] <= 4:
                cur.append(y)
            else:
                bands.append(cur)
                cur = [y]
        bands.append(cur)
        face_w = x1 - x0 + 1
        rows = []
        for bd in bands:
            cols = set()
            for y in bd:
                cols |= ymap[y]
            width = max(cols) - min(cols) + 1
            rows.append({"y": [bd[0], bd[-1]], "cols": len(cols),
                         "cover": round(len(cols) / face_w, 3),
                         "width_px": width})
        strong = [r for r in rows if r["cover"] >= 0.25]
        p("face_step_bands_total", len(rows))
        p("face_step_bands_cover>=25%", len(strong))
        p("face_step_bands", rows[:12])
        if strong:
            p("face_step_widest_px", max(r["width_px"] for r in strong))

# ================================================================ m1_hand
a = load("m1_hand.png")
L = lum(a)
# 阈值取 150 而非 Otsu：本图背景亮度 p50≈50（世界+地面），手臂/手掌亮部
# p50≈172~218，150 同时高于背景 3 倍且低于手部主峰；Otsu 会把画面右缘
# 的亮背景块也纳入，把「手指 run」数错。
thr = 150
fg = L > thr
p("hand_otsu_thr", thr)
p("hand_fg_fraction", round(float(fg.mean()), 4))
p("hand_fg_px", int(fg.sum()))
p("hand_lum_p5_p50_p95", [round(float(v), 1) for v in np.percentile(L, [5, 50, 95])])
ys, xs = np.where(fg)
if len(ys):
    hx0, hx1, hy0, hy1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    p("hand_fg_bbox", [hx0, hx1, hy0, hy1])
    p("hand_fg_box_wh", [hx1 - hx0 + 1, hy1 - hy0 + 1])
    p("hand_touches_frame", bool(hx0 <= 1 or hy0 <= 1 or hx1 >= a.shape[1] - 2
                                or hy1 >= a.shape[0] - 2))
    # 手 ROI：取「含图像中心列、且该列前景像素 >=30」的连续列区间，
    # 把画面右缘的大腿/背景碎块排除在外（否则会数出 5 段假手指）。
    cols = np.where(fg.sum(0) >= 30)[0]
    roi = [310, 310]
    for x in range(310, -1, -1):
        if fg[:, x].sum() >= 30:
            roi[0] = x
        else:
            break
    for x in range(310, a.shape[1]):
        if fg[:, x].sum() >= 30:
            roi[1] = x
        else:
            break
    p("hand_col_roi", roi)
    fy = np.where(fg[:, roi[0]:roi[1] + 1].any(1))[0]
    fy0, fy1 = int(fy.min()), int(fy.max())
    p("hand_row_range_in_roi", [fy0, fy1])
    H = fy1 - fy0 + 1
    rows = range(fy0 + int(0.55 * H), fy0 + int(0.95 * H))
    hist = {}
    best = (0, None, [])
    for y in rows:
        rr = runs(fg[y, roi[0]:roi[1] + 1], 3)
        hist[len(rr)] = hist.get(len(rr), 0) + 1
        if len(rr) > best[0]:
            best = (len(rr), y, rr)
    p("hand_finger_rows", [hy0 + int(0.55 * H), hy0 + int(0.95 * H)])
    p("hand_run_count_hist", {str(k): v for k, v in sorted(hist.items())})
    p("hand_max_run_count", best[0])
    p("hand_max_run_row", best[1])
    if best[2]:
        p("hand_max_run_widths_px", [w for _, w in best[2]])
        p("hand_max_run_gaps_px",
          [best[2][i + 1][0] - (best[2][i][0] + best[2][i][1])
           for i in range(len(best[2]) - 1)])

# ================================================================ m5_body_front
a = load("m5_body_front.png")
L = lum(a)
fg = fg_by_row_border(a)
p("body_fg_fraction", round(float(fg.mean()), 4))
ys, xs = np.where(fg)
if len(ys):
    bx0, bx1, by0, by1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    p("body_fg_bbox", [bx0, bx1, by0, by1])
    p("body_fg_box_wh", [bx1 - bx0 + 1, by1 - by0 + 1])
    p("body_image_size", [a.shape[1], a.shape[0]])
    p("body_crop_flags", {"left": bx0 <= 1, "right": bx1 >= a.shape[1] - 2,
                          "top": by0 <= 1, "bottom": by1 >= a.shape[0] - 2})

    # 手部 / 脸 / 前臂 皮肤色：世界 → 屏幕（正视正交，scale=500px/m）
    def box(x, z, hw, hh):
        cx, cy = 280 + x * 500.0, 450 - (z - 0.86) * 500.0
        return (int(max(0, cx - hw)), int(max(0, cy - hh)),
                int(min(a.shape[1], cx + hw)), int(min(a.shape[0], cy + hh)))

    def med(b):
        r = a[b[1]:b[3], b[0]:b[2]]
        rr = r.reshape(-1, 3)
        return [round(float(v), 1) for v in np.median(rr, axis=0)]

    def med_lum(b):
        r = a[b[1]:b[3], b[0]:b[2]]
        return round(float(np.median(lum(r))), 1)

    def skin_frac(b):
        r = a[b[1]:b[3], b[0]:b[2]]
        return round(float(skin_mask(r).mean()), 3)

    boxes = {"hand_R_world+x": box(0.232, 0.778, 6, 18),
             "hand_L_world-x": box(-0.232, 0.778, 6, 18),
             "face": box(0.0, 1.500, 30, 26),
             "forearm_R_world+x": box(0.205, 0.960, 12, 26),
             "forearm_L_world-x": box(-0.205, 0.960, 12, 26)}
    cols = {}
    for k, b in boxes.items():
        r = a[b[1]:b[3], b[0]:b[2]]
        if k.startswith("hand") and r.size:
            # 手部盒很窄（手掌厚仅 ~11px），用「盒内非背景像素」的中位数，
            # 否则背景会把中位数拉走。
            bgv = np.median(np.concatenate([a[:, :5, :], a[:, -5:, :]], axis=1), axis=1)
            dv = np.sqrt(((r - bgv[b[1]:b[3], None, :]) ** 2).sum(-1))
            sel = dv > 30
            rr = r[sel] if sel.sum() > 20 else r.reshape(-1, 3)
            fg_frac = round(float(sel.mean()), 3) if r.size else 0.0
        else:
            rr = r.reshape(-1, 3)
            fg_frac = skin_frac(b)
        cols[k] = {"box": list(b),
                   "median_rgb": [round(float(v), 1) for v in np.median(rr, axis=0)],
                   "median_lum": round(float(np.median(
                       0.2126 * rr[:, 0] + 0.7152 * rr[:, 1] + 0.0722 * rr[:, 2])), 1),
                   "skin_frac": fg_frac}
    p("body_skin_boxes", cols)
    if "face" in cols:
        fl = cols["face"]["median_lum"]
        for k in ("hand_R_world+x", "hand_L_world-x", "forearm_R_world+x",
                  "forearm_L_world-x"):
            p(f"lum_diff_{k}_vs_face", round(cols[k]["median_lum"] - fl, 1))
        # 近似 ΔE76（sRGB→Lab，仅作色差数量级参考）
        def to_lab(rgb):
            c = np.array(rgb, dtype=float) / 255.0
            c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
            Mx = np.array([[0.4124, 0.3576, 0.1805],
                           [0.2126, 0.7152, 0.0722],
                           [0.0193, 0.1192, 0.9505]])
            xyz = Mx @ c / np.array([0.95047, 1.0, 1.08883])
            f = np.where(xyz > 0.008856, xyz ** (1 / 3), 7.787 * xyz + 16 / 116)
            return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]),
                             200 * (f[1] - f[2])])

        def de(a_, b_):
            return round(float(np.sqrt(((to_lab(a_) - to_lab(b_)) ** 2).sum())), 1)

        for k in ("hand_R_world+x", "hand_L_world-x", "forearm_R_world+x",
                  "forearm_L_world-x"):
            p(f"dE76_{k}_vs_face", de(cols[k]["median_rgb"], cols["face"]["median_rgb"]))

# ================================================================ 姿势图差异
r = load("m5_pose_rest.png")
w = load("m5_pose_wave.png")
if r.shape == w.shape:
    Lr, Lw = lum(r), lum(w)
    d = np.abs(Lr - Lw)
    p("pose_full_diff_gt20", round(float((d > 20).mean()), 4))
    fgr = fg_by_row_border(r)
    ys, xs = np.where(fgr)
    xr = int(xs.max())
    ycol = int(np.median(np.where(fgr[:, max(0, xr - 20):xr + 1])[0]))
    bx = (max(0, xr - 200), xr + 1, max(0, ycol - 150), min(r.shape[0], ycol + 150))
    p("pose_handbox", list(bx))
    sub = d[bx[1]:bx[3], bx[0]:bx[2]]
    p("pose_handbox_diff_gt20", round(float((sub > 20).mean()), 4))
    sil = fgr[bx[1]:bx[3], bx[0]:bx[2]]
    if sil.sum() > 50:
        p("pose_hand_silhouette_px", int(sil.sum()))
        p("pose_hand_silhouette_diff_gt20", round(float((sub[sil] > 20).mean()), 4))
        p("pose_hand_silhouette_median_dlum",
          round(float(np.median(d[bx[1]:bx[3], bx[0]:bx[2]][sil])), 2))
    # 对照：躯干区域（画面中央）
    tb = (int(r.shape[1] * 0.42), int(r.shape[1] * 0.58),
          int(r.shape[0] * 0.25), int(r.shape[0] * 0.55))
    p("pose_torsobox", list(tb))
    p("pose_torsobox_diff_gt20",
      round(float((d[tb[2]:tb[3], tb[0]:tb[1]] > 20).mean()), 4))
else:
    p("pose_size_mismatch", [list(r.shape), list(w.shape)])


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
print("[px] done -> _stageA/logs/accept_pixels.json")