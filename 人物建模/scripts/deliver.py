# -*- coding: utf-8 -*-
"""交付闸门：把四套已有判据汇成一句「现在能不能交付」。

背景
----
到 2026-11-03 为止，项目里有四个判据入口，各自出各自的报告：

| 入口 | 产物 | 判什么 |
|---|---|---|
| `build.py measure` | `out/appearance_report.json` | 14 条宏观比例（**不判像不像**） |
| `scripts/visual_gate.py` | `out/visual_gate.json` | 画面信息密度对参考图的下限 |
| `build.py asset` | `out/m6_16_stats.json` | 16 机位渲染有没有硬伤 |
| `scripts/audit.py` | `out/audit.json` | 能不能进引擎 |
| `build.py check` | `opt/logs/check_report.md` | 绑定有没有坏 |

没有任何一个回答「**现在能不能交付**」。这个脚本就是那一声回答：
两个目标（进游戏 / 进作品集，BOSS 2026-11-03 定）各自全过才算可交付。

它**不重新测量**任何东西 —— 只读已有产物、判新鲜度、套已知例外、给结论。
所以它跑一次是毫秒级；产物本身过期了它会明确说「重跑哪条命令」。

用法
----
    python scripts/deliver.py                # 判两个目标
    python scripts/deliver.py --profile game # 只判进游戏
    python scripts/deliver.py --run          # 产物缺失/过期时自动重跑对应命令
    python scripts/deliver.py --json

退出码：0 两个目标都过 / 1 有目标未过或产物过期 / 2 配置或环境不对。
"""
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bpyrun  # noqa: E402  D12：utf8_stdio 单一来源

SPEC = os.path.join(ROOT, "spec", "deliver.json")
OUT_DIR = os.path.join(ROOT, "out")
REPORT_MD = os.path.join(OUT_DIR, "deliver_report.md")
REPORT_JSON = os.path.join(OUT_DIR, "deliver.json")

PROFILE_LABEL = {"game": "进游戏", "portfolio": "进作品集"}


# ---------------------------------------------------------------- 产物解析
# 每个 parse_* 返回 (ok, detail, fails)，fails 是「具体哪几条没过」的字符串列表。

def parse_appearance(path):
    d = json.load(open(path, encoding="utf-8"))
    s = d.get("summary", {})
    fail, missing = s.get("fail", 0), s.get("missing", 0)
    fails = ["%s（%s）" % (r.get("label", r.get("key")), r.get("key"))
             for r in d.get("rows", []) if r.get("verdict") == "FAIL"]
    detail = "%d PASS / %d WARN / %d FAIL" % (
        s.get("pass", 0), s.get("warn", 0), fail)
    if missing:
        detail += " / %d 缺失" % missing
    return detail, fails, {"blocking": fail + missing, "extra": 0}


def parse_asset(path):
    d = json.load(open(path, encoding="utf-8"))
    c = d.get("counts", {})
    fails = ["%s：实测 %s，要求 %s" % (x["label"], x["value"], x["target"])
             for x in d.get("checks", []) if x.get("status") == "FAIL"]
    return ("PASS %d / WARN %d / FAIL %d"
            % (c.get("PASS", 0), c.get("WARN", 0), c.get("FAIL", 0)),
            fails, {"blocking": c.get("FAIL", 0), "extra": 0})


_SUM_RE = re.compile(r"\|\s*\*\*合计\*\*\s*\|"      # | **合计** |  |  |  | **71** | **1** | **125** |
                     r"(?:[^|]*\|){3}\s*\*\*(\d+)\*\*\s*\|"
                     r"\s*\*\*(\d+)\*\*\s*\|")
_DETAIL_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*`(.+?)`\s*\|\s*$", re.M)


