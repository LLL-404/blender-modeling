# -*- coding: utf-8 -*-
r"""A 阶段挑刺式复算（几何）。只读项目代码，不改任何 lib/m*/cfg。

运行（工作目录 人物建模/）：
  "D:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
      --python _stageA/accept_geom.py > _stageA/logs/accept_geom.log 2>&1

所有量测打印 [acc] key=value，并写 _stageA/logs/accept_geom.json。
口径说明（独立于生成者的 probe，不复用其结论）：
  · 连通分量一律 r=3mm 圆形膨胀 + 8 邻域（DESIGN §4.2 陷阱 2），按 (x,y) 平面算，
    不按 x 排序（陷阱 3）。
  · 净空定义 margin = body_y - cloth_y，正面 -Y，y 越小越前，margin>0 才安全。
  · 手部「指尖带」同时报 10mm 与 12mm 两种口径（生成者把 10 改成 12，需复核）。
"""
import os
import sys
import json
import math

import bpy
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import cfg                      # noqa: E402
import look                     # noqa: E402
import head as headmod          # noqa: E402
import body as bodymod          # noqa: E402
import hair as hairmod          # noqa: E402
import outfit as outfitmod      # noqa: E402
import hand as handmod          # noqa: E402
import rig as rigmod            # noqa: E402

