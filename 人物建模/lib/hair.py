# -*- coding: utf-8 -*-
"""M4：头发。发帽 + 后发片 + 发束 + 刘海 + 侧发 + 呆毛。

思路：发丝全部是放样出来的椭圆截面管，宽度远大于厚度，所以
正面看是发片，侧面看有厚度；后脑用一片开缝曲面 + Solidify 兜住。
"""
import bpy
import math
import random
from mathutils import Vector

import cfg
import charparams
import head as headmod
from meshkit import (superellipse_ring, loft, resample, tube, resample_path,
                     join, shade_smooth, mesh_from, select_only)


# ---------------- 外观旋钮默认值（= 引入旋钮前的字面量） ----------------
_DEFAULT_BANGS_GROUPS = 3        # 刘海分组：左外撇 2 + 中 3 + 右外撇 2
_DEFAULT_CLUMP_COUNT = 7         # 后发束缕数
_DEFAULT_TWIN_TAILS = False      # 双马尾（现网没有，默认关）


def _cap():
    """发帽按头骨轮廓外扩 6mm 放样，保证任何高度都不会被头骨顶穿。

    用 headmod.head_rows() 而**不是**模块级 `head.HEAD`：后者是 import 时
    定型的快照，height / head_width_scale 在本进程内被改过时不会跟随。
    """
    rows = resample(headmod.head_rows(), "z", 0.010)
    rings = []
    for z, rx, ryf, ryb, cy, p in rows:
        if z < 1.488:
            continue
        rings.append(superellipse_ring(z, rx + 0.006, ryf + 0.006, cy - 0.002,
                                       0.0, p, 48, ry_back=ryb + 0.008))
    ob = loft(rings, name="hair_cap")
    for v in ob.data.vertices:
        # 发际线以下的正脸部分塞回头内：发帽只负责头顶和后脑，
        # 前额的边界交给刘海去遮。
        if v.co.z < 1.582 and v.co.y < -0.004:
            v.co.y = 0.022 + (v.co.y - 0.022) * 0.18
    ob.data.update()
    return ob


def _arc_ring(z, rx, ry, cy, a0, a1, seg):
    pts = []
    for i in range(seg):
        a = math.radians(a0 + (a1 - a0) * i / (seg - 1))
        pts.append(Vector((rx * math.cos(a), cy + ry * math.sin(a), z)))
    return pts


# ---------------- T22：后发片在颈段收窄（倒 V 缺口），让出颈后/颈侧 ----------------
# 实测（d_probe_waist.py 射线首击）：z 1.31~1.37 挡住侧面视线的是后发片的
# **侧边**（a≈322°/578°，x=±0.084~0.106 而 y 只有 0.006），不是后中线
# （a=450° 处 x=0，根本不挡）。所以"缺口"不是在后中挖三角，而是把发片下缘的
# 半张角从 128° 收到 105°：侧边从 (x .084, y .006) 退到 (x .102, y .021)，
# 颈侧 y<0.021 的视线就通了。1.370 以上一点不动 —— 后脑覆盖不变，不会露头皮
# （Head 最高只到 z=1.620，1.370 以下本来就没有头骨，收窄不会碰到头皮）。
_BACK_HALF_ANG = 128.0          # = 原 _arc_ring 的 322°..578°（后中线 450°±128°）
_BACK_HALF_ANG_NARROW = 100.0   # 颈段收窄后的半张角（边 y 从 0.006 退到 0.030）
_BACK_NOTCH_Z0 = 1.370          # 缺口起点（该高度及以上的环完全不动）
_BACK_NOTCH_Z1 = 1.340          # 收满的高度（30mm 内收满 = 短而尖的倒 V）
_BACK_NOTCH_HOLD_Z = 1.290      # 1.340→1.290 保持窄角，再往下回到全宽


