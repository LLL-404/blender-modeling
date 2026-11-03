# -*- coding: utf-8 -*-
"""M4：头发。发帽 + 后发片 + 发束 + 刘海 + 侧发 + 呆毛。

思路：发丝全部是放样出来的椭圆截面管，宽度远大于厚度，所以
正面看是发片，侧面看有厚度；后脑用一片开缝曲面 + Solidify 兜住。
"""
import bpy
import bmesh
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


# ---------------- 头发坐标 -> 当前头骨的映射 ----------------
# 为什么需要：本文件里后发片、发束、刘海、侧发、呆毛的坐标全部是**按旧头**
# （下巴 1.371、头宽 217mm）手写的绝对量。2026-11-03 把 head_to_body_ratio
# 从 6.505 改到 7.5 后头缩了 13%，这些坐标一个都没跟着动，实测后果：
# 发帽在头顶区比头骨大 35.9mm（像套了个头盔）、后发 z 范围 0.9894~1.6665
# 一个数都没变。所以所有硬编码的 z 过 _hz()、横向量过 _hr()。
#
# 归一化基准是 `_DEFAULT_HEAD_SCALE`（1.063，= 引入旋钮前那一版头骨的放大倍数），
# 所以默认 profile 下 k 恰好等于 1.0，三条映射都是恒等 —— 不破坏「默认逐位一致」。
def _hk():
    """当前头骨相对「写这些坐标时那一版头骨」的缩放比。默认 profile 下 = 1.0。"""
    return headmod._head_scale() / headmod._DEFAULT_HEAD_SCALE


def _hz(z):
    """绝对 z 映射：以头顶为锚，按 _hk() 缩短/拉长「离头顶的距离」。

    为什么以头顶为锚而不是等比缩放全表：发尾在 z≈0.99，若按 1.3836 那个
    锚点线性缩放，发尾会被抬 51mm（头发肉眼变短一截）；以头顶为锚时
    头顶钉死、发尾只随比例微动，长发长度基本守恒。
    """
    k = _hk()
    if k == 1.0:
        return z
    top = cfg.HEIGHT
    return top - (top - z) * k


def _hr(v):
    """横向长度（半径、x、y）按同一比例映射。"""
    k = _hk()
    return v if k == 1.0 else v * k


_CAP_SMOOTH_ITERS = 3      # 主体环拉普拉斯轮数（原 Smooth 修改器的 iterations）
_CAP_SMOOTH_FACTOR = 0.35  # 每轮位移比例（原修改器的 factor）


