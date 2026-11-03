# -*- coding: utf-8 -*-
"""扫描当前 Blender 的 API 表面，产出「机器可验证」的目录。

必须在 blender.exe 进程内跑：

    blender -b --factory-startup --python gen_catalog.py

产物写到 ./catalog/：
    api.json      结构化全量（供程序读）
    index.md      总览与统计
    0x_*.md       分域清单（供人和 AI 读）

为什么用扫描而不是手写：
    版本会漂。Blender 5.2 已经删掉了 `scene.eevee.use_gtao`，
    手抄的文档第二天就是错的。这份目录每次重跑都反映真实安装。
"""

import bpy
import bmesh
import json
import os
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "catalog")

# 只扫这些类型，避免把 bpy.types 里几千个 node 类型全展开
CORE_TYPES = [
    "Object", "Mesh", "Material", "Scene", "World", "Camera", "Light",
    "Armature", "Bone", "EditBone", "PoseBone", "Action", "Collection",
    "Curve", "Spline", "Image", "NodeTree", "Node", "NodeSocket",
    "Modifier", "Constraint", "VertexGroup", "ShapeKey", "Text",
]

OP_NAMESPACES = [
    "object", "mesh", "modifier", "material", "node", "render",
    "export_scene", "import_scene", "curve", "armature", "pose",
    "sculpt", "uv", "view3d", "wm", "image", "transform",
]

NODE_PREFIXES = [
    "ShaderNode", "GeometryNode", "CompositorNode", "FunctionNode", "TextureNode",
]


def enum_ids(prop):
    try:
        return [i.identifier for i in prop.enum_items]
    except Exception:
        return []


def props_of(rna, limit=300):
    out = []
    for p in rna.bl_rna.properties:
        if p.identifier == "rna_type":
            continue
        d = {"id": p.identifier, "type": p.type, "name": p.name,
             "readonly": bool(p.is_readonly)}
        if p.type == "ENUM":
            d["enum"] = enum_ids(p)
        if p.type in ("INT", "FLOAT") and not p.is_array:
            lo, hi = getattr(p, "hard_min", None), getattr(p, "hard_max", None)
            if lo is not None or hi is not None:
                d["range"] = [lo, hi]
        if getattr(p, "is_array", False):
            d["array"] = True
        out.append(d)
        if len(out) >= limit:
            break
    return out


def collect():
    data = {}
    data["_meta"] = {
        "version": bpy.app.version_string,
        "binary": bpy.app.binary_path,
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "factory_startup": bpy.app.factory_startup,
    }

    # ---- 渲染环境 ----
    sc = bpy.context.scene
    data["render"] = {
        "engines": [i.identifier for i in
                    bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items],
        "view_transforms": [i.identifier for i in
                            sc.view_settings.bl_rna.properties["view_transform"].enum_items],
        "looks": [i.identifier for i in
                  sc.view_settings.bl_rna.properties["look"].enum_items],
        "eevee_knobs": list(sc.eevee.bl_rna.properties.keys())
                        if hasattr(sc, "eevee") else [],
        "image_formats": [i.identifier for i in
                          bpy.types.ImageFormatSettings.bl_rna.properties["file_format"].enum_items],
    }

    # ---- 核心类型 ----
    data["types"] = {}
    for name in CORE_TYPES:
        rna = getattr(bpy.types, name, None)
        if rna is None:
            continue
        data["types"][name] = props_of(rna)

    # ---- 修改器 ----
    data["modifiers"] = {
        "types": [i.identifier for i in
                  bpy.types.Modifier.bl_rna.properties["type"].enum_items],
        "props": props_of(bpy.types.Modifier),
    }

    # ---- 约束 ----
    data["constraints"] = {
        "types": [i.identifier for i in
                  bpy.types.Constraint.bl_rna.properties["type"].enum_items],
    }

    # ---- bmesh 算子 ----
    bops = []
    for n in sorted(dir(bmesh.ops)):
        if n.startswith("_"):
            continue
        try:
            doc = (getattr(bmesh.ops, n).__doc__ or "").strip().splitlines()
        except Exception:
            doc = []
        bops.append({"name": n, "sig": (doc[0] if doc else "")[:200]})
    data["bmesh_ops"] = bops

    # ---- 节点类型 ----
    data["nodes"] = {}
    for prefix in NODE_PREFIXES:
        data["nodes"][prefix] = sorted(n for n in dir(bpy.types) if n.startswith(prefix))

    # ---- 操作符 ----
    ops = {}
    for ns in OP_NAMESPACES:
        sub = getattr(bpy.ops, ns, None)
        if sub is None:
            continue
        try:
            names = sorted(n for n in dir(sub) if not n.startswith("_"))
        except Exception:
            continue
        items = []
        for n in names:
            try:
                doc = (getattr(sub, n).__doc__ or "").strip().splitlines()
                doc0 = (doc[0] if doc else "")[:100]
            except Exception:
                doc0 = ""
            items.append({"name": n, "doc": doc0})
        ops[ns] = items
    data["ops"] = ops

    # ---- glTF 导出参数 ----
    try:
        gp = bpy.ops.export_scene.gltf.get_rna_type().properties
        data["gltf"] = sorted(k for k in gp.keys() if k.startswith("export_"))
    except Exception as e:
        data["gltf"] = ["<unavailable: %s>" % e]

    return data


# ---------------- Markdown 渲染 ----------------

def md_table(rows, head):
    out = ["| " + " | ".join(head) + " |",
           "|" + "|".join(["---"] * len(head)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "\\|") for c in r) + " |")
    return "\n".join(out)


