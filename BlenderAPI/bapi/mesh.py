# -*- coding: utf-8 -*-
"""bapi · 网格层：从顶点建面、截面放样、管状扫掠、法线修复。

全部走 `bpy.data` + `bmesh`，没有 ops，可放心在 `-b` 里循环几万次。
"""

import math

import bmesh
import bpy
from mathutils import Vector

from . import obj as objmod


def from_verts_faces(verts, faces, name="mesh", smooth=True):
    """最底层构造：顶点表 + 面索引表 → 对象。"""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.validate()
    me.update()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    return objmod.new_object(name, me)


def ring(z, rx, ry=None, cx=0.0, cy=0.0, power=2.0, seg=48):
    """Z 平面上的超椭圆截面。power>2 越方，=2 是椭圆。"""
    ry = rx if ry is None else ry
    e = 2.0 / power
    pts = []
    for i in range(seg):
        a = 2.0 * math.pi * i / seg
        c, s = math.cos(a), math.sin(a)
        x = cx + rx * math.copysign(abs(c) ** e, c)
        y = cy + ry * math.copysign(abs(s) ** e, s)
        pts.append(Vector((x, y, z)))
    return pts


def loft(rings, name="loft", cap_start=True, cap_end=True, smooth=True):
    """把等顶点数的若干截面环按顺序桥接成侧壁。"""
    if not rings:
        raise ValueError("loft: rings 为空")
    seg = len(rings[0])
    for r in rings:
        if len(r) != seg:
            raise ValueError("loft: 每个环的顶点数必须一致")

    verts = []
    for r in rings:
        verts.extend(r)

    faces = []
    for i in range(len(rings) - 1):
        a, b = i * seg, (i + 1) * seg
        for j in range(seg):
            j2 = (j + 1) % seg
            faces.append((a + j, a + j2, b + j2, b + j))

    if cap_start:
        c = len(verts)
        verts.append(sum(rings[0], Vector()) / seg)
        for j in range(seg):
            faces.append((c, (j + 1) % seg, j))

    if cap_end:
        c = len(verts)
        verts.append(sum(rings[-1], Vector()) / seg)
        base = (len(rings) - 1) * seg
        for j in range(seg):
            faces.append((c, base + j, base + (j + 1) % seg))

    return from_verts_faces(verts, faces, name, smooth=smooth)


def tube(points, radii, name="tube", seg=16, up=(0.0, 1.0, 0.0),
         cap_start=True, cap_end=True):
    """沿折线放样。radii 是 [(rx, ry), ...]，与 points 等长。

    用平行传输式的局部标架，避免沿路径扭转。
    """
    pts = [Vector(p) for p in points]
    n = len(pts)
    if n < 2:
        raise ValueError("tube: 至少两个点")
    ref_up = Vector(up).normalized()

    rings = []
    for i, p in enumerate(pts):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == n - 1:
            t = pts[-1] - pts[-2]
        else:
            t = pts[i + 1] - pts[i - 1]
        if t.length < 1e-9:
            t = Vector((0.0, 0.0, 1.0))
        t.normalize()
        ref = ref_up
        if abs(t.dot(ref)) > 0.98:
            ref = Vector((1.0, 0.0, 0.0))
        ax = t.cross(ref).normalized()
        ay = ax.cross(t).normalized()
        rx, ry = radii[i]
        ring_pts = []
        for k in range(seg):
            a = 2.0 * math.pi * k / seg
            ring_pts.append(p + ax * (rx * math.cos(a)) + ay * (ry * math.sin(a)))
        rings.append(ring_pts)

    return loft(rings, name=name, cap_start=cap_start, cap_end=cap_end)


