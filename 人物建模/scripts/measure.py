# -*- coding: utf-8 -*-
"""外观体检：跑测量 -> 读基准表 -> 打印「实测 vs 目标」差值表。

用法（在项目根 `实用工具/Blender建模/人物建模/` 下）：

    python scripts/measure.py                 # 重新测量并判定
    python scripts/measure.py --cached        # 不重跑 Blender，用上次的 out/appearance.json
    python scripts/measure.py --blend _bak_before_75/美女.blend   # 量别的文件
    python scripts/measure.py --spec spec/xxx.json                # 换一套基准

退出码：有 must 级 FAIL 返回 1，全过返回 0，测量失败返回 2。
产物：out/appearance.json（原始测量）、out/appearance_report.json（判定结果）。

为什么单独做一个入口而不是塞进 check.py：
`check.py` 判的是「结构合法性」（权重和、穿模、屈指），全是二值通过/不通过；
这里是「外观比例」，要的是**连续差值**（差 3.2mm 还是 30mm），判定逻辑与
输出形态都不同，混在一起会让两边的判据都变模糊。
"""
import argparse
import json
import os
import subprocess
import sys

import bpyrun

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lib"))

import appearance  # noqa: E402

DEFAULT_SPEC = os.path.join(ROOT, "spec", "reference.json")
DEFAULT_JSON = os.path.join(ROOT, "out", "appearance.json")
REPORT_JSON = os.path.join(ROOT, "out", "appearance_report.json")
PROBE = os.path.join(ROOT, "_probe", "appearance_probe.py")


def _w(s):
    """字符串显示宽度（中日韩字符算 2 列）。"""
    return sum(2 if ord(c) > 0x2E80 else 1 for c in str(s))


def _pad(s, width, align="<"):
    s = str(s)
    n = width - _w(s)
    if n <= 0:
        return s
    return s + " " * n if align == "<" else " " * n + s


def _fmt(key, val, unit):
    if val is None:
        return "—"
    if unit == "m":
        return "%.1f mm" % (val * 1000.0)
    if key == "heads_ratio":
        return "%.3f" % val
    return "%.4f" % val


def run_probe(blend):
    blender = bpyrun.blender_exe(bpyrun.BLENDER_ENV, bpyrun.DEFAULT_BLENDER)
    if blender is None:
        print("[measure] 错误：找不到 Blender", file=sys.stderr)
        return 2
    cmd = [blender, "-b", "--factory-startup", "--python-exit-code", "1",
           "--python", PROBE, "--", "--out", DEFAULT_JSON]
    if blend:
        cmd += ["--blend", blend]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        print("[measure] 错误：测量探针退出码 %d" % proc.returncode, file=sys.stderr)
        tail = (proc.stdout or "").strip().splitlines()[-12:]
        for line in tail:
            print("    " + line, file=sys.stderr)
        return 2
    for line in (proc.stdout or "").splitlines():
        if "[probe]" in line:
            print(line.replace("[probe]", "[measure]"))
    return 0


