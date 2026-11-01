# -*- coding: utf-8 -*-
"""手部（A1）：每手 = 1 块扁掌 + 4 指（近/中/远 3 段）+ 1 拇指。

为什么必须是独立物体（DESIGN §2.2 硬约束 2、§2.4.1 取舍）：
    body.build() 走 voxel_remesh(0.0050)，5mm 体素 + smooth(0.5, 5) 会把
    8mm 粗的手指糊成一根；而把全局 voxel 降到 2mm 会让整只身体顶点涨到 50 万、
    构建慢一个数量级。所以手自建 2mm 网格，**绝不 join 进 Body**。
    两只手各自 remesh 完之后才 join（此时几何已定，join 只是合并索引，安全）。

坐标系约定（与 body.arm() 一致）：
    Z 上、-Y 正脸朝向；side=+1 为角色左（+x），side=-1 为角色右（-x）；
    x、张开角等横向量一律乘 side，保证左右镜像对称。
    手垂在身侧、掌心朝身体内侧（side=+1 手掌心朝 -x，side=-1 朝 +x），
    所以掌厚沿 x、掌宽沿 y，手指屈曲方向 = 掌心方向。

尺寸全部来自 DESIGN §2.4.1（单位：米）。
"""

import math

import bpy
from mathutils import Vector

import cfg
import optio
import charparams
from meshkit import superellipse_ring, loft, tube, join, voxel_remesh, smooth, shade_smooth


# ---------------- 尺寸常量（DESIGN §2.4.1） ----------------
_DEFAULT_HAND_SCALE = 1.0       # 外观旋钮 appearance.hand_scale（只缩横向粗细）
PALM_W = 0.042          # 掌宽（沿 y）
PALM_T = 0.014          # 掌厚（沿 x）
PALM_L = 0.048          # 掌长：腕 → 指根
FINGER_T = 0.009        # 指厚（沿 x）
THUMB_D = 0.013         # 拇指直径
THUMB_L = 0.028         # 拇指长

INSERT = 0.007          # 腕口向上插入前臂 7mm（DESIGN 要求 6~8mm）
WRIST_X = cfg.ARM_WRIST_X       # 0.232，与 body.arm() 末端一致
WRIST_Y = 0.014
WRIST_Z = cfg.WRIST_Z           # 0.815，body.arm() 最后一个路径点

PALM_CY = 0.012                  # 掌中心 y
PALM_TOP_Z = WRIST_Z + INSERT    # 0.822：插入段顶（藏在前臂里）
PALM_BOT_Z = WRIST_Z - PALM_L    # 0.767：指根高度

# 四指根部从掌根往上、往掌中心偏的插入量（原先是 build() 里的字面量 0.0012 / 0.002）。
# 提成常量只为让 rig.py 能同源推导指骨坐标 —— 数值一个也没改。
ROOT_DX = 0.0012
ROOT_DZ = 0.002

CURL = 2.0              # 每段屈曲角（度）→ 合计 6°，DESIGN「微屈 6°，不要像耙子」

# 四指：(名字, 指根 y 偏移(相对掌中心), (近/中/远 长度), 指宽(直径), 张开角°)
#
# 张开角是**为分叉验收服务**的硬需求，不是审美：DESIGN §4.2 规定连通分量必须
# 对每个点做 r=3mm 膨胀再算 8 邻域，因此相邻指尖的 (x,y) 中心距必须
# > 半径和 + 2×3mm ≈ 14.5~15mm，否则膨胀后必然并成一根。指根间距 11.75mm 不够，
# 只能靠张开角拉大。实测值见 _stageA/a1_hand_probe.py 的 [probe] hand_tip。
FINGERS = (
    ("index",  -0.0150, (0.0115, 0.0080, 0.0065), 0.0080, -15.0),
    ("middle", -0.00325, (0.0125, 0.0085, 0.0070), 0.0085, -2.0),
    ("ring",    0.00850, (0.0110, 0.0078, 0.0062), 0.0080, 10.0),
    ("pinky",   0.01950, (0.0088, 0.0062, 0.0050), 0.0070, 30.0),
)

