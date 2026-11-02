# -*- coding: utf-8 -*-
"""资产化：色板贴图、AO 烘焙、法线一致性。

- `palette_atlas()` 不走渲染烘焙：按材质槽取「toon 的 light 档 / flat 的 Emission」
  作为 albedo，直接在 UV 空间逐三角填充。它是给后续手调用的起点图，
  不会被光照或视角污染（区别于 EMIT pass）。
- `bake_ao()` 用 Cycles 的 AO pass，写进每个材质的 Image Texture 节点。
"""
import bpy
import os

import numpy as np

from meshkit import select_only


def _rgb(c):
    return (float(c[0]), float(c[1]), float(c[2]))


def material_albedo(mat):
    """toon → base × ramp 最亮档；flat → Emission；PBR → Base Color。

    不能只取 ramp 的亮档：look.toon() 的最终色是 Mix(MULTIPLY) 的
    base（inputs[6]）× ramp（inputs[7]）。只取 ramp 会让皮肤发白、头发
    从深棕变成灰紫（M6 E4 对比图实测）。
    """
    if mat is None or not mat.use_nodes:
        return (0.6, 0.6, 0.6)
    nt = mat.node_tree
    ramp = next((n for n in nt.nodes if n.type == 'VALTORGB'), None)
    if ramp is not None and len(ramp.color_ramp.elements):
        light = _rgb(ramp.color_ramp.elements[-1].color)
        mix = next((n for n in nt.nodes
                    if n.type == 'MIX' and n.blend_type == 'MULTIPLY'), None)
        if mix is not None:
            base = _rgb(mix.inputs[6].default_value)
            return (base[0] * light[0], base[1] * light[1], base[2] * light[2])
        return light
    em = next((n for n in nt.nodes if n.type == 'EMISSION'), None)
    if em is not None:
        return _rgb(em.inputs["Color"].default_value)
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is not None:
        return _rgb(bsdf.inputs["Base Color"].default_value)
    return (0.6, 0.6, 0.6)


def _dilate(img, mask, iterations=12):
    """把 UV 岛颜色向外扩张，避免双线性采样采到背景形成黑缝。"""
    rgb = img[:, :, :3]
    filled = mask.copy()
    for _ in range(iterations):
        acc = np.zeros_like(rgb)
        cnt = np.zeros(mask.shape, dtype=np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1),
                       (1, 1), (1, -1), (-1, 1), (-1, -1)):
            acc += np.roll(rgb, (dy, dx), (0, 1)) * np.roll(filled, (dy, dx), (0, 1))[..., None]
            cnt += np.roll(filled, (dy, dx), (0, 1))
        grow = (~filled) & (cnt > 0)
        if not grow.any():
            break
        rgb[grow] = acc[grow] / cnt[grow][..., None]
        filled |= grow
    return filled


