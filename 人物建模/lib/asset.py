# -*- coding: utf-8 -*-
"""资产化：描边壳剥离、PBR 材质替换、glTF 导出与回读校验。"""
import bpy
import os


def strip_for_export(ob):
    """去掉描边 Solidify 等非蒙皮修改器，只保留 Armature。"""
    removed = []
    for m in list(ob.modifiers):
        if m.type != 'ARMATURE':
            removed.append((m.name, m.type))
            ob.modifiers.remove(m)
    return removed


def _pbr_material(name, albedo_path, roughness=0.6):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (100, 0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.location = (-260, 0)
    tex.image = bpy.data.images.load(albedo_path, check_existing=True)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def to_single_pbr(ob, albedo_path, roughness=0.6):
    """整网格换成一个 PBR 材质：albedo 已按原材质槽烧进 UV 图。"""
    removed = strip_for_export(ob)
    ob.data.materials.clear()
    ob.data.materials.append(_pbr_material("pbr_" + ob.name, albedo_path, roughness))
    return removed


def export_glb(path, objects):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:
        if ob is not None:
            ob.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format='GLB',
        use_selection=True,
        export_apply=False,
        export_skins=True,
        export_animations=False,
        export_yup=True,
        export_texcoords=True,
        export_normals=True,
        export_tangents=False,
        export_materials='EXPORT',
        export_image_format='AUTO',
    )
    return path if os.path.exists(path) else None


def readback(path, known=("Body", "Hands", "Head", "Hair", "Outfit")):
    """新建空场景导入 glb，返回结构与蒙皮统计。

    glTF 导入器会额外生成骨骼辅助网格（实测一个 42v/80f 的 Icosphere），
    它不在 glb 里，是导入器的显示物；这里只统计白名单网格，其余归 extras。
    """
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)
    out = {"meshes": {}, "armatures": {}, "images": len(bpy.data.images),
           "extras": []}
    for ob in bpy.data.objects:
        if ob.type == 'MESH':
            base = ob.name.split(".")[0]
            if base not in known:
                out["extras"].append({"name": ob.name,
                                      "verts": len(ob.data.vertices),
                                      "faces": len(ob.data.polygons)})
                continue
            me = ob.data
            tri = sum(1 for p in me.polygons if len(p.vertices) == 3)
            out["meshes"][base] = {
                "verts": len(me.vertices),
                "faces": len(me.polygons),
                "tri": tri,
                "uv": [l.name for l in me.uv_layers],
                "materials": [m.name if m else None for m in me.materials],
                "vgroups": len(ob.vertex_groups),
                "armature_mod": any(m.type == 'ARMATURE' for m in ob.modifiers),
            }
        elif ob.type == 'ARMATURE':
            out["armatures"][ob.name] = {"bones": len(ob.data.bones)}
    return out


def weights_ok(ob, tol=0.02):
    bad = 0
    for v in ob.data.vertices:
        s = sum(g.weight for g in v.groups)
        if abs(s - 1.0) > tol:
            bad += 1
    return bad, len(ob.data.vertices)