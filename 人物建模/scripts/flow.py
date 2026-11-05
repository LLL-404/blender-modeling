# -*- coding: utf-8 -*-
"""工序闸门：把「一个部位一个部位做，过闸才往下」变成能执行的流程。

为什么有这支脚本（2026-11-04 第二次根因复盘）
--------------------------------------------
上一轮的问题是**流程**，不是参数：

| 旧流程 | 后果 |
|---|---|
| `build.py all` 一口气建完 6 步，最后才 `measure` / `check` / `visual_gate` | 建到第 4 步方向错了，前 3 步的工全废 |
| 判据是「有没有」不是「像不像」 | 71 PASS / 0 FAIL 与「一顶灯罩」同时成立 |
| A2、C 两个探针零判定（PASS=0 SKIP=14 / SKIP=35） | 被当成 PASS 混进合计 |
| `spec/deliver.json` 手写「脸型、五眼、发型轮廓」 | 这三项从来没被量过 |

本脚本换成**部位闸门**：每个部位 = 构建 + 探针 + 图像指标 + 人眼复核。
四样都过才叫 PASS；任一项没有判定 = FAIL；证据比源码旧 = STALE。
`deliver.py` 只认这里的结论。

用法（在 人物建模/ 下）
--------------------
    python scripts/flow.py status              # 看每个部位过没过（不跑任何构建）
    python scripts/flow.py status --write      # 同时写 out/flow/summary.json（交付闸门读）
    python scripts/flow.py run body            # 建 body + 跑它的探针 + 判闸门
    python scripts/flow.py run all             # 按工序顺序推进，第一个没过就停
    python scripts/flow.py check body          # 不重建，只按现有产物和日志重判
    python scripts/flow.py review body         # 打印该部位的复核清单与现有签收状态

退出码：0 全过 / 1 有 FAIL / 3 等人眼复核 / 2 配置或环境错误。

复核文件（人眼签收，写在 `out/flow/<部位>/review.json`）
----------------------------------------------------
    {
      "part": "hair",
      "at": "2026-11-04T23:59:00",
      "images": ["out/m4_face_front.png", "..."],
      "items": [
        {"text": "<与 spec/parts.json 的 review 条目逐字一致>",
         "verdict": "PASS",
         "note": "看到什么：中分缝在正中，额头露出约 1/3，发梢到下颌"}
      ]
    }

`at` 必须晚于证据图；`images` 必须覆盖该部位全部证据图；`items` 必须一条不少。
少一条就按「没看」处理，不是「默认通过」。
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bpyrun  # noqa: E402  D12：Blender 定位单源

SPEC = os.path.join(ROOT, "spec", "parts.json")
VG_SPEC = os.path.join(ROOT, "spec", "visual_gate.json")
DELIVER_SPEC = os.path.join(ROOT, "spec", "deliver.json")
OUT = os.path.join(ROOT, "out", "flow")
SUMMARY = os.path.join(OUT, "summary.json")
MTIME_TOL = 2.0          # 文件系统时间戳容差（秒）
# 闸门规则版本：改了判定逻辑就 +1，旧记录自动作废。
# 不直接用 flow.py 的 mtime —— 改注释/打印也会让 6 个部位全部重跑，太吵。
GATE_VERSION = 3          # v3：新增「改模型前先过手册」闸门（manual_gate.verify）

_FAIL_RE = re.compile(r"\bFAIL\b")
_PASS_RE = re.compile(r"\bPASS\b")
_OK_RE = re.compile(r"\bOK\b")
_SUMMARY_RE = re.compile(r"\bPASS\s*=|\bFAIL\s*=")
_TRACEBACK = "Traceback (most recent call last)"


# ---------------------------------------------------------------- 基础
def _load(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _mtime(rel):
    p = os.path.join(ROOT, rel)
    if os.path.isdir(p):
        best = 0.0
        for base, _dirs, names in os.walk(p):
            for n in names:
                try:
                    best = max(best, os.path.getmtime(os.path.join(base, n)))
                except OSError:
                    pass
        return best
    try:
        return os.path.getmtime(p)
    except OSError:
        return 0.0


def _newest(rels):
    return max((_mtime(r) for r in rels), default=0.0)


def _fmt_time(ts):
    return time.strftime("%m-%d %H:%M", time.localtime(ts)) if ts else "—"


def _part_hash(part):
    """本部位工序定义的指纹：只改别的部位，不会让这个部位的记录作废。"""
    raw = json.dumps(part, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:12]


def _dw(s):
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in str(s))


def _pad(s, n):
    s = str(s)
    return s + " " * max(0, n - _dw(s))


def _rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def _blender():
    return bpyrun.blender_exe(bpyrun.BLENDER_ENV, bpyrun.DEFAULT_BLENDER)


def _run_stream(cmd, log_path, label):
    """跑命令，输出边打印边落 log；返回 (退出码, 全文, 耗时)。"""
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    t0 = time.monotonic()
    chunks = []
    print("  $ " + " ".join(cmd))
    try:
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                encoding="utf-8", errors="replace", bufsize=1)
        assert proc.stdout is not None
        for line in proc.stdout:
            chunks.append(line)
            sys.stdout.write("  | " + line if not line.endswith("\n") else "  | " + line)
        code = proc.wait()
    except OSError as exc:
        chunks.append("启动失败：{0!r}\n".format(exc))
        code = 2
    text = "".join(chunks)
    with open(log_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    elapsed = time.monotonic() - t0
    print("  -> %s exit=%d %.1fs  log=%s" % (label, code, elapsed, _rel(log_path)))
    return code, text, elapsed


def _classify(line):
    """探针行归类：FAIL / PASS / None。

    含 `PASS=` / `FAIL=` 的行是探针自己的汇总，不重复计数。
    """
    if _SUMMARY_RE.search(line):
        return None
    if _FAIL_RE.search(line):
        return "FAIL"
    if _PASS_RE.search(line) or _OK_RE.search(line):
        return "PASS"
    return None


def _probe_rows(text):
    rows = []
    for lineno, line in enumerate(text.splitlines(), 1):
        kind = _classify(line)
        if kind:
            rows.append({"lineno": lineno, "text": line.strip(), "verdict": kind})
    return rows


def _decision_detail(probe, n_total):
    """判定条数必须精确对上工序表；下限只能防全空，防不了探针悄悄缩水。

    v1 用 min_pass（下限）：A1 实判 18 条却只要求 ≥15，少判 3 条照样绿。
    v2 改 exact_decisions：原始 PASS+FAIL 行数（例外过滤前）必须**等于**登记值；
    探针加一条或删一条判据都要同步改 spec/parts.json，否则直接红。
    """
    exp = probe.get("exact_decisions")
    if exp is None:
        return "探针没登记 exact_decisions，工序表缺判据条数 —— 拒绝判 PASS"
    if n_total != int(exp):
        return ("判定条数 %d ≠ 登记 %d（探针加/删判据要同步改 "
                "spec/parts.json 的 exact_decisions）" % (n_total, int(exp)))
    return None


# ---------------------------------------------------------------- 闸门项
def _exception_hit(text, exceptions, today=None):
    """返回命中的例外 dict；过期例外不算命中。"""
    today = today or time.strftime("%Y-%m-%d")
    for ex in exceptions or []:
        if ex.get("contains", "") not in text:
            continue
        exp = ex.get("expires")
        if exp and today > exp:
            return {"expired": exp, "ex": ex}
        return ex
    return None


def _probe_gate(part, probe, build_log):
    """跑一个探针并判定。返回 (row, log_path)。"""
    log = os.path.join(OUT, part["id"], "probe_%s.log" % probe["id"])
    blender = _blender()
    if blender is None:
        return {"kind": "probe", "id": probe["id"], "label": probe["label"],
                "verdict": "FAIL", "detail": "找不到 Blender"}, log
    path = os.path.join(ROOT, probe["script"])
    if not os.path.isfile(path):
        return {"kind": "probe", "id": probe["id"], "label": probe["label"],
                "verdict": "FAIL", "detail": "脚本不存在：%s" % probe["script"]}, log
    code, text, _ = _run_stream(
        [blender, "-b", "--factory-startup", "--python-exit-code", "1",
         "--python", path], log, "probe:" + probe["id"])
    rows = _probe_rows(text)
    n_total = len(rows)          # 例外过滤前的原始判定条数
    decision_problem = _decision_detail(probe, n_total)
    n_pass = sum(r["verdict"] == "PASS" for r in rows)
    n_fail = sum(r["verdict"] == "FAIL" for r in rows)
    crash = code != 0 or _TRACEBACK in text

    excused, expired = [], []
    if n_fail:
        keep = []
        for r in rows:
            if r["verdict"] != "FAIL":
                keep.append(r)
                continue
            hit = _exception_hit(r["text"], probe.get("exceptions"))
            if isinstance(hit, dict) and "expired" in hit:
                expired.append(r["text"])
                keep.append(r)
            elif hit:
                excused.append(r["text"])
            else:
                keep.append(r)
        rows = keep
        n_fail = sum(r["verdict"] == "FAIL" for r in rows)

    if crash:
        verdict, detail = "FAIL", "崩溃（exit=%d）" % code
    elif n_pass == 0 and n_fail == 0:
        verdict, detail = "FAIL", "零判定（PASS=0 FAIL=0）——探针没在判，等同于没过"
    elif n_fail:
        verdict, detail = "FAIL", "%d PASS / %d FAIL" % (n_pass, n_fail)
    elif decision_problem:
        verdict, detail = "FAIL", decision_problem
    else:
        verdict, detail = "PASS", "%d PASS / 0 FAIL" % n_pass
    if excused:
        detail += " · %d 条已知例外" % len(excused)
    if expired:
        detail += " · %d 条例外已过期" % len(expired)

    fails = [r["text"] for r in rows if r["verdict"] == "FAIL"]
    return ({"kind": "probe", "id": probe["id"], "label": probe["label"],
             "verdict": verdict, "detail": detail, "log": _rel(log),
             "pass": n_pass, "fail": n_fail, "fails": fails,
             "excused": excused, "expired": expired}, log)


def _metric_gate(part, m):
    """图像指标：基线来自参考图，阈值来自 spec/visual_gate.json。"""
    import visual_gate as vg
    cfg = _load(VG_SPEC)
    base = cfg.get("baseline") or {}
    lim = cfg["limits"]
    img = os.path.join(ROOT, m["image"])
    if not os.path.isfile(img):
        return {"kind": "metric", "id": m["id"], "label": m["label"],
                "verdict": "FAIL", "detail": "证据图不存在：%s" % m["image"]}
    try:
        f, _diag = vg.features(img)
    except Exception as exc:
        return {"kind": "metric", "id": m["id"], "label": m["label"],
                "verdict": "FAIL", "detail": "算不出来：%s" % exc}
    got = float(f[m["key"]])
    ref = float(base.get(m["key"], 0.0))
    if m.get("mode") == "observe" or ref <= 0:
        return {"kind": "metric", "id": m["id"], "label": m["label"],
                "verdict": "OBSERVE", "got": round(got, 4), "ref": round(ref, 4),
                "detail": "观察项 %.4f（参考 %.4f），不拦" % (got, ref)}
    if m["mode"] == "min":
        bound = ref * lim["lower_ratio"]
        ok = got >= bound
        rule = "≥ %.4f（参考 %.4f × %.2f）" % (bound, ref, lim["lower_ratio"])
    else:
        ratio = m.get("ratio", lim["stripe_max_ratio"])
        bound = ref * ratio
        ok = got <= bound
        rule = "≤ %.4f（参考 %.4f × %.2f）" % (bound, ref, ratio)
    return {"kind": "metric", "id": m["id"], "label": m["label"],
            "verdict": "PASS" if ok else "FAIL",
            "got": round(got, 4), "ref": round(ref, 4), "bound": round(bound, 4),
            "detail": "实测 %.4f，要求 %s" % (got, rule)}


def _artifact_gate(part, item):
    """复用 deliver.py 的解析器，保证交付闸门与工序闸门同一口径。"""
    import deliver
    path = os.path.join(ROOT, item["path"])
    if not os.path.isfile(path):
        return {"kind": "artifact", "id": item["id"], "label": item["label"],
                "verdict": "FAIL", "detail": "产物不存在：%s" % item["path"]}
    dep = part.get("depends_on") or []
    newest_dep = _newest(dep)
    if newest_dep and os.path.getmtime(path) < newest_dep - MTIME_TOL:
        return {"kind": "artifact", "id": item["id"], "label": item["label"],
                "verdict": "STALE",
                "detail": "产物比依赖旧（%s，产物 %s）"
                          % ("、".join(dep), _fmt_time(os.path.getmtime(path)))}
    try:
        if item["parser"] == "views":
            gate = _load(DELIVER_SPEC)["views_gate"]
            detail, fails, meta = deliver.parse_views(path, gate)
        else:
            detail, fails, meta = deliver.PARSERS[item["parser"]](path)
    except Exception as exc:
        return {"kind": "artifact", "id": item["id"], "label": item["label"],
                "verdict": "FAIL", "detail": "解析失败：%s" % exc}
    ok = int(meta.get("blocking", 1)) <= 0
    return {"kind": "artifact", "id": item["id"], "label": item["label"],
            "verdict": "PASS" if ok else "FAIL", "detail": detail,
            "fails": fails, "artifact": item["path"]}


def _review_state(part, evidence):
    """返回 (state, at, items, problems)。state ∈ OK / MISSING / STALE / BAD。"""
    path = os.path.join(OUT, part["id"], "review.json")
    if not os.path.isfile(path):
        return "MISSING", 0.0, [], ["没有复核文件 out/flow/%s/review.json" % part["id"]]
    try:
        doc = _load(path)
    except Exception as exc:
        return "BAD", 0.0, [], ["复核文件读不了：%s" % exc]

    problems = []
    if doc.get("part") != part["id"]:
        problems.append("part 写成 %r，应为 %r" % (doc.get("part"), part["id"]))
    at_raw = doc.get("at", "")
    try:
        at = time.mktime(time.strptime(at_raw, "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        at, problems = 0.0, problems + ["at 不是 YYYY-MM-DDTHH:MM:SS：%r" % at_raw]

    items = doc.get("items") or []
    want = part.get("review") or []
    if len(items) != len(want):
        problems.append("复核条目 %d 条，清单要求 %d 条" % (len(items), len(want)))
    for i, text in enumerate(want):
        if i >= len(items):
            break
        got = items[i]
        if got.get("text") != text:
            problems.append("第 %d 条文字与清单不一致" % (i + 1))
        if got.get("verdict") not in ("PASS", "FAIL"):
            problems.append("第 %d 条没有 PASS/FAIL" % (i + 1))
        if not str(got.get("note", "")).strip():
            problems.append("第 %d 条没写看到什么" % (i + 1))

    imgs = doc.get("images") or []
    missing = [e for e in evidence if e not in imgs]
    if missing:
        problems.append("复核没覆盖证据图：%s" % "、".join(missing))

    newest = _newest(evidence)
    if at and at < newest - MTIME_TOL:
        problems.append("复核时间早于最新证据图（%s < %s）" % (_fmt_time(at), _fmt_time(newest)))
        return "STALE", at, items, problems
    if problems:
        return "BAD", at, items, problems
    return "OK", at, items, problems


def _review_rows(part, evidence):
    state, at, items, problems = _review_state(part, evidence)
    rows = []
    if state != "OK":
        rows.append({"kind": "review", "id": "review", "label": "人眼复核",
                     "verdict": "FAIL" if state in ("BAD",) else "MISSING",
                     "detail": "；".join(problems) if problems else state})
        return rows, state, at
    for i, item in enumerate(items):
        rows.append({"kind": "review", "id": "review.%d" % (i + 1),
                     "label": "复核 %d" % (i + 1),
                     "verdict": item["verdict"],
                     "detail": item.get("note", "")[:80]})
    return rows, state, at


def _calibration_gate():
    """视觉基线必须经 calibrate_guard.py 自检，且参考图/校准时间没变。

    v1 缺陷：`--calibrate` 直接覆盖基线，门槛会自动变松（换银发图后脸密度
    基线掉 44%），流程不要求任何人证明判据还有判别力。
    """
    import hashlib

    def bad(detail):
        return {"kind": "calibration", "id": "calibration", "label": "基线自检",
                "verdict": "FAIL", "detail": detail}

    try:
        cfg = _load(VG_SPEC)
    except Exception as exc:
        return bad("读不了 spec/visual_gate.json：%s" % exc)
    guard = os.path.join(OUT, "calibrate_guard.json")
    if not os.path.isfile(guard):
        return bad("缺自检记录，先跑 python scripts/calibrate_guard.py --verify")
    try:
        g = _load(guard)
    except Exception as exc:
        return bad("自检记录读不了：%s" % exc)
    if g.get("selftest") != "PASS":
        return bad("自检记录里 selftest 不是 PASS")
    if g.get("calibrated_at") != cfg.get("_calibrated_at"):
        return bad("基线重算过但没重跑自检（%s → %s）"
                   % (g.get("calibrated_at"), cfg.get("_calibrated_at")))
    if g.get("reference_image") != cfg.get("reference_image"):
        return bad("参考图路径换了但没重跑 --calibrate")
    ref = os.path.join(ROOT, cfg.get("reference_image", ""))
    if not os.path.isfile(ref):
        return bad("参考图不存在：%s" % cfg.get("reference_image"))
    md5 = hashlib.md5(open(ref, "rb").read()).hexdigest()
    if g.get("reference_md5") != md5:
        return bad("参考图内容变了但没重跑 --calibrate")
    return {"kind": "calibration", "id": "calibration", "label": "基线自检",
            "verdict": "PASS", "detail": "参考图与基线均已自检（%s）" % g.get("at")}


def _manual_gate(part):
    """BOSS 2026-11-05 定的硬规则：改模型前先过一遍 Blender 技术手册。

    查证记录 `out/flow/<部位>/manual_review.json` 由 `scripts/manual_gate.py` 校验：
    检索词 ≥2、手册页 ≥2 且路径真实存在、结论 ≥20 字、时间晚于源码改动。
    """
    import manual_gate
    ok, detail = manual_gate.verify(part["id"], part.get("sources") or [])
    return {"kind": "manual", "id": "manual", "label": "手册查证",
            "verdict": "PASS" if ok else "FAIL", "detail": detail}


# ---------------------------------------------------------------- 评估
def evaluate(part, do_build=False, do_probes=False):
    """按工序表判一个部位。do_build 先建，do_probes 先跑探针。"""
    os.makedirs(os.path.join(OUT, part["id"]), exist_ok=True)
    src_max = _newest(part.get("sources") or [])
    evidence = list(part.get("evidence") or [])
    rows = []
    logs = []

    # 手册闸门放在所有构建之前：不过就 FAIL 且**不执行任何 builds**。
    gate = _manual_gate(part)
    rows.append(gate)
    if do_build and gate["verdict"] != "PASS":
        rows.append({"kind": "build", "id": "build", "label": "构建",
                     "verdict": "FAIL",
                     "detail": "手册闸门未过，未执行任何构建（避免白改）"})
        return _record(part, rows, src_max, evidence, logs)

    if do_build:
        for i, cmd in enumerate(part.get("builds") or []):
            log = os.path.join(OUT, part["id"], "build_%d.log" % (i + 1))
            code, _text, _el = _run_stream([sys.executable] + cmd, log, "build%d" % (i + 1))
            logs.append(_rel(log))
            if code != 0:
                rows.append({"kind": "build", "id": "build", "label": "构建",
                             "verdict": "FAIL", "detail": "退出码 %d，见 %s" % (code, _rel(log))})
                return _record(part, rows, src_max, evidence, logs)

    if do_build or do_probes:
        for cmd in part.get("producers") or []:
            log = os.path.join(OUT, part["id"], "producer_%s.log" %
                               os.path.splitext(os.path.basename(cmd[0]))[0])
            t_start = time.time()
            code, _text, _el = _run_stream([sys.executable] + cmd, log, "producer")
            logs.append(_rel(log))
            if code != 0:
                # 产物脚本（measure / visual_gate）用退出码表达「判定失败」，
                # 不是「没生成」。只要它把产物写新了，就记观察行，结论交给产物闸门，
                # 否则同一件事会被算两次失败。
                arts = [os.path.join(ROOT, a["path"]) for a in part.get("artifacts") or []]
                refreshed = any(os.path.isfile(p) and os.path.getmtime(p) > t_start - 1.0
                                for p in arts)
                rows.append({"kind": "producer", "id": "producer", "label": "产物生成",
                             "verdict": "OBSERVE" if refreshed else "FAIL",
                             "detail": "退出码 %d%s，见 %s"
                                       % (code, "（判定失败，产物已更新）" if refreshed else "",
                                          _rel(log))})
        for probe in part.get("probes") or []:
            row, log = _probe_gate(part, probe, None)
            rows.append(row)
            logs.append(_rel(log))

    # 不重建时：探针日志必须存在且比源码新，否则 STALE
    if not (do_build or do_probes) and part.get("probes"):
        for probe in part["probes"]:
            log = os.path.join(OUT, part["id"], "probe_%s.log" % probe["id"])
            if not os.path.isfile(log):
                rows.append({"kind": "probe", "id": probe["id"], "label": probe["label"],
                             "verdict": "STALE", "detail": "没有探针日志，先跑 run"})
            elif os.path.getmtime(log) < src_max - MTIME_TOL:
                rows.append({"kind": "probe", "id": probe["id"], "label": probe["label"],
                             "verdict": "STALE", "detail": "探针日志比源码旧，先跑 run"})
            else:
                text = open(log, encoding="utf-8", errors="replace").read()
                rows.append(_probe_row_from_log(part, probe, text, log))

    for item in part.get("artifacts") or []:
        rows.append(_artifact_gate(part, item))

    # 参考图基线是全项目共用的前提，每个部位都验一次：换图/重算基线后，
    # 不该出现「某个部位还拿旧基线判过了」。
    rows.append(_calibration_gate())

    for m in part.get("metrics") or []:
        rows.append(_metric_gate(part, m))

    review_rows, review_state, review_at = _review_rows(part, evidence)
    rows.extend(review_rows)

    return _record(part, rows, src_max, evidence, logs,
                   review_state=review_state, review_at=review_at)


def _probe_row_from_log(part, probe, text, log):
    """check 模式：用已有日志重算判定（不重跑探针）。"""
    rows = _probe_rows(text)
    n_total = len(rows)          # 例外过滤前的原始判定条数
    decision_problem = _decision_detail(probe, n_total)
    n_pass = sum(r["verdict"] == "PASS" for r in rows)
    n_fail = sum(r["verdict"] == "FAIL" for r in rows)
    excused, kept = [], []
    for r in rows:
        if r["verdict"] == "FAIL":
            hit = _exception_hit(r["text"], probe.get("exceptions"))
            if isinstance(hit, dict) and "expired" in hit:
                kept.append(r)
            elif hit:
                excused.append(r["text"])
            else:
                kept.append(r)
        else:
            kept.append(r)
    n_fail = sum(r["verdict"] == "FAIL" for r in kept)
    if n_pass == 0 and n_fail == 0:
        verdict, detail = "FAIL", "零判定（PASS=0 FAIL=0）"
    elif n_fail:
        verdict, detail = "FAIL", "%d PASS / %d FAIL" % (n_pass, n_fail)
    elif decision_problem:
        verdict, detail = "FAIL", decision_problem
    else:
        verdict, detail = "PASS", "%d PASS / 0 FAIL" % n_pass
    if excused:
        detail += " · %d 条已知例外" % len(excused)
    return {"kind": "probe", "id": probe["id"], "label": probe["label"],
            "verdict": verdict, "detail": detail, "log": _rel(log),
            "pass": n_pass, "fail": n_fail,
            "fails": [r["text"] for r in kept if r["verdict"] == "FAIL"],
            "excused": excused}


def _record(part, rows, src_max, evidence, logs, review_state="MISSING", review_at=0.0):
    blocking = [r for r in rows if r["verdict"] == "FAIL"]
    stale = [r for r in rows if r["verdict"] == "STALE"]
    missing = [r for r in rows if r["verdict"] == "MISSING"]
    if blocking:
        verdict = "FAIL"
    elif stale:
        verdict = "STALE"
    elif missing or review_state in ("MISSING", "STALE", "BAD"):
        verdict = "NEEDS-REVIEW"
    elif not any(r["verdict"] in ("PASS", "FAIL") for r in rows):
        verdict = "FAIL"
        blocking = [{"label": "闸门", "detail": "一条判定都没有"}]
    else:
        verdict = "PASS"
    rec = {
        "part": part["id"], "label": part["label"], "why": part.get("why", ""),        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "generated_ts": time.time(),
        "gate_version": GATE_VERSION,
        "part_hash": _part_hash(part),
        "verdict": verdict,
        "rows": rows, "blocking": blocking, "logs": logs,
        "sources_max": src_max, "sources_max_h": _fmt_time(src_max),
        "evidence": [{"path": e, "mtime": _mtime(e), "exists": os.path.isfile(os.path.join(ROOT, e))}
                     for e in evidence],
        "review": {"state": review_state, "at": review_at},
        "counts": {
            # 探针按它内部的判定条数计，其他闸门按行计；否则「A2 3P/2F + C 4P/4F」
            # 在表里只会显示成「0P/2F」，看不出判了多少条。
            "PASS": sum((r.get("pass", 0) if r.get("kind") == "probe"
                         else int(r.get("verdict") == "PASS")) for r in rows),
            "FAIL": sum((r.get("fail", 0) if r.get("kind") == "probe"
                         else int(r.get("verdict") == "FAIL")) for r in rows),
            "OBSERVE": sum(r.get("verdict") == "OBSERVE" for r in rows)},
    }
    path = os.path.join(OUT, part["id"] + ".json")
    os.makedirs(OUT, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=2)
    return rec


# ---------------------------------------------------------------- 状态
def _stale_reason(part, rec):
    """记录之后源码或证据又变过 → 过期。"""
    if not rec:
        return "未跑"
    src_now = _newest(part.get("sources") or [])
    rec_ts = float(rec.get("generated_ts", 0))
    if src_now > rec_ts + MTIME_TOL:
        return "源码比闸门新（%s）" % _fmt_time(src_now)
    if int(rec.get("gate_version", GATE_VERSION)) != GATE_VERSION:
        return "闸门规则版本变了（记录 v%s → 当前 v%s）" % (
            rec.get("gate_version"), GATE_VERSION)
    if rec.get("part_hash") != _part_hash(part):
        return "本部位工序定义变了"
    for rel in part.get("gate_files") or []:
        t = _mtime(rel)
        if t > rec_ts + MTIME_TOL:
            return "判据文件比记录新（%s）" % rel
    new_ev = [e for e in rec.get("evidence", [])
              if e.get("exists") and e.get("mtime", 0) > rec_ts + MTIME_TOL]
    if new_ev:
        return "证据比闸门新（%s）" % new_ev[0]["path"]
    if not all(e.get("exists") for e in rec.get("evidence", [])):
        miss = [e["path"] for e in rec.get("evidence", []) if not e.get("exists")]
        return "证据缺失（%s）" % "、".join(miss)
    return ""


def load_records(spec):
    out = {}
    for part in spec["parts"]:
        path = os.path.join(OUT, part["id"] + ".json")
        if os.path.isfile(path):
            try:
                out[part["id"]] = _load(path)
            except Exception:
                out[part["id"]] = None
        else:
            out[part["id"]] = None
    return out


def status(spec, write=False):
    recs = load_records(spec)
    rows = []
    order_ok = True
    for part in spec["parts"]:
        rec = recs.get(part["id"])
        stale = _stale_reason(part, rec)
        verdict = rec["verdict"] if rec else "NOT-RUN"
        if stale:
            verdict = "STALE" if verdict in ("PASS", "FAIL", "NEEDS-REVIEW") else verdict
        up_ok = order_ok
        if verdict != "PASS":
            order_ok = False
        rows.append({"id": part["id"], "label": part["label"], "verdict": verdict,
                     "stale": stale, "order_ok": up_ok,
                     "record": rec})

    print()
    print(_pad("部位", 16) + _pad("状态", 14) + _pad("闸门", 22) + "说明")
    print("-" * 96)
    for r in rows:
        rec = r["record"]
        counts = rec["counts"] if rec else {"PASS": 0, "FAIL": 0, "OBSERVE": 0}
        gate = "%dP/%dF/%d观" % (counts["PASS"], counts["FAIL"], counts["OBSERVE"]) if rec else "—"
        note = r["stale"] or (rec["generated"] if rec else "还没跑过这一步")
        if not r["stale"] and rec and rec["verdict"] == "STALE":
            for row in rec.get("rows", []):
                if row.get("verdict") == "STALE":
                    note = row.get("detail") or "产物过期"
                    break
        if r["verdict"] == "PASS" and not r["order_ok"]:
            note = "本部位过闸，但上游未过 —— 不能交付"
        print(_pad(r["label"], 16) + _pad(r["verdict"], 14) + _pad(gate, 22) + str(note)[:60])
    print()

    bad = [r for r in rows if r["verdict"] != "PASS"]
    if bad:
        print("卡住的地方：")
        for r in bad:
            if r["record"]:
                shown = False
                for b in r["record"].get("blocking", [])[:3]:
                    fails = (b.get("fails") or [])[:3]
                    for detail in (fails or [b.get("detail", "")]):
                        print("  · %s：%s" % (r["label"], str(detail)[:110]))
                        shown = True
                if not shown:
                    for b in r["record"].get("rows", [])[:3]:
                        if b.get("verdict") in ("FAIL", "STALE", "MISSING"):
                            print("  · %s：%s" % (r["label"], str(b.get("detail", ""))[:110]))
                            shown = True
                if not shown:
                    print("  · %s：%s" % (r["label"], r["record"]["verdict"]))
            else:
                print("  · %s：还没跑 → python scripts/flow.py run %s" % (r["label"], r["id"]))
        print()

    overall = "PASS" if all(r["verdict"] == "PASS" for r in rows) else "FAIL"
    print("[flow] 工序总判定：%s（%d/%d 部位过闸）"
          % (overall, sum(r["verdict"] == "PASS" for r in rows), len(rows)))

    summary = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "verdict": overall,
               "parts": [{k: r[k] for k in ("id", "label", "verdict", "stale", "order_ok")}
                         | {"counts": (r["record"] or {}).get("counts", {})}
                         for r in rows]}
    if write:
        os.makedirs(OUT, exist_ok=True)
        with open(SUMMARY, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, ensure_ascii=False, indent=2)
        print("[flow] 汇总 -> %s" % _rel(SUMMARY))
    return 0 if overall == "PASS" else 1, summary


# ---------------------------------------------------------------- 复核
def print_review_template(part):
    path = os.path.join(OUT, part["id"], "review.json")
    state, at, items, problems = _review_state(part, part.get("evidence") or [])
    print()
    print("部位：%s（%s）" % (part["label"], part["id"]))
    print("证据图：")
    for e in part.get("evidence") or []:
        print("  %-40s %s" % (e, _fmt_time(_mtime(e))))
    print()
    print("复核清单（逐条看图，写 PASS/FAIL + 看到什么）：")
    for i, text in enumerate(part.get("review") or []):
        got = items[i].get("verdict") if i < len(items) else "未答"
        print("  %d. [%s] %s" % (i + 1, got, text))
    print()
    print("现有复核：%s%s" % (state, ("；" + "；".join(problems)) if problems else ""))
    print("文件位置：%s" % _rel(path))
    print()
    print("模板：")
    tpl = {"part": part["id"], "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "images": list(part.get("evidence") or []),
           "items": [{"text": t, "verdict": "PASS", "note": "看到什么"} for t in part.get("review") or []]}
    print(json.dumps(tpl, ensure_ascii=False, indent=2))
    return 0


# ---------------------------------------------------------------- 主流程
def main(argv=None):
    bpyrun.utf8_stdio()
    ap = argparse.ArgumentParser(prog="flow.py")
    ap.add_argument("cmd", choices=["status", "run", "check", "review"])
    ap.add_argument("part", nargs="?")
    ap.add_argument("--write", action="store_true", help="status 时写 out/flow/summary.json")
    a = ap.parse_args(argv)

    if not os.path.isfile(SPEC):
        print("[flow] 缺少工序表：%s" % SPEC, file=sys.stderr)
        return 2
    spec = _load(SPEC)
    parts = spec["parts"]
    by_id = {p["id"]: p for p in parts}

    if a.cmd == "status":
        code, _ = status(spec, write=a.write)
        return code

    if a.cmd == "review":
        if a.part not in by_id:
            print("[flow] 部位只能是：%s" % "、".join(by_id), file=sys.stderr)
            return 2
        return print_review_template(by_id[a.part])

    if a.part not in by_id and a.part != "all":
        print("[flow] 部位只能是：%s 或 all" % "、".join(by_id), file=sys.stderr)
        return 2

    todo = parts if a.part == "all" else [by_id[a.part]]
    # run all：已过闸且源码/判据/证据/复核都新鲜的部位不重建。
    # 否则每跑一次都把证据图刷新成比 review.json 新，复核永远「早于证据」，
    # 多部位连续推进会卡死在第一个部位（v1 缺陷）。
    recs = load_records(spec) if (a.part == "all" and a.cmd == "run") else {}
    last = 0
    for part in todo:
        if a.part == "all" and a.cmd == "run":
            old = recs.get(part["id"])
            fresh = (old and old.get("verdict") == "PASS"
                     and not _stale_reason(part, old)
                     and _review_state(part, part.get("evidence") or [])[0] == "OK")
            if fresh:
                print()
                print("[flow] ======== %s（%s）========" % (part["label"], part["id"]))
                print("[flow] %s -> SKIP（已过闸且新鲜：%s）" % (part["id"], old["generated"]))
                last = 0
                continue
        print()
        print("[flow] ======== %s（%s）========" % (part["label"], part["id"]))
        if a.cmd == "run":
            rec = evaluate(part, do_build=True, do_probes=True)
        else:
            rec = evaluate(part, do_build=False, do_probes=False)
        print("[flow] %s -> %s（%s）"
              % (part["id"], rec["verdict"],
                 "  ".join("%s=%s" % (r["label"], r["verdict"]) for r in rec["rows"])))
        if rec["verdict"] != "PASS":
            for b in rec["blocking"][:6]:
                print("  · %s：%s" % (b.get("label"), str(b.get("detail"))[:110]))
            if rec["verdict"] == "NEEDS-REVIEW":
                print("  · 去看图，然后写 out/flow/%s/review.json（模板：python scripts/flow.py review %s）"
                      % (part["id"], part["id"]))
            last = 3 if rec["verdict"] == "NEEDS-REVIEW" else 1
            break
        last = 0

    status(spec, write=True)
    return last


if __name__ == "__main__":
    sys.exit(main())
