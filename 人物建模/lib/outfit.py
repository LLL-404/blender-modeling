# -*- coding: utf-8 -*-
"""M5：服装。白衬衫 + 藏青百褶裙，全部从身体参数面 offset 出来。"""
import bpy
import math
from mathutils import Vector

import cfg
import optio
import charparams
import body as bodymod
from meshkit import (superellipse_ring, loft, resample, tube, resample_path,
                     join, shade_smooth, mesh_from, select_only, solidify,
                     recalc_normals)


# ---------------- 外观旋钮默认值（= 引入旋钮前的字面量） ----------------
_DEFAULT_SKIRT_PLEATS = 22
_DEFAULT_SKIRT_Z_BOTTOM = 0.650
_DEFAULT_SKIRT_AMP_SCALE = 1.0
_DEFAULT_SLEEVE_TIP_Z = 1.110
_DEFAULT_COLLAR_V_DEPTH = 0.022


def skirt_pleats():
    """百褶裙褶数（outfit.skirt_pleats，默认 22）。非正整数一律回退默认。"""
    n = int(charparams.get("outfit.skirt_pleats", _DEFAULT_SKIRT_PLEATS))
    return n if n >= 3 else _DEFAULT_SKIRT_PLEATS


def _shirt_grow(z):
    """衬衫相对 TORSO 参数面的外扩量（米），按 z 分三段给。

    一刀切 8mm 时第三带（锁骨下 z 1.18-1.22）只剩 8.5mm 净空，已在临界。
    但整体抬到 14mm 会把腰和肩一起撑成麻袋，所以分段：
      腰段 z<=1.10  → 10mm（腰本来就没有 sculpt 推量）
      胸段 1.15~1.19 → 14mm（胸型由 sculpt_torso 向前推 20mm，最吃余量）
      肩段 z>=1.23  → 12mm（肩颈收口，给多了会在颈根堆一圈）
    段间各留 40~50mm 线性过渡带，避免出现台阶状折痕。
    """
    if z <= 1.100:
        return 0.010
    if z < 1.150:
        return 0.010 + 0.004 * (z - 1.100) / 0.050      # 腰 → 胸
    if z <= 1.190:
        return 0.014                                    # 胸
    if z < 1.230:
        return 0.014 - 0.002 * (z - 1.190) / 0.040      # 胸 → 肩
    return 0.012                                        # 肩


def _front_y(cos, lo, hi, xc, tol):
    """z 带内、x≈xc 处最靠前（y 最小）的顶点 y；正面朝 -Y，y 越小越前。"""
    sel = [c.y for c in cos
           if lo <= c.z <= hi and abs(c.x - xc) <= tol and c.y < 0.0]
    return min(sel) if sel else None


def _param_torso_cos():
    """躯干参数面顶点（TORSO 环 + sculpt_torso），量完即删，不留在场景里。"""
    ob = bodymod.torso()
    bodymod.sculpt_torso(ob)
    cos = [v.co.copy() for v in ob.data.vertices]
    me = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me)
    return cos


def assert_clearance(shirt_cos):
    """内联净空自检：**只打印，绝不抛异常**（抛了会中断整条渲染链路）。

    口径：身体参数面（TORSO 环 + sculpt_torso）y − 衬衫环层 y。两者同源，
    所以这个数就是设计意义上的 grow，不含 solidify 的 ±2mm。
    真实 Body 经过 voxel+5 次 smooth 会收缩，实际净空比这里略大。
    """
    try:
        body_cos = _param_torso_cos()
    except Exception as exc:  # 自检不能把渲染拖死
        print(f"[fit][WARN] 参数面构建失败，跳过净空自检: {exc!r}")
        return
    bands = ((1.100, 1.140), (1.140, 1.180), (1.180, 1.220))
    worst = None
    for lo, hi in bands:
        row = []
        for xc, tol in ((0.000, 0.004), (-0.040, 0.012), (+0.040, 0.012)):
            by = _front_y(body_cos, lo, hi, xc, tol)
            sy = _front_y(shirt_cos, lo, hi, xc, tol)
            if by is None or sy is None:
                continue
            row.append((xc, by - sy))
        if not row:
            print(f"[fit] z=[{lo:.3f},{hi:.3f}] 采样缺失，无法判定")
            continue
        xw, m = min(row, key=lambda t: t[1])
        print(f"[fit] z=[{lo:.3f},{hi:.3f}] margin={m * 1000:+.1f}mm "
              f"(at x={xw * 1000:+.0f}mm)")
        if worst is None or m < worst:
            worst = m
    if worst is not None and worst < 0.010:
        print(f"[fit][FAIL] 最小净空 {worst * 1000:+.1f}mm < 10.0mm "
              f"（参数面口径，真实网格因 voxel 收缩会略大）")


