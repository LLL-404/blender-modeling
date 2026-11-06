# -*- coding: utf-8 -*-
"""身体：截面放样 + 顶点级形体雕塑 + 体素融合。坐标：Z 上，-Y 为正脸朝向。"""
import bpy
import math
from mathutils import Vector

import cfg
import charparams
from meshkit import (superellipse_ring, loft, resample, tube, resample_path,
                     join, voxel_remesh, smooth, shade_smooth, select_only)


# v2（2026-11-05 银发旗袍少女改基）：目标（spec §二，头宽实测 0.2246）
#   肩 1.8 头宽 / 腰 1.2 / 胯 1.6 / 腿 3.8 头长（裆高 0.6972，见 cfg.CROTCH_Z）。
# 表值 = 「网格目标 ÷ voxel+smooth 的带内经验因子」：
#   腰带 mesh/表 ≈1.034、胯带 ≈0.984（v1 实测，_probe/body_ratio_probe.py）→
#   腰行 0.131（网格 ≈0.135 = cfg.WAIST_RX）、髋行 0.183（网格 ≈0.180 =
#   cfg.HIP_RX）。肩帽环只给到 0.170：肩带宽度的承载者是三角肌（body.arm
#   上段外移，网格肩带 ≈0.202 = cfg.SHOULDER_RX），肩帽再宽会把上臂埋进躯干。
# 每行 ryf/ryb 按该行 rx 的放大系数同比缩放，保持 v1 的截面形状（宽:深 ≈0.78）。
# 顶部两行（1.315/1.325 颈根）不动：可见颈长判据 = 下巴 − 1.325（appearance.py
# 的 TORSO_TOP_Z），领口/衬衫收口锥都锚在这两行上。
# 裆位连锁：躯干底环 0.752 → 0.705（底帽插进腿管并集内），骨盆段
# 0.705/0.760/0.815 重排——裆高从 0.752 降到 0.6972，骨盆段拉长 63mm。
TORSO = [
    # z,     rx,    ry前,  ry后,  cy,    power
    (0.705, 0.055, 0.048, 0.054, 0.000, 2.0),
    (0.760, 0.125, 0.090, 0.108, 0.000, 2.2),
    (0.815, 0.170, 0.109, 0.131, 0.000, 2.2),
    (0.858, 0.183, 0.118, 0.146, 0.000, 2.2),
    (0.920, 0.163, 0.112, 0.129, 0.000, 2.2),
    (0.975, 0.143, 0.105, 0.118, -0.002, 2.2),
    (1.010, 0.131, 0.102, 0.113, -0.003, 2.2),
    (1.070, 0.132, 0.100, 0.108, -0.002, 2.2),
    (1.150, 0.136, 0.103, 0.099, -0.004, 2.2),
    (1.230, 0.150, 0.099, 0.097, 0.000, 2.2),
    (1.290, 0.170, 0.093, 0.095, 0.000, 2.4),
    (1.305, 0.150, 0.085, 0.087, 0.000, 2.3),
    (1.315, 0.116, 0.072, 0.074, 0.000, 2.2),
    (1.325, 0.088, 0.062, 0.064, 0.002, 2.1),
]


# ---------------- 外观旋钮的默认值（= 引入旋钮前的字面量） ----------------
# 这里只放「派生宽 / 粗细 / 长度」的乘子与比例，**截面表 TORSO 一个字都不改**。
_DEFAULT_SHOULDER_WIDTH_SCALE = 1.0
_DEFAULT_WAIST_SCALE = 1.0
_DEFAULT_HIP_SCALE = 1.0
_DEFAULT_LEG_LENGTH_RATIO = 0.469    # DESIGN §1.2 的腿长比（腿长/身高）
_DEFAULT_ARM_THICKNESS_SCALE = 1.0
_DEFAULT_FOOT_SIZE_SCALE = 1.0


