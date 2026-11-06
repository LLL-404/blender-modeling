# -*- coding: utf-8 -*-
"""M5 v2：挂脖旗袍形制（spec/角色设定-银发旗袍-v1.md §三.1）。

形制清单（本轮范围）：
  1. 立领挂脖式：立领环贴颈（颈半径 +5~6mm），衣身在颈台处收上领底；
     前中领面留水滴形金属盘扣座（配饰模块的吊坠/盘扣挂点）。
  2. 无袖修身：肩裸、袖窿止于 bust 上方，前幅在 z 1.13 以上收成挂脖 V
     （两条斜边从领底前侧 30° 下到 bust 侧 ±90°），正面中幅完整覆盖。
  3. 直筒微收腰：髋环以下截面保持不变（直筒），腰带用 cos 凸包放松
     躯干腰身的一半左右（微收腰，不跟满躯干 0.131 的收细）。
  4. 双侧超高开衩：开衩顶点 z≈0.955（胯最宽环 0.858 上方 ≈97mm，胯骨上方），
     下摆 z≈0.115。前/后幅在侧缝断开，边缘 ±7°(下摆)→0°(衩顶) 渐变张角，
     每条布边一根细棕色包边管（Ø5.6mm）。
  5. 腰胯交叉绑带 3 组 ×左右侧 ×2 根（X 交叉），1.5cm 宽、4.4mm 厚的实体
     凸起带，路径按 Body/Outfit 网格 BVH 射线吸附（布面贴布、皮肤贴皮肤），
     每根带两端一颗金色圆形铆钉（Ø11mm）。

本轮不做（honestNotes 记 TODO）：祥云暗纹（法线贴图，属 C 阶段材质）；
盘扣本体与水滴吊坠（配饰模块）；黑色雪纺飘袖（独立部件）。

实现要点（为什么要这样建）：
  · 前/后幅是两张**开弧放样**（25 点/弧），不是整环 loft 后删面——删面会在
    侧缝留下一个整列宽的楔形豁口，且悬空顶点列要二次清理；开弧把布边直接
    落在 ±off(z) 角度上，衩顶处 off→0 与上半环逐位重合，bmesh
    remove_doubles 一次焊死，侧缝以上是无缝整环。
  · 上半环也是「背弧 0..180 + 前弧 270±w」两段：挂脖 V 的皮露区就是背弧
    端点与前弧端点之间的角域，与设定书「正面完整覆盖」不冲突（V 露的是
    上胸两侧，前中从领底到 bust 全有布）。
  · 服装复用 body.sculpt_torso()（DESIGN §2.2 条 4）：参数面环先按
    grow+relax 放大，sculpt 的胸腹推量作用在服装顶点上，净空才不会被
    sculpt 吃掉。包边管同样过一遍 sculpt（管心与布边同一位移场，错位<1mm）。
  · 绑带不用参数面定位——它贴的是**最终网格**（体素+smooth 收缩后的皮肤
    和 solidify 后的布面），所以走 BVH ray_cast 吸附（与 head 贴片同一套路）。
  · join 后顶点索引重排（DESIGN §2.2 条 5）：材质在 join 前按部件挂好，
    join 只合并槽位，不依赖面索引。
"""
import bpy
import bmesh
import math
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import cfg
import charparams
import look as lookmod
import body as bodymod
from meshkit import (superellipse_ring, loft, resample, tube, join,
                     shade_smooth, mesh_from, solidify, recalc_normals,
                     dump_stats)
import outfit as outfitmod   # 只借 _param_torso_cos/_front_y 做净空自检


# ---------------- 形制常量（默认值；profile 无 qipao 段时全部生效） ----------------
def _knob(key, default):
    return charparams.get("qipao." + key, default)


HEM_Z = _knob("hem_z", 0.115)          # 裙摆（踝上 4cm，直筒）
SLIT_TOP_Z = _knob("slit_top_z", 0.955)  # 开衩顶点（胯骨上方）
BUST_FULL_Z = 1.130                    # 前幅满幅（±90°）的上限 z
COLLAR_BASE_Z = 1.335                  # 衣身顶环（颈台顶，领底盖住它）
ARC_N = 25                             # 每条弧的顶点数（180°/24 段 = 7.5°/段）
SLIT_OFF_MAX = _knob("slit_off_deg", 7.0)   # 下摆处布边张角（度），衩顶归零
W_TOP = 30.0                           # 挂脖 V 在领底处的半宽角（度）
STRAP_GROUP_ZS = (0.900, 0.815, 0.730)  # 3 组绑带中心高度（腰胯部）
STRAP_SWING = 0.055                    # 每根绑带前后端的高差（X 交叉）
STRAP_A0, STRAP_A1 = 305.0, 55.0       # (+x 侧) 绑带前端/后端角（过侧缝 0°）；
                                       # 首渲 322/38 时带子缩在侧缝一隅，参考图
                                       # 的带端要搭到前/后幅 1/3 处（110° 弧）