def _shirt_neck_ring(z_back=1.332, z_front=1.312, rx=0.066, ry=0.056, cy=0.002):
    """衬衫领口收口环：**V 形**，前中降到 z_front。

    为什么必须 V 形（D3 实测教训）：衬衫肩部在 z 1.305~1.332 之间从 150mm
    急收到 66mm，是一条很陡的收口锥。翻领前中无论怎么降，只要半径 <120mm
    就整片沉进衬衫内部 —— D3 之前「前领 V 深 24mm」在画面上完全不存在，
    探针量到的 37.8mm 只是领圈上下两环的高度差。收口环本身开 V，翻领的
    V 口才有地方露出来。
    """
    pts = []
    seg = cfg.RING_SEG
    for i in range(seg):
        a = 2.0 * math.pi * i / seg
        d = 0.5 * (1.0 - math.sin(a))       # 前中=1、后中=0
        z = z_back + (z_front - z_back) * d
        ca, sa = math.cos(a), math.sin(a)
        pts.append(Vector((rx * ca, cy + ry * sa, z)))
    return pts


def _shirt():
    # 用 body.torso_rows() 而不是 import 进来的 TORSO 常量：肩/腰/髋旋钮
    # 改了身体派生宽后，衬衫必须跟着一起变宽，否则会立刻穿模。
    rows = resample(bodymod.torso_rows(), "z", cfg.RESAMPLE_STEP)
    rings = []
    for z, rx, ryf, ryb, cy, p in rows:
        if z < 1.045 or z > 1.326:
            continue
        grow = _shirt_grow(z)
        rings.append(superellipse_ring(z, rx + grow, ryf + grow, cy - 0.001,
                                       0.0, p, cfg.RING_SEG, ry_back=ryb + grow))
    # 领口收口：从肩顶收到颈根，避免肩部出现一张平盖。
    # D3：收口环做成 **V 形**（前中降到 1.312），否则翻领前中会被这条水平
    # 环整片埋住（见 _shirt_neck_ring 的说明）。
    rings.append(_shirt_neck_ring())
    ob = loft(rings, cap_start=False, cap_end=False, name="shirt")
    bodymod.sculpt_torso(ob)   # 胸腹的软位移必须同步，否则胸前会被顶穿
    shirt_cos = [v.co.copy() for v in ob.data.vertices]   # solidify 之前的环层
    solidify(ob, 0.004)
    assert_clearance(shirt_cos)
    return ob


def _cuff_ring(side, tip_z=1.110):
    """袖口卷边：**内缘略厚、外缘略薄**的翻折环（不是一根等径箍）。

    基准口径（2026-11-01 实测，别再用 DESIGN 里的 47mm）：
      · 47.00mm 是袖筒的**环层**半径（solidify 之前）；
      · solidify 之后袖筒末端外表面实测 **48.34mm** —— 这才是肉眼可见的表面。
    所以「卷边凸出 2~4mm」必须相对 48.34mm 算，相对 47mm 算会把 1.65mm 读成 3.2mm。

    三段半径（Solidify 0.002 实测外偏移 +1.0mm）：
        inner −10mm → r 50.4 → 可见凸出 ≈ +2.50mm（内缘压住袖筒边）
        mid    −4mm → r 50.6 → 可见凸出 ≈ +3.26mm（过渡）
        outer   0mm → r 49.5 → 可见凸出 ≈ +2.13mm（布边收薄）
    注：斜面处 Solidify 的法线带倾斜分量，径向只增约 0.7mm（不是 1.0mm），
    所以实测比「r + 1.0mm」低 0.3~0.6mm —— 上面的可见值都是 probe 实测量级。
    内缘 − 外缘 = 0.40mm，跨 4mm 轴向长度 → 坡度约 5.7°，形成折返的明暗转折。
    任意一环内表面（r−1mm）都不低于袖筒外表面 48.34mm，不会嵌进袖筒。
    """
    s = side
    tip = Vector((0.169 * s, 0.006, tip_z))
    axis = Vector((-0.075 * s, 0.050, -0.996)).normalized()
    pts = [tip - axis * 0.010, tip - axis * 0.004, tip]
    rs = [(0.0504, 0.0504), (0.0506, 0.0506), (0.0495, 0.0495)]
    ob = tube(pts, rs, seg=40, name=f"cuff_{s}",
              cap_start=False, cap_end=False)
    solidify(ob, 0.002)
    return ob