def _tri(z, center, half):
    """三角权重：center 处 1，|z−center| >= half 处 0。"""
    t = abs(z - center) / half
    return 1.0 - t if t < 1.0 else 0.0


def _width_scale(z, sh, wa, hip):
    """肩 / 腰 / 髋三段宽度乘子的平滑权重（梯形加权平均）。

    三个乘子全为 1.0 时数学上恒等于 1.0，调用方走快路径不再逐行相乘。
    """
    w_sh = _tri(z, 1.290, 0.075)     # 肩：TORSO z=1.290 那一行（v2 rx 0.170）
    w_wa = _tri(z, 1.010, 0.120)     # 腰：全表最细处 z=1.010（v2 rx 0.131）
    w_hip = _tri(z, 0.858, 0.130)    # 髋：全表最宽处 z=0.858（v2 rx 0.183）
    tot = w_sh + w_wa + w_hip
    if tot < 1e-9:
        return 1.0
    return (w_sh * sh + w_wa * wa + w_hip * hip) / tot


def torso_rows():
    """TORSO 表按外观旋钮派生宽（肩/腰/髋三段）。

    默认值全为 1.0 时**直接返回 TORSO 的拷贝**（快路径），保证与引入旋钮前
    逐位一致；outfit._shirt 也调用本函数，所以衬衫会跟着身体一起变宽。
    """
    sh = charparams.get("appearance.shoulder_width_scale", _DEFAULT_SHOULDER_WIDTH_SCALE)
    wa = charparams.get("appearance.waist_scale", _DEFAULT_WAIST_SCALE)
    hip = charparams.get("appearance.hip_scale", _DEFAULT_HIP_SCALE)
    if sh == 1.0 and wa == 1.0 and hip == 1.0:
        return list(TORSO)
    return [(z, rx * _width_scale(z, sh, wa, hip),
             ryf * _width_scale(z, sh, wa, hip),
             ryb * _width_scale(z, sh, wa, hip), cy, p)
            for z, rx, ryf, ryb, cy, p in TORSO]


def torso():
    rows = resample(torso_rows(), "z", cfg.RESAMPLE_STEP)
    rings = [superellipse_ring(z, rx, ryf, cy, 0.0, p, cfg.RING_SEG, ry_back=ryb)
             for z, rx, ryf, ryb, cy, p in rows]
    return loft(rings, name="torso")


def gauss(d):
    return math.exp(-d * d)


def sculpt_torso(ob):
    """胸、腹的软变形：直接推顶点，不产生并集折痕。"""
    me = ob.data
    for v in me.vertices:
        x, y, z = v.co
        # 只有朝向正面的顶点参与，权重在侧面平滑降到 0
        w_front = (0.035 - y) / 0.060
        w_front = max(0.0, min(1.0, w_front))
        if w_front <= 0.0:
            continue
        push = 0.0
        # 胸：下半更饱满，上半收平（水滴形，不是半球）
        for s in (-1, 1):
            sz = 0.072 if z > 1.140 else 0.092
            dz = (z - 1.140) / sz
            dx = (x - 0.060 * s) / 0.058
            push += 0.032 * gauss(dz * dz + dx * dx)
        # 小腹：轻微前凸
        push += 0.008 * gauss(((z - 0.975) / 0.070) ** 2) * gauss((x / 0.085) ** 2)
        if push > 0.0:
            v.co.y -= push * w_front
            v.co.z -= push * w_front * 0.15
    me.update()


def blob(loc, radius, scale=(1, 1, 1), name="blob"):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20,
                                         radius=radius, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return ob