STRAP_HALF_W = 0.0078                  # 绑带半宽 → 全宽 15.6mm ≈ 1.5cm
STRAP_HALF_T = 0.0022                  # 绑带半厚 → 全厚 4.4mm
RIVET_R = 0.0055                       # 金铆钉半径（Ø11mm）
PIPE_R = 0.0028                        # 开衩包边管半径（Ø5.6mm）
# 颈台顶环：躯干表(1.325)+grow 之后收到领底宽度（领底环 0.076 盖住它）
RISER_TOP = (0.058, 0.054, 0.056, 0.014, 2.1)


# ---------------- 参数面（躯干表 → 服装环层参数） ----------------
def _grow(z):
    """服装相对躯干参数面的净空（贴身旗袍，比衬衫的 10~14mm 紧一档）。

    bust 带最多：sculpt_torso 的胸推量作用在服装上，净空就是 grow 本身；
    11mm 是衬衫 14mm 与「贴身无余量」之间的取值。髋带 9mm：内联净空
    自检的贴身下限是 8mm（参数面口径；网格还要再多 ~2mm）。
    """
    if z < 1.000:
        return 0.009
    if z < 1.120:
        return 0.009
    if z < 1.210:
        return 0.011
    if z < 1.270:
        return 0.008
    return 0.006


def _relax(z):
    """腰环放松量（米）。**v2.1 起默认 0**：旧值 +0.014 把腰填成了直筒。

    旧注释的理由是「直筒旗袍不跟满，腰处放松 0.014 后服装腰≈0.153，
    腰/髋≈0.80（微收腰可读）」—— 但 0.153 > 胸 0.147，腰比胸还宽，
    正面读作一只桶（复核图 `_v2_review_body_front.png`）。
    实测壳体：胸 147 / 腰 154 / 髋 192 / 下摆 179 mm，腰/髋 0.802；
    素体本身是 131/183 = 0.716（设定书 §二 腰 1.2 头宽 / 胯 1.6 头宽）。
    即「腰身没被表达」不是素体的问题，是这一项放松量。
    取 0 后壳体腰 140mm（= 素体 131 + 净空 9），腰/髋 0.729，且腰 < 胸。
    仍可用 `params/profile.json` 的 `qipao.relax_mm` 覆盖（正值再放松）。
    """
    amt = _knob("relax_mm", 0.0)
    if not amt:
        return 0.0
    d = (z - 1.010) / 0.090
    if abs(d) >= 1.0:
        return 0.0
    return amt * 0.5 * (1.0 + math.cos(math.pi * d))


def _surf(z, dense):
    """服装环层参数 (rx, ryf, ryb, cy, p)。

    0.858（髋最宽环）以下「直筒微收」：以髋环截面为基，向下线性微收，
    下摆收到 0.93 倍（不是 1.0 的桶，也不是 A 字）—— hold 0.80 的旧做法
    会让裙筒比髋最宽处还窄，大腿（外缘 0.167）擦布。
    """
    zs = [r[0] for r in dense]
    if z < 0.858:
        hip = _surf(0.858, dense)
        k = 1.0 - 0.070 * (0.858 - z) / (0.858 - HEM_Z)
        return (hip[0] * k, hip[1] * k, hip[2] * max(0.985, k), hip[3], hip[4])
    g = _grow(z)
    rel = _relax(z)
    if z <= zs[0]:
        row = dense[0]
    elif z >= zs[-1]:
        row = dense[-1]
    else:
        row = dense[-1]
        for i in range(len(dense) - 1):
            if zs[i] <= z <= zs[i + 1]:
                f = (z - zs[i]) / (zs[i + 1] - zs[i])
                a, b = dense[i], dense[i + 1]
                row = tuple(a[k] + (b[k] - a[k]) * f for k in range(6))
                break
    _, rx, ryf, ryb, cy, p = row
    return (rx + g + rel, ryf + g + rel * 0.6, ryb + g + rel * 0.6, cy, p)