def _sleeve(side, solid=True, cuff=True):
    """袖筒。末端**必须落在手臂轴线上**，半径才收得下来。

    实测（probe 同轴同面，袖口平面 z=1.110）：该处上臂半径 **38.8mm**
    （`[fit]`/probe 打印值，不是 body.arm 表在 z=1.220 的 45mm）。
      · 47mm → 间隙 **+8.2mm**，落在 [7,10]mm 区间中部，上下各留约 1.2mm 余量；
      · 53mm → 间隙 **+14.2mm**，**超出 [7,10] 上限** —— 这才是没用 53mm 的
        真实理由（更松，不是更紧）。
    「53mm 会切进上臂」是**另一回事**，只在末端点仍留在原位 (x=0.190) 时成立：
    该处手臂中心 x≈0.169、截面 x∈[0.131, 0.207]，袖口内壁 0.190−0.053=0.137
    正落在这段区间里，切进去约 6.3mm；末端点贴回轴以后这个问题就不存在了，
    53mm 只会更松。两种情形必须分开看，不能混成一句。
    旧 60mm 的由来：末端外撇 21mm 时，60mm 是"刚好包住手臂"的最小值
    （内侧余隙仅约 1mm、外侧空腔 40mm 且 cap_end=False 会露出袖内），不是随手取宽。
    cap_end=True 封住袖口，配合 _cuff_ring() 的卷边（实测外表面 50.2mm、
    相对袖筒凸出 3.2mm），侧面看不到袖内空腔。
    solid=False / cuff=False 只给 _stageA/a4_fit_probe.py 量测用，
    默认值与 m5_outfit 的调用完全一致。
    """
    s = side
    # 外观旋钮：sleeve_length = 袖口末端 z（默认 1.110 = 引入旋钮前的字面量）。
    z_tip = charparams.get("outfit.sleeve_length", _DEFAULT_SLEEVE_TIP_Z)
    pts = [Vector((0.105 * s, 0.000, 1.270)),
           Vector((0.140 * s, 0.002, 1.215)),
           Vector((0.172 * s, 0.004, 1.150)),
           Vector((0.169 * s, 0.006, z_tip))]
    rs = [(0.062, 0.062), (0.058, 0.058), (0.055, 0.055), (0.047, 0.047)]
    p, r = resample_path(pts, rs, 0.012)
    ob = tube(p, r, seg=40, name=f"sleeve_{s}", cap_start=True, cap_end=True)
    if not solid:
        return ob
    solidify(ob, 0.004)
    parts = [ob]
    if cuff:
        parts.append(_cuff_ring(s, z_tip))
    if len(parts) == 1:
        return parts[0]
    return join(parts, name=f"sleeve_{s}")


COLLAR_A0, COLLAR_A1 = 279.0, 621.0   # 开弧：绕过正后方，前中留 ±9° 开口


def _collar_arc(rx, ry, cy, z_back, z_front, seg):
    """一圈**开弧**：从 a=279° 绕过后脑到 621°(=261°)，z 随「离正后方」线性下降。

    角度约定同 superellipse_ring：0°=+x（右）、90°=+y（后）、270°=−y（前）。
    d=0 在正后方、d=1 在正前方，于是后领高、前领低，中间两翼平滑过渡。
    缺口取 ±9°（不是 ±20°）：r=66mm 时 9° 弧长 ≈10mm、x 半宽 ≈10mm，
    刚满足「前中 |x|<6mm 无顶点」的开口判据，又不会裂成一个大豁口。
    """
    pts = []
    for i in range(seg):
        a_deg = COLLAR_A0 + (COLLAR_A1 - COLLAR_A0) * i / (seg - 1)
        a = math.radians(a_deg)
        dd = abs(((a_deg - 90.0) + 180.0) % 360.0 - 180.0)   # 0(后)..180(前)
        d = dd / 180.0
        z = z_back + (z_front - z_back) * d
        pts.append(Vector((rx * math.cos(a), cy + ry * math.sin(a), z)))
    return pts


