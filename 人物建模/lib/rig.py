# -*- coding: utf-8 -*-
"""M5 骨架：手写人体骨架 + 最近骨段权重 + 三个测试姿势。

不走 Rigify：身体是参数化生成的，关节坐标本来就知道，
手写骨架比对齐 159 根元骨架更稳，蒙皮失败的概率也更低。
"""
import bpy
import math
from mathutils import Vector, Matrix

import cfg
import hand as handmod


def hand_bones(side, suffix):
    """每手 13 根骨：palm + 4 指 × 3 段（近/中/远）。

    位置全部从 hand.py 的表推导（hand.joints_for()），**不手写任何坐标** ——
    骨位一旦与网格分头手写，几毫米的偏差就够让手指弯曲时折到外面。
    拇指按 DESIGN 的 13 骨方案并入 palm 骨，不单独出骨。
    """
    x = handmod.WRIST_X * side
    cy = handmod.PALM_CY
    out = [
        (f"palm{suffix}", (x, cy, handmod.WRIST_Z),
         (x, cy, handmod.PALM_BOT_Z), f"forearm{suffix}", False, True),
    ]
    for fname, pts in handmod.joints_for(side).items():
        parent = f"palm{suffix}"
        for i, seg in enumerate(handmod.SEGMENTS):
            bn = f"{fname}_{seg}{suffix}"
            out.append((bn, tuple(pts[i]), tuple(pts[i + 1]), parent, False, True))
            parent = bn
    return out


# name, head, tail, parent, connected, deform
BONES = [
    ("hips",      (0.000, 0.000, 0.795), (0.000, 0.000, 0.905), None, False, True),
    ("spine",     (0.000, 0.000, 0.905), (0.000, 0.000, 1.060), "hips", True, True),
    ("chest",     (0.000, 0.000, 1.060), (0.000, 0.000, 1.245), "spine", True, True),
    ("neck",      (0.000, 0.004, 1.245), (0.000, 0.012, 1.378), "chest", True, True),
    # A6：head 骨 tail 随 HEAD 表缩放同步（1.598 → 1.5987，见 head.py:sz）。
    # head 骨的 head 端锚在颈根 1.378，与 neck.tail 保持连接，不随头骨下移。
    ("head",      (0.000, 0.012, 1.378), (0.000, 0.012, 1.5987), "neck", True, True),

    ("shoulder.L", (0.024, 0.000, 1.292), (0.126, 0.000, 1.276), "chest", False, True),
    ("upper_arm.L", (0.126, 0.000, 1.276), (0.194, 0.006, 1.045), "shoulder.L", True, True),
    ("forearm.L", (0.194, 0.006, 1.045), (0.232, 0.014, 0.815), "upper_arm.L", True, True),
    *hand_bones(1, ".L"),

    ("shoulder.R", (-0.024, 0.000, 1.292), (-0.126, 0.000, 1.276), "chest", False, True),
    ("upper_arm.R", (-0.126, 0.000, 1.276), (-0.194, 0.006, 1.045), "shoulder.R", True, True),
    ("forearm.R", (-0.194, 0.006, 1.045), (-0.232, 0.014, 0.815), "upper_arm.R", True, True),
    *hand_bones(-1, ".R"),

    # v2（2026-11-05）：腿骨 x 与 cfg.LEG_X（0.072→0.082）同源——胯加宽后
    # 站距外移，骨必须跟着腿管轴线走，否则最近骨段权重会把大腿判给对侧。
    ("thigh.L",   (0.082, 0.000, 0.865), (0.082, -0.010, 0.428), "hips", False, True),
    ("shin.L",    (0.082, -0.010, 0.428), (0.082, 0.012, 0.078), "thigh.L", True, True),
    ("foot.L",    (0.082, 0.012, 0.078), (0.082, -0.086, 0.024), "shin.L", True, True),
    ("toe.L",     (0.082, -0.086, 0.024), (0.082, -0.132, 0.020), "foot.L", True, True),

    ("thigh.R",   (-0.082, 0.000, 0.865), (-0.082, -0.010, 0.428), "hips", False, True),
    ("shin.R",    (-0.082, -0.010, 0.428), (-0.082, 0.012, 0.078), "thigh.R", True, True),
    ("foot.R",    (-0.082, 0.012, 0.078), (-0.082, -0.086, 0.024), "shin.R", True, True),
    ("toe.R",     (-0.082, -0.086, 0.024), (-0.082, -0.132, 0.020), "foot.R", True, True),
]

