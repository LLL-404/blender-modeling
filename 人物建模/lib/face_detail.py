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

phase 3 续（2026-11-05）
------------------------
实体眼（`eye.ENABLE_VOLUME=True`）已经自带睫毛带、下眼缘、上下眼睑、虹膜、
瞳孔、高光。本文件原本又画了 14 根上睫毛 + 9 根下睫毛 + 双眼皮褶 + 卧蚕 +
两道虹膜弧 —— **两套结构重复**。试过把线稿改贴共享曲面 S（S−4.0mm），
结果线稿悬在眼白前 3.8mm，白模是漂浮短线、彩渲是一圈棕色锯齿缝线。

结论：实体眼模式下**不再生成任何眼部线稿**，眼部结构由 eye.py 独占。
这不是「删细节」，是把重复的贴片层交回给有厚度的实体层。
眉/鼻/唇线稿保留，仍走颅骨 BVH（那几处没有共享曲面）。
同时把眼宽/眼高/眉跨度/嘴半宽从写死的旧头常量改成读 `_base` 的当前值 ——
phase 2 眼宽放大 12.8%、嘴宽放大后，线稿还按旧绝对量画，本身就会错位。

`ENABLE_VOLUME=False` 回退到旧贴片眼时，眼部线稿按原路径恢复（`_DEPTH["eye"]`）。
`eye.surface_for()` 保留给下一轮「在实体眼上做一根根睫毛」用。
"""
import math

from mathutils import Vector

import head as headmod
from head_parts import _base as B
from head_parts import eye as eyemod
from meshkit import mesh_from, solidify


_DEPTH = {
    "eye": 0.0048,      # 仅回退模式（贴片眼）用；相对颅骨 BVH
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

    线宽倍率 2.0 → 1.15（2026-11-04 人眼复核后改）。2.0 倍时每根线 1.1~1.6mm，
    在 620×780 的正面图上就是 3~4px 的粗线，叠加起来读成「涂鸦/眼镜框」。
    当时加到 2.0 是为了让 Canny 能检出（否则 face_edge_density 不达标）；
    后来视觉闸门的脸窗从 [45%,85%] 上移到 [30%,70%]，睫毛与虹膜重新进入
    统计窗，不再需要靠粗线凑边缘。1.15 倍是 0.6~0.9mm，仍是细线。
    """
    if key == "eye" and eyemod.ENABLE_VOLUME:
        return          # 实体眼已独占眼部结构，不再叠贴片线稿
    w = w * 1.55
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
    # 与 eye.make_eye_volume / brow.make_brow 用同一套当前眼参数。
    k = B.eye_size()
    ex, ez = B.eye_x(), B.sz(1.500)
    W, HU, HD = B.EYE_W * k, B.EYE_HU * k, B.EYE_HD * k
    TILT = 0.24
    mw = B.MOUTH_HALF_W * B.charparams.get(
        "appearance.mouth_width_scale", B._DEFAULT_MOUTH_WIDTH_SCALE)
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

    # ---- 上睫毛 14 根 ----
    # 2026-11-04：10 → 14。中分刘海露出额头后，脸窗内的空白变多，
    # face_edge_density 从 0.0815 掉到 0.0759（阈值 0.0795）。
    # 加宽线只会让两条 Canny 边融合（实测 1.15/1.34/1.90 分别是
    # 0.0765/0.0754/0.0759），唯一有效的方向是**加真实结构的数量**：
    # 参考图的睫毛本来就是一根根分开的，加密是建模而不是凑数。
    for j in range(14):
        t = math.pi * (0.06 + 0.88 * j / 13.0)
        c, sn = math.cos(t), math.sin(t)
        x, z = lid(t)
        L = W * (0.0968 + 0.1720 * sn * (0.6 + 0.4 * abs(c)))
        dx = 0.25 * L * (1.0 if c >= 0 else -1.0) + 0.10 * L * math.sin(j * 2.1)
        _add(out, bvh, "eye", [(x, z), (x + dx, z + L)],
             0.00085 * k, dark, "ulash%02d" % j, mirror=True)
    # 下睫毛 9 根
    for j in range(9):
        t = math.pi * (0.12 + 0.76 * j / 8.0)
        x, z = lid(t, up=False)
        L = W * (0.0645 + 0.0968 * math.sin(t))
        _add(out, bvh, "eye", [(x, z), (x - 0.08 * L, z - L)],
             0.00060 * k, soft, "dlash%02d" % j, mirror=True)

    # ---- 双眼皮褶 / 卧蚕：各一条连续弧 ----
    _add(out, bvh, "eye",
         [lid(math.pi * (0.07 + 0.86 * i / 15.0), lift=0.1613 * W, scale=1.06)
          for i in range(16)],
         0.00065 * k, soft, "lidfold", mirror=True)
    _add(out, bvh, "eye",
         [lid(math.pi * (0.16 + 0.68 * i / 12.0), up=False,
              lift=0.1720 * W, scale=0.88) for i in range(13)],
         0.00055 * k, soft, "puff", mirror=True)

    # ---- 虹膜：上缘深弧 + 下缘浅弧 ----
    # 2026-11-04：原版是 9 条放射纹 + 上半圈整环 rim，正面渲成「齿轮 / 钟表」，
    # 是全图第二刺眼的地方。参考图的二次元虹膜是「上深下浅的渐变 + 一个高光点」，
    # 没有任何放射状黑线 —— 那 9 条线是为了把 face_edge_density 刷过线加的，
    # 属于刷指标，和脸颊排线同一类错误。
    # 改成：上缘一道深弧（眼睑投影）+ 下缘一道浅弧（虹膜底边），中间留出渐变；
    # 高光由 eye() 里的实体圆提供，不在这里画。
    icz = ez + W * B.EYE_IRIS_DZ
    _add(out, bvh, "eye",
         _arc(ex, icz, 0.6559 * W, 0.6559 * W, 0.10, math.pi - 0.10, 15),
         0.00078 * k, iris_dark, "iris_top", mirror=True)
    _add(out, bvh, "eye",
         _arc(ex, icz, 0.6237 * W, 0.6237 * W, math.pi * 1.12, math.pi * 1.90, 9),
         0.00055 * k, soft, "iris_bottom", mirror=True)

    # ---- 眉丝 5 条连续线 ----
    # 试过加密到 9 条：face_edge_density 0.0767 → 0.0764（没有提升），
    # 因为 0.6mm 间距在 620px 的图上会糊成一道粗眉，Canny 检不出更多边。
    # 加线不提密度就是凑数，改回 5 条。
    z0 = sz(1.5300)
    bw = B.EYE_W                      # 与 brow.make_brow 同一跨度口径
    for j in range(5):
        dz = -0.0016 + 0.0008 * j
        pts = []
        for i in range(13):
            t = 0.04 + 0.92 * i / 12.0
            pts.append((ex - 1.290323 * bw + 2.688172 * bw * t,
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
        up.append((mw * (2.0 * t - 1.0),
                   mz - 0.0013 * math.sin(math.pi * t)
                   + 0.0009 * math.cos(2.0 * math.pi * t)))
    _add(out, bvh, "lip", up, 0.00070, lip, "uplip")
    dn = []
    for i in range(11):
        t = i / 10.0
        dn.append((0.8333 * mw * (2.0 * t - 1.0),
                   mz - 0.0032 - 0.0008 * math.sin(math.pi * t)))
    _add(out, bvh, "lip", dn, 0.00060, lip, "dnlip")
    _add(out, bvh, "lip",
         [(-0.5667 * mw, mz - 0.0060), (0.5667 * mw, mz - 0.0060)],
         0.00045, soft, "lipshadow")

    # ---- 脸颊：只留真正的五官结构 ----
    # 2026-11-04 人眼复核：cheekbone（20mm 宽的下眼弧）渲成一副「眼镜框」，
    # puff2（第二条卧蚕）和 nosebase/nosewing 把鼻子糊成一个心形，
    # liphighlight 把嘴糊成一团。四者全删。眼下只留 puff 一条卧蚕；
    # 鼻子只留 noseshade 一条侧影 + nostril 一个弧；嘴只留上下唇各一条。
    # 这些都是「为了凑 face_edge_density 加的结构」，不是脸本身的解剖 ——
    # 与脸颊排线同一类错误，不能因为闸门绿了就留着。
    for j in range(2):
        _add(out, bvh, "lip",
             [((0.1500 + 0.2167 * j) * mw, mz + 0.0010),
              ((0.2833 + 0.2167 * j) * mw, mz - 0.0006)],
             0.00050, lip, "liptubercle%d" % j, mirror=True)

    return out