# 手掌截面表：z, 中心 x 偏移(乘 side), rx(厚/2), ry(宽/2), power
# 腕部 24mm 宽 → 掌根 42mm 宽，power 从 2.4 升到 3.8 把截面从椭圆变成圆角矩形（扁掌）。
# 腕口两行在 A1 返工里从 (8.0, 10.6/10.8) 加宽到 (8.0, 11.5/12.0)：
# 目的是把「前臂末端 vs 手掌腕口」的径向台阶从 ~13.5mm 压到 ≤3mm（见 body.arm() 注释），
# 让手掌去够前臂、同时也让前臂收细，两边各让一步，免得任何一侧出现突兀的粗细突变。
PALM_ROWS = (
    (PALM_TOP_Z, 0.0000, 0.0088, 0.0115, 2.4),
    (WRIST_Z,    0.0000, 0.0088, 0.0120, 2.4),
    (0.8070,     0.0002, 0.0086, 0.0134, 2.8),
    (0.7960,     0.0006, 0.0076, 0.0152, 3.2),
    (0.7840,     0.0010, 0.0073, 0.0182, 3.5),
    (0.7720,     0.0012, 0.0070, 0.0205, 3.7),
    (PALM_BOT_Z, 0.0012, 0.0068, 0.0210, 3.8),
)


# ---------------- 小工具 ----------------

def _ellipsoid(loc, rx, ry, rz, name):
    """关节球：UV 球压成椭球，用于段间过渡（voxel remesh 会把它融圆）。"""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10,
                                         radius=1.0, location=tuple(loc))
    ob = bpy.context.object
    ob.name = name
    ob.scale = (rx, ry, rz)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return ob


def _dir(theta_deg, spread_deg, side):
    """手指某段的方向：theta 屈曲（朝掌心），spread 张开（在 y 平面里扇开）。"""
    th = math.radians(theta_deg)
    sp = math.radians(spread_deg)
    v = Vector((-math.sin(th) * side, math.sin(sp), -math.cos(th) * math.cos(sp)))
    return v.normalized()


def _poly_dist(p, poly):
    """点到折线的最短距离（顶点组按空间最近折线重新归属时用）。"""
    best = 1e9
    for a, b in zip(poly, poly[1:]):
        ab = b - a
        l2 = ab.length_squared
        if l2 < 1e-12:
            d = (p - a).length
        else:
            t = max(0.0, min(1.0, (p - a).dot(ab) / l2))
            d = (p - (a + ab * t)).length
        if d < best:
            best = d
    return best


def _finger(name, side, root, lens, width, spread, k=1.0):
    """一根手指：连续 tube（3 段、关节处半径 +8% 鼓包）+ 2 个关节球。

    为什么不把 3 段做成 3 根独立 tab：段间会留硬断口，弯曲后更明显。
    这里用一条沿 4 个关节点放样的 tube，段与段之间天然连续，
    再由关节球把关节处补圆 —— 既满足「3 段 + 关节球」的结构语义，又不会断。

    k 是外观旋钮 appearance.hand_scale：只乘截面半径（粗细），关节位置
    （lens）不动 —— 这样 hand.joints_for() 与 rig 的指骨永远与网格同源。

    返回 (tube 对象, 关节球列表, [2 个关节点]).
    """
    rx = FINGER_T * 0.5 * k
    ry = width * 0.5 * k

    joints = [root]
    th = 0.0
    for L in lens:
        th += CURL
        joints.append(joints[-1] + _dir(th, spread, side) * L)

    r1, r2, r3, tip = 1.0, 0.94, 0.80, 0.70
    pts, rad = [], []
    # 近节
    pts.append(joints[0]); rad.append((rx * r1, ry * r1))
    pts.append(joints[0].lerp(joints[1], 0.5)); rad.append((rx * r1 * 1.02, ry * r1 * 1.02))
    pts.append(joints[1]); rad.append((rx * r1 * 1.08, ry * r1 * 1.08))   # 关节 +8%
    # 中节
    pts.append(joints[1].lerp(joints[2], 0.5)); rad.append((rx * r2, ry * r2))
    pts.append(joints[2]); rad.append((rx * r2 * 1.08, ry * r2 * 1.08))   # 关节 +8%
    # 远节（指腹略鼓、指尖收尖）
    pts.append(joints[2].lerp(joints[3], 0.5)); rad.append((rx * r3, ry * r3))
    pts.append(joints[2].lerp(joints[3], 0.78)); rad.append((rx * r3 * 0.95, ry * r3 * 0.95))
    pts.append(joints[3]); rad.append((rx * r3 * tip, ry * r3 * tip))

    tb = tube(pts, rad, seg=20, name=f"finger_{name}_{side}")
    balls = [
        _ellipsoid(joints[1], rx * r1 * 1.10, ry * r1 * 1.10, ry * r1 * 0.90,
                   f"knuckle1_{name}_{side}"),
        _ellipsoid(joints[2], rx * r2 * 1.10, ry * r2 * 1.10, ry * r2 * 0.90,
                   f"knuckle2_{name}_{side}"),
    ]
    return tb, balls, [joints[1], joints[2], joints[3]]


