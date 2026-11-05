# -*- coding: utf-8 -*-
"""工序闸门自检：验证三条硬规则真的会拦，不是写在文档里。

    python scripts/selftest_flow.py

覆盖：
  1. exact_decisions 精确条数（少一条 / 多一条 / 没登记 都必须 FAIL）
  2. run all 跳过已 PASS 且新鲜的部位（v1 缺陷：每次都重建，复核永远追不上证据）
  3. 基线自检记录缺失 / 对不上时 FAIL，匹配时 PASS

用临时目录伪造一份「已过闸」的部位记录，不碰真实 out/flow。
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import time
from unittest.mock import patch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import flow  # noqa: E402


def _ok(cond, label, detail=""):
    print("  %-6s %s%s" % ("PASS" if cond else "FAIL", label,
                           (" — " + detail) if detail else ""))
    return 0 if cond else 1


def test_exact_decisions():
    print("[1] exact_decisions 精确条数")
    p = {"exact_decisions": 18}
    bad = 0
    bad += _ok(flow._decision_detail(p, 18) is None, "登记 18 / 实判 18 → 放行")
    bad += _ok(flow._decision_detail(p, 17) is not None, "少判 1 条 → FAIL",
               "v1 的 min_pass=15 在这里会误放行")
    bad += _ok(flow._decision_detail(p, 19) is not None, "多判 1 条 → FAIL",
               "加判据要同步改工序表")
    bad += _ok(flow._decision_detail({}, 18) is not None, "没登记 → FAIL")
    return bad


def test_run_all_skip():
    print("[2] run all 跳过已过闸且新鲜的部位")
    bad = 0
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "flow")
        os.makedirs(os.path.join(out, "a"), exist_ok=True)
        os.makedirs(os.path.join(out, "b"), exist_ok=True)

        part_a = {"id": "a", "label": "部位A", "sources": [], "evidence": [],
                  "review": [], "gate_files": [], "builds": [], "probes": [],
                  "metrics": []}
        part_b = dict(part_a, id="b", label="部位B")
        spec = {"parts": [part_a, part_b]}
        spec_path = os.path.join(tmp, "parts.json")
        with open(spec_path, "w", encoding="utf-8") as fh:
            json.dump(spec, fh, ensure_ascii=False)

        now = time.time()
        rec_a = {"part": "a", "label": "部位A", "verdict": "PASS",
                 "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
                 "generated_ts": now, "gate_version": flow.GATE_VERSION,
                 "part_hash": flow._part_hash(part_a), "evidence": [],
                 "rows": [], "blocking": [], "counts": {}}
        with open(os.path.join(out, "a.json"), "w", encoding="utf-8") as fh:
            json.dump(rec_a, fh, ensure_ascii=False)
        with open(os.path.join(out, "a", "review.json"), "w", encoding="utf-8") as fh:
            json.dump({"part": "a", "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                       "images": [], "items": []}, fh, ensure_ascii=False)

        passed = {"verdict": "PASS", "rows": [], "blocking": []}
        buf = io.StringIO()
        with patch.object(flow, "SPEC", spec_path), \
             patch.object(flow, "OUT", out), \
             patch.object(flow, "SUMMARY", os.path.join(out, "summary.json")), \
             patch.object(flow, "status", return_value=(0, {})), \
             patch.object(flow, "evaluate", return_value=passed) as ev, \
             contextlib.redirect_stdout(buf):
            code = flow.main(["run", "all"])
        text = buf.getvalue()
        bad += _ok(code == 0, "run all 正常结束", "exit=%d" % code)
        bad += _ok("a -> SKIP" in text, "部位A 打印 SKIP（没重建）")
        bad += _ok(ev.call_count == 1, "只评估了 1 个部位",
                   "实际 %d 次" % ev.call_count)
        if ev.call_args:
            bad += _ok(ev.call_args[0][0]["id"] == "b", "推进到了部位B",
                       "实际 %s" % ev.call_args[0][0]["id"])
        else:
            bad += _ok(False, "推进到了部位B", "没调用 evaluate")

        def run_twice():
            with patch.object(flow, "SPEC", spec_path), \
                 patch.object(flow, "OUT", out), \
                 patch.object(flow, "SUMMARY", os.path.join(out, "summary.json")), \
                 patch.object(flow, "status", return_value=(0, {})), \
                 patch.object(flow, "evaluate", return_value=passed) as evx, \
                 contextlib.redirect_stdout(io.StringIO()):
                flow.main(["run", "all"])
            return evx.call_count

        # 闸门规则版本变了 → 旧记录作废，不该跳过
        rec_a["gate_version"] = flow.GATE_VERSION - 1
        with open(os.path.join(out, "a.json"), "w", encoding="utf-8") as fh:
            json.dump(rec_a, fh, ensure_ascii=False)
        bad += _ok(run_twice() == 2, "闸门规则版本变了 → 两个部位都重判")

        # 复核文件没了 → 不该跳过
        rec_a["gate_version"] = flow.GATE_VERSION
        with open(os.path.join(out, "a.json"), "w", encoding="utf-8") as fh:
            json.dump(rec_a, fh, ensure_ascii=False)
        os.remove(os.path.join(out, "a", "review.json"))
        bad += _ok(run_twice() == 2, "复核缺失 → 两个部位都重判")
    return bad


def test_calibration():
    print("[3] 基线自检闸门")
    bad = 0
    real = flow._calibration_gate()
    bad += _ok(real["verdict"] == "PASS", "真实自检记录匹配 → PASS",
               real.get("detail", ""))
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(flow, "OUT", tmp):
            miss = flow._calibration_gate()
        bad += _ok(miss["verdict"] == "FAIL", "缺自检记录 → FAIL",
                   miss.get("detail", ""))
        guard = os.path.join(tmp, "calibrate_guard.json")
        cfg = json.load(open(flow.VG_SPEC, encoding="utf-8"))
        doc = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "mode": "verify",
               "calibrated_at": "2000-01-01 00:00:00",
               "reference_image": cfg.get("reference_image"),
               "reference_md5": "deadbeef", "selftest": "PASS"}
        json.dump(doc, open(guard, "w", encoding="utf-8"), ensure_ascii=False)
        with patch.object(flow, "OUT", tmp):
            stale = flow._calibration_gate()
        bad += _ok(stale["verdict"] == "FAIL", "校准时间/参考图对不上 → FAIL",
                   stale.get("detail", ""))
    return bad


def main():
    bad = test_exact_decisions() + test_run_all_skip() + test_calibration()
    print("[selftest] %s（%d 项不过）" % ("PASS" if bad == 0 else "FAIL", bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
