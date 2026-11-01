# -*- coding: utf-8 -*-
"""几何参数空间：搜索维度、范围、步长、默认值。

默认值纪律（这一条是整份搜索器的可信度基础）：
  **每个 default 都是从现网代码读出来的实测值，不是设计稿里的示例数。**
  证据写在每条的 `src` 字段（文件:行）。`verify_defaults()` 会在 Blender 里
  现场 import 两个模块、把模块级常量和这里的 default 再对一遍，打印
  MATCH/MISMATCH —— 代码改了默认值而这里忘了同步，会在 `--n 4` 冒烟时立刻暴露。

`inner` 口径（skirt_inner_mode）：
  * "valley"（现网行为）：裙腰环的**波谷**也要留够净空，故 inner = margin + amp；
  * "peak"  ：只要求**波峰**留够净空，故 inner = margin − 1.25·amp。
  两者是裙腰宽松度的主要开关：peak 口径把腰收窄 2.25·amp，可能把 net 压到
  2mm 硬线以下，也可能消掉 8mm 过松罚分 —— 交给搜索去裁决，不在这里预判。
"""
import halton

# 波峰/波谷相对基半径的增益：wave = amp·cosθ + amp·HARM2·cos2θ
#   peak = +1.25·amp（θ=0），trough = −0.75·amp（θ=π），见 lib/outfit.py 的 _skirt()
SKIRT_PEAK_GAIN = 1.0 + 0.25

DIMS = [
    {"key": "skirt_margin", "lo": 0.002, "hi": 0.010, "step": 0.001,
     "default": 0.0030,
     "src": "lib/outfit.py:262 SKIRT_WAIST_MARGIN = 0.0030"},

    {"key": "skirt_inner_mode", "choices": ["valley", "peak"], "default": "valley",
     "src": "lib/outfit.py:320 inner = margin + amps[i]（valley 分支，即现网行为）"},

    {"key": "finger_blend_p", "lo": 2.0, "hi": 6.0, "step": 0.5,
     "default": 3.5,
     "src": "lib/hand.py:210 BLEND_P = 3.5（原 assign_groups.blend 的 p 默认值）"},

    {"key": "finger_smooth_n", "lo": 2, "hi": 12, "step": 2, "int": True,
     "default": 6,
     "src": "lib/hand.py:213 SMOOTH_ITERS = 6（原 f, iters = 0.55, 6）"},

    # 关节混合带宽度：现网用「反距离混合」的 eps=1.5mm 表达带宽（eps 越大，
    # 两根相邻骨的权重过渡越宽）。实测默认 1.5mm 落在任务示例的 3~9 之外，
    # 若沿用示例区间，默认点不在搜索盒内、坐标下降也回不到默认 —— 故按实测
    # 值把区间取 [1.0, 4.0]；REPORT.md「搜索空间表」里写明了这处偏离。
    {"key": "joint_blend_mm", "lo": 1.0, "hi": 4.0, "step": 0.5,
     "default": 1.5,
     "src": "lib/hand.py:211 BLEND_EPS_MM = 1.5（原 blend() 的 eps=0.0015）"},
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
    """把**实际值** v 夹进范围并吸附到步长网格（整数维取整、类别维取下标）。"""
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
    """把 [0,1) 的归一化坐标映射到该维的实际值（采样用）。

    注意与 snap() 的分工：snap() 收的是**实际值**（坐标下降 ±1 step 时用），
    from_unit() 收的是**归一化坐标**（Halton 采样用）。这两个曾经混用过一次，
    结果是 32 个采样点全被夹到参数盒的右上角 —— 采样器看着在跑，实际只测了
    一个角点，搜索形同虚设。
    """
    u = max(0.0, min(1.0, float(u)))
    if "choices" in d:
        ch = d["choices"]
        i = int(u * len(ch))
        return ch[max(0, min(len(ch) - 1, i))]
    return snap(d, d["lo"] + u * (d["hi"] - d["lo"]))


def sample(n, seed=halton.DEFAULT_SEED):
    """Halton 采样 n 个参数点，覆盖整个参数盒。"""
    mat = halton.halton_seq(n, len(DIMS), seed=seed)
    out = []
    for row in mat:
        p = {}
        for d, v in zip(DIMS, row):
            p[d["key"]] = from_unit(d, float(v))
        out.append(p)
    return out


def verify_defaults(verbose=True):
    """在 Blender 进程内把 DIMS 的 default 与现网模块常量对一遍。

    返回不一致列表（空 = 全对）。非 Blender 环境下（import 不到 outfit/hand）
    返回 [] 并打印 SKIP —— 不把「没 vera」伪装成「通过」。
    """
    try:
        import outfit
        import hand
    except Exception as exc:      # 纯 Python 环境
        if verbose:
            print(f"[space] verify_defaults SKIP ({exc!r})")
        return []

    live = {
        "skirt_margin": outfit.SKIRT_WAIST_MARGIN,
        "skirt_inner_mode": outfit.SKIRT_INNER_MODE,
        "finger_blend_p": hand.BLEND_P,
        "finger_smooth_n": hand.SMOOTH_ITERS,
        "joint_blend_mm": hand.BLEND_EPS_MM,
    }
    bad = []
    for d in DIMS:
        k = d["key"]
        got = live.get(k)
        ok = (got == d["default"])
        if not ok:
            bad.append((k, d["default"], got))
        if verbose:
            print(f"[space] default {k}="
                  f"{d['default']!r} live={got!r} {'MATCH' if ok else 'MISMATCH'}")
    return bad