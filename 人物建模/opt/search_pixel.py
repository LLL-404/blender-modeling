# -*- coding: utf-8 -*-
"""opt/search_pixel.py —— 像素段搜索主循环（复用 T17 的 Halton + top-k 坐标下降）。

算法（与几何段同一套，只换了参数空间与评估器）：
**Halton 采样 n 点 → 按 score 取 top-k → 每个 top 点做 rounds 轮逐维邻域试探 → 全局最优。**
差异只有两处：
  * **预算硬上限**（默认 24 次评估）：每次要 evaluate 前先查预算，超了就停，
    没试到的维度如实写进 `skipped_dims`，不编造；
  * **枚举维**（`rim_azimuth`）不做 ±1 step，而是在 top 点上把 4 个方位**全枚举**一遍。

写入纪律（**读-改-写**，绝不覆盖几何段）：
    读 opt/best.json → 只替换/新增 `pixel` 段 → 原样写回。
    顶层 `best_params`（几何 5 维）、`baseline_*` 等**一个字节都不动**。
    写回后 `lib/optio.py` 的查找顺序是 pixel → 顶层 → default。

用法（工作目录 人物建模/）：
    blender -b --factory-startup --python opt/search_pixel.py -- --n 2     # 冒烟
    blender -b --factory-startup --python opt/search_pixel.py -- --n 16    # 全量
"""
import argparse
import datetime
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, ROOT, os.path.join(ROOT, "lib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import space_pixel        # noqa: E402
import eval_pixel         # noqa: E402

BEST_PATH = os.path.join(HERE, "best.json")
TRIALS_PATH = os.path.join(HERE, "trials_pixel.jsonl")

# 受控对照表（**实测回填**，不是估计值）：固定其余五维，只变一个维。
# 6 次定点评估的命令（--no-write，原始回显在 opt/logs/px_table.log，该目录被 gitignore）：
#   blender -b --factory-startup --python opt/eval_pixel.py -- \
#       --params '{"key_energy":55.0,"skin_pos_mid":0.68,"skin_pos_light":0.70,
#                  "rim_azimuth":"back_left","outline_px":2.0,"rim_energy":240.0}' --no-write
# 为什么需要它：24 次 Halton 点各维同时变化，按 outline_px 分组取中位只是平均混杂项，
# 不能回答「描边宽度 → rim 亮带」——那必须控制变量。
CONTROLLED_TABLE = {
    "note": "6 次定点评估（不在 24 次搜索预算内）；固定其余五维，只变 outline_px 或 rim_energy",
    "source": "opt/logs/px_table.log",
    "fixed": {"key_energy": 55.0, "skin_pos_mid": 0.68,
              "skin_pos_light": 0.70, "rim_azimuth": "back_left"},
    # 描边宽度三档（rim_energy 固定 240W）
    "by_outline_px": {
        "2.0": {"rim_energy": 240.0, "outline_p50": 1.0, "rim_band_px": 5.0,
                "skin_p50": 195.94, "skin_p95_m50": 33.79, "skin_p50_m5": 27.75,
                "skin_ge228_pct": 16.30, "hard": 1},
        "3.0": {"rim_energy": 240.0, "outline_p50": 2.0, "rim_band_px": 6.0,
                "skin_p50": 195.94, "skin_p95_m50": 33.79, "skin_p50_m5": 27.75,
                "skin_ge228_pct": 16.24, "hard": 0},
        "4.5": {"rim_energy": 240.0, "outline_p50": 3.0, "rim_band_px": 9.0,
                "skin_p50": 195.94, "skin_p95_m50": 33.79, "skin_p50_m5": 27.75,
                "skin_ge228_pct": 16.34, "hard": 0},
    },
    # rim 强度梯度（outline_px 固定 4.5）
    "by_rim_energy_at_outline_4_5": {
        "80": {"outline_p50": 4.0, "rim_band_px": 9.0, "hard": 0},
        "160": {"outline_p50": 3.0, "rim_band_px": 9.0, "hard": 0},
        "240": {"outline_p50": 3.0, "rim_band_px": 9.0, "hard": 0},
        "320": {"outline_p50": 3.0, "rim_band_px": 9.0, "hard": 0},
        "400": {"outline_p50": 3.0, "rim_band_px": 9.0, "hard": 0},
    },
}

# 维度试探顺序：先试与「轮廓光判定」直接相关的连续维，再试皮肤色阶两维。
# 预算只有 24 次，这个顺序保证不会把预算花在「已经不达标但影响很小」的维上。
# `rim_azimuth` **不在**这里 —— 它是枚举维，按任务书「只做全枚举、不参与 ±1 坐标下降」，
# 在 Halton 之后对默认参数做一次 4 方位全枚举（见 main 的 enum sweep）。
DIM_ORDER = ["rim_energy", "outline_px",
             "key_energy", "skin_pos_light", "skin_pos_mid"]


def _key(params):
    return json.dumps(params, sort_keys=True, ensure_ascii=False)


def candidates(p, d):
    """某维的邻域候选：枚举维 → 除当前值外全枚举；连续维 → ±1 step（夹紧后同值则跳过）。"""
    k = d["key"]
    out = []
    if "choices" in d:
        for v in d["choices"]:
            if v != p[k]:
                q = space_pixel.fixup({**p, k: v})
                if q != p:
                    out.append(q)
        return out
    for delta in (1, -1):
        v = space_pixel.snap(d, p[k] + delta * d["step"])
        if v != p[k]:
            q = space_pixel.fixup({**p, k: v})
            if q != p and q not in out:
                out.append(q)
    return out


def read_best():
    try:
        with open(BEST_PATH, "r", encoding="utf-8") as f:
            doc = json.load(f)
        return doc if isinstance(doc, dict) else {}
    except Exception:
        return {}


def write_best(pixel_doc):
    """读-改-写：只替换 pixel 段，其它段原样保留。"""
    doc = read_best()
    before_keys = sorted(doc.keys())
    doc["pixel"] = pixel_doc
    with open(BEST_PATH, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    return before_keys, sorted(doc.keys())



def dim_stats(recs):
    """每维的一阶敏感性 + 唯一值数自检（证明采样没塌缩到参数盒一角）。

    `uniq` 是该维在本轮实际测到的不同取值个数 —— 这是「归一化坐标 vs 实际值
    两个函数」那条陷阱的验收方式：若 uniq=1（整维都吸到同一角），说明 from_unit
    被当成了 snap 用。`rim_max/edge_med/skin_med` 是**混杂**分组统计（其它维仍在
    变），只能看作一阶指示，不能当控制变量结论。
    """
    out = {}
    for d in space_pixel.DIMS:
        k = d["key"]
        g = {}
        for r in recs:
            v = str(r["params"].get(k))
            e = g.setdefault(v, {"n": 0, "rim": [], "edge": [], "skin": []})
            e["n"] += 1
            e["rim"].append(r["metrics"].get("rim_band_px") or 0.0)
            if r["metrics"].get("outline_p50") is not None:
                e["edge"].append(r["metrics"]["outline_p50"])
            if r["metrics"].get("skin_p50") is not None:
                e["skin"].append(r["metrics"]["skin_p50"])
        med = lambda xs: (round(sorted(xs)[len(xs) // 2], 3) if xs else None)
        out[k] = {"uniq": len(g), "values": {
            v: {"n": e["n"], "rim_max": round(max(e["rim"]), 2),
                "edge_p50_med": med(e["edge"]), "skin_p50_med": med(e["skin"])}
            for v, e in sorted(g.items())}}
    return out


def rim_candidate(recs):
    """在没有硬违规的各组里取 rim 亮带最大的一组，作为「轮廓光候选交付」。

    为什么单独给候选而不是直接换 best：rim 只是软目标（1e-6 量级的差异级），
    硬约束 5 条已经把最优锁在默认参数附近；换候选会牺牲皮肤 p50（见 REPORT）。
    """
    ok = [r for r in recs if r["metrics"] and r["hard"] == 0]
    if not ok:
        return None
    ok.sort(key=lambda r: (-(r["metrics"].get("rim_band_px") or 0.0), r["score"]))
    r = ok[0]
    return {"params": r["params"], "metrics": r["metrics"],
            "score": r["score"], "label": r["label"],
            "rim_band_px": r["metrics"].get("rim_band_px"),
            "hard": r["hard"]}


def outline_table(recs):
    """描边宽度 → rim 亮带 对照表（按 outline_px 分组，取该组 rim_band_px 的最大/中位与最优 score）。"""
    groups = {}
    for r in recs:
        if not r.get("metrics"):
            continue
        o = r["params"].get("outline_px")
        if o is None:
            continue
        g = groups.setdefault(round(float(o), 2), {"rim": [], "score": [], "p50": [],
                                                   "n": 0})
        g["n"] += 1
        g["rim"].append(r["metrics"].get("rim_band_px") or 0.0)
        g["score"].append(r["score"])
        if r["metrics"].get("outline_p50") is not None:
            g["p50"].append(r["metrics"]["outline_p50"])
    out = {}
    for o in sorted(groups):
        g = groups[o]
        med = lambda xs: sorted(xs)[len(xs) // 2] if xs else None
        out[str(o)] = {"n": g["n"],
                       "rim_band_px_max": max(g["rim"]),
                       "rim_band_px_median": med(g["rim"]),
                       "outline_p50_median": med(g["p50"]),
                       "best_score": min(g["score"])}
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(prog="search_pixel")
    ap.add_argument("--n", type=int, default=16, help="Halton 采样点数")
    ap.add_argument("--topk", type=int, default=1, help="取前 k 个做坐标下降")
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--budget", type=int, default=24, help="评估次数硬上限")
    ap.add_argument("--seed", type=int, default=20261101)
    ap.add_argument("--tag", default="px", help="渲染文件名里的标记")
    a = ap.parse_args(argv)

    bad = space_pixel.verify_defaults()
    if bad:
        print(f"[searchp] FATAL 默认值不同源：{bad}")
        return 2

    cache = {}
    best = None
    t_start = time.time()
    marker = {"event": "pixel_run_start", "seed": a.seed, "n": a.n,
              "budget": a.budget, "topk": a.topk, "rounds": a.rounds,
              "created": datetime.datetime.now().astimezone().isoformat(
                  timespec="seconds")}
    os.makedirs(os.path.dirname(TRIALS_PATH), exist_ok=True)
    with open(TRIALS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(marker, ensure_ascii=False, sort_keys=True) + "\n")

    def budget_left():
        return a.budget - len(cache)

    def ev(params, label, force=False):
        key = _key(params)
        if key in cache:
            return cache[key]
        if not force and budget_left() <= 0:
            return None
        i = len(cache) + 1
        rec = eval_pixel.evaluate(params, index=i,
                                  label=f"{a.tag}:{label}".replace(":", "_"))
        cache[key] = rec
        bs = "-" if best is None else f"{best['score']:.4f}"
        if i % 4 == 0 or i <= 2:
            print(f"[searchp] {i}/{a.budget} best={bs} ({label}) "
                  f"t={rec['t']:.1f}s elapsed={time.time() - t_start:.0f}s")
        return rec

    # ---------------- 0) baseline ----------------
    best = None

    def offer(rec, params, label):
        """更新全局最优。**score 打平时按 rim 亮带更宽者胜**（软目标的实际意义）。

        为什么需要 tie-break：实测 `rim_azimuth=back_right` 与 `back_left` 的 score
        **完全相同**（都 4e-06 —— 硬约束全过、软项都落在 0 附近），但 rim 亮带
        10px vs 3px。严格 `<` 比较会永远停在 baseline，把「零代价的轮廓光改进」
        丢掉。两个点皮肤指标逐位相同（195.02/26.82/32.00/4.77），描边同为 3px。
        """
        nonlocal best
        if best is None:
            best = {"score": rec["score"], "params": dict(params),
                    "metrics": rec["metrics"], "label": label, "rec": rec}
            return True
        s, m = rec["score"], rec["metrics"]
        cur = best
        better = (s < cur["score"] - 1e-9
                  or (abs(s - cur["score"]) <= 1e-9
                      and (m.get("rim_band_px") or 0.0)
                      > (cur["metrics"].get("rim_band_px") or 0.0)))
        if better:
            best = {"score": s, "params": dict(params),
                    "metrics": m, "label": label, "rec": rec}
        return better

    base = ev(space_pixel.defaults(), "baseline", force=True)
    offer(base, base["params"], "baseline")
    print(f"[searchp] baseline score={base['score']:.4f} hard={base['hard']} "
          f"soft={base['soft']:.4f} rim_band_px={base['metrics'].get('rim_band_px')}")

    # ---------------- 1) Halton 采样 ----------------
    scored = []
    for k, p in enumerate(space_pixel.sample(a.n, seed=a.seed)):
        if budget_left() <= 0:
            print(f"[searchp] budget exhausted during halton at k={k}")
            break
        rec = ev(p, f"halton{k:02d}")
        scored.append((rec["score"], k, p))
        offer(rec, p, f"halton{k:02d}")
    scored.sort(key=lambda t: (t[0], t[1]))
    print(f"[searchp] halton done best={best['score']:.4f} ({best['label']}) "
          f"n_evals={len(cache)}")

    # ---------------- 1.5) rim_azimuth 全枚举（枚举维不参与 ±1 坐标下降） ----------------
    skipped = []
    for v in space_pixel.dim("rim_azimuth")["choices"]:
        q = space_pixel.fixup({**space_pixel.defaults(), "rim_azimuth": v})
        if budget_left() <= 0:
            skipped.append(f"enum:rim_azimuth={v}(budget)")
            continue
        rec = ev(q, f"enum_{v}")
        if rec is not None:
            offer(rec, q, f"enum_{v}")
    print(f"[searchp] enum rim_azimuth done best={best['score']:.4f} "
          f"({best['label']}) n_evals={len(cache)}")

    # ---------------- 2) top-k 坐标下降（连续维 ±1 step） ----------------
    top = scored[:max(1, min(a.topk, len(scored)))]
    for rank, (s0, k0, p0) in enumerate(top, 1):
        cur = dict(p0)
        cur_s = s0
        print(f"[searchp] cd top{rank} start score={cur_s:.4f} params="
              + json.dumps(cur, ensure_ascii=False, sort_keys=True))
        for r in range(a.rounds):
            for key in DIM_ORDER:
                d = space_pixel.dim(key)
                if budget_left() <= 0:
                    skipped.append(f"top{rank}r{r + 1}:{key}(budget)")
                    continue
                best_q, best_s = None, cur_s
                for q in candidates(cur, d):
                    if budget_left() <= 0:
                        skipped.append(f"top{rank}r{r + 1}:{key}(budget)")
                        break
                    rec = ev(q, f"cd{rank}r{r + 1}_{key}")
                    if rec is None:
                        break
                    if rec["score"] < best_s - 1e-12:
                        best_s, best_q = rec["score"], q
                if best_q is not None:
                    cur, cur_s = best_q, best_s
            print(f"[searchp] cd top{rank} round{r + 1} score={cur_s:.4f} "
                  f"n_evals={len(cache)} left={budget_left()}")
        if offer(cache[_key(cur)], cur, f"cd_top{rank}"):
            print(f"[searchp] new best: {cur_s:.4f} ({best['label']})")

    # ---------------- 3) 判定 + 读-改-写 best.json ----------------
    recs = list(cache.values())
    max_rim = max((r["metrics"].get("rim_band_px") or 0.0) for r in recs if r["metrics"])
    rim_cells = [(r["params"].get("rim_energy"), r["params"].get("rim_azimuth"),
                  r["params"].get("outline_px"),
                  r["metrics"].get("rim_band_px"),
                  r["metrics"].get("rim_lit_skirt_p50"),
                  r["metrics"].get("rim_lit_hair_p50"),
                  r["metrics"].get("rim_band_px_legacy"))
                 for r in recs if r["metrics"]]
    rim_cells.sort(key=lambda t: (-(t[3] or 0.0), t[0] if t[0] else 0))
    table = outline_table(recs)
    # 判定线按任务书：>=2px 才算「可达」；<=1px 一律写「不可达」。
    RIM_THRESHOLD_PX = 2.0
    verdict = "reachable" if max_rim >= RIM_THRESHOLD_PX else "unreachable"
    elapsed = time.time() - t_start

    pix_doc = {
        "best_params": best["params"],
        "best_metrics": best["metrics"],
        "score": best["score"],
        "n_evals": len(cache),
        "elapsed_s": round(elapsed, 1),
        "seed": a.seed,
        "algorithm": ("baseline -> halton(n={}) -> rim_azimuth full enum on the default "
                      "point (4 azimuths; enum dim never walks +/-1) -> sort by score "
                      "-> top-{} -> coordinate descent on {} continuous dims "
                      "({} rounds) -> global best (score tie-break = wider rim_band_px); "
                      "budget={}".format(a.n, len(top), len(DIM_ORDER), a.rounds,
                                         a.budget)),
        "baseline_metrics": base["metrics"],
        "baseline_score": base["score"],
        "hard_violations_best": best["rec"]["hard"],
        "soft_best": best["rec"]["soft"],
        "skipped_dims": skipped,
        "rim_verdict": verdict,
        "rim_threshold_px": RIM_THRESHOLD_PX,
        "rim_metric": ("rim_lit differential: rim lamp ON(E) vs OFF(0) on the same "
                       "ortho views; pixel counts only when lum_on-lum_off>=8 and "
                       "the run drops back below that before the scan window ends"),
        "rim_band_px_max": max_rim,
        "rim_scan_top5": [{"rim_energy": c[0], "rim_azimuth": c[1],
                           "outline_px": c[2], "rim_band_px": c[3],
                           "rim_lit_skirt_p50": c[4], "rim_lit_hair_p50": c[5],
                           "rim_band_px_legacy": c[6]}
                          for c in rim_cells[:5]],
        "outline_px_table": table,
        # 受控对照（固定其余五维的 6 次定点评估，实测回填）
        "outline_px_controlled_table": CONTROLLED_TABLE,
        "rim_candidate": rim_candidate(recs),
        "dim_stats": dim_stats(recs),
        "created": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "trials": "opt/trials_pixel.jsonl",
        "best_label": best["label"],
    }
    before, after = write_best(pix_doc)
    with open(TRIALS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"event": "pixel_run_end", "seed": a.seed,
                            "n_evals": len(cache), "score": best["score"],
                            "rim_verdict": verdict, "rim_band_px_max": max_rim,
                            "elapsed_s": round(elapsed, 1),
                            "best_params": best["params"]},
                           ensure_ascii=False, sort_keys=True) + "\n")

    print(f"[searchp] done n_evals={len(cache)} elapsed={elapsed:.0f}s -> {BEST_PATH}")
    print(f"[searchp] top-level keys before={before}")
    print(f"[searchp] top-level keys after ={after}  (best_params 是否保留="
          f"{'best_params' in after})")
    print(f"[searchp] baseline score={base['score']:.4f} -> best score={best['score']:.4f}")
    print(f"[searchp] rim_verdict={verdict} rim_band_px_max={max_rim}")
    print(f"[searchp] outline_px_table=" + json.dumps(table, ensure_ascii=False))
    print("[searchp] best_params " + json.dumps(best["params"], ensure_ascii=False,
                                                sort_keys=True))
    print(f"[searchp] skipped_dims={skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())