def _collar():
    """衬衫翻领：后领高、前领开 V、前中留**真空开口**。

    原实现是 3 个同心**闭合**环（z 1.300/1.322/1.336，rx 70/60/52mm），
    放样出来是一个套在脖子上的圈，视觉上是"颈圈"而不是衬衫领 —— 因为
    它既没有前后落差，也没有前中开口，更没有翻折边。

    现在的截面是「立起 → 翻下」三层（半径/高度单位是米）：
        领根   rx 58 ry 48   z 后 1.328 → 前 1.308   （藏进衬衫 V 形领口内侧）
        翻折线 rx 64 ry 53   z 后 1.342 → 前 1.320   （领座顶 = 后领高）
        外翻缘 rx 76 ry 64   z 后 1.334 → 前 1.312   （领尖外翻 12mm，略降）
    于是后领高 1.342、前领口 1.320，V 深 22mm（要求 ≥12）。

    **不能用 `meshkit.loft` 铺这三行**：loft 的桥接是 `j2=(j+1)%seg`，永远
    首尾闭合，会把前中缺口的两侧硬连成一张横跨的布（顶点仍为空、面却闭合，
    探针照样能报「开口」—— 典型假达标）。这里按「角度 × 3 行」手搓四边形，
    开弧两端（前中缺口两侧）保持开放，交给 Solidify 的 use_rim 缝边，
    边界边数仍为 0。
    """
    seg = 44
    # 外观旋钮：collar_v_depth = 前领相对后领的下降量（默认 0.022）。
    # 默认值走原字面量（1.308 / 1.320 / 1.312），不经过减法，避免 1ulp 漂移。
    dv = charparams.get("outfit.collar_v_depth", _DEFAULT_COLLAR_V_DEPTH)
    if dv == _DEFAULT_COLLAR_V_DEPTH:
        rows = [
            _collar_arc(0.058, 0.048, 0.003, 1.328, 1.308, seg),   # 领根
            _collar_arc(0.064, 0.053, 0.003, 1.342, 1.320, seg),   # 翻折线
            _collar_arc(0.076, 0.064, 0.003, 1.334, 1.312, seg),   # 外翻边缘
        ]
    else:
        k = dv / _DEFAULT_COLLAR_V_DEPTH
        rows = [
            _collar_arc(0.058, 0.048, 0.003, 1.328, 1.328 - 0.020 * k, seg),
            _collar_arc(0.064, 0.053, 0.003, 1.342, 1.342 - 0.022 * k, seg),
            _collar_arc(0.076, 0.064, 0.003, 1.334, 1.334 - 0.022 * k, seg),
        ]
    verts = []
    for r in rows:
        verts.extend(r)
    faces = []
    for k in range(seg - 1):                  # 开弧：k 只到 seg-2，不连回起点
        for i in range(len(rows) - 1):
            a = i * seg + k
            b = (i + 1) * seg + k
            faces.append((a, a + 1, b + 1, b))
    ob = mesh_from(verts, faces, name="collar")
    recalc_normals(ob)
    solidify(ob, 0.004)
    return ob


SKIRT_CY = 0.006            # 裙子环的前后中心偏移（与 _skirt() 里一致）
SKIRT_PLEATS = skirt_pleats()   # 外观旋钮 outfit.skirt_pleats（默认 22）
SKIRT_POINTS_PER_PLEAT = 8  # 每褶采样点数：48 段时每褶仅 2.18 点，峰谷混叠
SKIRT_SEG = SKIRT_PLEATS * SKIRT_POINTS_PER_PLEAT   # 默认 22×8 = 176
SKIRT_HARM2 = 0.25          # 二次谐波系数：峰更尖、谷更平
SKIRT_WAIST_MARGIN = 0.0030   # 裙腰环层相对躯干参数面的最小净空（可被 opt/best.json 覆盖）
SKIRT_INNER_MODE = "valley"   # 净空口径：valley = 波谷也留够；peak = 只保波峰

SKIRT_WAIST_BANDS = ((0.920, 0.960), (0.960, 1.000),
                     (1.000, 1.040), (1.040, 1.060))

# ---------- T22：裙腰「侧面最外表面 gap」口径 ----------
# 量法（leader 2026-11-01）：|v.z − z0| < 12mm 切片，背侧 max(y) / 腹侧 min(y)，
# 最终网格（Outfit 已 solidify）减 Body 最终网格。验收窗 [5,12]mm，中值 8.5mm。
# 反解 rx/ry 只能保证「参数面最外点被包住」，max() 一取就把整环撑成桶：
# z=1.045 的 ry 从 88 被推到 117.6，而体背只有 85.3 → 实测背侧 gap 42.4mm。
SKIRT_SIDE_GAP_TARGET = 0.0085            # 最终网格口径的目标中值（[5,12] 中值）
SKIRT_SIDE_GAP_LO, SKIRT_SIDE_GAP_HI = 0.005, 0.012
SKIRT_SHELL_ALLOW = 0.0020                # Solidify 0.004/offset 0 → 外表面 +2mm
SKIRT_MESH_SHRINK = 0.0015                # Body 体素+smooth 比参数面内缩（实测 1.2~2.7mm）
SKIRT_RING_GAP = SKIRT_SIDE_GAP_TARGET - SKIRT_SHELL_ALLOW - SKIRT_MESH_SHRINK  # 5.0mm
SKIRT_GAP_ROUNDS = 2                      # 量 → 收 → 再量，最多 2 轮
SKIRT_GAP_WINDOW = 0.012                  # 与 leader 量法完全相同的切片半宽
SKIRT_WAIST_FIT = (0.920, 1.060)          # 参与第二轮收缩的环（含 0.920 髋环：
                                          # z=0.94 的 gap 由 0.920/0.980 两环弦线决定）

# 最近一次 assert_skirt_clearance() 的实测结果，供 opt/eval_geom.py 取数
# （省掉「为了量净空再复算一遍躯干参数面」的重复构建）。键 = (zlo, zhi)，
# 值 = {"net": 该带最小净空(米), "row": [(x, net), ...]}。
LAST_SKIRT_NETS = {}