def palette_atlas(ob, path, size=1024):
    """按材质槽把颜色填进 UV 岛，输出一张 albedo 图。"""
    me = ob.data
    layer = me.uv_layers.active
    if layer is None:
        return None
    me.calc_loop_triangles()
    nt = len(me.loop_triangles)
    loops = np.empty(nt * 3, dtype=np.int32)
    me.loop_triangles.foreach_get("loops", loops)
    loops = loops.reshape(-1, 3)
    tri_mat = np.empty(nt, dtype=np.int32)
    me.loop_triangles.foreach_get("material_index", tri_mat)
    uv = np.empty(len(me.loops) * 2, dtype=np.float64)
    layer.data.foreach_get("uv", uv)
    uvp = uv.reshape(-1, 2)[loops] * (size - 1)

    albedo = [material_albedo(m) for m in me.materials]
    if not albedo:
        albedo = [(0.6, 0.6, 0.6)]

    img = np.full((size, size, 4), 0.0, dtype=np.float32)
    img[:, :, 3] = 1.0
    painted = np.zeros((size, size), dtype=bool)

    for t in range(nt):
        p = uvp[t]
        x0, y0 = np.floor(p.min(axis=0)).astype(int)
        x1, y1 = np.ceil(p.max(axis=0)).astype(int)
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(size - 1, x1), min(size - 1, y1)
        if x1 < x0 or y1 < y0:
            continue
        xs = np.arange(x0, x1 + 1)
        ys = np.arange(y0, y1 + 1)
        X, Y = np.meshgrid(xs, ys)

        d = ((p[1, 1] - p[2, 1]) * (p[0, 0] - p[2, 0]) +
             (p[2, 0] - p[1, 0]) * (p[0, 1] - p[2, 1]))
        if abs(d) < 1e-12:
            continue
        a = ((p[1, 1] - p[2, 1]) * (X - p[2, 0]) +
             (p[2, 0] - p[1, 0]) * (Y - p[2, 1])) / d
        b = ((p[2, 1] - p[0, 1]) * (X - p[2, 0]) +
             (p[0, 0] - p[2, 0]) * (Y - p[2, 1])) / d
        c = 1.0 - a - b
        inside = (a >= -1e-6) & (b >= -1e-6) & (c >= -1e-6)
        if not inside.any():
            continue
        mi = int(tri_mat[t])
        col = albedo[mi] if mi < len(albedo) else albedo[0]
        img[Y[inside], X[inside], 0:3] = col
        painted[Y[inside], X[inside]] = True

    _dilate(img, painted, iterations=12)

    # 实测：bpy image.save() 对 float 缓冲是线性直通（0.93 → 237），
    # 而 glTF/引擎按 sRGB 解释 PNG，不转会让 albedo 整体偏暗。
    rgb = np.clip(img[:, :, :3], 0.0, 1.0)
    img[:, :, :3] = np.where(rgb <= 0.0031308, rgb * 12.92,
                             1.055 * np.power(rgb, 1.0 / 2.4) - 0.055)

    im = bpy.data.images.new("albedo_" + ob.name, size, size, alpha=True)
    im.pixels.foreach_set(img.ravel())
    im.filepath_raw = path
    im.file_format = 'PNG'
    im.save()
    bpy.data.images.remove(im)
    return path if os.path.exists(path) else None


def _ensure_bake_image(ob, image):
    made = []
    for slot in ob.material_slots:
        mat = slot.material
        if mat is None or not mat.use_nodes:
            continue
        nt = mat.node_tree
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = image
        node.location = (-900, 500)
        node.select = True
        nt.nodes.active = node
        made.append((nt, node))
    return made


def bake_ao(ob, path, size=512, samples=8, margin=4):
    """Cycles 烘焙 AO 到 UV（不依赖材质 BSDF，toon/flat 都能烤）。

    必须先关掉全部修改器：Solidify 描边壳会在渲染态外扩一圈，
    Armature 也会把 evaluated mesh 换成另一套（实测开着时 AO 全 0）。
    这里只烤基础网格，烤完原样恢复。
    """
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.render.bake.use_pass_direct = False
    sc.render.bake.use_pass_indirect = False
    sc.render.bake.margin = margin

    img = bpy.data.images.new("ao_" + ob.name, size, size, alpha=False)
    made = _ensure_bake_image(ob, img)
    state = [(m, m.show_render, m.show_viewport) for m in ob.modifiers]
    for m, _r, _v in state:
        m.show_render = False
        m.show_viewport = False
    select_only(ob)
    try:
        bpy.ops.object.bake(type='AO', margin=margin, use_clear=True)
    finally:
        for m, r, v in state:
            m.show_render = r
            m.show_viewport = v
        for nt, node in made:
            nt.nodes.remove(node)
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    return path if os.path.exists(path) else None


def normals_report(ob):
    """rest 状态法线一致性：recalc 前后发生翻转的面数。"""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    before = [f.normal.copy() for f in bm.faces]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    changed = sum(1 for f, n in zip(bm.faces, before) if f.normal.dot(n) < 0.0)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return {"faces": len(ob.data.polygons), "flipped": changed}