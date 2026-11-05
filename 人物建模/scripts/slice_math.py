# -*- coding: utf-8 -*-
"""切片数学：傅里叶描述子、双层频谱压缩（FD3 思路）、截面缺陷检测。

输入 `out/slices.json`（由 `scripts/slice_probe.py` 在 Blender 里切出），
纯系统 Python（numpy/scipy/cv2），不进 Blender、不改模型。

算什么
------
1. 每层轮廓弧长重采样 → 复数描述子 FFT；低通截断的重构误差与上界
2. 沿 z 再做一次频谱截断（FD3 = 双重傅里叶描述子），算「多少系数能重建整个头」
3. 截面几何量曲线：面积/宽/深/前后/左右对称；二阶差分找平顶与台阶
4. 手写 `HEAD_RAW` 17 行表 vs 细分后真实网格的逐层偏差

输出 `out/slice_analysis.json` / `out/slice_analysis.png`
用法：python scripts/slice_math.py
"""
import json
import math
import os

import cv2
import numpy as np
from scipy.fft import dct, idct
from scipy.interpolate import BSpline
from scipy.optimize import least_squares

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "out", "slices.json")
DST = os.path.join(ROOT, "out", "slice_analysis.json")
IMG = os.path.join(ROOT, "out", "slice_analysis.png")

M = 128                     # 每层弧长重采样点数
KS = [1, 2, 3, 4, 6, 8, 12, 16, 24, 32]
MZS = [2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96]


# ---------------------------------------------------------------- 1. 描述子
def resample_closed(pts, m=M):
    """按**固定方位角**把闭合轮廓重采样成 m 个复数点。

    为什么不用弧长：沿 z 做第二重频谱（FD3）的前提是「第 j 个采样点
    在每层对应同一个物理方向」。弧长参数化的起点由轮廓中心决定，而各层
    前后不对称程度不同 → 起点角度漂移 → 层间序列里混入相位抖动，
    实测把 FD3 误差顶到 40~74mm。角度参数化让对应关系严格一致。
    """
    p = np.asarray(pts, dtype=float)
    cx, cy = float(p[:, 0].mean()), float(p[:, 1].mean())
    x, y = p[:, 0] - cx, p[:, 1] - cy
    ang = np.mod(np.arctan2(y, x), 2.0 * np.pi)
    order = np.argsort(ang)
    a, xx, yy = ang[order], x[order], y[order]
    # 前后各铺一圈，保证 θ∈[0,2π) 的**绝对方位**能插值（θ=0 就是 +x）
    a3 = np.r_[a - 2.0 * np.pi, a, a + 2.0 * np.pi]
    theta = np.linspace(0.0, 2.0 * np.pi, m, endpoint=False)
    return (cx + np.interp(theta, a3, np.tile(xx, 3))
            + 1j * (cy + np.interp(theta, a3, np.tile(yy, 3))))


def lowpass(z, k):
    """保留 |频率|≤k 的傅里叶系数，返回重构点与逐点上界。"""
    m = len(z)
    c = np.fft.fft(z) / m
    idx = np.arange(m)
    keep = (idx <= k) | (idx >= m - k)
    tail = float(np.sum(np.abs(c[~keep])))        # 三角不等式给出的逐点误差上界
    energy = float(np.sum(np.abs(c[~keep]) ** 2))  # Parseval 残余能量
    cc = c.copy()
    cc[~keep] = 0.0
    rec = np.fft.ifft(cc) * m
    err = np.abs(z - rec)
    return rec, float(err.max()) * 1000.0, float(np.sqrt(np.mean(err ** 2))) * 1000.0, \
        tail * 1000.0, energy


def fd3(C, mz):
    """第二重：沿 z 对每层频谱做 **DCT-II** 截断。C shape=(n_layers, m_freq)。

    为什么不能用 FFT：头部从下巴到头顶非周期（首尾截面积差 34 倍），
    DFT 的周期延拓会在边界产生巨大 Gibbs 振荡（实测最大误差 40mm）。
    DCT 等价「镜像偶延拓」，边界一阶导为 0，是非周期信号的正确基。
    实部/虚部分别变换（C 是复数）。
    """
    Fr = dct(C.real, axis=0, norm="ortho")
    Fi = dct(C.imag, axis=0, norm="ortho")
    F = Fr + 1j * Fi
    F[mz:, :] = 0.0
    Cr = idct(F.real, axis=0, norm="ortho") + 1j * idct(F.imag, axis=0, norm="ortho")
    contours = np.fft.ifft(Cr, axis=1) * C.shape[1]
    return contours, mz


