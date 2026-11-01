# -*- coding: utf-8 -*-
r"""双模式像素统计探针模板（描边 / 色阶 / ROI 阴影 / 发光带）。

两种跑法，**输出应逐位一致**：
    blender -b --factory-startup --python pixel_probe.py    # Blender 内无 Pillow，走 bpy
    python pixel_probe.py                                    # 系统 python + Pillow

拷进项目 `_stage?/` 后只需要改三处配置：
  1. `OUT`            —— 产物目录
  2. `VIEWS`          —— 机位参数，**必须与 m*.py 里的 camera() 调用逐字同步**
  3. `SKIN_TIERS`     —— toon 皮肤三档的显示色（base × ramp 的 sRGB 编码）

口径提醒（都踩过）：
  - 背景色取四角中位，前景 = 与背景最大通道差 > 18
  - 皮肤判据用「到三档色的最近距离 < 阈值」，**不要用绝对亮度**：
    绝对亮度阈值在色阶重标定后会失效，也会把「材质没接对」和「背光」混为一谈
  - 只看正对机位做像素↔世界换算：`px = w/2 + x*s`、`py = h/2 − (z−zc)*s`，`s = res_y/ortho`
  - 描边/发光带的判据都要「先跳过轮廓最外圈的暗像素」，否则一律读到 0
"""
import os
import sys
import math

import numpy as np

try:
    import bpy
    HAS_BPY = True
except ImportError:
    HAS_BPY = False
    from PIL import Image

# ---------------------------------------------------------------- 配置
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")

# 只对 frontal=True 的机位做世界↔像素换算
VIEWS = {
    "face_front": dict(w=620, h=780, ortho=0.30, zc=1.4956, frontal=True),
    "body_front": dict(w=560, h=900, ortho=1.80, zc=0.86, frontal=True),
    "body_q34":   dict(w=560, h=900, ortho=1.78, zc=0.86, frontal=False),
}

# 皮肤 toon 三档的显示色（sRGB 0~255）。色阶重标定只改 pos/灯强时这三档不变；
# 若动了 ramp 乘数，这里必须同步，否则分档统计全错。
SKIN_TIERS = [
    ("shadow", (198, 175, 191)),
    ("mid", (235, 202, 196)),
    ("light", (247, 224, 211)),
]
TIER_DIST = 38.0


def out(tag, text):
    print(f"[px] {tag}: {text}")


# ---------------------------------------------------------------- 读图
def read_rgb(name):
    if not name.endswith(".png"):
        name += ".png"
    path = os.path.join(OUT, name)
    if not os.path.exists(path):
        return None, path
    if HAS_BPY:
        img = bpy.data.images.load(path)
        w, h = img.size
        buf = np.empty(w * h * 4, dtype=np.float32)
        img.pixels.foreach_get(buf)
        # 两个必须记住的点：
        # 1) 8-bit sRGB PNG 的 pixels 是**编码值**（0.9765 = 249/255），直接 ×255
        # 2) pixels 是 **bottom-up**（行 0 = 图像最底行），必须 [::-1] 与 PIL 对齐
        a = (np.clip(buf.reshape(h, w, 4)[:, :, :3], 0.0, 1.0) * 255.0 + 0.5
             ).astype(np.uint8)[::-1]
        bpy.data.images.remove(img)
        return a, path
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8), path


def lum_of(a):
    f = a.astype(np.float32)
    return 0.2126 * f[:, :, 0] + 0.7152 * f[:, :, 1] + 0.0722 * f[:, :, 2]


def fg_mask(a):
    corners = np.concatenate([a[:8, :8].reshape(-1, 3), a[:8, -8:].reshape(-1, 3),
                              a[-8:, :8].reshape(-1, 3), a[-8:, -8:].reshape(-1, 3)])
    bg = np.median(corners.astype(np.float32), axis=0)
    return np.abs(a.astype(np.float32) - bg).max(axis=2) > 18


