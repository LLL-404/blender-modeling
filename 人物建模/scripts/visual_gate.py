# -*- coding: utf-8 -*-
"""视觉闸门：把「像不像参考图」变成能自动判、能拦下糊弄产出的一步。

为什么有这支脚本（2026-11-04 根因复盘）
--------------------------------------
到 2026-11-04 为止，工程里有 14 条外观 spec、6 个绑定探针、16 机位一致性、
56 项资产预算，合计报出「71 PASS / 13 PASS / 0 FAIL」。但把渲染图和参考图
并排一看，模型是一顶等距褶皱的灯罩，脸是一块平板 —— 没有任何一条判据会
为此变红。原因是三层同时失效：

| 层 | 失效点 |
|---|---|
| 判据 | 14 条 spec 全是宏观比例（头身比、腰肩比…），0 条量五官/发丝/材质层次 |
| 谎报 | deliver.json 却写「脸型、五眼、发型轮廓」，这三项并不存在 |
| 空判 | A2 面部探针 PASS=0 SKIP=14、C 三渲二 PASS=0 SKIP=35，parse_rig 只读 PASS/FAIL，把 SKIP 全吞了 |

参考图只在开工当天被看了一眼，之后再没进过任何判据。工程一直在优化
「能算的数字」，不是「像不像」。本脚本补的是这个缺口。

判什么
------
两张图（参考图 / 当前模型固定正面机位渲染）各自提取「粉色头发」区域，
算 6 个可解释的图像特征：明暗跨度、局部梯度、边缘密度、条纹周期性、
发梢起伏、脸部边缘密度。基线由**参考图自身**算出，当前模型必须落在
参考基线允许的区间内。阈值是固定倍率，不照当前模型反调。

边界（别把这支脚本吹成「AI 会看模型了」）
------------------------------------------
它量的是**画面信息密度**，是「像不像」的必要非充分条件：
过闸门不代表像；不过闸门说明连细节密度都远低于参考，一定不够格。
职责是拦住明显糊弄的产出。真正像不像仍需人眼看渲染图。

用法（在 人物建模/ 下，用系统 Python，需 numpy / opencv-python）：
    python scripts/visual_gate.py --calibrate   # 用参考图算基线，写回 spec
    python scripts/visual_gate.py --selftest    # 负控制：原图 PASS、退化图 FAIL
    python scripts/visual_gate.py --probe       # 只打印特征值，不判定
    python scripts/visual_gate.py              # 判定并写 out/visual_gate.json
    python scripts/visual_gate.py --render      # 强制重渲染当前模型再判定

退出码：0 全过 / 1 有 FAIL / 2 环境或产物错误。
"""
import argparse
import json
import os
import subprocess
import sys
import time

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bpyrun  # noqa: E402

SPEC_PATH = os.path.join(ROOT, "spec", "visual_gate.json")


# ---------------------------------------------------------------- 图像读写
# Windows 上 cv2.imread / imwrite 不认中文路径，必须走 numpy 的字节通道。
def imread(path):
    if not os.path.isfile(path):
        raise IOError("图片不存在：%s" % path)
    buf = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if img is None:
        raise IOError("图片解码失败：%s" % path)
    return img


def imwrite(path, img):
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise IOError("PNG 编码失败")
    buf.tofile(path)


# ---------------------------------------------------------------- 区域提取
def hair_mask(bgr):
    """粉色头发区域：亮粉种子 + 附近暗粉补全，排除参考图的暗红背景。

    只靠 HSV 会翻车：参考图上方的红色雨棚/招牌 H 与粉发几乎一样，
    实测 HSV 方案把 bbox 拉成 [0,0,1599,729]（整片背景都算成头发）。
    亮粉种子的判据是 RGB 关系（R 高、R-G 明显、B 介于 G 与 R 之间），
    实测 bbox 收紧到 [537,99,1094,723]，与人物头发位置一致。
    再用较宽的 HSV 条件在种子附近补回暗部发丝，避免漏掉阴影里的头发。
    """
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    B, G, R = cv2.split(bgr.astype(np.int16))
    seed = ((R > 165) & (R - G > 25) & (B - G > 5) & (B < R - 20))
    wide = (((h <= 15) | (h >= 165)) & (s >= 36) & (v >= 92))
    near = cv2.dilate(seed.astype(np.uint8), np.ones((41, 41), np.uint8)) > 0
    m = ((seed | (wide & near)).astype(np.uint8) * 255)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return m.astype(bool), 0
    areas = stats[1:, cv2.CC_STAT_AREA]
    keep = [i + 1 for i, a in enumerate(areas) if a >= areas.max() * 0.08]
    out = np.isin(lab, keep)
    return out, int(out.sum())


