# -*- coding: utf-8 -*-
"""内部执行 benchmark：RAG 检索命中 + 候选 bapi 脚本执行（纯标准库，不 import bpy）。

它不是“模型能力榜”，而是本仓升级后的**回归基线**：
  - 每个任务先跑 `rag.py query`，检查期望的 bapi/API 是否进 top-k；
  - 再把 `bench/candidates/<id>.py` 复制到本次 run 目录，用 `run_bapi.py` 的
    headless 执行门跑一遍，检查退出码/期望文件/期望文本；
  - 输出 JSON + Markdown 报告，记录逐任务耗时与通过率。

以后 agent 生成的候选代码可以放到 `--candidate-dir`，用同一套任务与判据对比。

用法（在 `人物建模/` 下执行）：

    python scripts/bench.py list
    python scripts/bench.py run
    python scripts/bench.py run --task cube_bevel
    python scripts/bench.py run --candidate-dir out/agent_candidates --json
    python scripts/bench.py selftest

产物：`out/bench/run-<时间戳>/`（候选副本 + PNG）、`out/bench/latest.json`、
`out/bench/latest.md`；out/ 已 gitignore。
"""
import argparse
import datetime
import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                       # 人物建模/
PROJECT = os.path.dirname(ROOT)                    # Blender建模/
BENCH_DIR = os.path.join(ROOT, "bench")
DEFAULT_TASKS = os.path.join(BENCH_DIR, "tasks.json")
OUT_DIR = os.path.join(ROOT, "out", "bench")

import rag          # noqa: E402
import run_bapi     # noqa: E402


def _utf8_stdio():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def load_tasks(path=DEFAULT_TASKS):
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    tasks = doc.get("tasks") if isinstance(doc, dict) else None
    if not isinstance(tasks, list) or not tasks:
        raise SystemExit("tasks.json 里没有 tasks 数组：" + path)
    seen = set()
    for task in tasks:
        for key in ("id", "title", "rag_query", "candidate", "expect_file", "expect_text"):
            if key not in task:
                raise SystemExit("task 缺少 {0}：{1!r}".format(key, task))
        if task["id"] in seen:
            raise SystemExit("task id 重复：" + task["id"])
        seen.add(task["id"])
    return tasks


def _candidate_path(task, candidate_dir):
    if candidate_dir:
        return os.path.join(candidate_dir, task["id"] + ".py")
    path = task["candidate"]
    return path if os.path.isabs(path) else os.path.join(ROOT, path)


def _rag_check(task):
    result = rag.query(task["rag_query"], limit=12, manual_limit=0)
    anchors = result.get("anchors", [])
    hay = "\n".join(
        (item.get("title", "") + " " + item.get("source", ""))
        for item in list(result.get("local", [])) + anchors)
    expected = list(task.get("expect_rag_any") or [])
    hits = [needle for needle in expected if needle.lower() in hay.lower()]
    return {
        "ok": bool(hits),
        "query": task["rag_query"],
        "expected": expected,
        "hits": hits,
        "anchors": [item.get("title", "") for item in anchors],
        "top": [item.get("title", "") for item in result.get("local", [])[:6]],
    }