def skin_tiers(a):
    """返回 (skin_mask, tier_index, dist)；tier: 0=shadow 1=mid 2=light。"""
    f = a.astype(np.float32)
    d = np.stack([np.sqrt(((f - np.array(c, dtype=np.float32)) ** 2).sum(axis=2))
                  for _, c in SKIN_TIERS], axis=0)
    return d.min(axis=0) < TIER_DIST, np.argmin(d, axis=0), d.min(axis=0)


# ---------------------------------------------------------------- 描边暗带宽度
def edge_dark_width(a, win=8, dark=40.0):
    """逐行找前景左右边界，在边界 ±win px 窗内量「亮度<dark」的最长连续带。"""
    h, w = a.shape[:2]
    lum, fg = lum_of(a), fg_mask(a)
    dark_m = lum < dark
    runs = []
    for y in range(30, h - 30):
        xs = np.where(fg[y])[0]
        if len(xs) < 8:
            continue
        for xb in (xs[0], xs[-1]):
            if xb < win or xb > w - win - 1:
                continue
            cur = best = 0
            for v in dark_m[y, xb - win: xb + win + 1]:
                cur = cur + 1 if v else 0
                best = max(best, cur)
            runs.append(best)
    if not runs:
        return None
    r = np.array(runs)
    return dict(n=len(r), p25=float(np.percentile(r, 25)),
                p50=float(np.percentile(r, 50)),
                p75=float(np.percentile(r, 75)), mx=int(r.max()))


# ---------------------------------------------------------------- 皮肤色阶
def skin_stats(a):
    skin, idx, _ = skin_tiers(a)
    n = int(skin.sum())
    if n == 0:
        return None
    ls = lum_of(a)[skin]
    p5, p50, p95 = np.percentile(ls, [5, 50, 95])
    return dict(n=n, p5=float(p5), p50=float(p50), p95=float(p95),
                p50m5=float(p50 - p5), p95m50=float(p95 - p50),
                ge228=float((ls >= 228).mean() * 100.0),
                tiers={name: float((idx[skin] == i).mean() * 100.0)
                       for i, (name, _) in enumerate(SKIN_TIERS)})


# ---------------------------------------------------------------- ROI（仅正对机位）
def to_px(view, x, z):
    v = VIEWS[view]
    s = v["h"] / float(v["ortho"])
    return (v["w"] / 2.0 + x * s, v["h"] / 2.0 - (z - v["zc"]) * s)


def px_z(view, py):
    v = VIEWS[view]
    return v["zc"] + (v["h"] / 2.0 - py) / (v["h"] / float(v["ortho"]))


def roi_mask(view, shape, xr, zr):
    h, w = shape[:2]
    v = VIEWS[view]
    s = v["h"] / float(v["ortho"])
    px0 = int(round(v["w"] / 2.0 + xr[0] * s))
    px1 = int(round(v["w"] / 2.0 + xr[1] * s))
    py0 = int(round(v["h"] / 2.0 - (zr[1] - v["zc"]) * s))
    py1 = int(round(v["h"] / 2.0 - (zr[0] - v["zc"]) * s))
    m = np.zeros((h, w), dtype=bool)
    m[max(0, py0):min(h, py1 + 1), max(0, px0):min(w, px1 + 1)] = True
    return m, (px0, px1, py0, py1)


def roi_skin(a, view, xr, zr):
    skin, idx, _ = skin_tiers(a)
    m, box = roi_mask(view, a.shape, xr, zr)
    sel = m & skin
    if sel.sum() == 0:
        return dict(n=0, box=box, median=None, shadow_pct=None)
    return dict(n=int(sel.sum()), box=box,
                median=float(np.median(lum_of(a)[sel])),
                shadow_pct=float((idx[sel] == 0).mean() * 100.0))