def parse_rig(path):
    """解析 check.py 的 markdown 报告：合计行 + FAIL 明细 + CRASH + 验收覆盖空洞。

    2026-11-04 根因复盘：A2 面部/头身比与 C 三渲二两个探针是纯信息探针，
    实测 PASS=0 SKIP=14 / PASS=0 SKIP=35，一条判定都没有。原版只读
    PASS/FAIL/CRASH，于是合计里的「71 PASS」把这两个空洞盖得严严实实。
    这里不把它们算成 FAIL（设计如此，不是回归），但必须在结论里点名，
    不许再出现「脸和渲染观感从来没被判过，却报全绿」的假象。
    """
    txt = open(path, encoding="utf-8").read()
    m = _SUM_RE.search(txt)
    if not m:
        return "报告里找不到合计行（格式变了？）", ["解析失败"], {"blocking": 1, "extra": 0}
    n_pass, n_fail = int(m.group(1)), int(m.group(2))
    fails = [raw.strip() for _probe, _line, raw in _DETAIL_RE.findall(txt)]
    crash = 0
    seg = txt.split("## CRASH 明细")
    if len(seg) > 1:
        body = seg[1].strip()
        if body and not body.lstrip().startswith("无"):
            rows = [x for x in body.splitlines() if x.startswith("|")]
            crash = max(0, len(rows) - 2)      # 去掉表头与分隔行

    holes = []
    for line in txt.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 7 or cells[0].startswith("**"):
            continue
        try:
            p, f, s = int(cells[4]), int(cells[5]), int(cells[6])
        except ValueError:
            continue        # 表头 / 分隔行
        if p == 0 and f == 0 and s > 0:
            holes.append(cells[0])
    detail = "PASS %d / FAIL %d / CRASH %d" % (n_pass, n_fail, crash)
    if holes:
        detail += " · 零判定探针 %d 个（%s）" % (len(holes), "、".join(holes))
    return detail, fails, {"blocking": n_fail, "extra": crash}


def parse_views(path, gate):
    d = json.load(open(path, encoding="utf-8"))
    before, after = d.get("before", []), d.get("after", [])
    if not before or len(before) != len(after):
        return ("机位数对不上（before=%d after=%d）" % (len(before), len(after)),
                ["数据不完整"], {"blocking": 1, "extra": 0})
    fails = []
    for i, (b, a) in enumerate(zip(before, after)):
        if a.get("cov", 0) <= gate["cov_min"]:
            fails.append("机位 %02d 覆盖率 %.4f ≤ %.2f（空图？）" % (i, a.get("cov", 0), gate["cov_min"]))
        if a.get("dark", 0) > gate["dark_max"]:
            fails.append("机位 %02d 暗部占比 %.3f > %.2f" % (i, a["dark"], gate["dark_max"]))
        if a.get("black", 0) > gate["black_max"]:
            fails.append("机位 %02d 纯黑占比 %.3f > %.2f" % (i, a["black"], gate["black_max"]))
        dlt = abs(b.get("cov", 0) - a.get("cov", 0))
        if dlt > gate["cov_delta_max"]:
            fails.append("机位 %02d 去描边前后覆盖率差 %.4f > %.2f" % (i, dlt, gate["cov_delta_max"]))
    worst = max(abs(b.get("cov", 0) - a.get("cov", 0)) for b, a in zip(before, after))
    return ("%d 机位，最大覆盖率差 %.4f" % (len(after), worst), fails,
            {"blocking": len(fails), "extra": 0})


def parse_visual(path):
    """视觉闸门：参考图 vs 固定正面渲染的画面信息密度下限。"""
    d = json.load(open(path, encoding="utf-8"))
    s = d.get("summary", {})
    fails = ["%s：实测 %.4f，要求 %s" % (r["label"], r["got"], r["rule"])
             for r in d.get("rows", []) if r.get("verdict") == "FAIL"]
    blocking = len(fails)
    drift = float(d.get("baseline_drift", 0))
    if drift > 0.02:
        fails.append("参考图与基线对不上（漂移 %.4f > 0.02），换图后要重跑 --calibrate" % drift)
        blocking += 1
    detail = "对参考图 PASS %d / FAIL %d" % (s.get("pass", 0), s.get("fail", 0))
    return detail, fails, {"blocking": blocking, "extra": 0}


PARSERS = {"appearance": parse_appearance, "asset": parse_asset,
           "rig": parse_rig, "visual": parse_visual}


# ---------------------------------------------------------------- 主流程

def _dw(s):
    """显示宽度：中日韩全角字符算 2 列，否则表格对不齐。"""
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in s)


def _pad(s, n):
    return s + " " * max(0, n - _dw(str(s)))


def _clean(rows):
    """去掉内部字段，给 JSON 用。"""
    return [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]