def run_task(task, run_dir, candidate_dir=None, timeout=None):
    source = _candidate_path(task, candidate_dir)
    if not os.path.isfile(source):
        return {
            "id": task["id"], "title": task.get("title", ""), "ok": False,
            "rag": _rag_check(task),
            "exec": {"ok": False, "exit": 2, "elapsed": 0.0,
                     "error": "候选脚本不存在：" + source,
                     "files": [], "missing_text": []},
        }
    dest = os.path.join(run_dir, task["id"] + ".py")
    shutil.copy2(source, dest)
    expect_path = os.path.join(run_dir, task["expect_file"])
    old_out = os.environ.get("BENCH_OUT_DIR")
    old_bapi = os.environ.get("BAPI_DIR")
    os.environ["BENCH_OUT_DIR"] = run_dir
    os.environ["BAPI_DIR"] = os.path.join(PROJECT, "BlenderAPI")
    try:
        started = time.monotonic()
        exec_result = run_bapi.run_candidate(
            dest, timeout=timeout or task.get("timeout", 60),
            expect_files=[expect_path],
            expect_text=list(task.get("expect_text") or []),
            tail=25)
        exec_result["wall"] = round(time.monotonic() - started, 3)
    finally:
        if old_out is None:
            os.environ.pop("BENCH_OUT_DIR", None)
        else:
            os.environ["BENCH_OUT_DIR"] = old_out
        if old_bapi is None:
            os.environ.pop("BAPI_DIR", None)
        else:
            os.environ["BAPI_DIR"] = old_bapi

    rag_result = _rag_check(task)
    return {
        "id": task["id"],
        "title": task.get("title", ""),
        "tags": task.get("tags", []),
        "ok": bool(rag_result["ok"] and exec_result["ok"]),
        "rag": rag_result,
        "exec": {
            "ok": exec_result["ok"],
            "exit": exec_result["exit"],
            "elapsed": exec_result["elapsed"],
            "wall": exec_result.get("wall", exec_result["elapsed"]),
            "files": exec_result["files"],
            "missing_text": exec_result["missing_text"],
            "error": exec_result.get("error", ""),
            "stdout_tail": exec_result.get("stdout_tail", ""),
            "stderr_tail": exec_result.get("stderr_tail", ""),
        },
    }


