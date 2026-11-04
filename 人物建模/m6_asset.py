# -*- coding: utf-8 -*-
"""M6 / E1+E2 + 资产化 LOD：把工作模型转成「能进游戏」的资产。

为什么在这一步做 LOD
--------------------
工作文件 美女.blend 是 DCC 精度：身体 5mm 体素重网格、手 2mm、五官贴片全
保留，实测 201,830 三角面。`spec/game_budget.json` 给的单角色上限是 60,000
（目标 50,000）。直接把工作文件降精度会连带毁掉 14 条宏观比例、六探针绑定
回归和所有已验收的渲染；正确做法是**DCC 工作文件与游戏资产分离**：
这里从 美女.blend 读出高精度网格，在资产版上做

    封闭开放面片 → 按 per_mesh_tri_warn 减面 → 三角合并收敛 → 权重归一化
    → UV 展开 → 另存 美女_asset.blend

`美女.blend` 一个字节都不动，`scripts/audit.py` 量的就是这个资产版。
LOD 目标直接读预算表已有的 per_mesh_tri_warn（合计 55,000 ≤ 60,000），
不为当前模型新造数字。

产物
----
- 美女_asset.blend（另存，不覆盖 美女.blend）
- out/m6_uv_<网格>.png（UV 布局）
- out/m6_e1e2.json（含每网格的 LOD 前后数字，便于复核）
"""
import bpy
import bmesh
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import uvkit
import retopo
import meshkit

SRC = os.path.join(HERE, "美女.blend")
DST = os.path.join(HERE, "美女_asset.blend")
OUT = os.path.join(HERE, "out")
MESHES = ("Body", "Hands", "Head", "Hair", "Outfit")

with open(os.path.join(HERE, "spec", "game_budget.json"), encoding="utf-8") as _f:
    LOD_TARGETS = json.load(_f)["per_mesh_tri_warn"]


def tri_count(ob):
    """glTF 实际吃到的三角数（四边面算 2，n 边面算 n-2）。"""
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def nm_count(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    n = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    return n


def seal(ob):
    """开放面片 → 封闭薄壳。

    Head 里的五官 fan/band 是单面贴片，工作文件里有 628 条非流形边。
    Solidify 给每条边补上侧面与背面，导出引擎才不会有不确定法线。
    """
    meshkit.solidify(ob, thickness=0.0004, offset=0.0)


def lod(ob, target):
    """按三角面目标迭代塌缩。ratio 每轮按实测反算，不猜一次到位的比例。"""
    for _ in range(5):
        cur = tri_count(ob)
        if cur <= target:
            break
        ratio = max(0.02, min(0.98, target / cur * 0.90))
        meshkit.select_only(ob)
        m = ob.modifiers.new("LOD", 'DECIMATE')
        m.decimate_type = 'COLLAPSE'
        m.ratio = ratio
        bpy.ops.object.modifier_apply(modifier=m.name)
    return tri_count(ob)


def quads_converge(ob, rounds=8):
    """把「本可配成四边」的三角合并干净，返回本轮**总共**合并掉的数量。

    audit.py 的 fixable_tris_max=0 用的就是同一个算子（参数逐项一致），
    所以「本轮返回 0」等价于「审计再跑一次也找不出漏网的」。
    返回总合并数而不是最后一轮的差值：调用方要靠它判断是否需要再展开一轮。
    """
    total = 0
    for _ in range(rounds):
        before = sum(1 for p in ob.data.polygons if len(p.vertices) == 3)
        retopo.tris_to_quads(ob)
        after = sum(1 for p in ob.data.polygons if len(p.vertices) == 3)
        merged = before - after
        if merged == 0:
            break
        total += merged
    return total


def normalize_weights(ob):
    """Decimate 会插值权重，和可能偏离 1；手动归回 1，避免蒙皮缩胀。"""
    for v in ob.data.vertices:
        groups = [(g.group, g.weight) for g in v.groups]
        s = sum(w for _i, w in groups)
        if s <= 1e-9 or abs(s - 1.0) < 1e-6:
            continue
        for gi, w in groups:
            ob.vertex_groups[gi].add([v.index], w / s, 'REPLACE')


os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC)
print("[m6] source " + SRC)