LOG_DIR = os.path.join(HERE, "_stageA", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

REC = {}


def p(key, val, note=""):
    REC[key] = val
    extra = f"   # {note}" if note else ""
    print(f"[acc] {key}={val}{extra}")


def mm(v, nd=2):
    return None if v is None else round(v * 1000.0, nd)


# ---------------------------------------------------------------- 连通分量

def comps(points, cell=0.0005, dilate=0.0030):
    """(x,y) 点集 → (分量数, 每点标签, [(n_cells, cx, cy)...])。

    与 DESIGN §4.2 完全一致：先 r=dilate 圆形膨胀，再 8 邻域 BFS。
    返回的标签按「原始点」给出（取该点所在栅格）。
    """
    if len(points) == 0:
        return 0, np.zeros(0, dtype=int), []
    pts = np.asarray(points, dtype=float)
    r = int(round(dilate / cell))
    pad = r + 2
    i0 = int(np.floor(pts[:, 0].min() / cell))
    j0 = int(np.floor(pts[:, 1].min() / cell))
    nx = int(np.ceil(pts[:, 0].max() / cell)) - i0 + 1 + 2 * pad
    ny = int(np.ceil(pts[:, 1].max() / cell)) - j0 + 1 + 2 * pad
    grid = np.zeros((nx, ny), dtype=bool)
    ix = np.floor(pts[:, 0] / cell).astype(int) - i0 + pad
    iy = np.floor(pts[:, 1] / cell).astype(int) - j0 + pad
    grid[ix, iy] = True

    dil = grid.copy()
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            if dx == 0 and dy == 0:
                continue
            if dx * dx + dy * dy > r * r:
                continue
            dil |= np.roll(np.roll(grid, dx, axis=0), dy, axis=1)

    label = np.full((nx, ny), -1, dtype=int)
    cents = []
    n = 0
    for i in range(nx):
        row = dil[i]
        if not row.any():
            continue
        for j in range(ny):
            if not row[j] or label[i, j] >= 0:
                continue
            label[i, j] = n
            stack = [(i, j)]
            cells = [(i, j)]
            while stack:
                a, b = stack.pop()
                for da in (-1, 0, 1):
                    aa = a + da
                    if aa < 0 or aa >= nx:
                        continue
                    for db in (-1, 0, 1):
                        bb = b + db
                        if bb < 0 or bb >= ny:
                            continue
                        if dil[aa, bb] and label[aa, bb] < 0:
                            label[aa, bb] = n
                            stack.append((aa, bb))
                            cells.append((aa, bb))
            ci = sum(c[0] for c in cells) / len(cells)
            cj = sum(c[1] for c in cells) / len(cells)
            cents.append((len(cells), (ci - pad + i0) * cell, (cj - pad + j0) * cell))
            n += 1
    cents.sort(reverse=True)
    return n, label[ix, iy], cents


def min_gap(A, B):
    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    if len(A) == 0 or len(B) == 0:
        return None
    d = np.sqrt(((A[:, None, :] - B[None, :, :]) ** 2).sum(-1))
    return float(d.min())


def front_y(cos, lo, hi, xc=0.0, tol=0.004):
    sel = [c[1] for c in cos if lo <= c[2] <= hi and abs(c[0] - xc) <= tol and c[1] < 0.0]
    return min(sel) if sel else None


def bbox3(cos):
    a = np.asarray(cos, dtype=float)
    return (a[:, 0].min(), a[:, 0].max(), a[:, 1].min(), a[:, 1].max(),
            a[:, 2].min(), a[:, 2].max())


# ---------------------------------------------------------------- 构建（顺序同 m5_rig）

bpy.ops.wm.read_factory_settings(use_empty=True)
M = look.set_all()
h = headmod.build(M)
look.flatten_face(h)
b = bodymod.build()
hair = hairmod.build(M)
cloth = outfitmod.build(M)
hands = bpy.data.objects.get("Hands")

# ---------------- 对象清单 ----------------
inv = []
for ob in bpy.data.objects:
    if ob.type == 'MESH':
        inv.append({"name": ob.name, "verts": len(ob.data.vertices),
                    "faces": len(ob.data.polygons),
                    "mats": [m.name for m in ob.data.materials],
                    "mods": [m.type for m in ob.modifiers],
                    "vgroups": len(ob.vertex_groups)})
p("objects", inv)
p("object_count_before_rig", len(bpy.data.objects))

bcos = [tuple(v.co) for v in b.data.vertices]
hcos = [tuple(v.co) for v in h.data.vertices]
ccos = [tuple(cloth.matrix_world @ v.co) for v in cloth.data.vertices]
haircos = [tuple(v.co) for v in hair.data.vertices]
hndcos = [tuple(v.co) for v in hands.data.vertices]

bx = bbox3(bcos)
p("body_bbox_mm", [round(v * 1000, 2) for v in bx])
p("body_zmin_mm", round(bx[4] * 1000, 2))
p("body_verts", len(bcos))

# ---------------------------------------------------------------- A1 手
p("hands_verts", len(hndcos))
p("hands_vgroups_total", len(hands.vertex_groups))
p("hands_vgroup_names", [g.name for g in hands.vertex_groups])
p("hands_modifiers", [m.type for m in hands.modifiers])
p("palm_bot_z", handmod.PALM_BOT_Z)

hand_summary = {}
for side, tag in ((-1, "R"), (1, "L")):
    sel = [c for c in hndcos if c[0] * side > 0.02]
    if not sel:
        p(f"hand_{tag}", "EMPTY")
        continue
    x0, x1, y0, y1, z0, z1 = bbox3(sel)
    dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
    ratio = dz / max(dx, dy)
    s = {"bbox_mm": [round(v * 1000, 1) for v in (x0, x1, y0, y1, z0, z1)],
         "thick_x_mm": mm(dx, 1), "width_y_mm": mm(dy, 1), "len_z_mm": mm(dz, 1),
         "aspect_dz_max_dxdy": round(ratio, 3),
         "aspect_ok_0.8_1.6": 0.8 <= ratio <= 1.6,
         "aspect_ok_design_1.0_1.6": 1.0 <= ratio <= 1.6}

    # 指尖带：10mm 与 12mm 两种口径
    for band_mm in (10, 12):
        hi = z0 + band_mm / 1000.0
        pts = [(c[0], c[1]) for c in sel if z0 <= c[2] <= hi]
        n, _, cents = comps(pts)
        s[f"tip_band{band_mm}_comps"] = n
        s[f"tip_band{band_mm}_pts"] = len(pts)
        s[f"tip_band{band_mm}_cents_mm"] = [[c[0] * 1000, c[1] * 1000] for c in cents]
        p(f"hand_{tag}_tip{band_mm}_comps", n,
          f"pts={len(pts)} cents={[[round(c[1]*1000,1), round(c[2]*1000,1)] for c in cents]}")

    # 深度扫描：掌底向下每 2mm 取 2mm 厚切片
    root = handmod.PALM_BOT_Z
    scan = []
    first4 = None
    for dmm in range(0, 42, 2):
        lo = root - (dmm + 2) / 1000.0
        hi = root - dmm / 1000.0
        pts = [(c[0], c[1]) for c in sel if lo <= c[2] <= hi]
        n, _, _ = comps(pts)
        scan.append([dmm, n, len(pts)])
        if n >= 4 and first4 is None:
            first4 = dmm
    s["depth_scan"] = scan
    s["first_4comp_depth_mm"] = first4
    p(f"hand_{tag}_depth_scan", " ".join(f"{d}:{n}" for d, n, _ in scan))
    p(f"hand_{tag}_first4_depth_mm", first4)

    # 中段（掌底下方 12~14mm）分量与相邻最小间隙
    lo = root - 0.014
    hi = root - 0.012
    pts = [(c[0], c[1]) for c in sel if lo <= c[2] <= hi]
    n, labels, cents = comps(pts)
    groups = {}
    for (pt, lab) in zip(pts, labels):
        groups.setdefault(int(lab), []).append(pt)
    order = sorted(groups.keys(), key=lambda k: np.mean([g[1] for g in groups[k]]))
    gaps = []
    for a, bb in zip(order, order[1:]):
        g = min_gap(groups[a], groups[bb])
        if g is not None:
            gaps.append(round(g * 1000, 2))
    s["mid_comps"] = n
    s["mid_pts"] = len(pts)
    s["mid_gaps_mm"] = gaps
    p(f"hand_{tag}_mid_comps", n, f"z=[{lo:.4f},{hi:.4f}] pts={len(pts)}")
    p(f"hand_{tag}_mid_gaps_mm", gaps)

    # 手腕接缝：手最靠上的 x-z 截面 vs 前臂末端
    wrist_band = [c for c in sel if z0 + 0.045 <= c[2] <= z1]
    if wrist_band:
        wx0, wx1 = min(c[0] for c in wrist_band), max(c[0] for c in wrist_band)
        wy0, wy1 = min(c[1] for c in wrist_band), max(c[1] for c in wrist_band)
        # 前臂末端在 Body 上的截面（同 z 带、同侧）
        arm_pts = [c for c in bcos if c[0] * side > 0.15 and z0 + 0.045 <= c[2] <= z1]
        if arm_pts:
            ax0, ax1 = min(c[0] for c in arm_pts), max(c[0] for c in arm_pts)
            ay0, ay1 = min(c[1] for c in arm_pts), max(c[1] for c in arm_pts)
            s["wrist_hand_xz_span_mm"] = [mm(wx0, 1), mm(wx1, 1), mm(wy0, 1), mm(wy1, 1)]
            s["wrist_arm_xz_span_mm"] = [mm(ax0, 1), mm(ax1, 1), mm(ay0, 1), mm(ay1, 1)]
            s["wrist_overlap_x_mm"] = [round(max(wx0, ax0) * 1000, 1),
                                       round(min(wx1, ax1) * 1000, 1)]
            s["wrist_overlap_y_mm"] = [round(max(wy0, ay0) * 1000, 1),
                                       round(min(wy1, ay1) * 1000, 1)]
            p(f"hand_{tag}_wrist_overlap_x_mm", s["wrist_overlap_x_mm"])
            p(f"hand_{tag}_wrist_overlap_y_mm", s["wrist_overlap_y_mm"])
    # 每手顶点组数
    nvg = len([g for g in hands.vertex_groups if g.name.endswith("_" + tag)])
    s["vgroups_this_hand"] = nvg
    p(f"hand_{tag}_vgroups", nvg)
    hand_summary[tag] = s
p("hand_summary", hand_summary)

# ---------------------------------------------------------------- A4 脚趾

zmin = bx[4]
p("foot_zmin_mm", round(zmin * 1000, 2))
foot_res = {}
for side, tag in ((1, "L"), (-1, "R")):
    sel = [c for c in bcos if c[0] * side > 0.02]
    r = {}
    # ① 裸 z∈[6,20]mm
    pts = [(c[0], c[1]) for c in sel if 0.006 <= c[2] <= 0.020]
    r["bare_z6_20"] = comps(pts)[0]
    # ② z∈[4,20]mm ∧ y<=-96mm（陈拓口径）
    pts = [(c[0], c[1]) for c in sel if 0.004 <= c[2] <= 0.020 and c[1] <= -0.096]
    r["z4_20_y96"] = comps(pts)[0]
    r["z4_20_y96_pts"] = len(pts)
    # ③ z∈[6,16]mm ∧ y<=-90mm（验收者口径）
    pts = [(c[0], c[1]) for c in sel if 0.006 <= c[2] <= 0.016 and c[1] <= -0.090]
    r["z6_16_y90"] = comps(pts)[0]
    r["z6_16_y90_pts"] = len(pts)
    # ④ y=-100mm 处 x-z 切片（独立终判口径）
    pts = []
    for half in (0.0015, 0.0025):
        pts = [(c[0], c[2]) for c in sel if abs(c[1] + 0.100) <= half and c[2] < 0.060]
        if len(pts) >= 30:
            r["y100_halfband_mm"] = half * 1000
            break
    r["y100_xz"] = comps(pts)[0]
    r["y100_xz_pts"] = len(pts)
    r["y100_cents_mm"] = [[round(c[1] * 1000, 1), round(c[2] * 1000, 1)]
                          for c in comps(pts)[2]]
    # 趾缝凹陷：z∈[6,16] ∧ y<=-90 的 x 方向直方图凹陷数
    xs = sorted(c[0] for c in sel if 0.006 <= c[2] <= 0.016 and c[1] <= -0.090)
    if xs:
        bins = np.arange(min(xs), max(xs) + 0.001, 0.001)
        hist, _ = np.histogram(xs, bins=bins)
        # 仅统计两侧都有内容的空档（被夹住的 0 段）= 趾缝
        nz = [k for k, v in enumerate(hist) if v > 0]
        gaps = 0
        for ia, ib in zip(nz, nz[1:]):
            if ib - ia > 1:
                gaps += 1
        r["x_hist_gaps"] = gaps
        r["x_hist"] = hist.tolist()
        r["x_range_mm"] = [round(min(xs) * 1000, 1), round(max(xs) * 1000, 1)]
    foot_res[tag] = r
p("foot", foot_res)

# ---------------------------------------------------------------- A2 / A6

hx0, hx1, hy0, hy1, hz0, hz1 = bbox3(hcos)
head_len = hz1 - hz0
head_w = hx1 - hx0
head_d = hy1 - hy0
stature = hz1 - zmin
p("head_z_range", [round(hz0, 4), round(hz1, 4)])
p("head_len", round(head_len, 4), "目标 0.2492±0.002")
p("head_width", round(head_w, 4), "目标 0.212~0.218")
p("head_depth", round(head_d, 4), "目标 0.182~0.190")
p("head_y_front_back", [round(hy0, 4), round(hy1, 4)])
p("stature", round(stature, 4), "目标 1.620±0.005")
p("heads_ratio", round(stature / head_len, 3), "目标 6.50±0.06")

# 头宽口径 2：HEAD 表本身（不含耳贴片）
head_w_table = 2.0 * max(r[1] for r in headmod.HEAD)
p("head_width_from_HEAD_table", round(head_w_table, 4))

# 下巴：整体 z_min 与中线（|x|<5mm, y<0）
chin_all = min(c[2] for c in hcos)
chin_mid = min(c[2] for c in hcos if abs(c[0]) < 0.005 and c[1] < 0.0)
p("chin_z_all", round(chin_all, 4))
p("chin_z_midline", round(chin_mid, 4))
p("cfg_CHIN_Z", cfg.CHIN_Z)
p("cfg_CHIN_Z_vs_measured_mm", round((cfg.CHIN_Z - chin_mid) * 1000, 2))

# 鼻子
zn_lo, zn_hi = headmod.sz(1.440), headmod.sz(1.470)
zf_lo, zf_hi = headmod.sz(1.520), headmod.sz(1.570)


def mid_front(lo, hi, xmax=0.003):
    sel = [c[1] for c in hcos if abs(c[0]) < xmax and lo <= c[2] <= hi and c[1] < 0]
    return (min(sel), len(sel)) if sel else (None, 0)


nose_y, nose_n = mid_front(zn_lo, zn_hi)
fore_y, fore_n = mid_front(zf_lo, zf_hi)
p("nose_tip_y", round(nose_y, 5) if nose_y else None)
p("forehead_y", round(fore_y, 5) if fore_y else None)
p("nose_protrusion_mm", round((fore_y - nose_y) * 1000, 2) if nose_y else None,
  "目标 8.5~10.0")
p("nose_windows", [round(zn_lo, 4), round(zn_hi, 4), round(zf_lo, 4), round(zf_hi, 4)])


def verts_by_mat(ob, name):
    m = ob.data
    idx = {i for i, mat in enumerate(m.materials)
           if mat is not None and mat.name.split(".")[0] == name}
    vi = set()
    for poly in m.polygons:
        if poly.material_index in idx:
            vi.update(poly.vertices)
    return [tuple(m.vertices[i].co) for i in vi]


lip = verts_by_mat(h, "lip")
if lip:
    lx = [c[0] for c in lip]
    mw = max(lx) - min(lx)
    p("mouth_width", round(mw, 4))
    p("mouth_over_head_bbox", round(100.0 * mw / head_w, 2))
    p("mouth_over_head_table", round(100.0 * mw / head_w_table, 2))
else:
    p("mouth", "MISS")

sclera = verts_by_mat(h, "sclera")
if sclera:
    rx = [c[0] for c in sclera if c[0] > 0]
    lx = [c[0] for c in sclera if c[0] < 0]
    inner = min(rx) - max(lx)
    win_w = (max(rx) - min(rx) + max(lx) - min(lx)) / 2.0
    p("eye_inner_gap", round(inner, 4))
    p("eye_width", round(win_w, 4))
    p("eye_ratio", round(inner / win_w, 3), "目标 0.85~1.00（内眼角口径）")

# 耳高（同 ear() 单建）
earL = headmod.ear(-1, M)
ez = [v.co.z for v in earL.data.vertices]
p("ear_height_mm", round((max(ez) - min(ez)) * 1000, 2), "目标 45~50")
p("ear_z_range", [round(min(ez), 4), round(max(ez), 4)])
me_ear = earL.data
bpy.data.objects.remove(earL, do_unlink=True)
bpy.data.meshes.remove(me_ear)

# 脖子：下巴到各颈/肩地标的垂直距离
torso_top = max(r[0] for r in bodymod.TORSO)
p("torso_top_z", torso_top)
p("neck_chin_to_torso_top_mm", round((chin_mid - torso_top) * 1000, 1))
p("neck_chin_to_SHOULDER_Z_mm", round((chin_mid - cfg.SHOULDER_Z) * 1000, 1))
p("neck_chin_to_TORSO_maxrx_z_mm", round((chin_mid - 1.290) * 1000, 1))
p("neck_chin_to_shoulder_over_head", round((chin_mid - cfg.SHOULDER_Z) / head_len, 3))

# 面中法线偏离
me = h.data
try:
    cn = [c.vector.copy() for c in me.corner_normals]
except AttributeError:
    cn = [lp.normal.copy() for lp in me.loops]
target = look.Vector((0.0, -1.0, 0.0))


def max_dev(zlo, zhi, xmax=0.013):
    worst = 0.0
    at = None
    cnt = 0
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index]
            if abs(v.co.x) < xmax and zlo <= v.co.z <= zhi and v.co.y < -0.02:
                d = max(-1.0, min(1.0, cn[li].dot(target)))
                a = math.degrees(math.acos(d))
                cnt += 1
                if a > worst:
                    worst = a
                    at = (v.co.x, v.co.y, v.co.z)
    return cnt, worst, at


