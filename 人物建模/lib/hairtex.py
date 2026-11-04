# -*- coding: utf-8 -*-
"""头发的程序化发丝贴图（alpha + 明暗）。

为什么要有这一层
----------------
头发现在是 25 张 hair card：几何上有分缕、有收尖，但整张卡是**实心的**，
边缘是刀切一样的直边，正面只剩描边在勾轮廓 —— 所以无论怎么调宽度、
角度、层数，读起来都是「塑料叶片 / 瓦片」。工业管线里发片的细发丝从来
不是几何，是贴图：

  · alpha 通道把卡片的边缘切成一根根的发梢（轮廓不再是一条直线）
  · RGB 通道画出丝状明暗（二次元里发丝本来就是画上去的）

参考：HairDeck（arXiv 2610.40599）与主流实时管线都用「card + alpha strands」，
不是靠堆卡片数量。CHARM 只解决「卡片摆在哪」，不解决「卡片表面长什么样」。

贴图布局
--------
u = 0..1 横跨卡片宽度，v = 0..1 从根（贴头皮）到梢。

  · 根部（v < 0.42）保持实心：发根必须贴住头皮，不能漏出背景
  · 中段开始露出分缕，v 越大缝越宽
  · 发梢（v > 0.58）靠 13 根各自收尾的发丝撑轮廓，末端参差不齐
  · 左右边缘有随 v 变化的内缩，避免几何边缘出现一条贴图直线

所有随机量用固定种子，产物可复现；改种子才换发型细节。
"""
import math
import os
import struct
import zlib

import numpy as np

W, H = 512, 1024          # 贴图尺寸；卡片约 40mm 宽，512 足够，再大只是浪费显存
# 一张卡横向分几缕。513 贴图压缩到渲染约 37px，13 缕时每缕不到 3px，
# 贴图上的缝在屏幕上细于 1px，只会变成摩尔纹；9 缕与二次元发束的比例一致。
N_STRAND = 9
SEED = 7


