# -*- coding: utf-8 -*-
"""执行候选 bapi 脚本并给结构化结果（纯标准库，不 import bpy）。

定位：`rag.py` 给上下文、agent 写候选代码，`run_bapi.py` 负责**真的跑一遍**：
headless Blender + `--factory-startup` + `--python-exit-code 1`，捕获退出码/耗时/
stdout/stderr，再检查期望文件与期望文本。它是候选代码的执行门，不是 LLM。

用法（在 `人物建模/` 下执行）：

    python scripts/run_bapi.py out/candidate.py
    python scripts/run_bapi.py out/candidate.py --json
    python scripts/run_bapi.py out/candidate.py --expect-file out/demo.png
    python scripts/run_bapi.py out/candidate.py --expect-text "[demo]" --timeout 120
    python scripts/run_bapi.py --selftest

安全边界：候选脚本是**可执行代码**，本脚本不做 OS 级沙箱；只允许候选文件位于
`人物建模/` 内，且默认要求放在 `out/`（`--allow-any` 才放行其它目录）。
期望文件只读检查，不写盘。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                       # 人物建模/

import bpyrun  # noqa: E402  （同目录，Blender 定位单源）


def _utf8_stdio():
    bpyrun.utf8_stdio()


def _resolve_candidate(path, allow_any=False):
    if not isinstance(path, str) or not path:
        raise ValueError("候选脚本路径必须是非空字符串")
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    real = os.path.realpath(p)
    root = os.path.realpath(ROOT)
    if os.path.normcase(os.path.commonpath([root, real])) != os.path.normcase(root):
        raise ValueError("候选脚本必须位于 人物建模/ 内：" + path)
    out = os.path.join(root, "out")
    if not allow_any and os.path.normcase(os.path.commonpath([out, real])) != os.path.normcase(out):
        raise ValueError("候选脚本默认必须放在 人物建模/out/ 下（或加 --allow-any）：" + path)
    if not os.path.isfile(real):
        raise ValueError("候选脚本不存在：" + real)
    return real


def _resolve_expect(path):
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    return os.path.realpath(p)


def _tail(text, lines=40):
    text = (text or "").rstrip()
    if not text:
        return ""
    parts = text.splitlines()
    return "\n".join(parts[-lines:])


def _check_files(paths):
    out = []
    ok = True
    for raw in paths or []:
        path = _resolve_expect(raw)
        exists = os.path.isfile(path)
        size = os.path.getsize(path) if exists else 0
        good = exists and size > 0
        ok = ok and good
        out.append({"path": path, "exists": exists, "bytes": size, "ok": good})
    return ok, out


def _check_text(text, needles):
    missing = [needle for needle in (needles or []) if needle not in text]
    return not missing, missing


def run_candidate(candidate, timeout=120, expect_files=None, expect_text=None,
                  allow_any=False, tail=40, blender=None):
    """跑一个候选脚本，返回结构化结果；不抛异常（路径错误除外）。"""
    real = _resolve_candidate(candidate, allow_any=allow_any)
    blender = blender or bpyrun.blender_exe(bpyrun.BLENDER_ENV, bpyrun.DEFAULT_BLENDER)
    if not blender:
        return {
            "ok": False, "exit": 2, "elapsed": 0.0, "candidate": real,
            "blender": None, "timed_out": False,
            "stdout_tail": "", "stderr_tail": "",
            "files": [], "missing_text": [],
            "error": "找不到 Blender（设 BLENDER_EXE）",
        }

    cmd = [blender, "-b", "--factory-startup", "--python-exit-code", "1",
           "--python", real]
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    t0 = time.monotonic()
    timed_out = False
    try:
        proc = subprocess.run(
            cmd, cwd=ROOT, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout)
        code = proc.returncode
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        code = 124
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        stderr += "\n[run_bapi] 超时 {0}s，已终止".format(timeout)
    except OSError as exc:
        code = 2
        stdout = ""
        stderr = "[run_bapi] 启动失败：{0!r}".format(exc)
    elapsed = time.monotonic() - t0

    files_ok, files = _check_files(expect_files)
    combined = stdout + "\n" + stderr
    text_ok, missing = _check_text(combined, expect_text)
    ok = (code == 0) and files_ok and text_ok and not timed_out
    return {
        "ok": ok,
        "exit": code,
        "elapsed": round(elapsed, 3),
        "candidate": real,
        "blender": blender,
        "timed_out": timed_out,
        "stdout_tail": _tail(stdout, tail),
        "stderr_tail": _tail(stderr, tail),
        "files": files,
        "missing_text": missing,
        "error": "" if code != 2 else "启动失败/路径错误",
    }


def _print_result(result, tail=40):
    print("[run_bapi] candidate={0}".format(result["candidate"]))
    print("[run_bapi] blender={0}".format(result.get("blender")))
    print("[run_bapi] exit={0} elapsed={1:.1f}s ok={2}{3}".format(
        result["exit"], result["elapsed"], result["ok"],
        " TIMEOUT" if result["timed_out"] else ""))
    if result["files"]:
        print("[run_bapi] files:")
        for item in result["files"]:
            print("  {0} {1} bytes={2} {3}".format(
                "PASS" if item["ok"] else "FAIL", item["path"], item["bytes"],
                "missing" if not item["exists"] else ""))
    if result["missing_text"]:
        print("[run_bapi] 缺少期望文本：")
        for needle in result["missing_text"]:
            print("  - {0!r}".format(needle))
    if result["stdout_tail"]:
        print("[run_bapi] stdout (tail):")
        print(result["stdout_tail"])
    if result["stderr_tail"]:
        print("[run_bapi] stderr (tail):")
        print(result["stderr_tail"])


def selftest():
    out_root = os.path.join(ROOT, "out")
    os.makedirs(out_root, exist_ok=True)
    passed = 0
    failed = 0
    with tempfile.TemporaryDirectory(dir=out_root) as td:
        good = os.path.join(td, "good.py")
        with open(good, "w", encoding="utf-8", newline="\n") as f:
            f.write(
                "import os\n"
                "print('[selftest-good] hello')\n"
                "open(os.path.join(os.path.dirname(__file__), 'good.txt'), 'w').write('ok')\n")
        result = run_candidate(
            good, timeout=60,
            expect_files=[os.path.join(td, "good.txt")],
            expect_text=["[selftest-good]"])
        if result["ok"]:
            print("[selftest] PASS good candidate")
            passed += 1
        else:
            print("[selftest] FAIL good candidate: exit={0} files={1} missing={2}".format(
                result["exit"], result["files"], result["missing_text"]))
            failed += 1

        bad = os.path.join(td, "bad.py")
        with open(bad, "w", encoding="utf-8", newline="\n") as f:
            f.write("import sys\nprint('[selftest-bad]')\nsys.exit(3)\n")
        result = run_candidate(bad, timeout=60, expect_text=["[selftest-bad]"])
        if (not result["ok"]) and result["exit"] != 0:
            print("[selftest] PASS bad candidate rejected (exit={0})".format(result["exit"]))
            passed += 1
        else:
            print("[selftest] FAIL bad candidate was not rejected: {0}".format(result))
            failed += 1

        # 纯文件检查：期望文件不存在必须 FAIL，不额外启动 Blender。
        ok, files = _check_files([os.path.join(td, "missing.png")])
        if (not ok) and files and not files[0]["exists"]:
            print("[selftest] PASS missing expected file rejected")
            passed += 1
        else:
            print("[selftest] FAIL missing expected file check: {0}".format(files))
            failed += 1

    print("[selftest] PASS={0} FAIL={1}".format(passed, failed))
    return 0 if failed == 0 else 1


def main(argv=None):
    _utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="run_bapi.py",
        description="headless 执行候选 bapi 脚本并检查退出码/文件/文本")
    parser.add_argument("candidate", nargs="?", help="候选脚本路径（默认要求 out/ 下）")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--expect-file", action="append", default=[],
                        help="期望存在且非空的文件；可重复")
    parser.add_argument("--expect-text", action="append", default=[],
                        help="期望出现在 stdout/stderr 的文本；可重复")
    parser.add_argument("--allow-any", action="store_true",
                        help="允许候选脚本位于 out/ 之外（仍在 人物建模/ 内）")
    parser.add_argument("--tail", type=int, default=40)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.candidate:
        parser.error("需要候选脚本路径（或 --selftest）")

    try:
        result = run_candidate(
            args.candidate, timeout=args.timeout,
            expect_files=args.expect_file, expect_text=args.expect_text,
            allow_any=args.allow_any, tail=args.tail)
    except ValueError as exc:
        print("[run_bapi] 错误：{0}".format(exc), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_result(result, args.tail)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
