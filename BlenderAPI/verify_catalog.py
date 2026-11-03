# -*- coding: utf-8 -*-
"""核对 catalog/ 产物（不依赖 bpy，系统 Python 就能跑）。

    python verify_catalog.py

和 gen_catalog.py 的分工：那个负责**生成**，这个负责**挑错**。
判据全部可判定：数值相等、条数下限、字符串存在、反引号配对。
任何一项不过就以非 0 退出。

为什么要单独一份：`gen_catalog.py` 正常退出只说明「没抛异常」，
不说明「扫到的东西是对的」。本文件用另一条路径（读产物文件）复核。

可选的回归对比：如果存在 `catalog_bak/`（上一版产物），额外核对
「未改动的分域应逐字节相同」，用来发现扫描逻辑的意外副作用。
"""
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CAT = os.path.join(HERE, "catalog")
BAK = os.path.join(HERE, "catalog_bak")

fails = []
oks = 0


def check(name, ok, detail=""):
    global oks
    print(("  OK   " if ok else "  FAIL ") + name + ("  " + detail if detail else ""))
    if ok:
        oks += 1
    else:
        fails.append(name)


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def rj(name):
    return json.load(io.open(os.path.join(CAT, name), encoding="utf-8"))


def rt(name):
    return io.open(os.path.join(CAT, name), encoding="utf-8").read()


print("=== 1. 产物完整性 ===")
need = ["index.md", "01_env.md", "02_types.md", "03_modifiers.md",
        "04_bmesh.md", "05_nodes.md", "06_ops.md", "07_gltf.md", "api.json"]
missing = [f for f in need if not os.path.exists(os.path.join(CAT, f))]
check("9 个产物齐全", not missing, "缺 %s" % missing if missing else "api.json %d B"
      % os.path.getsize(os.path.join(CAT, "api.json")))
if missing:
    print("\n产物不全，后续检查跳过")
    sys.exit(1)

api = rj("api.json")

print()
print("=== 2. 回归：未改动的分域应逐字节不变 ===")
if os.path.isdir(BAK):
    for f in ("02_types.md", "04_bmesh.md", "06_ops.md", "07_gltf.md"):
        p = os.path.join(BAK, f)
        if not os.path.exists(p):
            check("%s 基线缺失" % f, False)
            continue
        same = md5(p) == md5(os.path.join(CAT, f))
        check("%s 未被意外改动" % f, same)
    old = json.load(io.open(os.path.join(BAK, "api.json"), encoding="utf-8"))
    check("核心类型条数一致",
          all(len(api["types"][k]) == len(old["types"][k]) for k in old["types"]),
          "%d 类" % len(api["types"]))
    check("ops 条数一致",
          sum(len(v) for v in api["ops"].values()) == sum(len(v) for v in old["ops"].values()),
          "%d 条" % sum(len(v) for v in api["ops"].values()))
    check("bmesh 条数一致", len(api["bmesh_ops"]) == len(old["bmesh_ops"]),
          "%d 条" % len(api["bmesh_ops"]))
else:
    print("  SKIP  没有 catalog_bak/，跳过回归对比（想比就先备份一份旧产物）")

print()
print("=== 3. 修改器参数 ===")
m = api["modifiers"]
check("83 类全部扫到", len(m["detail"]) == len(m["types"]) == 83,
      "%d/%d，失败 %d" % (len(m["detail"]), len(m["types"]), len(m["unsupported"])))
rows = sum(v["n"] for v in m["detail"].values())
check("参数条数 > 1000", rows > 1000, "%d 条" % rows)
sol = {p["id"]: p for p in m["detail"]["SOLIDIFY"]["props"]}
for k, want in (("thickness", 0.01), ("offset", -1.0), ("use_rim", True)):
    got = sol.get(k, {}).get("default")
    check("SOLIDIFY.%s 默认值 = %r" % (k, want), got == want, "实际 %r" % (got,))
boo = {p["id"] for p in m["detail"]["BOOLEAN"]["props"]}
check("BOOLEAN 含 operation/operand_type/solver",
      {"operation", "operand_type", "solver"} <= boo, "共 %d 条" % len(boo))
check("基类通用属性已剔除",
      not ({"show_viewport", "persistent_uid", "rna_type"} & set(sol)),
      "SOLIDIFY 剩 %d 条特有参数" % len(sol))
check("枚举型参数带取值列表",
      all(p.get("enum") for p in m["detail"]["SOLIDIFY"]["props"] if p["type"] == "ENUM"))