def leg(side):
    # v2 腿管（2026-11-05）：LEG_X 0.072 → 0.082（胯加宽后站距外移，rig 腿骨
    # 同源改 x），大腿上段加粗（大腿饱满，brief §二）。裆位口径 0.6972
    # （cfg.CROTCH_Z = 0.415 × 骨相身高 1.68）：
    #   裆缝是「两腿管内缘之间的缝」，voxel(5mm)+smooth(0.5×5) 会把表面间隙
    #   <≈23mm 的缝填平（v1 实测：0.62 环内缘间隙 12mm 的缝，网格缝顶掉到
    #   0.565 ≈ 间隙 23mm 处）。所以 0.700 环的内缘间隙给到 26mm
    #   （0.082 − 0.069 = 0.013 → 双侧 26mm），缝顶实测落在 ≈0.69x；
    #   0.700 以上的行内缘互相搭接/被躯干底帽（TORSO 0.705 环）盖住，中轴充实。
    zs = [0.950, 0.900, 0.840, 0.760, 0.700, 0.640, 0.560, 0.500,
          0.425, 0.340, 0.220, 0.075]
    # 外观旋钮：腿长比。以膝（z=0.425）为铰点缩放膝以上，膝以下与脚不动 ——
    # 这样脚底 z、踝柱与 body.arm/foot 的接合都不受影响。
    # 默认 0.469 走快路径，zs 一个浮点都不动。
    # ⚠ 该旋钮与 leg_ratio 判据（cfg.CROTCH_Z/身高）**解耦**：翻它只缩腿管
    # 几何、不动判据数字（设定书 §一已挂账），v2 不动它（profile 保持 0.469）。
    ratio = charparams.get("appearance.leg_length_ratio", _DEFAULT_LEG_LENGTH_RATIO)
    if ratio > 0.0 and ratio != _DEFAULT_LEG_LENGTH_RATIO:
        k = ratio / _DEFAULT_LEG_LENGTH_RATIO
        zs = [0.425 + (z - 0.425) * k if z >= 0.425 else z for z in zs]
    ys = [0.004, 0.002, -0.002, -0.004, -0.005, -0.006, -0.007, -0.008,
          -0.010, -0.002, 0.006, 0.012]
    rs = [(0.045, 0.049), (0.060, 0.064), (0.086, 0.089), (0.083, 0.087),
          (0.069, 0.073), (0.063, 0.066), (0.057, 0.060), (0.053, 0.056),
          (0.049, 0.052), (0.056, 0.060), (0.041, 0.045), (0.030, 0.034)]
    x = cfg.LEG_X * side
    pts = [Vector((x, ys[i], zs[i])) for i in range(len(zs))]
    p, r = resample_path(pts, rs, 0.012)
    return tube(p, r, name=f"leg_{side}")


# ---------------- 脚（A4） ----------------
# 为什么脚单独走 3mm 体素（DESIGN §2.2 条目 2 / §2.4.2）：
#   5mm 体素把 9~11mm 的脚趾糊平（实测 toe 切片 xy_components=1）。
#   脚在画面里占比小，走 3mm 单独融化的代价可接受；手则必须完全独立（见 lib/hand.py）。
FOOT_VOXEL = 0.0030
TOE_Z = 0.0110           # 脚趾轴线高度（底面约 0.0055，前掌底面 0.0015~0.0022）
TOE_ZONE_Y = -0.096      # 脚趾区 y 分界：脚掌前端做到 -0.092，此线之外只剩脚趾

# 脚掌截面表（沿 -Y 前进，截面是 x-z 平面内的超椭圆；power 越大底面越平）：
#   y,     rx,    z_lo,   z_hi,  power
FOOT_ROWS = (
    (0.062, 0.022, 0.0080, 0.0420, 2.6),   # 脚跟后方
    (0.048, 0.028, 0.0035, 0.0520, 3.0),
    (0.030, 0.034, 0.0018, 0.0580, 3.2),   # 脚跟着地点
    (0.012, 0.036, 0.0030, 0.0560, 3.4),   # 足弓起（底面略抬）
    (-0.014, 0.036, 0.0042, 0.0460, 3.4),  # 足弓最低抬高量
    (-0.040, 0.035, 0.0032, 0.0360, 3.4),
    (-0.066, 0.033, 0.0018, 0.0280, 3.4),  # 前掌着地点
    (-0.082, 0.030, 0.0015, 0.0230, 3.2),  # 全脚最低点（决定 z_min）
    (-0.092, 0.026, 0.0022, 0.0200, 3.0),  # 前端收口
)