def _skirt_p(z):
    """裙子截面指数：腰段与躯干同为 2.2，往裙摆回落到 2.0（保持原椭圆摆）。

    为什么腰段必须跟着躯干用超椭圆：躯干 p=2.2 比正椭圆"方"，侧前方
    （x≈50mm）的身体表面比同 rx/ry 的椭圆更靠前。拿正椭圆去包，正面会被
    撑鼓一大截 —— 实测 z=1.045 环的 ry 要 88→115mm 才勉强包住，正面白白
    多出 +21.7mm 净空（裙腰像套了个桶）。形状对齐后各点净空才是均匀的。
    """
    if z >= 0.920:
        # T22：腰段指数 2.2 → 2.6 渐变（到 1.045 环）。躯干是 p=2.2，但胸在
        # x≈±42mm 处比椭圆侧壁多鼓 10mm（z=1.05：中心前 −85，x=42.6 处 −94.9）；
        # p=2.2 的裙子要满足胸的 5mm 净空，中心就得松 22mm（验收口径报 12.5mm）。
        # 侧壁抬"方"之后同一个胸净空下中心只松 ~16mm，两侧差从 6mm 降到 2mm。
        # 0.850 及以下的裙摆指数不受影响（仍走下面的 2.0→2.2 回落），D5 褶形不变。
        return 2.2 + 0.4 * max(0.0, min(1.0, (z - 0.920) / 0.125))
    # 外观旋钮：裙摆底 z 变了，指数回落区间跟着变（默认 0.650 走原式）
    zb = charparams.get("outfit.skirt_length", _DEFAULT_SKIRT_Z_BOTTOM)
    if zb == _DEFAULT_SKIRT_Z_BOTTOM:
        t = (z - 0.650) / 0.270
    else:
        t = (z - zb) / (0.920 - zb)
    return 2.0 + 0.2 * max(0.0, min(1.0, t))


def _waist_window_points(body_cos, z):
    """体表在 |z − z0| < 12mm 窗口内的点（与 leader 量法**同一个窗口**）。

    为什么要窗口而不是本 z 的点：验收量的是窗口极值，环按本 z 反解会系统性
    偏紧 2~3mm。点数不足 8 个返回 None（裙腰兜底跳过这一环）。
    """
    sel = [c for c in body_cos if abs(c.z - z) < SKIRT_GAP_WINDOW]
    return sel if len(sel) >= 8 else None


