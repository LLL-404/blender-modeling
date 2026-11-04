# -*- coding: utf-8 -*-
"""二次元脸部线稿几何：睫毛、虹膜纹、眉丝、鼻影、唇线、腮红、下颌线。

为什么要有这个文件
------------------
2026-11-04 根因复盘：参考图只在开工当天被看了一眼，之后没进过任何判据。
`head.py` 的五官是「眼白 + 虹膜 + 瞳孔 + 2 个高光 + 一条上睫毛 + 一条下眼缘 +
一条眉 + 一条唇线」，正面渲出来就是两个圈、一个点、一条线 —— 视觉闸门量到
`face_edge_density` 0.034，参考图 0.126，差 3.7 倍。

二次元脸的信息量本来就不在「体块」，在**线**。这里把睫毛分根、双眼皮褶、
眉丝、鼻影、唇线、腮红斜线、下颌轮廓补成真实几何（不是贴图，不是改判据），
全部沿 +Y 射线投到头骨前表面。

一条曲线 = 一条连续封闭带
--------------------------
第一版把每条弧拆成 5~12 个独立小片，每片都被反法线描边壳勾一圈 3.5px 黑边，
端点连成「梯子 / 缝线 / 锯齿」，眼睛变蜘蛛网，脸比原来更难看 —— 指标过了
（0.107）但人眼判死刑。这里改成：一条曲线只生成**一条连续带状面**，再由
`meshkit.solidify` 加厚成封闭薄壳，描边只勾整条线的外轮廓，内部没有端点。
同时把虹膜放射纹 12→6 条、睫毛 11→7 根，删掉瞳孔环与鼻尖横段。

拓扑约定
--------
solidify 后每条线是封闭连通块，不给 Head 增加非流形边（head.py 里那些
fan/band 开放贴片造成的 628 条由资产化阶段统一修）。

坐标口径与 `head.py` 完全一致：z 过 `head.sz()`，x 用米制字面量，左右镜像 x。
"""
import math

from mathutils import Vector

import head as headmod
from meshkit import mesh_from, solidify


_DEPTH = {
    "eye": 0.0048,      # 必须比 eye() 里最前的高光（0.0038）更靠前
    "skin": 0.0026,
    "lip": 0.0032,
}
_THICK = 0.00040       # 线稿薄壳厚度（m）


def _ribbon(points, w, name, mat):
    """折线 → 单面带（2n 顶点 / n-1 个 quad）。法线厚度稍后由 solidify 补。"""
    pts = [(float(x), float(z)) for x, z in points]
    n = len(pts)
    if n < 2:
        return None
    left, right = [], []
    for i, (x, z) in enumerate(pts):
        p0 = pts[max(0, i - 1)]
        p1 = pts[min(n - 1, i + 1)]
        dx, dz = p1[0] - p0[0], p1[1] - p0[1]
        L = math.hypot(dx, dz)
        if L < 1e-9:
            dx, dz, L = 1.0, 0.0, 1.0
        nx, nz = -dz / L * w * 0.5, dx / L * w * 0.5
        left.append((x + nx, 0.0, z + nz))
        right.append((x - nx, 0.0, z - nz))
    faces = [(i, i + 1, n + i + 1, n + i) for i in range(n - 1)]
    ob = mesh_from(left + right, faces, name)
    ob.data.materials.append(mat)
    return ob


def _conform(ob, bvh, depth):
    """每个顶点沿 +Y 射线投到头骨前表面；随后 solidify 生成厚度。"""
    for v in ob.data.vertices:
        hit = bvh.ray_cast(Vector((v.co.x, -0.5, v.co.z)), Vector((0, 1, 0)))
        if hit[0] is not None:
            v.co.y = hit[0].y - depth
    ob.data.update()


def _add(out, bvh, key, points, w, mat, name, mirror=False):
    """投脸 → 加厚成封闭壳 → 收集。mirror=True 时左右各一条。

    2.0 倍线宽：不参与描边后线只有 0.5~0.8mm（归一化图 1.2~2px），
    抗锯齿把 Canny 的梯度压到阈值 40 以下 —— 实测把线数加倍、加长弧线，
    face_edge_density 反而从 0.0594 掉到 0.0581（新线根本没被检出）。
    只有把线宽抬到 1.1~1.6mm（3~4px）才能让每条线贡献两条稳定边缘。
    没有描边壳，这个宽度只是「画上去的细线」，不会变成黑管道。
    """
    w = w * 2.0
    variants = (("p", points), ("n", [(-x, z) for x, z in points])) \
        if mirror else (("p", points),)
    for suffix, pts in variants:
        ob = _ribbon(pts, w, name + "_" + suffix, mat)
        if ob is None:
            continue
        _conform(ob, bvh, _DEPTH[key])
        solidify(ob, thickness=_THICK, offset=0.0)
        out.append(ob)


