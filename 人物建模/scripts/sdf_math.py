# -*- coding: utf-8 -*-
"""SDF 融合体的解析推导 + 数值验证（纯 numpy/cv2，不进 Blender、不改模型）。

回答 BOSS「没有用高等数学算算吗」：上一轮只查了节点 API，这一轮真算。

算什么
------
1. smin 过渡带的解析式、梯度、Hessian；证明 |∇d| ≠ 1 并算出 Offset 的位移放大倍数
2. 两圆相交 2mm（耳轮尺度），极坐标解零水平集 r(θ)，算面积膨胀/颈部曲率半径/
   Hausdorff 偏移，扫描 k
3. marching cubes 的位置误差上界 → 反解「保住 2.8mm 耳轮」的最大体素 h
4. n 次显式 Laplacian 迭代的等效扩散半径 L = h√n，用 2D 场数值验证 √n 标度
5. 满网格 vs 窄带（Band Width）两种内存模型

输出：out/sdf_math.json、out/sdf_math.png
用法：python scripts/sdf_math.py
"""
import json
import math
import os

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")

# ---- 几何尺度（m）：耳轮 2.8mm、耳甲 4.2mm；两圆模拟「部件插入 2mm」 ----
R = 0.020             # 圆半径 20mm
C = 0.018             # 圆心 ±18mm → 相交 2mm
RIM = 0.0028          # 耳轮最细特征 2.8mm
TOL = 0.05            # 允许误差 = 特征的 5%


# ---------------------------------------------------------------- 1. 解析
def sd_circle(x, y, cx):
    return np.hypot(x - cx, y) - R


def smin_poly(a, b, k):
    """Inigo Quilez 多项式 smin：h=max(k-|a-b|,0)/k；d=min(a,b)-h²k/4。"""
    if k <= 0:
        return np.minimum(a, b)
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def smin_closed(a, b, k):
    """过渡带 |a-b|<k 内的**闭式等价式**：(a+b)/2 - k/4 - (a-b)²/(4k)。

    外面退回 min(a,b)。这个形式是后面求梯度/Hessian 的出发点。
    """
    if k <= 0:
        return np.minimum(a, b)
    delta = a - b
    inner = 0.5 * (a + b) - 0.25 * k - delta * delta / (4.0 * k)
    return np.where(np.abs(delta) < k, inner, np.minimum(a, b))


def field(x, y, k):
    return smin_closed(sd_circle(x, y, -C), sd_circle(x, y, C), k)


def grad_field(x, y, k, eps=1e-7):
    """中心差分 ∇d，用于数值验证 |∇d|≠1。"""
    dx = (field(x + eps, y, k) - field(x - eps, y, k)) / (2 * eps)
    dy = (field(x, y + eps, k) - field(x, y - eps, k)) / (2 * eps)
    return dx, dy


def check_closed_form():
    """闭式等价式与原始 smin 必须逐点一致（浮点误差 <1e-12）。"""
    rng = np.random.default_rng(7)
    a, b = rng.uniform(-0.02, 0.02, 2000), rng.uniform(-0.02, 0.02, 2000)
    worst = 0.0
    for k in (0.0005, 0.002, 0.008):
        worst = max(worst, float(np.max(np.abs(smin_poly(a, b, k)
                                               - smin_closed(a, b, k)))))
    return worst


# ---------------------------------------------------------------- 2. 零水平集
N_TH = 2048
TH = np.linspace(0.0, 2.0 * math.pi, N_TH, endpoint=False)
CT, ST = np.cos(TH), np.sin(TH)


def radius_curve(k):
    """沿每条射线二分求 d(r,θ)=0，得到 r(θ)。两圆并集关于原点星形，根唯一。"""
    lo = np.zeros_like(TH)
    hi = np.full_like(TH, 0.060)
    for _ in range(64):
        mid = 0.5 * (lo + hi)
        d = field(mid * CT, mid * ST, k)
        inside = d < 0.0
        lo = np.where(inside, mid, lo)
        hi = np.where(inside, hi, mid)
    return 0.5 * (lo + hi)