def main(argv):
    bpyrun.utf8_stdio()
    if not os.path.exists(SPEC):
        print("[deliver] 缺少配置：%s" % SPEC, file=sys.stderr)
        return 2
    cfg = json.load(open(SPEC, encoding="utf-8"))

    only = None
    if "--profile" in argv:
        i = argv.index("--profile")
        only = argv[i + 1] if i + 1 < len(argv) else None
        if only not in (None, "game", "portfolio", "both"):
            print("[deliver] --profile 只能是 game / portfolio / both", file=sys.stderr)
            return 2
    do_run = "--run" in argv
    as_json = "--json" in argv

    root_file = os.path.join(ROOT, cfg["source_root"])
    root_mtime = os.path.getmtime(root_file) if os.path.exists(root_file) else 0

    results = []
    for src in cfg["sources"]:
        art = os.path.join(ROOT, src["artifact"])
        row = {"id": src["id"], "label": src["label"], "why": src.get("why", ""),
               "artifact": src["artifact"], "producer": src["producer"],
               "profiles": src["profiles"], "ok": False, "detail": "",
               "fails": [], "stale": False, "missing": not os.path.exists(art),
               "_meta": {"blocking": 0, "extra": 0}, "_excused": 0}
        if row["missing"]:
            row["detail"] = "产物不存在"
            row["_meta"] = {"blocking": 1, "extra": 0}
        else:
            row["stale"] = os.path.getmtime(art) < root_mtime - 1
            try:
                if src["id"] == "views":
                    detail, fails, meta = parse_views(art, cfg["views_gate"])
                else:
                    detail, fails, meta = PARSERS[src["id"]](art)
            except Exception as e:                      # 产物坏掉也要说清楚，别崩
                detail, fails, meta = ("解析失败：%s" % e, ["产物无法解析"],
                                       {"blocking": 1, "extra": 0})
            row.update(detail=detail, fails=fails, _meta=meta)
        results.append(row)

    # 套已知例外：只在 FAIL 明细里按子串匹配，匹配到就摘掉并标为豁免
    excused = []
    for ex in cfg.get("known_exceptions", []):
        for row in results:
            if row["id"] != ex["source"]:
                continue
            hit = [f for f in row["fails"] if ex["contains"] in f]
            if hit:
                row["fails"] = [f for f in row["fails"] if f not in hit]
                row["_excused"] += len(hit)
                excused.append({"source": ex["source"], "hit": hit,
                                "reason": ex.get("reason", ""), "todo": ex.get("todo", "")})

    # 状态必须在豁免**之后**算：先算会留下「FAIL 被摘掉了、状态还红着」的自相矛盾
    # （第一次跑就是这个 bug，绑定那条豁免了却仍判 FAIL）。
    for row in results:
        m = row["_meta"]
        row["ok"] = (m["blocking"] - row["_excused"] <= 0) and m["extra"] == 0

    # --run：按 sources 数组顺序补缺失/过期的，跑完重新收集
    if do_run:
        todo = [r for r in results if r["missing"] or r["stale"]]
        if todo:
            for r in todo:
                cmd = [sys.executable] + r["producer"]
                print("[deliver] 重跑 %-12s %s" % (r["id"], " ".join(r["producer"])),
                      file=sys.stderr)
                t0 = time.time()
                p = subprocess.run(cmd, cwd=ROOT)
                print("[deliver]   exit=%d %.1fs" % (p.returncode, time.time() - t0),
                      file=sys.stderr)
            return main([a for a in argv if a != "--run"])   # 重跑后重新判一次

    # 目标判定：该目标下的所有来源都要 ok 且不 stale
    profiles = ["game", "portfolio"]
    if only in ("game", "portfolio"):
        profiles = [only]
    verdict = {}
    for prof in profiles:
        rows = [r for r in results if prof in r["profiles"]]
        good = all(r["ok"] and not r["stale"] and not r["missing"] for r in rows)
        verdict[prof] = {"ok": good,
                         "rows": [r["id"] for r in rows if not (r["ok"] and not r["stale"])]}

    # 输出
    if as_json:
        print(json.dumps({"generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                          "verdict": verdict, "sources": _clean(results),
                          "excused": excused},
                         ensure_ascii=False, indent=2))
        return 0 if all(v["ok"] for v in verdict.values()) else 1

    print()
    print(_pad("产物", 32) + _pad("状态", 10) + _pad("结论", 36) + "用途")
    print("-" * 118)
    for r in results:
        if r["missing"]:
            st, note = "MISSING", "产物不存在"
        elif r["stale"]:
            st, note = "STALE", "比 %s 旧，已过期" % cfg["source_root"]
        else:
            st, note = ("PASS" if r["ok"] else "FAIL"), r["detail"]
        print(_pad(r["label"], 32) + _pad(st, 10) + _pad(note, 36) + (r["why"] or ""))
    print()
    for prof in profiles:
        v = verdict[prof]
        print("  %-10s %s" % (PROFILE_LABEL[prof], "可以交付" if v["ok"] else "还不行"))
    print()

    bad = [r for r in results if not r["ok"] or r["stale"] or r["missing"]]
    if bad:
        print("卡住的地方：")
        for r in bad:
            if r["missing"] or r["stale"]:
                print("  · %s：%s → 跑 `python %s`"
                      % (r["label"], "产物缺失" if r["missing"] else "产物过期",
                         " ".join(r["producer"])))
            else:
                for f in r["fails"][:6]:
                    print("  · %s：%s" % (r["label"], f))
                if len(r["fails"]) > 6:
                    print("  · …… 以及 %d 条，详见 %s" % (len(r["fails"]) - 6, r["artifact"]))
        print()
    if excused:
        print("已知例外（不算失败，但要知道）：")
        for e in excused:
            print("  · [%s] %s" % (e["source"], e["hit"][0][:88]))
            print("    %s" % e["reason"])
            if e["todo"]:
                print("    待办：%s" % e["todo"])
        print()

    write_report(results, verdict, excused, profiles, cfg)
    print("[deliver] 报告 out/deliver_report.md   数据 out/deliver.json")
    return 0 if all(v["ok"] for v in verdict.values()) else 1


