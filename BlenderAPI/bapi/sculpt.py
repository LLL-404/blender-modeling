# -*- coding: utf-8 -*-
"""bapi · 雕刻层：headless 下的「笔刷」替代品。

背景（实测，2026-11-03，Blender 5.2.2）：
    `bpy.ops.object.mode_set(mode='SCULPT')` 能成功，但
    `bpy.ops.sculpt.brush_stroke.poll()` 抛
    `RuntimeError: Operator ... poll() failed, context is incorrect`，
    而且 `bpy.data.brushes` 在 `-b` 下只有一个 `Draw`。
    **一笔都落不下去。** 雕刻笔刷依赖视口 + 数位板的实时反馈循环。

替代方案：把笔刷行为写成「权重 × 方向」的顶点位移场。
    权重 = falloff(到笔刷中心的距离 / 半径)
    方向 = 法线 / 固定轴 / 指向中心 / 指向平面

好处是这些函数**可复现、可参数化、能喂给搜索器**：
手雕一刀定型，位移场可以跑 96 次选最优。

坐标约定：所有 center/radius 都是**对象本地坐标**（网格坐标）。
如果对象带 matrix_world 变换，先 `obj.apply_transform()`。
"""

import math

import bmesh


# ---------------------------------------------------------------- 权重

def falloff(t, kind="smooth"):
    """t ∈ [0,1]：0 在笔刷中心，1 在边缘。返回 1→0 的权重。"""
    t = max(0.0, min(1.0, t))
    if kind == "constant":
        return 1.0
    if kind == "linear":
        return 1.0 - t
    if kind == "sharp":
        return (1.0 - t) ** 3
    if kind == "sphere":
        return math.sqrt(max(0.0, 1.0 - t * t))
    u = 1.0 - t                                   # smooth（默认）
    return u * u * (3.0 - 2.0 * u)


def weights(ob, center, radius, kind="smooth", invert=False):
    """返回 [(顶点索引, 权重)]，只含权重 > 0 的顶点。"""
    c = tuple(center)
    r2 = radius * radius
    out = []
    for v in ob.data.vertices:
        d2 = (v.co[0] - c[0]) ** 2 + (v.co[1] - c[1]) ** 2 + (v.co[2] - c[2]) ** 2
        if d2 > r2:
            continue
        w = falloff(math.sqrt(d2) / radius, kind)
        if invert:
            w = 1.0 - w
        if w > 0.0:
            out.append((v.index, w))
    return out


def to_group(ob, name, center, radius, kind="smooth", threshold=0.0):
    """把权重写成顶点组，可直接喂给 DISPLACE / SMOOTH / SHRINKWRAP 修改器。"""
    vg = ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)
    for idx, w in weights(ob, center, radius, kind):
        if w > threshold:
            vg.add([idx], w, 'REPLACE')
    return vg


# ---------------------------------------------------------------- 位移

