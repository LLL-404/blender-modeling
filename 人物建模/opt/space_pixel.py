# -*- coding: utf-8 -*-
"""像素段参数空间（T18）：描边 / key 灯 / skin 三档 / rim 灯。

默认值纪律与几何段一致：**每个 default 都是现网代码里的实际值**，`src` 字段给出
`文件:行`。`verify_defaults()` 在 Blender 里现场 import `look` / `shots` 再对一遍，
打印 MATCH/MISMATCH —— 代码改了默认值而这里忘同步，会在 `--n 2` 冒烟时立刻暴露。

枚举维（`rim_azimuth`）不参与连续坐标下降：搜索器只在 top-k 点上把 4 个方位
**全枚举**一遍（见 search_pixel.py 的 `enum_sweep`）。
"""
import halton

DIMS = [
    # 描边目标线宽（px）。实际 thickness = px × ortho/res_y，所以 px 是视图无关量。
    {"key": "outline_px", "lo": 2.0, "hi": 4.5, "step": 0.5,
     "default": 3.5,
     "src": "lib/look.py:30 OUTLINE_PX = 3.5（正式入口 m3_look.py:63 base_px=3.5）"},

    {"key": "key_energy", "lo": 40.0, "hi": 60.0, "step": 5.0,
     "default": 49.0,
     "src": "lib/shots.py:15 KEY_ENERGY = 49.0"},

    {"key": "skin_pos_mid", "lo": 0.56, "hi": 0.70, "step": 0.02,
     "default": 0.62,
     "src": "lib/look.py:31 SKIN_POS_MID = 0.62（set_all 的 pos[1]）"},

    {"key": "skin_pos_light", "lo": 0.66, "hi": 0.84, "step": 0.02,
     "default": 0.68,
     "src": "lib/look.py:32 SKIN_POS_LIGHT = 0.68（set_all 的 pos[2]）"},

    {"key": "rim_energy", "lo": 80.0, "hi": 400.0, "step": 80.0,
     "default": 80.0,
     "src": "lib/shots.py:19 RIM_ENERGY = 80.0"},

    # 枚举维：半径/高度固定为 R=hypot(2.2,2.0)=2.974、z=2.2，只改方位角。
    {"key": "rim_azimuth", "choices": ["back", "back_left", "left", "back_right"],
     "default": "back_left",
     "src": "lib/shots.py:26 RIM_AZIMUTH='back_left'（原 rim_ob.location=(-2.2,2.0,2.2)）"},
]


def dims():
    return list(DIMS)


def dim(key):
    for d in DIMS:
        if d["key"] == key:
            return d
    raise KeyError(key)


def defaults():
    return {d["key"]: d["default"] for d in DIMS}


def snap(d, v):
    """实际值 → 夹进范围 + 吸附步长网格（整数维取整、类别维取下标）。"""
    if "choices" in d:
        ch = d["choices"]
        if isinstance(v, str):
            return v if v in ch else d["default"]
        i = int(v * len(ch))
        return ch[max(0, min(len(ch) - 1, i))]
    v = float(v)
    lo, hi = d["lo"], d["hi"]
    v = max(lo, min(hi, v))
    k = round((v - lo) / d["step"])
    v = lo + k * d["step"]
    v = max(lo, min(hi, v))
    if d.get("int"):
        return int(round(v))
    return round(v, 6)


def from_unit(d, u):
    """归一化坐标 [0,1) → 实际值（Halton 采样用；与 snap 的分工见 space_geom 的同名注释）。"""
    u = max(0.0, min(1.0, float(u)))
    if "choices" in d:
        ch = d["choices"]
        i = int(u * len(ch))
        return ch[max(0, min(len(ch) - 1, i))]
    return snap(d, d["lo"] + u * (d["hi"] - d["lo"]))


def fixup(p):
    """把采样/邻域点修成**物理合法**的组合：skin ramp 必须 0 < mid < light。

    ColorRamp 的元素位置必须严格递增，否则三档色阶的顺序会乱（look.set_all 里也会
    兜底夹紧，但那样「评估记录的参数」与「实际生效的参数」就分叉了 —— 指标无从归因）。
    """
    q = dict(p)
    mid, lig = q.get("skin_pos_mid"), q.get("skin_pos_light")
    if mid is not None and lig is not None and lig < mid + 0.02 - 1e-9:
        q["skin_pos_light"] = snap(dim("skin_pos_light"), mid + 0.02)
    return q


def sample(n, seed=halton.DEFAULT_SEED):
    """Halton 采样 n 个参数点（6 维，覆盖整个参数盒）。"""
    mat = halton.halton_seq(n, len(DIMS), seed=seed)
    out = []
    for row in mat:
        p = {}
        for d, v in zip(DIMS, row):
            p[d["key"]] = from_unit(d, float(v))
        out.append(fixup(p))
    return out


def verify_defaults(verbose=True):
    """把 DIMS 的 default 与现网模块常量对一遍；返回不一致列表（空 = 全对）。"""
    try:
        import look
        import shots
    except Exception as exc:      # 非 Blender 环境
        if verbose:
            print(f"[spacep] verify_defaults SKIP ({exc!r})")
        return []

    live = {
        "outline_px": look.OUTLINE_PX,
        "key_energy": shots.KEY_ENERGY,
        "skin_pos_mid": look.SKIN_POS_MID,
        "skin_pos_light": look.SKIN_POS_LIGHT,
        "rim_energy": shots.RIM_ENERGY,
        "rim_azimuth": shots.RIM_AZIMUTH,
    }
    bad = []
    for d in DIMS:
        k = d["key"]
        got = live.get(k)
        ok = (got == d["default"])
        if not ok:
            bad.append((k, d["default"], got))
        if verbose:
            print(f"[spacep] default {k}={d['default']!r} live={got!r} "
                  f"{'MATCH' if ok else 'MISMATCH'}")
    return bad