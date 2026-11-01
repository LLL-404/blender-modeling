# -*- coding: utf-8 -*-
"""参数注入层：把 opt/best.json 里的最优参数喂给 lib 模块，**带默认值回退**。

best.json 现在是**两段共享**的一份文件：

    {
      "best_params": {...},                 # 几何段（T17 写出）
      "pixel": {"best_params": {...}},      # 像素段（T18 写出）
      ...
    }

查找顺序（`param(key, default)`）：
    1. 进程内 override（搜索器 `set_overrides()` 注入，不落盘）；
    2. `pixel.best_params[key]`（像素段优先，因为像素段是后写的、更专指）；
    3. 顶层 `best_params[key]`（几何段）；
    4. 调用方给的 default。

为什么要「pixel 优先」而不是合并成一张表：两段各有自己的搜索器，写盘时各自只碰自己
那一段（读-改-写），互不覆盖；读取时若两段出现同名键，按「更晚写的一段赢」优先，
避免一段的参数被另一段的旧值悄悄顶掉。实测两段键名不重叠（几何 5 维 / 像素 6 维）。

文件缺失 / JSON 解析失败 / 键不存在 / 类型转换失败，一律返回 default —— 「删掉
opt/best.json 就回到手调默认值」这条回滚路径永远成立，不需要改任何调用点。

本模块**不 import bpy**，可以在纯 Python 下被读取（space_geom / 探针的导入链都会碰到它）。
"""
import json
import os

# 人物建模/opt/best.json（本文件在 人物建模/lib/ 下）
BEST_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "opt", "best.json")

_cache = None          # None = 还没读盘；dict = {"pixel": {...}, "top": {...}}
_overrides = {}        # 进程内注入（搜索器用），优先级最高


def best_path():
    return BEST_PATH


def _read():
    """读 best.json 的两段参数，任何失败都退化成空 dict（不抛异常）。"""
    global _cache
    if _cache is not None:
        return _cache
    doc = {}
    try:
        with open(BEST_PATH, "r", encoding="utf-8") as f:
            doc = json.load(f)
    except Exception:      # 文件缺失/半截写入/权限问题都走这里
        doc = {}
    if not isinstance(doc, dict):
        doc = {}

    top = doc.get("best_params")
    top = top if isinstance(top, dict) else {}
    pix_doc = doc.get("pixel")
    pix_doc = pix_doc if isinstance(pix_doc, dict) else {}
    pix = pix_doc.get("best_params")
    pix = pix if isinstance(pix, dict) else {}

    _cache = {"pixel": pix, "top": top}
    return _cache


def reload():
    """丢掉缓存，下一次 param() 重新读盘（改 best.json 后不重启也能生效）。"""
    global _cache
    _cache = None


def set_overrides(mapping):
    """进程内注入参数（搜索器专用）。传 None 清空。"""
    global _overrides, _cache
    _overrides = dict(mapping or {})
    _cache = None


def active_source():
    """返回当前生效来源，便于探针打印口径。"""
    if _overrides:
        return "override"
    d = _read()
    if d["pixel"] or d["top"]:
        return "best.json(pixel+top)"
    return "default"


def active_params():
    """当前生效的两段参数合并视图（pixel 覆盖同名的 top 值）。"""
    d = _read()
    out = dict(d["top"])
    out.update(d["pixel"])
    out.update(_overrides)
    return out


def param(key, default):
    """读最优参数；任何异常都回退到 default（值域转换也按 default 的类型）。"""
    if key in _overrides:
        raw = _overrides[key]
    else:
        d = _read()
        if key in d["pixel"]:
            raw = d["pixel"][key]
        elif key in d["top"]:
            raw = d["top"][key]
        else:
            raw = default
    try:
        if isinstance(default, bool):          # bool 必须先于 int 判断
            return bool(raw)
        if isinstance(default, int):
            return int(round(float(raw)))
        if isinstance(default, str):
            return str(raw)
        return float(raw)
    except Exception:
        return default