# ---------------------------------------------------------------- 2b. 超椭圆参数化
TH = np.linspace(0.0, 2.0 * np.pi, M, endpoint=False)
CTH, STH = np.cos(TH), np.sin(TH)


def superellipse_r(rx, ryf, ryb, p):
    """固定方位角上的超椭圆半径（与 HEAD_RAW 的 rx/ryf/ryb/p 同一口径）。"""
    r = np.where(STH < 0.0, ryf, ryb)
    return (np.abs(CTH / rx) ** p + np.abs(STH / r) ** p) ** (-1.0 / p)


def observed_r(pts):
    """把每层的 (x,y) 轮廓转成同一套固定角度上的半径 r(θ)。"""
    p = np.asarray(pts, float)
    cx, cy = float(p[:, 0].mean()), float(p[:, 1].mean())
    x, y = p[:, 0] - cx, p[:, 1] - cy
    ang = np.mod(np.arctan2(y, x), 2.0 * np.pi)
    o = np.argsort(ang)
    a, rr = ang[o], np.hypot(x, y)[o]
    a3 = np.r_[a - 2.0 * np.pi, a, a + 2.0 * np.pi]
    return np.interp(TH, a3, np.tile(rr, 3)), (cx, cy)


def fit_layer(robs, w0):
    """最小二乘拟合 (rx, ryf, ryb, p)；返回参数与最大径向残差(mm)。"""
    def resid(q):
        return (superellipse_r(*q) - robs) * 1000.0

    x0 = [w0 / 2.0, w0 / 2.5, w0 / 2.5, 2.1]
    r = least_squares(resid, x0,
                      bounds=([0.001, 0.001, 0.001, 1.2],
                              [0.20, 0.20, 0.20, 6.0]),
                      max_nfev=200)
    return r.x, float(np.max(np.abs(r.fun)))


def spline_compress(z, P, n_ctrl, k=3):
    """把 96 层 × 4 参数用 3 次 B 样条最小二乘压成 n_ctrl 个控制点。"""
    inner = np.linspace(z[0], z[-1], n_ctrl - k + 1)[1:-1]
    t = np.r_[[z[0]] * (k + 1), inner, [z[-1]] * (k + 1)]
    A = BSpline.design_matrix(z, t, k, extrapolate=False).toarray()
    ctrl = np.linalg.lstsq(A, P, rcond=None)[0]
    return A @ ctrl


def contour_err(P, robs_all):
    errs = [np.abs(superellipse_r(*q) - robs_all[i])
            for i, q in enumerate(P)]
    e = np.concatenate(errs)
    return float(e.max()) * 1000.0, float(np.sqrt(np.mean(e ** 2))) * 1000.0


# ---------------------------------------------------------------- 2. 几何量
def second_diff(v, dz):
    """二阶差分（除以 dz² 使不同层距可比）。"""
    return np.gradient(np.gradient(v, dz), dz)