def write_md(data):
    os.makedirs(OUT, exist_ok=True)
    meta = data["_meta"]

    # index
    lines = [
        "# Blender API 目录",
        "",
        "由 `gen_catalog.py` 在运行中的 Blender 内扫描生成，**不是手抄文档**。",
        "",
        md_table([
            ["Blender", meta["version"]],
            ["binary", "`%s`" % meta["binary"]],
            ["生成时间", meta["generated"]],
            ["factory_startup", meta["factory_startup"]],
            ["渲染引擎", ", ".join(data["render"]["engines"])],
            ["修改器类型", len(data["modifiers"]["types"])],
            ["bmesh 算子", len(data["bmesh_ops"])],
            ["节点类型", sum(len(v) for v in data["nodes"].values())],
            ["操作符", sum(len(v) for v in data["ops"].values())],
        ], ["项", "值"]),
        "",
        "## 分域",
        "",
        "| 文件 | 内容 |",
        "|---|---|",
        "| [01_env.md](01_env.md) | 渲染引擎、色彩管理、EEVEE 旋钮、图像格式 |",
        "| [02_types.md](02_types.md) | 核心类型的属性表（Object/Mesh/Material/…） |",
        "| [03_modifiers.md](03_modifiers.md) | 修改器与约束的完整类型枚举 |",
        "| [04_bmesh.md](04_bmesh.md) | bmesh 算子及签名首行 |",
        "| [05_nodes.md](05_nodes.md) | 着色/几何/合成/函数节点清单 |",
        "| [06_ops.md](06_ops.md) | 操作符清单（含 headless 可用性提示） |",
        "| [07_gltf.md](07_gltf.md) | glTF 导出参数 |",
        "",
        "> 判读原则：**目录只证明「存在」，不证明「能用」**。",
        "> 无头可用性见 `../bapi/` 的封装与 `../selftest.py` 的实测。",
        "",
    ]
    with open(os.path.join(OUT, "index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # 01 env
    r = data["render"]
    lines = ["# 环境与渲染", "",
             "## 渲染引擎", "", "```", *r["engines"], "```", "",
             "## 色彩管理 view_transform", "", "```", *r["view_transforms"], "```", "",
             "## look", "", "```", *r["looks"], "```", "",
             "## EEVEE 旋钮（%d）" % len(r["eevee_knobs"]), "", "```",
             *sorted(r["eevee_knobs"]), "```", "",
             "## 图像格式", "", "```", *r["image_formats"], "```", ""]
    with open(os.path.join(OUT, "01_env.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # 02 types
    lines = ["# 核心类型属性", "",
             "`readonly` 表示只能读不能写；`enum` 是该属性的合法取值。", ""]
    for tname, props in data["types"].items():
        lines.append("## %s（%d）" % (tname, len(props)))
        lines.append("")
        rows = []
        for p in props:
            extra = ""
            if p.get("enum"):
                e = p["enum"]
                extra = ", ".join(e[:6]) + (" …" if len(e) > 6 else "")
            if p.get("range"):
                extra = "range %s..%s" % tuple(p["range"])
            rows.append([p["id"], p["type"], "RO" if p["readonly"] else "",
                         extra.replace("|", "/")])
        lines.append(md_table(rows, ["属性", "类型", "", "取值/范围"]))
        lines.append("")
    with open(os.path.join(OUT, "02_types.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # 03 modifiers
    lines = ["# 修改器与约束", "",
             "## 修改器类型（%d）" % len(data["modifiers"]["types"]), "", "```",
             " ".join(data["modifiers"]["types"]), "```", "",
             "## 约束类型（%d）" % len(data["constraints"]["types"]), "", "```",
             " ".join(data["constraints"]["types"]), "```", ""]
    with open(os.path.join(OUT, "03_modifiers.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # 04 bmesh
    lines = ["# bmesh 算子（%d）" % len(data["bmesh_ops"]), "",
             "签名取自运行时 docstring，可能被截断；调用前用 `help(bmesh.ops.x)` 确认。", ""]
    rows = [[o["name"], (o["sig"] or "").replace("|", "/")] for o in data["bmesh_ops"]]
    lines.append(md_table(rows, ["算子", "签名首行"]))
    with open(os.path.join(OUT, "04_bmesh.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # 05 nodes
    lines = ["# 节点类型", ""]
    for prefix, names in data["nodes"].items():
        lines.append("## %s（%d）" % (prefix, len(names)))
        lines.append("")
        lines.append("```")
        lines.extend(names)
        lines.append("```")
        lines.append("")
    with open(os.path.join(OUT, "05_nodes.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # 06 ops
    lines = ["# 操作符", "",
             "无头模式下 `bpy.ops` 的 poll 可能失败。标 ⚠ 的是本仓实测"
             "在 `-b` 下不可靠的命名空间。", ""]
    risky = {"sculpt", "view3d"}
    for ns, items in data["ops"].items():
        mark = " ⚠" if ns in risky else ""
        lines.append("## %s（%d）%s" % (ns, len(items), mark))
        lines.append("")
        rows = [[i["name"], i["doc"].replace("|", "/")] for i in items]
        lines.append(md_table(rows, ["操作符", "说明"]))
        lines.append("")
    with open(os.path.join(OUT, "06_ops.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # 07 gltf
    lines = ["# glTF 导出参数", "", "```", *data["gltf"], "```", ""]
    with open(os.path.join(OUT, "07_gltf.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    data = collect()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "api.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    write_md(data)
    print("[catalog] version=%s" % data["_meta"]["version"])
    print("[catalog] types=%d bmesh_ops=%d nodes=%d ops=%d" % (
        len(data["types"]), len(data["bmesh_ops"]),
        sum(len(v) for v in data["nodes"].values()),
        sum(len(v) for v in data["ops"].values())))
    print("[catalog] out=%s" % OUT)


main()