def _fit_skirt_waist(zs, rxs, rys, amps, body_cos):
    """裙腰环半径：①参数面兜底 ≥ inner；②按侧面实测 gap 收到 [5,12]mm。

    为什么必须兜底：裙子原来是"按髋部参数表 offset"，而躯干前面有
    sculpt_torso() 的胸腹推力（z=1.02 处约 9mm），表里的 ry 并没有把这部分算进去，
    于是裙腰在 z 1.00~1.04 嵌进躯干 1.4~5.6mm（probe 与验收都实测到）。
    第一轮改成显式净空：逐环取躯干参数面在该 z 带的最外点，反解出超椭圆需要的
    rx/ry；波谷（amp 最小半径处）也要留够 margin，所以 inner = margin + amp。

    第二轮（T22）解决的是第一轮的**反向**问题：max() 取的是"带内最外点"，
    可 z=1.045 那一段再往上就是胸部，参数面在 z 1.03 处只有 83.6mm，而环被
    撑到 ry=117.6 → 实测背侧 gap 42.4mm，图上就是"筒子套在外面"。
    第二轮直接量**最终网格同款口径**的窗口极值，把环收到目标 gap。

    三个关键取舍（都是实测逼出来的，不是审美）：

      1. **背/腹半径分开**（ryb ≠ ryf）。体表不以 SKIRT_CY 为中心：z=1.02 处
         体心 −2.4mm、环心 +6.0mm，这 8.4mm 偏心让背侧比腹侧多 17mm gap；
         z=1.045 更极端 —— 最靠前的点是**胸部**（x=+42.6, y=−95.2），而背侧
         最靠后只有 +85.1，单个 ry 无论取多少都无法让两侧同时落进 [5,12]。
         分开之后背侧跟背、腹侧避胸，两侧各自可解。
      2. **腰段褶幅归零**。带褶幅时谷 = 基线 − 0.75·amp，而验收量的是峰
         （正面中线/背中线上 phase 落在峰），收到 8.5mm 的峰会让谷只剩
         8.5 − 2·amp ≈ 2~4mm，必然多出一圈穿模。归零后峰谷重合，整圈均匀。
         褶从 z=0.850 环（amp 6.8mm）往上渐隐到 0，D5 的褶峰判据在裙摆，
         不受影响。
      3. **rx 按侧向 max|x| 单独反解**，不按 ry 的比例缩：背侧要多收 34mm、
         侧向只多 12mm，等比缩会把髋部在 x 上压进身体 30mm。

    `z<=0.92 的裙摆保持原表不动` 这条在 T22 放宽到 **0.920 环也参与**：z=0.94
    的 gap 由 0.920/0.980 两环的弦线决定（体表 0.92→0.98 是 112.5→90.0 的
    单调曲线，弦在 z=0.94 处比真值高 0.9mm），不放 0.920 的话 0.94 只能落在
    14mm 以上。0.850 及以下的裙摆仍未参与，D5 的褶形不受影响。
    """
    out_rx = list(rxs)
    out_ryf, out_ryb = list(rys), list(rys)
    out_amp = list(amps)               # 第二轮把腰段褶幅归零
    # 参数注入：best.json 不存在时两者恒等于模块常量，行为与手调版逐位一致。
    margin = optio.param("skirt_margin", SKIRT_WAIST_MARGIN)
    mode = optio.param("skirt_inner_mode", SKIRT_INNER_MODE)
    if mode not in ("valley", "peak"):
        mode = SKIRT_INNER_MODE
    peak_gain = 1.0 + SKIRT_HARM2          # 波峰相对基半径的增益 = 1.25
    for i, z in enumerate(zs):
        if not (0.960 <= z <= 1.060):
            continue
        # 量测区间按「相邻环中点」切分，别一路向上看 30mm —— 裙腰顶端
        # (z=1.045) 再往上就是胸部，裙子根本不覆盖它，把它算进来会把
        # ry 从 111 直接撑到 128（正面白鼓 20mm）。顶端环只额外向上看 15mm。
        hi = (zs[i - 1] + z) / 2.0 if i > 0 else z + 0.015
        lo = (z + zs[i + 1]) / 2.0 if i + 1 < len(zs) else z - 0.020
        band = [c for c in body_cos if lo <= c.z <= hi]
        if len(band) < 8:
            continue
        if mode == "peak":
            inner = margin - peak_gain * amps[i]   # 只保波峰不碰身体
        else:
            inner = margin + amps[i]               # 波谷也不能跌破最小净空
        # 第一轮兜底：偏保守（背/腹共用一个 ry），第二轮再按实测分侧收紧。
        p = _skirt_p(z)
        out_rx[i] = max(out_rx[i], max(abs(c.x) for c in band) + inner)
        need_ry = max(out_ryf[i], out_ryb[i])
        for c in band:
            ax = abs(c.x) / out_rx[i]
            if ax >= 1.0:
                continue
            s = (1.0 - ax ** p) ** (1.0 / p)     # 超椭圆在 x 处的 y 系数
            if s < 1e-6:
                continue
            if c.y < 0.0:
                need = (SKIRT_CY - c.y + inner) / s      # 正面：y 要比身体更靠前
            else:
                need = (c.y + inner - SKIRT_CY) / s      # 背面：对称
            if need > need_ry:
                need_ry = need
        out_ryf[i] = out_ryb[i] = need_ry
        print(f"[fit] skirt_ring z={z:.3f} rx {rxs[i] * 1000:.1f}->"
              f"{out_rx[i] * 1000:.1f} ry {rys[i] * 1000:.1f}->"
              f"{need_ry * 1000:.1f}mm n={len(band)} "
              f"inner={inner * 1000:+.2f}mm mode={mode}")

    # ---------------- 第二轮：按实测侧面 gap 收缩 ----------------
    # 环层（solidify 前）目标 gap：最终网格 8.5mm − 壳外扩 2mm − 体素内缩 1.5mm。
    # 保留 best.json 的 skirt_margin 语义（margin 越大越松），但不允许把
    # 「已达标」的窗撑破：环层目标取两者较大者。
    ring_gap = max(SKIRT_RING_GAP, margin - SKIRT_SHELL_ALLOW - SKIRT_MESH_SHRINK)
    for rnd in range(1, SKIRT_GAP_ROUNDS + 1):
        for i, z in enumerate(zs):
            if not (SKIRT_WAIST_FIT[0] <= z <= SKIRT_WAIST_FIT[1]):
                continue
            win = _waist_window_points(body_cos, z)
            if win is None:
                continue
            bmax = max(c.y for c in win)
            bmin = min(c.y for c in win)
            gb = SKIRT_CY + out_ryb[i] - bmax        # 背侧 gap（环层，收前）
            gf = bmin - (SKIRT_CY - out_ryf[i])      # 腹侧 gap（环层，收前）
            gx = out_rx[i] - max(abs(c.x) for c in win)
            # 腰段褶幅归零：峰谷重合 → 收到目标 gap 时整圈都不会穿模
            out_amp[i] = 0.0
            out_rx[i] = max(abs(c.x) for c in win) + ring_gap
            # 逐点反解（不是只看极值点）：胸在 x=42.6 处比中心更靠前，
            # 只按最前点算会把整环撑到 8.5+6mm；按每个点的超椭圆系数 s(x)
            # 反解，才能让"最紧的那个点"刚好拿到 ring_gap。
            p = _skirt_p(z)
            ryb_need, ryf_need = 0.0, 0.0
            for c in win:
                ax = abs(c.x) / out_rx[i]
                if ax >= 1.0:
                    continue
                s = (1.0 - ax ** p) ** (1.0 / p)
                if s < 1e-6:
                    continue
                if c.y < 0.0:
                    ryf_need = max(ryf_need, (SKIRT_CY - c.y + ring_gap) / s)
                else:
                    ryb_need = max(ryb_need, (c.y + ring_gap - SKIRT_CY) / s)
            # 直接取逐点反解，不再和第一轮比较：第一轮的 need 是用**收之前**
            # 的 rx 算的 s(x)，rx 收小后同一个点需要的 ry 更大（实测 99.3 vs
            # 100.7），min() 会把环留在「用旧 rx 算的、现在不够」的值上 ——
            # z=1.02 的最近距离因此只剩 1.3mm（要求 >=2mm）。
            out_ryb[i] = ryb_need
            out_ryf[i] = ryf_need
            gb2 = SKIRT_CY + out_ryb[i] - bmax
            gf2 = bmin - (SKIRT_CY - out_ryf[i])
            gx2 = out_rx[i] - max(abs(c.x) for c in win)
            print(f"[fit] skirt_gap r{rnd} z={z:.3f} 环层 gap 背 {gb * 1000:+6.1f}"
                  f"->{gb2 * 1000:+5.1f} 腹 {gf * 1000:+6.1f}->{gf2 * 1000:+5.1f} "
                  f"侧 {gx * 1000:+6.1f}->{gx2 * 1000:+5.1f} | "
                  f"rx {rxs[i] * 1000:.1f}->{out_rx[i] * 1000:.1f} "
                  f"ry(背/腹) {rys[i] * 1000:.1f}->{out_ryb[i] * 1000:.1f}"
                  f"/{out_ryf[i] * 1000:.1f} amp->0")
    return out_rx, out_ryf, out_ryb, out_amp


