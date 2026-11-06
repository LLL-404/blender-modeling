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
# ---- v2 设计口径（银发旗袍少女，spec/角色设定-银发旗袍-v1.md §一量参表）----
# 头：height 1.68 / 头身比 6.5 由 profile 旋钮驱动（head.py sz/sx 现读），
# 几何下巴 = head_rows()[0][0] = sz(1.384) = 1.4220；头长 0.2580 → 头身比 6.511。
# 下面这些 z 常量是**描述性设计口径**（不参与几何，几何在 body.TORSO /
# body.leg / body.arm 的表里），与表同步维护：
CHIN_Z = 1.4220         # 几何下巴（Head bbox 最低点，appearance.json chin_z 同源）
NECK_BASE_Z = 1.296     # 颈柱底（body.neck base，hard-code 在 body.neck()）
SHOULDER_Z = 1.290      # 肩帽环（body.TORSO 最宽肩行）
BUST_Z = 1.150          # 胸围环
WAIST_Z = 1.010         # 腰最细环
HIP_Z = 0.858           # 胯最宽环
# 裆高（骨相身高 1.68 × 0.415 = 0.6972）。推导（spec §一量参表 + reference.json
# leg_ratio 键）：brief 腿长 3.8 头长 → 腿长/身高 = 3.8/6.5 = 0.585 →
# 裆高/身高 = 1 − 0.585 = 0.415（表键实测口径 = CROTCH_Z/身高，warn 级）。
# v1 的 0.760 是「躯干底环」高度，与网格裆缝顶（v1 实测 0.565）差了近 20cm；
# v2 改成真裆高口径，腿管与躯干底环已按同一口径重排（body.leg 的 0.700 环
# 内缘间隙 ≈26mm —— voxel+smooth 对裆缝的填充阈值经验线 ≈23mm 表面间隙，
# 见 _probe/body_ratio_probe.py，网格缝顶实测 ≈0.69x）。
CROTCH_Z = 0.6972
KNEE_Z = 0.425
ANKLE_Z = 0.075

# ---- 宽度（半宽，米）----
# v2 口径（spec §二；头宽实测 0.2246）：肩 = 1.8 头宽 → 半宽 0.9×0.2246 = 0.202；
# 腰 = 1.2 头宽 → 0.135；胯 = 1.6 头宽 → 0.180。
# 这四个 RX 是 lib/appearance.py:320-325 判据的**口径源**（判据不实测 Body）；
# 网格真值由 _probe/body_ratio_probe.py 并排监督（mesh/cfg ∈ 0.97~1.03 才算
# 判据与几何一致）。RY 侧无任何消费者，仅作描述（取对应环 ryf/ryb 平均）。
HIP_RX, HIP_RY = 0.180, 0.132      # 髋环 ryf 0.118 / ryb 0.146
WAIST_RX, WAIST_RY = 0.135, 0.107  # 腰环 ryf 0.102 / ryb 0.113
BUST_RX, BUST_RY = 0.138, 0.101    # 胸环 ryf 0.103 / ryb 0.099
SHOULDER_RX = 0.202                # 肩带实测口径（三角肌外缘，非 TORSO 肩帽环 0.170）

LEG_X = 0.082          # 腿中心偏离中轴（v2 胯加宽 → 站距外移；rig 腿骨 x 同源）
ARM_SHOULDER_X = 0.126  # 肩峰骨位（rig shoulder.L tail；描述常量，几何在 body.arm）
ARM_ELBOW_X = 0.194     # 肘点（body.arm z=1.045 处 x；描述常量）
ARM_WRIST_X = 0.232     # 腕点（body.arm 末端 = hand.py WRIST_X = rig forearm tail，未动）
WRIST_Z = 0.815

# ---- 细分 ----
RING_SEG = 48          # 每圈顶点数
RESAMPLE_STEP = 0.008  # 纵向重采样步长

SEED = 20261031


def height():
    """身高（米），**调用时**读 profile（cfg 的 HEIGHT 是 import 时定型的快照）。"""
    return charparams.get("appearance.height", _DEFAULT_HEIGHT)