# 3 组脚趾：大趾 + 其余合并成 2 组（DESIGN §2.4.2）
#   name, x 偏移(乘 side，负=靠中轴), y0(插入脚掌), y1(趾尖), 半径
TOES = (
    ("big", -0.0240, -0.0860, -0.1100, 0.0055),   # 直径 11mm，可见长 18mm
    ("mid",  0.0060, -0.0860, -0.1060, 0.0050),   # 直径 10mm，可见长 14mm
    ("out",  0.0280, -0.0860, -0.1020, 0.0045),   # 直径  9mm，可见长 10mm
)


def _y_ring(y, cx, rx, z_lo, z_hi, power=3.0):
    """沿 -Y 前进的一个截面环（x-z 平面内的超椭圆，z 从 z_lo 到 z_hi）。

    meshkit.superellipse_ring 只能做 z 平面的水平环；脚掌要沿 y 放样，
    这里就地写一个同构的环，保证与 loft() 的桥接约定一致（角度递增、顶点数相同）。
    """
    seg = cfg.RING_SEG
    zc = 0.5 * (z_lo + z_hi)
    rz = 0.5 * (z_hi - z_lo)
    e = 2.0 / power
    out = []
    for i in range(seg):
        a = 2.0 * math.pi * i / seg
        c, s = math.cos(a), math.sin(a)
        ex = rx * math.copysign(abs(c) ** e, c)
        ez = rz * math.copysign(abs(s) ** e, s)
        out.append(Vector((cx + ex, y, zc + ez)))
    return out


def foot(side):
    """一只脚：脚掌放样 + 踝柱 + 3 组脚趾，单独 3mm 体素融合。"""
    x = cfg.LEG_X * side
    seg = cfg.RING_SEG

    # 外观旋钮：脚尺寸（横向半宽 + 沿 -Y 的脚长）。高度 z 不动 ——
    # 脚底由 align_floor 归零、踝柱与腿末端接合都依赖 z，缩放 z 会连锁。
    k = charparams.get("appearance.foot_size_scale", _DEFAULT_FOOT_SIZE_SCALE)
    rows_src, toes_src = FOOT_ROWS, TOES
    if k != 1.0:
        rows_src = [(y * k, rx * k, zl, zh, p) for y, rx, zl, zh, p in FOOT_ROWS]
        toes_src = [(n, xo * k, y0 * k, y1 * k, r * k)
                    for n, xo, y0, y1, r in TOES]

    rings = [_y_ring(y, x, rx, zl, zh, p) for y, rx, zl, zh, p in rows_src]
    palm = loft(rings, name=f"foot_palm_{side}")

    # 踝柱：向上插进腿末端（腿到 z=0.075），让脚的顶面被腿包住，接缝藏在踝部
    ankle = tube([Vector((x, 0.016, 0.108)), Vector((x, 0.012, 0.070)),
                  Vector((x, 0.008, 0.045))],
                 [(0.030, 0.034), (0.032, 0.038), (0.033, 0.039)],
                 seg=seg, name=f"ankle_{side}")

    parts = [palm, ankle]
    for name, xo, y0, y1, r in toes_src:
        cx = x + xo * side
        ym = 0.5 * (y0 + y1)
        pts = [Vector((cx, y0, TOE_Z)), Vector((cx, ym, TOE_Z)),
               Vector((cx, y1, TOE_Z))]
        rad = [(r, r), (r, r), (r * 0.82, r * 0.82)]   # 趾尖收圆
        parts.append(tube(pts, rad, seg=20, name=f"toe_{name}_{side}"))

    ft = join(parts, name=f"foot_{side}")
    voxel_remesh(ft, size=FOOT_VOXEL)
    smooth(ft, factor=0.30, iterations=2)
    return ft