def assert_skirt_clearance(skirt_cos, body_cos):
    """裙腰净空自检：**只打印，绝不抛异常**（与 assert_clearance 同风格）。

    口径：躯干参数面 y − 裙子环层 y，正面朝 -Y。负值 = 裙子嵌进躯干。
    环层在 solidify 之前，所以这里比最终网格保守约 2mm（solidify 会把外表面
    再往前推 2mm），probe 用最终网格复测时数值会略大。
    """
    if body_cos is None:
        print("[fit][WARN] 裙腰自检跳过：躯干参数面不可用")
        return
    LAST_SKIRT_NETS.clear()
    worst = None
    for lo, hi in SKIRT_WAIST_BANDS:
        row = []
        for xc, tol in ((0.000, 0.004), (-0.040, 0.012), (+0.040, 0.012)):
            by = _front_y(body_cos, lo, hi, xc, tol)
            sy = _front_y(skirt_cos, lo, hi, xc, tol)
            if by is None or sy is None:
                continue
            row.append((xc, by - sy))
        if not row:
            print(f"[fit] skirt z=[{lo:.3f},{hi:.3f}] 采样缺失，无法判定")
            continue
        xw, m = min(row, key=lambda t: t[1])
        LAST_SKIRT_NETS[(lo, hi)] = {"net": m, "row": row}
        detail = " ".join(f"x={r[0] * 1000:+.0f}:{r[1] * 1000:+.1f}"
                          for r in row)
        print(f"[fit] skirt z=[{lo:.3f},{hi:.3f}] net={m * 1000:+.1f}mm "
              f"(at x={xw * 1000:+.0f}mm) | {detail}")
        if worst is None or m < worst:
            worst = m
    if worst is not None and worst < 0.002:
        print(f"[fit][FAIL] 裙腰最小净空 {worst * 1000:+.1f}mm < +2.0mm")