c1, w1, a1 = max_dev(headmod.sz(1.440), headmod.sz(1.500))
c2, w2, a2 = max_dev(headmod.sz(1.400), headmod.sz(1.550))
p("normals_mid_deg", round(w1, 2), f"loop={c1} at_mm={[round(v*1000,1) for v in a1]}")
p("normals_face_deg", round(w2, 2), f"loop={c2} at_mm={[round(v*1000,1) for v in a2]}")
p("normals_mid_at", [round(v, 4) for v in a1])
p("normals_face_at", [round(v, 4) for v in a2])

# ---------------------------------------------------------------- A3 衬衫净空

param = bodymod.torso()
bodymod.sculpt_torso(param)
pcos = [tuple(v.co) for v in param.data.vertices]
me_p = param.data
bpy.data.objects.remove(param, do_unlink=True)
bpy.data.meshes.remove(me_p)

BANDS = ((1.100, 1.140), (1.140, 1.180), (1.180, 1.220))
XS = ((0.000, 0.004), (-0.040, 0.012), (0.040, 0.012))
shirt = {}
for lo, hi in BANDS:
    key = f"{lo:.3f}-{hi:.3f}"
    row_body, row_param = [], []
    for xc, tol in XS:
        by = front_y(bcos, lo, hi, xc, tol)
        py = front_y(pcos, lo, hi, xc, tol)
        cy = front_y(ccos, lo, hi, xc, tol)
        if by is not None and cy is not None:
            row_body.append([round(xc * 1000), mm(by - cy)])
        if py is not None and cy is not None:
            row_param.append([round(xc * 1000), mm(py - cy)])
    mb = min(row_body, key=lambda t: t[1]) if row_body else None
    mp_ = min(row_param, key=lambda t: t[1]) if row_param else None
    shirt[key] = {"bodymesh": row_body, "param": row_param,
                  "min_bodymesh": mb, "min_param": mp_}
    p(f"shirt_margin_body_{key}", mb)
    p(f"shirt_margin_param_{key}", mp_)