# ---------------------------------------------------------------- 轮廓亮带
def rim_width(a, skip_dark=10, ref_a=25, ref_b=45, gain=10.0, scan=10):
    """必须先跳过描边暗带；rim 光落在描边内侧。"""
    h, w = a.shape[:2]
    lum, fg = lum_of(a), fg_mask(a)
    widths = []
    for y in range(40, h - 40):
        xs = np.where(fg[y])[0]
        if len(xs) < 20:
            continue
        for xb, d in ((xs[0], 1), (xs[-1], -1)):
            k = 0
            while k < skip_dark and 0 <= xb + d * (k + 1) < w and \
                    lum[y, xb + d * (k + 1)] < 70.0:
                k += 1
            i0, i1 = xb + d * ref_a, xb + d * ref_b
            if not (0 <= i0 < w and 0 <= i1 < w):
                continue
            ref = float(np.median(lum[y, min(i0, i1):max(i0, i1) + 1]))
            cur = best = 0
            for j in range(1, scan + 1):
                x = xb + d * (k + j)
                if not (0 <= x < w):
                    break
                if lum[y, x] > ref + gain:
                    cur += 1
                    best = max(best, cur)
                elif cur:
                    break
            widths.append(best)
    if not widths:
        return None
    ww = np.array(widths)
    return dict(n=len(ww), p50=float(np.percentile(ww, 50)),
                p90=float(np.percentile(ww, 90)), mx=int(ww.max()))


# ---------------------------------------------------------------- 头发高光带
def hair_band(a, view, z_lo, z_hi, band=(1.52, 1.60)):
    """头发像素 = 非皮肤 & 非虹膜(r−b 大) & 非纯白眼白；看 p99 的 z 分布。

    z_lo 用「画面下沿之上一点」，不要用接近 band 的值——否则判据本身就是循环论证。
    """
    h, w = a.shape[:2]
    lum, fg = lum_of(a), fg_mask(a)
    skin, _, _ = skin_tiers(a)
    f = a.astype(np.float32)
    r, b = f[:, :, 0], f[:, :, 2]
    not_iris = (r - b) < 40.0
    not_white = ~((lum > 246) & ((f.max(axis=2) - f.min(axis=2)) < 8))
    zmap = np.array([[px_z(view, y) for _ in range(w)] for y in range(h)])
    m = fg & (~skin) & not_iris & not_white & (zmap > z_lo) & (zmap < z_hi)
    if m.sum() < 500:
        return dict(n=int(m.sum()), in_band=None)
    t99 = float(np.percentile(lum[m], 99))
    zs = zmap[m & (lum >= t99)]
    return dict(n=int(m.sum()), t99=t99, n_hi=int(len(zs)),
                z_med=float(np.median(zs)),
                in_band=float(((zs >= band[0]) & (zs <= band[1])).mean() * 100.0))


# ---------------------------------------------------------------- 主流程
def main():
    out("mode", "Blender(bpy+numpy)" if HAS_BPY else "system python(Pillow+numpy)")

    a, p = read_rgb("body_q34")
    if a is not None:
        e = edge_dark_width(a)
        out("edge", f"body_q34 p50={e['p50']:.0f}px "
                    f"(p25={e['p25']:.0f} p75={e['p75']:.0f} max={e['mx']}) 目标 2~4")

    a, _ = read_rgb("face_front")
    if a is not None:
        s = skin_stats(a)
        out("skin", f"n={s['n']} p5={s['p5']:.1f} p50={s['p50']:.1f} p95={s['p95']:.1f} "
                    f"p50-p5={s['p50m5']:.1f} p95-p50={s['p95m50']:.1f} "
                    f"ge228={s['ge228']:.1f}% tiers={ {k: round(v, 1) for k, v in s['tiers'].items()} }")
        nose = roi_skin(a, "face_front", (-0.010, 0.010), (1.4308, 1.4435))
        out("roi_nose", f"box={nose['box']} n={nose['n']} median={nose['median']} "
                        f"目标 ≤ 皮肤 p50 − 20 = {s['p50'] - 20:.1f}")
        r = rim_width(a)
        if r:
            out("rim", f"p50={r['p50']:.0f} p90={r['p90']:.0f} max={r['mx']} 目标 2~6")


main()