# -*- coding: utf-8 -*-
"""游戏可用性审计：把「能不能进游戏」变成一组可判定的数字。

为什么要有它
------------
`measure.py` 判的是「像不像参考图」，`check.py` 判的是「绑定有没有坏」。
这两个都不回答「这东西能不能塞进游戏引擎」——面数、四边面比例、UV、蒙皮
权重、非流形边，没有任何一个入口在管。目标既然是「真进游戏用」，缺的正是这一层。

用法（在 `实用工具/Blender建模/人物建模/` 下）
---------------------------------------------
    python scripts/audit.py                  # 全量：glb 资产预算 + blend 结构预算
    python scripts/audit.py --fast           # 只查 glb（纯 Python，不启动 Blender，<1s）
    python scripts/audit.py --glb out/x.glb --blend 美女.blend

阈值全在 `spec/game_budget.json`，本文件不写死任何上限。改一行就能调松紧。

退出码：0 全过（可能有 warn）/ 1 有 must FAIL / 2 环境或输入不对。

实现说明
--------
单文件双模式：外层是系统 Python（解 glb、汇总判定），带 `--blender-side` 参数
启动时变成 Blender 内运行的探针（量 blend 的网格结构）。这样不用多维护一个文件，
也不会出现「探针和外层判据不同步」。
"""
import json
import os
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

sys.path.insert(0, HERE)
import bpyrun  # noqa: E402  D12：Blender 定位单源

MESHES = ("Body", "Hands", "Head", "Hair", "Outfit")
ROOT_BLEND = os.path.join(ROOT, "美女.blend")
# 结构审计要看**资产化之后**的文件：UV 是 m6_asset 阶段才展开的，
# 拿工作文件 美女.blend 去查 UV 必然全 FAIL，那是审错对象不是真缺陷。
ASSET_BLEND = os.path.join(ROOT, "美女_asset.blend")
DEFAULT_BLEND = ASSET_BLEND if os.path.exists(ASSET_BLEND) else ROOT_BLEND
DEFAULT_GLB = os.path.join(ROOT, "out", "美女.glb")
DEFAULT_BUDGET = os.path.join(ROOT, "spec", "game_budget.json")
OUT_DIR = os.path.join(ROOT, "out")


# ---------------------------------------------------------------- Blender 侧

