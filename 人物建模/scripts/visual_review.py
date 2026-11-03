# -*- coding: utf-8 -*-
"""视觉审查问题单：把「AI 读图挑错」落成机器可读 JSON（纯标准库，不 import bpy）。

背景：`Blender体检/check.sh` 已经能出 16 环绕 + 顶视 + 拼版 + manifest；
`README` 的闭环协议第 3 步是「按视角列结构化问题」。本脚本把这一步固定成
schema、生成器、校验器和汇总器，避免问题单只存在于会话文字里。

它**不做视觉判断**：图仍由人或 VLM 看，本脚本只负责：
  1. `init` 从 manifest 生成空白问题单（带视图清单/渲染完整性检查）；
  2. `validate` 校验问题单的字段、枚举、视图名、重复 id、渲染文件是否存在；
  3. `summary` 出按严重度/状态/类别的计数与 Markdown 表。

用法（在 `人物建模/` 下执行）：

    python scripts/visual_review.py init \
        --manifest ../Blender体检/out/美女/manifest.json \
        --out out/美女_visual_review.json
    python scripts/visual_review.py validate out/美女_visual_review.json
    python scripts/visual_review.py summary out/美女_visual_review.json
    python scripts/visual_review.py selftest

问题单形状见 `init` 生成的文件；`problems[]` 每条至少要：
`id / view / severity / category / description / script_fixable / status`。
"""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                       # 人物建模/

SCHEMA = "blender-visual-review/v1"
SEVERITIES = ("high", "medium", "low", "info")
CATEGORIES = ("silhouette", "proportion", "intersection", "normal",
              "texture", "material", "lighting", "camera", "cropping", "other")
STATUSES = ("open", "fixed", "wontfix", "accepted")


def _utf8_stdio():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise SystemExit("找不到文件：" + path)
    except json.JSONDecodeError as exc:
        raise SystemExit("JSON 解析失败：{0}（{1}）".format(path, exc))


def _atomic_write(path, doc):
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def _manifest_views(manifest, base_dir):
    shots = manifest.get("shots") or []
    views = []
    for shot in shots:
        if not isinstance(shot, dict) or not shot.get("file"):
            continue
        name = str(shot["file"])
        views.append({
            "file": name,
            "azimuth_deg": shot.get("azimuth_deg"),
            "elevation_deg": shot.get("elevation_deg"),
            "exists": os.path.isfile(os.path.join(base_dir, name)),
            "bytes": os.path.getsize(os.path.join(base_dir, name))
            if os.path.isfile(os.path.join(base_dir, name)) else 0,
        })
    return views


def _render_checks(manifest_path, manifest, base_dir):
    items = []
    for name in [v.get("file") for v in manifest.get("shots") or [] if isinstance(v, dict)]:
        if not name:
            continue
        path = os.path.join(base_dir, name)
        exists = os.path.isfile(path)
        size = os.path.getsize(path) if exists else 0
        items.append({"file": name, "exists": exists, "bytes": size,
                      "ok": exists and size > 0})
    for name in ("sheet.png",):
        path = os.path.join(base_dir, name)
        exists = os.path.isfile(path)
        size = os.path.getsize(path) if exists else 0
        items.append({"file": name, "exists": exists, "bytes": size,
                      "ok": exists and size > 0})
    exists = os.path.isfile(manifest_path)
    size = os.path.getsize(manifest_path) if exists else 0
    items.append({"file": "manifest.json", "exists": exists, "bytes": size,
                  "ok": exists and size > 0})
    return items


def init_report(manifest_path, out_path, force=False):
    manifest = _load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise SystemExit("manifest 顶层必须是对象")
    out_dir = manifest.get("out_dir") or os.path.dirname(os.path.abspath(manifest_path))
    out_dir = os.path.abspath(out_dir)
    views = _manifest_views(manifest, out_dir)
    checks = _render_checks(manifest_path, manifest, out_dir)
    report = {
        "schema": SCHEMA,
        "model": manifest.get("model", ""),
        "manifest": os.path.abspath(manifest_path),
        "out_dir": out_dir,
        "created": datetime.datetime.now().isoformat(timespec="seconds"),
        "views": views,
        "render_checks": checks,
        "problems": [],
    }
    if os.path.exists(out_path) and not force:
        raise SystemExit("问题单已存在（加 --force 覆盖）：" + out_path)
    _atomic_write(out_path, report)
    return report