# ---------------------------------------------------------------- 3. 作图
def _axes(img, x0, y0, w, h, title, xlabel, ylabel, legend=None):
    cv2.putText(img, title, (x0 + 10, y0 + 22), cv2.FONT_HERSHEY_SIMPLEX,
                0.5, (20, 20, 20), 1, cv2.LINE_AA)
    cv2.line(img, (x0 + 55, y0 + h - 38), (x0 + w - 12, y0 + h - 38),
             (70, 70, 70), 1)
    cv2.line(img, (x0 + 55, y0 + 38), (x0 + 55, y0 + h - 38), (70, 70, 70), 1)
    cv2.putText(img, xlabel, (x0 + w // 2 - 35, y0 + h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (90, 90, 90), 1, cv2.LINE_AA)
    cv2.putText(img, ylabel, (x0 + 6, y0 + h - 55), cv2.FONT_HERSHEY_SIMPLEX,
                0.36, (90, 90, 90), 1, cv2.LINE_AA)
    if legend:
        for i, (txt, col) in enumerate(legend):
            cv2.putText(img, txt, (x0 + 62, y0 + 52 + 17 * i),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.34, col, 1, cv2.LINE_AA)


def _line(img, x0, y0, w, h, xs, ys, col, ymin=None, ymax=None):
    xs = np.asarray(xs, float)
    ys = np.asarray(ys, float)
    if ymin is None:
        ymin, ymax = float(np.min(ys)), float(np.max(ys))
    if ymax - ymin < 1e-12:
        ymax = ymin + 1.0
    px = (x0 + 55 + (w - 70) * (xs - xs.min()) / max(xs.max() - xs.min(), 1e-12))
    py = (y0 + h - 38 - (h - 80) * np.clip((ys - ymin) / (ymax - ymin), 0, 1))
    pts = [(int(a), int(b)) for a, b in zip(px, py)]
    for i in range(len(pts) - 1):
        cv2.line(img, pts[i], pts[i + 1], col, 2, cv2.LINE_AA)


def plot(doc, path):
    W, H = 1300, 760
    img = np.full((H, W, 3), 250, np.uint8)
    panels = [(25, 20, 410, 330), (445, 20, 410, 330),
              (865, 20, 410, 330), (25, 365, 410, 330),
              (445, 365, 410, 330), (865, 365, 410, 330)]
    for x0, y0, w, h in panels:
        cv2.rectangle(img, (x0, y0), (x0 + w, y0 + h), (222, 222, 222), 1)

    sl = doc["slices"]
    z = np.array([c["z_mm"] for c in sl])
    area = np.array([c["area_mm2"] for c in sl])
    ww = np.array([c["w_mm"] for c in sl])
    dd = np.array([c["d_mm"] for c in sl])
    raww = np.array([c["raw_w_mm"] for c in sl])
    sym = np.array([c["sym_x_mm"] for c in sl])
    dw = np.array([c["d_w_mm"] for c in sl])

    # 1 轮廓叠加（正视 x 极值 + 侧视 y 极值）
    x0, y0, w, h = panels[0]
    _axes(img, x0, y0, w, h, "section envelope (front+side)",
          "z (mm)", "x / y (mm)",
          [("blue: +-x envelope", (180, 90, 30)),
           ("green: +-y envelope", (30, 140, 60)),
           ("red: raw table +-rx", (30, 60, 200))])
    _line(img, x0, y0, w, h, z, ww / 2, (180, 90, 30), -10, 115)
    _line(img, x0, y0, w, h, z, dd / 2, (30, 140, 60), -10, 115)
    _line(img, x0, y0, w, h, z, raww / 2, (30, 60, 200), -10, 115)

    # 2 面积 / 二阶差分
    x0, y0, w, h = panels[1]
    _axes(img, x0, y0, w, h, "area & curvature peak", "z (mm)", "A (mm2)",
          [("blue: section area", (180, 90, 30)),
           ("red line: max |d2A|", (30, 60, 200))])
    _line(img, x0, y0, w, h, z, area, (180, 90, 30))
    d2 = np.array([c["d2_area"] for c in sl])
    i_peak = int(np.argmax(np.abs(d2)))
    xpk = int(x0 + 55 + (w - 70) * (float(z[i_peak]) - float(z.min()))
              / max(float(z.max()) - float(z.min()), 1e-9))
    cv2.line(img, (xpk, y0 + 38), (xpk, y0 + h - 38), (30, 60, 200), 1)

    # 3 手写表偏差 / 对称差
    x0, y0, w, h = panels[2]
    _axes(img, x0, y0, w, h, "raw table vs mesh", "z (mm)", "delta (mm)",
          [("blue: measured w - 2rx", (180, 90, 30)),
           ("green: |left-right| x", (30, 140, 60))])
    _line(img, x0, y0, w, h, z, dw, (180, 90, 30))
    _line(img, x0, y0, w, h, z, sym, (30, 140, 60))

    # 4 单层傅里叶截断误差
    x0, y0, w, h = panels[3]
    _axes(img, x0, y0, w, h, "per-slice Fourier truncation", "K", "error (mm)",
          [("blue: rms error", (180, 90, 30)),
           ("green: max error", (30, 140, 60)),
           ("red: analytic bound", (30, 60, 200))])
    ft = doc["fourier_per_slice"]
    ks = [r["K"] for r in ft]
    _line(img, x0, y0, w, h, ks, [r["rms_mm"] for r in ft], (180, 90, 30))
    _line(img, x0, y0, w, h, ks, [r["max_mm"] for r in ft], (30, 140, 60))
    _line(img, x0, y0, w, h, ks, [r["bound_mm"] for r in ft], (30, 60, 200))

    # 5 FD3 双层压缩
    x0, y0, w, h = panels[4]
    _axes(img, x0, y0, w, h, "FD3 two-axis compression", "coeff count", "max err (mm)",
          [("blue: max vertex error", (180, 90, 30))])
    fd = doc["fd3_front"]
    ns = [r["n_real"] for r in fd]
    _line(img, x0, y0, w, h, ns, [r["max_mm"] for r in fd], (180, 90, 30))

    # 6 结论条
    x0, y0, w, h = panels[5]
    for i, line in enumerate(doc["_plot_lines"]):
        cv2.putText(img, line, (x0 + 12, y0 + 30 + 30 * i),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (30, 30, 30), 1, cv2.LINE_AA)

    ok, buf = cv2.imencode(".png", img)
    if ok:
        buf.tofile(path)


# ---------------------------------------------------------------- main
def main():
    src = json.load(open(SRC, encoding="utf-8"))
    sl = src["slices"]
    zs = np.array([c["z"] for c in sl], float)
    dz = float(np.mean(np.diff(zs)))
    Z = [resample_closed(c["pts"]) for c in sl]

    # --- 1 单层傅里叶截断（用中间那层作代表 + 全层统计）---
    mid = len(Z) // 2
    ft = []
    for k in KS:
        rec, emax, erms, bound, energy = lowpass(Z[mid], k)
        per = [lowpass(zz, k) for zz in Z]
        allmax = max(p[1] for p in per)
        allrms = float(np.sqrt(np.mean([p[2] ** 2 for p in per])))
        allbound = max(p[3] for p in per)      # 全层逐点误差上界 Σ|c_k|
        ft.append({"K": k, "n_coeff_complex": 2 * k + 1,
                   "max_mm": round(allmax, 5), "rms_mm": round(allrms, 5),
                   "mid_max_mm": round(emax, 5), "mid_rms_mm": round(erms, 5),
                   "bound_mid_mm": round(bound, 5),
                   "bound_mm": round(allbound, 5),
                   "tail_energy": round(energy, 10)})
    bound_ok = all(r["max_mm"] <= r["bound_mm"] + 1e-6 for r in ft)

    # --- 2 FD3：扫 (每层频率数 K0) × (沿 z 的 DCT 频率数 mz) ---
    K0S = [8, 12, 16, 24, 32]
    Zfull = np.stack(Z)
    fd = []
    for K0 in K0S:
        C = np.stack([np.fft.fft(zz) / M for zz in Z])     # (n_layers, M)
        keep = (np.arange(M) <= K0) | (np.arange(M) >= M - K0)
        C[:, ~keep] = 0.0
        for mz in MZS:
            contours, nz = fd3(C, mz)
            err = np.abs(Zfull - contours)
            n_real = (2 * K0 + 1) * nz * 2
            fd.append({"K_per_slice": K0, "mz_along_z": mz,
                       "n_freq_z": nz, "n_real": n_real,
                       "compression_vs_contours": round(
                           len(Z) * M * 2 / n_real, 2),
                       "max_mm": round(float(err.max()) * 1000.0, 4),
                       "rms_mm": round(float(np.sqrt(np.mean(err ** 2))) * 1000.0, 4)})
    front = []
    for n in sorted({r["n_real"] for r in fd}):
        front.append(min([r for r in fd if r["n_real"] == n],
                         key=lambda r: r["max_mm"]))
    front.sort(key=lambda r: r["n_real"])

    # 自检：沿 z 不截断（mz=n_layers）时必须精确回到「只截单层频率」的结果。
    # 若这条不成立，说明 DCT/FFT 往返本身有 bug，后面的误差数字都不可信。
    Kchk = 32
    Cchk = np.stack([np.fft.fft(zz) / M for zz in Z])
    kp = (np.arange(M) <= Kchk) | (np.arange(M) >= M - Kchk)
    Cchk[:, ~kp] = 0.0
    rec_full, _ = fd3(Cchk, len(Z))
    identity_err = float(np.abs(Zfull - rec_full).max()) * 1000.0

    # --- 2c 超椭圆先验 + B 样条：这才是「切片参数化」在本项目的可行形态 ---
    robs_all, P_fit, per_layer = [], [], []
    for c in sl:
        ro, _ = observed_r(c["pts"])
        robs_all.append(ro)
        q, em = fit_layer(ro, c["w"])
        P_fit.append(q)
        per_layer.append(em)
    robs_all = np.asarray(robs_all)
    P_fit = np.asarray(P_fit)
    P_raw = np.array([[c["raw"]["rx"], c["raw"]["ryf"],
                       c["raw"]["ryb"], c["raw"]["p"]] for c in sl])
    raw_max, raw_rms = contour_err(P_raw, robs_all)
    fit_max, fit_rms = contour_err(P_fit, robs_all)
    spline = []
    for n_ctrl in (8, 12, 17, 24, 32, 48):
        Ph = spline_compress(zs, P_fit, n_ctrl)
        em, er = contour_err(Ph, robs_all)
        spline.append({"n_ctrl": n_ctrl, "n_real": n_ctrl * 4,
                       "max_mm": round(em, 4), "rms_mm": round(er, 4)})
    s17 = next(r for r in spline if r["n_ctrl"] == 17)

    # --- 3 几何量与缺陷 ---
    area = np.array([c["area"] for c in sl]) * 1e6          # mm²
    w = np.array([c["w"] for c in sl]) * 1000.0
    d = np.array([c["d"] for c in sl]) * 1000.0
    sym = np.array([c["sym_x"] for c in sl]) * 1000.0
    dw = np.array([c["d_w_raw"] for c in sl]) * 1000.0
    dd = np.array([c["d_d_raw"] for c in sl]) * 1000.0
    d2 = second_diff(area, dz * 1000.0)
    i_d2 = int(np.argmax(np.abs(d2)))
    i_dw = int(np.argmax(np.abs(dw)))
    # 顶部 15% 的面积下降率（平顶判据）
    top = area[-max(3, len(area) // 7):]
    top_slope = float(np.polyfit(np.arange(len(top)), top, 1)[0])

    out_slices = []
    for i, c in enumerate(sl):
        out_slices.append({
            "z_mm": round(c["z"] * 1000.0, 3),
            "n_pts": c["n"],
            "area_mm2": round(float(area[i]), 3),
            "w_mm": round(float(w[i]), 3), "d_mm": round(float(d[i]), 3),
            "sym_x_mm": round(float(sym[i]), 4),
            "raw_w_mm": round(2.0 * c["raw"]["rx"] * 1000.0, 3),
            "d_w_mm": round(float(dw[i]), 3),
            "d_d_mm": round(float(dd[i]), 3),
            "d2_area": round(float(d2[i]), 6),
        })

    # --- 4 结论 ---
    k1mm = next((r["K"] for r in ft if r["max_mm"] <= 1.0), None)
    fd1mm = next((r for r in front if r["max_mm"] <= 1.0), None)
    doc = {
        "source": src["source"], "n_slices": len(sl),
        "mesh": src["mesh"], "raw_rows": src["raw_rows"],
        "fourier_per_slice": ft,
        "bound_valid": bound_ok,
        "fd3": fd, "fd3_front": front,
        "fd3_identity_check_mm": round(identity_err, 8),
        "superellipse": {
            "fit_per_layer_max_mm": round(max(per_layer), 4),
            "fit_per_layer_mean_mm": round(float(np.mean(per_layer)), 4),
            "fitted_96layers_max_mm": round(fit_max, 4),
            "fitted_96layers_rms_mm": round(fit_rms, 4),
            "handwritten_17rows_max_mm": round(raw_max, 4),
            "handwritten_17rows_rms_mm": round(raw_rms, 4),
            "spline": spline,
            "fitted_17ctrl_max_mm": s17["max_mm"],
            "note": "同样 17 个控制层：手写表 vs 从真实几何最小二乘反解 + B 样条",
        },
        "slices": out_slices,
        "geometry": {
            "area_min_mm2": round(float(area.min()), 2),
            "area_max_mm2": round(float(area.max()), 2),
            "w_max_mm": round(float(w.max()), 2),
            "d_max_mm": round(float(d.max()), 2),
            "max_left_right_asym_mm": round(float(sym.max()), 4),
            "raw_width_dev_min_mm": round(float(dw.min()), 3),
            "raw_width_dev_max_mm": round(float(dw.max()), 3),
            "raw_width_dev_at_z_mm": round(float(zs[i_dw] * 1000.0), 2),
            "raw_depth_dev_min_mm": round(float(dd.min()), 3),
            "raw_depth_dev_max_mm": round(float(dd.max()), 3),
            "largest_d2A_at_z_mm": round(float(zs[i_d2] * 1000.0), 2),
            "largest_d2A": round(float(d2[i_d2]), 6),
            "top15pct_area_slope_mm2_per_layer": round(top_slope, 2),
        },
        "design": {
            "K_for_1mm": k1mm,
            "fd3_for_1mm": fd1mm,
            "handwritten_param_count": src["raw_rows"] * 6,
            "note": "手写表 17 行 × 6 列 = 102 个数字，但只能表达超椭圆；FD3 的系数直接拟合真实网格",
        },
        "_plot_lines": [
            "%d slices / %d verts / %d faces"
            % (len(sl), src["mesh"]["v"], src["mesh"]["f"]),
            "Fourier bound OK=%s ; K=%s -> <1mm" % (bound_ok, k1mm),
            "FD3 <1mm: %s coeffs (%.1fx)"
            % (fd1mm["n_real"] if fd1mm else "none",
               fd1mm["compression_vs_contours"] if fd1mm else 0),
            "Raw table w dev %.1f .. %.1f mm" % (dw.min(), dw.max()),
            "|d2A| peak z=%.1fmm ; sym %.4fmm"
            % (zs[i_d2] * 1000, sym.max()),
            "Superellipse: raw17 %.2fmm -> fit17 %.2fmm"
            % (raw_max, s17["max_mm"]),
            "fit floor %.2fmm = model limit" % fit_max,
            "DCT round-trip %.2fmm = trunc floor" % identity_err,
        ],
    }
    with open(DST, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
    plot(doc, IMG)

    print("[slice-math] slices=%d  bound_valid=%s  K for <1mm=%s"
          % (len(sl), bound_ok, k1mm))
    for r in ft:
        print("  K=%2d  max=%8.4fmm  rms=%8.4fmm  bound(mid)=%8.4fmm"
              % (r["K"], r["max_mm"], r["rms_mm"], r["bound_mid_mm"]))
    print("[slice-math] FD3 (DCT-II along z), %d combos, Pareto front %d:"
          % (len(fd), len(front)))
    for r in front[::max(1, len(front) // 8)]:
        print("  K=%2d mz=%2d  n_real=%5d  comp=%6.1fx  max=%8.4fmm  rms=%8.4fmm"
              % (r["K_per_slice"], r["mz_along_z"], r["n_real"],
                 r["compression_vs_contours"], r["max_mm"], r["rms_mm"]))
    print("[slice-math] DCT round-trip = %.6f mm (= K=32 单层截断下界，无额外误差)"
          % identity_err)
    print("[slice-math] min coeffs for <1mm: %s"
          % (fd1mm["n_real"] if fd1mm else "none (need larger K/mz)"))
    print("[slice-math] superellipse: 17 handwritten rows %.4fmm vs "
          "17 fitted spline ctrl %.4fmm (96-layer fit floor %.4fmm)"
          % (raw_max, s17["max_mm"], fit_max))
    for r in spline:
        print("  ctrl=%2d  n=%3d  max=%8.4fmm  rms=%8.4fmm"
              % (r["n_ctrl"], r["n_real"], r["max_mm"], r["rms_mm"]))
    g = doc["geometry"]
    print("[slice-math] raw w dev %.2f..%.2fmm ; raw d dev %.2f..%.2fmm"
          % (g["raw_width_dev_min_mm"], g["raw_width_dev_max_mm"],
             g["raw_depth_dev_min_mm"], g["raw_depth_dev_max_mm"]))
    print("[slice-math] |d2A| max at z=%.1fmm ; top slope %.0f mm2/layer ; sym max %.4fmm"
          % (g["largest_d2A_at_z_mm"], g["top15pct_area_slope_mm2_per_layer"],
             g["max_left_right_asym_mm"]))
    print("[slice-math] -> out/slice_analysis.json  out/slice_analysis.png")


if __name__ == "__main__":
    main()