# 躯干与手臂骨；裙子/躯干权重从这里挑，避免裙子被腿骨带走
UPPER = {"hips", "spine", "chest", "neck", "head",
         "shoulder.L", "upper_arm.L", "forearm.L", "palm.L",
         "shoulder.R", "upper_arm.R", "forearm.R", "palm.R"}


def is_finger(name):
    """是否指骨（按段名后缀识别，不硬编码 26 个名字）。"""
    return name.split(".")[0].endswith(("_proximal", "_middle", "_distal"))


def is_arm_bone(name):
    """是否属于手臂链（含手掌与指骨）。"""
    if name.startswith(("shoulder", "upper_arm", "forearm", "hand", "palm")):
        return True
    return is_finger(name)


def build_armature(name="Rig"):
    arm = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, arm)
    bpy.context.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    for bname, head, tail, parent, conn, deform in BONES:
        eb = arm.edit_bones.new(bname)
        eb.head = Vector(head)
        eb.tail = Vector(tail)
        eb.use_deform = deform
        if parent:
            eb.parent = arm.edit_bones[parent]
            eb.use_connect = conn
    bpy.ops.object.mode_set(mode='OBJECT')
    arm.display_type = 'STICK'
    return ob


def _seg_dist(p, a, b):
    ab = b - a
    t = 0.0
    d2 = ab.length_squared
    if d2 > 1e-12:
        t = max(0.0, min(1.0, (p - a).dot(ab) / d2))
    return (p - (a + ab * t)).length


def weight_nearest(ob, arm, bones, power=4.0, keep=2):
    me = ob.data
    segs = {}
    for bname in bones:
        b = arm.data.bones[bname]
        segs[bname] = (b.head_local.copy(), b.tail_local.copy())

    groups = {n: ob.vertex_groups.new(name=n) for n in bones}
    for v in me.vertices:
        p = v.co
        dists = sorted(((_seg_dist(p, a, b), n) for n, (a, b) in segs.items()),
                       key=lambda t: t[0])[:keep]
        ws = [(n, 1.0 / (d + 0.012) ** power) for d, n in dists]
        total = sum(w for _, w in ws)
        for n, w in ws:
            groups[n].add([v.index], w / total, 'REPLACE')

    mod = ob.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm
    ob.parent = arm
    return ob


# ---------------- B1/B2：分带 + 侧向约束的权重 ----------------
#
# B1 要解决的问题（DESIGN §3.2 B1，实测 55.1%）：裙子 z<1.04 的 672 个顶点里
# 370 个的主骨是 hand.L/R + forearm.L/R —— 因为裙摆半径 226mm 比髋骨离手臂骨更远，
# 但「最近骨段」只看直线距离，裙腰两侧恰好离前臂最近。走路时裙摆被手臂拽走。
#
# B2 要解决的问题（实测 1.23%，z 中位数 0.710 = 大腿内侧）：纯最近距离不区分左右，
# 大腿内侧的顶点会同时吃到对侧 thigh 的权重。
#
# 两者都做成「候选骨筛选」，不动 weight_nearest 本身（它的签名被别处依赖）。

HIP_BONES = ("hips", "spine", "chest")
LEG_BONES = ("thigh.L", "thigh.R", "shin.L", "shin.R",
             "foot.L", "foot.R", "toe.L", "toe.R")