def _view_set(report):
    names = set()
    for view in report.get("views") or []:
        if isinstance(view, dict) and view.get("file"):
            names.add(str(view["file"]))
    names.add("sheet.png")
    names.add("all")
    return names


def validate_report(report):
    errors = []
    warnings = []
    if not isinstance(report, dict):
        return {"ok": False, "errors": ["报告顶层必须是对象"], "warnings": [], "counts": {}}
    if report.get("schema") != SCHEMA:
        errors.append("schema 必须是 {0!r}".format(SCHEMA))
    if not isinstance(report.get("model"), str):
        errors.append("model 必须是字符串")
    views = report.get("views")
    if not isinstance(views, list) or not views:
        errors.append("views 必须是非空数组")
    problems = report.get("problems")
    if not isinstance(problems, list):
        errors.append("problems 必须是数组")
        problems = []

    allowed_views = _view_set(report)
    seen = set()
    for i, problem in enumerate(problems):
        tag = "problems[{0}]".format(i)
        if not isinstance(problem, dict):
            errors.append(tag + " 必须是对象")
            continue
        pid = problem.get("id")
        if not isinstance(pid, str) or not pid.strip():
            errors.append(tag + ".id 必须是非空字符串")
        elif pid in seen:
            errors.append(tag + ".id 重复：" + pid)
        else:
            seen.add(pid)
        view = problem.get("view")
        if view not in allowed_views:
            errors.append("{0}.view 不在视图清单里：{1!r}".format(tag, view))
        severity = problem.get("severity")
        if severity not in SEVERITIES:
            errors.append("{0}.severity 必须是 {1}".format(tag, "/".join(SEVERITIES)))
        category = problem.get("category")
        if category not in CATEGORIES:
            errors.append("{0}.category 必须是 {1}".format(tag, "/".join(CATEGORIES)))
        status = problem.get("status")
        if status not in STATUSES:
            errors.append("{0}.status 必须是 {1}".format(tag, "/".join(STATUSES)))
        desc = problem.get("description")
        if not isinstance(desc, str) or not desc.strip():
            errors.append(tag + ".description 必须是非空字符串")
        if not isinstance(problem.get("script_fixable"), bool):
            errors.append(tag + ".script_fixable 必须是 bool")
        for key in ("suggested_fix", "evidence"):
            if key in problem and not isinstance(problem[key], str):
                errors.append("{0}.{1} 必须是字符串".format(tag, key))

    checks = report.get("render_checks") or []
    if not isinstance(checks, list):
        errors.append("render_checks 必须是数组")
        checks = []
    missing = [c.get("file") for c in checks if isinstance(c, dict) and not c.get("ok")]
    for name in missing:
        errors.append("渲染文件缺失或为空：" + str(name))

    counts = {
        "problems": len(problems),
        "open": sum(1 for p in problems if isinstance(p, dict) and p.get("status") == "open"),
        "fixed": sum(1 for p in problems if isinstance(p, dict) and p.get("status") == "fixed"),
        "high": sum(1 for p in problems if isinstance(p, dict) and p.get("severity") == "high"),
        "script_fixable": sum(1 for p in problems
                              if isinstance(p, dict) and p.get("script_fixable") is True),
    }
    return {"ok": not errors, "errors": errors, "warnings": warnings, "counts": counts}


def summary(report):
    result = validate_report(report)
    problems = report.get("problems") or []
    lines = []
    lines.append("# 视觉审查问题单")
    lines.append("")
    lines.append("model: `{0}`".format(report.get("model", "")))
    lines.append("")
    lines.append("| 项 | 数 |")
    lines.append("|---|---|")
    for key in ("problems", "open", "fixed", "high", "script_fixable"):
        lines.append("| {0} | {1} |".format(key, result["counts"].get(key, 0)))
    lines.append("")
    if problems:
        lines.append("| id | view | severity | category | status | fixable | description |")
        lines.append("|---|---|---|---|---|---|---|")
        for p in problems:
            if not isinstance(p, dict):
                continue
            desc = str(p.get("description", "")).replace("|", "\\|")
            lines.append("| {0} | {1} | {2} | {3} | {4} | {5} | {6} |".format(
                p.get("id", ""), p.get("view", ""), p.get("severity", ""),
                p.get("category", ""), p.get("status", ""),
                "yes" if p.get("script_fixable") else "no", desc))
    else:
        lines.append("（还没有问题条目）")
    if not result["ok"]:
        lines.append("")
        lines.append("## 校验错误")
        for error in result["errors"]:
            lines.append("- " + error)
    return "\n".join(lines) + "\n", result