def _cap():
    """发帽按头骨轮廓外扩 6mm 放样，保证任何高度都不会被头骨顶穿。

    用 headmod.head_rows() 而**不是**模块级 `head.HEAD`：后者是 import 时
    定型的快照，height / head_width_scale 在本进程内被改过时不会跟随。
    """
    # 步长 0.010 → 0.004（2026-11-03）：颅顶那一刀收得极陡（1.6034 rx=64.5mm
    # → 1.6200 rx=25.8mm，16.6mm 内掉 39mm）。10mm 采样会把中间行整个跳过，
    # 剩一条 16.6mm 高的**圆台**，圆台顶上再接球冠，正面渲成一颗「馒头」
    # （out/m4_face_front.png 头顶那个凸包）。4mm 才跟得上头骨自身的收口曲线。
    rows = resample(headmod.head_rows(), "z", 0.004)
    rings = []
    for z, rx, ryf, ryb, cy, p in rows:
        # 阈值是「按旧头写的绝对 z」，必须过 sz()：头缩到 0.9215 后
        # 1.488 相对新头已经落到下巴以下，发帽会从脸颊中部开始，露头皮。
        if z < headmod.sz(1.488):
            continue
        rings.append(superellipse_ring(z, rx + 0.007, ryf + 0.007, cy - 0.002,
                                       0.0, p, 48, ry_back=ryb + 0.007))
    # ---- 圆顶收口（2026-11-03）----
    n_dome = 0          # 穹顶环数；平滑时跳过它们，保住数学曲线
    # head_rows() 的最上一环就是头顶平面，`loft` 直接把它封成一个平顶 —— 3/4 视角下
    # 整颗头像扣了一块平板（out/m4_body_q34.png）。这里在最上环之上补 5 圈余弦收缩的
    # 环，把短发帽收成圆顶；顶环半径留 6% 而不是 0，避免退化环让 loft 出破面。
    if rings:
        base = rings[-1]
        z_top = base[0].z
        cy0 = sum(p.y for p in base) / len(base)
        dome_h = 0.014
        steps = 6
        n_dome = steps
        for i in range(1, steps + 1):
            t = i / steps
            # 收口曲线用 (1−t)^1.5，不是 sqrt(1−t²)：后者在 t=0 处切线水平，
            # 而它下面那一段（1.6135 处 54mm → 1.620 处 32mm）是陡峭的圆台，
            # 两段接出一个「肩」，正面渲成一颗小馒头（out/m4_face_front.png）。
            # 幂 1.5 让起点斜率为 −1.5（正好等于圆台斜率换算成归一化后的值），
            # 顶点处斜率归零，整条轮廓从侧面看是一条连续弧，没有转折。
            # 顶环半径留 1.2%：留太多（旧值 6%）会封出一个 1.9mm 的小圆台，
            # 描边一勾就是颅顶那个「小尖」。
            # 2026-11-03（三）：1.2% 太小了 —— 48 个顶点挤进直径 0.2mm 的圆里，
            # 相邻顶点连向量都算不准，拉普拉斯平滑（3 轮 0.35）把它们推成
            # 一个**旋涡状凹坑**，正顶视是一个向心放射的褶（out/_cap_top.png）。
            # 抬到 10%（半径 ≈5.4mm）：顶环还是一个规整的小圆，法线方向稳定，
            # 封出来的平顶在正顶视只有 21 像素，且完全被鲍伯壳（rx 0.040）压住，
            # 看不见。宁可留一个小平顶，也不能留一个旋涡。
            s = max((1.0 - t) ** 1.5, 0.10)
            zz = z_top + dome_h * t
            rings.append([Vector((p.x * s, cy0 + (p.y - cy0) * s, zz))
                          for p in base])
    # 颅顶去折角（2026-11-03）：头骨自身在 1.600→1.618 从 70mm 陡收到 28mm
    # （斜率 −1.64 → −3.43），发帽跟着走就会在这个位置折出一条明暗交界
    # （out/_zoom_crown.png）。头骨是共用几何、动它会连锁改头长/五官位置，
    # 所以折角在发帽上抹圆。
    #
    # 2026-11-03（三）：从「Smooth 修改器」改成**只对主体环做手工拉普拉斯**。
    # 修改器是全网格的，dome 的收口环也被一起推 —— 实测把穹顶压塌 10mm
    # （发顶只高出头骨 4.0mm，而 dome_h 是 14mm），并在顶点推成一个向心旋涡：
    # 正顶视是放射状凹坑（out/_cap_top.png、_cap_top_v1.png 两次都是，
    # 把收口半径从 0.2mm 抬到 5.4mm 也没用 —— 因为元凶是平滑不是半径）。
    # 手工平滑跳过 n_dome 个穹顶环后，穹顶保持数学曲线，折角仍由主体环承担。
    # factor 0.35 / 3 轮沿用原值，外扩 7mm 也沿用（平滑收缩量远小于余量）。
    if rings and n_dome:
        for _ in range(_CAP_SMOOTH_ITERS):
            src = [[Vector(p) for p in ring] for ring in rings]
            for k in range(len(rings) - n_dome):
                m = len(src[k])
                for i in range(m):
                    nb = [src[k][(i - 1) % m], src[k][(i + 1) % m]]
                    if k > 0:
                        nb.append(src[k - 1][i])
                    nb.append(src[k + 1][i])       # k+1 必在（后面还有 dome 环）
                    avg = Vector((0.0, 0.0, 0.0))
                    for q in nb:
                        avg += q
                    avg /= len(nb)
                    rings[k][i] = src[k][i] + (avg - src[k][i]) * _CAP_SMOOTH_FACTOR
    ob = loft(rings, cap_end=False, name="hair_cap")
    if n_dome:
        # 顶环合并成一个点（2026-11-03 三改）。
        # loft 的 cap_end 是**重心扇形封顶**：顶环半径多大，平顶就多大。
        # s 下限 0.10 时顶环半径 7.2mm，封出一个圆盘，圆盘与斜面之间
        # 留一圈折角 —— 正顶视就是一个向心旋涡（out/_cap_top_v2.png，
        # 抬半径、去平滑两次都没消掉，因为前两次都没动封顶方式）。
        # 合并成一个顶点后，顶环的 48 个四边形变成 48 个三角形，全部
        # 收向一个极点，法线朝正上，是标准球顶拓扑。
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        zmax = max(v.co.z for v in bm.verts)
        ring = [v for v in bm.verts if abs(v.co.z - zmax) < 1e-6]
        if len(ring) > 1:
            bmesh.ops.pointmerge(bm, verts=ring, merge_co=(0.0, cy0, zmax))
            bmesh.ops.dissolve_degenerate(bm, dist=1e-7, edges=bm.edges)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            print("[cap] 顶环 %d 点合并为 1 点，z=%.4f" % (len(ring), zmax))
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.update()
    for v in ob.data.vertices:
        # 发际线以下的正脸部分塞回头内：发帽只负责头顶和后脑，
        # 前额的边界交给刘海去遮。
        # 2026-11-03：折返线 1.582 → 1.534。原值让发帽在额头处直接收回去，
        # 刘海管再怎么摆都盖不严那条缝 —— 正面/斜侧会露出一条**皮肤**，
        # 色值正好是皮肤阴影档 #C8B4C2（out/m4_face_q34.png 头顶那条浅带）。
        # 放到眉线 1.534 后，帽体自己盖住整片额头，刘海只在外层做缕感，
        # 露皮肤的缝从几何上就不存在了。
        # 2026-11-03（二）：原条件没有 |x| 限制，耳朵上方也被一并压平 —— 那里
        # 越出了刘海覆盖区，压出来的台阶直接露在头发侧面。
        # 但加横向渐变之后反而在太阳穴多出一块朝前的斜面（比台阶更显眼），
        # 所以维持无条件压平，侧面那道台阶交给外壳去盖（外壳在 z 1.50~1.60
        # 比发帽宽 10mm 以上，本来就把发帽的这个区域整个罩住）。
        th = headmod.sz(1.534)
        if v.co.z < th and v.co.y < -0.004:
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

    三个阈值都过 _hz()：它们也是按旧头写的绝对 z，头缩了不跟着走的话
    缺口会落在脖子中间而不是颈根。

    1.370 以上 128°（后脑全包）；1.370→1.340 线性收到 100°（倒 V 缺口）；
    1.340→1.290 保持 100°（颈段整段让开）；再往下线性放回 128°（长发照旧
    披在肩上，背面剪影不变）。
    """
    z0, z1, zh = _hz(_BACK_NOTCH_Z0), _hz(_BACK_NOTCH_Z1), _hz(_BACK_NOTCH_HOLD_Z)
    if z >= z0:
        return _BACK_HALF_ANG
    if z >= z1:
        t = (z0 - z) / max(1e-9, (z0 - z1))
        return _BACK_HALF_ANG + (_BACK_HALF_ANG_NARROW - _BACK_HALF_ANG) * t
    if z >= zh:
        return _BACK_HALF_ANG_NARROW
    t = min(1.0, (zh - z) / 0.090)     # 1.290→1.200 放回全宽
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
    # 上面整张表是按旧头写的绝对量，按当前头骨缩放（默认 profile 下恒等）
    rows = [(_hz(z), _hr(rx), _hr(ry), _hr(cy)) for z, rx, ry, cy in rows]
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
        z0 = _hz(1.586)
        # 坐标全部过 _hz/_hr：这张点列也是按旧头写的（默认 profile 下恒等）
        pts = [Vector((_hr(x0 * 0.52), _hr(0.020), z0)),
               Vector((_hr(x0 * 0.92), _hr(0.108), _hz(1.520))),
               Vector((_hr(x0), _hr(0.108), _hz(1.400))),
               Vector((_hr(x0 * 1.04), _hr(0.106), _hz(1.250))),
               Vector((_hr(x0 * 1.02), _hr(0.098), _hz(1.110))),
               Vector((_hr(x0 * 0.90), _hr(0.086), _hz(1.010 - rnd.uniform(0.0, 0.02))))]
        widths = [_hr(0.014) * wk, _hr(0.0165) * wk, _hr(0.019) * wk,
                  _hr(0.0165) * wk, _hr(0.014) * wk, _hr(0.004) * wk]
        out.append(_strand(pts, widths, _hr(0.009) * tk))
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
        # 2026-11-03：起点从 (y=−0.052, z=1.588) 挪到 (y=−0.034, z=1.630) 并加一段。
        # 原起点在**头骨以内**（额面 y≈−0.068，发帽再外扩 6mm ≈ −0.074），于是刘海
        # 是从发帽檐口「下面」钻出来的，帽子前沿的暗面在正面渲成一条帽舌 —— 整颗头
        # 像戴了顶鸭舌帽（out/m4_face_q34.png）。改成从冠内长出来、中段推到脸前 8mm，
        # 才是「刘海盖在额头上」。
        # 2026-11-03：按**实测额面轮廓**重摆（head_rows：z 1.586 ryf=0.0510、
        # z 1.6009 ryf=0.0425、z 1.5668 ryf=0.0574，发帽再外扩 6mm）。
        #   z 1.592 → 帽面 −0.055  → 刘海取 −0.058（前 3mm）
        #   z 1.570 → 帽面 −0.063  → 取 −0.066
        #   z 1.548 → 帽面 −0.068  → 取 −0.070
        # 起点必须略高于发帽前缘折返线 z=1.582，才能把那条折边盖住；
        # 但又不能远到 −0.077（悬空 26mm，斜侧会露出后面的额头皮肤）。
        pts = [Vector((_hr(x), _hr(-0.058), _hz(1.592))),
               Vector((_hr(x * 1.05), _hr(-0.066), _hz(1.570))),
               Vector((_hr(x * 1.10), _hr(-0.070), _hz(1.548))),
               Vector((_hr(x * spread), _hr(-0.071), _hz(z_tip)))]
        # 2026-11-03：**宽度保持原表 0.012/0.017/0.015/0.0035**，不再加宽。
        # 一度加宽到 0.015/0.019/0.017 去填「牙齿缝」，但 d_probe 的 D1 判据要求
        # 组间留 1~2mm 真空缝，加宽直接判 FAIL。真正的解法是让发帽盖住额头
        # （_cap 折返线 1.582→1.534）—— 缝后面变成深色头发而不是皮肤，
        # 缝就从「露出一排皮肤」变成「发缕之间的沟」，观感与判据同时成立。
        widths = [_hr(0.012), _hr(0.017), _hr(0.015), _hr(0.0035)]
        out.append(_strand(pts, widths, _hr(0.006)))
    return out


def _side_locks():
    out = []
    for s in (-1, 1):
        pts = [Vector((_hr(0.075 * s), _hr(-0.030), _hz(1.578))),
               Vector((_hr(0.092 * s), _hr(-0.052), _hz(1.520))),
               Vector((_hr(0.101 * s), _hr(-0.048), _hz(1.440))),
               Vector((_hr(0.099 * s), _hr(-0.032), _hz(1.340))),
               Vector((_hr(0.092 * s), _hr(-0.014), _hz(1.220))),
               Vector((_hr(0.086 * s), _hr(0.002), _hz(1.130)))]
        widths = [_hr(0.014), _hr(0.021), _hr(0.023), _hr(0.020), _hr(0.014), _hr(0.004)]
        out.append(_strand(pts, widths, _hr(0.010)))
    return out


def _ahoge():
    """呆毛：一根从头顶翘起又回收的细发丝。

    注意 `_strand` 的 widths 传的是**半径**，全宽 = 2×widths[0]。
    旧的 0.008 是全宽 16mm，比一根手指还粗，正面看像天线；
    这里整体减半到全宽 7mm，轨迹点一个不动（高度保持 +50.7mm 相对 Head z_max）。
    """
    pts = [Vector((_hr(0.004), _hr(-0.030), _hz(1.612))),
           Vector((_hr(0.010), _hr(-0.035), _hz(1.646))),
           Vector((_hr(0.018), _hr(-0.046), _hz(1.664))),
           Vector((_hr(0.026), _hr(-0.060), _hz(1.652))),
           Vector((_hr(0.028), _hr(-0.066), _hz(1.634)))]
    # 外观旋钮：length_scale 从发根（pts[0]）沿轨迹等比拉伸，thickness_scale
    # 乘半径。默认 1.0 时两者都不做运算（×1.0 精确），与引入前逐位一致。
    lk = charparams.get("hair.ahoge_length_scale", 1.0)
    tk = charparams.get("hair.ahoge_thickness_scale", 1.0)
    if lk != 1.0:
        p0 = pts[0]
        pts = [p0 + (p - p0) * lk for p in pts]
    widths = [_hr(w) * tk for w in (0.0035, 0.0028, 0.0024, 0.0016, 0.0008)]
    return [_strand(pts, widths, _hr(0.004) * tk, seg=10, step=0.006)]


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
        pts = [Vector((_hr(0.075 * s), _hr(0.060), _hz(1.560))),
               Vector((_hr(0.120 * s), _hr(0.090), _hz(1.470))),
               Vector((_hr(0.135 * s), _hr(0.100), _hz(1.340))),
               Vector((_hr(0.128 * s), _hr(0.095), _hz(1.200))),
               Vector((_hr(0.118 * s), _hr(0.088), _hz(1.080)))]
        widths = [_hr(0.012), _hr(0.020), _hr(0.022), _hr(0.017), _hr(0.005)]
        out.append(_strand(pts, widths, _hr(0.010), seg=20))
    return out


# ---------------- 鲍伯头（2026-11-03 按参考图重建）----------------
# 参考图量测（1600px 原图，以「发顶→下巴」= 1 单位为基准）：
#   · 头发最大宽度 548px = 0.94 单位 → 当前头骨（H≈0.2156）半宽 0.121
#   · 发梢在下巴下方 45px = 0.08 单位 → z ≈ 1.384（下巴 1.4044）
#   · 可见脸宽 253px，头发盖掉两侧 = 头发必须**压住脸颊边缘**，不是披在脑后
# 结构：一圈**闭合**放样壳 + 一整片锯齿刘海 + 两缕面框鬓角。
# 外壳正面不做开口弧、也不做折返 —— 两种都试过并失败：
#   · 开口弧 → 两条边界边被描边壳勾成黑线，顶端漏 V 形缺口
#   · 闭合环+折返 → 折返后环非凸，loft 的重心封顶炸成一团
# 现在用**软钳制**：凡是有脸的地方（|y| 方向够靠前），把壳的点按 smoothstep
# 压到「脸面内侧 3mm」；颅顶和侧后方壳本来就比脸靠后，w=0 完全不被动。
# 闭合环保持凸性，没有边界边，转折自然。
_DEFAULT_STYLE = "long"

_BOB_ROWS = [
    # t（0 = 下巴 1 = 头顶）, rx,    ry,    cy
    # 最高只到 t=0.907（z 1.600）：发帽在那里是 0.054，外壳 0.048 正好藏在帽内，
    # 顶端 cap 的封口面也就看不见。再往上（1.62 以上）没有头骨遮挡，折返段会
    # 直接露出来渲成一团皱褶（2026-11-03 实测）。
    (0.907, 0.040, 0.035, 0.018),
    (0.870, 0.052, 0.046, 0.018),
    (0.820, 0.078, 0.068, 0.018),
    (0.760, 0.094, 0.080, 0.018),
    (0.700, 0.106, 0.087, 0.018),
    (0.640, 0.114, 0.091, 0.018),
    (0.560, 0.120, 0.094, 0.018),
    (0.470, 0.121, 0.095, 0.018),
    (0.370, 0.120, 0.094, 0.018),
    (0.270, 0.117, 0.092, 0.018),
    (0.170, 0.113, 0.089, 0.018),
    (0.080, 0.106, 0.084, 0.018),
    (0.000, 0.094, 0.077, 0.018),
    (-0.060, 0.080, 0.067, 0.018),
    (-0.090, 0.062, 0.054, 0.018),
]

_RX_K = 0.90            # 参考图口径：发宽/头高 = 0.94，原表按 1.07 偏宽
_HAIR_T = 0.007         # 发厚：壳在任意高度至少比头骨大这么多，防止头骨戳穿
_OPEN_K = 0.64          # 开口半宽 = 0.64 × 该高度头骨半宽。参考图口径：发宽/可见
                        # 脸宽 = 2.17（模型原来 1.30，脸露出太多）；收到 0.64 后
                        # 鬓发盖住两颊，只留中间一条脸，比值约 1.8。再小会吃到
                        # 眼外眼角（眼睛外缘 x≈0.059，此处开口 ≈0.062）。
_OPEN_MIN = 0.052       # 下半段（下颌/颈）保底开口，别把脖子包住
_BOB_TOP = 0.907        # _BOB_ROWS 的最高 t（= 表首行）
_TUCK_FROM = 0.72       # 从该 t 起把外壳整圈往发帽里收，到 _BOB_TOP 收满
_TUCK_DEPTH = 0.014     # 收口末端：壳体基准面比「发帽表面」内缩多少（米）
                        # 旧值 _TUCK_IN=-0.003 的推算漏了外壳自己那层 Solidify：
                        # 它是沿法线**向外**长 4.5mm 的（apply 后实测 z_max
                        # 1.5999→1.6030），所以收口段的「壳外表面」= 头骨
                        # +3+4.5 = 头骨+7.5mm，而发帽 = 头骨+7mm —— 外表面
                        # 永远比发帽大 0.5mm，顶边收不进去。
                        # 再叠上截面形状差（发帽超椭圆 power 2.0~2.1 + 前后
                        # 不同半径 + cy=-0.002；外壳单椭圆 cy=0.018、前后同半径），
                        # 同一 (x,z) 处前后最多差 9.6mm（z 1.565 / x 70mm：
                        # 外壳 −31.9mm vs 发帽 −41.5mm）。实测顶环 144 个顶点里
                        # 74 个戳出发帽、最多 5.2mm（out/probe_hair.py），戳出的
                        # 顶边被描边壳勾成黑线 —— 侧/3-4 视角头顶那道横线、
                        # 两端针状尖刺（「猫耳」）都是它。
                        # 现取 14mm：收口末端壳外表面 = 发帽 −9.5mm；再留 4.5mm
                        # 给外壳 Solidify、1.4mm 给描边壳，仍有 ≥3.6mm 余量。


def _smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _chin_top():
    """(下巴 z, 头顶 z)。两者都在世界坐标，随 head_to_body_ratio 自动跟随。"""
    return headmod.sz(1.384), headmod.sz(1.618)


def _head_front_y(rows, x, z):
    """头骨前表面在 (x, z) 处的 y。超椭圆截面，与 head.HEAD_RAW 的 power 同源。"""
    if z <= rows[0][0]:
        r = rows[0]
    elif z >= rows[-1][0]:
        r = rows[-1]
    else:
        r = rows[-1]
        for a, b in zip(rows, rows[1:]):
            if a[0] <= z <= b[0]:
                w = (z - a[0]) / max(1e-9, b[0] - a[0])
                r = [a[i] + (b[i] - a[i]) * w for i in range(5)] + [b[5]]
                break
    _z, rx, ryf, _ryb, cy, p = r
    if rx <= 1e-6:
        return cy - ryf
    t = min(0.9995, abs(x) / rx)
    return cy - ryf * max(0.0, 1.0 - t ** p) ** (1.0 / p)


def _row_at(rows, z):
    """按 z 在 head_rows 里插值出一行 (z, rx, ryf, ryb, cy, power)。"""
    if z <= rows[0][0]:
        return rows[0]
    if z >= rows[-1][0]:
        return rows[-1]
    for a, b in zip(rows, rows[1:]):
        if a[0] <= z <= b[0]:
            w = (z - a[0]) / max(1e-9, b[0] - a[0])
            return [a[i] + (b[i] - a[i]) * w for i in range(5)] + [b[5]]
    return rows[-1]


def _bob_dense(steps=44):
    """把 _BOB_ROWS 线性插值加密。

    表只有 15 行、竖直间距约 10mm，直接放样的话开口内缘（鬓发内缘）和发梢
    下缘都是一段段折线，每 10mm 拐一个硬角 —— 正面看就是脸侧那两道锯齿。
    加密到 44 行后同一条边界变成连续曲线。
    """
    src = sorted(_BOB_ROWS, key=lambda r: r[0])
    t0, t1 = src[0][0], src[-1][0]
    out = []
    for i in range(steps):
        t = t0 + (t1 - t0) * i / (steps - 1)
        for a, b in zip(src, src[1:]):
            if a[0] <= t <= b[0]:
                w = (t - a[0]) / max(1e-9, b[0] - a[0])
                out.append(tuple(a[j] + (b[j] - a[j]) * w for j in range(4)))
                break
    return out


def _bob_shell():
    """鲍伯外壳：**开口**放样 —— 截面从右鬓内缘绕过后脑，到左鬓内缘收住。

    旧做法是「闭合环 + 把 |x|<lim 的 y 拉回脑后」，两头都错：
      ① 壳比头骨窄（顶端 rx 36mm，同高度头骨 67mm），头骨直接戳穿外壳，只剩
         发帽的球冠露在外面 —— 正面头顶那颗「馒头」；
      ② 拉回点在 x=±lim 处留下一片近乎垂直的折墙，3/4 视角就是两块悬在脸前
         的「帘子」（out/m4_face_q34.png 左右各一片）。
    开口弧没有折返段，边界天然落在鬓发内缘，也就不存在折墙。

    宽度取「表值」与「头骨 + 发厚」的较大者：下半段（发梢）由表画出 A 字外扩，
    上半段自动退化成贴颅骨的一层，永远不会被头骨顶穿。
    """
    chin, top = _chin_top()
    h = top - chin
    rows = resample(headmod.head_rows(), "z", 0.006)
    seg = 72
    layers = []
    for t, rx0, ry0, cy in _bob_dense():
        z = chin + h * t
        row = _row_at(rows, z)
        f_rx, ryf, ryb, cy_head, p = row[1], row[2], row[3], row[4], row[5]
        cy_cap = cy_head - 0.002        # 与 _cap() 的 superellipse_ring(cy−0.002) 同源
        # ① bob 自身截面（A 字下摆）：表值与「头骨+发厚」取大，前/后分别钳
        rx_b = max(rx0 * _RX_K, f_rx + _HAIR_T)
        yf_b = min(cy - ry0 * _RX_K, -(ryf + _HAIR_T))   # 前表面（负）
        yb_b = max(cy + ry0 * _RX_K, ryb + _HAIR_T)      # 后表面（正）
        # ② 收口目标截面：与发帽**完全同形**（同 power p、同 cy_cap、前后分开），
        #    再把三个极值整体内缩 _TUCK_DEPTH —— 连外壳外表面一起沉进发帽。
        #    形状与深度必须走**同一条**斜坡：形状先改、深度后收会在中间那段
        #    露出一个横向台阶（实测 out/zoom_v2_temple_q34_r.png），两者同步时
        #    形状变化正好被同时下沉的壳吃掉，外观最干净。
        c = _smoothstep((t - _TUCK_FROM) / max(1e-6, _BOB_TOP - _TUCK_FROM))
        d = _TUCK_DEPTH * c
        rx_c = f_rx + _HAIR_T
        yf_c = cy_cap - (ryf + _HAIR_T)
        yb_c = cy_cap + (ryb + _HAIR_T)
        rx = (rx_b * (1.0 - c) + rx_c * c) - d
        yf = (yf_b * (1.0 - c) + yf_c * c) + d
        yb = (yb_b * (1.0 - c) + yb_c * c) - d
        zt = (z - chin) / max(1e-9, h)
        k_open = 0.70 - 0.14 * (1.0 - _smoothstep(zt / 0.42))
        lim = min(max(k_open * f_rx, _OPEN_MIN * 0.86), rx * 0.94)
        th0 = math.asin(lim / rx)
        span = 2.0 * math.pi - 2.0 * th0
        e = 2.0 / max(1e-6, p)
        pts = []
        for i in range(seg):
            th = th0 + span * i / (seg - 1)
            cs = math.cos(th)
            # 现状轮廓：单椭圆（前后同半径，中心 = (yf+yb)/2）
            y_ell = yb + (yf - yb) * 0.5 * (1.0 + cs)
            if c > 0.0:
                # 发帽同形轮廓：前后两个半超椭圆，x 极值处落到 cy_cap。
                # 单椭圆在太阳穴对角线处比发帽靠后最多 9.6mm，发帽就从外壳
                # 上方露出来一小块（3/4 视角的「折面」）；同形之后两边平行、
                # 不再露，收口时也能整圈一起沉进发帽。
                a = abs(cs) ** e
                if cs >= 0.0:
                    y_cap = cy_cap - (cy_cap - yf) * a
                else:
                    y_cap = cy_cap + (yb - cy_cap) * a
                y = y_ell * (1.0 - c) + y_cap * c
            else:
                y = y_ell
            pts.append(Vector((rx * math.sin(th), y, z)))
        layers.append(pts)
    # 手工连四边形带：loft 的 j2=(j+1)%seg 会把开口首尾相连，渲成一张横挡在
    # 脸前的平板（这就是上一版把开口强行闭合的由来）。
    verts, faces = [], []
    for ring in layers:
        verts.extend((p.x, p.y, p.z) for p in ring)
    for j in range(len(layers) - 1):
        b0, b1 = j * seg, (j + 1) * seg      # layers 按 t 递减排，b1 在下方
        for i in range(seg - 1):
            faces.append((b0 + i, b1 + i, b1 + i + 1, b0 + i + 1))
    ob = mesh_from(verts, faces, "hair_bob")
    select_only(ob)
    m = ob.modifiers.new("Solidify", 'SOLIDIFY')
    m.thickness = 0.0045
    m.offset = -1.0
    bpy.ops.object.modifier_apply(modifier=m.name)
    shade_smooth(ob)
    return ob


def _fringe():
    """齐刘海：一整片带锯齿下缘的曲面。

    为什么不用 `_strand` 拼：7 根半径 12~17mm 的管子并排，正面渲出来是一排
    香肠 —— 上一版「竖棱」就是这么来的（管径 24~34mm，间距 18~34mm）。
    改成连续曲面后，缕与缕之间是**浅槽**，不是断开的圆管。

    下缘：基高 1.533（眼上睫毛线 1.532 附近）+ 周期 35.5mm 的余弦锯齿，
    幅度 4.2mm；两侧比中间短 6mm，避免正面看是一条水平直边。
    上缘跟随发际线：中间 1.606、两侧 1.566。
    """
    chin, top = _chin_top()
    h = top - chin
    rows = resample(headmod.head_rows(), "z", 0.006)
    cols, nrow = 45, 8
    x_max = 0.089
    verts, faces = [], []
    for i in range(cols):
        x = -x_max + 2.0 * x_max * i / (cols - 1)
        u = x / x_max
        scallop = 0.0042 * math.cos(2.0 * math.pi * x / 0.0355)
        z_bot = chin + h * 0.625 + scallop - 0.006 * u * u
        # 上缘走**穹顶弧**而不是水平线：水平线到两侧会飞出头顶轮廓，渲成两只
        # 「猫耳」（实测踩过）。圆弧让顶缘贴着颅顶走，两端的角落到外壳侧面里。
        z_top = chin + h * 0.985 - 0.055 * u * u
        # 纵向缕槽（2026-11-03）：整片光滑曲面在正面读作「一块帽檐」，参考图的
        # 刘海是一绺一绺、缝隙里能看见暗部。让表面沿 x 做起伏，配合描边出竖缝。
        # 两个周期（34.5mm + 19.3mm，相位错开）叠加是为了打散等距感 —— 单一
        # 周期会渲成一排「瓦楞/肋骨」（第一版 3.4mm 等距就是这样）；幅度也必须
        # 压到 1.6mm 以下、且顶端完全不起伏（×tt^1.3），否则额头顶会鼓成一排管子。
        groove = (0.0016 * math.cos(2.0 * math.pi * x / 0.0345)
                  + 0.0010 * math.cos(2.0 * math.pi * x / 0.0193 + 1.1))
        for j in range(nrow):
            tt = j / (nrow - 1)
            z = z_top + (z_bot - z_top) * tt
            # 顶端压到**头骨表面以内 4mm**（off 为负 = 塞进头里），中段才鼓出来。
            # 只「塞进发帽」不够：描边壳会把刘海的上边界勾成一条黑线（实测），
            # 必须让它整体沉到描边也够不到的地方。
            off = -0.008 + 0.014 * tt + groove * (tt ** 1.3)
            y = _head_front_y(rows, x, z) - off
            verts.append((x, y, z))
    for i in range(cols - 1):
        for j in range(nrow - 1):
            a = i * nrow + j
            b = (i + 1) * nrow + j
            faces.append((a, b, b + 1, a + 1))
    ob = mesh_from(verts, faces, "hair_fringe")
    select_only(ob)
    m = ob.modifiers.new("Solidify", 'SOLIDIFY')
    m.thickness = 0.006
    m.offset = -1.0
    bpy.ops.object.modifier_apply(modifier=m.name)
    return ob


def _bob_locks():
    """面框鬓角：两缕从太阳穴垂到下颌，末端收尖。鲍伯头的「脸边框」。"""
    chin, top = _chin_top()
    h = top - chin
    out = []
    for s in (-1, 1):
        pts = [Vector((0.070 * s, -0.040, chin + h * 0.700)),
               Vector((0.082 * s, -0.052, chin + h * 0.490)),
               Vector((0.086 * s, -0.050, chin + h * 0.230)),
               Vector((0.083 * s, -0.044, chin - h * 0.030))]
        widths = [0.010, 0.013, 0.011, 0.0035]
        out.append(_strand(pts, widths, 0.008))
    return out


# ---------------- hair card 版鲍伯头（2026-11-03） ----------------
# 表示法换成 CHARM（SIGGRAPH Asia 2025）的 5 参数 hair card：
# 每个控制点只存「位置 + 宽 + 厚」，截面是菱形（见 lib/haircard.py）。
# 与旧 _bob_shell 的根本差别：
#   · 旧 = 一圈椭圆环按高度缩放再放样 → 每一层截面都是椭圆，**结构上不可能
#     有分缕**，且必须封顶（颅顶旋涡/肚脐改了 4 次没解决）
#   · 新 = 一张张独立发片 → 卡片之间天然有缝，不封顶，法线由外向内明确
# 17 张卡片 × 10 控制点 ≈ 640 顶点，比旧壳的 6336 顶点少一个数量级，
# 却多了 17 条可数的分缕。

_CARDS_N = 18           # 环绕卡片数。30 张 × 24mm 读成「细条纹」，参考图是
                        # 8~12 绺粗的；18 张间距 38mm，配合 40mm 宽正好对接
_CARDS_CTRL = 10        # 每张卡片的控制点数
_CARDS_OPEN_DEG = 38.0  # 正面开口半角。54° 时「刘海止于 ±48°、环绕卡片从 60° 起」，
                        # 中间 48~60° 是一条空档，正面看是两道露出壳体的竖缝，
                        # 两侧头发读成两片「帘子」（out/_quad_cards.png 第 1 格）。
                        # 收到 38° 后 40° 那张进画面，正好接住刘海的边。
                        # 40° 在 z=1.55 处 x≈71mm，可见脸半宽约 50mm —— 夹不到脸。
_CARDS_W_ROOT = 0.0015  # 根部宽度（全宽）：18mm 时卡片顶端是一个平切面朝上，
                        # 顶视读成一圈齿轮锯齿（out/_z_top.png）。收到 6mm 后
                        # 顶端接近一个点，藏进发帽里就看不到切口了
_CARDS_W_MID = 0.042    # 中段最宽 ≈ 间距（38mm）的 1.10 倍 → 只轻微搭边。
                        # 试过 0.056（重叠 18mm）想让卡片互相叠压：结果两张
                        # 菱形截面的卡片在空间里**穿插**，相交线是随机折线，
                        # 侧面渲成一块块错位的硬边补丁（out/_z_side4.png，
                        # 多色渲染确认在 hcard_05 上，out/cardid_m4_face_side.png）。
                        # 菱形截面只能「搭边」，压不住；要真叠压得用弯曲的
                        # 片体 + 明确的内外层，那是下一步的事。规则感交给
                        # 长短/宽窄错落（下方 j1/j2）去打散，不靠重叠
_CARDS_W_TIP = 0.030    # 发梢：0.010 会收成尖刺（像章鱼腿），平切才像短发
_CARDS_T_ROOT = 0.0022  # 根部厚度（全厚）：壳外表面在 4.5mm，卡片中心 5.0mm，
                        # 半厚 1.1mm → 外表面 6.1mm，凸出壳 1.6mm。旧值 3.6mm
                        # 时凸出 2.8mm，沟的深度是宽度的 7%，读成「南瓜瓣」
_CARDS_T_TIP = 0.0009   # 发梢厚度


def _se_pt(row, a, out=0.0):
    """超椭圆上方位角 a 处的点，沿径向向外 out 米。

    a = 0 在正前方（-y），a = π/2 在 +x 侧，a = π 在正后（+y）。
    头骨前后半径不同（ryf/ryb），按 cos 的正负分别取。
    """
    z, rx, ryf, ryb, cy, p = row
    s, c = math.sin(a), math.cos(a)
    ry = ryf if c >= 0.0 else ryb
    e = 2.0 / max(1e-6, p)
    x = rx * math.copysign(abs(s) ** e, s)
    y = cy - ry * math.copysign(abs(c) ** e, c)
    v = Vector((x, y, z))
    if out:
        d = Vector((x, y - cy, 0.0))
        if d.length > 1e-9:
            v = v + d.normalized() * out
    return v


def _cards_bob():
    """鲍伯头（hair card 版）：贴在 `_bob_shell` 表面的一圈发片。

    位置必须**复刻壳的半径公式**，不能只跟表值。壳里是
    `max(表值 × _RX_K, 头骨 + _HAIR_T)` —— 中下段被头骨撑大，所以只跟表值的
    卡片会整圈被壳埋掉，只有最上一段（壳已结束、归发帽管）露出来，渲成一顶
    「花冠」（out/_cmp_cards4~6.png 连续三次都是这个症状）。

    外扩取 0.0055：壳自身有 Solidify（thickness 0.0045），卡片外表面要到
    壳外表面之外才能看见。
    """
    import haircard as hc

    chin, top = _chin_top()
    h = top - chin
    src = _bob_dense(14)
    rows = resample(headmod.head_rows(), "z", 0.006)
    center = Vector((0.0, 0.014, chin + h * 0.55))

    def at(t):
        """在 src 上插值出 (rx, ry, cy)，已乘 _RX_K。

        注意 `_bob_dense` 返回的是**升序**（src[0] 是最低的 t=-0.09，
        src[-1] 是最高 0.907）。按降序写会让每个 t 都命中第一个分支、
        全部返回最低处的半径 —— 卡片退化成一根根等半径的竖柱：顶部因为
        壳也小所以露出来，中下段全被壳埋掉（out/_cmp_cards4~7.png 连续
        四次都是「只有头顶有分缕」，根因就在这里）。
        """
        if t <= src[0][0]:
            r = src[0]
        elif t >= src[-1][0]:
            r = src[-1]
        else:
            r = src[-1]
            for r0, r1 in zip(src, src[1:]):        # r0[0] < r1[0]
                if r0[0] <= t <= r1[0]:
                    w = (t - r0[0]) / max(1e-9, r1[0] - r0[0])
                    r = tuple(r0[i] + (r1[i] - r0[i]) * w for i in range(4))
                    break
        return r[1] * _RX_K, r[2] * _RX_K, r[3]

    # 下端延长 0.05：卡片最低点必须低于壳的最低行，否则发梢下方会露出一圈
    # 壳（分色渲染 out/split_base_m4_face_side.png 底部那条绿色带，约 25mm）。
    # at() 对超出表的 t 会 clamp 到首/末行，等于垂直向下延伸，正好接上。
    t_hi, t_lo = src[-1][0], src[0][0] - 0.05
    out_off = 0.0050
    # root_frac 0.12 → 0.34：宽度从 1.5mm 长到 42mm 只用 1 个控制点（10mm 高）
    # 时，卡片上半段是一个 33mm 宽、8mm 高的硬三角，顶视/侧视都是一排「山峰」。
    # 摊到 3 个控制点后变成锥形发缕，尖端从发旋里长出来。
    widths = hc.blend_widths(_CARDS_CTRL, _CARDS_W_ROOT, _CARDS_W_MID,
                             _CARDS_W_TIP, root_frac=0.34, tip_frac=0.22)
    thicks = hc.blend_thicks(_CARDS_CTRL, _CARDS_T_ROOT, _CARDS_T_TIP)

    parts = []
    for k in range(_CARDS_N):
        # 方位角加 ±3.2° 抖动：等距排列从背后看是一圈规整竖肋，像灯罩
        # （out/_quad_cards.png 第 4 格）。长短/宽窄错落打散纵向，抖动打散横向。
        a = (2.0 * math.pi * k / _CARDS_N
             + 0.090 * math.sin(k * 3.100 + 0.7))
        aa = a if a <= math.pi else a - 2.0 * math.pi
        if abs(math.degrees(aa)) < _CARDS_OPEN_DEG:
            continue                          # 正面开口：留给刘海

        # 错落：黄金角取伪随机（sin(k·2.399)），无周期、可复现、不用 random。
        # 等长等宽是「南瓜瓣」的另一半原因 —— 只改宽度不改长度，沟会变浅但
        # 仍然等距；只改长度不改宽度，管子还是管子。
        j1 = 0.5 + 0.5 * math.sin(k * 2.399)           # 末端高度 0~1
        j2 = 0.5 + 0.5 * math.sin(k * 5.113 + 1.7)     # 宽度 0~1
        j3 = (k % 3) - 1                               # -1/0/+1 三档分层
        lo = t_lo + 0.095 * j1                         # 末端高低差约 20mm
        wsc = 0.84 + 0.30 * j2                         # 宽度 ±15%
        # 走向：卡片不是纯竖直的。顶端在 a、末端偏移 spread，读作「从发旋
        # 向两侧斜下」。纯竖直 + 等距是「罗纹灯罩」的根 —— 改宽度/长度/方位
        # 只能打散规律感，改不了「竖条」本身（out/_quad_cards2~3.png 背视）。
        spread = 0.15 * math.sin(k * 2.399 + 0.4)      # ±8.6°
        # 宽度剖面也逐张抖：最宽处的高度由 root_frac 决定，全卡一致时
        # 背面看是一圈横向对齐的「罗纹」（out/_quad_cards2.png 第 4 格）。
        # 单张重建剖面，成本可忽略（每张才 10 个数）。
        w_here = hc.blend_widths(_CARDS_CTRL, _CARDS_W_ROOT * wsc,
                                 _CARDS_W_MID * wsc, _CARDS_W_TIP * wsc,
                                 root_frac=0.26 + 0.20 * j2,
                                 tip_frac=0.16 + 0.16 * j1)
        # 分层：相邻卡片错开 0.7mm 半径，读作「后一张压在前一张上」。
        # 完全共面会在交叠区产生硬边和 z-fighting。
        off = out_off + 0.0007 * j3
        pts = []
        for i in range(_CARDS_CTRL):
            u = i / (_CARDS_CTRL - 1)
            t = t_hi + (lo - t_hi) * u
            rx0, ry0, cy = at(t)
            z = chin + h * t
            row = _row_at(rows, z)
            f_rx, ryf, ryb = row[1], row[2], row[3]
            # 位置**必须复用 _bob_shell 的截面公式**。这里原来是
            #   rx = max(rx0, f_rx + _HAIR_T) + off
            #   y  = cy ± rx·cos(a)          ← 用「头骨 x 半宽」当 y 半径，还把
            #                                    cy 当半径的一部分加进去
            # 结果正后方向 y 比壳多出 16mm，渲成一根伸出轮廓的薄针
            # （out/split_now_m4_face_side.png 右上那根红线；多色渲染确认是
            # 后脑那张卡片）。壳用的是 yf=min(cy-ry0, -(ryf+T))、yb=max(...)，
            # 两条式子差一个 cy 和 ryf/ryb 的区别，只有正前/正后能看出来。
            # 收口区间 18mm（0.82→0.907）。两头都试过：
            # · 40mm（0.72 起）→ 过渡面是一大块朝上的斜面，侧视是「翻起的盖板」
            #   （out/_z_side3.png y≈270 那条水平浅色带）
            # · 8mm（0.87 起）→ 藏得住，但卡片上半段还宽 6~15mm，顶端仍是
            #   一根根凸出发帽轮廓的尖锥（out/_z_side5.png 顶部与右缘那几根）
            # 18mm 处卡片宽度已收到 ~11mm，过渡面小到看不出。
            k_in = _smoothstep((t - 0.82) / max(1e-6, _BOB_TOP - 0.82))
            off_e = off - 0.012 * k_in
            rx = max(rx0, f_rx + _HAIR_T) + off_e
            yf = min(cy - ry0, -(ryf + _HAIR_T)) - off_e     # 前表面（负）
            yb = max(cy + ry0, ryb + _HAIR_T) + off_e        # 后表面（正）
            aa = a + spread * u                              # 越往下越偏
            k = 0.5 * (1.0 + math.cos(aa))                   # 1=正前 0=正后
            pts.append(Vector((rx * math.sin(aa), yb + (yf - yb) * k, z)))
        parts.append(hc.hair_card("hcard_%02d" % k, pts, w_here, thicks,
                                  center=center))
    return parts


def _cards_fringe():
    """刘海（hair card 版）：正面开口里放 5 张短发片，中间短、两侧长。"""
    import haircard as hc

    chin, top = _chin_top()
    h = top - chin
    rows = resample(headmod.head_rows(), "z", 0.006)
    center = Vector((0.0, 0.014, chin + h * 0.55))

    # (方位角°, 根 z, 尖 z, 中段宽)
    # 2026-11-03（五改）：原来 7 张的尖 z 只有 118~132（差 6mm）→ 正面看是
    # 一排等长的竖条，末端还是平切圆头，读成「梳齿」（out/_z_bangs.png）。
    # 真发的刘海是**长短交替**的：短的一绺让别人看见、长的一绺盖住缝。
    # 现在差 34mm（118~152），且刻意不单调（短-长-短-长交错）。
    # 中段宽 22~31mm ≈ 13° 弧长（25mm），相邻重叠约 2 倍，短的也不会露皮肤。
    spec = [(-48.0, top - 0.004, chin + 0.150, 0.023),
            (-33.0, top - 0.004, chin + 0.128, 0.028),
            (-17.0, top - 0.004, chin + 0.145, 0.030),
            (0.0, top - 0.004, chin + 0.134, 0.031),
            (17.0, top - 0.004, chin + 0.147, 0.029),
            (33.0, top - 0.004, chin + 0.126, 0.027),
            (48.0, top - 0.004, chin + 0.152, 0.022)]

    parts = []
    for i, (deg, z0, z1, wmid) in enumerate(spec):
        a = math.radians(deg)
        pts = []
        # 末端向两侧外撇 3°：真发的刘海发梢不会笔直垂下，总会往旁边带一点。
        # 只在 u>0.5 之后生效，根部仍从同一个发旋长出来。
        side = 1.0 if deg >= 0.0 else -1.0
        for j in range(_CARDS_CTRL):
            u = j / (_CARDS_CTRL - 1)
            z = z0 + (z1 - z0) * u
            row = _row_at(rows, max(z, chin + 0.012))
            row = (z,) + tuple(row[1:])
            # 刘海要离开额头一点，否则插进头骨里。
            # 剖面是「中段鼓出、末端贴回脸」：sin 驼峰给外凸，u>0.55 之后
            # 再往回收 —— 末端收拢才是内扣，一直往外推会变成一顶帽檐。
            lift = (0.012 * math.sin(math.pi * u)
                    - 0.007 * max(0.0, u - 0.55) / 0.45)
            aa = a + side * math.radians(3.0) * max(0.0, u - 0.5) * 2.0
            pts.append(_se_pt(row, aa, _HAIR_T + 0.008 + lift))
        # 末端收尖到 2.2mm：原来留 wmid*0.55（≈15mm）再平切，是一个圆头，
        # 正面看是一排「梳齿」。尖梢才有发丝的方向感。
        ws = hc.blend_widths(_CARDS_CTRL, wmid * 0.32, wmid, 0.0022,
                             root_frac=0.16, tip_frac=0.34)
        ts = hc.blend_thicks(_CARDS_CTRL, 0.0040, 0.0010)
        parts.append(hc.hair_card("hfringe_%02d" % i, pts, ws, ts, center=center))
    return parts


def build(mats):
    style = charparams.get("hair.style", _DEFAULT_STYLE)
    if style == "cards":
        # hair card 版（CHARM 5 参数表示）：壳提供体积，卡片提供表面分缕。
        # 与 bob 的区别只在「有没有分缕」：bob 是一整块壳，从任何角度切都是椭圆；
        # cards 在壳外再贴 18 张发片（+刘海），读作一绺一绺。
        parts = [_cap(), _bob_shell()]
        parts += _cards_bob()
        parts += _cards_fringe()
    elif style == "bob":
        parts = [_cap(), _bob_shell(), _fringe()]
    else:
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
