# -*- coding: utf-8 -*-
"""一键自检：依次跑 6 个探针，把 PASS/FAIL 汇总到 opt/logs/check_report.md。

用法（在项目根 `实用工具/Blender建模/人物建模/` 下）：

    python scripts/check.py
    python scripts/build.py check          # 等价转调

口径（重要，别改坏）：
  · 每行只按**探针自己打印的显式标记**归类，不做语义猜测：
      含 `FAIL`                    -> FAIL
      含 `PASS` 或 `OK`            -> PASS  （_stageA/a4_fit_probe.py、_stageD/d_probe.py 用 OK 当通过标记）
      只有 [probe]/[bprobe]/[cprobe]/[dprobe] 的信息行 -> SKIP（只记录，不判定）
  · 探针崩溃（退出码非 0 或输出含 Traceback）单独记 CRASH，**不计入 PASS/FAIL/SKIP**。
  · 行号 = 该探针 stdout 的第 N 行；完整输出落在 opt/logs/probe_<脚本名>.log，便于回查源码位置。
  · Blender 缺失或 6 个探针脚本一个都不存在时，直接报错退出（退出码 2），不假装通过。
"""
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_BLENDER = r"D:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
BLENDER_ENV = "BLENDER_EXE"

# 探针清单：(短名, 相对路径, 覆盖什么)
PROBES = (
    ("A1 手/脚趾", "_stageA/a1_hand_probe.py", "腕部台阶、每指末 5mm 分量、脚底落地、脚趾分量"),
    ("A2 面部/头身比", "_stageA/a2_face_probe.py", "鼻尖前伸、嘴宽、耳高、面中法线、头身比"),
    ("A4 服装净空", "_stageA/a4_fit_probe.py", "衬衫三带净空、袖口间隙/边界边、呆毛环宽、裙腰四段"),
    ("B 骨架/权重", "_stageB/b_probe.py", "骨骼数、分带权重、左右串权、Hands 绑定、屈指边长比"),
    ("C 三渲二", "_stageC/c_probe.py", "描边宽度、皮肤色阶分位、面部阴影、头发高光/轮廓光"),
    ("D 发型服装细节", "_stageD/d_probe.py", "刘海分组、后发束、翻领、袖口卷边、裙褶相位"),
)

MARKER_TOKENS = ("PASS", "FAIL", "[probe]", "[bprobe]", "[cprobe]", "[dprobe]")
LOG_DIR = os.path.join(ROOT, "opt", "logs")
REPORT_PATH = os.path.join(LOG_DIR, "check_report.md")

_FAIL_RE = re.compile(r"\bFAIL\b")
_PASS_RE = re.compile(r"\bPASS\b")
_OK_RE = re.compile(r"\bOK\b")
_TRACEBACK = "Traceback (most recent call last)"


def _blender():
    path = os.environ.get(BLENDER_ENV) or DEFAULT_BLENDER
    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(path):
        print("[check] 错误：找不到 Blender：", file=sys.stderr)
        print("        " + path, file=sys.stderr)
        print("        请安装 Blender 5.2，或设置环境变量 {0}。".format(BLENDER_ENV), file=sys.stderr)
        return None
    return path


def _classify(line):
    """按探针自己的显式标记归类：FAIL / PASS / SKIP。"""
    if _FAIL_RE.search(line):
        return "FAIL"
    if _PASS_RE.search(line) or _OK_RE.search(line):
        return "PASS"
    return "SKIP"


def _extract(stdout):
    """抽取带标记的行，返回 [(行号, 原文, 归类)]。"""
    rows = []
    for lineno, line in enumerate(stdout.splitlines(), 1):
        text = line.rstrip()
        if any(token in text for token in MARKER_TOKENS):
            rows.append((lineno, text, _classify(text)))
    return rows


def _run_probe(blender, path):
    """跑一个探针，返回 (退出码, stdout, 耗时秒)。"""
    t0 = time.monotonic()
    cmd = [blender, "-b", "--factory-startup", "--python-exit-code", "1", "--python", path]
    try:
        proc = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
        code, out = proc.returncode, proc.stdout or ""
    except OSError as exc:
        code, out = 2, "启动 Blender 失败：{0!r}".format(exc)
    return code, out, time.monotonic() - t0