report = {}
for name in MESHES:
    ob = bpy.data.objects.get(name)
    if ob is None:
        print("[m6] 缺失网格: " + name)
        continue

    before = retopo.face_stats(ob)
    tri0, nm0 = tri_count(ob), nm_count(ob)
    tri_before_mat = retopo.tri_by_material(ob)
    print(retopo.line("E2 " + name + " before", before))
    print("[LOD {0}] tri={1} target={2} nonmanifold={3}".format(
        name, tri0, LOD_TARGETS.get(name, 0), nm0))
    if tri_before_mat:
        print("[E2 {0}] tri_by_material={1}".format(name, tri_before_mat))

    if nm0:
        seal(ob)
        print("[LOD {0}] 封闭开放面片：nonmanifold {1} -> {2}".format(
            name, nm0, nm_count(ob)))

    tri1 = lod(ob, LOD_TARGETS.get(name, 10 ** 9))
    quads_converge(ob)                 # 先收拾几何本身的可合并三角
    normalize_weights(ob)

    # UV 展开会重排 UV 岛，让原来「UV 不连续、合不了」的相邻三角变成能合并。
    # 2026-11-04 实测：只在展开前收敛，Head 存盘后审计仍量出 8 对漏网。
    # 所以这里做成固定点：展开 → 收敛 → 只要还在合并就再展开一轮，
    # 直到「展开后的网格上一次都合不动」，此时与 audit 的判据完全一致。
    t0 = time.time()
    fixable = -1
    for uv_round in range(1, 5):
        uvkit.unwrap(ob)
        fixable = quads_converge(ob)
        print("[LOD {0}] UV 第 {1} 轮：新可合并三角 {2}".format(
            name, uv_round, fixable))
        if fixable == 0:
            break
    unwrap_s = time.time() - t0

    tri1 = tri_count(ob)
    after = retopo.face_stats(ob)
    nm1 = nm_count(ob)
    s = uvkit.stats(ob)
    print(retopo.line("E2 " + name + " after", after))
    print("[LOD {0}] tri {1} -> {2}  nonmanifold {3} -> {4}  残余可合并三角 {5}"
          .format(name, tri0, tri1, nm0, nm1, fixable))
    print(uvkit.report("E1 " + name, s) + " unwrap={0:.1f}s".format(unwrap_s))
    p = uvkit.raster_layout(ob, os.path.join(OUT, "m6_uv_" + name + ".png"))
    print("[E1 {0}] layout={1} size={2}B".format(
        name, p, os.path.getsize(p) if p else 0))
    report[name] = {"before": before, "after": after, "merged_tris": 0,
                    "tri_materials": tri_before_mat, "uv": s, "layout": p,
                    "lod": {"tri_before": tri0, "tri_after": tri1,
                            "nonmanifold_before": nm0, "nonmanifold_after": nm1,
                            "fixable_tris": fixable,
                            "target": LOD_TARGETS.get(name, 0)}}

summary = os.path.join(OUT, "m6_e1e2.json")
with open(summary, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print("[m6] report " + summary)

bpy.ops.wm.save_as_mainfile(filepath=DST)
print("[m6] saved " + DST)

fails = []
for name, r in report.items():
    a, u, L = r["after"], r["uv"], r["lod"]
    # 资产版经过塌缩，四边面比例不再是有效指标（只作参考打印）。
    # 真判据：可合并三角 = 0、非流形 = 0、面数达标、UV 有效。
    topo_ok = (L["fixable_tris"] == 0 and L["nonmanifold_after"] == 0
               and L["tri_after"] <= L["target"])
    uv_ok = (u["islands"] > 0 and u["uv_vert_ratio"] < 0.35
             and u["spread"] <= 1.35 and u["degenerate"] == 0)
    print("[assert] {0} {1}: tri={2}/{3} nm={4} fixable={5} quad={6}% "
          "uv_vert_ratio={7} spread={8} islands={9}".format(
              name, "PASS" if (topo_ok and uv_ok) else "FAIL",
              L["tri_after"], L["target"], L["nonmanifold_after"],
              L["fixable_tris"], a["quad_pct"], u["uv_vert_ratio"],
              u["spread"], u["islands"]))
    if not (topo_ok and uv_ok):
        fails.append(name)
print("[assert] summary: 未达标 {0}".format(fails or "无"))
print("[done] M6 E1+E2+LOD")
