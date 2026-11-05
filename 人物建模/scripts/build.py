# -*- coding: utf-8 -*-
"""统一构建入口（纯标准库，不 import bpy）。

用法（在项目根 `实用工具/Blender建模/人物建模/` 下执行）：

    python scripts/build.py body            # 只跑 m1_body.py
    python scripts/build.py head            # m2_head.py
    python scripts/build.py look            # m3_look.py
    python scripts/build.py clay            # scripts/render_clay.py（白模四视图，判几何用）
    python scripts/build.py hair            # m4_hair.py
    python scripts/build.py outfit          # m5_outfit.py
    python scripts/build.py rig             # m5_rig.py（含 B4 回归断言）
    python scripts/build.py asset           # M6：E1+E2 UV/四边 → E3 贴图/AO → E4 glb
    python scripts/build.py all             # 依次跑 m1 -> m5_rig（不含 asset）
    python scripts/build.py check           # 转调 scripts/check.py（全部探针）
    python scripts/build.py measure         # 转调 scripts/measure.py（外观 spec 体检）
    python scripts/build.py archive         # out/ 与 *.blend 复制到 ../../../散件归档/

职责边界：只负责起 Blender 进程并转发退出码，**不解析、不改写**任何模块参数。
Blender 可执行文件取环境变量 `BLENDER_EXE`，缺省为本机安装路径
（定位单源在本目录 scripts/bpyrun.py，D12）；
路径不存在时打印中文提示并以退出码 2 结束（不静默失败）。
"""
import argparse
import datetime
import glob
import os
import shutil
import subprocess
import sys
import time

import bpyrun  # D12：Blender 定位单源（本目录 scripts/bpyrun.py）

# 项目根 = 本文件（scripts/build.py）的父目录的父目录
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_BLENDER = bpyrun.DEFAULT_BLENDER
BLENDER_ENV = bpyrun.BLENDER_ENV

# 子命令 -> (入口脚本, 说明)。顺序即 `all` 的执行顺序，不可打乱：
# m1 素体 -> m2 头 -> m3 着色 -> m4 头发 -> m5 服装 -> m5 骨架。
STEPS = {
    "body": ("m1_body.py", "身体素模 + 四视图 + 手部近景"),
    "head": ("m2_head.py", "头与五官"),
    "look": ("m3_look.py", "三渲二着色/描边验收"),
    # clay 不并入 ALL_ORDER：它是 face 部位的几何证据，由 flow 单独调用。
    "clay": ("scripts/render_clay.py", "白模四视图（无描边/无 bloom/无 alpha）"),
    "hair": ("m4_hair.py", "头发"),
    "outfit": ("m5_outfit.py", "服装"),
    "rig": ("m5_rig.py", "45 骨骨架 + 4 姿势 + 回归断言"),
}
ALL_ORDER = ("body", "head", "look", "hair", "outfit", "rig")

# asset 是多脚本步骤（M6 资产化），单独跑，不并入 all：
# 它依赖 美女.blend，且 E4 会重导出 glb（约 40s）。
M6_STEPS = (
    ("m6_asset.py", "E1+E2 UV 展开与残余三角归因"),
    ("m6_bake.py", "E3 色板贴图 + AO + 法线一致性"),
    ("m6_export.py", "E4 去描边壳 + PBR + glb 导出与回读"),
    ("m6_multiview.py", "E5 16 机位环绕复核（toon vs glb）"),
)

ARCHIVE_OUT_DIR = "out"
ARCHIVE_BLEND_GLOB = "*.blend"
# 归档真身：D:/G/github/散件归档/人物建模/<时间戳>/（从 ROOT 上跳 3 级到 D:/G/github/ 再入 散件归档/）
ARCHIVE_REL = os.path.join("..", "..", "..", "散件归档", "人物建模")


def blender_exe():
    """返回可用的 Blender 路径；不可用时打印中文提示并返回 None。

    （D12 起转调 bpyrun.blender_exe；签名与返回值不变。）
    """
    return bpyrun.blender_exe(BLENDER_ENV, DEFAULT_BLENDER)


def run_script(step, script, blender, extra=None):
    """用 Blender 跑单个入口脚本，返回 (退出码, 耗时秒)。

    extra：透传给入口脚本的 `--` 之后参数（如 m7_aux 的 --nool）。
    """
    script_path = os.path.join(ROOT, script)
    if not os.path.exists(script_path):
        print("[build] 错误：入口脚本不存在：" + script_path, file=sys.stderr)
        print("[build] step={0} exit=2 elapsed=0.0s".format(step), file=sys.stderr)
        return 2, 0.0

    cmd = [blender, "-b", "--factory-startup", "--python-exit-code", "1", "--python", script_path]
    if extra:
        cmd += ["--"] + list(extra)
    t0 = time.monotonic()
    try:
        # 不捕获 stdout：Blender 的构建日志直接透传，保留 [ratio]/[render]/[assert] 原文。
        proc = subprocess.run(cmd, cwd=ROOT)
        code = proc.returncode
    except OSError as exc:
        print("[build] 错误：无法启动 Blender：{0!r}".format(exc), file=sys.stderr)
        code = 2
    elapsed = time.monotonic() - t0
    print("[build] step={0} exit={1} elapsed={2:.1f}s".format(step, code, elapsed))
    return code, elapsed