def _back_half_ang(z):
    """后发片在高度 z 的半张角（度）。

    1.370 以上 128°（后脑全包）；1.370→1.340 线性收到 100°（倒 V 缺口）；
    1.340→1.290 保持 100°（颈段整段让开）；再往下线性放回 128°（长发照旧
    披在肩上，背面剪影不变）。
    """
    if z >= _BACK_NOTCH_Z0:
        return _BACK_HALF_ANG
    if z >= _BACK_NOTCH_Z1:
        t = (_BACK_NOTCH_Z0 - z) / (_BACK_NOTCH_Z0 - _BACK_NOTCH_Z1)
        return _BACK_HALF_ANG + (_BACK_HALF_ANG_NARROW - _BACK_HALF_ANG) * t
    if z >= _BACK_NOTCH_HOLD_Z:
        return _BACK_HALF_ANG_NARROW
    t = min(1.0, (_BACK_NOTCH_HOLD_Z - z) / 0.090)     # 1.290→1.200 放回全宽
    return _BACK_HALF_ANG_NARROW + (_BACK_HALF_ANG - _BACK_HALF_ANG_NARROW) * t


def _back_profile(rows, z):
    """在 rows 表上按 z 线性插值 (rx, ry, cy)。表本身就是折线，插值不改形状。"""
    if z >= rows[0][0]:
        return rows[0][1], rows[0][2], rows[0][3]
    for r0, r1 in zip(rows, rows[1:]):
        if r1[0] <= z <= r0[0]:
            t = (r0[0] - z) / (r0[0] - r1[0])
            return (r0[1] + (r1[1] - r0[1]) * t,
                    r0[2] + (r1[2] - r0[2]) * t,
                    r0[3] + (r1[3] - r0[3]) * t)
    return rows[-1][1], rows[-1][2], rows[-1][3]


def _back_sheet():
    rows = [
        # z,     rx,    ry,    cy
        (1.606, 0.050, 0.042, 0.012),
        (1.585, 0.080, 0.055, 0.035),
        (1.552, 0.094, 0.060, 0.045),
        (1.500, 0.104, 0.061, 0.052),
        (1.440, 0.100, 0.055, 0.045),
        (1.370, 0.106, 0.055, 0.040),
        # T22：1.340 环是加出来的（原表没有）。缺口必须在这一环**收满**，
        # 否则 loft 只在 1.370/1.290 两环间插值，1.36 处侧边 y 才退到 9mm
        # （实测被 Solidify 再压到 6mm），颈后仍看不出来。插值自原表：
        # t=(1.370−1.340)/0.080=0.375 → rx .10825 ry .055 cy .038125
        (1.340, 0.108, 0.055, 0.038),
        (1.290, 0.112, 0.055, 0.035),
        (1.200, 0.110, 0.052, 0.032),
        (1.110, 0.104, 0.048, 0.028),
        (1.040, 0.090, 0.042, 0.022),
        (0.995, 0.060, 0.030, 0.016),
    ]
    seg = 40
    # 环数与列数都不变（11×40），只是颈段各列角度收窄 —— 顶点数保持 440。
    rings = []
    for z in (r[0] for r in rows):
        rx, ry, cy = _back_profile(rows, z)
        half = _back_half_ang(z)
        rings.append(_arc_ring(z, rx, ry, cy, 450.0 - half, 450.0 + half, seg))
    ob = loft(rings, cap_start=False, cap_end=False, name="hair_back")
    select_only(ob)
    m = ob.modifiers.new("Solidify", 'SOLIDIFY')
    m.thickness = 0.006
    m.offset = 0.0
    bpy.ops.object.modifier_apply(modifier=m.name)
    return ob


def _strand(points, widths, thick, seg=16, step=0.010):
    radii = [(w, thick) for w in widths]
    p, r = resample_path(points, radii, step)
    return tube(p, r, seg=seg, name="strand")