def _write_report(rows, blender):
    """把结果写成 Markdown 表；目录不存在时自动创建（opt/logs 不入库）。"""
    os.makedirs(LOG_DIR, exist_ok=True)
    lines = [
        "# 探针自检报告",
        "",
        "- 生成时间：{0}".format(time.strftime("%Y-%m-%d %H:%M:%S")),
        "- Blender：`{0}`".format(blender),
        "- 项目根：`{0}`".format(ROOT),
        "- 判定口径：含 `FAIL` -> FAIL；含 `PASS` 或 `OK` -> PASS（A4/D 两个探针用 `OK` 当通过标记）；",
        "  只有 `[probe]/[bprobe]/[cprobe]/[dprobe]` 的信息行 -> SKIP。",
        "  崩溃（退出码非 0 或含 Traceback）单独记 CRASH，不计入 PASS/FAIL/SKIP。",
        "  行号 = 该探针 stdout 的第 N 行，完整输出在 `opt/logs/probe_<脚本名>.log`。",
        "",
        "## 汇总",
        "",
        "| 探针 | 状态 | exit | 耗时 | PASS | FAIL | SKIP |",
        "|---|---|---|---|---|---|---|",
    ]
    total = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    for item in rows:
        if item["status"] == "MISSING":
            lines.append("| {0} | MISSING | - | - | - | - | - |".format(item["name"]))
            continue
        if item["status"] != "CRASH":
            for key in total:
                total[key] += item["counts"][key]
        lines.append("| {0} | {1} | {2} | {3:.1f}s | {4} | {5} | {6} |".format(
            item["name"], item["status"], item["exit"], item["elapsed"],
            item["counts"]["PASS"], item["counts"]["FAIL"], item["counts"]["SKIP"]))
    lines.append("| **合计** |  |  |  | **{0}** | **{1}** | **{2}** |".format(
        total["PASS"], total["FAIL"], total["SKIP"]))
    lines.append("")

    fails = [(item, r) for item in rows for r in item["rows"] if r[2] == "FAIL"]
    lines.append("## FAIL 明细")
    lines.append("")
    if not fails:
        lines.append("无。")
    else:
        lines.append("| 探针 | stdout 行号 | 原文 |")
        lines.append("|---|---|---|")
        for item, (lineno, text, _kind) in fails:
            lines.append("| {0} | {1} | `{2}` |".format(item["name"], lineno, text.replace("|", "\\|")))
    lines.append("")

    crashes = [item for item in rows if item["status"] == "CRASH"]
    lines.append("## CRASH 明细")
    lines.append("")
    if not crashes:
        lines.append("无。")
    else:
        for item in crashes:
            lines.append("### {0}（exit={1}，{2}）".format(item["name"], item["exit"], item["path"]))
            lines.append("")
            tail = item["stdout"].strip().splitlines()[-8:]
            lines.append("```")
            lines.extend(tail)
            lines.append("```")
            lines.append("")

    missing = [item for item in rows if item["status"] == "MISSING"]
    if missing:
        lines.append("## MISSING 明细（脚本不存在，未运行）")
        lines.append("")
        for item in missing:
            lines.append("- `{0}`".format(item["path"]))
        lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        f.write("\n")
    return total


def main():
    blender = _blender()
    if blender is None:
        return 2

    existing = [p for _n, p, _d in PROBES if os.path.exists(os.path.join(ROOT, p))]
    if not existing:
        print("[check] 错误：6 个探针脚本一个都不存在，项目结构不完整：", file=sys.stderr)
        for _name, path, _desc in PROBES:
            print("        " + path, file=sys.stderr)
        return 2

    os.makedirs(LOG_DIR, exist_ok=True)
    rows = []
    print("[check] root={0}".format(ROOT))
    print("[check] blender={0}".format(blender))
    for name, rel, desc in PROBES:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            print("[check] {0}: MISSING ({1})".format(name, rel))
            rows.append({"name": name, "path": rel, "status": "MISSING",
                         "exit": None, "elapsed": 0.0, "stdout": "",
                         "rows": [], "counts": {"PASS": 0, "FAIL": 0, "SKIP": 0}})
            continue

        print("[check] ---- {0}: {1} ----".format(name, desc))
        code, out, elapsed = _run_probe(blender, path)
        log_path = os.path.join(LOG_DIR, "probe_{0}.log".format(os.path.splitext(os.path.basename(rel))[0]))
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(out)

        crash = code != 0 or _TRACEBACK in out
        extracted = _extract(out)
        counts = {"PASS": 0, "FAIL": 0, "SKIP": 0}
        for _lineno, _text, kind in extracted:
            counts[kind] += 1
        status = "CRASH" if crash else "OK"
        rows.append({"name": name, "path": rel, "status": status, "exit": code,
                     "elapsed": elapsed, "stdout": out, "rows": extracted, "counts": counts})
        print("[check] {0}: exit={1} {2} PASS={3} FAIL={4} SKIP={5} {6:.1f}s -> {7}".format(
            name, code, status, counts["PASS"], counts["FAIL"], counts["SKIP"], elapsed,
            os.path.basename(log_path)))

    total = _write_report(rows, blender)

    crash_count = sum(1 for item in rows if item["status"] == "CRASH")
    missing_count = sum(1 for item in rows if item["status"] == "MISSING")
    print("[check] PASS={0} FAIL={1} SKIP={2} CRASH={3} MISSING={4}".format(
        total["PASS"], total["FAIL"], total["SKIP"], crash_count, missing_count))
    fails = [(item["name"], r[0], r[1]) for item in rows for r in item["rows"] if r[2] == "FAIL"]
    if fails:
        print("[check] FAIL 明细：")
        for name, lineno, text in fails:
            print("  {0} 行 {1}: {2}".format(name, lineno, text))
    if crash_count:
        print("[check] CRASH 明细：")
        for item in rows:
            if item["status"] == "CRASH":
                print("  {0}（exit={1}）日志 {2}".format(
                    item["name"], item["exit"], os.path.join("opt", "logs",
                    "probe_{0}.log".format(os.path.splitext(os.path.basename(item["path"]))[0]))))
    print("[check] 报告 -> {0}".format(REPORT_PATH))

    if total["FAIL"] or crash_count or missing_count:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())