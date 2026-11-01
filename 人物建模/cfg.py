# -*- coding: utf-8 -*-
"""角色参数。改这里就能改人，脚本不用动。

外观旋钮（`params/profile.json`，读取层见 `lib/charparams.py`）：下面这些常量
是**默认值**，profile.json 里有同名键且类型正确时覆盖之。文件缺失 → 全部走
默认值，行为与引入旋钮之前逐位一致（见 params/README.md 的接线清单）。
"""
import charparams

# ---- 比例（米）----
# 外观旋钮：appearance.height（默认 1.62 = 引入旋钮前的字面量）
_DEFAULT_HEIGHT = 1.62
HEIGHT = charparams.get("appearance.height", _DEFAULT_HEIGHT)
HEAD_TOP = HEIGHT
# A6 后 head.py 的 HEAD 表绕 1.3836 放大 1.063 并整体下移，几何下巴落在
# 1.3712；头长 = 1.6200 − 1.3712 = 0.2488 → 头身比 6.51。
# 这个常量只用于「设计口径」和探针，不参与几何。
CHIN_Z = 1.3712
NECK_BASE_Z = 1.320
SHOULDER_Z = 1.295
BUST_Z = 1.150
WAIST_Z = 1.000
HIP_Z = 0.860
CROTCH_Z = 0.760
KNEE_Z = 0.425
ANKLE_Z = 0.075

# ---- 宽度（半宽，米）----
HIP_RX, HIP_RY = 0.155, 0.115
WAIST_RX, WAIST_RY = 0.100, 0.078
BUST_RX, BUST_RY = 0.128, 0.098
SHOULDER_RX = 0.118

LEG_X = 0.072          # 腿中心偏离中轴
ARM_SHOULDER_X = 0.150
ARM_ELBOW_X = 0.198
ARM_WRIST_X = 0.232
WRIST_Z = 0.815

# ---- 细分 ----
RING_SEG = 48          # 每圈顶点数
RESAMPLE_STEP = 0.008  # 纵向重采样步长

SEED = 20261031


def height():
    """身高（米），**调用时**读 profile（cfg 的 HEIGHT 是 import 时定型的快照）。"""
    return charparams.get("appearance.height", _DEFAULT_HEIGHT)