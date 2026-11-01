# -*- coding: utf-8 -*-
"""A1/A4 几何量测（不渲染）：在同一 Blender 进程里构建 Body + Hands 然后量。

设计口径（DESIGN §4.2 的三个陷阱全部按这里的写法规避）：
  1. 连通分量**必须** r=3mm 膨胀 + 8 邻域，否则 2mm 体素网格的表面会被切成几十块假阳性。
  2. 不按 x 排序判分叉（闭合环天然断两段），一律用 (x,y) 平面连通分量。
  3. 「指尖切片」口径：z ∈ [该手 z_min, z_min+10mm]；另有「各指末端 5mm」的
     精确口径作为交叉验证。脚趾切片见下方 TOE 说明。

运行：
  "D:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
      --python _stageA/a1_hand_probe.py 2>&1 | grep -E "\\[probe\\]|Traceback"
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "lib"))

import bpy
import numpy as np
from collections import deque

import cfg
import body as bodymod
import hand as handmod

LAST_CENTROIDS = []


# ---------------- 量测工具 ----------------

def cos_of(ob):
    mw = ob.matrix_world
    return [mw @ v.co for v in ob.data.vertices]


def bbox(cos):
    xs = [c.x for c in cos]
    ys = [c.y for c in cos]
    zs = [c.z for c in cos]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


def components(points, cell=0.0005, dilate=0.0030):
    """(x,y) 点集 → 先 r=dilate 圆形膨胀，再 8 邻域连通分量数。

    返回 (分量数, 点数, 网格边长)。纯 numpy：对圆内偏移逐次 roll 后取并集。
    pad 取 r+2，保证 np.roll 的循环卷绕不会把远端内容接到有效区域内。
    """
    if not points:
        return 0, 0, (0, 0)
    xs = np.fromiter((p[0] for p in points), dtype=float)
    ys = np.fromiter((p[1] for p in points), dtype=float)
    r = int(round(dilate / cell))
    pad = r + 2
    i0 = int(np.floor(xs.min() / cell))
    j0 = int(np.floor(ys.min() / cell))
    nx = int(np.ceil(xs.max() / cell)) - i0 + 1 + 2 * pad
    ny = int(np.ceil(ys.max() / cell)) - j0 + 1 + 2 * pad
    grid = np.zeros((nx, ny), dtype=bool)
    ix = np.floor(xs / cell).astype(int) - i0 + pad
    iy = np.floor(ys / cell).astype(int) - j0 + pad
    grid[ix, iy] = True

    dil = grid.copy()
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            if dx == 0 and dy == 0:
                continue
            if dx * dx + dy * dy > r * r:
                continue
            dil |= np.roll(np.roll(grid, dx, axis=0), dy, axis=1)

    seen = np.zeros_like(dil)
    count = 0
    cents = []
    for i in range(nx):
        if not dil[i].any():
            continue
        for j in range(ny):
            if not dil[i, j] or seen[i, j]:
                continue
            count += 1
            seen[i, j] = True
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
                        if dil[aa, bb] and not seen[aa, bb]:
                            seen[aa, bb] = True
                            stack.append((aa, bb))
                            cells.append((aa, bb))
            ci = sum(c[0] for c in cells) / len(cells)
            cj = sum(c[1] for c in cells) / len(cells)
            cents.append((len(cells), (ci - pad + i0) * cell, (cj - pad + j0) * cell))
    global LAST_CENTROIDS
    LAST_CENTROIDS = sorted(cents, reverse=True)
    return count, len(points), (nx, ny)


def zmin(cos):
    return min(c.z for c in cos)


# ---------------- 构建 ----------------

bpy.ops.wm.read_factory_settings(use_empty=True)
body = bodymod.build()
hands = bpy.data.objects.get("Hands")
if hands is None:
    print("[probe] FATAL: 没有 Hands 物体（hand.build_pair 未执行）")
    raise SystemExit(1)

bcos = cos_of(body)
x0, x1, y0, y1, z0, z1 = bbox(bcos)
print(f"[probe] Body verts={len(body.data.vertices)} x[{x0:+.4f},{x1:+.4f}] "
      f"y[{y0:+.4f},{y1:+.4f}] z[{z0:+.4f},{z1:+.4f}]")
print(f"[probe] Body z_min={z0 * 1000.0:+.3f}mm  (验收 [-2,+2]mm)")
print(f"[probe] Body floor_ok={-0.002 <= z0 <= 0.002}")

# ---------------- 腕部径向台阶（A1 返工新增） ----------------
# 口径（写死在这，避免以后口径漂移；-Y 是正脸方向，与 body.arm() 一致）：
#   * 腕平面带 z ∈ [WRIST_Z-5mm, WRIST_Z+5mm]，两组物体各取带内顶点。
#   * 前臂外半径 = Body 里只属于该手臂的顶点（|x*side - WRIST_X| < 40mm，排除躯干/腿）
#     相对手轴心 (WRIST_X*side, WRIST_Y) 的最大 |Δy|（宽方向）和最大 |Δx|（厚方向）。
#   * 手掌半宽   = Hands 在同一带内的最大 |Δy| / |Δx|。
#   * 台阶 = 前臂外半径 − 手掌半宽；验收「径向台阶 ≤3mm」（宽、厚两个方向都要看，
#     因为手是扁的，只看宽方向会把厚度方向的台阶藏起来）。
hcos = cos_of(hands)

WRIST_Z = handmod.WRIST_Z
WX = handmod.WRIST_X
WY = handmod.WRIST_Y


def band_extent(cos, zlo, zhi, cx, cy, xmax=None):
    """带内顶点相对轴心 (cx, cy) 的最大 |Δx| / |Δy|，返回 (dx, dy, n)。"""
    mx = my = 0.0
    n = 0
    for c in cos:
        if not (zlo <= c.z <= zhi):
            continue
        if xmax is not None and abs(c.x - cx) > xmax:
            continue
        n += 1
        mx = max(mx, abs(c.x - cx))
        my = max(my, abs(c.y - cy))
    return mx, my, n


wlo, whi = WRIST_Z - 0.005, WRIST_Z + 0.005
for side, tag in ((-1, "R"), (1, "L")):
    ax, ay, an = band_extent(bcos, wlo, whi, WX * side, WY, xmax=0.040)
    px_, py_, pn = band_extent([c for c in hcos if c.x * side > 0.02],
                               wlo, whi, WX * side, WY)
    print(f"[probe] wrist_{tag} z[{wlo:.4f},{whi:.4f}] "
          f"forearm_radius x={ax * 1000:.2f} y={ay * 1000:.2f}mm n={an} | "
          f"palm_half x={px_ * 1000:.2f} y={py_ * 1000:.2f}mm n={pn}")
    print(f"[probe] wrist_{tag} step x={(ax - px_) * 1000:+.2f}mm "
          f"y={(ay - py_) * 1000:+.2f}mm  (验收 径向台阶 <=3mm) "
          f"{'PASS' if max(ax - px_, ay - py_) <= 0.003 else 'FAIL'}")

# ---------------- 手 ----------------

print(f"[probe] Hands verts={len(hands.data.vertices)} "
      f"vgroups={len(hands.vertex_groups)}")

for side, tag in ((-1, "R"), (1, "L")):
    sel = [c for c in hcos if c.x * side > 0.02]
    if not sel:
        print(f"[probe] hand_{tag}: 空")
        continue
    hx0, hx1, hy0, hy1, hz0, hz1 = bbox(sel)
    dx, dy, dz = hx1 - hx0, hy1 - hy0, hz1 - hz0
    ratio = dz / max(dx, dy)
    print(f"[probe] hand_{tag} bbox x[{hx0:+.4f},{hx1:+.4f}] y[{hy0:+.4f},{hy1:+.4f}] "
          f"z[{hz0:+.4f},{hz1:+.4f}]")
    print(f"[probe] hand_{tag} size mm: thick_x={dx * 1000:.1f} width_y={dy * 1000:.1f} "
          f"len_z={dz * 1000:.1f}")
    print(f"[probe] hand_{tag} aspect(z/max(x,y))={ratio:.3f}  (验收 [0.8,1.6]) "
          f"aspect_ok={0.8 <= ratio <= 1.6}")

    vg_names = [g.name for g in hands.vertex_groups if g.name.endswith("." + tag)]

    # ===== 判据 A（主）：每指「自己最末 5mm」独立切片 =====
    # 为什么不再用统一 z 带：band 10mm 得 3、band 12mm 得 4，4 分量只存在于 4mm 薄带里、
    # 余量 1.2mm —— 判据本身比被测几何还脆弱，换个角度（手指微屈 0.5°）就会翻结论。
    # 现在改为按顶点组各取「该指自己最末 5mm」，逐指算 xy_components（须 ≥1），
    # 再合并算一次（须 =4：四指的分量互不连通）。
    #
    # B3 之后顶点组粒度从「每指 1 组」细化成「每指 proximal/middle/distal 3 段」，
    # 组名从 index_R 变成 index_proximal.R 等，所以这里要把 3 段组合起来用。
    FINGER_SET = ("index", "middle", "ring", "pinky")
    SEGS = ("proximal", "middle", "distal")
    tip5 = {}
    for base_name in FINGER_SET:
        gi_set = [hands.vertex_groups[nm].index for nm in
                  (f"{base_name}_{seg}.{tag}" for seg in SEGS)
                  if nm in hands.vertex_groups]
        if not gi_set:
            print(f"[probe] hand_{tag}_tip5 {base_name}: NO GROUP FAIL")
            continue
        vs = [hands.data.vertices[v.index].co
              for v in hands.data.vertices
              if any(gg.group in gi_set and gg.weight > 0 for gg in v.groups)]
        if not vs:
            print(f"[probe] hand_{tag}_tip5 {base_name}: EMPTY FAIL")
            continue
        zl = min(v.z for v in vs)
        grp = [v for v in vs if v.z <= zl + 0.005]
        tip5[base_name] = grp
        na, ma, _ = components([(v.x, v.y) for v in grp])
        print(f"[probe] hand_{tag}_tip5 {base_name}: vgrp_v={len(vs)} tip5_v={len(grp)} "
              f"z[{zl:.4f},{zl + 0.005:.4f}] xy_components={na} pts={ma} "
              f"{'PASS' if na >= 1 else 'FAIL'}")

    merged = [(v.x, v.y) for g in tip5.values() for v in g]
    n5, m5, _ = components(merged)
    all_have = (len(tip5) == 4)
    print(f"[probe] hand_{tag}_tip5_merged fingers={len(tip5)}/4 xy_components={n5} "
          f"pts={m5} (验收 每指各自>=1 且合并仍=4) "
          f"{'PASS' if all_have and n5 == 4 else 'FAIL'}")

    # ===== 判据 B：掌底向下深度扫描 =====
    # 从指根高度 PALM_BOT_Z 向下，每 2mm 一档、档厚 2mm，逐档投影算 xy_components，
    # 打印「深度:mm 处分量数」曲线 + 首次达到 4 分量的深度。
    # 单一切片只是这条曲线的一个采样点；曲线才是「手指从掌里分出来」的完整描述。
    curve, first4 = [], None
    base_z = handmod.PALM_BOT_Z
    d = 0.0
    while base_z - d >= hz0 - 0.001:
        clo, chi = base_z - d - 0.001, base_z - d + 0.001
        pts = [(c.x, c.y) for c in sel if clo <= c.z <= chi]
        nc, mc, _ = components(pts)
        curve.append((d, nc, mc))
        if nc >= 4 and first4 is None:
            first4 = d
        d += 0.002
    print(f"[probe] hand_{tag}_depth_scan "
          + " ".join(f"{dd * 1000:.0f}mm:{nc}" for dd, nc, _ in curve))
    if first4 is None:
        print(f"[probe] hand_{tag}_first4_components depth=None "
              f"(扫到 {(base_z - hz0) * 1000:.1f}mm 仍未到 4 分量) FAIL")
    else:
        print(f"[probe] hand_{tag}_first4_components depth={first4 * 1000:.0f}mm "
              f"(从掌底 PALM_BOT_Z 向下计，档厚 2mm) PASS")

    # ===== 对照（不作判据）：原来的单一 z 带 =====
    lo, hi = hz0, hz0 + 0.012
    tip_pts = [(c.x, c.y) for c in sel if lo <= c.z <= hi]
    n, m, g = components(tip_pts)
    print(f"[probe] hand_{tag}_tip_uniformband z[{lo:.4f},{hi:.4f}] "
          f"xy_components={n} pts={m} grid={g} (仅对照，不作判据)")

    # 掌心带：掌根以上 6~20mm，应当是 1 个分量（闭合扁掌）
    plo = handmod.PALM_BOT_Z + 0.006
    phi = handmod.PALM_BOT_Z + 0.020
    palm_pts = [(c.x, c.y) for c in sel if plo <= c.z <= phi]
    np_comps, nmp, _ = components(palm_pts)
    print(f"[probe] hand_{tag}_palm z[{plo:.4f},{phi:.4f}] xy_components={np_comps} "
          f"pts={nmp} (基线上限 1，掌是完整闭合块)")

    print(f"[probe] hand_{tag} vgroups={len(vg_names)} "
          f"(验收 >=5) {'PASS' if len(vg_names) >= 5 else 'FAIL'} {vg_names}")

# ---------------- 脚趾 ----------------
#
# 口径陷阱（写清楚，别被数字骗）：
#   按 DESIGN 原文「toe 切片 z∈[8,20]mm」直接投影，脚掌主体在这个高度带内
#   也有完整侧壁，投影与脚趾**必然连通**（解剖上脚趾必须连着脚掌），
#   所以裸 z 切片的上限就是 1 个分量，加脚趾也不会变。
#   真正的「脚趾分叉」体现在趾与趾之间的空隙，所以主指标取「趾区」口径：
#   z∈[4,20]mm ∧ y ≤ TOE_ZONE_Y（脚掌前端做到 -0.092，这条线之外只剩脚趾）。
#   同时打印裸 z 切片的对照值，两个数一起看。
cos = bcos
ft_lo, ft_hi = z0 + 0.004, z0 + 0.020

for side, tag in ((1, "L"), (-1, "R")):
    sel = [c for c in cos if c.x * side > 0.02]
    if not sel:
        continue
    # 主指标：趾区
    zone = [(c.x, c.y) for c in sel
            if ft_lo <= c.z <= ft_hi and c.y <= bodymod.TOE_ZONE_Y]
    nz, mz, _ = components(zone)
    print(f"[probe] foot_{tag}_toe_zone z[{ft_lo:.4f},{ft_hi:.4f}] "
          f"y<= {bodymod.TOE_ZONE_Y:.3f} xy_components={nz} pts={mz} "
          f"(验收 >=2) {'PASS' if nz >= 2 else 'FAIL'}")

    # 对照：裸 z 切片（无 y 限制），预期 1（口径陷阱，见上）
    bare = [(c.x, c.y) for c in sel if ft_lo <= c.z <= ft_hi]
    nb, mb, _ = components(bare)
    print(f"[probe] foot_{tag}_toe_bare z[{ft_lo:.4f},{ft_hi:.4f}] "
          f"xy_components={nb} pts={mb} (对照值，解剖上脚趾连着脚掌，上限 1)")

print("[probe] done")