def stripe_peak(V, hm, min_period=6, max_period=140):
    """水平扫描线亮度信号的 FFT：返回 (主峰能量占比, 主峰对应周期 px)。

    等距卡片会在每一条扫描线上产生同一个周期，能量集中在一个峰；
    真实发束粗细/间距不齐，能量摊在多个频率上，且主峰周期更短（发丝更细）。
    两个量都在归一化后的 512 宽图上算，跨分辨率可比。
    """
    n = V.shape[1]
    if n < 64:
        return 0.0, 0.0
    win = np.hanning(n).astype(np.float32)
    powers = []
    for y in range(V.shape[0]):
        row = V[y].astype(np.float32).copy()
        valid = hm[y]
        if valid.sum() < n * 0.55:
            continue
        row[~valid] = row[valid].mean()
        s = (row - row.mean()) * win
        powers.append(np.abs(np.fft.rfft(s)) ** 2)
    if not powers:
        return 0.0, 0.0
    p = np.mean(np.asarray(powers), axis=0)
    k0 = max(1, int(n / max_period))
    k1 = min(len(p) - 1, int(n / min_period))
    band = p[k0:k1 + 1]
    tot = float(band.sum())
    if tot <= 0:
        return 0.0, 0.0
    k = k0 + int(np.argmax(band))
    return float(band.max() / tot), float(n / k)


NORM_W = 512   # 两张图统一裁到头发包围盒后缩放到此宽度，跨分辨率才可比

# 脸部窗口：按头发包围盒高度取 [30%, 70%]，覆盖「眼睛 → 嘴角」。
# 2026-11-04 修正：原 [45%, 85%] 把眼睛整个排除在统计窗之外，判据只量
# 眼下到下巴那一块；建模侧为了凑密度只能往脸颊加规则排线，渲成「栅栏」，
# 属于典型的刷指标。上移后参考 0.1325 / 渲染 0.1020，窗口语义对齐，
# 余量也从 +0.0045 增至 +0.0225，不再逼着模型画假结构。
FACE_TOP, FACE_BOTTOM = 0.30, 0.70


