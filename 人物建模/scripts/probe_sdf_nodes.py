# -*- coding: utf-8 -*-
"""只读探针：列出本机 Blender 的原生 SDF 几何节点、输入参数与运算枚举。

不建模型、不改任何产物。用于 `docs/SDF融合体调研.md` 的可行性结论复现。

    "D:/Program Files/Blender Foundation/Blender 5.2/blender.exe" \
        -b --factory-startup --python-exit-code 1 --python scripts/probe_sdf_nodes.py
"""
import bpy

KEEP_ENUM = {"operation", "mode", "data_type", "interpolation",
             "resolution_mode", "domain", "grid_type", "filter_type"}
TRY = (
    "GeometryNodeMeshToSDFGrid", "GeometryNodeSDFGridBoolean",
    "GeometryNodeSDFGridFillet", "GeometryNodeSDFGridOffset",
    "GeometryNodeSDFGridMean", "GeometryNodeSDFGridLaplacian",
    "GeometryNodeGridToMesh", "GeometryNodeMeshToVolume",
    "GeometryNodeVolumeToMesh", "GeometryNodeSDFGridSphere",
)


def main():
    print("[sdf] BLENDER", bpy.app.version_string)
    names = [n for n in dir(bpy.types) if "SDFGrid" in n or "GridToMesh" in n
             or "MeshToSDF" in n]
    print("[sdf] RNA 里 SDF 相关类 %d 个：%s" % (len(names), "、".join(sorted(names))))

    tree = bpy.data.node_groups.new("probe_sdf", "GeometryNodeTree")
    for name in TRY:
        try:
            nd = tree.nodes.new(name)
        except Exception as exc:
            print("[sdf] MISS %-36s %s" % (name, type(exc).__name__))
            continue
        print("[sdf] OK   %s" % name)
        for p in nd.bl_rna.properties:
            if p.type == "ENUM" and p.identifier in KEEP_ENUM:
                print("       enum %-14s %s" % (
                    p.identifier, [i.identifier for i in p.enum_items]))
        for s in nd.inputs:
            default = getattr(s, "default_value", "—")
            print("       in   %-22s %-20s default=%s" % (
                s.name, s.bl_idname, default))
    bpy.data.node_groups.remove(tree)


if __name__ == "__main__":
    main()