def cube(size=1.0, name="cube", center=(0.0, 0.0, 0.0)):
    """轴对齐立方体。size 是边长（不是半边长）。"""
    h = size / 2.0
    cx, cy, cz = center
    v = [(cx - h, cy - h, cz - h), (cx + h, cy - h, cz - h),
         (cx + h, cy + h, cz - h), (cx - h, cy + h, cz - h),
         (cx - h, cy - h, cz + h), (cx + h, cy - h, cz + h),
         (cx + h, cy + h, cz + h), (cx - h, cy + h, cz + h)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
         (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = from_verts_faces(v, f, name, smooth=False)
    recalc_normals(ob)
    return ob


def plane(size=1.0, name="plane", z=0.0, center=(0.0, 0.0)):
    """XZ 平面上的方形面片，法线朝 +Z。"""
    h = size / 2.0
    cx, cy = center
    v = [(cx - h, cy - h, z), (cx + h, cy - h, z),
         (cx + h, cy + h, z), (cx - h, cy + h, z)]
    ob = from_verts_faces(v, [(0, 1, 2, 3)], name, smooth=False)
    recalc_normals(ob)
    return ob


def sphere(radius=1.0, seg=32, rings=16, name="sphere", center=(0.0, 0.0, 0.0)):
    """UV 球。seg 是经线数，rings 是纬线数（含两极）。"""
    cx, cy, cz = center
    verts = [Vector((cx, cy, cz + radius))]
    for i in range(1, rings):
        phi = math.pi * i / rings
        z = radius * math.cos(phi)
        r = radius * math.sin(phi)
        for j in range(seg):
            a = 2.0 * math.pi * j / seg
            verts.append(Vector((cx + r * math.cos(a), cy + r * math.sin(a), cz + z)))
    verts.append(Vector((cx, cy, cz - radius)))

    faces = []
    for j in range(seg):                                  # 顶盖
        faces.append((0, 1 + j, 1 + (j + 1) % seg))
    for i in range(rings - 2):                            # 中段
        base = 1 + i * seg
        nxt = base + seg
        for j in range(seg):
            j2 = (j + 1) % seg
            faces.append((base + j, nxt + j, nxt + j2, base + j2))
    last = len(verts) - 1                                 # 底盖
    base = 1 + (rings - 2) * seg
    for j in range(seg):
        faces.append((last, base + (j + 1) % seg, base + j))

    ob = from_verts_faces(verts, faces, name, smooth=True)
    recalc_normals(ob)
    return ob


def cylinder(z0=0.0, z1=1.0, r=0.5, seg=32, name="cylinder", power=2.0):
    """直圆柱：两个截面环 + 端盖。"""
    rings = [ring(z0, r, r, seg=seg, power=power),
             ring(z1, r, r, seg=seg, power=power)]
    return loft(rings, name)


def resample_path(points, radii, step):
    """沿折线按弧长等距重采样（线性插值，够用且可预测）。"""
    pts = [Vector(p) for p in points]
    seglen = [(pts[i + 1] - pts[i]).length for i in range(len(pts) - 1)]
    total = sum(seglen)
    count = max(3, int(round(total / step)) + 1)
    out_p, out_r = [], []
    for k in range(count):
        t = total * k / (count - 1)
        acc = 0.0
        idx = 0
        while idx < len(seglen) - 1 and acc + seglen[idx] < t:
            acc += seglen[idx]
            idx += 1
        f = 0.0 if seglen[idx] <= 1e-12 else (t - acc) / seglen[idx]
        f = max(0.0, min(1.0, f))
        out_p.append(pts[idx].lerp(pts[idx + 1], f))
        rx = radii[idx][0] * (1 - f) + radii[idx + 1][0] * f
        ry = radii[idx][1] * (1 - f) + radii[idx + 1][1] * f
        out_r.append((rx, ry))
    return out_p, out_r


def recalc_normals(ob):
    """统一朝外。bmesh 版，不需要编辑模式。"""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


def shade_smooth(ob, on=True):
    for p in ob.data.polygons:
        p.use_smooth = on
    ob.data.update()
    return ob


def merge_by_distance(ob, dist=1e-4):
    """焊接重合顶点。返回被删掉的顶点数。"""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    before = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=dist)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return before - len(ob.data.vertices)


def flip_normals(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for f in bm.faces:
        f.normal_flip()
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


def non_manifold_edges(ob):
    """返回非流形边数量（健康检查用，不做修改）。"""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    n = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    return n


def flipped_faces(ob):
    """用有符号体积法近似判断法线是否整体朝内。"""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    vol = 0.0
    for f in bm.faces:
        vs = f.verts
        if len(vs) >= 3:
            vol += vs[0].co.dot(vs[1].co.cross(vs[2].co)) / 6.0
    bm.free()
    return vol < 0.0