def _w_at(z):
    """挂脖 V 的前幅半宽角（度）：z≤1.13 满幅 90°，领底收到 30°。

    幂 1.6 让 V 在下段张开更快（参考图：上胸两侧露肤三角要宽，
    线性收角时 V 只剩领口一条细缝，露肤三角被吃掉）。
    """
    if z <= BUST_FULL_Z:
        return 90.0
    if z >= 1.330:
        return W_TOP
    t = (1.330 - z) / (1.330 - BUST_FULL_Z)
    return W_TOP + (90.0 - W_TOP) * t ** 1.6


def _slit_off(z):
    """开衩布边张角（度）：衩顶 0 → 下摆 SLIT_OFF_MAX，幂 0.45 收口。

    线性收口实测会把豁口挤在裙摆端（z=0.85 处只剩 7mm，上半个开衩近乎
    闭合，首渲可见）；幂 0.45 让豁口在衩顶下方很快就张开到半幅以上，
    与参考图「整条开衩大敞」一致，衩顶仍精确归零保焊接。
    """
    if z >= SLIT_TOP_Z:
        return 0.0
    t = (SLIT_TOP_Z - z) / (SLIT_TOP_Z - HEM_Z)
    return SLIT_OFF_MAX * t ** 0.45


def _dress_rows(dense):
    """[(z, pr, off_deg, w_deg)]，z 单调升：下摆→衩顶→满幅→颈台顶。"""
    rows = []
    n_lo = 28
    for i in range(n_lo + 1):
        z = HEM_Z + (SLIT_TOP_Z - HEM_Z) * i / n_lo
        rows.append((z, _surf(z, dense), _slit_off(z), 90.0))
    n_mid = 6
    for i in range(1, n_mid + 1):
        z = SLIT_TOP_Z + (BUST_FULL_Z - SLIT_TOP_Z) * i / n_mid
        rows.append((z, _surf(z, dense), 0.0, 90.0))
    n_up = 6
    for i in range(1, n_up + 1):
        z = BUST_FULL_Z + (1.300 - BUST_FULL_Z) * i / n_up
        rows.append((z, _surf(z, dense), 0.0, _w_at(z)))
    for z in (1.315, 1.325):
        rows.append((z, _surf(z, dense), 0.0, _w_at(z)))
    r13 = _surf(1.325, dense)
    mid = tuple(0.5 * (a + b) for a, b in zip(r13, RISER_TOP))
    rows.append((1.330, mid, 0.0, _w_at(1.330)))
    rows.append((COLLAR_BASE_Z, RISER_TOP, 0.0, W_TOP))
    return rows


def _arc_pts(z, a0, a1, pr, n=ARC_N):
    """超椭圆开弧（角度约定同 meshkit.superellipse_ring：0°=+x、90°=+y 后）。"""
    rx, ryf, ryb, cy, p = pr
    e = 2.0 / p
    pts = []
    for i in range(n):
        a = math.radians(a0 if n == 1 else a0 + (a1 - a0) * i / (n - 1))
        c, s = math.cos(a), math.sin(a)
        x = rx * math.copysign(abs(c) ** e, c)
        r = ryb if s > 0 else ryf
        y = cy + r * math.copysign(abs(s) ** e, s)
        pts.append(Vector((x, y, z)))
    return pts


def _panel(rows, front, name):
    """前/后幅：开弧放样，布边落在 ±off 角度上（衩顶以上 off=0 无缝）。"""
    rings = []
    for z, pr, off, w in rows:
        if front:
            if off > 0.0:
                a0, a1 = 180.0 + off, 360.0 - off
            else:
                a0, a1 = 270.0 - w, 270.0 + w
        else:
            if off > 0.0:
                a0, a1 = off, 180.0 - off
            else:
                a0, a1 = 0.0, 180.0
        rings.append(_arc_pts(z, a0, a1, pr))
    return loft(rings, cap_start=False, cap_end=False, name=name)


def _weld_doubles(ob, dist=0.0009):
    """焊死衩顶以上前/后幅的重合布边（0°/180° 两侧，逐位重合）。"""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=dist)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