# ---------------- R5：臂管判据（body_allow 的臂皮肤豁免，2026-11-06） ----------------
# 臂轴段与 rig.BONES 的 upper_arm/forearm 逐字同源（lib/body.py:arm 的路径表：
# 肩 (0.126,1.276) → 肘 (0.194,1.045) → 腕 (0.232,0.815)）；改动臂路径须同步。
# 0.040 = 臂截面半径包络 + 余量；**下限由髋外缘反推**：z=0.858 处前臂轴
# x=0.2275、髋环网格最宽 0.183 → 管半径必须 ≤0.040 才不会把髋外环豁免成
# 臂骨候选（首版 0.044 把撕裂点推到了髋外环 x±0.180-0.183，实测 flip_region）。
# 该半径下前臂内侧窄条（z 0.92-0.95, x≈0.185-0.187, 距轴 0.027-0.028）仍在管内。
_ARM_SEGMENTS = (
    (Vector((0.126, 0.000, 1.276)), Vector((0.194, 0.006, 1.045))),
    (Vector((0.194, 0.006, 1.045)), Vector((0.232, 0.014, 0.815))),
    (Vector((-0.126, 0.000, 1.276)), Vector((-0.194, 0.006, 1.045))),
    (Vector((-0.194, 0.006, 1.045)), Vector((-0.232, 0.014, 0.815))),
)
_ARM_TUBE_R = 0.040


def _in_arm_tube(co):
    """顶点是否落在同侧臂管内（到任一臂轴段距离 ≤ _ARM_TUBE_R）。"""
    for a, b in _ARM_SEGMENTS:
        if _seg_dist(co, a, b) <= _ARM_TUBE_R:
            return True
    return False


def outfit_allow(co):
    """裙子（Outfit）：z<1.15 一律只允许 hips/spine/chest。

    1.05~1.15 这一段 chest 已在这组里，而 chest 骨 head 在 z=1.060、裙腰在 1.045，
    距离上自然占优 —— 不需要再人为加偏置（加了反而会让腰部僵硬）。
    z>=1.15 是袖子区，回到全骨集合，手臂正常带动袖口。
    """
    if co.z < 1.15:
        return HIP_BONES
    return None


def body_allow(co):
    """身体：z<1.05 的臀/髋/腿区，候选集去掉手臂骨（保留腿骨）。

    |x| 分界必须按 z 分段 —— 上臂内缘的 |x| 随 z 快速变化（z=1.045 处只有 0.160），
    统一用 0.17 会把上臂内缘划进躯干区、被 hips/thigh 主导（实测产生 58.5mm 假越出）。
    v2（2026-11-05）随形体加宽重算（几何来源 body.TORSO/leg/arm）：
      z<0.95：腿/髋最外 0.180（髋环 0.183 的网格值）、上臂内缘 ≥0.192
        （z=0.905 处 0.216−0.0245）→ 分界 0.187；
      0.95≤z<1.05：躯干 rx ≤0.147（0.975 行 0.143 的网格值）、上臂内缘
        ≥0.161（z=1.045 处 0.194−0.033）→ 分界 0.155。

    （返工 3 期间试过两种「连续衰减」替代方案：按 |x| 衰减会压到上臂内缘
     （假越出 181 个/24.5mm），按骨段距离衰减仍有 46 个/18.8mm，都比集合裁剪差，
     已回退。硬边界带来的应变见报告 R3 节。）

    R5（2026-11-06，管线整合工程师）：v2 的 0.187 分界依据「上臂内缘 ≥0.192」
    的估算漏了**体素融合外扩**——前臂内下侧面的网格实际到 x≈0.185-0.187
    （b_probe R2 leak rest 顶点 (±0.187, 0.027, 0.948) lead 是 hips/thigh，
    即臂皮肤被绑到腿骨），这条 ~7mm 窄条在交叉姿势下与臂身撕扯，是
    R3 normal_flips=31/35 的共同根因。修复：|x| 分界保持不变，但**臂管内**
    （到同侧臂轴距离 ≤0.044，臂截面包络 0.040 + 4mm 余量）的顶点豁免限制——
    臂皮肤候选集不限制，由最近骨段自然归臂骨。髋外缘 0.183 距臂轴 ≥0.0445，
    仍走原 |x| 分界（余量 0.5mm，实测见 b_probe R2/R3 复跑）。
    """
    if co.z >= 1.05:
        return None
    if _in_arm_tube(co):
        return None
    lim = 0.187 if co.z < 0.95 else 0.155
    if abs(co.x) < lim:
        return HIP_BONES + LEG_BONES
    return None


