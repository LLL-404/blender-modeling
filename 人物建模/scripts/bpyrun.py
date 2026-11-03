# -*- coding: utf-8 -*-
"""Blender 可执行文件定位单源（D12）。

scripts/build.py 的 blender_exe() 与 scripts/check.py 的 _blender() 都转调这里的
blender_exe()——环境变量名与默认安装路径只在本文件写一份。
Blender体检/check.sh 的 find_blender() 探测根与 DEFAULT_BLENDER 同源
（bash 侧自包含不 import，只在默认路径行旁注释互指）。

纯标准库，不 import bpy；由 build.py / check.py 以同目录模块导入。
"""
import os
import sys

# 与 Blender体检/check.sh 的探测根 "D:/Program Files/Blender Foundation" 同源，
# 改一处须对另一处。
DEFAULT_BLENDER = r"D:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
BLENDER_ENV = "BLENDER_EXE"


def utf8_stdio():
    """把 stdout/stderr 强制成 UTF-8（仅在**非交互**输出时生效）。

    为什么需要：Windows 下 Python 的管道/重定向输出用系统 locale（本机 cp936＝GBK），
    而本项目的中文报表里有 GBK 编码不了的字符（如 `spec/reference.json` 的
    「头身接缝（头底−颈柱顶）」里的 U+2212 MINUS SIGN）。实测 `python scripts/measure.py`
    在 pwsh 里被捕获（非 tty）时直接 UnicodeEncodeError 崩在打印表格处——这正是
    AI/批处理读报表的路径。交互控制台本来就经 WriteConsoleW 走 UTF-8（PEP 528），
    不受影响，故只在非 tty 时改。

    调用点：build.py / check.py / measure.py / sweep.py 的 main() 开头。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            if not stream.isatty():
                stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def blender_exe(env="BLENDER_EXE", default=DEFAULT_BLENDER):
    """返回可用的 Blender 路径；不可用时打印中文提示并返回 None。"""
    path = os.environ.get(env) or default
    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(path):
        print("[bpyrun] 错误：找不到 Blender 可执行文件：", file=sys.stderr)
        print("        " + path, file=sys.stderr)
        print("        请安装 Blender 5.2，或用环境变量 {0} 指向 blender.exe。".format(env),
              file=sys.stderr)
        print("        例（PowerShell）：$env:{0} = 'D:\\path\\to\\blender.exe'".format(env),
              file=sys.stderr)
        return None
    return path