print()
print("=== 4. 节点端口 ===")
nd = api["nodes"]
check("540 可实例化 + 22 不可", len(nd["detail"]) == 540 and len(nd["abstract"]) == 22,
      "%d / %d" % (len(nd["detail"]), len(nd["abstract"])))
sockets = sum(len(v["in"]) + len(v["out"]) for v in nd["detail"].values())
check("socket 总数 > 2000", sockets > 2000, "%d 个" % sockets)
pr = nd["detail"]["ShaderNodeBsdfPrincipled"]
check("Principled 32 输入 / 1 输出", len(pr["in"]) == 32 and len(pr["out"]) == 1,
      "%d / %d" % (len(pr["in"]), len(pr["out"])))
names = [s[0] for s in pr["in"]]
check("端口名带空格（'Base Color' 而非 base_color）", "Base Color" in names, str(names[:4]))
check("端口默认值已记录", pr["in"][0][2] == [0.8, 0.8, 0.8, 1.0], str(pr["in"][0]))
check("compositor 树已接上",
      any(v["tree"] == "compositor" for v in nd["detail"].values()),
      "%d 个合成节点" % sum(1 for v in nd["detail"].values() if v["tree"] == "compositor"))
check("geometry 树已接上",
      any(v["tree"] == "geometry" for v in nd["detail"].values()),
      "%d 个几何节点" % sum(1 for v in nd["detail"].values() if v["tree"] == "geometry"))
abstracts = {a["node"] for a in nd["abstract"]}
check("abstract 含基类与 node_tree 类型",
      {"ShaderNode", "ShaderNodeTree", "CompositorNodeTree"} <= abstracts,
      "%d 个" % len(abstracts))

print()
print("=== 5. 色彩管理 ===")
r = api["render"]
cm = r["colormanagement"]
check("view_transform 不再是占位 ['NONE']",
      len(r["view_transforms"]) >= 5 and r["view_transforms"] != ["NONE"],
      "%d 个: %s" % (len(r["view_transforms"]), r["view_transforms"][:5]))
check("含 Standard / AgX / Filmic / Raw",
      {"Standard", "AgX", "Filmic", "Raw"} <= set(r["view_transforms"]))
check("look 全量 27、当前可用 9",
      len(cm["looks_all"]) == 27 and len(r["looks"]) == 9,
      "%d / %d" % (len(cm["looks_all"]), len(r["looks"])))
bvt = cm["looks_by_view_transform"]
check("look 分组覆盖所有 view_transform", len(bvt) == len(r["view_transforms"]),
      str({k: len(v) for k, v in bvt.items()}))
check("AgX 组是 AgX 系列、Filmic 组是 Filmic 系列",
      any(x.startswith("AgX - ") for x in bvt.get("AgX", []))
      and "Very High Contrast" in bvt.get("Filmic", []))
check("OCIO 来源已记录", bool(cm.get("source")), cm.get("source", ""))

print()
print("=== 6. Markdown 可读性 ===")
for f in ("01_env.md", "03_modifiers.md", "05_nodes.md", "index.md"):
    s = rt(f)
    check("%s 反引号成对" % f, s.count("`") % 2 == 0, "%d 个" % s.count("`"))
    check("%s 无空标题" % f, "## \n" not in s and "### \n" not in s)

env = rt("01_env.md")
check("01_env 有 look 分组表", "| view_transform | 可用 look 数 |" in env)
check("01_env 警告「不要读 RNA 枚举」", "不要读 RNA 枚举" in env)

mod = rt("03_modifiers.md")
check("03_modifiers 有 SOLIDIFY 参数表", "### SOLIDIFY（" in mod)
check("float 全域噪声已过滤", "-3.4028234663852886e+38" not in mod)
check("03_modifiers 指出参数不在 ops 里", "不在 `bpy.ops` 里" in mod)

nodes = rt("05_nodes.md")
check("05_nodes 有 Principled 端口行", "| ShaderNodeBsdfPrincipled |" in nodes)
check("05_nodes 有「不可实例化」一节", "## 不可实例化" in nodes)
check("05_nodes 里 Base Color 可见", "`Base Color:RGBA`" in nodes)

idx = rt("index.md")
check("index 统计含「参数已扫」", "参数已扫" in idx)
check("index 统计含「端口已扫」", "端口已扫" in idx)

print()
print("=" * 56)
print("通过 %d 项" % oks)
if fails:
    print("FAIL %d 项：" % len(fails))
    for f in fails:
        print("   -", f)
    print("=" * 56)
    sys.exit(1)
print("全部通过")
print("=" * 56)
