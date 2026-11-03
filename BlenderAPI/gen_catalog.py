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
import re
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


# ---------------- 新增：#1 修改器参数 / #2 节点端口 / #3 OCIO ----------------
#
# 这三个扫描都有「必须先造出实例才能读」的共同点：修改器的参数表挂在具体
# 修改器上（Modifier 基类只有 13 条通用属性），节点的端口挂在具体节点实例上。
# 所以下面的写法是「试建 → 读 → 删掉」，一个都不留在场景里。

# 修改器要挂在不同宿主上才能建：GREASE_PENCIL_* 要 grease pencil 对象，
# MESH_TO_VOLUME / VOLUME_DISPLACE 要 volume 对象。四种宿主覆盖全部 83 类。
MOD_HOST_KINDS = ("mesh", "curve", "grease_pencil", "volume")

# 每种节点前缀优先在哪种 node_tree 上新建（第一个失败就换下一个）
NODE_PREFIX_TREES = {
    "ShaderNode": ("shader", "geometry"),
    "GeometryNode": ("geometry", "shader"),
    "CompositorNode": ("compositor", "shader"),
    "FunctionNode": ("shader", "geometry"),
    "TextureNode": ("texture", "shader"),
}


def _mk_hosts():
    """建四种宿主对象，返回 {kind: object}。用完由 _drop_hosts 删掉。"""
    hosts = {}
    sc = bpy.context.scene

    def link(ob):
        sc.collection.objects.link(ob)
        return ob

    try:
        hosts["mesh"] = link(bpy.data.objects.new("cg_host_mesh", bpy.data.meshes.new("cg_me")))
    except Exception:
        pass
    try:
        cu = bpy.data.curves.new("cg_cu", "CURVE")
        cu.dimensions = "3D"
        sp = cu.splines.new("BEZIER")
        sp.bezier_points.add(1)
        hosts["curve"] = link(bpy.data.objects.new("cg_host_curve", cu))
    except Exception:
        pass
    try:
        gp = bpy.data.grease_pencils.new("cg_gp")
        hosts["grease_pencil"] = link(bpy.data.objects.new("cg_host_gp", gp))
    except Exception:
        pass
    try:
        hosts["volume"] = link(bpy.data.objects.new("cg_host_vol", bpy.data.volumes.new("cg_vol")))
    except Exception:
        pass
    return hosts


def _drop_hosts(hosts):
    for ob in hosts.values():
        data = ob.data
        try:
            bpy.data.objects.remove(ob, do_unlink=True)
        except Exception:
            pass
        try:
            if isinstance(data, bpy.types.Mesh):
                bpy.data.meshes.remove(data)
            elif isinstance(data, bpy.types.Curve):
                bpy.data.curves.remove(data)
            elif isinstance(data, bpy.types.GreasePencil):
                bpy.data.grease_pencils.remove(data)
            elif isinstance(data, bpy.types.Volume):
                bpy.data.volumes.remove(data)
        except Exception:
            pass


def _mk_trees():
    """建四种 node_tree，返回 {kind: tree}。合成树在 5.x 要用 node_groups.new。"""
    trees = {}
    try:
        m = bpy.data.materials.new("cg_mat")
        m.use_nodes = True
        trees["shader"] = m.node_tree
    except Exception:
        pass
    try:
        trees["geometry"] = bpy.data.node_groups.new("cg_ng", "GeometryNodeTree")
    except Exception:
        pass
    try:
        trees["compositor"] = bpy.data.node_groups.new("cg_comp", "CompositorNodeTree")
    except Exception:
        pass
    try:
        trees["texture"] = bpy.data.node_groups.new("cg_tex", "TextureNodeTree")
    except Exception:
        pass
    return trees


def _drop_trees(trees):
    for t in trees.values():
        try:
            for n in list(t.nodes):
                t.nodes.remove(n)
        except Exception:
            pass
    for ng in list(bpy.data.node_groups):
        try:
            bpy.data.node_groups.remove(ng)
        except Exception:
            pass
    for m in list(bpy.data.materials):
        if m.name.startswith("cg_"):
            try:
                bpy.data.materials.remove(m)
            except Exception:
                pass


