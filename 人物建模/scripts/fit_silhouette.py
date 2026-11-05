# -*- coding: utf-8 -*-
"""C 步：从参考图反解头发轮廓的比例参数（路线 2 的拟合环节）。

做什么
------
不是「再渲染一张图看看像不像」，而是把「像不像」变成一个可求解的量：

  1. 参考图与当前渲染各自分割出头发（复用 visual_gate 的分割；配置读 spec/visual_gate.json）
  2. 两边都按「头发包围盒高度」归一化、水平居中，缩放到同一高度
  3. 算剪影 IoU —— 形状重合度，0~1
  4. 在「横向缩放 × 纵向平移」上做小网格搜索，找 IoU 最大的仿射对齐，
     得到「当前头发相对参考图偏宽/偏窄多少」
  5. 把宽度偏差换算成 `_RX_K`（hair.py 的横向系数），给出一条可执行的建议

为什么只调宽度、不做全参数反解
------------------------------
剪影只约束「外轮廓」。刘海长度、卡片层数、发梢形状都会改变内部细节但
几乎不改变外轮廓 —— 用剪影去解它们会得到病态解（多组参数同样 IoU）。
这里只解剪影真正能确定的量，其余留给视觉闸门与人眼。

输出
----
  out/silhouette_fit.json   两图的比例、IoU、最佳仿射、建议系数
  out/_silhouette_cmp.png   两图剪影并排（红=仅参考、蓝=仅当前、白=重合）

用法
----
  python scripts/fit_silhouette.py                    # 只测量
  python scripts/fit_silhouette.py --apply            # 测量并把建议写进 profile
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import visual_gate as vg

# 2026-11-05 换靶复盘：原来写死 1000139587.jpg，且 hair_mask 走默认的
# profile="pink"。换成银白发概念图后，粉发掩码套银发图必然分割失败。
# 现在参考图与分割配置**唯一来源**都是 spec/visual_gate.json，换图只改那一处。
_CFG = json.load(open(os.path.join(ROOT, "spec", "visual_gate.json"), encoding="utf-8"))
REF = os.path.join(ROOT, _CFG["reference_image"])
MCFG = _CFG.get("hair_mask")
CUR = os.path.join(ROOT, "out", "visual_front.png")
OUT = os.path.join(ROOT, "out")

NORM_H = 256          # 归一化后的剪影高度（像素）
NORM_W = 256          # 画布宽度；两侧留白，宽度差异会体现在 IoU 上


def mask_of(path, is_reference=False):
    bgr = vg.imread(path)
    m, area = vg.hair_mask(bgr, MCFG, is_reference=is_reference)
    if area < 800:
        raise SystemExit("头发分割失败：%s 只有 %d 像素" % (path, area))
    return m.astype(np.uint8)


def norm_silhouette(m):
    """按包围盒高度归一化、水平居中，放进 NORM_H × NORM_W 画布。"""
    ys, xs = np.where(m > 0)
    y0, y1 = int(ys.min()), int(ys.max())
    x0, x1 = int(xs.min()), int(xs.max())
    crop = m[y0:y1 + 1, x0:x1 + 1]
    h, w = crop.shape
    scale = NORM_H / float(h)
    nw = max(1, int(round(w * scale)))
    # 最近邻缩放：掩码是二值的，插值会产生中间值
    yi = np.clip((np.arange(NORM_H) / scale).astype(int), 0, h - 1)
    xi = np.clip((np.arange(nw) / scale).astype(int), 0, w - 1)
    small = crop[yi][:, xi]
    canvas = np.zeros((NORM_H, NORM_W), np.uint8)
    x_off = (NORM_W - nw) // 2
    if nw <= NORM_W:
        canvas[:, x_off:x_off + nw] = small
    else:
        canvas[:] = small[:, (nw - NORM_W) // 2:(nw - NORM_W) // 2 + NORM_W]
    return canvas, (w / float(h)), (x0, y0, x1, y1)


def iou(a, b):
    inter = int(((a > 0) & (b > 0)).sum())
    union = int(((a > 0) | (b > 0)).sum())
    return inter / float(union) if union else 0.0


def best_affine(ref, cur, scales, shifts):
    """在当前剪影上搜「横向缩放 + 横向平移」，返回 (IoU, scale, shift)。"""
    best = (-1.0, 1.0, 0.0)
    cx = NORM_W // 2
    for s in scales:
        # 以画布中线为锚做横向缩放
        xs = (np.arange(NORM_W) - cx) / s + cx
        xi = np.clip(xs.astype(int), 0, NORM_W - 1)
        warped = cur[:, xi]
        for dx in shifts:
            moved = np.zeros_like(warped)
            if dx >= 0:
                moved[:, dx:] = warped[:, :NORM_W - dx] if dx else warped
            else:
                moved[:, :NORM_W + dx] = warped[:, -dx:]
            v = iou(ref, moved)
            if v > best[0]:
                best = (v, s, dx)
    return best


def write_cmp(path, ref, cur):
    """红 = 仅参考有、蓝 = 仅当前有、白 = 都有。"""
    rgb = np.zeros((NORM_H, NORM_W, 3), np.uint8)
    rgb[..., 0] = ref * 255
    rgb[..., 2] = cur * 255
    both = (ref > 0) & (cur > 0)
    rgb[both] = (255, 255, 255)
    vg.imwrite(path, rgb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="把建议的宽度系数写进 params/profile.json")
    args = ap.parse_args()

    ref, ref_wh, ref_bb = norm_silhouette(mask_of(REF, is_reference=True))
    cur, cur_wh, cur_bb = norm_silhouette(mask_of(CUR, is_reference=False))
    base = iou(ref, cur)

    scales = [round(0.80 + 0.01 * i, 3) for i in range(41)]     # 0.80 ~ 1.20
    shifts = list(range(-16, 17, 2))
    top, s, dx = best_affine(ref, cur, scales, shifts)

    # 宽度系数：把「当前剪影再缩放 s 倍才对齐参考」翻译成「几何要乘多少」。
    # 掩码按高度归一化，所以这里得到的是纯宽度比。
    k = round(1.0 / s, 4) if s else 1.0

    out = {
        "reference": {"bbox": list(ref_bb), "w_over_h": round(ref_wh, 4),
                      "pixels": int((ref > 0).sum())},
        "current": {"bbox": list(cur_bb), "w_over_h": round(cur_wh, 4),
                    "pixels": int((cur > 0).sum())},
        "iou": round(base, 4),
        "best_affine": {"iou": round(top, 4), "scale": s, "shift": dx},
        "width_coef_suggest": k,
        "_note": ("剪影只约束外轮廓；刘海长度/卡片层数/发梢形状改不动它，"
                  "所以这里只解宽度，其余交给视觉闸门与人眼。"
                  "best_affine.iou 是「只做横向缩放能达到的上界」，"
                  "它与 iou 的差越大，说明差的主要是轮廓比例而不是细节。"),
    }

    os.makedirs(OUT, exist_ok=True)
    jp = os.path.join(OUT, "silhouette_fit.json")
    json.dump(out, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    write_cmp(os.path.join(OUT, "_silhouette_cmp.png"), ref, cur)

    print("[fit] 参考 w/h=%.4f  当前 w/h=%.4f  比例差 %+.1f%%"
          % (ref_wh, cur_wh, (cur_wh / ref_wh - 1.0) * 100.0))
    print("[fit] 剪影 IoU = %.4f" % base)
    print("[fit] 最佳横向缩放 = %.2f（IoU 上界 %.4f）→ 建议宽度系数 %.3f"
          % (s, top, k))
    print("[fit] 报告 -> %s" % jp)

    if args.apply and abs(k - 1.0) > 0.03:
        pp = os.path.join(ROOT, "params", "profile.json")
        prof = json.load(open(pp, encoding="utf-8"))
        hair = prof.setdefault("hair", {})
        old = hair.get("hair_width_scale", 1.0)
        hair["hair_width_scale"] = round(old * k, 4)
        json.dump(prof, open(pp, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print("[fit] profile: hair.hair_width_scale %s -> %s"
              % (old, hair["hair_width_scale"]))
    elif args.apply:
        print("[fit] 宽度偏差 <3%%，不动 profile")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