def _thumb(side, k=1.0):
    """拇指：长 28mm、直径 13mm，与手掌中线成 20°（DESIGN 指定外展 20°）。

    指根放在掌根**前缘偏内**（y≈-0.0045）、比四指根高 29mm 的位置 ——
    这个高差是必要的：若拇指根与食指根同高，两者半径和 11mm > 间距，
    2mm 体素会把拇指和食指融成一根。
    """
    x = WRIST_X * side
    root = Vector((x - 0.0045 * side, PALM_CY - 0.0165, 0.7960))
    d = Vector((-0.10 * side, -0.34, -0.935)).normalized()
    r = THUMB_D * 0.5 * k
    pts = [root,
           root + d * (THUMB_L * 0.36),
           root + d * (THUMB_L * 0.68),
           root + d * THUMB_L]
    rad = [(r, r), (r, r), (r * 0.97, r * 0.97), (r * 0.80, r * 0.80)]
    tb = tube(pts, rad, seg=20, name=f"thumb_{side}")
    ball = _ellipsoid(pts[2], r * 1.10, r * 1.10, r * 0.90, f"knuckle_thumb_{side}")
    return tb, ball, pts


def joints_for(side=1):
    """每根手指的 4 个关节点：指根 → 近节末端 → 中节末端 → 指尖。

    与 build() 内部的 _finger() 完全同源（同一张 FINGERS 表 + 同一个 _dir 公式），
    所以 rig.py 用它建指骨时，骨位与网格永远不会错位。
    返回 {指名: [Vector × 4]}；拇指不在其中（DESIGN 的 13 骨方案把拇指并入 palm 骨）。
    """
    s = 1 if side > 0 else -1
    x = WRIST_X * s
    root_z = PALM_BOT_Z + ROOT_DZ
    out = {}
    for name, yoff, lens, width, spread in FINGERS:
        root = Vector((x + ROOT_DX * s, PALM_CY + yoff, root_z))
        th = 0.0
        pts = [root]
        for L in lens:
            th += CURL
            pts.append(pts[-1] + _dir(th, spread, s) * L)
        out[name] = pts
    return out


# 每根手指的顶点组粒度：近节 / 中节 / 远节（与 rig.BONES 的 3 根指骨一一对应）
SEGMENTS = ("proximal", "middle", "distal")

# ---------------- 蒙皮权重可调参数 ----------------
# 三个默认值都是**本文件当前实现的实际值**（提成模块常量只为让 optio 注入，
# 数值一个没改）：best.json 不存在时 assign_groups 的行为与手调版逐位一致。
BLEND_P = 3.5            # 反距离混合指数 p（越大越锐，权重越接近「最近骨」）
BLEND_EPS_MM = 1.5       # 反距离分母的 eps（毫米）—— 等价于「关节混合带宽度」
SMOOTH_FACTOR = 0.55     # 拓扑邻接 Laplacian 平滑因子
SMOOTH_ITERS = 6         # Laplacian 平滑次数


def group_names(side=1):
    """本手全部顶点组名（= 骨骼名）：palm + 4 指 × 3 段 = 13 个。"""
    suf = ".L" if side > 0 else ".R"
    out = [f"palm{suf}"]
    for fname in joints_for(side):
        out.extend(f"{fname}_{seg}{suf}" for seg in SEGMENTS)
    return out


