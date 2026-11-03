# -*- coding: utf-8 -*-
"""二次元头发的 hair card 表示法（CHARM / SIGGRAPH Asia 2025 的 5 参数参数化）。

为什么换表示法
--------------
原来 `hair.py` 的鲍伯壳是「一圈椭圆环按高度缩放」再放样 —— 每一层截面都是
椭圆，所以：

  · 从任何角度切一刀都是椭圆，**原理上不可能有分缕**
  · 要封闭就必须封顶，而封顶必然留瑕（颅顶旋涡/肚脐，实测改了 4 次没解决）
  · 壳有折叠，40.1% 的面法线朝内，toon 把它们判成背光

二次元头发的工业/学术标准表示是一张张**发片**（hair card），每个控制点只存
5 个参数：

    位置 p = (x, y, z)  +  宽度 w  +  厚度 t

截面是菱形，四个角在

    p + ½w·ω,  p + ½t·ψ,  p − ½w·ω,  p − ½t·ψ

（ω = 宽度方向单位向量，ψ = 厚度方向单位向量）。相邻控制点的四个角两两相连，
组成一条有厚度的四边形带。CHARM 证明这套变换**完全可逆**：参数能建网格，
网格也能反解出参数。

参考：CHARM (arXiv 2509.21114)、HairDeck (arXiv 2610.40599, Apache-2.0)。
AnimeHair 数据集 37K 发型、平均每发型约 70 张 card。

与旧实现的关系
--------------
本模块只提供几何构造，不改 `hair.py` 里既有的 `bob` 分支。新样式挂在
`hair.style = "cards"` 下，两套可以并存对比。
"""
import math

import bpy
from mathutils import Vector

from meshkit import mesh_from


def _tangent(pts, i):
    """控制点 i 处的切线（端点用单侧差分）。"""
    n = len(pts)
    if n < 2:
        return Vector((0.0, 0.0, -1.0))
    if i == 0:
        d = pts[1] - pts[0]
    elif i == n - 1:
        d = pts[-1] - pts[-2]
    else:
        d = pts[i + 1] - pts[i - 1]
    if d.length < 1e-9:
        return Vector((0.0, 0.0, -1.0))
    return d.normalized()


def _frame(p, tan, center, up_bias=0.0):
    """给定位置与切线，返回 (宽度方向, 厚度方向)。

    厚度方向取「从 head 中心指向外」的径向，再投影到垂直于切线的平面上 ——
    这样卡片永远是「贴着头发面」的，宽度沿头皮、厚度沿法向。up_bias 让厚度
    方向额外偏向 +Z，用来做「发片立起来」的效果（0 = 完全贴面）。
    """
    radial = p - center
    if radial.length < 1e-9:
        radial = Vector((0.0, 0.0, 1.0))
    radial.normalize()
    if up_bias:
        radial = (radial + Vector((0.0, 0.0, 1.0)) * up_bias)
        if radial.length < 1e-9:
            radial = Vector((0.0, 0.0, 1.0))
        radial.normalize()
    # 去掉沿切线的分量
    nrm = radial - tan * radial.dot(tan)
    if nrm.length < 1e-6:
        # 切线几乎与径向平行（发梢朝外）时退化，用竖直方向兜底
        nrm = Vector((0.0, 0.0, 1.0)) - tan * tan.z
        if nrm.length < 1e-6:
            nrm = Vector((0.0, 1.0, 0.0))
    nrm.normalize()
    side = tan.cross(nrm)
    if side.length < 1e-9:
        side = Vector((1.0, 0.0, 0.0))
    side.normalize()
    return side, nrm


def card_rings(points, widths, thicks, center=None, up_bias=0.0):
    """把控制点展开成「每点 4 个角的菱形截面」环列表。

    points / widths / thicks 长度必须一致；widths/thicks 是**全宽/全厚**。
    返回 [[v0, v1, v2, v3], ...]，v 顺序绕截面一圈（+side, +nrm, -side, -nrm）。
    """
    pts = [Vector(p) for p in points]
    n = len(pts)
    if center is None:
        center = sum(pts, Vector((0.0, 0.0, 0.0))) / max(1, n)
    else:
        center = Vector(center)
    out = []
    for i, p in enumerate(pts):
        tan = _tangent(pts, i)
        side, nrm = _frame(p, tan, center, up_bias)
        hw = max(1e-5, widths[i] * 0.5)
        ht = max(1e-5, thicks[i] * 0.5)
        out.append([p + side * hw, p + nrm * ht,
                    p - side * hw, p - nrm * ht])
    return out


def card_mesh(rings, name="hair_card", cap_start=True, cap_end=True):
    """菱形截面环 → 四边形带网格。

    绕向：手写顶点顺序不可靠（实测 10 个面里 6 个朝内），所以建完 mesh 后
    用 bmesh 重算一次外向法线。卡片是闭合体，recalc_face_normals 能给出
    唯一正确的朝向。
    """
    import bmesh

    verts, faces = [], []
    for r in rings:
        verts.extend(r)
    seg = 4
    for i in range(len(rings) - 1):
        a = i * seg
        b = (i + 1) * seg
        for j in range(seg):
            j2 = (j + 1) % seg
            faces.append((a + j, a + j2, b + j2, b + j))
    if cap_start:
        faces.append((3, 2, 1, 0))
    if cap_end:
        base = (len(rings) - 1) * seg
        faces.append((base, base + 1, base + 2, base + 3))
    ob = mesh_from(verts, faces, name)

    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


def hair_card(name, points, widths, thicks, center=None, up_bias=0.0,
              cap_start=True, cap_end=True):
    """一张发片：控制点 + 宽度 + 厚度 → 网格对象。"""
    rings = card_rings(points, widths, thicks, center, up_bias)
    return card_mesh(rings, name, cap_start, cap_end)


def blend_widths(n, root_w, mid_w, tip_w, root_frac=0.12, tip_frac=0.25):
    """按「根细 → 中段最宽 → 尖细」生成宽度序列，长度 n。

    二次元发片的典型宽度剖面：根部收窄（插进头皮），中段饱满，末端收成尖。
    """
    w = []
    for i in range(n):
        t = i / max(1, n - 1)
        if t < root_frac:
            k = t / max(1e-6, root_frac)
            w.append(root_w + (mid_w - root_w) * k)
        elif t > 1.0 - tip_frac:
            k = (t - (1.0 - tip_frac)) / max(1e-6, tip_frac)
            w.append(mid_w + (tip_w - mid_w) * (k * k))
        else:
            # 中段微微鼓起
            u = (t - root_frac) / max(1e-6, 1.0 - root_frac - tip_frac)
            w.append(mid_w * (1.0 + 0.06 * math.sin(math.pi * u)))
    return w


def blend_thicks(n, root_t, tip_t):
    """厚度序列：根部厚、末端薄。"""
    return [root_t + (tip_t - root_t) * (i / max(1, n - 1)) for i in range(n)]