def write_report(results, verdict, excused, profiles, cfg):
    n_ok = sum(1 for r in results if r["ok"] and not r["stale"] and not r["missing"])
    lines = [
        "# 交付闸门",
        "",
        "| 项 | 值 |",
        "|---|---|",
        "| 生成时间 | %s |" % time.strftime("%Y-%m-%d %H:%M:%S"),
        "| 两个目标 | %s |" % "、".join("%s **%s**" % (PROFILE_LABEL[p],
                                                     "可以交付" if verdict[p]["ok"] else "还不行")
                                        for p in profiles),
        "| 通过的产物 | %d / %d |" % (n_ok, len(results)),
        "",
        "判定规则：某个目标下的**全部**来源都要 PASS 且产物不旧于 `%s`。" % cfg["source_root"],
        "",
        "## 产物",
        "",
        "| 状态 | 产物 | 结论 | 用途 | 重跑命令 |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        if r["missing"]:
            st = "MISSING"
        elif r["stale"]:
            st = "STALE"
        else:
            st = "PASS" if r["ok"] else "FAIL"
        lines.append("| %s | %s | %s | %s | `python %s` |"
                     % (st, r["label"], r["detail"], r["why"],
                        " ".join(r["producer"])))
    bad = [r for r in results if not r["ok"] or r["stale"] or r["missing"]]
    lines += ["", "## 卡住的地方", ""]
    if not bad:
        lines.append("无。两个目标都可以交付。")
    else:
        for r in bad:
            if r["missing"] or r["stale"]:
                lines.append("- **%s**：%s，跑 `python %s`"
                             % (r["label"], "产物缺失" if r["missing"] else "产物过期",
                                " ".join(r["producer"])))
            else:
                lines.append("- **%s**（%d 条）：" % (r["label"], len(r["fails"])))
                for f in r["fails"]:
                    lines.append("  - %s" % f)
    lines += ["", "## 已知例外", ""]
    if not excused:
        lines.append("无。")
    for e in excused:
        lines.append("- `%s`：%s" % (e["source"], e["hit"][0]))
        lines.append("  - 为什么不算失败：%s" % e["reason"])
        if e["todo"]:
            lines.append("  - 待办：%s" % e["todo"])
    lines.append("")
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump({"generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "verdict": verdict, "sources": _clean(results),
                   "excused": excused},
                  f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