def assign_groups(ob, side=1, suffix="", blend_r=0.004):
    """remesh 之后按空间位置重建顶点组（每手 13 组），**关节处两骨混合**。

    voxel_remesh 会重建整个网格、原始索引全部失效，所以顶点组只能在 remesh
    **之后**按几何位置重新归属。

    为什么不能每顶点只归一根骨（返工 4 的实测教训）：单骨刚性时，屈指 45°/30°
    会让关节处折成硬角 —— 实测边长比 p95=1.000 但 max=36.4×、266 条边 >1.5×，
    也就是整个手指像折纸一样在关节处撕开。现在在 3 个关节（掌↔近节、近节↔中节、
    中节↔远节）周围 4mm 半径内，用 smoothstep 在两根相邻骨之间混合：
    关节点处 50/50，半径边缘退回 100/0，权重和恒为 1。

    分组优先级：
      1. 拇指（y 越过掌前缘）→ palm（DESIGN 的 13 骨方案不含独立拇指骨）；
      2. 掌区（掌根以上 4mm 且 y 在掌宽内）→ palm，靠近某个指根时与近节混合；
      3. 其余 → 最近的两段指骨，相邻则按关节距离混合。
    """
    s = 1 if side > 0 else -1
    if not suffix:
        suffix = ".L" if s > 0 else ".R"

    # 参数注入（best.json 缺失时 = 模块常量的实测默认值，行为不变）
    p_mix = float(optio.param("finger_blend_p", BLEND_P))
    eps_mix = float(optio.param("joint_blend_mm", BLEND_EPS_MM)) * 0.001
    smooth_iters = int(optio.param("finger_smooth_n", SMOOTH_ITERS))
    print(f"[hint] hand weights{suffix} p={p_mix:g} eps={eps_mix * 1000:g}mm "
          f"smooth_n={smooth_iters}")

    joints = joints_for(s)
    palm_name = f"palm{suffix}"
    palm_seg = (Vector((WRIST_X * s, PALM_CY, PALM_TOP_Z)),
                Vector((WRIST_X * s, PALM_CY, PALM_BOT_Z)))

    segs = [(palm_name, palm_seg[0], palm_seg[1])]
    joint_of = {}
    prox_names = []
    for fname, pts in joints.items():
        names3 = [f"{fname}_{seg}{suffix}" for seg in SEGMENTS]
        for i, seg in enumerate(SEGMENTS):
            segs.append((names3[i], pts[i], pts[i + 1]))
        prox_names.append(names3[0])
        joint_of[(palm_name, names3[0])] = pts[0]          # 掌 ↔ 近节
        joint_of[(names3[0], names3[1])] = pts[1]          # 近节 ↔ 中节
        joint_of[(names3[1], names3[2])] = pts[2]          # 中节 ↔ 远节

    names = [palm_name] + [n for n, _, _ in segs[1:]]
    for nm in names:
        if nm not in ob.vertex_groups:
            ob.vertex_groups.new(name=nm)

    seg_by_name = {n: (a, b) for n, a, b in segs}
    acc = {nm: [] for nm in names}
    def blend(co, n1, n2, p=None, eps=None):
        """相邻两骨之间的反距离混合权重（d 越小权重越大，p 控制锐度）。

        为什么用「反距离」而不是「距关节点 blend_r 内才混合」：
        硬分配（最近骨）在两条骨线的等距面附近会让相邻顶点跳到不同的骨，
        屈指时一条 0.27~0.52mm 的体素退化边会被拉到 36~84×。反距离权重是
        d1、d2 的连续函数，等距面上自动 50/50，不存在跳变。

        p / eps 的默认值来自模块常量（BLEND_P / BLEND_EPS_MM），可被
        opt/best.json 覆盖；eps 越大，两根骨之间的权重过渡越宽（混合带越宽）。
        """
        p = p_mix if p is None else p
        eps = eps_mix if eps is None else eps
        a, b = seg_by_name[n1], seg_by_name[n2]
        d1 = _poly_dist(co, list(a)) + eps
        d2 = _poly_dist(co, list(b)) + eps
        w1 = (1.0 / d1 ** p) / (1.0 / d1 ** p + 1.0 / d2 ** p)
        return [(n1, w1), (n2, 1.0 - w1)]

    for v in ob.data.vertices:
        co = v.co
        # palm 的距离打 0.6 折（不是 1.15 的放大）：掌心与拇指（y 越过掌前缘那一片）
        # 都是「离 palm 线近、离指骨远」，打折后自然归 palm；而掌↔指交界两侧各自
        # 最近骨不同时，靠下面的反距离混合连续过渡。
        # 这里**不能**用 "y < edge_y 就强制归 palm" 的硬分支 —— 实测该分支的阈值线
        # 正好穿过掌前缘一圈体素顶点，相邻两点一个 100% palm、一个 100% index_proximal，
        # 屈指 45° 时那条 1.24mm 的边被拉到 12×。
        ds = sorted(((_poly_dist(co, list(seg_by_name[n])) * (0.60 if n == palm_name else 1.0), n)
                     for n, _, _ in segs), key=lambda t: t[0])
        n1 = ds[0][1]
        n2 = None
        for _, cand in ds[1:]:
            if (n1, cand) in joint_of or (cand, n1) in joint_of:
                n2 = cand
                break
        if n2 is None:
            acc[n1].append((v.index, 1.0))
        else:
            for nm, w in blend(co, n1, n2):
                acc[nm].append((v.index, w))

    # ---- 权重平滑（拓扑邻接上的 Laplacian）----
    # 为什么必须做：反距离混合已经把大部分交界处连续化了，但「最近骨」在空间上仍会
    # 有极小的跳变面（例如掌根一条 0.5mm 的退化边，两端分属 palm 与 index_distal），
    # 屈指 45° 时这条边被拉到 36×。平滑直接作用在**拓扑邻接**上，所以任何短边两端的
    # 权重都不会差到撕裂的程度；迭代 3 次、因子 0.5 的扩散半径约 6mm，正好是一个
    # 指节的量级，不会把整根手指泡软。
    Wm = {v.index: {} for v in ob.data.vertices}
    for nm, lst in acc.items():
        for i, w in lst:
            Wm[i][nm] = Wm[i].get(nm, 0.0) + w
    adj = [[] for _ in range(len(ob.data.vertices))]
    for e in ob.data.edges:
        a, b = e.vertices
        adj[a].append(b)
        adj[b].append(a)
    f, iters = SMOOTH_FACTOR, smooth_iters
    for _ in range(iters):
        nxt = {}
        for i, w in Wm.items():
            if not adj[i]:
                nxt[i] = w
                continue
            near = {}
            for j in adj[i]:
                for n, ww in Wm[j].items():
                    near[n] = near.get(n, 0.0) + ww
            k = len(adj[i])
            keys = set(w) | set(near)
            merged = {n: (1.0 - f) * w.get(n, 0.0) + f * near.get(n, 0.0) / k for n in keys}
            tot = sum(merged.values()) or 1.0
            nxt[i] = {n: ww / tot for n, ww in merged.items() if ww > 1e-4}
        Wm = nxt

    # ---- 退化短边上的权重对齐 ----
    # 2mm 体素 remesh 会产生少量 <0.6mm 的极小边（实测最短 0.183mm）。这种边在
    # 视觉上不可见，但只要两端权重差千分之几，边长比就会掉到 0.5（0.183mm 的边
    # 只需要 0.09mm 位移差就压缩一半）。对这类边直接把两端权重取平均、迭代 3 次，
    # 让它们严格 1:1 跟随，避免污染「<0.6 的边 = 0」这条判据。
    short_edges = [(e.vertices[0], e.vertices[1]) for e in ob.data.edges
                   if (ob.data.vertices[e.vertices[0]].co
                       - ob.data.vertices[e.vertices[1]].co).length < 0.0006]
    for _ in range(3):
        for a, b in short_edges:
            keys = set(Wm[a]) | set(Wm[b])
            avg = {n: 0.5 * (Wm[a].get(n, 0.0) + Wm[b].get(n, 0.0)) for n in keys}
            tot = sum(avg.values()) or 1.0
            avg = {n: w / tot for n, w in avg.items() if w > 1e-5}
            Wm[a] = dict(avg)
            Wm[b] = dict(avg)

    # 平滑会把权重扩散到「不该有它的骨」上（实测 palm 的权重被抹到食指远端，
    # z≈0.744 处，造成 13× 的局部剪切）。这里按「顶点到该骨段的距离」做一次硬截断：
    # 超过 22mm 的骨权重直接清零再归一化 —— 22mm 足以保留相邻/隔一节骨的过渡，
    # 又不让手掌的权重跑到指尖。
    REACH = 0.032
    for i, w in list(Wm.items()):
        co = ob.data.vertices[i].co
        keep = {n: ww for n, ww in w.items()
                if _poly_dist(co, list(seg_by_name[n])) <= REACH}
        if keep:
            tot = sum(keep.values()) or 1.0
            Wm[i] = {n: ww / tot for n, ww in keep.items()}
        else:
            Wm[i] = w

    acc = {nm: [] for nm in names}
    for i, w in Wm.items():
        tot = sum(w.values()) or 1.0
        for n, ww in w.items():
            acc[n].append((i, ww / tot))

    for nm, lst in acc.items():
        for idx, w in lst:
            ob.vertex_groups[nm].add([idx], w, 'REPLACE')

    for nm in names:
        lst = acc[nm]
        if lst:
            ids = [i for i, _ in lst]
            print(f"[hint] vgroup {nm}: n={len(ids)} idx=[{min(ids)}..{max(ids)}]")