def _clumps():
    """后发片上的纵向发束，制造沟壑而不是一张光滑的布。

    三个数要一起看（widths/thick 都是**半径**）：
      · 半宽 max **19mm** → 全宽 38mm；旧值 28mm 是全宽 56mm；
        （18.0mm 正好压在下限，浮点插值后会量成 17.99 → 判 FAIL，
        取 19mm 落在 [18,24] 中部；沟壑深度用公式估 4.9mm 仍达标）
      · 厚 9mm → 全厚 18mm；旧值 11mm；
      · 间距 26mm → **34mm**。这一条才是沟壑能不能出来的关键：
        中心距 26mm、全宽 56mm 时相邻重叠 30mm，交叠处反而隆起成"峰"，
        整片后脑被抹平；34mm 与「7 缕 × 204mm 覆盖后脑 208mm」匹配，
        相邻重叠降到 2mm。注意**谷深由 thick（y 半径 9mm）封顶**，不是 width：
        groove = thick·(1−√(1−(d/2width)²))，旧 11·(1−√(1−(26/56)²))=3.3mm，
        现在 9·(1−√(1−(34/36)²))=5.5mm。width 再大谷就被吞掉了。
    y 不能往里收：后发片**外表面**在 y≈0.049~0.116（DESIGN 写的 0.104 是
    表值 cy+ry，**没算 Solidify 的 +3mm**；实测最厚处在 z≈1.50，y=0.116）。
    发束中段 y 0.106~0.108 → 外表面 0.115~0.117，比后发片多 1~9mm 才能露出来；
    顶部 z 1.520 原来只有 y 0.078（外表面 0.087），在后发片 0.108 下方整整埋了
    21mm —— 背面看那一整段是光滑的布，正是 D2 像素判据上不去的直接原因。
    """
    out = []
    rnd = random.Random(cfg.SEED + 7)
    # 外观旋钮：缕数 / 宽度 / 厚度（默认 7 / ×1.0 / ×1.0，与引入前逐位一致）
    count = int(charparams.get("hair.clump_count", _DEFAULT_CLUMP_COUNT))
    if count < 3:
        count = _DEFAULT_CLUMP_COUNT
    wk = charparams.get("hair.clump_width_scale", 1.0)
    tk = charparams.get("hair.clump_thickness_scale", 1.0)
    for i in range(count):
        if count == _DEFAULT_CLUMP_COUNT:
            x0 = -0.102 + 0.034 * i        # 默认缕数走原式，保证逐位不变
        else:
            x0 = -0.034 * ((count - 1) // 2) + 0.034 * i
        z0 = 1.586
        pts = [Vector((x0 * 0.52, 0.020, z0)),
               Vector((x0 * 0.92, 0.108, 1.520)),
               Vector((x0, 0.108, 1.400)),
               Vector((x0 * 1.04, 0.106, 1.250)),
               Vector((x0 * 1.02, 0.098, 1.110)),
               Vector((x0 * 0.90, 0.086, 1.010 - rnd.uniform(0.0, 0.02)))]
        widths = [0.014 * wk, 0.0165 * wk, 0.019 * wk,
                  0.0165 * wk, 0.014 * wk, 0.004 * wk]
        out.append(_strand(pts, widths, 0.009 * tk))
    return out


def _bangs():
    """刘海：3 组，不是 7 根等距柱子。

    分组（按 x 排序，探针靠大半包围盒认组，不靠对象名）：
      左外撇 2 缕 → 中 3 缕齐 → 右外撇 2 缕
    中组末端几乎不外扩（1.02~1.05），贴额、末端齐；外撇组末端外扩
    1.22/1.26，形成向外翻的走向。
    组间留 **真空几何缝**（1~2mm），不是靠贴图/材质画出来的：
    中组整体 x 范围约 ±47.5mm，外撇组第一缕内缘从 ±49.0mm 起（缝 1.5mm）。
    末端 z_tip 1.530~1.532 → 顶点 z_min≈1.525，仍落在眉上沿
    （1.530~1.537）下方，与 A 阶段位置一致，**不要改低**。
    """
    out = []
    # 外观旋钮：bangs_groups = 中间那组的缕数（默认 3 = 现网「中 3 齐」）。
    # 左右外撇组恒为 2 缕（它们是「外撇走向」的语义，不在旋钮范围内）。
    groups = int(charparams.get("hair.bangs_groups", _DEFAULT_BANGS_GROUPS))
    if groups < 1:
        groups = _DEFAULT_BANGS_GROUPS
    # (中心 x, 末端外扩倍率, z_tip)
    spec = [(-0.0800, 1.26, 1.530),
            (-0.0620, 1.22, 1.530)]
    if groups == _DEFAULT_BANGS_GROUPS:
        spec += [(-0.0280, 1.05, 1.532),          # 默认分组走原表，逐位不变
                 (0.0000, 1.02, 1.532),
                 (0.0280, 1.05, 1.532)]
    else:
        for i in range(groups):
            gx = 0.028 * (i - (groups - 1) / 2.0)
            # 中间最平（1.02）、越靠外越外撇（上限 1.05）
            gspread = 1.02
            if groups > 1:
                gspread += 0.03 * abs(2.0 * i / (groups - 1) - 1.0)
            spec.append((gx, gspread, 1.532))
    spec += [(0.0620, 1.22, 1.530),
             (0.0800, 1.26, 1.530)]
    for x, spread, z_tip in spec:
        pts = [Vector((x, -0.052, 1.588)),
               Vector((x * 1.06, -0.062, 1.568)),
               Vector((x * 1.12, -0.070, 1.547)),
               Vector((x * spread, -0.073, z_tip))]
        widths = [0.012, 0.017, 0.015, 0.0035]
        out.append(_strand(pts, widths, 0.006))
    return out


def _side_locks():
    out = []
    for s in (-1, 1):
        pts = [Vector((0.075 * s, -0.030, 1.578)),
               Vector((0.092 * s, -0.052, 1.520)),
               Vector((0.101 * s, -0.048, 1.440)),
               Vector((0.099 * s, -0.032, 1.340)),
               Vector((0.092 * s, -0.014, 1.220)),
               Vector((0.086 * s, 0.002, 1.130))]
        widths = [0.014, 0.021, 0.023, 0.020, 0.014, 0.004]
        out.append(_strand(pts, widths, 0.010))
    return out


def _ahoge():
    """呆毛：一根从头顶翘起又回收的细发丝。

    注意 `_strand` 的 widths 传的是**半径**，全宽 = 2×widths[0]。
    旧的 0.008 是全宽 16mm，比一根手指还粗，正面看像天线；
    这里整体减半到全宽 7mm，轨迹点一个不动（高度保持 +50.7mm 相对 Head z_max）。
    """
    pts = [Vector((0.004, -0.030, 1.612)),
           Vector((0.010, -0.035, 1.646)),
           Vector((0.018, -0.046, 1.664)),
           Vector((0.026, -0.060, 1.652)),
           Vector((0.028, -0.066, 1.634))]
    # 外观旋钮：length_scale 从发根（pts[0]）沿轨迹等比拉伸，thickness_scale
    # 乘半径。默认 1.0 时两者都不做运算（×1.0 精确），与引入前逐位一致。
    lk = charparams.get("hair.ahoge_length_scale", 1.0)
    tk = charparams.get("hair.ahoge_thickness_scale", 1.0)
    if lk != 1.0:
        p0 = pts[0]
        pts = [p0 + (p - p0) * lk for p in pts]
    widths = [w * tk for w in (0.0035, 0.0028, 0.0024, 0.0016, 0.0008)]
    return [_strand(pts, widths, 0.004 * tk, seg=10, step=0.006)]


def _twin_tails():
    """双马尾（外观旋钮 hair.twin_tails）。

    默认 False → 返回空列表，build() 里 `parts += []` 不产生任何几何，
    与引入旋钮前的 Hair 网格逐位一致。True 时从后脑两侧各加一条下垂发束，
    宽度/厚度沿用后发束（_clumps）的量级，保证 10mm 级 voxel 观感一致。
    """
    if not charparams.get("hair.twin_tails", _DEFAULT_TWIN_TAILS):
        return []
    out = []
    for s in (-1, 1):
        pts = [Vector((0.075 * s, 0.060, 1.560)),
               Vector((0.120 * s, 0.090, 1.470)),
               Vector((0.135 * s, 0.100, 1.340)),
               Vector((0.128 * s, 0.095, 1.200)),
               Vector((0.118 * s, 0.088, 1.080))]
        widths = [0.012, 0.020, 0.022, 0.017, 0.005]
        out.append(_strand(pts, widths, 0.010, seg=20))
    return out


def build(mats):
    parts = [_cap(), _back_sheet()]
    parts += _clumps()
    parts += _bangs()
    parts += _side_locks()
    parts += _ahoge()
    parts += _twin_tails()
    hair = join(parts, "Hair")
    shade_smooth(hair)
    hair.data.materials.append(mats["hair"])
    return hair