SKIRT_CAP = 0.35            # 裙摆下段 thigh 权重上限
SKIRT_CAP_Z = (0.78, 0.95)  # 0.78 以下给满上限，0.78~0.95 线性回收到 0


def skirt_thigh_cap(z):
    """裙摆 thigh 权重上限随 z 的曲线：z≤0.78 → 0.35；0.78~0.95 线性降到 0。"""
    if z >= SKIRT_CAP_Z[1]:
        return 0.0
    if z <= SKIRT_CAP_Z[0]:
        return SKIRT_CAP
    return SKIRT_CAP * (SKIRT_CAP_Z[1] - z) / (SKIRT_CAP_Z[1] - SKIRT_CAP_Z[0])


def _dist_weights(co, segs, names, power, keep):
    ds = sorted(((_seg_dist(co, *segs[n]), n) for n in names), key=lambda t: t[0])[:keep]
    ws = [(n, 1.0 / (d + 0.012) ** power) for d, n in ds]
    tot = sum(w for _, w in ws)
    return [(n, w / tot) for n, w in ws]


def weight_outfit(ob, arm, power=4.0, keep=2):
    """Outfit 权重：裙（z<1.05）按 z 给同侧 thigh 一个上限；袖/领（z≥1.05）走正常距离权重。

    返工 2 的背景：只给 hips/spine/chest 时裙摆几乎刚性（hem 位移 3.64mm vs 腿 215mm，
    比值 1.69%），walk 下 300+ 个腿/臀顶点越出裙面。给 thigh 0.35 的上限后，
    hem 会跟着腿摆 20% 以上，同时 z≥0.95 的腰段保持只受躯干控制（不抽搐）。
    左右腿按 x 符号分离，不串到对侧。
    """
    me = ob.data
    # 裙摆要能加 thigh 权重，所以组集合 = UPPER ∪ thigh.L/R
    names = sorted(set(UPPER) | {"thigh.L", "thigh.R"})
    segs = {n: (arm.data.bones[n].head_local.copy(),
                arm.data.bones[n].tail_local.copy()) for n in names}
    groups = {n: ob.vertex_groups.new(name=n) for n in names}

    for v in me.vertices:
        co = v.co
        if co.z >= 1.05:
            ws = _dist_weights(co, segs, names, power, keep)
        else:
            cap = skirt_thigh_cap(co.z)
            w_t = 0.0
            if cap > 0.0:
                # 中轴附近（|x|<40mm）削峰，避免裙子前后中线跟着单侧腿抖
                t = min(1.0, abs(co.x) / 0.040)
                w_t = cap * (t * t * (3.0 - 2.0 * t))
            base = _dist_weights(co, segs, HIP_BONES, power, keep)
            ws = [(n, (1.0 - w_t) * w) for n, w in base]
            if w_t > 0.0:
                ws.append(("thigh.L" if co.x > 0 else "thigh.R", w_t))
        for n, w in ws:
            groups[n].add([v.index], w, 'REPLACE')

    mod = ob.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm
    ob.parent = arm
    return ob