def align_floor(ob, target=0.0):
    """把对象整体沿 z 平移到最低点 = target。

    只对**脚**调用：脚底陷进地板 11.6mm 是 5mm 体素 + 平滑收缩的净结果，
    把脚整体平移到 z=0 就修好「脚陷地板」，同时腿、躯干、头一概不动，
    DESIGN §1.2 的腿长比 0.469 不受影响（DESIGN A4 的回退条件）。
    """
    zmin = min(v.co.z for v in ob.data.vertices)
    dz = target - zmin
    if abs(dz) > 1e-9:
        for v in ob.data.vertices:
            v.co.z += dz
        ob.data.update()
    return dz


def arm(side):
    """手臂。末端**渐细且变扁**，与手掌腕口对接（A1 返工）。

    为什么改：原实现末端是半径 24~25mm 的圆端帽，而手掌腕口只有 21mm 宽 / 16mm 厚，
    两者在同一平面（z=0.815）形成约 27mm 的环形台阶，侧前方看像「手腕断了」
    （验收实测 φ47.1mm 对 20.1mm）。

    改法（DESIGN §2.4.1 的路线 A：收细前臂末端，不改全局 voxel、不 join 手）：
      z 1.045 → 0.815 的 230mm 内把截面从 Ø66mm 圆渐变成 22×30mm 的扁椭圆，
      与手掌腕口（16×24mm）在厚/宽两个方向的径向差各约 3mm。
      路径端点 z 范围 [1.265, 0.815] 保持不变 —— 臂长不缩短，肘部形态不动。

    注意 tube 的 (rx, ry)：管沿 -Z 走时 rx 沿 x（掌厚方向）、ry 沿 y（掌宽方向），
    所以末端写成 (0.0110, 0.0150) 就是「厚 22mm、宽 30mm」的扁腕，解剖上手腕本就扁。

    v2（2026-11-05）：肩宽目标 1.8 头宽 = 0.405（cfg.SHOULDER_RX=0.202，判据 =
    2×SHOULDER_RX/头宽）。肩带宽度的承载者是三角肌——肩带（z 1.20~1.32）
    的网格最宽点就是上臂上段外缘（v1 实测 0.1857 = 0.135+0.045 再加体素外扩）。
    所以只把上段路径外移：z=1.220 处 x 0.135→0.154（外缘 0.199，网格 ≈0.202），
    1.265 处 0.095→0.114（藏在肩帽环 0.170 内侧），1.105 处 0.172→0.181；
    **肘以下一个数不动**（0.194/0.207/0.216/0.224/0.232）：腕点 0.232 是
    cfg.ARM_WRIST_X = hand.py WRIST_X = rig forearm tail 的三源锚点，动了
    要三处同步——本轮不动。
    """
    zs = [1.265, 1.220, 1.105, 1.045, 0.960, 0.905, 0.860, 0.815]
    xs = [0.114, 0.154, 0.181, 0.194, 0.207, 0.216, 0.224, 0.232]
    ys = [0.000, 0.002, 0.004, 0.006, 0.008, 0.010, 0.012, 0.014]
    rs = [(0.050, 0.050), (0.045, 0.045), (0.037, 0.037), (0.033, 0.033),
          (0.0290, 0.0310), (0.0245, 0.0275), (0.0165, 0.0210), (0.0105, 0.0150)]
    # 外观旋钮：手臂粗细。只乘截面半径，路径点一个不动（臂长/肘位不变）。
    k = charparams.get("appearance.arm_thickness_scale", _DEFAULT_ARM_THICKNESS_SCALE)
    if k != 1.0:
        rs = [(a * k, b * k) for a, b in rs]
    pts = [Vector((xs[i] * side, ys[i], zs[i])) for i in range(len(zs))]
    p, r = resample_path(pts, rs, 0.012)
    return tube(p, r, name=f"arm_{side}")