def run_all(tasks, candidate_dir=None, timeout=None, run_id=None):
    run_id = run_id or datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = os.path.join(OUT_DIR, "run-" + run_id)
    os.makedirs(run_dir, exist_ok=True)
    t0 = time.monotonic()
    results = []
    for i, task in enumerate(tasks, 1):
        print("[bench] ({0}/{1}) {2} ...".format(i, len(tasks), task["id"]),
              file=sys.stderr)
        result = run_task(task, run_dir, candidate_dir=candidate_dir, timeout=timeout)
        results.append(result)
        print("[bench]   rag={0} exec={1} ok={2}".format(
            "PASS" if result["rag"]["ok"] else "FAIL",
            "PASS" if result["exec"]["ok"] else "FAIL",
            "PASS" if result["ok"] else "FAIL"), file=sys.stderr)
    elapsed = time.monotonic() - t0
    total = len(results)
    rag_pass = sum(1 for r in results if r["rag"]["ok"])
    exec_pass = sum(1 for r in results if r["exec"]["ok"])
    all_pass = sum(1 for r in results if r["ok"])
    report = {
        "schema": "blender-bench-report/v1",
        "run_id": run_id,
        "started": datetime.datetime.now().isoformat(timespec="seconds"),
        "run_dir": run_dir,
        "candidate_dir": candidate_dir or "",
        "aggregate": {
            "total": total,
            "rag_pass": rag_pass,
            "exec_pass": exec_pass,
            "all_pass": all_pass,
            "pass_rate": round(all_pass / total, 4) if total else 0.0,
            "elapsed": round(elapsed, 3),
            "avg_task_elapsed": round(
                sum(r["exec"].get("wall", r["exec"]["elapsed"]) for r in results) / total, 3)
            if total else 0.0,
        },
        "tasks": results,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    stamp_path = os.path.join(OUT_DIR, "report-{0}.json".format(run_id))
    latest_path = os.path.join(OUT_DIR, "latest.json")
    for path in (stamp_path, latest_path):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
    md = format_markdown(report)
    for path in (os.path.join(OUT_DIR, "report-{0}.md".format(run_id)),
                 os.path.join(OUT_DIR, "latest.md")):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(md)
    report["_paths"] = {"json": latest_path, "md": os.path.join(OUT_DIR, "latest.md"),
                        "stamped_json": stamp_path, "run_dir": run_dir}
    return report


def format_markdown(report):
    agg = report["aggregate"]
    lines = [
        "# Blender bench report",
        "",
        "run_id: `{0}`".format(report["run_id"]),
        "",
        "| 指标 | 值 |",
        "|---|---|",
        "| tasks | {0} |".format(agg["total"]),
        "| RAG pass | {0}/{1} |".format(agg["rag_pass"], agg["total"]),
        "| exec pass | {0}/{1} |".format(agg["exec_pass"], agg["total"]),
        "| all pass | {0}/{1} ({2:.0%}) |".format(
            agg["all_pass"], agg["total"], agg["pass_rate"]),
        "| wall | {0:.1f}s |".format(agg["elapsed"]),
        "| avg task | {0:.2f}s |".format(agg["avg_task_elapsed"]),
        "",
        "| id | RAG | exec | exit | wall | file |",
        "|---|---|---|---|---|---|",
    ]
    for task in report["tasks"]:
        files = task["exec"].get("files") or []
        file_cell = "PASS" if files and all(f.get("ok") for f in files) else "FAIL"
        lines.append("| {0} | {1} | {2} | {3} | {4:.2f}s | {5} |".format(
            task["id"],
            "PASS" if task["rag"]["ok"] else "FAIL",
            "PASS" if task["exec"]["ok"] else "FAIL",
            task["exec"]["exit"],
            task["exec"].get("wall", task["exec"]["elapsed"]),
            file_cell))
    return "\n".join(lines) + "\n"


def selftest():
    tasks = load_tasks()
    task = next((t for t in tasks if t["id"] == "cube_bevel"), None)
    if task is None:
        print("[selftest] FAIL 缺少 cube_bevel 任务")
        return 1
    out_root = os.path.join(ROOT, "out")
    os.makedirs(out_root, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out_root) as td:
        result = run_task(task, td)
        if result["ok"]:
            print("[selftest] PASS cube_bevel rag+exec")
            return 0
        print("[selftest] FAIL cube_bevel: rag={0} exec={1}".format(
            result["rag"], result["exec"]))
        return 1


def _print_report(report):
    print("[bench] run={0} dir={1}".format(report["run_id"], report["run_dir"]))
    print("[bench] all_pass={0}/{1} pass_rate={2:.0%} wall={3:.1f}s".format(
        report["aggregate"]["all_pass"], report["aggregate"]["total"],
        report["aggregate"]["pass_rate"], report["aggregate"]["elapsed"]))
    print("[bench] report: {0}".format(report["_paths"]["md"]))
    for task in report["tasks"]:
        print("  {0:<20} rag={1:<4} exec={2:<4} exit={3:<3} wall={4:.2f}s".format(
            task["id"],
            "PASS" if task["rag"]["ok"] else "FAIL",
            "PASS" if task["exec"]["ok"] else "FAIL",
            task["exec"]["exit"],
            task["exec"].get("wall", task["exec"]["elapsed"])))


def main(argv=None):
    _utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="bench.py",
        description="内部执行 benchmark：RAG 命中 + 候选 bapi 脚本执行")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="列出任务")
    p_list.add_argument("--tasks", default=DEFAULT_TASKS)

    p_run = sub.add_parser("run", help="跑全部/单个任务")
    p_run.add_argument("--tasks", default=DEFAULT_TASKS)
    p_run.add_argument("--task", action="append", default=[],
                       help="只跑指定 id；可重复")
    p_run.add_argument("--candidate-dir",
                       help="候选目录（文件名=<id>.py）；缺省用 tasks.json 的 candidate")
    p_run.add_argument("--timeout", type=float, help="覆盖每个任务的超时秒数")
    p_run.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="跑 cube_bevel 做真实验证")

    args = parser.parse_args(argv)
    if args.cmd == "list":
        for task in load_tasks(args.tasks):
            print("{0:<20} {1}".format(task["id"], task["title"]))
        return 0
    if args.cmd == "run":
        tasks = load_tasks(args.tasks)
        if args.task:
            wanted = set(args.task)
            tasks = [t for t in tasks if t["id"] in wanted]
            if not tasks:
                print("[bench] 没有匹配的任务：{0}".format(args.task), file=sys.stderr)
                return 2
        candidate_dir = None
        if args.candidate_dir:
            candidate_dir = args.candidate_dir
            if not os.path.isabs(candidate_dir):
                candidate_dir = os.path.join(ROOT, candidate_dir)
        report = run_all(tasks, candidate_dir=candidate_dir, timeout=args.timeout)
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            _print_report(report)
        return 0 if report["aggregate"]["all_pass"] == report["aggregate"]["total"] else 1
    if args.cmd == "selftest":
        return selftest()
    return 2


if __name__ == "__main__":
    sys.exit(main())