# ---------------------------------------------------------------- A5 袖口 / 呆毛

SEG = 40


def _unit(v):
    ln = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / ln for x in v]


def _sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def _dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def _mean(pts):
    n = len(pts)
    return [sum(p[i] for p in pts) / n for i in range(3)]


def _perp(pts, c, axis):
    out = []
    for pt in pts:
        d = _sub(pt, c)
        al = _dot(d, axis)
        perp = [d[i] - al * axis[i] for i in range(3)]
        out.append(math.sqrt(sum(x * x for x in perp)))
    return out


def sleeve_mouth(side):
    ob = outfitmod._sleeve(side, solid=False, cuff=False)
    vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
    vs = [[v.x, v.y, v.z] for v in vs]
    ring = vs[-(SEG + 2):-2]
    prev = vs[-(2 * SEG + 2):-(SEG + 2)]
    c_last = _mean(ring)
    c_prev = _mean(prev)
    axis = _unit(_sub(c_last, c_prev))
    rad = sorted(_perp(ring, c_last, axis))
    me_ = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me_)
    return {"center": c_last, "axis": axis, "radius": rad[-1],
            "radius_med": rad[len(rad) // 2], "n": len(rad)}


def arm_radius_at(mouth, side, xmin=0.135, band=0.005, rmax=0.070):
    axis, rc = mouth["axis"], mouth["center"]
    sel = []
    for c in bcos:
        if c[0] * side <= xmin:
            continue
        d = _sub(list(c), rc)
        if abs(_dot(d, axis)) > band:
            continue
        if _perp([list(c)], rc, axis)[0] > rmax:
            continue
        sel.append(list(c))
    if len(sel) < 8:
        return None, None, None
    rad = sorted(_perp(sel, rc, axis))
    return rad[len(rad) // 2], rad[-1], rad[0]


cuff = {}
for side, tag in ((1, "R(+x)"), (-1, "L(-x)")):
    m = sleeve_mouth(side)
    med, mx, mn = arm_radius_at(m, side)
    c = {"center_mm": [round(v * 1000, 1) for v in m["center"]],
         "axis": [round(v, 3) for v in m["axis"]],
         "cuff_radius_mm": round(m["radius"] * 1000, 2),
         "cuff_radius_med_mm": round(m["radius_med"] * 1000, 2),
         "arm_radius_med_mm": mm(med), "arm_radius_max_mm": mm(mx),
         "arm_radius_min_mm": mm(mn),
         "diff_vs_arm_med_mm": None if med is None else round((m["radius"] - med) * 1000, 2),
         "diff_vs_45mm": round((m["radius"] - 0.045) * 1000, 2),
         "diff_vs_53mm_arm": None if med is None else round((0.053 - med) * 1000, 2)}
    cuff[tag] = c
    p(f"cuff_{tag}", c)
# 袖口半径 53mm 是否会切进：比较 53 - 实测臂半径
p("cuff_53_minus_arm", {t: cuff[t]["diff_vs_53mm_arm"] for t in cuff})

# 边界边
import bmesh
bm = bmesh.new()
bm.from_mesh(cloth.data)
inner = total = 0
for e in bm.edges:
    if not e.is_boundary:
        continue
    total += 1
    if all(v.co.z < 1.140 and v.co.x > 0.130 for v in e.verts):
        inner += 1
bm.free()
p("cuff_boundary_edges_region", inner)
p("outfit_boundary_edges_total", total)

# 卷边外表面半径
if "R(+x)" in cuff:
    m = sleeve_mouth(1)
    sel = [list(c) for c in ccos if c[0] > 0.13
           and abs(_dot(_sub(list(c), m["center"]), m["axis"])) <= 0.010]
    if sel:
        rad = sorted(_perp(sel, m["center"], m["axis"]))
        p("cuff_ring_outfit_rmax_mm", round(rad[-1] * 1000, 2),
          f"凸出={(rad[-1] - m['radius'])*1000:+.1f}mm")
        p("cuff_ring_verts", len(sel))
    # 清理
    # (sleeve_mouth 已删除临时对象)

# 呆毛
AH = hairmod._ahoge()
ring_w = {}
if AH:
    ob = AH[0]
    vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
    vs = [[v.x, v.y, v.z] for v in vs]
    n_ring = (len(vs) // 10) * 10
    rings = [vs[i:i + 10] for i in range(0, n_ring, 10)]
    wx = [(max(q[0] for q in r) - min(q[0] for q in r), r[0][2]) for r in rings]
    wy = [(max(q[1] for q in r) - min(q[1] for q in r), r[0][2]) for r in rings]
    ring_w = {"max_x_mm": round(max(w[0] for w in wx) * 1000, 2),
              "max_y_mm": round(max(w[0] for w in wy) * 1000, 2),
              "x_at_z": [[round(w[0] * 1000, 2), round(w[1], 4)] for w in wx],
              "z_range": [round(min(q[2] for q in vs), 4), round(max(q[2] for q in vs), 4)],
              "verts": len(vs), "rings": len(rings)}
    me_a = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me_a)
p("ahoge_standalone", ring_w)
p("ahoge_above_head_mm", round((ring_w.get("z_range", [None, 0])[1] - hz1) * 1000, 1),
  "目标 40~55")
above = [c for c in haircos if c[2] > 1.62]
if above:
    p("ahoge_hair_z>1.62_xspan_mm",
      round((max(c[0] for c in above) - min(c[0] for c in above)) * 1000, 2),
      "整体 bbox 轨迹跨度（非单环，仅对照）")
    p("ahoge_hair_z>1.62_verts", len(above))
p("hair_zmax", round(max(c[2] for c in haircos), 4))

# 裙腰净空
skirt = {}
for lo, hi in ((1.000, 1.040), (0.960, 1.000), (0.920, 0.960)):
    key = f"{lo:.3f}-{hi:.3f}"
    rows_b, rows_p = [], []
    for xc, tol in XS:
        by = front_y(bcos, lo, hi, xc, tol)
        py = front_y(pcos, lo, hi, xc, tol)
        cy = front_y(ccos, lo, hi, xc, tol)
        if by is not None and cy is not None:
            rows_b.append([round(xc * 1000), mm(by - cy)])
        if py is not None and cy is not None:
            rows_p.append([round(xc * 1000), mm(py - cy)])
    skirt[key] = {"bodymesh": rows_b, "param": rows_p,
                  "min_bodymesh": min(rows_b, key=lambda t: t[1]) if rows_b else None,
                  "min_param": min(rows_p, key=lambda t: t[1]) if rows_p else None}
    p(f"skirt_margin_body_{key}", skirt[key]["bodymesh"])
    p(f"skirt_margin_param_{key}", skirt[key]["param"])
# 更细：x 网格扫描，找最负的点
skirt_scan = []
for lo, hi in ((1.000, 1.040),):
    for xmm in range(-60, 61, 20):
        xc = xmm / 1000.0
        by = front_y(bcos, lo, hi, xc, 0.006)
        cy = front_y(ccos, lo, hi, xc, 0.006)
        if by is not None and cy is not None:
            skirt_scan.append([xmm, mm(by - cy)])
p("skirt_scan_x_mm", skirt_scan, "z 1.00~1.04，x=-60..60 步 20mm")

# ---------------------------------------------------------------- 骨架/绑定

armature = rigmod.build_armature()
p("armature_bones", len(armature.data.bones))
p("hand_groups_match_bones", [g.name for g in hands.vertex_groups
                              if g.name in armature.data.bones])
p("object_count_with_rig", len(bpy.data.objects))

# 姿势响应：先按 m5_rig 的方式绑 Body/Outfit/Head/Hair（**不绑 Hands**），
# 再用 depsgraph 取求值后的 bbox，判断 Hands 是否随姿势移动。
rigmod.weight_nearest(b, armature, [n for n, *_ in rigmod.BONES], power=4.0, keep=3)
rigmod.weight_nearest(cloth, armature, sorted(rigmod.UPPER), power=4.0, keep=2)
rigmod.rigid_to(h, armature, "head")
rigmod.rigid_to(hair, armature, "head")


def eval_bbox(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me2 = ev.to_mesh()
    mw = ev.matrix_world
    pts = [mw @ v.co for v in me2.vertices]
    out = (min(q.x for q in pts), max(q.x for q in pts),
           min(q.y for q in pts), max(q.y for q in pts),
           min(q.z for q in pts), max(q.z for q in pts))
    ev.to_mesh_clear()
    return out


pose_res = {}
for pose in ("rest", "wave"):
    rigmod.apply_pose(armature, pose)
    pose_res[pose] = {"hands": eval_bbox(hands), "body": eval_bbox(b)}
d_hands = max(abs(pose_res["wave"]["hands"][i] - pose_res["rest"]["hands"][i])
              for i in range(6))
d_body = max(abs(pose_res["wave"]["body"][i] - pose_res["rest"]["body"][i])
             for i in range(6))
p("pose_hands_bbox_delta_mm", round(d_hands * 1000, 3))
p("pose_body_bbox_delta_mm", round(d_body * 1000, 3))
p("pose_rest_hands_bbox", [round(v, 4) for v in pose_res["rest"]["hands"]])
p("pose_wave_hands_bbox", [round(v, 4) for v in pose_res["wave"]["hands"]])
p("objects_with_rig", [f"{o.name}:{o.type}" for o in bpy.data.objects])

def _san(o):
    if isinstance(o, dict):
        return {k: _san(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_san(v) for v in o]
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.generic):
        return o.item()
    return o


with open(os.path.join(LOG_DIR, "accept_geom.json"), "w", encoding="utf-8") as f:
    json.dump(_san(REC), f, ensure_ascii=False, indent=1)
print("[acc] done -> _stageA/logs/accept_geom.json")