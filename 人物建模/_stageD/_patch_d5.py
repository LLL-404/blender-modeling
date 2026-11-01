# -*- coding: utf-8 -*-
"""D5 补丁：裙褶环采样 132→176、开放 solid=False 通道、探针 D5 换傅里叶口径。

为什么用脚本改：lib/outfit.py 与 _stageD/d_probe.py 在本目录会被周期性重写
（mtime 每 1~2 分钟跳一次），按偏移保存的编辑器会反复失败。这里全部用
**内容锚点**做幂等替换，重复执行无副作用。

用法（工作目录 人物建模/）：
    python _stageD/_patch_d5.py
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTFIT = os.path.join(HERE, "lib", "outfit.py")
PROBE = os.path.join(HERE, "_stageD", "d_probe.py")

NEW_D5_BLOCK = '''    # D5 裙褶（2026-11-01 口径修正）：取**未 solidify 的裙摆单环**，按索引
    # 顺序（= _skirt 的角度顺序）做 DFT。22 次分量才是褶幅，2 次分量是椭圆
    # 本身，互不污染。
    # 旧口径（z 窗口 0.644~0.658 内排序后每褶 max-min）同时收进内外两层
    # （实测 264 = 132×2 个点）、每褶仅 6 点，差值里混着椭圆各向异性，
    # 报出 32.2mm 的假值 —— 典型的「量到的不是要量的东西」。
    skirt = outfitmod._skirt(solid=False)
    scos = cos_of(skirt)
    drop(skirt)
    seg = outfitmod.SKIRT_SEG
    pleats = 22
    if len(scos) >= seg:
        ring = scos[-seg:]                     # 最后一环 = 裙摆 z=0.650
        n = len(ring)
        rk = np.array([math.hypot(c.x, c.y - SKIRT_CY_D) for c in ring],
                      dtype=np.float64)
        kk = np.arange(n)
        th = 2.0 * np.pi * pleats * kk / n

        def _amp(order):
            c = np.sum(rk * np.exp(-2j * np.pi * order * kk / n)) * 2.0 / n
            return float(abs(c)), float(np.angle(c))

        a1, p1 = _amp(pleats)
        a2, p2 = _amp(2 * pleats)
        w = a1 * np.cos(th + p1) + a2 * np.cos(2.0 * th + p2)
        peak, trough = float(w.max()), float(w.min())
        out("D5 pleat peak_trough",
            f"seg={n} per_pleat={n / pleats:.1f} amp22={mm(a1)}mm "
            f"amp44={mm(a2)}mm peak={mm(peak)}mm trough={mm(trough)}mm "
            f"diff={mm(peak - trough)}mm "
            f"{'OK' if peak - trough >= 0.010 else 'FAIL'}（要求 >=10mm）")
        # 正面中线：|x| 最小、y 最前的顶点（a≈−90°）
        idx = min(range(n), key=lambda i: (abs(ring[i].x), ring[i].y))
        w_mid = float(w[idx])
        out("D5 pleat center_phase",
            f"mid_k={idx} a_mid={math.degrees(2 * math.pi * idx / n) - 360:.1f}deg "
            f"w_mid={mm(w_mid)}mm peak={mm(peak)}mm "
            f"delta={mm(peak - w_mid)}mm "
            f"{'OK(中线是峰)' if peak - w_mid <= 0.0015 else 'FAIL(中线不是峰)'}")
    else:
        out("D5 pleat peak_trough", "SKIP（裙子顶点数不足一环）")

'''

SKIRT_CY_CONST = '''SKIRT_SEG = 176             # 22 褶 × 8 点：48 段时每褶仅 2.18 点，峰谷混叠
SKIRT_HARM2 = 0.25          # 二次谐波系数：峰更尖、谷更平
'''


def patch_outfit():
    s = io.open(OUTFIT, encoding="utf-8").read()
    ch = []

    # 1) 环采样 132 → 176
    if "SKIRT_SEG = 132" in s:
        s = s.replace(
            "SKIRT_SEG = 132             # 22 褶 × 6 点：48 段时每褶仅 2.18 点，峰谷混叠",
            "SKIRT_SEG = 176             # 22 褶 × 8 点：48 段时每褶仅 2.18 点，峰谷混叠")
        ch.append("seg176")
    elif "SKIRT_SEG = 176" in s:
        pass
    else:
        print("[patch] WARN: 未找到 SKIRT_SEG 定义")

    s = s.replace("SKIRT_SEG=132（22 褶 × 6 点）", "SKIRT_SEG=176（22 褶 × 8 点）")

    # 2) 开放 solid 通道：probe 要取未 solidify 的干净单环
    if "def _skirt():" in s:
        s = s.replace("def _skirt():", "def _skirt(solid=True):")
        old_sig_doc = '''    三个改动（D5）：'''
        new_sig_doc = '''    `solid=False` 只给 _stageD/d_probe.py 量褶形用（与 `_sleeve(solid=False)`
    同一约定）：不 solidify 时顶点数 = 8 环 × SKIRT_SEG，最后一环就是干净的
    裙摆单环；solidify 之后内外两层 z 只差约 1mm，按 z 窗口取样必然混层。

    三个改动（D5）：'''
        if old_sig_doc in s:
            s = s.replace(old_sig_doc, new_sig_doc, 1)
        ch.append("solid_arg")

    if "        solidify(ob, 0.004)\n    assert_skirt_clearance(skirt_cos, body_cos)" in s:
        s = s.replace(
            "        solidify(ob, 0.004)\n    assert_skirt_clearance(skirt_cos, body_cos)",
            "        solidify(ob, 0.004)\n    assert_skirt_clearance(skirt_cos, body_cos)")
    # 只替换 _skirt 内的那一处（assert_skirt_clearance 唯一出现点）
    s = s.replace(
        "    skirt_cos = [v.co.copy() for v in ob.data.vertices]   # solidify 之前的环层\n"
        "    solidify(ob, 0.004)\n"
        "    assert_skirt_clearance(skirt_cos, body_cos)",
        "    skirt_cos = [v.co.copy() for v in ob.data.vertices]   # solidify 之前的环层\n"
        "    if solid:\n"
        "        solidify(ob, 0.004)\n"
        "    assert_skirt_clearance(skirt_cos, body_cos)")

    io.open(OUTFIT, "w", encoding="utf-8", newline="\n").write(s)
    print(f"[patch] outfit changed={ch or ['none']}")


def patch_probe():
    s = io.open(PROBE, encoding="utf-8").read()
    i0 = s.find("    # D5 裙褶")
    i1 = s.find("    drop(cloth)", i0)
    if i0 < 0 or i1 < 0:
        print("[patch] FAIL: probe D5 锚点未找到")
        return 1
    if NEW_D5_BLOCK not in s[i0:i1]:
        s = s[:i0] + NEW_D5_BLOCK + s[i1:]
        io.open(PROBE, "w", encoding="utf-8", newline="\n").write(s)
        print("[patch] probe D5 已替换")
    else:
        print("[patch] probe D5 已是最新")

    # 需要 SKIRT_CY 常量（探针里没有 outfit 的模块级常量引用）
    if "SKIRT_CY_D" in s and "SKIRT_CY_D = " not in s:
        anchor = "def mm(v):"
        j = s.find(anchor)
        s = s[:j] + "SKIRT_CY_D = 0.006   # 与 outfit.SKIRT_CY 一致（探针独立常量）\n\n\n" + s[j:]
        io.open(PROBE, "w", encoding="utf-8", newline="\n").write(s)
        print("[patch] probe 注入 SKIRT_CY_D")
    return 0


if __name__ == "__main__":
    patch_outfit()
    sys.exit(patch_probe())