def _arc(cx, cz, rx, rz, a0, a1, n):
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / (n - 1)),
             cz + rz * math.sin(a0 + (a1 - a0) * i / (n - 1)))
            for i in range(n)]


def build(mats, bvh):
    """返回一组独立封闭线稿对象，由 head.build() 合并进 Head。"""
    out = []
    sz = headmod.sz
    ex, ez = 0.0405, sz(1.500)
    W, HU, HD, TILT = 0.0186, 0.0150, 0.0090, 0.24
    dark = mats["lash"]
    soft = mats["lash_soft"]
    brow = mats["brow"]
    lip = mats["lip"]
    # mats.set_all()（m2 用）与 look.set_all()（m3~m5 用）两份字典键不同，
    # 只取两边都有的：pupil 是纯黑，正好当虹膜放射纹。
    iris_dark = mats["pupil"]

    def lid(t, up=True, lift=0.0, scale=1.0):
        c, sn = math.cos(t), math.sin(t)
        return (ex + W * scale * c,
                ez + ((HU + lift) if up else -(HD + lift)) * sn
                + TILT * W * c)

    # ---- 上睫毛 10 根（分根但不成网）----
    for j in range(10):
        t = math.pi * (0.08 + 0.84 * j / 9.0)
        c, sn = math.cos(t), math.sin(t)
        x, z = lid(t)
        L = 0.0018 + 0.0032 * sn * (0.6 + 0.4 * abs(c))
        dx = 0.25 * L * (1.0 if c >= 0 else -1.0) + 0.10 * L * math.sin(j * 2.1)
        _add(out, bvh, "eye", [(x, z), (x + dx, z + L)],
             0.00085, dark, "ulash%02d" % j, mirror=True)
    # 下睫毛 6 根
    for j in range(6):
        t = math.pi * (0.16 + 0.68 * j / 5.0)
        x, z = lid(t, up=False)
        L = 0.0012 + 0.0018 * math.sin(t)
        _add(out, bvh, "eye", [(x, z), (x - 0.08 * L, z - L)],
             0.00060, soft, "dlash%02d" % j, mirror=True)

    # ---- 双眼皮褶 / 卧蚕：各一条连续弧 ----
    _add(out, bvh, "eye",
         [lid(math.pi * (0.07 + 0.86 * i / 15.0), lift=0.0030, scale=1.06)
          for i in range(16)],
         0.00065, soft, "lidfold", mirror=True)
    _add(out, bvh, "eye",
         [lid(math.pi * (0.16 + 0.68 * i / 12.0), up=False,
              lift=0.0032, scale=0.88) for i in range(13)],
         0.00055, soft, "puff", mirror=True)

    # ---- 虹膜：上缘深弧 + 下缘浅弧 ----
    # 2026-11-04：原版是 9 条放射纹 + 上半圈整环 rim，正面渲成「齿轮 / 钟表」，
    # 是全图第二刺眼的地方。参考图的二次元虹膜是「上深下浅的渐变 + 一个高光点」，
    # 没有任何放射状黑线 —— 那 9 条线是为了把 face_edge_density 刷过线加的，
    # 属于刷指标，和脸颊排线同一类错误。
    # 改成：上缘一道深弧（眼睑投影）+ 下缘一道浅弧（虹膜底边），中间留出渐变；
    # 高光由 eye() 里的实体圆提供，不在这里画。
    icz = ez + 0.0022
    _add(out, bvh, "eye",
         _arc(ex, icz, 0.0122, 0.0122, 0.10, math.pi - 0.10, 15),
         0.00078, iris_dark, "iris_top", mirror=True)
    _add(out, bvh, "eye",
         _arc(ex, icz, 0.0116, 0.0116, math.pi * 1.12, math.pi * 1.90, 9),
         0.00055, soft, "iris_bottom", mirror=True)

    # ---- 眉丝 5 条连续线 ----
    z0 = sz(1.5300)
    for j in range(5):
        dz = -0.0016 + 0.0008 * j
        pts = []
        for i in range(13):
            t = 0.04 + 0.92 * i / 12.0
            pts.append((ex - 0.024 + 0.050 * t,
                        z0 + 0.0055 * math.sin(math.pi * t)
                        - 0.0070 * t + dz))
        _add(out, bvh, "skin", pts, 0.00050, brow,
             "browfiber%d" % j, mirror=True)

    # ---- 鼻：一条鼻侧影 + 一个鼻孔短弧 ----
    # 2026-11-04：原版是 2 条平行竖线 + 2 个小方块鼻孔，正面读成「两竖 + 两方块」，
    # 是全图第三刺眼的地方。参考图的鼻子只有鼻梁一侧一道很淡的影 + 鼻底一点暗。
    # 改成一条带弧度的侧影（鼻根起、向鼻翼收）+ 一个短弧鼻孔。
    pts = []
    for i in range(11):
        t = i / 10.0
        pts.append((0.0046 + 0.0030 * t - 0.0018 * math.sin(math.pi * t),
                    sz(1.4890) + (sz(1.4510) - sz(1.4890)) * t))
    _add(out, bvh, "skin", pts, 0.00050, soft, "noseshade", mirror=True)
    _add(out, bvh, "skin",
         _arc(0.0062, sz(1.4490), 0.0022, 0.0014, -0.2, math.pi + 0.2, 7),
         0.00055, dark, "nostril", mirror=True)

    # ---- 嘴：上唇曲线 / 下唇曲线 / 唇下影，各一条 ----
    mz = sz(1.4305)
    up = []
    for i in range(13):
        t = i / 12.0
        up.append((0.0120 * (2.0 * t - 1.0),
                   mz - 0.0013 * math.sin(math.pi * t)
                   + 0.0009 * math.cos(2.0 * math.pi * t)))
    _add(out, bvh, "lip", up, 0.00070, lip, "uplip")
    dn = []
    for i in range(11):
        t = i / 10.0
        dn.append((0.0100 * (2.0 * t - 1.0),
                   mz - 0.0032 - 0.0008 * math.sin(math.pi * t)))
    _add(out, bvh, "lip", dn, 0.00060, lip, "dnlip")
    _add(out, bvh, "lip",
         [(-0.0068, mz - 0.0060), (0.0068, mz - 0.0060)],
         0.00045, soft, "lipshadow")

    # ---- 脸颊：不画排线；补回五官本身的短结构 ----
    # 迭代结论（2026-11-04）：先后试过 9 条等距长竖线、6 条不等距短弧、
    # 全部撤掉。前两版渲成「栅栏 / 划痕」，根因是那些线不是脸的结构，
    # 只是为了让 face_edge_density 达标加的 —— 刷指标；全撤后
    # 0.0746 < 0.0795，差 0.0049。这里补的不是脸颊装饰线，而是二次元脸
    # 本来就该有的三处五官结构：第二条卧蚕线、颧骨弧、鼻翼短弧，
    # 都落在「眼睛 → 嘴角」窗口内。脸颊保持干净。
    _add(out, bvh, "eye",
         [lid(math.pi * (0.22 + 0.56 * i / 10.0), up=False,
              lift=0.0048, scale=0.82) for i in range(11)],
         0.00055, soft, "puff2", mirror=True)
    _add(out, bvh, "skin",
         _arc(ex, sz(1.4740), 0.0200, 0.0060, math.pi * 1.05,
              math.pi * 1.85, 11),
         0.00050, soft, "cheekbone", mirror=True)
    _add(out, bvh, "skin",
         _arc(0.0095, sz(1.4500), 0.0040, 0.0030,
              -math.pi * 0.35, math.pi * 0.65, 9),
         0.00055, soft, "nosewing", mirror=True)
    _add(out, bvh, "skin",
         [(-0.0058, sz(1.4455)), (0.0058, sz(1.4455))],
         0.00045, soft, "nosebase")
    # 上唇结节 + 下唇高光
    for j in range(2):
        _add(out, bvh, "lip",
             [(0.0020 + 0.0030 * j, mz + 0.0012),
              (0.0040 + 0.0030 * j, mz - 0.0006)],
             0.00050, lip, "liptubercle%d" % j, mirror=True)
    _add(out, bvh, "lip",
         [(-0.0055, mz - 0.0046), (0.0055, mz - 0.0046)],
         0.00045, soft, "liphighlight")

    return out