def features(path):
    """返回 (特征值 dict, 诊断 dict)。区域全部由图像内容推出，不依赖固定像素坐标。

    为什么必须归一化：参考图 1600×1600、当前渲染 620×780。Canny 边缘密度、
    FFT 频带都随分辨率漂，不归一化等于拿两把不同的尺子比。
    另外粗黑描边会制造大量 Canny 边缘，所以「头发内边缘密度」之类总量指标
    分不清「细密发丝」和「18 条黑沟」，只作为诊断值输出，不参与判定。
    """
    bgr = imread(path)
    hm, area = hair_mask(bgr)
    if area < 800:
        raise ValueError("粉色头发区域只有 %d 像素，分割失败（检查发色或阈值）" % area)

    ys, xs = np.where(hm)
    bx0, bx1, by0, by1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    W, H = bx1 - bx0 + 1, by1 - by0 + 1
    pad = int(0.05 * W)
    cx0, cy0 = max(0, bx0 - pad), max(0, by0 - pad)
    cx1, cy1 = min(bgr.shape[1], bx1 + pad), min(bgr.shape[0], by1 + pad)
    crop = bgr[cy0:cy1, cx0:cx1]
    cm = hm[cy0:cy1, cx0:cx1].astype(np.uint8)
    nh = max(64, int(round(crop.shape[0] * NORM_W / crop.shape[1])))
    crop = cv2.resize(crop, (NORM_W, nh), interpolation=cv2.INTER_AREA)
    cm = cv2.resize(cm, (NORM_W, nh), interpolation=cv2.INTER_NEAREST) > 0

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    V = hsv[:, :, 2].astype(np.float32) / 255.0
    # 反法线描边壳是纯黑粗线，混进亮度分位会把「一块均匀粉色」伪装成
    # 「有高光有暗部」。只在非黑发丝像素上量明暗层次。
    bright = cm & (V > 0.15)
    excluded = float((cm & ~bright).sum())
    vv = V[bright] if bright.sum() > 500 else V[cm]
    v8 = (V * 255).astype(np.uint8)
    gx = cv2.Sobel(v8, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(v8, cv2.CV_32F, 0, 1, ksize=3)
    grad = np.hypot(gx, gy)
    edges = cv2.Canny(v8, 40, 110) > 0

    peak, period = stripe_peak(V, cm)

    # 脸窗口：按头发包围盒的比例取中央竖带；FACE_TOP/BOTTOM 见上方说明
    mys, mxs = np.where(cm)
    mw = mxs.max() - mxs.min() + 1
    mh = mys.max() - mys.min() + 1
    fx0, fx1 = int(mxs.min() + 0.28 * mw), int(mxs.max() - 0.28 * mw)
    fy0 = int(mys.min() + FACE_TOP * mh)
    fy1 = int(mys.min() + FACE_BOTTOM * mh)
    fx0, fy0 = max(0, fx0), max(0, fy0)
    fx1, fy1 = min(NORM_W, fx1), min(nh, fy1)
    face_density = float(edges[fy0:fy1, fx0:fx1].mean()) if fy1 > fy0 and fx1 > fx0 else 0.0

    f = {
        "hair_tone_span": float(np.quantile(vv, 0.95) - np.quantile(vv, 0.05)),
        "hair_stripe_peak": float(peak),
        "face_edge_density": face_density,
    }
    diag = {
        "image": os.path.relpath(path, ROOT).replace(os.sep, "/"),
        "size": [bgr.shape[1], bgr.shape[0]],
        "hair_pixels": area,
        "hair_bbox": [bx0, by0, bx1, by1],
        "normalized": [NORM_W, nh],
        "face_window": [fx0, fy0, fx1, fy1],
        "diagnostic_only": {
            "_why": "这三个量不参与判定：粗黑描边会制造大量边缘/梯度，FFT 主峰周期被大尺度明暗主导，分不清「细发丝」与「黑沟槽」。留着供人工复核。",
            "hair_stripe_period_px": round(float(period), 3),
            "hair_local_contrast": round(float(grad[cm].mean() / 255.0), 6),
            "hair_edge_density": round(float(edges[cm].mean()), 6),
            "outline_black_pixels_excluded": round(excluded, 1),
        },
    }
    return f, diag


# ---------------------------------------------------------------- 配置与判定
def load_cfg():
    with open(SPEC_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def paths(cfg):
    return (os.path.join(ROOT, cfg["reference_image"]),
            os.path.join(ROOT, cfg["render_image"]),
            os.path.join(ROOT, cfg["report"]))


def ensure_render(cfg, force=False):
    """当前模型渲染图缺失或旧于 美女.blend 时重渲染。"""
    ref, front, _ = paths(cfg)
    blend = os.path.join(ROOT, "美女.blend")
    stale = (not os.path.isfile(front)) or (
        os.path.isfile(blend) and os.path.getmtime(front) < os.path.getmtime(blend) - 1)
    if not (force or stale):
        return False
    blender = bpyrun.blender_exe(bpyrun.BLENDER_ENV, bpyrun.DEFAULT_BLENDER)
    if blender is None:
        raise RuntimeError("找不到 Blender")
    cmd = [blender, "-b", "--factory-startup", "--python-exit-code", "1",
           "--python", os.path.join(ROOT, cfg["render_producer"])]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True,
                       encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError("渲染失败：\n" + (p.stdout or "")[-1200:])
    return True


def judge(got, cfg):
    base = cfg.get("baseline")
    if not base:
        raise RuntimeError("基线未校准，先跑 --calibrate")
    lim = cfg["limits"]
    rows = []
    for f in cfg["features"]:
        k = f["key"]
        r, g = float(base[k]), float(got[k])
        if f["mode"] == "min":
            bound = r * lim["lower_ratio"]
            ok = g >= bound
            rule = "≥ %.4f（参考 × %.2f）" % (bound, lim["lower_ratio"])
        else:
            ratio = f.get("ratio", lim["stripe_max_ratio"])
            bound = r * ratio
            ok = g <= bound
            rule = "≤ %.4f（参考 × %.2f）" % (bound, ratio)
        rows.append({"key": k, "label": f["label"], "why": f["why"],
                     "ref": round(r, 6), "got": round(g, 6),
                     "limit": round(bound, 6), "rule": rule,
                     "verdict": "PASS" if ok else "FAIL"})
    return rows


def print_rows(rows):
    print("  %-26s %10s %10s  %-24s %s" % ("特征", "参考", "实测", "要求", "判定"))
    print("  " + "-" * 88)
    for r in rows:
        print("  %-26s %10.4f %10.4f  %-24s %s"
              % (r["label"][:26], r["ref"], r["got"], r["rule"], r["verdict"]))


# ---------------------------------------------------------------- 子命令
def calibrate(cfg, ref):
    f, diag = features(ref)
    cfg["baseline"] = {k: round(v, 6) for k, v in f.items()}
    cfg["_calibrated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    cfg["_calibrated_from"] = diag
    with open(SPEC_PATH, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)
    print("[visual] 基线已由参考图自身算出，写入 %s" % os.path.relpath(SPEC_PATH, ROOT))
    for k, v in f.items():
        print("  %-24s %.6f" % (k, v))
    print("  头发区域 %d 像素，bbox %s" % (diag["hair_pixels"], diag["hair_bbox"]))
    return 0


def degraded_copy(ref, out):
    """负控制：把头发与脸部的细节抹平，模拟「塑料色块 + 平板脸」的糊弄产出。

    早先试过「全图轻模糊 + 颜色量化」，结果三条判据全 PASS：量化产生的
    色带边缘反而把边缘密度拾高了，不算有效负例。这里改成**只抹平这两块
    区域**（大 σ 模糊 + 粗量化），语义直接对应判据要拦的东西。
    """
    img = imread(ref)
    hm, _ = hair_mask(img)
    flat = cv2.GaussianBlur(img, (0, 0), 18).astype(np.float32)
    flat = (flat // 48) * 48 + 24
    out_img = img.copy()
    out_img[hm] = flat[hm].astype(np.uint8)
    ys, xs = np.where(hm)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    w, h = x1 - x0 + 1, y1 - y0 + 1
    fx0, fx1 = int(x0 + 0.28 * w), int(x1 - 0.28 * w)
    fy0, fy1 = int(y0 + FACE_TOP * h), int(y0 + FACE_BOTTOM * h)
    out_img[fy0:fy1, fx0:fx1] = flat[fy0:fy1, fx0:fx1].astype(np.uint8)
    imwrite(out, out_img)
    return out


def selftest(cfg, ref, front):
    """参考图自己必须全 PASS；退化图必须至少 3 项 FAIL。两项都成立才算有判别力。"""
    base = cfg.get("baseline")
    if not base:
        print("[selftest] 基线未校准，先跑 --calibrate")
        return 2
    f_ref, _ = features(ref)
    rows_ref = judge(f_ref, cfg)
    n_ref_fail = sum(r["verdict"] == "FAIL" for r in rows_ref)

    deg = os.path.join(ROOT, "out", "_visual_gate_degraded.png")
    os.makedirs(os.path.dirname(deg), exist_ok=True)
    degraded_copy(ref, deg)
    f_deg, _ = features(deg)
    rows_deg = judge(f_deg, cfg)
    n_deg_fail = sum(r["verdict"] == "FAIL" for r in rows_deg)

    print("[selftest] 参考图自己：")
    print_rows(rows_ref)
    print("[selftest] 抹平头发/脸部细节后的退化图：")
    print_rows(rows_deg)
    ok = (n_ref_fail == 0) and (n_deg_fail >= 2)
    print("[selftest] 原图 FAIL=%d（要求 0）  退化图 FAIL=%d（要求 ≥2，共 %d 条判据）  → %s"
          % (n_ref_fail, n_deg_fail, len(rows_deg), "PASS" if ok else "判据失效"))
    return 0 if ok else 1


def probe(cfg, ref, front):
    for p in (ref, front):
        f, d = features(p)
        print("[probe] %s  头发 %d px  bbox %s  脸窗 %s"
              % (d["image"], d["hair_pixels"], d["hair_bbox"], d["face_window"]))
        for k, v in f.items():
            print("    %-24s %.6f" % (k, v))
    return 0


def run(cfg, ref, front, report, force_render):
    if force_render:
        ensure_render(cfg, force=True)
    f_ref, d_ref = features(ref)
    f_got, d_got = features(front)
    base = cfg.get("baseline")
    if not base:
        print("[visual] 基线未校准，先跑 --calibrate")
        return 2
    # 基线必须与当前登记的参考图对得上，防止换图后基线没重算
    drift = max(abs(f_ref[k] - base[k]) / (abs(base[k]) + 1e-6)
                for k in base if isinstance(base[k], (int, float)))
    rows = judge(f_got, cfg)
    fails = [r for r in rows if r["verdict"] == "FAIL"]
    summary = {"pass": len(rows) - len(fails), "fail": len(fails)}
    doc = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "verdict": "PASS" if not fails else "FAIL",
        "reference": cfg["reference_image"],
        "render": cfg["render_image"],
        "baseline_drift": round(drift, 6),
        "reference_diag": d_ref,
        "render_diag": d_got,
        "reference_features": {k: round(v, 6) for k, v in f_ref.items()},
        "measured": {k: round(v, 6) for k, v in f_got.items()},
        "rows": rows,
        "summary": summary,
        "boundary": cfg["_boundary"],
    }
    os.makedirs(os.path.dirname(report), exist_ok=True)
    with open(report, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
    print("[visual] 参考 %s  /  当前 %s" % (cfg["reference_image"], cfg["render_image"]))
    print_rows(rows)
    print("[visual] 合计 PASS=%d FAIL=%d  基线漂移=%.4f  判定 %s"
          % (summary["pass"], summary["fail"], drift, doc["verdict"]))
    if drift > 0.02:
        print("[visual] 警告：参考图与基线对不上，换过图就重跑 --calibrate", file=sys.stderr)
    print("[visual] 报告 -> %s" % os.path.relpath(report, ROOT))
    return 0 if not fails else 1


def main(argv=None):
    bpyrun.utf8_stdio()
    ap = argparse.ArgumentParser(prog="visual_gate.py")
    ap.add_argument("--calibrate", action="store_true", help="用参考图算基线并写回 spec")
    ap.add_argument("--selftest", action="store_true", help="负控制自检")
    ap.add_argument("--probe", action="store_true", help="只打印特征值")
    ap.add_argument("--render", action="store_true", help="强制重渲染当前模型")
    a = ap.parse_args(argv)

    cfg = load_cfg()
    ref, front, report = paths(cfg)
    if not os.path.isfile(ref):
        print("[visual] 缺少参考图：%s" % ref, file=sys.stderr)
        return 2
    if a.calibrate:
        return calibrate(cfg, ref)
    if a.probe:
        if not os.path.isfile(front):
            ensure_render(cfg)
        return probe(cfg, ref, front)
    if a.selftest:
        return selftest(cfg, ref, front)
    try:
        if not a.render:
            ensure_render(cfg)
        else:
            ensure_render(cfg, force=True)
    except RuntimeError as e:
        print("[visual] %s" % e, file=sys.stderr)
        return 2
    return run(cfg, ref, front, report, a.render)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