def _count_mergeable(ob, deg=40.0):
    """能合并掉多少三角面：在**副本**上真跑一次 tris_convert_to_quads，原网格不动。

    为什么不用几何近似：先试过「相邻 + 法线夹角 ≤40°」，results 比算子多出一大截
    （Head 520 / Hair 626），因为算子还看四边形的形状与 UV/锐边/材质边界。
    近似会把「本来合不了的」算成缺陷，那比不查更糟 —— 判据必须和工程实际用的算子一致。
    """
    import bpy
    import math

    before = sum(1 for p in ob.data.polygons if len(p.vertices) == 3)
    if before == 0:
        return 0

    me_dup = ob.data.copy()
    dup = bpy.data.objects.new("__audit_merge_probe", me_dup)
    bpy.context.scene.collection.objects.link(dup)
    try:
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = dup
        dup.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.tris_convert_to_quads(
            face_threshold=math.radians(deg),
            shape_threshold=math.radians(deg),
            topology_influence=0.0,
            uvs=True, vcols=False, seam=True, sharp=True,
            materials=True, deselect_joined=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        after = sum(1 for p in me_dup.polygons if len(p.vertices) == 3)
    finally:
        bpy.data.objects.remove(dup, do_unlink=True)
        if me_dup.users == 0:
            bpy.data.meshes.remove(me_dup)
    return max(0, before - after)


def _measure_mesh(ob, tol):
    """单个网格的结构指标。"""
    import bmesh

    me = ob.data
    faces = len(me.polygons)
    quads = sum(1 for p in me.polygons if len(p.vertices) == 4)
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    ngons = sum(1 for p in me.polygons if len(p.vertices) > 4)

    bm = bmesh.new()
    bm.from_mesh(me)
    nonmanifold = sum(1 for e in bm.edges if not e.is_manifold)
    loose_v = sum(1 for v in bm.verts if not v.link_edges)
    bm.free()

    # 「可合并三角面」比「四边面百分比」有用：扇形贴片、发片尖端那类三角是
    # 结构固有的，永远合并不了，拿百分比当判据只会天天报假警。
    fixable_n = _count_mergeable(ob)

    # UV：只查「有没有」和「有没有跑到 0~1 之外」，重叠没做（见 budget 的 not_implemented）
    uv_names = [l.name for l in me.uv_layers]
    uv_oor = None
    if me.uv_layers:
        data = me.uv_layers[0].data
        n = len(data)
        step = max(1, n // 4000)          # 抽样，几万个 loop 全扫太慢且没必要
        bad = tot = 0
        for i in range(0, n, step):
            u, v = data[i].uv
            tot += 1
            if u < -1e-4 or u > 1 + 1e-4 or v < -1e-4 or v > 1 + 1e-4:
                bad += 1
        uv_oor = round(100.0 * bad / max(1, tot), 3)

    # 蒙皮：权重和 + 每顶点影响骨数
    bad_w = 0
    max_inf = 0
    for vtx in me.vertices:
        s = 0.0
        k = 0
        for g in vtx.groups:
            if g.weight > 1e-5:
                s += g.weight
                k += 1
        if abs(s - 1.0) > tol:
            bad_w += 1
        if k > max_inf:
            max_inf = k

    return {
        "verts": len(me.vertices),
        "faces": faces,
        "data_name": me.name,       # glb 里的网格名用的是数据块名（torso/head…），不是对象名
        "tris": tris,
        "quad_pct": round(100.0 * quads / faces, 1) if faces else 0.0,
        "ngons": ngons,
        "fixable_tris": fixable_n,
        "nonmanifold": nonmanifold,
        "loose_verts": loose_v,
        "uv_layers": uv_names,
        "uv_out_of_range_pct": uv_oor,
        "weightsum_bad": bad_w,
        "max_influences": max_inf,
        "vgroups": len(ob.vertex_groups),
        "materials": len([m for m in me.materials if m]),
        "armature_mod": any(m.type == "ARMATURE" for m in ob.modifiers),
        "solidify": any(m.type == "SOLIDIFY" for m in ob.modifiers),
        "modifiers": [m.type for m in ob.modifiers],
    }


def blender_side(out_path):
    """在已加载的 blend 里量结构，写一份 JSON 给外层。"""
    import bpy

    tol = 0.001
    data = {"meshes": {}, "bones": 0, "objects_extra": []}
    for ob in bpy.data.objects:
        if ob.type == "ARMATURE":
            data["bones"] = max(data["bones"], len(ob.data.bones))
        elif ob.type == "MESH":
            if ob.name in MESHES:
                data["meshes"][ob.name] = _measure_mesh(ob, tol)
            else:
                data["objects_extra"].append(
                    {"name": ob.name, "faces": len(ob.data.polygons)})
    data["file"] = bpy.data.filepath
    data["blender"] = bpy.app.version_string
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("[audit-probe] wrote " + out_path)
    return 0


# ---------------------------------------------------------------- 外层：glb

def _read_vec4(js, blob, acc_index):
    """把 VEC4 浮点 accessor 读成元组列表。非 float 分量返回 None。"""
    acc = js["accessors"][acc_index]
    if acc.get("componentType") != 5126 or acc.get("type") != "VEC4":
        return None
    bv = js["bufferViews"][acc["bufferView"]]
    base = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = bv.get("byteStride") or 16
    return [struct.unpack_from("<4f", blob, base + i * stride)
            for i in range(acc["count"])]


def parse_glb(path):
    """纯 Python 解 glb（不 import bpy）：面数、属性、材质、贴图、骨骼、权重和。"""
    with open(path, "rb") as f:
        raw = f.read()
    magic, ver, total = struct.unpack("<III", raw[:12])
    if magic != 0x46546C67:
        raise ValueError("不是 glb：%s" % path)
    off, js, blob = 12, None, b""
    while off < total:
        ln, ty = struct.unpack("<II", raw[off:off + 8])
        off += 8
        if ty == 0x4E4F534A:                 # JSON
            js = json.loads(raw[off:off + ln].decode("utf-8"))
        elif ty == 0x004E4942:               # BIN
            blob = raw[off:off + ln]
        off += ln
    if js is None:
        raise ValueError("glb 缺少 JSON chunk：%s" % path)

    acc = js.get("accessors", [])
    meshes = []
    tot_tri = 0
    for m in js.get("meshes", []):
        tri = 0
        attrs = set()
        bad_w = 0       # 权重和偏离 1 的顶点数（引擎真正吃到的值）
        checked_w = 0
        unverifiable = False
        for pr in m.get("primitives", []):
            attrs |= set(pr.get("attributes", {}).keys())
            if "indices" in pr:
                tri += acc[pr["indices"]]["count"] // 3
            wi = pr.get("attributes", {}).get("WEIGHTS_0")
            if wi is not None:
                vs = _read_vec4(js, blob, wi)
                if vs is None:
                    unverifiable = True
                else:
                    for q in vs:
                        checked_w += 1
                        if abs(sum(q) - 1.0) > 0.01:
                            bad_w += 1
        tot_tri += tri
        meshes.append({"name": m.get("name", ""), "tri": tri,
                       "primitives": len(m.get("primitives", [])),
                       "attrs": sorted(attrs),
                       "weightsum_bad": bad_w,
                       "weightsum_checked": checked_w,
                       "weightsum_unverifiable": unverifiable})
    return {
        "bytes": len(raw),
        "mb": round(len(raw) / 1048576.0, 2),
        "gltf_version": ver,
        "generator": js.get("asset", {}).get("generator", ""),
        "meshes": meshes,
        "tri_total": tot_tri,
        "materials": len(js.get("materials", [])),
        "images": len(js.get("images", [])),
        "skins": len(js.get("skins", [])),
        "joints": [len(s.get("joints", [])) for s in js.get("skins", [])],
        "nodes": len(js.get("nodes", [])),
    }


# ---------------------------------------------------------------- 判定

def _mk(cid, label, value, target, level, ok, why="", unit=""):
    return {"id": cid, "label": label, "value": value, "target": target,
            "unit": unit, "level": level,
            "status": "PASS" if ok else ("FAIL" if level == "must" else "WARN"),
            "why": why}


def judge(budget, glb, st, paths=None):
    """把实测值与预算表比对，返回 checks 列表。"""
    a = budget["asset"]
    s = budget["structure"]
    paths = paths or {}
    out = []

    # 产物新鲜度：拿旧 glb 判「能进游戏」比不判更糟，所以这项放在最前面。
    root = paths.get("root")
    asset = paths.get("asset")
    glb_p = paths.get("glb")
    stale = []
    try:
        if root and asset and os.path.exists(root) and os.path.exists(asset):
            if os.path.getmtime(asset) < os.path.getmtime(root) - 1:
                stale.append("资产文件比工作文件旧，跑 m6_asset.py 重新 UV 展开")
        if asset and glb_p and os.path.exists(asset) and os.path.exists(glb_p):
            if os.path.getmtime(glb_p) < os.path.getmtime(asset) - 1:
                stale.append("glb 比资产文件旧，跑 m6_export.py 重新导出")
    except OSError:
        pass
    out.append(_mk("fresh", "产物新鲜度",
                   "落后" if stale else "最新", "与源文件同步", "must",
                   not stale, "；".join(stale) or "blend → asset → glb 时间戳递进"))

    def num(sec, key):
        """取一项阈值。有的项只有 target（越小越好）、有的只有 max（上限），
        缺哪个就用另一个顶上 —— 免得改预算表时踩 KeyError。"""
        d = sec[key]
        t = d.get("target", d.get("max"))
        m = d.get("max", d.get("target"))
        return t, m, d.get("level", "must"), d.get("unit", ""), d.get("why", "")

    # ---- 资产级 ----
    _, t_max, t_lv, t_u, t_why = num(a, "tri_total")
    out.append(_mk("tri_total", "总三角面", glb["tri_total"], "≤%d" % t_max,
                   t_lv, glb["tri_total"] <= t_max, t_why, t_u))

    _, t_max, t_lv, t_u, t_why = num(a, "glb_mb")
    out.append(_mk("glb_mb", "glb 体积", glb["mb"], "≤%.1f" % t_max,
                   t_lv, glb["mb"] <= t_max, t_why, t_u))

    _, t_max, t_lv, t_u, t_why = num(a, "materials")
    out.append(_mk("materials", "材质数", glb["materials"], "≤%d" % t_max,
                   t_lv, glb["materials"] <= t_max, t_why, t_u))

    _, t_max, t_lv, t_u, t_why = num(a, "images")
    out.append(_mk("images", "贴图数", glb["images"], "≤%d" % t_max,
                   t_lv, glb["images"] <= t_max, t_why, t_u))

    t_target, _, t_lv, t_u, t_why = num(a, "joints")
    joints = max(glb["joints"]) if glb["joints"] else 0
    ok_j = (glb["skins"] == 1 and joints == t_target)
    out.append(_mk("joints", "骨骼数", "%d（skins=%d）" % (joints, glb["skins"]),
                   "=%d" % t_target, t_lv, ok_j, t_why, t_u))

    # 每个 primitive 必须齐 5 组属性，缺一就是进不了引擎
    need = {"POSITION", "NORMAL", "TEXCOORD_0", "JOINTS_0", "WEIGHTS_0"}
    for m in glb["meshes"]:
        miss = need - set(m["attrs"])
        out.append(_mk("attr:" + m["name"], "%s 顶点属性" % m["name"],
                       "缺 " + ",".join(sorted(miss)) if miss else "齐全",
                       "5 组齐全", "must", not miss,
                       "缺 TEXCOORD_0 没贴图，缺 JOINTS_0/WEIGHTS_0 蒙皮失效"))

    # glb 里的权重和 —— 引擎真正拿到的就是这份，比 blend 里量的更算数
    for m in glb["meshes"]:
        if m["weightsum_unverifiable"]:
            out.append(_mk("gwsum:" + m["name"], "%s glb 权重和" % m["name"],
                           "无法校验", "=0 偏离", "warn", True,
                           "WEIGHTS_0 不是 float VEC4（量化存储），本脚本不解"))
        elif m["weightsum_checked"]:
            out.append(_mk("gwsum:" + m["name"], "%s glb 权重和" % m["name"],
                           "%d/%d 顶点偏离" % (m["weightsum_bad"], m["weightsum_checked"]),
                           "=0", "must", m["weightsum_bad"] == 0,
                           "导出器会归一化；这里不为 0 说明引擎侧形变会偏"))

    # ---- 结构级 ----
    q_target, _, q_lv, q_u, q_why = num(s, "quad_pct_min")
    fx_target, fx_max, fx_lv, fx_u, fx_why = num(s, "fixable_tris_max")
    nm_target, nm_max, nm_lv, nm_u, nm_why = num(s, "nonmanifold_max")
    ws_tol = s["weightsum_tol"]["target"]
    mi_target, mi_max, mi_lv, mi_u, mi_why = num(s, "max_influences")
    uv_oor_max = s["uv_out_of_range_max"]["target"]

    for name in MESHES:
        m = st["meshes"].get(name)
        if m is None:
            out.append(_mk("mesh:" + name, name + " 存在", "缺失", "存在",
                           "must", False, "五个主网格缺一不可"))
            continue
        out.append(_mk("fix:" + name, "%s 可合并三角面" % name,
                       m["fixable_tris"], "=%d" % fx_max, fx_lv,
                       m["fixable_tris"] <= fx_max, fx_why, fx_u))
        out.append(_mk("quad:" + name, "%s 四边面" % name,
                       "%.1f%%" % m["quad_pct"], "≥%.0f%%" % q_target,
                       q_lv, m["quad_pct"] >= q_target, q_why, q_u))
        out.append(_mk("nm:" + name, "%s 非流形边" % name, m["nonmanifold"],
                       "≤%d" % nm_max, nm_lv, m["nonmanifold"] <= nm_max,
                       nm_why, nm_u))
        out.append(_mk("uv:" + name, "%s UV 层" % name,
                       ",".join(m["uv_layers"]) or "无", "≥1 层",
                       "must", bool(m["uv_layers"]),
                       s["uv_required"]["why"]))
        if m["uv_layers"]:
            out.append(_mk("uvoor:" + name, "%s UV 越界" % name,
                           "%.2f%%" % m["uv_out_of_range_pct"],
                           "≤%.1f%%" % uv_oor_max, "warn",
                           m["uv_out_of_range_pct"] <= uv_oor_max,
                           s["uv_out_of_range_max"]["why"], "%"))
        out.append(_mk("wsum:" + name, "%s 权重和" % name,
                       "%d 个顶点偏离" % m["weightsum_bad"], "=0",
                       "must", m["weightsum_bad"] == 0,
                       "权重和 ≠1 蒙皮会缩/胀（容差 %.3f）" % ws_tol))
        out.append(_mk("inf:" + name, "%s 每顶点最多骨" % name,
                       m["max_influences"], "≤%d" % mi_max,
                       mi_lv, m["max_influences"] <= mi_max, mi_why, mi_u))

    # ---- 每条网格的三角面（定位面数花在哪）----
    warn_map = budget.get("per_mesh_tri_warn", {})
    alias = {mm.get("data_name"): k for k, mm in st.get("meshes", {}).items()
             if mm.get("data_name")}
    for m in glb["meshes"]:
        logical = alias.get(m["name"], m["name"])
        w = warn_map.get(logical)
        if w is None:
            continue
        out.append(_mk("tri:" + logical,
                       "%s 三角面（glb 名 %s）" % (logical, m["name"]),
                       m["tri"], "≤%d" % w, "warn", m["tri"] <= w,
                       "单项超预算时优先减这里", "tri"))
    return out


# ---------------------------------------------------------------- 输出

def print_table(checks):
    print("%-6s %-26s %-16s %-12s %s"
          % ("状态", "检查项", "实测", "要求", "说明"))
    print("-" * 104)
    for c in checks:
        print("%-6s %-26s %-16s %-12s %s"
              % (c["status"], c["label"][:26], str(c["value"])[:16],
                 str(c["target"])[:12], (c["why"] or "")[:44]))


def write_report(checks, glb, st, budget, path, glb_path):
    n = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for c in checks:
        n[c["status"]] += 1
    lines = [
        "# 游戏可用性审计",
        "",
        "| 项 | 值 |",
        "|---|---|",
        "| 生成时间 | %s |" % time.strftime("%Y-%m-%d %H:%M:%S"),
        "| blend | `%s` |" % st.get("file", "?"),
        "| glb | `%s`（%.2f MB）|" % (glb_path, glb["mb"]),
        "| Blender | %s |" % st.get("blender", "?"),
        "| 判定 | **PASS %d / WARN %d / FAIL %d** |" % (n["PASS"], n["WARN"], n["FAIL"]),
        "",
        "阈值来源：`spec/game_budget.json`，脚本不写死数字。",
        "",
        "## 结论",
        "",
    ]
    fails = [c for c in checks if c["status"] == "FAIL"]
    warns = [c for c in checks if c["status"] == "WARN"]
    if fails:
        lines.append("**不能进游戏**，%d 项硬指标不达标：" % len(fails))
        lines.append("")
        for c in fails:
            lines.append("- **%s**：实测 %s，要求 %s —— %s"
                         % (c["label"], c["value"], c["target"], c["why"]))
    elif warns:
        lines.append("硬指标全过，%d 项超预算（可接受但值得记）：" % len(warns))
        lines.append("")
        for c in warns:
            lines.append("- %s：实测 %s，建议 %s" % (c["label"], c["value"], c["target"]))
    else:
        lines.append("全部达标。")
    lines += ["", "## 面数分布", "",
              "| 网格 | 三角面 | 占比 | 单项预算 |",
              "|---|---|---|---|"]
    alias = {mm.get("data_name"): k for k, mm in st.get("meshes", {}).items()
             if mm.get("data_name")}
    for m in sorted(glb["meshes"], key=lambda x: -x["tri"]):
        logical = alias.get(m["name"], m["name"])
        w = budget.get("per_mesh_tri_warn", {}).get(logical)
        lines.append("| %s（%s） | %d | %.1f%% | %s |"
                     % (logical, m["name"], m["tri"],
                        100.0 * m["tri"] / max(1, glb["tri_total"]),
                        ("≤%d%s" % (w, "" if m["tri"] <= w else " **超**")) if w else "—"))
    lines += ["", "## 全部检查项", "",
              "| 状态 | 检查项 | 实测 | 要求 | 说明 |", "|---|---|---|---|---|"]
    for c in checks:
        lines.append("| %s | %s | %s | %s | %s |"
                     % (c["status"], c["label"], c["value"], c["target"],
                        c["why"] or ""))
    lines += ["", "## 本审计**没有**覆盖的项", "",
              "写在这里是为了不让人误以为「全绿＝能上线」。", ""]
    for x in budget.get("not_implemented", []):
        lines.append("- " + x)
    lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return n


# ---------------------------------------------------------------- 主流程

def main(argv):
    if "--blender-side" in argv:
        i = argv.index("--blender-side")
        return blender_side(argv[i + 1])

    bpyrun.utf8_stdio()
    blend = DEFAULT_BLEND
    glb_path = DEFAULT_GLB
    budget_path = DEFAULT_BUDGET
    fast = "--fast" in argv

    for i, a in enumerate(argv):
        if a == "--blend" and i + 1 < len(argv):
            blend = argv[i + 1]
        elif a == "--glb" and i + 1 < len(argv):
            glb_path = argv[i + 1]
        elif a == "--budget" and i + 1 < len(argv):
            budget_path = argv[i + 1]

    if not os.path.exists(budget_path):
        print("[audit] 缺少预算表：%s" % budget_path, file=sys.stderr)
        return 2
    with open(budget_path, encoding="utf-8") as f:
        budget = json.load(f)

    if not os.path.exists(glb_path):
        print("[audit] 缺少 glb：%s\n        先跑 python scripts/build.py all 或 m6_export" % glb_path,
              file=sys.stderr)
        return 2
    glb = parse_glb(glb_path)

    # 结构：要么调 Blender 现量，要么用上次的缓存（--fast）
    struct_path = os.path.join(OUT_DIR, "audit_structure.json")
    st = None
    if fast and os.path.exists(struct_path):
        with open(struct_path, encoding="utf-8") as f:
            st = json.load(f)
        print("[audit] 结构数据取自缓存 %s" % struct_path)
    else:
        if not os.path.exists(blend):
            print("[audit] 缺少 blend：%s（可加 --fast 只看 glb）" % blend,
                  file=sys.stderr)
            return 2
        exe = bpyrun.blender_exe()
        if exe is None:
            return 2
        os.makedirs(OUT_DIR, exist_ok=True)
        print("[audit] 结构对象 %s" % os.path.basename(blend))
        t0 = time.time()
        cmd = [exe, "--factory-startup", "-b", blend,
               "--python", os.path.abspath(__file__),
               "--", "--blender-side", struct_path]
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0 or not os.path.exists(struct_path):
            print("[audit] Blender 侧失败（exit=%d）" % r.returncode, file=sys.stderr)
            print((r.stdout or "")[-1200:], file=sys.stderr)
            print((r.stderr or "")[-1200:], file=sys.stderr)
            return 2
        with open(struct_path, encoding="utf-8") as f:
            st = json.load(f)
        print("[audit] 结构测量 %.1fs" % (time.time() - t0))

    checks = judge(budget, glb, st,
                   {"root": ROOT_BLEND, "asset": blend, "glb": glb_path})
    print()
    print_table(checks)
    os.makedirs(OUT_DIR, exist_ok=True)
    n = write_report(checks, glb, st, budget,
                     os.path.join(OUT_DIR, "audit_report.md"), glb_path)
    payload = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"),
               "glb": glb, "structure": st, "counts": n,
               "checks": checks,
               "not_implemented": budget.get("not_implemented", [])}
    with open(os.path.join(OUT_DIR, "audit.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print()
    print("[audit] PASS %d / WARN %d / FAIL %d"
          % (n["PASS"], n["WARN"], n["FAIL"]))
    print("[audit] 报告 out/audit_report.md   数据 out/audit.json")
    return 0 if n["FAIL"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