# ---------------- 净空自检（只打印，绝不抛异常，与 outfit.assert_* 同风格） ----------------
def _assert_fit(dress_cos):
    try:
        body_cos = outfitmod._param_torso_cos()
    except Exception as exc:
        print(f"[qipao][WARN] 净空自检跳过：{exc!r}")
        return
    bands = ((0.840, 0.900, "hip"), (0.980, 1.040, "waist"),
             (1.120, 1.180, "bust"))
    worst = None
    for lo, hi, tag in bands:
        row = []
        for xc, tol in ((0.000, 0.004), (-0.040, 0.012), (+0.040, 0.012)):
            by = outfitmod._front_y(body_cos, lo, hi, xc, tol)
            sy = outfitmod._front_y(dress_cos, lo, hi, xc, tol)
            if by is None or sy is None:
                continue
            row.append((xc, by - sy))
        if not row:
            print(f"[qipao][fit] {tag} z=[{lo:.3f},{hi:.3f}] 采样缺失")
            continue
        xw, m = min(row, key=lambda t: t[1])
        print(f"[qipao][fit] {tag} z=[{lo:.3f},{hi:.3f}] margin={m * 1000:+.1f}mm "
              f"(at x={xw * 1000:+.0f}mm)")
        if worst is None or m < worst:
            worst = m
    if worst is not None and worst < 0.008:
        print(f"[qipao][fit][FAIL] 最小净空 {worst * 1000:+.1f}mm < 8.0mm（贴身下限）")


# ---------------- 形制量测（join 前对 dress 部件做，绑带不会混进样本） ----------------
def _form_facts(dress):
    """开衩可视顶点（豁口≥10mm 的最高 z）/ 各高度布边豁口宽。

    豁口口径：x>0.165 的布边顶点按 y 分正负两簇，簇间空隙 = 前后幅布边
    的实际开口（含包边管径内缩前的布边位置）。
    """
    vs = [v.co for v in dress.data.vertices]

    def gap_at(zt):
        ys = sorted(p.y for p in vs if p.x > 0.165 and abs(p.z - zt) < 0.015)
        neg = [y for y in ys if y < 0.0]
        pos = [y for y in ys if y > 0.0]
        if not (neg and pos):
            return None
        return (min(pos) - max(neg)) * 1000.0

    top_eff = None
    z = 0.20
    while z <= SLIT_TOP_Z + 0.001:
        g = gap_at(z)
        if g is not None and g >= 10.0:
            top_eff = round(z, 3)
        z += 0.025
    print(f"[qipao][form] 开衩可视顶点(豁口≥10mm) ≈ {top_eff} (设计衩顶 {SLIT_TOP_Z})")
    for zt in (0.25, 0.50, 0.75, 0.90):
        g = gap_at(zt)
        print(f"[qipao][form] z={zt:.2f} 布边豁口 {g if g is None else round(g, 1)}mm")


# ---------------- 立领 + 盘扣座 ----------------
def _collar():
    """立领：锥形环从肩颈 junction 收上颈柱，底环盖住衣身顶环。

    底环 r 0.076 在躯干顶网格（≈0.075@1.332）外侧 1~2mm，靠 solidify
    2mm 盖缝；顶环贴颈（颈网格 r≈0.040@1.384 + 5~6mm 余量 = 贴合不嵌）。
    """
    rings = [
        superellipse_ring(1.332, 0.076, 0.062, 0.006, 0.0, 2.2, 40, ry_back=0.066),
        superellipse_ring(1.358, 0.055, 0.052, 0.016, 0.0, 2.2, 40, ry_back=0.052),
        superellipse_ring(1.384, 0.050, 0.047, 0.018, 0.0, 2.2, 40, ry_back=0.047),
    ]
    ob = loft(rings, cap_start=False, cap_end=False, name="qipao_collar")
    solidify(ob, 0.002)
    return ob


def _clasp_seat():
    """水滴盘扣座：立领前中的水滴形金属小座（吊坠挂点，配饰模块对接）。

    贴在领面外表面上（领面 z1.368 处 y≈−0.034，座背 −0.0337 相切），
    下尖上圆的水滴轮廓，厚 3.6mm。
    """
    cx0 = Vector((0.0, -0.0355, 1.368))
    n = 16
    verts = []
    for i in range(n):
        phi = 2.0 * math.pi * i / n
        r = 0.011 * (1.0 - 0.42 * max(0.0, -math.sin(phi)))   # 下尖上圆
        verts.append(Vector((cx0.x + r * math.cos(phi), cx0.y,
                             cx0.z + r * math.sin(phi) * 1.18)))
    cf = len(verts)
    verts.append(cx0 + Vector((0.0, -0.0018, 0.0)))
    cb = len(verts)
    verts.append(cx0 + Vector((0.0, 0.0018, 0.0)))
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append((cf, i, j))
        faces.append((cb, j, i))
    ob = mesh_from(verts, faces, "qipao_clasp_seat")
    recalc_normals(ob)
    return ob