def main(argv=None):
    bpyrun.utf8_stdio()   # 管道/重定向下用 UTF-8，防 GBK 编码崩溃
    ap = argparse.ArgumentParser(prog="measure.py", description="外观体检：形状 -> 数字 -> 判定")
    ap.add_argument("--cached", action="store_true", help="复用 out/appearance.json，不重跑 Blender")
    ap.add_argument("--blend", default=None, help="要测量的 blend（默认 美女.blend）")
    ap.add_argument("--spec", default=DEFAULT_SPEC, help="基准表路径")
    ap.add_argument("--json", default=DEFAULT_JSON, help="测量结果路径")
    args = ap.parse_args(argv)

    spec_path = args.spec if os.path.isabs(args.spec) else os.path.join(ROOT, args.spec)
    if not os.path.exists(spec_path):
        print("[measure] 错误：找不到基准表 " + spec_path, file=sys.stderr)
        return 2
    with open(spec_path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    spec = {k: v for k, v in doc.items() if isinstance(v, dict) and "target" in v}
    meta = doc.get("_meta", {})

    if not args.cached:
        code = run_probe(args.blend)
        if code != 0:
            return code

    json_path = args.json if os.path.isabs(args.json) else os.path.join(ROOT, args.json)
    if not os.path.exists(json_path):
        print("[measure] 错误：没有测量结果，先跑一次不带 --cached", file=sys.stderr)
        return 2
    with open(json_path, "r", encoding="utf-8") as f:
        measured = json.load(f)

    rows = appearance.check(spec, measured)

    fails = [r for r in rows if r["verdict"] == "FAIL"]
    warns = [r for r in rows if r["verdict"] == "WARN"]
    missing = [r for r in rows if r["verdict"] == "MISSING"]

    print()
    print("外观体检 · %s" % meta.get("name", os.path.basename(spec_path)))
    print("基准表 %s" % os.path.relpath(spec_path, ROOT))
    found = measured.get("_meta", {})
    print("测量源 %s  部件 %s%s" % (
        found.get("blend", "?"),
        ",".join(found.get("objects_found", [])),
        ("  缺 " + ",".join(found["objects_missing"])) if found.get("objects_missing") else ""))
    print()
    print(_pad("指标", 30) + _pad("实测", 12, ">") + _pad("目标", 12, ">")
          + _pad("差值", 12, ">") + _pad("容差", 16, ">") + "  判定")
    print("─" * 88)
    for r in rows:
        unit = r["unit"]
        got = _fmt(r["key"], r["got"], unit)
        tgt = _fmt(r["key"], r["target"], unit)
        diff = r["diff"]
        if diff is None:
            dstr = "—"
        elif unit == "m":
            dstr = "%+.1f mm" % (diff * 1000.0)
        elif r["key"] == "heads_ratio":
            dstr = "%+.3f" % diff
        else:
            dstr = "%+.4f" % diff
        if r["tol"] is not None:
            tstr = _fmt(r["key"], r["tol"], unit)
        elif r.get("lo") is not None and r.get("hi") is not None:
            tstr = "%s~%s" % (_fmt(r["key"], r["lo"], unit), _fmt(r["key"], r["hi"], unit))
        elif r.get("lo") is not None:
            tstr = "≥" + _fmt(r["key"], r["lo"], unit)
        else:
            tstr = "—"
        print(_pad(r["label"], 30) + _pad(got, 12, ">") + _pad(tgt, 12, ">")
              + _pad(dstr, 12, ">") + _pad(tstr, 16, ">") + "  " + r["verdict"])
    print("─" * 88)
    print("PASS %d   FAIL %d   WARN %d   MISSING %d" %
          (len([r for r in rows if r["verdict"] == "PASS"]), len(fails), len(warns), len(missing)))

    if fails:
        print()
        print("必须修：")
        for r in fails:
            print("  · %s：实测 %s，目标 %s，差 %s" % (
                r["label"], _fmt(r["key"], r["got"], r["unit"]),
                _fmt(r["key"], r["target"], r["unit"]),
                ("%+.1f mm" % (r["diff"] * 1000.0)) if r["unit"] == "m" else "%+.4f" % r["diff"]))
            if r.get("source"):
                pass
    if warns:
        print()
        print("已知取舍（不拦）：")
        for r in warns:
            print("  · %s：%s" % (r["label"], r["key"]))

    os.makedirs(os.path.dirname(REPORT_JSON), exist_ok=True)
    payload = {
        "spec": os.path.relpath(spec_path, ROOT),
        "spec_name": meta.get("name"),
        "blend": found.get("blend"),
        "summary": {
            "pass": len([r for r in rows if r["verdict"] == "PASS"]),
            "fail": len(fails), "warn": len(warns), "missing": len(missing),
        },
        "rows": rows,
    }
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print()
    print("报告 -> %s" % os.path.relpath(REPORT_JSON, ROOT))
    return 1 if (fails or missing) else 0


if __name__ == "__main__":
    sys.exit(main())
