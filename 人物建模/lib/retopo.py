# -*- coding: utf-8 -*-
"""资产化：面型统计与残余三角收口。

只做「顶点集合不变」的拓扑整理（tris_convert_to_quads），所以顶点组权重与
Armature 修改器都不受影响；QuadriFlow 那类重建顶点的方式不在此模块使用。
"""
import bpy
import math

from meshkit import select_only


def face_stats(ob):
    me = ob.data
    tri = quad = ngon = 0
    for p in me.polygons:
        n = len(p.vertices)
        if n == 3:
            tri += 1
        elif n == 4:
            quad += 1
        else:
            ngon += 1
    total = len(me.polygons)
    return {
        "verts": len(me.vertices),
        "total": total,
        "tri": tri,
        "quad": quad,
        "ngon": ngon,
        "quad_pct": round(100.0 * quad / total, 2) if total else 0.0,
        "tri_pct": round(100.0 * tri / total, 2) if total else 0.0,
    }


def tri_by_material(ob):
    """三角面按材质槽分布，用来判断残余三角是否集中在贴片/发片尖端。"""
    me = ob.data
    names = [m.name if m else "<none>" for m in me.materials]
    out = {}
    for p in me.polygons:
        if len(p.vertices) != 3:
            continue
        i = p.material_index
        key = names[i] if i < len(names) else "<none>"
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def tris_to_quads(ob, face_deg=40.0, shape_deg=40.0,
                  materials=True, uvs=True, seam=True, sharp=True):
    """合并相邻三角为四边。顶点不变，权重安全。"""
    select_only(ob)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.tris_convert_to_quads(
        face_threshold=math.radians(face_deg),
        shape_threshold=math.radians(shape_deg),
        topology_influence=0.0,
        uvs=uvs,
        vcols=False,
        seam=seam,
        sharp=sharp,
        materials=materials,
        deselect_joined=False,
    )
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    return ob


def line(tag, s):
    return ("[{0}] verts={1} faces={2} quad={3}({4}%) tri={5}({6}%) ngon={7}").format(
        tag, s["verts"], s["total"], s["quad"], s["quad_pct"],
        s["tri"], s["tri_pct"], s["ngon"])