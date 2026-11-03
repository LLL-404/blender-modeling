# -*- coding: utf-8 -*-
"""brief -> profile 受控参数入口（纯标准库，不 import bpy）。

定位：把“已落成点路径的设计 brief”校验成 `params/profile.json` 的**受控补丁**，
而不是让模型直接写 bpy 代码。本脚本**不解析自然语言**：`brief` 字段只作记录，
真正要改什么由人或 LLM 先写进 `set`。它只做四件事：

1. 读 brief JSON（`set` 里是点路径 -> 新值）；
2. 按当前 profile 的键、类型、params/README.md 的建议范围做校验；
3. 打印「现值 / 新值 / 判定」差值表，并给出下一步验收命令；
4. `--apply` 才写盘，写前把原 profile 备份到 `out/brief/`，原子替换。

设计约束（与仓内其它脚本一致）：

* 缺省 dry-run，只有 `--apply` 落盘；
* 只允许写 `人物建模/` 内的 profile，路径越界直接拒绝；
* 不猜测语义：未知键、类型不符、超范围一律报错，不静默回退；
* 对「尚未接线」和「仅在 hair.style=long 生效」的键给 warning，
  避免改了没效果却被当成已生效（本仓的“假达标”纪律）。

用法（在 `人物建模/` 下执行）：

    python scripts/brief.py briefs/example.json
    python scripts/brief.py briefs/example.json --json
    python scripts/brief.py briefs/example.json --apply
    python scripts/brief.py --selftest

brief JSON 形状：

    {
      "brief": "7.5 头身、bob 短发、藏青裙的少女",
      "base": "params/profile.json",
      "set": {
        "appearance.height": 1.68,
        "appearance.head_to_body_ratio": 7.5,
        "hair.style": "bob",
        "outfit.skirt_length": 0.62
      }
    }

`base` 可省略，默认 `params/profile.json`；`--profile` 可临时覆盖。
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                  # 人物建模/
DEFAULT_PROFILE = os.path.join(ROOT, "params", "profile.json")
DEFAULT_BACKUP_DIR = os.path.join(ROOT, "out", "brief")

# params/README.md 的“取值范围（建议）”。这里是 brief 的硬门；
# 新增键时先补 README，再补这张表，避免两处口径漂移。
RANGES = {
    "appearance.height": (1.45, 1.80),
    "appearance.head_to_body_ratio": (5.5, 8.0),
    "appearance.head_width_scale": (0.95, 1.05),
    "appearance.face_width_scale": (0.95, 1.05),
    "appearance.eye_spacing_scale": (0.9, 1.1),
    "appearance.eye_size_scale": (0.9, 1.1),
    "appearance.nose_depth_scale": (0.8, 1.0),
    "appearance.mouth_width_scale": (0.8, 1.2),
    "appearance.ear_scale": (0.85, 1.15),
    "appearance.shoulder_width_scale": (0.95, 1.08),
    "appearance.waist_scale": (0.9, 1.1),
    "appearance.hip_scale": (0.95, 1.1),
    "appearance.leg_length_ratio": (0.42, 0.52),
    "appearance.arm_thickness_scale": (0.9, 1.15),
    "appearance.hand_scale": (0.9, 1.15),
    "appearance.foot_size_scale": (0.9, 1.15),
    "hair.bangs_groups": (1, 7),
    "hair.clump_count": (5, 9),
    "hair.clump_width_scale": (0.75, 1.25),
    "hair.clump_thickness_scale": (0.8, 1.2),
    "hair.ahoge_length_scale": (0.6, 1.4),
    "hair.ahoge_thickness_scale": (0.7, 1.3),
    "outfit.skirt_length": (0.55, 0.72),
    "outfit.skirt_pleats": (12, 28),
    "outfit.skirt_amplitude_scale": (0.6, 1.5),
    "outfit.sleeve_length": (1.05, 1.18),
    "outfit.collar_v_depth": (0.012, 0.03),
    "render.outline_px": (0.0, 10.0),
    "render.skin_pos_mid": (0.0, 1.0),
    "render.skin_pos_light": (0.0, 1.0),
    "render.key_energy": (0.0, 500.0),
    "render.rim_energy": (0.0, 500.0),
}

ENUMS = {
    "hair.style": ("long", "bob", "cards"),
}

COLOR_KEYS = {
    "hair.hair_color",
    "hair.hair_shadow_color",
    "hair.hair_ring_color",
    "outfit.shirt_color",
    "outfit.skirt_color",
}

# params/README.md 明确“只登记、未接线”的键：改了不会影响渲染。
UNWIRED = {
    "outfit.shirt_color",
    "outfit.skirt_color",
    "render.outline_px",
    "render.skin_pos_mid",
    "render.skin_pos_light",
    "render.key_energy",
    "render.rim_energy",
}

# 这些 hair 键只在 long 路径生效；bob 下改了也不会影响几何。
LONG_ONLY = {
    "hair.bangs_groups",
    "hair.clump_count",
    "hair.clump_width_scale",
    "hair.clump_thickness_scale",
    "hair.ahoge_length_scale",
    "hair.ahoge_thickness_scale",
    "hair.twin_tails",
}

COMMANDS = (
    "python scripts/build.py all",
    "python scripts/build.py check",
    "python scripts/measure.py",
)

OPTIONAL_COMMANDS = (
    "python scripts/build.py asset",
    "python scripts/audit.py",
    "python scripts/deliver.py",
)


class BriefError(Exception):
    """brief 文件 / profile 路径 / 写盘失败时抛出。"""


def _utf8_stdio():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f)
    except FileNotFoundError:
        raise BriefError("找不到文件：" + path)
    except json.JSONDecodeError as exc:
        raise BriefError("JSON 解析失败：{0}（{1}）".format(path, exc))
    except OSError as exc:
        raise BriefError("读取失败：{0}（{1!r}）".format(path, exc))
    if not isinstance(doc, dict):
        raise BriefError("顶层必须是 JSON 对象：" + path)
    return doc


def _resolve_profile(path):
    """把 profile 路径限制在 人物建模/ 内，防路径穿越。"""
    if not isinstance(path, str) or not path:
        raise BriefError("profile 路径必须是非空字符串，收到 {0!r}".format(path))
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    real = os.path.realpath(p)
    root = os.path.realpath(ROOT)
    if os.path.normcase(os.path.commonpath([root, real])) != os.path.normcase(root):
        raise BriefError("profile 必须位于 人物建模/ 内：" + path)
    if not real.lower().endswith(".json"):
        raise BriefError("profile 必须是 .json：" + path)
    return real


def _flatten(node, prefix=""):
    out = {}
    if not isinstance(node, dict):
        return out
    for key, value in node.items():
        full = "{0}.{1}".format(prefix, key) if prefix else str(key)
        if isinstance(value, dict):
            out.update(_flatten(value, full))
        else:
            out[full] = value
    return out


def _set_path(doc, key, value):
    parts = key.split(".")
    node = doc
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            child = {}
            node[part] = child
        node = child
    node[parts[-1]] = value


def _same(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) < 1e-12
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    return a == b


def _validate_value(key, raw, base_value):
    """返回 (normalized, errors, warnings)。类型不符时 normalized=None。"""
    errors = []
    warnings = []
    normalized = None

    if isinstance(base_value, bool):
        if not isinstance(raw, bool):
            errors.append("{0}: 需要 bool，收到 {1!r}".format(key, raw))
        else:
            normalized = raw
    elif isinstance(base_value, int):
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            errors.append("{0}: 需要整数，收到 {1!r}".format(key, raw))
        elif isinstance(raw, float) and not raw.is_integer():
            errors.append("{0}: 需要整数，收到 {1!r}".format(key, raw))
        else:
            normalized = int(raw)
    elif isinstance(base_value, float):
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            errors.append("{0}: 需要数字，收到 {1!r}".format(key, raw))
        else:
            normalized = float(raw)
    elif isinstance(base_value, str):
        if not isinstance(raw, str):
            errors.append("{0}: 需要字符串，收到 {1!r}".format(key, raw))
        else:
            normalized = raw
    elif isinstance(base_value, (list, tuple)):
        if not isinstance(raw, (list, tuple)) or len(raw) != len(base_value):
            errors.append("{0}: 需要长度 {1} 的数组，收到 {2!r}".format(
                key, len(base_value), raw))
        else:
            vals = []
            for i, (item, proto) in enumerate(zip(raw, base_value)):
                if isinstance(proto, bool) or not isinstance(item, (int, float)):
                    errors.append("{0}[{1}]: 需要数字，收到 {2!r}".format(key, i, item))
                    break
                vals.append(float(item))
            if len(vals) == len(base_value):
                normalized = vals
    else:
        errors.append("{0}: 不支持的 profile 值类型 {1}".format(key, type(base_value).__name__))

    if normalized is not None and key in ENUMS:
        if normalized not in ENUMS[key]:
            errors.append("{0}: 只接受 {1}，收到 {2!r}".format(
                key, " / ".join(ENUMS[key]), normalized))
    if normalized is not None and key in RANGES:
        lo, hi = RANGES[key]
        if not (lo <= float(normalized) <= hi):
            errors.append("{0}: 超出建议范围 [{1}, {2}]，收到 {3!r}".format(
                key, lo, hi, normalized))
    if normalized is not None and key in COLOR_KEYS:
        for i, channel in enumerate(normalized):
            if not (0.0 <= channel <= 1.0):
                errors.append("{0}[{1}]: RGB 必须在 0~1，收到 {2!r}".format(
                    key, i, channel))
                break

    if key in UNWIRED:
        warnings.append("{0}: 该键尚未接线，改了不会影响渲染/外观（见 params/README.md）".format(key))
    return normalized, errors, warnings


def validate_brief(brief, base_doc, base_path):
    """校验 brief，返回结构化结果；不写盘。"""
    if not isinstance(brief, dict):
        raise BriefError("brief 顶层必须是 JSON 对象")
    set_map = brief.get("set", {})
    if not isinstance(set_map, dict):
        raise BriefError("brief.set 必须是对象（点路径 -> 新值）")

    base_flat = _flatten(base_doc)
    if not base_flat:
        raise BriefError("base profile 为空或不是对象：" + base_path)

    errors = []
    warnings = []
    changes = []
    merged = json.loads(json.dumps(base_doc, ensure_ascii=False))

    for key in sorted(set_map, key=lambda item: str(item)):
        if not isinstance(key, str) or not key:
            errors.append("set 的键必须是非空点路径字符串：{0!r}".format(key))
            continue
        if key not in base_flat:
            errors.append("{0}: 未知键（先看 params/README.md 的 39 键表）".format(key))
            continue
        raw = set_map[key]
        normalized, errs, warns = _validate_value(key, raw, base_flat[key])
        errors.extend(errs)
        warnings.extend(warns)
        status = "OK"
        if errs:
            status = "ERROR"
        elif _same(normalized, base_flat[key]):
            status = "NOOP"
        changes.append({
            "key": key,
            "old": base_flat[key],
            "new": normalized if normalized is not None else raw,
            "status": status,
        })
        if not errs and normalized is not None:
            _set_path(merged, key, normalized)

    # 依赖 hair.style 的键：按补丁后的最终风格判断，避免“同时设 long + 发束”误报。
    effective_style = _flatten(merged).get("hair.style", "long")
    for change in changes:
        key = change["key"]
        if key in LONG_ONLY and effective_style != "long":
            warnings.append("{0}: 仅在 hair.style=long 生效；当前是 {1!r}".format(
                key, effective_style))

    commands = list(COMMANDS)
    optional = list(OPTIONAL_COMMANDS)
    return {
        "ok": not errors,
        "brief": brief.get("brief", ""),
        "base": base_path,
        "changes": changes,
        "warnings": _dedupe(warnings),
        "errors": errors,
        "commands": commands,
        "optional": optional,
        "env": {},
    }


def _dedupe(items):
    out = []
    seen = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _backup(profile_path, backup_dir=None):
    src = profile_path
    if not os.path.exists(src):
        raise BriefError("profile 不存在，无法备份：" + src)
    dst_dir = backup_dir or DEFAULT_BACKUP_DIR
    os.makedirs(dst_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(src))[0]
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = os.path.join(dst_dir, "{0}-{1}.json".format(stem, stamp))
    n = 0
    while os.path.exists(dst):
        n += 1
        dst = os.path.join(dst_dir, "{0}-{1}-{2}.json".format(stem, stamp, n))
    try:
        shutil.copy2(src, dst)
    except OSError as exc:
        raise BriefError("备份失败：{0}（{1!r}）".format(dst, exc))
    return dst


def _atomic_write(path, doc):
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except OSError as exc:
        raise BriefError("写 profile 失败：{0}（{1!r}）".format(path, exc))


def apply_brief(brief, profile_path, backup_dir=None):
    """重新读盘 -> 校验 -> 备份 -> 原子写。返回 (result, backup_or_None)。"""
    base_doc = _load_json(profile_path)
    result = validate_brief(brief, base_doc, profile_path)
    if not result["ok"]:
        raise BriefError("brief 有 {0} 条错误，拒绝写盘".format(len(result["errors"])))
    changed = [c for c in result["changes"] if c["status"] == "OK"]
    if not changed:
        result["applied"] = False
        result["backup"] = None
        return result, None
    merged = json.loads(json.dumps(base_doc, ensure_ascii=False))
    for change in changed:
        _set_path(merged, change["key"], change["new"])
    backup = _backup(profile_path, backup_dir)
    _atomic_write(profile_path, merged)
    result["applied"] = True
    result["backup"] = backup
    return result, backup


def _default_run_specs():
    """brief --run 的默认验证链。

    blocking：失败即停（build 不过、measure 的 must 级不过）。
    advisory：check 有既知 R4 FAIL、audit 有既知面数/非流形 FAIL，默认只记录；
    --strict 时任何非 0 都算失败，留给干净基线/CI 用。
    """
    return [
        {"name": "build.py all", "cmd": [sys.executable, "scripts/build.py", "all"], "blocking": True},
        {"name": "measure.py", "cmd": [sys.executable, "scripts/measure.py"], "blocking": True},
        {"name": "build.py check", "cmd": [sys.executable, "scripts/build.py", "check"], "blocking": False},
        {"name": "audit.py --fast", "cmd": [sys.executable, "scripts/audit.py", "--fast"], "blocking": False},
    ]


def run_chain(specs, strict=False, runner=None, env=None):
    """按顺序跑验证命令；返回结构化结果。runner/env 可注入，便于 selftest。"""
    runner = runner or subprocess.run
    results = []
    ok = True
    for spec in specs:
        print("[brief] run: {0}".format(spec["name"]))
        t0 = time.monotonic()
        try:
            proc = runner(spec["cmd"], cwd=ROOT, env=env)
            code = proc.returncode
        except OSError as exc:
            print("[brief] run: 启动失败 {0!r}".format(exc))
            code = 2
        elapsed = time.monotonic() - t0
        blocking = bool(spec.get("blocking"))
        results.append({
            "name": spec["name"],
            "cmd": spec["cmd"],
            "exit": code,
            "blocking": blocking,
            "elapsed": round(elapsed, 3),
        })
        print("[brief] run: {0} exit={1} elapsed={2:.1f}s".format(spec["name"], code, elapsed))
        if code != 0:
            if blocking or strict:
                ok = False
                break
            print("[brief] run: 非阻塞项失败，继续（--strict 可把它升级为失败）")
    return {"ok": ok, "strict": bool(strict), "results": results}


def _print_run(run_result):
    print("")
    print("[brief] run 结论：{0}（strict={1}）".format(
        "PASS" if run_result["ok"] else "FAIL",
        "yes" if run_result["strict"] else "no"))
    for item in run_result["results"]:
        print("  {0:<18} exit={1} {2} {3:.1f}s".format(
            item["name"], item["exit"],
            "blocking" if item["blocking"] else "advisory",
            item["elapsed"]))


def _fmt(value):
    if isinstance(value, float):
        return "{0:.4g}".format(value)
    if isinstance(value, list):
        return "[" + ", ".join(_fmt(v) for v in value) + "]"
    return str(value)


def _print_human(result, applied=False, show_next=True):
    print("[brief] profile={0}".format(result["base"]))
    if result.get("brief"):
        print("[brief] 目标：{0}".format(result["brief"]))
    if not result["changes"]:
        print("[brief] set 为空：没有变更")
    else:
        print("")
        print("{0:<38} {1:<14} {2:<14} {3}".format("键", "现值", "新值", "判定"))
        print("-" * 88)
        for change in result["changes"]:
            print("{0:<38} {1:<14} {2:<14} {3}".format(
                change["key"], _fmt(change["old"]), _fmt(change["new"]), change["status"]))
    if result["warnings"]:
        print("")
        print("[brief] 警告（不阻塞）：")
        for warning in result["warnings"]:
            print("  - " + warning)
    if result["errors"]:
        print("")
        print("[brief] 错误（阻塞）：")
        for error in result["errors"]:
            print("  - " + error)
    print("")
    if not result["ok"]:
        print("[brief] 结论：FAIL（{0} 条错误，未写盘）".format(len(result["errors"])))
        return
    if applied:
        print("[brief] 结论：OK（已写盘）")
        if result.get("backup"):
            print("[brief] 备份：{0}".format(result["backup"]))
    else:
        print("[brief] 结论：OK（dry-run，未写盘；加 --apply 执行）")
    if not show_next:
        return
    if result.get("env"):
        print("[brief] 注意：本次不是默认 profile；手动跑下一步前先设环境变量：")
        for key, value in result["env"].items():
            print("  {0}={1}".format(key, value))
    print("[brief] 下一步：")
    for cmd in result["commands"]:
        print("  " + cmd)
    print("[brief] 可选（需要资产/交付时）：")
    for cmd in result["optional"]:
        print("  " + cmd)


def _print_json(result):
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=False))


def _selftest():
    base_doc = _load_json(DEFAULT_PROFILE)
    cases = []

    def add(name, brief, expect_ok, expect_error_contains=None, expect_warning_contains=None):
        cases.append((name, brief, expect_ok, expect_error_contains, expect_warning_contains))

    add("valid patch", {"set": {
        "appearance.height": 1.68,
        "appearance.head_to_body_ratio": 7.5,
        "hair.style": "bob",
        "outfit.skirt_length": 0.62,
    }}, True)
    add("unknown key", {"set": {"appearance.not_a_key": 1}}, False, "未知键")
    add("wrong type", {"set": {"appearance.height": "tall"}}, False, "需要数字")
    add("out of range", {"set": {"appearance.height": 3.0}}, False, "超出建议范围")
    add("unwired warning", {"set": {"render.key_energy": 60}}, True,
        None, "尚未接线")
    add("long-only warning", {"set": {
        "hair.style": "bob",
        "hair.bangs_groups": 4,
    }}, True, None, "仅在 hair.style=long 生效")
    add("bad enum", {"set": {"hair.style": "mohawk"}}, False, "只接受")
    add("non-integer pleats", {"set": {"outfit.skirt_pleats": 22.5}}, False, "需要整数")

    passed = 0
    failed = 0
    for name, brief, expect_ok, err_sub, warn_sub in cases:
        try:
            result = validate_brief(brief, base_doc, DEFAULT_PROFILE)
            if result["ok"] != expect_ok:
                raise AssertionError("ok={0} 期望 {1}".format(result["ok"], expect_ok))
            if err_sub and not any(err_sub in e for e in result["errors"]):
                raise AssertionError("错误里没有 {0!r}: {1}".format(err_sub, result["errors"]))
            if warn_sub and not any(warn_sub in w for w in result["warnings"]):
                raise AssertionError("警告里没有 {0!r}: {1}".format(warn_sub, result["warnings"]))
            print("[selftest] PASS {0}".format(name))
            passed += 1
        except Exception as exc:
            print("[selftest] FAIL {0}: {1}".format(name, exc))
            failed += 1

    # 写盘 + 备份 + 拒绝非法 patch 的行为测试（临时 profile 在 out/ 下，自动清理）
    out_root = os.path.join(ROOT, "out")
    os.makedirs(out_root, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=out_root) as td:
            temp_profile = os.path.join(td, "profile.json")
            shutil.copy2(DEFAULT_PROFILE, temp_profile)
            result, backup = apply_brief(
                {"set": {"appearance.height": 1.68}}, temp_profile, backup_dir=td)
            after = _load_json(temp_profile)
            assert result["applied"] is True
            assert after["appearance"]["height"] == 1.68
            assert after["appearance"]["head_to_body_ratio"] == base_doc["appearance"]["head_to_body_ratio"]
            assert backup and os.path.exists(backup)
            print("[selftest] PASS apply + backup + preserve other keys")
            passed += 1
    except Exception as exc:
        print("[selftest] FAIL apply + backup + preserve other keys: {0}".format(exc))
        failed += 1

    try:
        with tempfile.TemporaryDirectory(dir=os.path.join(ROOT, "out")) as td:
            temp_profile = os.path.join(td, "profile.json")
            shutil.copy2(DEFAULT_PROFILE, temp_profile)
            before = _load_json(temp_profile)
            try:
                apply_brief({"set": {"appearance.height": "tall"}}, temp_profile, backup_dir=td)
                raise AssertionError("非法 patch 没有抛 BriefError")
            except BriefError:
                pass
            after = _load_json(temp_profile)
            assert after == before
            print("[selftest] PASS invalid patch refuses to write")
            passed += 1
    except Exception as exc:
        print("[selftest] FAIL invalid patch refuses to write: {0}".format(exc))
        failed += 1

    def fake_specs(codes):
        specs = []
        for i, code in enumerate(codes):
            specs.append({
                "name": "fake-{0}".format(i),
                "cmd": [sys.executable, "-c", "import sys; sys.exit({0})".format(code)],
                "blocking": i == 0,
            })
        return specs

    run_cases = [
        ("run chain all pass", fake_specs([0, 0]), False, True, 2),
        ("run chain blocking fail stops", fake_specs([1, 0]), False, False, 1),
        ("run chain advisory fail non-strict", fake_specs([0, 1]), False, True, 2),
        ("run chain advisory fail strict", fake_specs([0, 1]), True, False, 2),
    ]
    for name, specs, strict, expect_ok, expect_len in run_cases:
        try:
            result = run_chain(specs, strict=strict)
            if result["ok"] != expect_ok:
                raise AssertionError("ok={0} 期望 {1}".format(result["ok"], expect_ok))
            if len(result["results"]) != expect_len:
                raise AssertionError("results={0} 期望 {1}".format(
                    len(result["results"]), expect_len))
            print("[selftest] PASS {0}".format(name))
            passed += 1
        except Exception as exc:
            print("[selftest] FAIL {0}: {1}".format(name, exc))
            failed += 1

    print("[selftest] PASS={0} FAIL={1}".format(passed, failed))
    return 0 if failed == 0 else 1


def main(argv=None):
    _utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="brief.py",
        description="把 brief JSON 校验成 params/profile.json 的受控补丁（默认 dry-run）")
    parser.add_argument("brief", nargs="?", help="brief JSON 路径")
    parser.add_argument("--profile", help="覆盖 brief.base 的 profile 路径（须在 人物建模/ 内）")
    parser.add_argument("--apply", action="store_true", help="真正写盘；缺省只打印差值")
    parser.add_argument("--run", action="store_true",
                        help="写盘后跑 build.py all + measure.py + check + audit（需 --apply）")
    parser.add_argument("--strict", action="store_true",
                        help="配合 --run：任何非 0 都算失败（默认 check/audit 为 advisory）")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    parser.add_argument("--selftest", action="store_true", help="跑内置校验/写盘测试，不读写真实 profile")
    args = parser.parse_args(argv)

    if args.selftest:
        return _selftest()

    if not args.brief:
        parser.error("需要 brief JSON 路径（或用 --selftest）")
    if args.run and not args.apply:
        parser.error("--run 需要同时加 --apply（先写盘再验证）")

    brief = {}
    base_path = args.profile or "params/profile.json"
    try:
        brief = _load_json(args.brief)
        base_path = args.profile or brief.get("base") or "params/profile.json"
        profile_path = _resolve_profile(base_path)
        if args.apply:
            result, _backup = apply_brief(brief, profile_path)
        else:
            result = validate_brief(brief, _load_json(profile_path), profile_path)
        default_real = os.path.normcase(os.path.realpath(DEFAULT_PROFILE))
        if os.path.normcase(profile_path) != default_real:
            result["env"] = {"PM_PROFILE": profile_path}
    except BriefError as exc:
        if args.json:
            _print_json({
                "ok": False,
                "brief": brief.get("brief", "") if isinstance(brief, dict) else "",
                "base": base_path,
                "changes": [],
                "warnings": [],
                "errors": [str(exc)],
                "commands": [],
                "optional": [],
                "env": {},
            })
        else:
            print("[brief] 错误：{0}".format(exc), file=sys.stderr)
        return 2

    if args.run:
        run_env = dict(os.environ)
        run_env["PM_PROFILE"] = profile_path
        result["run"] = run_chain(_default_run_specs(), strict=args.strict, env=run_env)

    if args.json:
        _print_json(result)
    else:
        _print_human(result, applied=args.apply, show_next=not args.run)
        if args.run:
            _print_run(result["run"])
    if not result["ok"]:
        return 1
    if args.run and not result["run"]["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
