# -*- coding: utf-8 -*-
"""bapi · 对象层：创建、链接、合并、变换、包围盒。

`join()` 刻意不用 `bpy.ops.object.join()`——那个依赖 active/selected，
headless 下容易并错对象。这里直接拼顶点，材质槽做索引重映射。
"""

import bpy
from mathutils import Matrix, Vector


def link(ob, collection=None):
    """把对象挂进集合（默认当前场景的活动集合）。"""
    coll = collection or bpy.context.collection
    if ob.name not in coll.objects:
        coll.objects.link(ob)
    return ob


def new_object(name, data, collection=None):
    ob = bpy.data.objects.new(name, data)
    return link(ob, collection)


def select_only(ob):
    """ops 调用前的上下文准备。bapi 自己尽量不用，留给外部。"""
    vl = bpy.context.view_layer
    for o in vl.objects:
        o.select_set(False)
    ob.select_set(True)
    vl.objects.active = ob
    return ob


def delete(ob):
    data = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    if data is not None and getattr(data, "users", 0) == 0:
        if isinstance(data, bpy.types.Mesh):
            bpy.data.meshes.remove(data)


def stats(ob):
    me = ob.data
    smooth = sum(1 for p in me.polygons if p.use_smooth)
    return {
        "name": ob.name,
        "verts": len(me.vertices),
        "edges": len(me.edges),
        "polys": len(me.polygons),
        "materials": [m.name if m else None for m in me.materials],
        "smooth_polys": smooth,
        "modifiers": [m.type for m in ob.modifiers],
    }


def bbox(ob, world=True, update=True):
    """返回 (min, max) 两个 Vector。空网格返回 None。

    注意：刚改过 `ob.location` 时 `matrix_world` 还没刷新，
    所以默认先 `view_layer.update()`。批量量测时可传 update=False 省时间。
    """
    pts = [v.co for v in ob.data.vertices]
    if not pts:
        return None
    if world and update:
        bpy.context.view_layer.update()
    mw = ob.matrix_world if world else Matrix.Identity(4)
    xs = [(mw @ p) for p in pts]
    lo = Vector((min(p.x for p in xs), min(p.y for p in xs), min(p.z for p in xs)))
    hi = Vector((max(p.x for p in xs), max(p.y for p in xs), max(p.z for p in xs)))
    return lo, hi


def apply_transform(ob):
    """把 matrix_world 烘进网格，再把对象矩阵归一。

    比 bpy.ops.object.transform_apply 少一层 context 依赖。
    注意：网格若被多个对象共享，会一起被改。
    """
    me = ob.data
    me.transform(ob.matrix_world)
    me.update()
    ob.matrix_world = Matrix.Identity(4)
    return ob


def join(objs, name="joined"):
    """把若干网格对象拼成一个。保留材质槽与平滑标记。

    全程走数据层：不选中、不激活、不调用 ops。
    """
    objs = [o for o in objs if o is not None and o.type == 'MESH']
    if not objs:
        raise ValueError("join: 没有可用的网格对象")

    mats = []
    verts, faces, mat_idx, smooth = [], [], [], []

    for ob in objs:
        base = len(verts)
        mw = ob.matrix_world
        for v in ob.data.vertices:
            verts.append(tuple(mw @ v.co))

        remap = {}
        for i, m in enumerate(ob.data.materials):
            if m is None:
                continue
            if m not in mats:
                mats.append(m)
            remap[i] = mats.index(m)

        for p in ob.data.polygons:
            faces.append(tuple(base + i for i in p.vertices))
            mat_idx.append(remap.get(p.material_index, 0))
            smooth.append(p.use_smooth)

    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    me.update()
    for m in mats:
        me.materials.append(m)
    for p, mi, sm in zip(me.polygons, mat_idx, smooth):
        p.material_index = mi
        p.use_smooth = sm

    out = new_object(name, me)
    out.matrix_world = Matrix.Identity(4)
    return out


def duplicate(ob, name=None):
    me = ob.data.copy()
    new = new_object(name or (ob.name + "_copy"), me)
    new.matrix_world = ob.matrix_world.copy()
    return new