def _skirt(solid=True):
    """百褶裙。褶不是纯正弦：峰要硬、谷要圆，且正面中线必须落在褶峰上。

    `solid=False` 只给 _stageD/d_probe.py 量褶形用（与 `_sleeve(solid=False)`
    同一约定）：不 solidify 时顶点数 = 8 环 × SKIRT_SEG，最后一环就是干净的
    裙摆单环；solidify 之后内外两层 z 只差约 1mm，按 z 窗口取样必然混层。

    三个改动（D5）：
      1. 环采样 cfg.RING_SEG=48 → SKIRT_SEG=176（22 褶 × 8 点）。48 段时
         每褶只有 2.18 个点，峰谷根本采不出来，量出来的"峰谷差"是混叠值。
      2. 相位 +π：a=3π/2（正面中线，|x|≈0 且 y 最小）处 22a+π=34π → cos=1，
         中线成为褶峰；旧相位那里是 cos(33π)=−1，正好是谷。
      3. 叠加二次谐波 0.25·cos(2θ)：θ=0 处 f''=−2（尖），θ=π 处 f''=0（平），
         即"峰硬谷圆"；峰谷差仍是 2·amp（峰 1.25amp、谷 −0.75amp）。
    """
    # T22：髋环 0.920 → **0.930**。体表正面在 0.92→0.98 是 -103.1→-91.2 的
    # 强凸曲线，弦在 0.94（验收高度之一）比真值高 10mm：两个环怎么反解，0.94
    # 的 gap 都压不到 5mm（实测 4.6）。把髋环放到 0.930（凸起最靠前处附近），
    # 0.94 距环 10mm，弦误差从 10mm 降到 0.9mm，环数不变、顶点数不变。
    zs = [1.045, 1.020, 0.980, 0.930, 0.850, 0.780, 0.710, 0.650]
    # 外观旋钮：skirt_length = 裙摆最低 z（默认 0.650 = 引入旋钮前的字面量）。
    # 按「裙腰 1.045 固定、向下线性拉伸」重映射，默认值不走这步（逐位不变）。
    zb = charparams.get("outfit.skirt_length", _DEFAULT_SKIRT_Z_BOTTOM)
    if zb != _DEFAULT_SKIRT_Z_BOTTOM:
        kz = (1.045 - zb) / (1.045 - _DEFAULT_SKIRT_Z_BOTTOM)
        zs = [1.045 - (1.045 - z) * kz for z in zs]
    rxs = [0.112, 0.118, 0.130, 0.148, 0.170, 0.190, 0.210, 0.226]
    rys = [0.088, 0.094, 0.104, 0.118, 0.134, 0.150, 0.166, 0.180]
    pleats = SKIRT_PLEATS
    # 外观旋钮：skirt_amplitude_scale 乘褶幅（默认 1.0，×1.0 精确）
    ak = charparams.get("outfit.skirt_amplitude_scale", _DEFAULT_SKIRT_AMP_SCALE)
    amps = [(0.002 + 0.011 * (i / (len(zs) - 1)) ** 1.4) * ak
            for i in range(len(zs))]

    try:
        body_cos = _param_torso_cos()
    except Exception as exc:      # 兜底失败也不能拖死渲染
        print(f"[fit][WARN] 躯干参数面构建失败，裙腰跳过兜底: {exc!r}")
        body_cos = None
    ryf = list(rys)                # 腰段背/腹分开（第二轮按实测反解）
    ryb = list(rys)
    if body_cos is not None:
        rxs, ryf, ryb, amps = _fit_skirt_waist(zs, rxs, rys, amps, body_cos)

    rings = []
    for i, z in enumerate(zs):
        amp = amps[i]
        p = _skirt_p(z)
        e = 2.0 / p
        ring = []
        for k in range(SKIRT_SEG):
            a = 2.0 * math.pi * k / SKIRT_SEG
            th = pleats * a + math.pi          # 相位：正面中线为峰
            wave = amp * math.cos(th) + amp * SKIRT_HARM2 * math.cos(2.0 * th)
            ca, sa = math.cos(a), math.sin(a)
            xk = math.copysign(abs(ca) ** e, ca)
            yk = math.copysign(abs(sa) ** e, sa)
            # 背/腹半径分开：腰段要"贴背 + 避胸"，单个 ry 无解（见 fit 说明）
            r_y = ryb[i] if yk > 0.0 else ryf[i]
            ring.append(Vector(((rxs[i] + wave) * xk,
                                SKIRT_CY + (r_y + wave) * yk, z)))
        rings.append(ring)
    ob = loft(rings, cap_start=False, cap_end=False, name="skirt")
    skirt_cos = [v.co.copy() for v in ob.data.vertices]   # solidify 之前的环层
    if solid:
        solidify(ob, 0.004)
    assert_skirt_clearance(skirt_cos, body_cos)
    return ob


def build(mats):
    parts = [_shirt(), _collar(), _skirt()]
    for s in (-1, 1):
        parts.append(_sleeve(s))
    cloth = join(parts, "Outfit")
    shade_smooth(cloth)
    cloth.data.materials.append(mats["cloth_white"])
    idx = len(cloth.data.materials)
    cloth.data.materials.append(mats["cloth_navy"])

    # 裙子原来的面索引在 join 之后被重排，直接按 z 重新分材质
    for p in cloth.data.polygons:
        cz = sum(cloth.data.vertices[v].co.z for v in p.vertices) / len(p.vertices)
        p.material_index = 1 if cz < 1.040 else 0
    return cloth