# ---------------- 开衩包边 ----------------
def _slit_piping(dense):
    """4 条布边各一根棕色细包边管（Ø5.6mm），随布边 ±off 角度走。

    管心贴在布边表面外 0.5mm：一半嵌进布边，读作「缝上去的包边」。
    """
    parts = []
    n = 19
    for s in (1, -1):
        for which in ("back", "front"):
            pts = []
            for i in range(n):
                z = (HEM_Z + 0.012 +
                     (SLIT_TOP_Z - 0.006 - (HEM_Z + 0.012)) * i / (n - 1))
                off = _slit_off(z)
                if s > 0:
                    a = off if which == "back" else 360.0 - off
                else:
                    a = (180.0 - off) if which == "back" else 180.0 + off
                pr = _surf(z, dense)
                p0 = _arc_pts(z, a, a, pr, n=1)[0]
                rad = Vector((p0.x, p0.y - pr[3], 0.0))
                if rad.length < 1e-6:
                    rad = Vector((float(s), 0.0, 0.0))
                rad.normalize()
                pts.append(p0 + rad * 0.0005)
            ob = tube(pts, [(PIPE_R, PIPE_R)] * n, seg=6,
                      name=f"qipao_pipe_{which}_{s}",
                      cap_start=True, cap_end=True)
            bodymod.sculpt_torso(ob)
            parts.append(ob)
    return parts


# ---------------- 交叉绑带 + 铆钉 ----------------
def _ray_snap(origin, direction, bvhs):
    """对多张 BVH 射线投射，取离 origin 最近的命中（布面优先于皮肤）。"""
    best = None
    for bvh in bvhs:
        loc, nor, _idx, dist = bvh.ray_cast(origin, direction)
        if loc is not None and (best is None or dist < best[3]):
            best = (loc, nor, _idx, dist)
    return best


def _straps_and_rivets(dense, dress, body_ob):
    """3 组 ×左右 ×2 根交叉绑带（1.5cm 宽实体凸起）+ 两端金铆钉。

    路径吸附：粗点取服装环层外 10mm，向中轴射线，命中（布或皮）后沿命中
    法线外移 3mm —— 布面段贴布、开衩豁口段贴皮肤，与参考图一致。
    """
    dg = bpy.context.evaluated_depsgraph_get()
    bvhs = [BVHTree.FromObject(dress, dg)]
    if body_ob is not None:
        bvhs.append(BVHTree.FromObject(body_ob, dg))
    parts = []
    rivets = 0
    misses = 0
    n = 13
    for s in (1, -1):
        for gi, gz in enumerate(STRAP_GROUP_ZS):
            for k in (0, 1):
                pts, nors = [], []
                for i in range(n):
                    t = i / (n - 1)
                    # 过 0°（+x 侧缝）：必须 +76° 走短弧（322→398≡38）。
                    # 直减 284° 会绕经 270°/180°——绑带整个裹住前半身（首渲实测）。
                    ang = STRAP_A0 + (STRAP_A1 + 360.0 - STRAP_A0) * t
                    if s < 0:
                        ang = (180.0 - ang) % 360.0              # 镜像到 −x 侧
                    dz = STRAP_SWING - 2.0 * STRAP_SWING * t if k == 0 \
                        else -STRAP_SWING + 2.0 * STRAP_SWING * t
                    z = gz + dz
                    pr = _surf(z, dense)
                    a = math.radians(ang)
                    c, sa = math.cos(a), math.sin(a)
                    e = 2.0 / pr[4]
                    p0 = Vector((pr[0] * math.copysign(abs(c) ** e, c),
                                 pr[3] + (pr[2] if sa > 0 else pr[1]) *
                                 math.copysign(abs(sa) ** e, sa), z))
                    axis_pt = Vector((0.0, pr[3], z))
                    outward = Vector((p0.x, p0.y - pr[3], 0.0))
                    if outward.length < 1e-6:
                        outward = Vector((float(s), 0.0, 0.0))
                    outward.normalize()
                    origin = p0 + outward * 0.010
                    hit = _ray_snap(origin, -outward, bvhs) if bvhs else None
                    if hit is not None:
                        loc, nor = hit[0], hit[1].normalized()
                        if nor.dot(-outward) > 0.0:   # 法线要朝外
                            nor = -nor
                        pts.append(loc + nor * 0.0030)
                        nors.append(nor)
                    else:
                        misses += 1
                        pts.append(origin - outward * 0.012)
                        nors.append(outward)
                ob = tube(pts, [(STRAP_HALF_T, STRAP_HALF_W)] * len(pts),
                          seg=6, up=(0.0, 0.0, 1.0),
                          name=f"qipao_strap_g{gi}_{k}_{s}",
                          cap_start=True, cap_end=True)
                parts.append(ob)
                for idx in (0, len(pts) - 1):   # 两端金铆钉
                    p, nn = pts[idx], nors[idx]
                    parts.append(tube([p + nn * 0.001, p + nn * 0.0065],
                                      [(RIVET_R, RIVET_R), (RIVET_R, RIVET_R)],
                                      seg=6, name=f"qipao_rivet_g{gi}_{k}_{s}_{idx}",
                                      cap_start=True, cap_end=True))
                    rivets += 1
    print(f"[qipao] straps=12 (3 组×左右×2) rivets={rivets} ray_miss={misses}")
    return parts


