# -*- coding: utf-8 -*-
"""opt/search.py —— 几何参数搜索主循环。

算法（一句话）：**Halton 低差异采样 32 点 → 按 score 取 top-4 → 每个 top 点做
2 轮逐维 ±1 step 的坐标下降 → 取全局最优。**

为什么不是贝叶斯优化 / CMA-ES：
  * 进程内只有 numpy，**没有 scipy**（没有 scipy.stats / scipy.optimize）；
  * 维度只有 5 个（4 数值 + 1 类别），一次评估要 3~8s，总预算 ≤100 次 ——
    代理模型（GP）在这个预算下拟合不出可信曲面，收益不如「把 32 个点铺匀 +
    局部下坡」来得确定；
  * 坐标下降天然给出「每维 ±1 step 是否改善」的敏感性数据，报告里能直接引用。

用法（工作目录 人物建模/）：
    blender -b --factory-startup --python opt/search.py -- --n 4          # 冒烟
    blender -b --factory-startup --python opt/search.py -- --n 32 --topk 4 --rounds 2

产物：
    opt/best.json     最优参数 + baseline 对照 + 敏感性（本文件写出，别手改）
    opt/trials.jsonl  每次评估一行（eval_geom 追加写）

可复现：采样与坐标下降全都不含随机性；唯一随机源是 `--seed`（默认 20261101），
它只决定 Halton 的跳跃起点与维度乱序，best.json 里记了 seed。
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

import space_geom          # noqa: E402
import eval_geom           # noqa: E402

BEST_PATH = os.path.join(HERE, "best.json")
TRIALS_PATH = os.path.join(HERE, "trials.jsonl")


def _key(params):
    return json.dumps(params, sort_keys=True, ensure_ascii=False)


def neighbours(p, d):
    """某维 ±1 个 step（越界则夹紧；夹紧后与原值相同就不试探）。"""
    k = d["key"]
    out = []
    if "choices" in d:
        ch = d["choices"]
        i = ch.index(p[k]) if p[k] in ch else 0
        for delta in (1, -1):
            j = i + delta
            if 0 <= j < len(ch):
                q = dict(p)
                q[k] = ch[j]
                out.append(q)
    else:
        for delta in (1, -1):
            v = space_geom.snap(d, p[k] + delta * d["step"])
            if v != p[k]:
                q = dict(p)
                q[k] = v
                out.append(q)
    return out


def _short(v, nd=3):
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)



def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(prog="search")
    ap.add_argument("--n", type=int, default=32, help="Halton 采样点数")
    ap.add_argument("--topk", type=int, default=4, help="取 score 最好的前 k 个做坐标下降")
    ap.add_argument("--rounds", type=int, default=2, help="坐标下降轮数")
    ap.add_argument("--seed", type=int, default=20261101)
    ap.add_argument("--out", default=BEST_PATH)
    a = ap.parse_args(argv)

    bad = space_geom.verify_defaults()
    if bad:
        print(f"[search] FATAL 默认值不同源：{bad}")
        print("[search] space_geom.DIMS 与现网模块常量不一致，先对齐再搜索")
        return 2

    n_dims = len(space_geom.DIMS)
    cache = {}                      # key -> rec
    order = []                      # 按评估顺序的 key
    best = None                     # 全局最优（下面 ev() 的进度行要用）
    t_start = time.time()
    total_est = 1 + a.n + a.topk * n_dims * 2 * a.rounds + n_dims
    marker = {"event": "run_start", "seed": a.seed, "n": a.n, "topk": a.topk,
              "rounds": a.rounds,
              "created": datetime.datetime.now().astimezone().isoformat(
                  timespec="seconds")}
    os.makedirs(os.path.dirname(TRIALS_PATH), exist_ok=True)
    with open(TRIALS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(marker, ensure_ascii=False, sort_keys=True) + "\n")

    def ev(params, label):
        key = _key(params)
        if key in cache:
            return cache[key]
        i = len(cache) + 1
        rec = eval_geom.evaluate(params, index=i, label=label)
        cache[key] = rec
        order.append(key)
        if i % 8 == 0 or i == total_est:
            bs = "-" if best is None else f"{best['score']:.4f}"
            print(f"[search] {i}/{total_est} best={bs} "
                  f"({label}) t={rec['t']:.1f}s elapsed={time.time() - t_start:.0f}s")
        return rec

    # ---------------- 0) baseline（= 现网手调默认值） ----------------
    base = ev(space_geom.defaults(), "baseline")
    best = {"score": base["score"], "params": dict(base["params"]),
            "metrics": base["metrics"], "rec": base, "label": "baseline"}
    print(f"[search] baseline score={base['score']:.4f} "
          f"hard={base['hard']} soft={base['soft']:.4f}")

    # ---------------- 1) Halton 采样 n 点 ----------------
    cands = space_geom.sample(a.n, seed=a.seed)
    scored = []
    for k, p in enumerate(cands):
        rec = ev(p, f"halton{k:02d}")
        scored.append((rec["score"], k, p))
        if rec["score"] < best["score"]:
            best = {"score": rec["score"], "params": dict(p),
                    "metrics": rec["metrics"], "rec": rec, "label": f"halton{k:02d}"}
    scored.sort(key=lambda t: (t[0], t[1]))
    print(f"[search] halton done: best={best['score']:.4f} ({best['label']}) "
          f"n_evals={len(cache)}")

    # ---------------- 2) top-k 坐标下降 ----------------
    top = scored[:max(1, min(a.topk, len(scored)))]
    for rank, (s0, k0, p0) in enumerate(top, 1):
        cur = dict(p0)
        cur_s = s0
        print(f"[search] cd top{rank} start score={cur_s:.4f} params="
              + json.dumps(cur, ensure_ascii=False, sort_keys=True))
        for r in range(a.rounds):
            for d in space_geom.DIMS:
                best_q, best_s = None, cur_s
                for q in neighbours(cur, d):
                    s = ev(q, f"cd{rank}r{r + 1}_{d['key']}")["score"]
                    if s < best_s - 1e-12:
                        best_s, best_q = s, q
                if best_q is not None:
                    cur, cur_s = best_q, best_s
            print(f"[search] cd top{rank} round{r + 1} score={cur_s:.4f} "
                  f"n_evals={len(cache)}")
        if cur_s < best["score"] - 1e-12:
            rec = cache[_key(cur)]
            best = {"score": cur_s, "params": dict(cur),
                    "metrics": rec["metrics"], "rec": rec,
                    "label": f"cd_top{rank}"}
            print(f"[search] new best from top{rank}: {cur_s:.4f}")

    # ---------------- 3) 每维敏感性：把该维固定在默认值 ----------------
    sensitivity = {}
    for d in space_geom.DIMS:
        k = d["key"]
        if best["params"].get(k) == d["default"]:
            sensitivity[k] = {"default": d["default"], "best": best["params"].get(k),
                              "score_at_default": best["score"], "delta": 0.0,
                              "note": "最优值 = 默认值（该维已是局部最优）"}
            continue
        p2 = dict(best["params"])
        p2[k] = d["default"]
        rec = ev(p2, f"sens_{k}")
        sensitivity[k] = {
            "default": d["default"], "best": best["params"].get(k),
            "score_at_default": rec["score"],
            "delta": round(rec["score"] - best["score"], 6),
            "note": "把该维固定在默认值 vs 最优值的 score 差（>0 = 最优值更好）",
        }
    print("[search] sensitivity " + json.dumps(sensitivity, ensure_ascii=False))

    # ---------------- 4) 落盘 ----------------
    elapsed = time.time() - t_start
    doc = {
        "seed": a.seed,
        "n_evals": len(cache),
        "best_params": best["params"],
        "best_metrics": best["metrics"],
        "score": best["score"],
        "baseline_metrics": base["metrics"],
        "baseline_score": base["score"],
        "created": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "algorithm": ("halton(n={}) -> sort by score -> top-{} -> coordinate descent "
                      "({} rounds, per-dim +/-1 step) -> global best"
                      .format(a.n, len(top), a.rounds)),
        "n_halton": a.n, "topk": len(top), "rounds": a.rounds,
        "hard_violations_best": best["rec"]["hard"],
        "soft_best": best["rec"]["soft"],
        "hard_violations_baseline": base["hard"],
        "soft_baseline": base["soft"],
        "sensitivity": sensitivity,
        "elapsed_s": round(elapsed, 1),
        "trials": "opt/trials.jsonl",
        "best_label": best["label"],
    }
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    with open(TRIALS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"event": "run_end", "seed": a.seed,
                            "n_evals": len(cache), "score": best["score"],
                            "elapsed_s": round(elapsed, 1),
                            "best_params": best["params"]},
                           ensure_ascii=False, sort_keys=True) + "\n")

    # ---------------- 5) 汇总打印 ----------------
    print(f"[search] done n_evals={len(cache)} elapsed={elapsed:.0f}s -> {a.out}")
    print(f"[search] baseline score={base['score']:.4f} -> best score={best['score']:.4f}")
    print("[search] best_params " + json.dumps(best["params"], ensure_ascii=False,
                                               sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())