def _plain(value):
    """把 RNA 属性值转成可 JSON 化的标量/数组；转不了就返回 None。"""
    if value is None or isinstance(value, (bool, int, float, str)):
        if isinstance(value, float):
            return round(value, 5)
        return value
    try:
        if hasattr(value, "__len__"):
            return [round(float(x), 5) for x in value]
    except Exception:
        pass
    return None


# 所有修改器共有的通用属性：查参数表时这些是噪声，单独剔出去
BASE_MOD_PROPS = [
    "name", "type", "show_viewport", "show_render", "show_in_editmode",
    "show_on_cage", "show_expanded", "is_active", "use_pin_to_last",
    "is_override_data", "use_apply_on_spline", "execution_time",
    "persistent_uid", "rna_type",
]


def props_of_instance(inst, skip_common=True):
    """读一个实例上的全部属性：类型 / 默认值 / 枚举取值 / 数值范围。

    skip_common=True 时跳过所有修改器共有的那批（name/type/show_viewport…），
    只留该类特有的参数 —— 那才是查表时真正要找的东西。
    """
    common = set(BASE_MOD_PROPS)
    out = []
    for p in inst.bl_rna.properties:
        if skip_common and p.identifier in common:
            continue
        d = {"id": p.identifier, "type": p.type}
        if p.type == "ENUM":
            d["enum"] = enum_ids(p)
        if p.type in ("INT", "FLOAT") and not p.is_array:
            lo, hi = getattr(p, "hard_min", None), getattr(p, "hard_max", None)
            if lo is not None or hi is not None:
                d["range"] = [lo, hi]
        if getattr(p, "is_array", False):
            d["array"] = True
        if not p.is_readonly:
            v = _plain(getattr(inst, p.identifier, None))
            if v is not None:
                d["default"] = v
        out.append(d)
    return out


def collect_modifiers(mod_types):
    """逐类试建修改器，读它特有的参数。返回 (detail, failed)。"""
    hosts = _mk_hosts()
    detail, failed = {}, []
    for t in mod_types:
        got = None
        errs = []
        for kind in MOD_HOST_KINDS:
            host = hosts.get(kind)
            if host is None:
                continue
            try:
                md = host.modifiers.new("cg_" + t, t)
                if md is None:
                    errs.append("%s:None" % kind)
                    continue
                props = props_of_instance(md)
                detail[t] = {"host": kind, "n": len(props), "props": props}
                host.modifiers.remove(md)
                got = True
                break
            except Exception as e:
                errs.append("%s:%s" % (kind, type(e).__name__))
        if not got:
            failed.append({"type": t, "tried": errs})
    _drop_hosts(hosts)
    return detail, failed


def collect_nodes(node_types):
    """逐个试建节点，读 inputs/outputs。返回 (detail, abstract)。"""
    trees = _mk_trees()
    detail, abstract = {}, []
    for prefix, names in node_types.items():
        order = NODE_PREFIX_TREES.get(prefix, ("shader",))
        for nm in names:
            got = False
            errs = []
            for kind in order:
                tree = trees.get(kind)
                if tree is None:
                    continue
                try:
                    nd = tree.nodes.new(nm)
                except Exception as e:
                    errs.append("%s:%s" % (kind, type(e).__name__))
                    continue
                ins, outs = [], []
                for s in nd.inputs:
                    item = [s.name, s.type]
                    dv = _plain(getattr(s, "default_value", None))
                    if dv is not None:
                        item.append(dv)
                    if getattr(s, "is_multi_input", False):
                        item.append("multi")
                    ins.append(item)
                for s in nd.outputs:
                    item = [s.name, s.type]
                    if getattr(s, "is_multi_input", False):
                        item.append("multi")
                    outs.append(item)
                detail[nm] = {"tree": kind, "in": ins, "out": outs}
                tree.nodes.remove(nd)
                got = True
                break
            if not got:
                # 基类 / node_tree 类型 / CustomGroup / 已删除节点：本来就不能 new
                abstract.append({"node": nm, "reason": errs[0] if errs else "no tree"})
    _drop_trees(trees)
    return detail, abstract


def _ocio_path():
    try:
        rp = bpy.utils.resource_path("LOCAL")
    except Exception:
        return None
    cand = os.path.join(rp, "datafiles", "colormanagement", "config.ocio")
    if os.path.exists(cand):
        return cand
    for root, _dirs, files in os.walk(rp):
        if "config.ocio" in files:
            return os.path.join(root, "config.ocio")
    return None