def _smoothstep(a, b, x):
    """a / b 可以是标量，也可以是按行变化的数组（边缘内缩随 v 变）。"""
    d = np.asarray(b, dtype=np.float32) - np.asarray(a, dtype=np.float32)
    d = np.where(np.abs(d) < 1e-9, np.float32(1e-9), d)
    t = np.clip((x - a) / d, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _params(seed=SEED, n=N_STRAND):
    """每根发丝的参数。固定种子 → 每次构建一致。"""
    rng = np.random.default_rng(seed)
    out = []
    for k in range(n):
        out.append(dict(
            c0=(k + 0.5) / n + float(rng.uniform(-0.014, 0.014)),
            amp=float(rng.uniform(0.004, 0.017)),      # 横向摆动幅度
            freq=float(rng.uniform(0.7, 2.3)),         # 摆动频率（沿长度）
            ph=float(rng.uniform(0.0, 2.0 * math.pi)),
            w=float(rng.uniform(0.042, 0.056)),        # 半宽（u 单位）
            # 1/3 的发丝贯穿到底，其余在 0.74 之后陆续结束 ——
            # 早先 vend 取 0.60~1.00，结果 v≈0.72 处一半发丝同时退出，
            # 贴图出现一条水平断崖（预览图可见），贴到卡片上就是一道横线。
            # 上限从 1.02 收到 0.97：贯彻到 v=1 的发丝会把「几何边缘」
            # 一路撑到最下面，配上描边就是刘海下缘那条锯齿黑线。
            # 全部在 0.97 前收尾后，几何底边所在区域 alpha=0，完全不可见，
            # 肉眼看到的是发丝自己的终点（自然的碎发）。
            vend=(0.955 if k % 3 == 0 else float(rng.uniform(0.78, 0.955))),
            spread=float(rng.uniform(-0.030, 0.030)),  # 向梢部散开
        ))
    return out


def build_arrays(seed=SEED, n=N_STRAND):
    """返回 (rgb float32 HxWx3, alpha float32 HxW)。"""
    v = ((np.arange(H) + 0.5) / H).astype(np.float32)[:, None]   # 行 = 沿长度
    u = ((np.arange(W) + 0.5) / W).astype(np.float32)[None, :]   # 列 = 沿宽度

    alpha = np.zeros((H, W), np.float32)
    lum = np.ones((H, W), np.float32)

    for p in _params(seed, n):
        c = (p["c0"]
             + p["amp"] * np.sin(2.0 * math.pi * p["freq"] * v + p["ph"])
             + p["spread"] * (v ** 1.6))
        wv = p["w"] * (1.0 - 0.28 * v)                 # 向梢部收窄（不能太多，否则露背景）
        wv = np.maximum(wv, 1e-4)
        d = (u - c) / wv                               # 归一化到「几个半宽」
        m = 1.0 - _smoothstep(0.62, 1.0, np.abs(d))
        # 发丝自己的收尾：vend 前 14% 长度内渐隐，末端自然参差；
        # 渐隐区间要足够长，否则相邻发丝同时退出又会在贴图上留下横线。
        m = m * (1.0 - _smoothstep(p["vend"] - 0.14, p["vend"], v))
        alpha = np.maximum(alpha, m)

        # 亮芯暗边：这是「丝」的关键，纯靠 alpha 只能得到剪影
        core = np.exp(-(d / 0.52) ** 2)
        edge = np.exp(-((np.abs(d) - 0.96) / 0.26) ** 2)
        lum += 0.115 * core - 0.150 * edge

    # 根部实心：发根必须贴住头皮。
    # 横向 jitter 很关键：base 是 z 向的平滑渐变，clip 到 0.5 后会变成
    # **一整行同时消失**，贴到卡片上就是一道水平线（实测 v≈0.54 处不透明
    # 比例从 96% 直掉 35%）。给每列加不同的起止位置，边界就是参差的发梢。
    nb1 = 0.5 + 0.5 * np.sin(2.0 * math.pi * 11.0 * u + 0.7)
    nb2 = 0.5 + 0.5 * np.sin(2.0 * math.pi * 27.0 * u + 2.3)
    jit = 0.085 * nb1 + 0.045 * nb2 - 0.065
    # 上界 1.02 -> 1.12：原来 v=0.94 处只剩 15% 覆盖，刘海下缘几乎全透，
    # 几何的参差边裸露成一排锯齿。抬起后末端仍分缕，但保留 30% 以上的覆盖。
    base = 1.0 - _smoothstep(0.26 + jit, 1.02 + jit, v)
    alpha = np.maximum(alpha, base)

    # 左右边缘内缩 + 随 v 抖动，避免几何边缘露出贴图直线
    eo = (0.005
          + 0.006 * (0.5 + 0.5 * np.sin(21.3 * v + 0.7))
          + 0.004 * (0.5 + 0.5 * np.sin(47.1 * v + 2.1)))
    alpha *= _smoothstep(eo, eo + 0.007, u)
    alpha *= 1.0 - _smoothstep(1.0 - eo - 0.007, 1.0 - eo, u)

    # 低频体积明暗：两三道宽带，让卡片有「一绺」的圆度
    lum *= 1.0 - 0.085 * (0.5 + 0.5 * np.cos(2.0 * math.pi * 1.6 * u + 0.9))
    lum *= 1.0 - 0.070 * _smoothstep(0.72, 1.0, v)     # 梢部略暗，压住剪影

    lum = np.clip(lum, 0.52, 1.14)
    alpha = np.clip(alpha, 0.0, 1.0)
    rgb = np.repeat(lum[:, :, None], 3, axis=2).astype(np.float32)
    return rgb, alpha


def _write_png(path, arr, alpha=False):
    """手写 PNG 编码（color type 6=RGBA / 2=RGB，8-bit）。

    不能依赖 Pillow：构建跑在 Blender 自带的 Python 里，实测
    `ModuleNotFoundError: No module named 'PIL'`；而 bpy 的 image.save()
    会按色彩空间做一次 sRGB 编码，把「明暗系数」当成颜色改掉。
    zlib 是标准库，两张图不到 50 行，反而最稳。
    """
    a = np.ascontiguousarray(arr)
    h, w = a.shape[:2]
    ctype = 6 if alpha else 2
    raw = b"".join(b"\x00" + a[y].tobytes() for y in range(h))

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    blob = (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ctype, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(blob)
    return path


def write_png(path, rgb, alpha):
    """RGBA PNG：RGB = 明暗系数，A = 发丝镂空。"""
    rgba = np.empty((rgb.shape[0], rgb.shape[1], 4), np.uint8)
    rgba[:, :, :3] = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
    rgba[:, :, 3] = np.clip(alpha * 255.0, 0, 255).astype(np.uint8)
    return _write_png(path, rgba, alpha=True)


def write_preview(path, rgb, alpha):
    """棋盘底 + 镂空，人眼检查用（不参与构建）。"""
    h, w = alpha.shape
    yy, xx = np.mgrid[0:h, 0:w]
    checker = ((yy // 24 + xx // 24) % 2).astype(np.float32)
    bg = 0.22 + 0.20 * checker
    a = alpha[:, :, None]
    comp = rgb * 0.55 + 0.30          # 压到可见范围，纯看形状
    out = comp * a + bg[:, :, None] * (1.0 - a)
    img = (np.clip(out, 0, 1) * 255).astype(np.uint8)
    return _write_png(path, img, alpha=False)


def build(out_dir):
    """生成贴图，返回 (png 路径, 预览路径)。已存在且比本模块新则复用。"""
    png = os.path.join(out_dir, "tex_hair_strands.png")
    prev = os.path.join(out_dir, "_hair_strands_preview.png")
    rgb, alpha = build_arrays()
    write_png(png, rgb, alpha)
    write_preview(prev, rgb, alpha)
    return png, prev


if __name__ == "__main__":
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p, q = build(os.path.join(here, "out"))
    rgb, a = build_arrays()
    print("[hairtex] png={0} preview={1}".format(p, q))
    print("[hairtex] alpha mean={0:.3f}  opaque={1:.1%}  rgb mean={2:.3f}".format(
        float(a.mean()), float((a > 0.5).mean()), float(rgb.mean())))