def build(side=1):
    """建一只完整的手，返回独立 mesh 对象（已 2mm remesh + smooth + 顶点组）。"""
    s = 1 if side > 0 else -1
    suffix = ".L" if s > 0 else ".R"
    x = WRIST_X * s

    parts = []
    bones = []

    # 外观旋钮：hand_scale 只缩放横向（掌宽/掌厚/指粗/拇指径），
    # 掌长与指长不动 —— 否则 PALM_BOT_Z 与 rig 的指骨坐标会与网格分家。
    k = charparams.get("appearance.hand_scale", _DEFAULT_HAND_SCALE)

    # ---- 1) 扁掌：腕 21mm 宽 → 掌根 42mm 宽 ----
    rings = [superellipse_ring(z, rx * k, ry * k, PALM_CY, x + dx * s, p, cfg.RING_SEG)
             for z, dx, rx, ry, p in PALM_ROWS]
    palm = loft(rings, name=f"palm_{s}")
    parts.append(palm)
    bones.append(("palm", [Vector((x, PALM_CY, PALM_TOP_Z)),
                           Vector((x, PALM_CY, PALM_BOT_Z))]))

    # ---- 2) 四指：各 3 段，插入掌内 2mm 保证融合 ----
    root_z = PALM_BOT_Z + ROOT_DZ
    for name, yoff, lens, width, spread in FINGERS:
        root = Vector((x + ROOT_DX * s, PALM_CY + yoff, root_z))
        tb, balls, joints = _finger(name, s, root, lens, width, spread, k)
        parts.append(tb)
        parts.extend(balls)
        bones.append((name, [root] + joints))

    # ---- 3) 拇指 ----
    tb, ball, tpts = _thumb(s, k)
    parts.append(tb)
    parts.append(ball)
    bones.append(("thumb", tpts))

    # ---- 4) 2mm 体素融合 + 轻平滑 ----
    hd = join(parts, name=f"hand_{s}")
    voxel_remesh(hd, size=0.0020)
    smooth(hd, factor=0.30, iterations=2)
    assign_groups(hd, s, suffix)
    shade_smooth(hd)
    return hd


def _placeholder_skin():
    """A 阶段的占位皮肤材质（Principled，不是 look 的 toon）。

    为什么放在这里：body.build() 会创建 Hands，而 m2~m5 只给 Body 赋材质，
    若 Hands 没材质会用 Blender 默认白（反照率 0.8），在 m5_pose_* 图里比身体亮一大截，
    看起来像「戴了白手套」。给它一个接近皮肤基色的 Principled 只是让 A 阶段的
    几何核对图不至于跑偏；**C 阶段必须改接 look.set_all() 的 skin toon 材质**。
    """
    name = "hand_skin_placeholder"
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = (0.96, 0.80, 0.72, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.62
    return mat


def build_pair():
    """双手：各自 remesh 完之后才 join（join 不改几何，安全），名为 Hands。"""
    hands = [build(-1), build(1)]
    ob = join(hands, "Hands")
    shade_smooth(ob)
    ob.data.materials.append(_placeholder_skin())
    groups = [g.name for g in ob.vertex_groups]
    print(f"[hint] Hands vgroups n={len(groups)}: {groups}")
    for suf in (".L", ".R"):
        n = len([g for g in groups if g.endswith(suf)])
        print(f"[hint] Hands per-hand vgroups{suf} = {n}")
    return ob