# ---------------- 材质 ----------------
def _mats():
    """银灰缎面 / 棕色包边·绑带 / 金属金。toon 骨架与全角色一致。"""
    return {
        "satin": lookmod.toon("qipao_satin", (0.800, 0.815, 0.855),
                              shadow=(0.400, 0.420, 0.520),
                              mid=(0.660, 0.685, 0.750),
                              light=(0.985, 0.990, 1.000),
                              pos=(0.0, 0.40, 0.70)),
        "trim": lookmod.toon("qipao_trim_brown", (0.360, 0.235, 0.150),
                             shadow=(0.150, 0.095, 0.060),
                             mid=(0.300, 0.195, 0.120),
                             light=(0.550, 0.400, 0.270),
                             pos=(0.0, 0.36, 0.62)),
        "gold": lookmod.toon("qipao_gold", (0.850, 0.640, 0.180),
                             shadow=(0.400, 0.270, 0.070),
                             mid=(0.740, 0.550, 0.150),
                             light=(1.000, 0.900, 0.500),
                             pos=(0.0, 0.40, 0.68)),
    }


_MAT_OF = {"qipao_dress": "satin", "qipao_collar": "satin",
           "qipao_clasp_seat": "gold"}


def build(mats=None):
    """挂脖旗袍。返回 join 后的 "Outfit"（与 outfit.build 同约定）。

    mats 参数收下不用（形制自带 3 个材质）——保持与 outfit.build(mats)
    同签名，m5_outfit 的 style 分支可以无差别调用。
    """
    dense = resample(bodymod.torso_rows(), "z", cfg.RESAMPLE_STEP)
    rows = _dress_rows(dense)

    dress = join([_panel(rows, False, "qipao_back"),
                  _panel(rows, True, "qipao_front")], "qipao_dress")
    _weld_doubles(dress)
    bodymod.sculpt_torso(dress)
    dress_cos = [v.co.copy() for v in dress.data.vertices]   # solidify 前环层
    solidify(dress, 0.003)
    _form_facts(dress)

    parts = [dress, _collar(), _clasp_seat()]
    parts += _slit_piping(dense)

    body_ob = bpy.data.objects.get("Body")
    if body_ob is not None:
        parts += _straps_and_rivets(dense, dress, body_ob)
    else:
        print("[qipao][WARN] 场景无 Body，跳过绑带/铆钉（探针模式）")

    M = _mats()
    for ob in parts:
        key = _MAT_OF.get(ob.name, "trim" if "pipe" in ob.name or
                          "strap" in ob.name else "gold")
        ob.data.materials.append(M[key])

    cloth = join(parts, "Outfit")
    shade_smooth(cloth)
    dump_stats(cloth)
    _assert_fit(dress_cos)
    print(f"[qipao] form: 立领挂脖 + 直筒微收腰 + 双侧开衩 "
          f"(top z={SLIT_TOP_Z:.3f}, hem z={HEM_Z:.3f}) + 绑带 3 组×左右×2 + 金铆钉")
    return cloth
