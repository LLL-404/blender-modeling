# -*- coding: utf-8 -*-
"""建模共用工具：轮廓重采样、放样、合并、重网格。"""
import bpy
import bmesh
import math
from mathutils import Vector


# ---------------- 数学 ----------------

def catmull_rom(vals, t):
    """vals: 标量列表，t∈[0,1] 映射到整条曲线。"""
    n = len(vals)
    if n == 1:
        return vals[0]
    x = t * (n - 1)
    i = min(int(x), n - 2)
    f = x - i
    p0 = vals[max(i - 1, 0)]
    p1 = vals[i]
    p2 = vals[i + 1]
    p3 = vals[min(i + 2, n - 1)]
    return 0.5 * ((2 * p1) + (-p0 + p2) * f +
                  (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f +
                  (-p0 + 3 * p1 - 3 * p2 + p3) * f * f * f)


def resample(table, key, step):
    """table: [(z, rx, ry, cy, power), ...] 按 z 重采样。返回同结构列表。"""
    zs = [r[0] for r in table]
    z0, z1 = zs[0], zs[-1]
    count = max(2, int(round((z1 - z0) / step)) + 1)
    out = []
    for k in range(count):
        z = z0 + (z1 - z0) * k / (count - 1)
        # 在 zs 中定位 t
        t = _t_at(zs, z)
        out.append(tuple(catmull_rom([r[i] for r in table], t) for i in range(len(table[0]))))
    return out


def _t_at(zs, z):
    n = len(zs)
    if z <= zs[0]:
        return 0.0
    if z >= zs[-1]:
        return 1.0
    for i in range(n - 1):
        if zs[i] <= z <= zs[i + 1]:
            f = (z - zs[i]) / (zs[i + 1] - zs[i]) if zs[i + 1] != zs[i] else 0.0
            return (i + f) / (n - 1)
    return 1.0


# ---------------- 网格构造 ----------------

def superellipse_ring(z, rx, ry, cy=0.0, cx=0.0, power=2.0, seg=48, ry_back=None):
    """Z 轴上的一个超椭圆截面。p>2 越方；ry_back 给背面单独深度（做臀部）。"""
    pts = []
    for i in range(seg):
        a = 2.0 * math.pi * i / seg
        c, s = math.cos(a), math.sin(a)
        e = 2.0 / power
        x = cx + rx * math.copysign(abs(c) ** e, c)
        r = ry if (ry_back is None or s <= 0) else ry_back
        y = cy + r * math.copysign(abs(s) ** e, s)
        pts.append(Vector((x, y, z)))
    return pts


def loft(rings, cap_start=True, cap_end=True, name="loft"):
    """rings: [ [Vector,...], ... ] 顶点数必须一致，按顺序桥接成四边形。"""
    seg = len(rings[0])
    verts, faces = [], []
    for r in rings:
        verts.extend(r)
    for i in range(len(rings) - 1):
        a = i * seg
        b = (i + 1) * seg
        for j in range(seg):
            j2 = (j + 1) % seg
            faces.append((a + j, a + j2, b + j2, b + j))
    if cap_start:
        c = len(verts)
        verts.append(sum(rings[0], Vector()) / seg)
        for j in range(seg):
            faces.append((c, rings_face_index(0, j + 1, seg), rings_face_index(0, j, seg)))
    if cap_end:
        c = len(verts)
        verts.append(sum(rings[-1], Vector()) / seg)
        base = (len(rings) - 1) * seg
        for j in range(seg):
            faces.append((c, base + j, base + (j + 1) % seg))
    return mesh_from(verts, faces, name)


def rings_face_index(ring_i, j, seg):
    return ring_i * seg + (j % seg)


def mesh_from(verts, faces, name):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate()
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return ob


def tube(points, radii, seg=48, name="tube", up=(0.0, 1.0, 0.0),
         cap_start=True, cap_end=True):
    """沿折线放样。points: [Vector]，radii: [(rx, ry)]。"""
    pts = [Vector(p) for p in points]
    n = len(pts)
    rings = []
    ref_up = Vector(up).normalized()
    for i, p in enumerate(pts):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == n - 1:
            t = pts[-1] - pts[-2]
        else:
            t = (pts[i + 1] - pts[i - 1])
        if t.length < 1e-9:
            t = Vector((0, 0, 1))
        t.normalize()
        ref = ref_up
        if abs(t.dot(ref)) > 0.98:
            ref = Vector((1.0, 0.0, 0.0))
        ax = t.cross(ref).normalized()
        ay = ax.cross(t).normalized()
        rx, ry = radii[i]
        ring = []
        for k in range(seg):
            a = 2.0 * math.pi * k / seg
            ring.append(p + ax * (rx * math.cos(a)) + ay * (ry * math.sin(a)))
        rings.append(ring)
    return loft(rings, cap_start=cap_start, cap_end=cap_end, name=name)


def resample_path(points, radii, step):
    """沿路径按弧长重采样。"""
    pts = [Vector(p) for p in points]
    seglen = [(pts[i + 1] - pts[i]).length for i in range(len(pts) - 1)]
    total = sum(seglen)
    count = max(3, int(total / step) + 1)
    tvals = [i / (count - 1) for i in range(count)]
    out_p, out_r = [], []
    for t in tvals:
        x = t * len(seglen)
        i = min(int(x), len(seglen) - 1)
        f = x - i
        p = pts[i].lerp(pts[i + 1], f) if i + 1 < len(pts) else pts[-1]
        out_p.append(p)
        out_r.append((catmull_rom([r[0] for r in radii], t),
                      catmull_rom([r[1] for r in radii], t)))
    return out_p, out_r


# ---------------- 对象操作 ----------------

def select_only(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def join(objs, name="joined"):
    select_only(objs[0])
    for o in objs[1:]:
        o.select_set(True)
    bpy.ops.object.join()
    ob = bpy.context.object
    ob.name = name
    return ob


def voxel_remesh(ob, size=0.006, adaptivity=0.0):
    select_only(ob)
    m = ob.modifiers.new("Remesh", 'REMESH')
    m.mode = 'VOXEL'
    m.voxel_size = size
    m.adaptivity = adaptivity
    m.use_smooth_shade = True
    bpy.ops.object.modifier_apply(modifier=m.name)
    return ob


def smooth(ob, factor=0.5, iterations=6):
    select_only(ob)
    m = ob.modifiers.new("Smooth", 'SMOOTH')
    m.factor = factor
    m.iterations = iterations
    bpy.ops.object.modifier_apply(modifier=m.name)
    return ob


def solidify(ob, thickness=0.004, offset=0.0):
    select_only(ob)
    m = ob.modifiers.new("Solidify", 'SOLIDIFY')
    m.thickness = thickness
    m.offset = offset
    bpy.ops.object.modifier_apply(modifier=m.name)
    return ob


def shade_smooth(ob):
    select_only(ob)
    bpy.ops.object.shade_smooth()


def mirror_x(ob):
    select_only(ob)
    m = ob.modifiers.new("Mirror", 'MIRROR')
    m.use_axis[0] = True
    bpy.ops.object.modifier_apply(modifier=m.name)
    return ob


def recalc_normals(ob):
    select_only(ob)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def dump_stats(ob):
    me = ob.data
    print(f"[stats] {ob.name}: verts={len(me.vertices)} faces={len(me.polygons)}")