SIDE_CAP_LO = 0.030      # |x| 在此以内：对侧骨完全自由（不压）
SIDE_CAP_HI = 0.055      # |x| 到此为止：对侧骨完全剔除
SIDE_CAP_MAX = 0.09      # 过渡带起点处对侧骨允许的绝对权重上限（< cross_side_leak 的 0.10 判据）


def side_cap(x, mid=SIDE_CAP_LO):
    """B2 的左右侧向约束：返回对侧骨的**权重上限**，None 表示不限制。

    返工 3 的背景：原来在 |x|=30mm 硬切（|x|>30 直接剔除对侧骨），实测交叉姿势下
    胯部最大边拉伸 5.28×（现口径）/ 12.9×（全模型口径）、670~736 个面法线翻转，
    比完全关掉 side_lock（5.16×）还差 —— 硬切让相邻顶点的候选骨集合突变。
    现在改成连续过渡：|x|≤30mm 完全自由；30~55mm 对侧权重上限从 0.09 平滑降到 0；
    |x|≥55mm 才彻底没有对侧。上限取 0.09 而不是 1.0，是为了不触碰 cross_side_leak
    的 0.10 判据（否则 |x|>30 的软过渡顶点会被判成「串权」，两个指标互相打架）。
    """
    ax = abs(x)
    if ax <= SIDE_CAP_LO:
        return None
    if ax >= SIDE_CAP_HI:
        return 0.0
    t = (ax - SIDE_CAP_LO) / (SIDE_CAP_HI - SIDE_CAP_LO)
    st = t * t * (3.0 - 2.0 * t)
    return SIDE_CAP_MAX * (1.0 - st)


HIP_ZONE = (0.70, 1.00, 0.10)   # 胯部混合区：z 0.70~1.00 且 |x|<100mm
# 2026-11-06 R5 注：|x| 加宽到 0.17 对 60/30 的 5 个翻面无效（见 THIGH_FADE 注），
# 维持 v1 返工 3 定的 0.10。


# ---------------- R3 返工：胯部混合区以外的静置骨/跨侧腿骨连续衰减（2026-11-03） ----------------
# 六探针门 b_probe R3 在 cross 60/30 下 17 个面法线翻转（35/15 为 0），逐面定位
# （诊断件 out/r34_diag2.py）：
#   · 15 面在外左大腿 z≈0.64 一圈：顶点带 4~6% 的 hips/spine（静置骨，距其骨段
#     200mm+）。60° 摆动时静置份额把大腿表面掀过 90°（rest 法线朝 +x，变形后朝
#     +z，dot≈−0.01~−0.25）；35/15 行程短，同机制不翻。
#   · 3 面在小腿中线 z≈0.24：|x|<30mm 中轴带对侧 shin 不设防（~9%），两侧摆角差
#     30° × 行程差 ~200mm 把内侧条带撕折。
#   · 1 面在小腹 z≈1.05：body_allow 在 z=1.05 的候选集跳变（上有臂骨、下有腿骨），
#     跨面一侧顶点带 6.8% thigh.R 被腿带走、邻点带臂骨不动。
# 三处都是「权重场梯度 × 姿势行程差」的剪切折叠；preserve volume（DQ）实测更糟
# （43 面）。用 weight_nearest_banded 的 atten 钩子做**连续**衰减（无候选集硬断层），
# 胯部混合区（0.70~1.00）一行不动 —— R3 的边拉伸判据人群（z 0.70~1.05、|x| 20~55mm）
# 因此不受影响。
STATIC_TORSO = ("hips", "spine", "chest")
LEG_CHAIN = ("thigh", "shin", "foot", "toe")
STATIC_FADE = (0.62, 0.70)     # 静置躯干骨：z≤0.62 清零，0.62~0.70 线性回补
CROSS_FADE = (0.55, 0.70)      # 跨侧腿骨：z≤0.55 清零，0.55~0.70 线性回补（裆部混合保留）
THIGH_FADE = (1.00, 1.05)      # 同侧腿骨上探：z≥1.05 清零（肚子不吃大腿）
# 2026-11-06 R5 注：试过 THIGH_FADE (0.85,1.05) 与 HIP_ZONE |x| 0.17 两个加宽
# 方案，60/30 的 5 个翻面（裆缝融合带 x[+0.030,+0.165]）纹丝不动——折反来自
# 融合网格在 60° 外展下的**几何自相交**（折线跟随权重过渡带移动，不是候选集
# 跳变），权重侧无解；v1 能过 60/30 靠的是裆位更低（0.760）+腿管更窄的几何。
# 详见 out/_v2_r3_diag.py 的翻面顶点权重诊断。


