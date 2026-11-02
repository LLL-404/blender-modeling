# -*- coding: utf-8 -*-
"""资产化：UV 展开、UV 质量统计、UV 布局导出。

口径说明：
- 拉伸比 = sqrt(UV 三角面积 / 3D 三角面积)，单位「UV/米」；绝对值与贴图分辨率有关，
  只看 p95/p05 的离散度（spread），越小说明 UV 越均匀。
- island_count 用「同一顶点且 UV 相同 → 合并」的并查集，沿面内 loop 连通。
- 布局图不走 `uv.export_layout`（它依赖 GPU，headless 会报 gpu.init 错误），
  改为 numpy 自己光栅化三角边，直接写 PNG。
"""
import bpy
import math
import os

import numpy as np

from meshkit import select_only


def ensure_uv(ob, name="UVMap"):
    me = ob.data
    layer = me.uv_layers.get(name)
    if layer is None:
        layer = me.uv_layers.new(name=name)
    me.uv_layers.active = layer
    layer.active_render = True
    return layer


def unwrap(ob, angle_deg=66.0, margin=0.003, pack=True):
    """按锐角分岛智能展开，再打包进 0~1。原地修改。"""
    ensure_uv(ob)
    select_only(ob)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle_deg),
                             island_margin=margin,
                             area_weight=0.0,
                             correct_aspect=True,
                             scale_to_bounds=False)
    bpy.ops.uv.select_all(action='SELECT')
    if pack:
        try:
            bpy.ops.uv.pack_islands(rotate=True, margin=margin)
        except TypeError:
            bpy.ops.uv.pack_islands()
    bpy.ops.object.mode_set(mode='OBJECT')
    return ob.data.uv_layers.active


def _uv_arrays(me, uv_layer):
    me.calc_loop_triangles()
    nt = len(me.loop_triangles)
    tris = np.empty(nt * 3, dtype=np.int32)
    me.loop_triangles.foreach_get("vertices", tris)
    loops = np.empty(nt * 3, dtype=np.int32)
    me.loop_triangles.foreach_get("loops", loops)
    co = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get("co", co)
    uv = np.empty(len(me.loops) * 2, dtype=np.float64)
    uv_layer.data.foreach_get("uv", uv)
    return (tris.reshape(-1, 3), loops.reshape(-1, 3),
            co.reshape(-1, 3), uv.reshape(-1, 2))


def island_count(ob):
    me = ob.data
    layer = me.uv_layers.active
    if layer is None:
        return 0
    parent = list(range(len(me.loops)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    first = {}
    for li, loop in enumerate(me.loops):
        u, v = layer.data[li].uv
        key = (loop.vertex_index, round(u, 5), round(v, 5))
        if key in first:
            union(li, first[key])
        else:
            first[key] = li
    for p in me.polygons:
        ls = p.loop_indices
        for i in range(1, len(ls)):
            union(ls[0], ls[i])
    return len({find(i) for i in range(len(parent))})


def stats(ob):
    me = ob.data
    layer = me.uv_layers.active
    if layer is None:
        return {"error": "no_uv"}
    tris, loops, co, uv = _uv_arrays(me, layer)
    p0, p1, p2 = co[tris[:, 0]], co[tris[:, 1]], co[tris[:, 2]]
    a3 = 0.5 * np.linalg.norm(np.cross(p1 - p0, p2 - p0), axis=1)
    q0, q1, q2 = uv[loops[:, 0]], uv[loops[:, 1]], uv[loops[:, 2]]
    e1 = q1 - q0
    e2 = q2 - q0
    a2 = 0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])

    ok = a3 > 1e-12
    degen = int(np.count_nonzero(ok & (a2 <= 1e-12)))
    ratio = np.sqrt(a2[ok] / a3[ok])
    ratio = ratio[np.isfinite(ratio)]

    def q(f):
        return float(np.quantile(ratio, f)) if ratio.size else 0.0

    return {
        "uv_layer": layer.name,
        "uv_area": round(float(a2.sum()), 5),
        "islands": island_count(ob),
        "loops": len(me.loops),
        "uv_vert_ratio": round(len({(round(u, 5), round(v, 5))
                                    for u, v in uv.tolist()}) / len(me.loops), 3),
        "tris": int(ratio.size),
        "degenerate": degen,
        "p05": round(q(0.05), 4),
        "p50": round(q(0.50), 4),
        "p95": round(q(0.95), 4),
        "spread": round(q(0.95) / q(0.05), 2) if q(0.05) > 0 else 0.0,
        "bounds": [round(float(uv[:, 0].min()), 3), round(float(uv[:, 1].min()), 3),
                   round(float(uv[:, 0].max()), 3), round(float(uv[:, 1].max()), 3)],
    }


def raster_layout(ob, path, size=1024, samples=5):
    """headless 可用的 UV 布局图：逐三角边采样写像素，蓝线 + 深底。"""
    me = ob.data
    layer = me.uv_layers.active
    if layer is None:
        return None
    me.calc_loop_triangles()
    nt = len(me.loop_triangles)
    loops = np.empty(nt * 3, dtype=np.int32)
    me.loop_triangles.foreach_get("loops", loops)
    loops = loops.reshape(-1, 3)
    uv = np.empty(len(me.loops) * 2, dtype=np.float64)
    layer.data.foreach_get("uv", uv)
    p = uv.reshape(-1, 2)[loops]                     # (T, 3, 2)

    edges = np.stack([p[:, 0], p[:, 1], p[:, 1], p[:, 2], p[:, 2], p[:, 0]],
                     axis=1).reshape(-1, 2, 2)        # (3T, 2, 2)
    t = np.linspace(0.0, 1.0, samples)[None, :, None]
    pts = edges[:, 0:1, :] * (1.0 - t) + edges[:, 1:2, :] * t
    xy = np.clip((pts * (size - 1)).astype(np.int32), 0, size - 1)

    img = np.zeros((size, size, 4), dtype=np.float32)
    img[:, :, 3] = 1.0
    img[:, :, 0:3] = 0.016
    rows = xy[:, :, 1]
    cols = xy[:, :, 0]
    img[rows, cols, 0] = 0.24
    img[rows, cols, 1] = 0.62
    img[rows, cols, 2] = 1.00

    im = bpy.data.images.new("uv_layout", size, size, alpha=True)
    im.pixels.foreach_set(img.ravel())
    im.filepath_raw = path
    im.file_format = 'PNG'
    im.save()
    bpy.data.images.remove(im)
    return path if os.path.exists(path) else None


def report(tag, s):
    if "error" in s:
        return "[{0}] UV 缺失: {1}".format(tag, s["error"])
    return ("[{0}] layer={1} uv_area={2} islands={3} uv_vert_ratio={4} tris={5} "
            "degen={6} p05={7} p50={8} p95={9} spread={10} bounds={11}").format(
                tag, s["uv_layer"], s["uv_area"], s["islands"], s["uv_vert_ratio"],
                s["tris"], s["degenerate"], s["p05"], s["p50"], s["p95"],
                s["spread"], s["bounds"])