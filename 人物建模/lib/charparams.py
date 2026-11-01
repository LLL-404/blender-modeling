# -*- coding: utf-8 -*-
"""外观旋钮读取层：`params/profile.json` → lib 模块，**带默认值回退**。

设计约束（与 lib/optio.py 同一风格，但两者职责不同）：

* optio.py 读的是**搜索器产出**的 `opt/best.json`（几何/像素两段，数值在跑搜索时变）；
* charparams.py 读的是**人手工调风格**的 `params/profile.json`（分组的语义旋钮）。

模块名为什么是 charparams 而不是 profile：Python 标准库自带 `profile`
（性能剖析器）。只要 `lib/` 不在 `sys.path` 最前，裸 `import profile` 就会
静默拿到 stdlib 的那个，调用 `profile.get()` 直接
`AttributeError: module 'profile' has no attribute 'get'`。改名后路径错会
变成显式的 `ModuleNotFoundError`，不会再「静默拿错模块」。

两者互不替代。调用点的默认值永远是「引入旋钮之前代码里的那个字面量」，所以：

* 文件不存在 / JSON 半截写入 / 键不存在 / 类型不符 → 返回调用方给的 default；
* 每条路径都不抛异常 —— 「删掉 params/profile.json 就回到未参数化时的行为」
  这条回滚路径永远成立，不需要改任何调用点。

文件路径：
    1. 环境变量 `PM_PROFILE`（相对路径按项目根解释）—— 便于临时换一套 profile；
    2. 默认 `人物建模/params/profile.json`。

本模块**不 import bpy**，可以在纯 Python 下被读取。
"""
import json
import os

# 人物建模/lib/ 的上一级 = 项目根
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_REL = os.path.join("params", "profile.json")

_cache = None          # None = 还没读盘；dict = 已解析的 profile 文档
_cache_path = None     # 缓存对应的绝对路径（PM_PROFILE 变了要重读）


def profile_path():
    """当前生效的 profile 文件绝对路径（不检查是否存在）。"""
    env = os.environ.get("PM_PROFILE")
    if env:
        return env if os.path.isabs(env) else os.path.join(_PROJECT_ROOT, env)
    return os.path.join(_PROJECT_ROOT, DEFAULT_REL)


def _read():
    """读到一份 dict；任何失败都退化成空 dict（不抛异常）。"""
    global _cache, _cache_path
    path = profile_path()
    if _cache is not None and _cache_path == path:
        return _cache
    doc = {}
    try:
        # 必须显式 encoding='utf-8'：Windows 默认 gbk，遇到 UTF-8 中文注释会炸
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            doc = raw
    except Exception:      # 文件缺失 / 无权限 / 半截写入 / 非法 JSON 全走这里
        doc = {}
    _cache = doc
    _cache_path = path
    return _cache


def reload():
    """丢掉缓存，下一次 get() 重新读盘（换 profile 后不重启进程也能生效）。"""
    global _cache, _cache_path
    _cache = None
    _cache_path = None


def active_source():
    """当前生效来源，便于探针/自检打印口径。"""
    if _read():
        return "profile(" + profile_path() + ")"
    return "default"


def all_params():
    """扁平 dict（点路径 → 值），便于打印与比对；文件缺失时是空 dict。"""
    out = {}

    def walk(prefix, node):
        for k, v in node.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, dict):
                walk(key, v)
            else:
                out[key] = v

    walk("", _read())
    return out


def _coerce(raw, default):
    """按 default 的类型校验/转换 raw；不合规就抛，交给 get() 回退。"""
    if isinstance(default, bool):                  # bool 必须先于 int 判断
        if isinstance(raw, bool):
            return raw
        raise TypeError("bool 键收到 %r" % (raw,))
    if isinstance(default, int):
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise TypeError("int 键收到 %r" % (raw,))
        return int(round(float(raw)))
    if isinstance(default, float):
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise TypeError("float 键收到 %r" % (raw,))
        return float(raw)
    if isinstance(default, str):
        if not isinstance(raw, str):
            raise TypeError("str 键收到 %r" % (raw,))
        return raw
    if isinstance(default, (list, tuple)):
        if not isinstance(raw, (list, tuple)) or len(raw) != len(default):
            raise TypeError("序列键长度/类型不符：%r" % (raw,))
        # 颜色/向量：逐项按 default 的元素类型校验。int 原型只收 int ——
        # 否则 [0,0,0] 这种默认值会把 0.115 悄悄四舍五入成 0（类型不符应回退）。
        out = []
        for item, proto in zip(raw, default):
            if isinstance(proto, int) and not isinstance(proto, bool):
                if isinstance(item, bool) or not isinstance(item, int):
                    raise TypeError("int 元素收到 %r" % (item,))
                out.append(int(item))
            else:
                out.append(_coerce(item, proto))
        return out
    return raw                                     # dict / None 等原样返回


def get(key, default):
    """按点路径读 profile：`get("appearance.height", 1.62)`。

    文件缺失 / JSON 解析失败 / 键不存在 / 类型不符 → 一律返回 default。永不抛异常。
    """
    try:
        node = _read()
        if not node:
            return default
        for part in str(key).split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return _coerce(node, default)
    except Exception:
        return default