def _fade_in(z, lo, hi):
    """z≤lo → 0，z≥hi → 1，中间线性。"""
    if z >= hi:
        return 1.0
    if z <= lo:
        return 0.0
    return (z - lo) / (hi - lo)


def leg_atten(co, bone):
    """weight_nearest_banded 的 atten：按骨名 × 位置返回权重乘子（≥0）。见上节注释。"""
    z = co.z
    if bone in STATIC_TORSO:
        return _fade_in(z, *STATIC_FADE)
    if bone.endswith((".L", ".R")) and bone[:-2] in LEG_CHAIN:
        own = bone.endswith(".L" if co.x >= 0 else ".R")
        if own:
            return 1.0 - _fade_in(z, *THIGH_FADE)
        return _fade_in(z, *CROSS_FADE)
    return 1.0


def in_hip_zone(co):
    return HIP_ZONE[0] <= co.z <= HIP_ZONE[1] and abs(co.x) < HIP_ZONE[2]


def weight_nearest_banded(ob, arm, bones, power=4.0, keep=2,
                          allow=None, mid=SIDE_CAP_LO, side_lock=False,
                          keep_hip=None, atten=None):
    """最近骨段权重 + 候选骨筛选（B1 分带 / B2 左右侧向约束）。

    allow: 可调用对象，入参顶点坐标，返回允许的骨名集合（None = 不限制）。
    side_lock: True 时，|x| > mid 的顶点排除对侧骨（.R / .L），±mid 中轴带不约束，
               否则脊柱/髋会在中轴断成两半。
    """
    me = ob.data
    names = list(bones)
    segs = {n: (arm.data.bones[n].head_local.copy(),
                arm.data.bones[n].tail_local.copy()) for n in names}
    groups = {n: ob.vertex_groups.new(name=n) for n in names}

    for v in me.vertices:
        allowed = names
        if allow is not None:
            subset = allow(v.co)
            if subset is not None:
                allowed = [n for n in names if n in subset] or names

        k = keep
        if keep_hip and in_hip_zone(v.co):
            k = keep_hip          # 胯部多混两根骨，压掉候选集合跳变造成的应变尖峰
        d_sorted = sorted(((_seg_dist(v.co, *segs[n]), n) for n in allowed),
                          key=lambda t: t[0])[:k]
        ws = [(n, 1.0 / (d + 0.012) ** power) for d, n in d_sorted]
        if atten is not None:
            # 按骨名 × 位置连续衰减（比「候选集裁剪」好在边界不产生硬断层）
            ws = [(n, w * atten(v.co, n)) for n, w in ws]
            if sum(w for _, w in ws) < 1e-9:
                ws = [(n, 1.0 / (d + 0.012) ** power) for d, n in d_sorted]
        total = sum(w for _, w in ws)
        ws = [(n, w / total) for n, w in ws]

        if side_lock:
            cap = side_cap(v.co.x, mid)
            if cap is not None:
                cross = ".R" if v.co.x > 0 else ".L"
                w_cross = sum(w for n, w in ws if n.endswith(cross))
                if w_cross > cap:
                    # 对侧权重压到 cap，差额按比例还给其余骨（总量仍 1.0，无需再归一化）
                    rest = 1.0 - w_cross
                    scale = (1.0 + (w_cross - cap) / rest) if rest > 1e-9 else 1.0
                    ws = [(n, cap * w / w_cross if n.endswith(cross) else w * scale)
                          for n, w in ws]
                    total = 1.0

        for n, w in ws:
            groups[n].add([v.index], w, 'REPLACE')

    mod = ob.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm
    ob.parent = arm
    return ob


