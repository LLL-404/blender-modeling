# -*- coding: utf-8 -*-
"""参数响应表：扫一个旋钮，量出「参数 -> 形状」的定量关系。

用法（在项目根 `实用工具/Blender建模/人物建模/` 下）：

    python scripts/sweep.py --param appearance.head_to_body_ratio --values 6.5,7.0,7.5,8.0
    python scripts/sweep.py --param appearance.waist_scale --values 0.95,1.0,1.05
    python scripts/sweep.py --param appearance.head_to_body_ratio --values 6.5,7.5 --no-build

每一步：写一份只改了这个键的临时 profile -> `PM_PROFILE` 指过去 ->
`build.py all` 重建 -> 测量 -> 记录。最后把 `params/profile.json` 的
配置重建一遍，保证磁盘上留下的仍是原配置（--keep 可保留最后一个扫点）。

为什么值得跑：`head_to_body_ratio` 从 6.505 改到 7.5 时，头长了 −33mm、
可见颈长 +33mm、肩宽/头宽 +0.15 —— 三个指标同时动，靠读代码是推不准的
（本项目里脖子、领口、头发的硬编码坐标都不跟随这个旋钮，是实测才发现的）。
跑一张表，下次就知道改一个数会连带什么。

产物：`out/sweep_<参数名>.json`（每点的完整测量 + 响应矩阵）。
"""
import argparse
import copy
import json
import os
import subprocess
import sys

import bpyrun

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR = os.path.join(ROOT, "params", "_tmp")
TMP_PROFILE = os.path.join(TMP_DIR, "sweep.json")
PROFILE = os.path.join(ROOT, "params", "profile.json")
PROBE = os.path.join(ROOT, "_probe", "appearance_probe.py")

# 响应表里要对比的指标（顺序即表格顺序）。只挑能读懂、且随参数动的那几个。
TRACK = [
    ("heads_ratio", "头身比", "%.3f"),
    ("head_len", "头长 mm", "%.1f"),
    ("head_width", "头宽 mm", "%.1f"),
    ("neck_visible", "颈长 mm", "%.1f"),
    ("head_body_gap", "头身接缝 mm", "%+.1f"),
    ("hair_cap_gap", "发帽厚 mm", "%.1f"),
    ("hair_back_ratio", "后脑厚宽比", "%.3f"),
    ("shoulder_over_headw", "肩宽/头宽", "%.3f"),
    ("waist_over_hip", "腰/髋", "%.3f"),
    ("skirt_taper", "裙摆锥度", "%.3f"),
    ("leg_ratio", "腿长比", "%.3f"),
]

SCALE = {"head_len": 1000.0, "head_width": 1000.0, "neck_visible": 1000.0,
         "head_body_gap": 1000.0, "hair_cap_gap": 1000.0}


def _set(doc, dotted, value):
    node = doc
    parts = dotted.split(".")
    for p in parts[:-1]:
        node = node.setdefault(p, {})
    node[parts[-1]] = value


def _blender():
    return bpyrun.blender_exe(bpyrun.BLENDER_ENV, bpyrun.DEFAULT_BLENDER)