def selftest():
    import tempfile
    out_root = os.path.join(ROOT, "out")
    os.makedirs(out_root, exist_ok=True)
    passed = 0
    failed = 0
    with tempfile.TemporaryDirectory(dir=out_root) as td:
        out_dir = os.path.join(td, "views")
        os.makedirs(out_dir)
        for name in ("view_000.png", "view_001.png", "view_top.png", "sheet.png"):
            with open(os.path.join(out_dir, name), "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n" + b"x" * 32)
        manifest = {
            "model": "selftest.blend",
            "out_dir": out_dir,
            "shots": [
                {"file": "view_000.png", "azimuth_deg": 0, "elevation_deg": 20},
                {"file": "view_001.png", "azimuth_deg": 180, "elevation_deg": 20},
                {"file": "view_top.png", "azimuth_deg": 0, "elevation_deg": 90},
            ],
        }
        manifest_path = os.path.join(td, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False)
        report_path = os.path.join(td, "review.json")
        try:
            report = init_report(manifest_path, report_path)
            assert report["schema"] == SCHEMA
            assert len(report["views"]) == 3
            assert all(c["ok"] for c in report["render_checks"])
            print("[selftest] PASS init from manifest")
            passed += 1
        except Exception as exc:
            print("[selftest] FAIL init: {0}".format(exc))
            failed += 1
            report = None

        if report is not None:
            report["problems"] = [{
                "id": "P1", "view": "view_000.png", "severity": "high",
                "category": "silhouette", "description": "左肩轮廓有台阶",
                "script_fixable": True, "status": "open",
                "suggested_fix": "调 shoulder_width_scale", "evidence": "view_000",
            }]
            result = validate_report(report)
            if result["ok"]:
                print("[selftest] PASS validate good report")
                passed += 1
            else:
                print("[selftest] FAIL validate good report: {0}".format(result["errors"]))
                failed += 1

            bad = json.loads(json.dumps(report))
            bad["problems"][0]["severity"] = "urgent"
            bad["problems"][0]["view"] = "view_999.png"
            result = validate_report(bad)
            if (not result["ok"]) and any("severity" in e for e in result["errors"]) \
                    and any("view" in e for e in result["errors"]):
                print("[selftest] PASS validate rejects bad fields")
                passed += 1
            else:
                print("[selftest] FAIL validate bad report: {0}".format(result["errors"]))
                failed += 1

            text, result = summary(report)
            if result["ok"] and "P1" in text and "左肩" in text:
                print("[selftest] PASS summary markdown")
                passed += 1
            else:
                print("[selftest] FAIL summary markdown")
                failed += 1

    print("[selftest] PASS={0} FAIL={1}".format(passed, failed))
    return 0 if failed == 0 else 1


def main(argv=None):
    _utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="visual_review.py",
        description="Blender 体检图的结构化视觉审查问题单（init/validate/summary）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="从 Blender体检 manifest 生成空白问题单")
    p_init.add_argument("--manifest", required=True)
    p_init.add_argument("--out", required=True)
    p_init.add_argument("--force", action="store_true")

    p_val = sub.add_parser("validate", help="校验问题单")
    p_val.add_argument("report")
    p_val.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary", help="打印问题单 Markdown 汇总")
    p_sum.add_argument("report")
    p_sum.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="临时 manifest/问题单自检")

    args = parser.parse_args(argv)
    if args.cmd == "init":
        report = init_report(args.manifest, args.out, force=args.force)
        result = validate_report(report)
        print("[visual] 问题单 -> {0}".format(args.out))
        print("[visual] views={0} render_checks={1} problems={2}".format(
            len(report["views"]), len(report["render_checks"]), len(report["problems"])))
        if not result["ok"]:
            for error in result["errors"]:
                print("[visual] 错误：" + error, file=sys.stderr)
            return 1
        return 0
    if args.cmd == "validate":
        report = _load_json(args.report)
        result = validate_report(report)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("[visual] ok={0} counts={1}".format(result["ok"], result["counts"]))
            for error in result["errors"]:
                print("  - " + error)
        return 0 if result["ok"] else 1
    if args.cmd == "summary":
        report = _load_json(args.report)
        text, result = summary(report)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(text, end="")
        return 0 if result["ok"] else 1
    if args.cmd == "selftest":
        return selftest()
    return 2


if __name__ == "__main__":
    sys.exit(main())