def run_py_script(step, script, blender):
    """转调本目录的纯标准库脚本（check.py / measure.py），返回退出码。

    Blender 定位由子脚本自己走 bpyrun；这里把同一个可执行文件用环境变量透传，
    保证父子进程不会各找一个。
    """
    script_path = os.path.join(ROOT, "scripts", script)
    if not os.path.exists(script_path):
        print("[build] 错误：找不到 " + script_path, file=sys.stderr)
        print("[build] step={0} exit=2".format(step), file=sys.stderr)
        return 2
    t0 = time.monotonic()
    env = dict(os.environ)
    env[BLENDER_ENV] = blender
    try:
        proc = subprocess.run([sys.executable, script_path], cwd=ROOT, env=env)
        code = proc.returncode
    except OSError as exc:
        print("[build] 错误：无法启动 {0}：{1!r}".format(script, exc), file=sys.stderr)
        code = 2
    elapsed = time.monotonic() - t0
    print("[build] step={0} exit={1} elapsed={2:.1f}s".format(step, code, elapsed))
    return code


def _count_files(path):
    """统计目录/文件树下的文件数与总字节。"""
    if os.path.isfile(path):
        return 1, os.path.getsize(path)
    files = 0
    total = 0
    for base, _dirs, names in os.walk(path):
        for name in names:
            files += 1
            try:
                total += os.path.getsize(os.path.join(base, name))
            except OSError:
                pass
    return files, total


def run_archive():
    """把 out/ 与 *.blend 复制到 ../../../散件归档/人物建模/<时间戳>/（复制，不移动）。"""
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dst_root = os.path.abspath(os.path.join(ROOT, ARCHIVE_REL, stamp))
    if os.path.isdir(dst_root):
        dst_root = dst_root + "-1"          # 同一秒重跑，避免覆盖上一次

    sources = []
    out_dir = os.path.join(ROOT, ARCHIVE_OUT_DIR)
    if os.path.isdir(out_dir):
        sources.append(out_dir)
    else:
        print("[build] 提示：没有 out/ 目录，跳过渲染产物复制")
    blend_files = sorted(glob.glob(os.path.join(ROOT, ARCHIVE_BLEND_GLOB)))
    sources.extend(blend_files)
    if not sources:
        print("[build] 错误：out/ 与 *.blend 都不存在，没有可归档的产物", file=sys.stderr)
        return 1

    os.makedirs(dst_root, exist_ok=True)
    files = 0
    total = 0
    for src in sources:
        dst = os.path.join(dst_root, os.path.basename(src))
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        n, size = _count_files(dst)
        files += n
        total += size
        print("[build] archive copy {0} -> {1} ({2} files)".format(
            os.path.relpath(src, ROOT), os.path.basename(dst), n))

    print("[build] archive -> {0} (files={1} bytes={2})".format(dst_root, files, total))
    return 0


def main(argv=None):
    bpyrun.utf8_stdio()   # 管道/重定向下用 UTF-8，防 GBK 编码崩溃
    parser = argparse.ArgumentParser(
        prog="build.py",
        description="人物建模统一构建入口（body|head|look|hair|outfit|rig|asset|check|aux|all|archive）")
    parser.add_argument("step",
                        choices=list(ALL_ORDER) + ["clay", "asset", "check", "measure", "aux",
                                                   "all", "archive"],
                        help="构建步骤；all = 依次跑 m1 -> m5_rig（不含 asset）")
    parser.add_argument("--nool", action="store_true",
                        help="仅 aux：关掉反法线描边壳，看裸几何（产物带 _nool 后缀）")
    args = parser.parse_args(argv)

    blender = blender_exe()
    if blender is None:
        return 2

    if args.step == "check":
        return run_py_script("check", "check.py", blender)

    if args.step == "measure":
        return run_py_script("measure", "measure.py", blender)

    if args.step == "aux":
        # 全向补视角：顶 / 底 / 左 / 后 + 斜上斜下，补 m2~m5 全平视留下的盲区。
        code, _ = run_script("aux", "m7_aux.py", blender,
                            extra=["--nool"] if args.nool else None)
        return code

    if args.step == "archive":
        return run_archive()

    steps = list(ALL_ORDER) if args.step == "all" else [args.step]
    print("[build] root={0}".format(ROOT))
    print("[build] blender={0}".format(blender))
    if args.step == "asset":
        for script, desc in M6_STEPS:
            print("[build] ---- asset: {0} ({1}) ----".format(desc, script))
            code, _elapsed = run_script("asset:" + script, script, blender)
            if code != 0:
                print("[build] 中止：step={0} 退出码 {1}".format(script, code), file=sys.stderr)
                return code
        print("[build] done")
        return 0
    for step in steps:
        script, desc = STEPS[step]
        print("[build] ---- {0}: {1} ({2}) ----".format(step, desc, script))
        code, _elapsed = run_script(step, script, blender)
        if code != 0:
            print("[build] 中止：step={0} 退出码 {1}".format(step, code), file=sys.stderr)
            return code
    print("[build] done")
    return 0


if __name__ == "__main__":
    sys.exit(main())