def _build_and_measure(blender, out_json, do_build):
    env = dict(os.environ)
    env["PM_PROFILE"] = os.path.relpath(TMP_PROFILE, ROOT)
    if do_build:
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build.py"), "all"],
                           cwd=ROOT, env=env, capture_output=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            tail = (r.stdout or "").strip().splitlines()[-6:]
            raise RuntimeError("build 失败 rc=%d\n%s" % (r.returncode, "\n".join(tail)))
    r = subprocess.run([blender, "-b", "--factory-startup", "--python-exit-code", "1",
                        "--python", PROBE, "--", "--out", out_json],
                       cwd=ROOT, env=env, capture_output=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        tail = (r.stdout or "").strip().splitlines()[-6:]
        raise RuntimeError("probe 失败 rc=%d\n%s" % (r.returncode, "\n".join(tail)))


def main(argv=None):
    bpyrun.utf8_stdio()   # 管道/重定向下用 UTF-8，防 GBK 编码崩溃
    ap = argparse.ArgumentParser(prog="sweep.py", description="参数 -> 形状 响应表")
    ap.add_argument("--param", required=True, help="点路径，如 appearance.head_to_body_ratio")
    ap.add_argument("--values", required=True, help="逗号分隔的取值，如 6.5,7.0,7.5")
    ap.add_argument("--no-build", action="store_true",
                    help="只测量不重建（测那些不需要重建就生效的参数，或复用已有 blend）")
    ap.add_argument("--keep", action="store_true", help="保留最后一个扫点，不恢复原配置")
    args = ap.parse_args(argv)

    blender = _blender()
    if blender is None:
        print("[sweep] 找不到 Blender", file=sys.stderr)
        return 2
    if not os.path.exists(PROFILE):
        print("[sweep] 找不到 " + PROFILE, file=sys.stderr)
        return 2

    with open(PROFILE, "r", encoding="utf-8") as f:
        base_doc = json.load(f)
    values = []
    for tok in args.values.split(","):
        tok = tok.strip()
        if not tok:
            continue
        values.append(int(tok) if tok.lstrip("-").isdigit() else float(tok))
    if len(values) < 2:
        print("[sweep] 至少给两个取值才能看响应", file=sys.stderr)
        return 2

    os.makedirs(TMP_DIR, exist_ok=True)
    results = []
    print("[sweep] 参数 %s  取值 %s" % (args.param, values))
    for i, v in enumerate(values):
        doc = copy.deepcopy(base_doc)
        _set(doc, args.param, v)
        with open(TMP_PROFILE, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
        out_json = os.path.join(ROOT, "out", "sweep_%s_%02d.json" % (args.param.replace(".", "_"), i))
        print("[sweep] ---- %s = %s ----" % (args.param, v))
        _build_and_measure(blender, out_json, not args.no_build)
        with open(out_json, "r", encoding="utf-8") as f:
            results.append((v, json.load(f)))

    # ---- 响应矩阵（先算先落盘）----
    # 顺序讲究：恢复原配置要再跑一次 `build.py all`（几十秒），失败或中断时
    # 不该把已经花掉的扫描结果一起丢掉。所以矩阵先打印、先写文件，再恢复。
    headers = ["指标"] + ["%s" % v for v, _ in results] + ["每 +1 的变化"]
    widths = [22] + [12] * len(results) + [16]
    print()
    print("[sweep] 响应矩阵：%s" % args.param)
    print("  " + "".join(h.ljust(w) for h, w in zip(headers, widths)))
    print("  " + "─" * sum(widths))
    matrix = {}
    for key, label, fmt in TRACK:
        vals = []
        for _v, d in results:
            raw = d.get(key)
            vals.append(None if raw is None else raw * SCALE.get(key, 1.0))
        cells = []
        for x in vals:
            cells.append("—" if x is None else (fmt % x))
        # 斜率：首尾差 / 参数跨度
        slope = "—"
        pair = [(v, x) for (v, _d), x in zip(results, vals) if x is not None]
        if len(pair) >= 2:
            dv = pair[-1][0] - pair[0][0]
            if abs(dv) > 1e-12:
                slope = fmt % ((pair[-1][1] - pair[0][1]) / dv)
        matrix[key] = {"label": label,
                       "points": [{"value": v, "measured": x} for (v, _d), x in zip(results, vals)],
                       "per_unit": None if slope == "—" else (pair[-1][1] - pair[0][1]) / (pair[-1][0] - pair[0][0])}
        print("  " + label.ljust(widths[0]) + "".join(c.rjust(w) for c, w in zip(cells, widths[1:])))
    print()

    payload = {"param": args.param, "values": values, "build": not args.no_build,
               "matrix": matrix}
    out_path = os.path.join(ROOT, "out", "sweep_%s.json" % args.param.replace(".", "_"))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print("[sweep] 表 -> %s" % os.path.relpath(out_path, ROOT))

    # ---- 恢复原配置并重建（收尾动作放最后：即使它失败，扫描结果已经落盘）----
    if not args.keep:
        with open(TMP_PROFILE, "w", encoding="utf-8") as f:
            json.dump(base_doc, f, ensure_ascii=False, indent=1)
        print("[sweep] 恢复原配置并重建 ...")
        _build_and_measure(blender, os.path.join(ROOT, "out", "appearance.json"), True)
        print("[sweep] 已恢复 params/profile.json 的配置")
    return 0


if __name__ == "__main__":
    sys.exit(main())
