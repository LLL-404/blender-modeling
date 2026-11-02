# -*- coding: utf-8 -*-
# 人物建模资产批量改名：美女.blend → <角色名>_rig_v001.blend（含 .blend1 联动）。
# 用法：python scripts/rename_assets.py --to <角色名> [--apply]
#   缺省 dry-run：只打印计划，不动任何文件；--apply 才真正执行。
# ⚠ 执行前确认没有前台 Blender 开着 美女.blend（CLI 感知不到窗口内未保存状态）。
# 引用联动（本脚本只打印步骤，由作者按清单手工改，避免脚本内变量路径写盘）：
#   1. 人物建模/m5_rig.py:104 附近的 BLEND=os.path.join(HERE,"美女.blend") → 换新文件名
#   2. 人物建模/README.md 中 3 处「美女.blend」字面引用 → 换新文件名
# 纪律：只动本脚本点名的文件；git 提交由作者在会话外完成。
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # 人物建模/
ALLOWED = os.path.realpath(ROOT)


def _safe(rel):
    """解析 ROOT 下相对名并防穿越：拒绝解析结果逃出 人物建模/ 或含 .. 段。"""
    if os.sep in rel or "/" in rel or ".." in rel:
        sys.exit(f"[rename] 拒绝含路径分隔符或 .. 的名字：{rel!r}")
    p = os.path.realpath(os.path.join(ALLOWED, rel))
    if os.path.commonpath([ALLOWED, p]) != ALLOWED:
        sys.exit(f"[rename] 拒绝人物建模/ 之外的解析结果：{rel!r}")
    return p


def main():
    ap = argparse.ArgumentParser(description="把 美女.blend 规范改名为 <角色名>_rig_v001.blend")
    ap.add_argument("--to", required=True, help="角色名，如：小铃")
    ap.add_argument("--apply", action="store_true", help="真正执行；缺省只打印计划")
    args = ap.parse_args()
    name = args.to.strip()
    if not name:
        sys.exit("[rename] 角色名不能为空")
    bad = set(name) & set('\\/:*?"<>|')
    if bad:
        sys.exit(f"[rename] 角色名含非法文件名字符：{bad}")
    new = f"{name}_rig_v001.blend"

    src = _safe("美女.blend")
    if not os.path.exists(src):
        sys.exit("[rename] 找不到 美女.blend——可能已改过名，无需重复执行")
    dst = _safe(new)

    print(f"[rename] 计划：美女.blend -> {new}")
    print(f"  改名 {src}")
    print(f"    -> {dst}")
    if os.path.exists(_safe("美女.blend1")):
        print(f"  改名 {os.path.join(ALLOWED, '美女.blend1')} -> {_safe(new.replace('.blend', '.blend1'))}")

    if not args.apply:
        print("[rename] dry-run 结束（加 --apply 执行）")
        print("[rename] 引用联动请按脚本头注释的两条清单手工执行")
        return

    os.rename(src, dst)
    print(f"[rename] 已改名 -> {dst}")
    b1src = _safe("美女.blend1")
    if os.path.exists(b1src):
        os.rename(b1src, _safe(new.replace(".blend", ".blend1")))
        print("[rename] 已联动 .blend1")
    print("[rename] 完成。此后 build.py rig 会写到新文件名；引用联动两条手工清单见脚本头注释。")


if __name__ == "__main__":
    main()