def curve_stats(k):
    """面积、颈部(θ=π/2)曲率半径、沿射线最大膨胀。"""
    r = radius_curve(k)
    dth = 2.0 * math.pi / N_TH
    area = 0.5 * float(np.sum(r * r) * dth)
    rp = np.gradient(r, dth)                 # dr/dθ
    rpp = np.gradient(rp, dth)               # d²r/dθ²
    num = r * r + 2.0 * rp * rp - r * rpp
    den = (r * r + rp * rp) ** 1.5
    kappa = num / den                       # 极坐标曲率
    rho = np.abs(1.0 / kappa)               # 曲率半径
    i_neck = int(round(N_TH / 4.0))         # θ=π/2
    return {
        "k_mm": round(k * 1000.0, 4),
        "area_mm2": round(area * 1e6, 4),
        "neck_r_mm": round(float(r[i_neck]) * 1000.0, 4),
        "neck_rho_mm": round(float(rho[i_neck]) * 1000.0, 4),
        "min_rho_mm": round(float(np.min(rho)) * 1000.0, 4),
        "_r": r,
    }


# ---------------------------------------------------------------- 3. 误差界
def voxel_bounds(h, rho_mm):
    """两种位置误差上界（mm）。"""
    e_sample = math.sqrt(3.0) / 2.0 * h * 1000.0     # 体素对角线一半
    e_interp = (h * 1000.0) ** 2 / (8.0 * rho_mm)    # 线性插值弦高 h²/(8ρ)
    return e_sample, e_interp


def memory_models(h):
    """满网格 vs 窄带（Band Width=3，两侧各 3 层）float32 字节数。"""
    nx, ny, nz = 0.060 / h, 0.040 / h, 0.060 / h
    full = nx * ny * nz * 4.0
    surf_cells = 5000e-6 / (h * h)          # 表面积 ≈5000 mm² = 5e-3 m²
    narrow = surf_cells * 6.0 * 4.0        # 带宽 2×3 层
    return {"h_mm": round(h * 1000.0, 4),
            "full_MB": round(full / 1048576.0, 2),
            "narrow_band_MB": round(narrow / 1048576.0, 2),
            "grid": [int(nx), int(ny), int(nz)]}


# ---------------------------------------------------------------- 4. 扩散标度
def laplacian_scale(h=1.0, size=192, lam=0.24):
    """2D 显式 Laplacian 迭代：验证平滑半径 ∝ √n。

    场 = 两个方形 SDF 的硬并集，尖角在 (0,0) 附近。每次迭代
    d ← d + λ·(四邻域和 − 4d)，λ<1/4 稳定。量零水平集在角部相对原场的
    最大位移，拟合 log(位移) vs log(n) 的斜率，理论值 0.5。
    """
    yy, xx = np.mgrid[0:size, 0:size].astype(float)
    d1 = np.maximum(np.abs(xx - size * 0.40) - size * 0.13,
                    np.abs(yy - size * 0.50) - size * 0.13)
    d2 = np.maximum(np.abs(xx - size * 0.55) - size * 0.10,
                    np.abs(yy - size * 0.50) - size * 0.10)
    d0 = np.minimum(d1, d2)
    d = d0.copy()
    ns, disp = [], []
    for n in range(1, 65):
        lap = (np.roll(d, 1, 0) + np.roll(d, -1, 0)
               + np.roll(d, 1, 1) + np.roll(d, -1, 1) - 4.0 * d)
        d = d + lam * lap
        if n in (1, 2, 4, 8, 16, 32, 64):
            # 角部区域（两方形交界）零水平集相对初始的最大位移
            roi = (xx > size * 0.44) & (xx < size * 0.52) & \
                  (yy > size * 0.45) & (yy < size * 0.55)
            shift = np.abs(d - d0)[roi]
            ns.append(n)
            disp.append(float(np.percentile(shift, 95)))
    slope = float(np.polyfit(np.log(ns), np.log(np.maximum(disp, 1e-9)), 1)[0])
    return {"n": ns, "disp_px": [round(v, 4) for v in disp],
            "fit_slope": round(slope, 4),
            "theory_slope": 0.5,
            "lam": lam,
            "note": "2D 稳定上界 λ≤1/4；L=h√(6Dt) 形式下 2D 为 h√(4λn)，本例 λ=0.24 → L≈0.98h√n"}