def collect_colormanagement():
    """view_transform / look 的真实可选值。

    为什么不能只读 RNA 枚举：Blender 5.2 这两个枚举由 OCIO 配置在运行时注入，
    `bl_rna.properties[...].enum_items` 只返回一条占位 'NONE'（实测，当前值却是
    AgX）。所以改从这里读 OCIO 的 displays:/looks: 段，再逐值写回验证。

    为什么 look 要按 view_transform 分组：look 不是全局可用的。实测 5.2：
    view_transform=AgX 时只有 `AgX - *` 那 9 个能写；切到 Filmic/Standard/Raw
    只剩 `Very High Contrast` 等 7 个 Filmic 系；`False Color` 对应 9 个。
    写错就是 TypeError。所以这里把每个 view_transform 下可用的 look 全测一遍。

    换行：OCIO 配置是 CRLF，统一用 splitlines() 切 —— str.split('\\n') 会留下
    行尾 '\\r'，让 `re.match(..., '$')` 匹配不上（在 Windows 的 text mode 下侥幸
    不出错，Linux 上必踩）。
    """
    out = {
        "source": None,
        "displays": {},
        "views": [],
        "view_transforms": [],
        "looks_all": [],
        "looks_available": [],
        "looks_by_view_transform": {},
        "current_display": "",
        "current_view_transform": "",
        "notes": [],
    }
    path = _ocio_path()
    if not path:
        out["notes"].append("OCIO 配置文件未找到，本项为空")
        return out
    out["source"] = path
    lines = open(path, encoding="utf-8", errors="replace", newline="").read().splitlines()

    # displays: 段 —— 2 空格缩进是 display 名，其下 - !<View> {name: X, ...}
    cur, inside = None, False
    for ln in lines:
        if ln.strip() == "displays:" and not ln.startswith(" "):
            inside = True
            continue
        if not inside:
            continue
        if ln and not ln[0].isspace():
            break
        m = re.match(r"^  (\S[^:]*):\s*$", ln)
        if m:
            cur = m.group(1).strip()
            out["displays"][cur] = []
            continue
        m = re.match(r"^\s+- !<View>\s*\{(.*)\}\s*$", ln)
        if m and cur is not None:
            nm = re.search(r"name:\s*([^,}]+)", m.group(1))
            if nm:
                out["displays"][cur].append(nm.group(1).strip())

    # looks: 段 —— 每个 - !<Look> 后面紧跟一条 name:
    inside, want_name = False, False
    for ln in lines:
        if ln.strip() == "looks:" and not ln.startswith(" "):
            inside = True
            continue
        if not inside:
            continue
        if ln and not ln[0].isspace():
            break
        if ln.strip() == "- !<Look>":
            want_name = True
            continue
        if want_name:
            m = re.match(r"^\s+name:\s*(.+?)\s*$", ln)
            if m:
                out["looks_all"].append(m.group(1))
                want_name = False

    sc = bpy.context.scene
    dev = getattr(sc.display_settings, "display_device", "")
    out["current_display"] = dev
    cand = list(out["displays"].get(dev, []))
    out["views"] = cand

    def _set_look_none():
        for v in ("None", ""):
            try:
                sc.view_settings.look = v
                return
            except Exception:
                continue

    # 当前 display 下的 view 名 = Blender 给的 view_transform 可选值，逐个写回验证
    orig = sc.view_settings.view_transform
    ok = []
    for v in cand:
        try:
            sc.view_settings.view_transform = v
            ok.append(v)
        except Exception:
            pass
    try:
        sc.view_settings.view_transform = orig
    except Exception:
        pass
    out["view_transforms"] = ok
    out["current_view_transform"] = orig
    if not ok:
        out["notes"].append("OCIO 解析到 %d 个候选但全部写回失败" % len(cand))

    # look：按 view_transform 分组实测
    for vt in ok:
        try:
            sc.view_settings.view_transform = vt
        except Exception:
            continue
        _set_look_none()
        got = []
        for lk in out["looks_all"]:
            try:
                sc.view_settings.look = lk
                got.append(lk)
            except Exception:
                pass
        out["looks_by_view_transform"][vt] = got
    try:
        sc.view_settings.view_transform = orig
        _set_look_none()
    except Exception:
        pass
    out["looks_available"] = out["looks_by_view_transform"].get(orig, [])
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
    cm = collect_colormanagement()
    data["render"] = {
        "engines": [i.identifier for i in
                    bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items],
        # view_transforms / looks 转由 OCIO 读取，见 collect_colormanagement 的说明
        "view_transforms": cm["view_transforms"],
        "looks": cm["looks_available"],
        "colormanagement": cm,
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
    mod_types = [i.identifier for i in
                 bpy.types.Modifier.bl_rna.properties["type"].enum_items]
    mod_detail, mod_failed = collect_modifiers(mod_types)
    data["modifiers"] = {
        "types": mod_types,
        "props": props_of(bpy.types.Modifier),     # 基类 13 条通用属性
        "detail": mod_detail,                       # 每类自己的参数（新增）
        "unsupported": mod_failed,
        # 这是全仓最常查的一张表：修改器的参数名在这里，不在 bpy.ops 里。
        "howto": "host.modifiers.new(name, 'SOLIDIFY') 之后读 detail.SOLIDIFY.props",
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
    node_types = {}
    for prefix in NODE_PREFIXES:
        node_types[prefix] = sorted(n for n in dir(bpy.types) if n.startswith(prefix))
    node_detail, node_abstract = collect_nodes(node_types)
    data["nodes"] = {
        "by_prefix": node_types,
        "detail": node_detail,      # 每个节点的 inputs/outputs（新增）
        "abstract": node_abstract,  # 不能 new 的：基类 / node_tree / CustomGroup
        "socket_schema": "[name, type, default?, 'multi'?]",
    }

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


def _fmt_val(v):
    """默认值转成表格里好读的一格。"""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, float):
        if v != 0.0 and (abs(v) >= 1e6 or abs(v) < 1e-4):
            return "%.3g" % v
        return ("%.4f" % v).rstrip("0").rstrip(".") or "0"
    if isinstance(v, list):
        if len(v) > 4:
            return "[" + ", ".join(_fmt_val(x) for x in v[:3]) + ", …]"
        return "[" + ", ".join(_fmt_val(x) for x in v) + "]"
    return str(v)


_FLT_MAX = 3.0e38


def _fmt_range(rng):
    """数值范围。float 全域（±3.4e38）等于「没限制」，不占表格一行。"""
    lo, hi = rng[0], rng[1]
    if lo is not None and hi is not None and lo <= -_FLT_MAX and hi >= _FLT_MAX:
        return ""
    return "range %s..%s" % (_fmt_val(lo), _fmt_val(hi))


def _fmt_socket(s):
    """socket 条目 [name, type, default?, 'multi'?] → `名字:类型`。"""
    name, typ = s[0], s[1]
    mark = "*" if "multi" in s[2:] else ""
    return "`%s:%s`%s" % (name.replace("|", "/"), typ, mark)


def write_md(data):
    # 写产物时**不要**显式指定 newline。本仓 core.autocrlf=true：仓库内存 LF、
    # 检出的工作区是 CRLF，Python 按平台默认写（Windows 得 CRLF）正好与之吻合。
    # 曾经试过加 newline="\n" 强制 LF，结果 git status 永久显示这些文件 modified
    # （内容 diff 为空，纯换行规范化噪声）。2026-11-03 实测后撤回。
    os.makedirs(OUT, exist_ok=True)
    meta = data["_meta"]
    mod_detail = data["modifiers"].get("detail", {})
    node_detail = data["nodes"].get("detail", {})
    n_mod_props = sum(v["n"] for v in mod_detail.values())
    n_sockets = sum(len(v["in"]) + len(v["out"]) for v in node_detail.values())

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
            ["修改器类型", "%d（参数已扫 %d 类 / 共 %d 条）"
             % (len(data["modifiers"]["types"]), len(mod_detail), n_mod_props)],
            ["bmesh 算子", len(data["bmesh_ops"])],
            ["节点类型", "%d（端口已扫 %d 个 / 共 %d 个 socket）"
             % (sum(len(v) for v in data["nodes"]["by_prefix"].values()),
                len(node_detail), n_sockets)],
            ["操作符", sum(len(v) for v in data["ops"].values())],
        ], ["项", "值"]),
        "",
        "## 分域",
        "",
        "| 文件 | 内容 |",
        "|---|---|",
        "| [01_env.md](01_env.md) | 渲染引擎、色彩管理（view_transform / look 取自 OCIO）、EEVEE 旋钮、图像格式 |",
        "| [02_types.md](02_types.md) | 核心类型的属性表（Object/Mesh/Material/…） |",
        "| [03_modifiers.md](03_modifiers.md) | 修改器类型枚举 **+ 每类的参数表**（属性名/类型/默认值/取值） |",
        "| [04_bmesh.md](04_bmesh.md) | bmesh 算子及签名首行 |",
        "| [05_nodes.md](05_nodes.md) | 节点清单 **+ 每个节点的输入输出端口**（名字/类型） |",
        "| [06_ops.md](06_ops.md) | 操作符清单（含 headless 可用性提示） |",
        "| [07_gltf.md](07_gltf.md) | glTF 导出参数 |",
        "",
        "> 判读原则：**目录只证明「存在」，不证明「能被 headless 调用」**。",
        "> 参数与端口是从真实实例上读的（试建 → 读 RNA → 删除），比名单可信；",
        "> 但 `bpy.ops` 的 poll 结果仍要看 `../bapi/` 的封装与 `../selftest.py` 的实测。",
        "",
    ]
    with open(os.path.join(OUT, "index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # 01 env
    r = data["render"]
    cm = r.get("colormanagement", {})
    notes = cm.get("notes", [])
    lines = ["# 环境与渲染", "",
             "## 渲染引擎", "", "```", *r["engines"], "```", "",
             "## 色彩管理 view_transform（%d）" % len(r["view_transforms"]), "",
             "> 取自 OCIO 配置并逐个写回验证过。**不要读 RNA 枚举**：",
             "> Blender 5.2 的 `view_settings.bl_rna.properties['view_transform']",
             "> .enum_items` 只返回一条占位 `NONE`，而实际当前值是 `AgX`。",
             ""]
    if cm.get("source"):
        lines.append("> OCIO 配置：`%s`；当前 display：`%s`"
                     % (cm["source"], cm.get("current_display", "")))
        lines.append("")
    for n in notes:
        lines += ["> ⚠ " + n, ""]
    lines += ["```", *r["view_transforms"], "```", ""]

    # 其它 display 下的 view（换 display_device 时才用得上）
    others = {k: v for k, v in cm.get("displays", {}).items()
              if k != cm.get("current_display")}
    if others:
        lines += ["### 其它 display 下的 view", ""]
        for dev, vs in others.items():
            lines += ["**%s**（%d）：`%s`" % (dev, len(vs), "`, `".join(vs)), ""]

    # look —— 按 view_transform 分组，这是本项最容易踩的地方
    byvt = cm.get("looks_by_view_transform", {})
    lines += ["## look（OCIO 共 %d 个，当前 view_transform 下可用 %d 个）"
              % (len(cm.get("looks_all", [])), len(r["looks"])), "",
              "> **look 不是全局可用的**：它由当前 `view_settings.view_transform` 决定。",
              "> 实测 5.2：`AgX` 下只有 `AgX - *` 那批能写，切到 `Filmic` / `Standard` / `Raw`",
              "> 只剩 Filmic 那批。写错直接 `TypeError`。下表按 view_transform 分组。",
              ""]
    if byvt:
        rows = [[vt, str(len(v)),
                 ("`" + "`, `".join(v) + "`") if v else "—"]
                for vt, v in byvt.items()]
        lines.append(md_table(rows, ["view_transform", "可用 look 数", "可用的 look"]))
        lines.append("")
    lines += ["## EEVEE 旋钮（%d）" % len(r["eevee_knobs"]), "", "```",
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
    md = data["modifiers"]
    detail = md.get("detail", {})
    lines = ["# 修改器与约束", "",
             "## 修改器类型（%d）" % len(md["types"]), "", "```",
             " ".join(md["types"]), "```", "",
             "## 约束类型（%d）" % len(data["constraints"]["types"]), "", "```",
             " ".join(data["constraints"]["types"]), "```", ""]

    lines += ["## 修改器参数（%d 类）" % len(detail), "",
              "参数名、类型、默认值都从**真实实例**读取：`host.modifiers.new(name, type)`",
              "之后读 RNA，读完把实例删掉。已剔除下面这批所有修改器共有的通用属性：",
              "",
              "`" + "` · `".join(BASE_MOD_PROPS) + "`",
              "",
              "> **修改器的参数不在 `bpy.ops` 里。** `bpy.ops.modifier` 命名空间在 5.2 实测 0 条；",
              "> 加修改器一律 `ob.modifiers.new(name, TYPE)` 再赋属性，属性名查下表。",
              ""]
    if md.get("unsupported"):
        lines += ["> ⚠ 有 %d 类试建失败：%s"
                  % (len(md["unsupported"]),
                     ", ".join(u["type"] for u in md["unsupported"])), ""]

    for t in sorted(detail):
        d = detail[t]
        lines.append("### %s（%d 条 · 宿主 %s）" % (t, d["n"], d["host"]))
        lines.append("")
        rows = []
        for p in d["props"]:
            extra = ""
            if p.get("enum"):
                e = p["enum"]
                extra = ", ".join(e[:6]) + (" …" if len(e) > 6 else "")
            elif p.get("range"):
                extra = _fmt_range(p["range"])
            rows.append([p["id"], p["type"], _fmt_val(p.get("default")),
                         extra.replace("|", "/")])
        lines.append(md_table(rows, ["属性", "类型", "默认", "取值/范围"]))
        lines.append("")
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
    nd = data["nodes"]
    ndetail = nd.get("detail", {})
    lines = ["# 节点类型", "",
             "端口从**真实节点实例**读取（`tree.nodes.new(type)` 后读 `inputs`/`outputs`），",
             "格式 `` `名字:类型` ``，尾部 `*` 表示多输入口（可以接多条线）。",
             "完整结构（含默认值）见 `api.json` → `nodes.detail`。", ""]

    for prefix, names in nd["by_prefix"].items():
        have = [n for n in names if n in ndetail]
        lines.append("## %s（%d，其中可实例化 %d）" % (prefix, len(names), len(have)))
        lines.append("")
        trees = sorted({ndetail[n]["tree"] for n in have})
        if trees:
            lines.append("> node_tree：`%s`" % "` / `".join(trees))
            lines.append("")
        rows = []
        for nm in have:
            d = ndetail[nm]
            ins = ", ".join(_fmt_socket(s) for s in d["in"]) or "—"
            outs = ", ".join(_fmt_socket(s) for s in d["out"]) or "—"
            rows.append([nm, ins, outs])
        if rows:
            lines.append(md_table(rows, ["节点", "输入", "输出"]))
            lines.append("")

    bad = nd.get("abstract", [])
    if bad:
        lines += ["## 不可实例化（%d）" % len(bad), "",
                  "这些类型 `nodes.new()` 会报 `Node type … undefined`，不是扫描失败——",
                  "它们是**基类 / node_tree 类型 / 自定义组 / 已删除节点**，本来就没有实例。", "",
                  md_table([[b["node"], b["reason"].replace("|", "/")] for b in bad],
                           ["节点", "nodes.new 报错"]),
                  ""]
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
        sum(len(v) for v in data["nodes"]["by_prefix"].values()),
        sum(len(v) for v in data["ops"].values())))
    md_ = data["modifiers"]
    print("[catalog] modifiers: %d types, %d with params, %d param rows"
          % (len(md_["types"]), len(md_.get("detail", {})),
             sum(v["n"] for v in md_.get("detail", {}).values())))
    nd_ = data["nodes"]
    print("[catalog] nodes: %d instantiable, %d abstract, %d sockets"
          % (len(nd_.get("detail", {})), len(nd_.get("abstract", [])),
             sum(len(v["in"]) + len(v["out"]) for v in nd_.get("detail", {}).values())))
    cm = data["render"].get("colormanagement", {})
    print("[catalog] view_transforms=%d looks=%d/%d (source=%s)"
          % (len(data["render"]["view_transforms"]), len(data["render"]["looks"]),
             len(cm.get("looks_all", [])), "ocio" if cm.get("source") else "none"))
    print("[catalog] look 按 view_transform 分组：%s"
          % {k: len(v) for k, v in cm.get("looks_by_view_transform", {}).items()})
    print("[catalog] out=%s" % OUT)


main()