def attach_weights(ob, arm):
    """给**已经自带顶点组**的物体挂骨架：只加 modifier + 父级，不重算权重。

    Hands 的顶点组名与骨骼名一一对应、权重已是 1.0 单组刚性，用 weight_nearest
    重算反而会把 13 根手骨揉成软过渡（手指会像橡皮）。所以这里只挂不改权。
    """
    for m in list(ob.modifiers):
        if m.type == 'ARMATURE':
            ob.modifiers.remove(m)
    mod = ob.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm
    ob.parent = arm
    ob.matrix_parent_inverse = arm.matrix_world.inverted()
    return ob


def bind_all(body_ob, cloth_ob, head_ob, hair_ob, hands_ob, arm, side_lock=False):
    """m5_rig 与 _stageB/b_probe 共用的绑定序列（防止两处各写一份而漂移）。

    side_lock 留给 B2 单独开关：B1 只验「分带」，B2 再打开侧向约束，
    这样两次的实测数字能分开归因。
    """
    body_bones = [n for n, *_ in BONES if not is_finger(n)]
    # keep=4 而不是 3：胯部（hips↔thigh 交界）用 3 骨时，相邻顶点的候选集合会跳变，
    # 交叉姿势下实测最大边拉伸 4.45×；加到 4 骨让交界处的权重集合连续。
    weight_nearest_banded(body_ob, arm, body_bones, power=3.0, keep=5,
                          allow=body_allow, side_lock=side_lock, atten=leg_atten)
    weight_outfit(cloth_ob, arm, power=4.0, keep=2)
    rigid_to(head_ob, arm, "head")
    rigid_to(hair_ob, arm, "head")
    if hands_ob is not None:
        attach_weights(hands_ob, arm)
    return arm


def rigid_to(ob, arm, bone):
    vg = ob.vertex_groups.new(name=bone)
    vg.add(list(range(len(ob.data.vertices))), 1.0, 'REPLACE')
    mod = ob.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm
    ob.parent = arm
    return ob


def rot_bone(arm, name, axis, deg):
    """按世界轴旋转骨骼：把世界旋转共轭进骨骼局部空间。"""
    pb = arm.pose.bones[name]
    pb.rotation_mode = 'QUATERNION'
    rest = pb.bone.matrix_local.to_3x3()
    R = Matrix.Rotation(math.radians(deg), 3, axis)
    local = rest.inverted() @ R @ rest
    pb.rotation_quaternion = local.to_quaternion()


POSES = {
    "rest": [],
    "wave": [
        ("upper_arm.L", 'Y', -100), ("forearm.L", 'X', -35),
        ("palm.L", 'Y', -10), ("head", 'Z', 6),
    ],
    "walk": [
        ("thigh.L", 'X', -26), ("shin.L", 'X', 12),
        ("thigh.R", 'X', 22), ("shin.R", 'X', 6),
        ("upper_arm.L", 'X', 20), ("upper_arm.R", 'X', -22),
        ("spine", 'Z', -4),
    ],
    "reach": [
        ("upper_arm.L", 'X', -78), ("upper_arm.R", 'X', -78),
        ("forearm.L", 'X', -18), ("forearm.R", 'X', -18),
        ("chest", 'X', -8),
    ],
}


def apply_pose(arm, name):
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    for bone, axis, deg in POSES[name]:
        rot_bone(arm, bone, axis, deg)
    bpy.context.view_layer.update()