# ---------------------------------------------------------------- 作图
def plot(rows_k, rows_h, diff, path, design):
    W, H = 1280, 700
    img = np.full((H, W, 3), 250, np.uint8)
    panels = [(30, 30, 400, 380), (440, 30, 400, 380), (850, 30, 400, 380)]
    for x0, y0, w, h in panels:
        cv2.rectangle(img, (x0, y0), (x0 + w, y0 + h), (225, 225, 225), 1)

    def axes(x0, y0, w, h, title, xlabel, ylabel):
        cv2.putText(img, title, (x0 + 10, y0 + 22), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (20, 20, 20), 1, cv2.LINE_AA)
        cv2.line(img, (x0 + 55, y0 + h - 40), (x0 + w - 15, y0 + h - 40),
                 (60, 60, 60), 1)
        cv2.line(img, (x0 + 55, y0 + 40), (x0 + 55, y0 + h - 40),
                 (60, 60, 60), 1)
        cv2.putText(img, xlabel, (x0 + w // 2 - 40, y0 + h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (80, 80, 80), 1, cv2.LINE_AA)
        cv2.putText(img, ylabel, (x0 + 6, y0 + h - 58), cv2.FONT_HERSHEY_SIMPLEX,
                    0.38, (80, 80, 80), 1, cv2.LINE_AA)

    def poly(x0, y0, w, h, xs, ys, color, xmax, ymax):
        pts = [(int(x0 + 55 + (w - 70) * x / xmax),
                int(y0 + h - 40 - (h - 85) * min(y / ymax, 1.0)))
               for x, y in zip(xs, ys)]
        for i in range(len(pts) - 1):
            cv2.line(img, pts[i], pts[i + 1], color, 2, cv2.LINE_AA)
        return pts

    # 面板 1：k vs 颈部曲率半径 / 面积膨胀
    x0, y0, w, h = panels[0]
    axes(x0, y0, w, h, "k vs neck curvature radius", "k (mm)", "rho (mm) / dA (%)")
    ks = [r["k_mm"] for r in rows_k]
    rhos = [r["neck_rho_mm"] for r in rows_k]
    a0 = rows_k[0]["area_mm2"]
    das = [100.0 * (r["area_mm2"] - a0) / a0 for r in rows_k]
    poly(x0, y0, w, h, ks, rhos, (30, 90, 200), 8.0, max(rhos) * 1.2)
    poly(x0, y0, w, h, ks, das, (200, 60, 30), 8.0, max(das) * 1.2 or 1.0)
    cv2.putText(img, "blue: neck rho (mm)", (x0 + 60, y0 + 55),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (30, 90, 200), 1, cv2.LINE_AA)
    cv2.putText(img, "red: area gain (%)", (x0 + 60, y0 + 75),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 60, 30), 1, cv2.LINE_AA)
    cv2.putText(img, "each curve normalized separately", (x0 + 60, y0 + 95),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (110, 110, 110), 1, cv2.LINE_AA)

    # 面板 2：h vs 误差界 + 容差线
    x0, y0, w, h = panels[1]
    axes(x0, y0, w, h, "voxel size vs position error", "h (mm)", "error (mm)")
    hs = [r["h_mm"] for r in rows_h]
    e1 = [r["e_sample_mm"] for r in rows_h]
    e2 = [r["e_interp_mm"] for r in rows_h]
    poly(x0, y0, w, h, hs, e1, (30, 90, 200), 1.0, max(e1) * 1.1)
    poly(x0, y0, w, h, hs, e2, (30, 160, 80), 1.0, max(e1) * 1.1)
    tol_mm = TOL * RIM * 1000.0
    ytol = int(y0 + h - 40 - (h - 85) * tol_mm / (max(e1) * 1.1))
    cv2.line(img, (x0 + 55, ytol), (x0 + w - 15, ytol), (0, 0, 220), 1, cv2.LINE_AA)
    cv2.putText(img, "red: 5% of 2.8mm rim = 0.14mm", (x0 + 60, y0 + 55),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 220), 1, cv2.LINE_AA)
    cv2.putText(img, "blue: sqrt(3)/2*h  green: h^2/(8*rho)", (x0 + 60, y0 + 75),
                cv2.FONT_HERSHEY_SIMPLEX, 0.37, (60, 60, 60), 1, cv2.LINE_AA)

    # 面板 3：n vs 扩散位移，验证 √n
    x0, y0, w, h = panels[2]
    axes(x0, y0, w, h, "Laplacian rounds vs sqrt(n)", "n", "disp (px)")
    ns, ds = diff["n"], diff["disp_px"]
    poly(x0, y0, w, h, ns, ds, (30, 90, 200), max(ns), max(ds) * 1.1 or 1.0)
    cv2.putText(img, "fit slope = %.3f (theory 0.5)" % diff["fit_slope"],
                (x0 + 60, y0 + 55), cv2.FONT_HERSHEY_SIMPLEX,
                0.42, (20, 20, 20), 1, cv2.LINE_AA)

    # 下方结论条
    y = 450
    for line in (
        "Analytic: d = (a+b)/2 - k/4 - (a-b)^2/(4k)   for |a-b|<k   (max err 7e-18)",
        "Gradient at a=b: grad d = (ga+gb)/2 -> |grad d| = |cos(theta/2)| = 0.436 < 1",
        "So Offset(-k/4) inflates geometry by (k/4)/|grad d| = 2.29x, not k/4",
        "rho(k) = 0.02763k^2 + 0.24839k + 0.014 mm ; rho=2.8mm needs k=%.2fmm (inflates %.2fmm)"
        % (design["k_for_rho_eq_rim_mm"], design["k_for_rho_eq_rim_mm"] / 4.0),
        "Error: e <= sqrt(3)/2*h ; 5% of 2.8mm rim -> h <= 0.162mm (full 130MB, narrow 4.4MB)",
        "n Laplacian rounds: L ~ h*sqrt(n) ; k=2mm at h=0.162mm needs n~153 (fit slope 0.455)",
    ):
        cv2.putText(img, line, (40, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (30, 30, 30), 1, cv2.LINE_AA)
        y += 34
    ok, buf = cv2.imencode(".png", img)
    if ok:
        buf.tofile(path)


# ---------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    closed_err = check_closed_form()

    # 1. |∇d| 与 Offset 失真（颈部 θ=π/2，k=0 处的解析值）
    y_neck = math.sqrt(R * R - C * C)
    gnorm_analytic = y_neck / R                  # = |∇d| at a=b, k→0
    gx, gy = grad_field(0.0, y_neck, 0.002)
    gnorm_numeric = math.hypot(gx, gy)
    # k=4mm 时颈部 r 的精确解 vs 一阶近似
    k_test = 0.004
    r0 = math.sqrt(R * R - C * C)
    r_exact = math.sqrt((R + k_test / 4.0) ** 2 - C * C)
    r_linear = r0 + (k_test / 4.0) / gnorm_analytic

    # 2. k 扫描
    k_list = [0.0, 0.0005, 0.001, 0.002, 0.004, 0.006, 0.008]
    rows_k = []
    for k in k_list:
        s = curve_stats(k)
        s.pop("_r", None)
        rows_k.append(s)
    # k=0 是硬并集的尖角（理论曲率半径 0，数值上只剩离散残差 0.013mm）。
    # 它不能当「要保住的特征尺寸」—— 那正是 smin 要消掉的东西。
    # 插值误差界用**设计融合带** k=2mm 的颈部曲率半径。
    rho_spike = rows_k[0]["neck_rho_mm"]
    rho_design = [r["neck_rho_mm"] for r in rows_k if r["k_mm"] == 2.0][0]
    kk = np.array([r["k_mm"] for r in rows_k])
    rr = np.array([r["neck_rho_mm"] for r in rows_k])
    coef = np.polyfit(kk, rr, 2)                # ρ(k) 二次拟合
    roots = np.roots([coef[0], coef[1], coef[2] - RIM * 1000.0])
    k_for_rim = float(max(x.real for x in roots if abs(x.imag) < 1e-9 and x.real > 0)) \
        if any(abs(x.imag) < 1e-9 and x.real > 0 for x in roots) else None

    # 3. 体素误差界 + 内存
    h_list = [0.0001, 0.00016, 0.00025, 0.0004, 0.0005, 0.0008, 0.001]
    rows_h = []
    for h in h_list:
        e1, e2 = voxel_bounds(h, rho_design)
        mem = memory_models(h)
        rows_h.append({"h_mm": mem["h_mm"], "e_sample_mm": round(e1, 4),
                       "e_interp_mm": round(e2, 4),
                       "tol_mm": round(TOL * RIM * 1000.0, 4),
                       "full_MB": mem["full_MB"],
                       "narrow_band_MB": mem["narrow_band_MB"],
                       "grid": mem["grid"]})
    tol_mm = TOL * RIM * 1000.0
    h_max_sample = tol_mm * 2.0 / math.sqrt(3.0) / 1000.0
    h_max_interp = math.sqrt(8.0 * rho_design * tol_mm) / 1000.0
    h_need = min(h_max_sample, h_max_interp)
    mem_need = memory_models(h_need)
    n_needed = (0.002 / h_need) ** 2           # k=2mm 融合带所需 Laplacian 轮数

    diff = laplacian_scale()

    doc = {
        "scale": {"R_mm": 20.0, "C_mm": 18.0, "overlap_mm": 2.0,
                  "rim_mm": RIM * 1000.0, "tol_frac": TOL},
        "analytic": {
            "transition_formula": "d=(a+b)/2-k/4-(a-b)^2/(4k) for |a-b|<k, else min(a,b)",
            "closed_form_max_error": closed_err,
            "gradient_at_equal": "|grad d|=|grad a+grad b|/2=|cos(theta/2)|",
            "hessian_at_equal": "H=(Ha+Hb)/2-(ga-gb)(ga-gb)^T/(2k)  (rank-1 negative term)",
            "neck_y_mm": round(y_neck * 1000.0, 4),
            "grad_norm_analytic": round(gnorm_analytic, 6),
            "grad_norm_numeric_k2mm": round(gnorm_numeric, 6),
            "offset_inflation_factor": round(1.0 / gnorm_analytic, 4),
            "k4mm_neck_r_exact_mm": round(r_exact * 1000.0, 4),
            "k4mm_neck_r_linear_mm": round(r_linear * 1000.0, 4),
            "k4mm_linear_error_pct": round(100.0 * (r_linear - r_exact) / (r_exact - r0), 3),
        },
        "k_scan": rows_k,
        "curvature_design": {
            "hard_union_spike_rho_mm": rho_spike,
            "rho_at_k2mm_mm": rho_design,
            "rho_of_k_poly2": [round(float(v), 6) for v in coef],
            "k_for_rho_eq_rim_mm": round(k_for_rim, 3) if k_for_rim else None,
            "note": "ρ(k) 超线性；要让融合带圆到 2.8mm 耳轮尺度，k 需约 %.1fmm，但其整体膨胀 k/4 已达 %.2fmm" % (
                k_for_rim or 0, (k_for_rim or 0) / 4.0),
        },
        "voxel": {
            "rows": rows_h, "rho_used_mm": rho_design,
            "h_max_sample_mm": round(h_max_sample * 1000.0, 4),
            "h_max_interp_mm": round(h_max_interp * 1000.0, 4),
            "h_required_mm": round(h_need * 1000.0, 4),
            "memory_at_required": mem_need,
            "laplacian_rounds_for_k2mm": round(n_needed, 1),
            "note": "n_full 是满网格估算；Blender 的 Band Width 暗示稀疏窄带存储，峰值内存必须实测",
        },
        "laplacian": diff,
    }
    with open(os.path.join(OUT, "sdf_math.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
    plot(rows_k, rows_h, diff, os.path.join(OUT, "sdf_math.png"),
         doc["curvature_design"])

    print("[sdf] closed-form max error = %.3e" % closed_err)
    print("[sdf] |grad d| analytic %.4f / numeric %.4f  -> offset inflation %.3fx"
          % (gnorm_analytic, gnorm_numeric, 1.0 / gnorm_analytic))
    print("[sdf] k=4mm neck r: exact %.4fmm  linear %.4fmm"
          % (r_exact * 1000, r_linear * 1000))
    for r in rows_k:
        print("  k=%5.2fmm  area=%9.2fmm2  neck_r=%7.4f  neck_rho=%8.3f  min_rho=%8.3f"
              % (r["k_mm"], r["area_mm2"], r["neck_r_mm"],
                 r["neck_rho_mm"], r["min_rho_mm"]))
    print("[sdf] hard-union spike rho = %.4fmm ; design rho(k=2mm) = %.3fmm ; tolerance %.4fmm"
          % (rho_spike, rho_design, tol_mm))
    print("[sdf] rho(k) poly2 = %s -> k for rho=2.8mm is %.2fmm (inflation k/4=%.2fmm)"
          % ([round(float(v), 5) for v in coef], k_for_rim or -1,
             (k_for_rim or 0) / 4.0))
    print("[sdf] h_max: sample %.4fmm / interp %.4fmm -> need %.4fmm"
          % (h_max_sample * 1000, h_max_interp * 1000, h_need * 1000))
    print("[sdf] memory at h_need: full %.1fMB / narrow %.2fMB"
          % (mem_need["full_MB"], mem_need["narrow_band_MB"]))
    print("[sdf] Laplacian rounds for k=2mm at h_need: %.0f" % n_needed)
    print("[sdf] fit slope %.4f (theory 0.5)" % diff["fit_slope"])
    print("[sdf] -> out/sdf_math.json  out/sdf_math.png")


if __name__ == "__main__":
    main()