def hand(side):
    """已废弃：旧实现只有一根管 + 拇指，无手指（DESIGN §5.5 缺陷 1）。

    保留这个名字只为兼容可能的外部调用，内部转发到 lib/hand.py。
    注意返回的是**独立物体**，绝不能再 join 进 Body（会被 5mm 体素糊掉）。
    """
    import hand as handmod
    return handmod.build(side)


def neck():
    """独立颈柱：半径比躯干顶部小得多，靠体素融合长出斜方肌过渡。

    顶端必须**跟住头底**。`head_to_body_ratio` 是可调旋钮，头缩了下巴会上移
    （6.505→7.5 时从 1.3710 抬到 1.4039），而颈柱原来钉死在 1.394 ——
    实测在下巴底下留了 8.7mm 的缝，头看起来是浮在脖子上的。
    这里取 head_rows() 第一环的 z（头骨最低截面的高度）+ 8mm 插入量：
    多插进去的部分会被 5mm 体素融合吃掉，不会顶穿下巴。
    """
    import head as headmod
    base = 1.296
    top = headmod.head_rows()[0][0] + 0.008
    mid = base + (top - base) * 0.53      # 保持原来的颈根粗/颈顶细收分比例
    pts = [Vector((0.0, 0.018, base)), Vector((0.0, 0.020, mid)),
           Vector((0.0, 0.022, top))]
    rs = [(0.056, 0.052), (0.045, 0.043), (0.039, 0.039)]
    p, r = resample_path(pts, rs, 0.008)
    return tube(p, r, name="neck")


def build(voxel=0.0050, foot_voxel=FOOT_VOXEL, with_hands=True):
    """身体。返回 Body（躯干 + 颈 + 腿 + 脚 + 臂）。

    改造要点（DESIGN §2.4.1 / §2.4.2）：
    1. 脚**不**参与主融合：先 join 进 Body 之外单独走 3mm，再 join 回来。
    2. 手完全不进 Body，由 hand.build_pair() 另建 "Hands" 物体（2mm 网格）。
    3. sculpt_torso() 必须最先执行、签名不变 —— outfit._shirt() 依赖它。

    2026-11-04（路线 2 的 E 步，**已回退**）：
    试过 voxel 5.0→3.8mm、平滑 5→3 轮，想让锁骨/肩胛/膝踝的 2~3mm 结构
    不被抹平。结果是绑定回归 R3 交叉姿势的边长比从合格变成
    max 4.281（35°/15°，限 3.0）与 6.115（60°/30°，限 4.0），另新增
    3 个法线翻转 —— 体素越细，关节褶皱处越容易长出长条三角形，大幅扭转时
    被拉伸。身体被衣服遮住，这点细节收益看不见，代价是回归变红，所以回退。
    真正的解法是控制笼 + 细分（需要一张连通的身体拓扑图），本轮没做。
    """
    t = torso()
    sculpt_torso(t)
    parts = [t, neck()]
    feet = []
    for s in (-1, 1):
        parts.append(leg(s))
        parts.append(arm(s))
        feet.append(foot(s))

    body = join(parts, "Body")
    voxel_remesh(body, size=voxel)
    smooth(body, factor=0.5, iterations=5)

    # 脚：3mm 体素单独融，融完对齐地面，再拼回已定型的 Body（拼回后不再重网格）
    ft = join(feet, "feet")
    voxel_remesh(ft, size=foot_voxel)
    smooth(ft, factor=0.30, iterations=2)
    dz = align_floor(ft, 0.0)
    print(f"[stats] feet lift dz={dz * 1000.0:+.2f}mm (只抬脚，不动腿/踝)")
    body = join([body, ft], "Body")

    shade_smooth(body)

    if with_hands:
        import hand as handmod
        handmod.build_pair()
    return body