def _bm(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    bm.normal_update()
    return bm


def _done(ob, bm, moved):
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return moved


def move(ob, center, radius, offset, kind="smooth", axis=None):
    """整体平移一块区域（= Grab 笔刷）。

    axis 给 ('X',) / ('X','Z') 之类可限制方向；None 表示不限制。
    offset 是 (dx, dy, dz) 或标量（沿 axis 的方向用）。
    """
    if isinstance(offset, (int, float)):
        if not axis:
            raise ValueError("move: offset 是标量时必须给 axis")
        vec = [0.0, 0.0, 0.0]
        for a in axis:
            vec["XYZ".index(a)] = float(offset)
        offset = tuple(vec)
    ox, oy, oz = offset
    if axis:
        if "X" not in axis:
            ox = 0.0
        if "Y" not in axis:
            oy = 0.0
        if "Z" not in axis:
            oz = 0.0

    bm = _bm(ob)
    moved = 0.0
    for idx, w in weights(ob, center, radius, kind):
        v = bm.verts[idx]
        v.co.x += ox * w
        v.co.y += oy * w
        v.co.z += oz * w
        moved = max(moved, math.sqrt((ox * w) ** 2 + (oy * w) ** 2 + (oz * w) ** 2))
    return _done(ob, bm, moved)


def inflate(ob, center, radius, amount, kind="smooth"):
    """沿法线外推（正）/内收（负）= Inflate / Crease 的一半。

    负 amount + kind='sharp' 就是压一条沟（Crease）。
    """
    bm = _bm(ob)
    moved = 0.0
    for idx, w in weights(ob, center, radius, kind):
        v = bm.verts[idx]
        d = amount * w
        v.co += v.normal * d
        moved = max(moved, abs(d))
    return _done(ob, bm, moved)


def pinch(ob, center, radius, amount=0.5, kind="smooth"):
    """向笔刷中心收拢 = Pinch。amount=0.5 表示满权重处走一半距离。"""
    c = tuple(center)
    bm = _bm(ob)
    moved = 0.0
    for idx, w in weights(ob, center, radius, kind):
        v = bm.verts[idx]
        dx = (c[0] - v.co.x) * amount * w
        dy = (c[1] - v.co.y) * amount * w
        dz = (c[2] - v.co.z) * amount * w
        v.co.x += dx
        v.co.y += dy
        v.co.z += dz
        moved = max(moved, math.sqrt(dx * dx + dy * dy + dz * dz))
    return _done(ob, bm, moved)


def flatten(ob, center, radius, amount=1.0, kind="smooth", plane_normal=None):
    """压向局部拟合平面 = Flatten。plane_normal 不给就用区域平均法线。"""
    bm = _bm(ob)
    sel = weights(ob, center, radius, kind)
    if not sel:
        return _done(ob, bm, 0.0)

    if plane_normal is None:
        nx = sum(bm.verts[i].normal.x * w for i, w in sel)
        ny = sum(bm.verts[i].normal.y * w for i, w in sel)
        nz = sum(bm.verts[i].normal.z * w for i, w in sel)
        ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        n = (nx / ln, ny / ln, nz / ln)
    else:
        ln = math.sqrt(sum(c * c for c in plane_normal)) or 1.0
        n = tuple(c / ln for c in plane_normal)

    # 加权平均位置当作平面上的一点
    sw = sum(w for _, w in sel) or 1.0
    px = sum(bm.verts[i].co.x * w for i, w in sel) / sw
    py = sum(bm.verts[i].co.y * w for i, w in sel) / sw
    pz = sum(bm.verts[i].co.z * w for i, w in sel) / sw

    moved = 0.0
    for idx, w in sel:
        v = bm.verts[idx]
        dist = ((v.co.x - px) * n[0] + (v.co.y - py) * n[1] + (v.co.z - pz) * n[2])
        d = dist * amount * w
        v.co.x -= n[0] * d
        v.co.y -= n[1] * d
        v.co.z -= n[2] * d
        moved = max(moved, abs(d))
    return _done(ob, bm, moved)


def smooth_region(ob, center, radius, iterations=3, factor=0.5, kind="smooth"):
    """只对一块区域做拉普拉斯平滑（= Smooth 笔刷）。

    用 `bmesh.ops.smooth_vert`，实测单次最大位移 9.6mm，headless 可用。
    """
    sel = weights(ob, center, radius, kind)
    if not sel:
        return 0.0
    bm = _bm(ob)
    verts = [bm.verts[i] for i, _ in sel]
    before = [v.co.copy() for v in verts]
    for _ in range(max(1, iterations)):
        bmesh.ops.smooth_vert(bm, verts=verts, factor=factor,
                              use_axis_x=True, use_axis_y=True, use_axis_z=True)
    moved = max((v.co - b).length for v, b in zip(verts, before))
    return _done(ob, bm, moved)


def scale_region(ob, center, radius, factor=1.0, kind="smooth", pivot=None):
    """以 pivot（默认笔刷中心）为原点缩放一块区域。factor>1 鼓起，<1 收紧。"""
    p = tuple(pivot) if pivot is not None else tuple(center)
    bm = _bm(ob)
    moved = 0.0
    for idx, w in weights(ob, center, radius, kind):
        v = bm.verts[idx]
        s = 1.0 + (factor - 1.0) * w
        for k in range(3):
            old = v.co[k]
            v.co[k] = p[k] + (old - p[k]) * s
            moved = max(moved, abs(v.co[k] - old))
    return _done(ob, bm, moved)


# ---------------------------------------------------------------- 量测

def roughness(ob, center=None, radius=None, kind="smooth"):
    """区域「粗糙度」：每个顶点到邻居均值的距离的均值（米）。

    这是判断平滑有没有生效的客观指标——比看图可靠。
    center/radius 为 None 时统计全网格。
    """
    sel = None
    if center is not None:
        sel = {i for i, _ in weights(ob, center, radius, kind)}

    me = ob.data
    nbr = {}
    for e in me.edges:
        a, b = e.vertices
        nbr.setdefault(a, []).append(b)
        nbr.setdefault(b, []).append(a)

    total, count = 0.0, 0
    for i, js in nbr.items():
        if sel is not None and i not in sel:
            continue
        if not js:
            continue
        v = me.vertices[i].co
        ax = sum(me.vertices[j].co.x for j in js) / len(js)
        ay = sum(me.vertices[j].co.y for j in js) / len(js)
        az = sum(me.vertices[j].co.z for j in js) / len(js)
        total += math.sqrt((v.x - ax) ** 2 + (v.y - ay) ** 2 + (v.z - az) ** 2)
        count += 1
    return total / count if count else 0.0


def planarity(ob, center, radius, kind="smooth"):
    """区域到最佳拟合平面的平均距离（米）。越小越平。"""
    sel = weights(ob, center, radius, kind)
    if len(sel) < 4:
        return 0.0
    me = ob.data
    sw = sum(w for _, w in sel) or 1.0
    px = sum(me.vertices[i].co.x * w for i, w in sel) / sw
    py = sum(me.vertices[i].co.y * w for i, w in sel) / sw
    pz = sum(me.vertices[i].co.z * w for i, w in sel) / sw

    # 用协方差最小特征向量的近似：法线取加权平均顶点法线
    nx = sum(me.vertices[i].normal.x * w for i, w in sel)
    ny = sum(me.vertices[i].normal.y * w for i, w in sel)
    nz = sum(me.vertices[i].normal.z * w for i, w in sel)
    ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    nx, ny, nz = nx / ln, ny / ln, nz / ln

    total = 0.0
    for i, w in sel:
        v = me.vertices[i].co
        total += abs((v.x - px) * nx + (v.y - py) * ny + (v.z - pz) * nz) * w
    return total / sw
