# -*- coding: utf-8 -*-
"""校准守护：换参考图 / 重算基线后，必须先证明判据还有判别力。

为什么要有这个入口（2026-11-05 换靶复盘）
----------------------------------------
`visual_gate.py --calibrate` 会直接覆盖基线，没有任何东西要求证明新基线
还分得开「参考图」和「抹平细节的退化图」。这次换银发概念图，脸密度基线
0.1325 → 0.0746（降 44%）、条纹 0.0768 → 0.1778，门槛自动变松。
判据没坏（手动 --selftest 能分开），但流程不拦，下次未必有人手动验。

用法（项目根下）
--------------
    python scripts/calibrate_guard.py --calibrate   # 换参考图：备份 -> 重算基线 -> 自检 -> 不过就回滚
    python scripts/calibrate_guard.py --verify      # 不写 spec，只验现有基线并登记

成功后写 `out/flow/calibrate_guard.json`；`flow.py` 的校准闸门会检查这份记录。
**不要直接跑 visual_gate.py --calibrate**，那条路径绕过了自检。
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPEC = os.path.join(ROOT, "spec", "visual_gate.json")
GUARD = os.path.join(ROOT, "out", "flow", "calibrate_guard.json")
VG = os.path.join(HERE, "visual_gate.py")


def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _run(flag):
    p = subprocess.run([sys.executable, VG, flag], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    tail = (p.stdout or "").strip().splitlines()[-8:]
    for line in tail:
        print("  " + line)
    if p.returncode != 0 and (p.stderr or "").strip():
        print("  [stderr] " + (p.stderr or "").strip().splitlines()[-1])
    return p.returncode


def _record(mode, cfg):
    ref = os.path.join(ROOT, cfg.get("reference_image", ""))
    doc = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "mode": mode,
        "calibrated_at": cfg.get("_calibrated_at"),
        "reference_image": cfg.get("reference_image"),
        "reference_md5": _md5(ref) if os.path.isfile(ref) else None,
        "baseline": cfg.get("baseline"),
        "selftest": "PASS",
        "note": "由 calibrate_guard.py 写入；基线或参考图一变就过期",
    }
    os.makedirs(os.path.dirname(GUARD), exist_ok=True)
    with open(GUARD, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
    print("[guard] 自检记录 -> %s" % os.path.relpath(GUARD, ROOT))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="calibrate_guard.py")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--calibrate", action="store_true", help="重算基线并自检，失败回滚")
    g.add_argument("--verify", action="store_true", help="只验证现有基线，不写 spec")
    a = ap.parse_args(argv)

    if not os.path.isfile(SPEC):
        print("[guard] 缺少 %s" % SPEC, file=sys.stderr)
        return 2
    backup = open(SPEC, "rb").read()

    if a.calibrate:
        print("[guard] 1/2 重算基线")
        if _run("--calibrate") != 0:
            open(SPEC, "wb").write(backup)
            print("[guard] 校准失败，已回滚 spec/visual_gate.json")
            return 1
    else:
        print("[guard] 1/2 沿用现有基线（--verify 不写 spec）")

    print("[guard] 2/2 负控制自检")
    if _run("--selftest") != 0:
        if a.calibrate:
            open(SPEC, "wb").write(backup)
            print("[guard] 判据失效，基线已回滚；先修判据再校准")
        else:
            print("[guard] 判据失效，现有基线不可用")
        return 1

    cfg = json.load(open(SPEC, encoding="utf-8"))
    _record("calibrate" if a.calibrate else "verify", cfg)
    print("[guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
