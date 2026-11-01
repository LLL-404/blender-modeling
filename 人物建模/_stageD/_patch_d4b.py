# -*- coding: utf-8 -*-
"""D4 补丁（第二版）：按「可见凸出」重设卷边三段半径。

上一版把基准当成了 47mm（环层），实际 solidify 后袖筒外表面 = 48.34mm，
于是卷边 max 49.99 → 可见凸出只有 1.65mm；端口半径 46 < 47 还会嵌进袖筒。

本版以 48.34mm 为基准，Solidify 实测外偏移 +1.0mm：
    inner r 49.8 → 外表面 50.8 → 可见 +2.46mm（内缘厚）
    mid   r 50.4 → 外表面 51.4 → 可见 +3.06mm（最鼓，落在 [2,4]）
    outer r 49.4 → 外表面 50.4 → 可见 +2.06mm（外缘薄）
内缘 − 外缘 = 0.40mm 收薄；任意一环内表面 >= 48.34 的贴合线附近，
不再嵌进袖筒。

用法（工作目录 人物建模/）：
    python _stageD/_patch_d4b.py
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTFIT = os.path.join(HERE, "lib", "outfit.py")

NEW_CUFF = '''def _cuff_ring(side):
    """袖口卷边：**内缘略厚、外缘略薄**的翻折环（不是一根等径箍）。

    基准口径（2026-11-01 实测，别再用 DESIGN 里的 47mm）：
      · 47.00mm 是袖筒的**环层**半径（solidify 之前）；
      · solidify 之后袖筒末端外表面实测 **48.34mm** —— 这才是肉眼可见的表面。
    所以「卷边凸出 2~4mm」必须相对 48.34mm 算，相对 47mm 算会把 1.65mm 读成 3.2mm。

    三段半径（Solidify 0.002 实测外偏移 +1.0mm）：
        inner −10mm → r 49.8 → 外表面 50.8 → 可见凸出 +2.46mm（内缘压住袖筒边）
        mid    −4mm → r 50.4 → 外表面 51.4 → 可见凸出 +3.06mm（最鼓）
        outer   0mm → r 49.4 → 外表面 50.4 → 可见凸出 +2.06mm（布边收薄）
    内缘 − 外缘 = 0.40mm，跨 4mm 轴向长度 → 坡度约 5.7°，形成折返的明暗转折。
    任意一环内表面（r−1mm）都不低于袖筒外表面 48.34mm，不会嵌进袖筒。
    """
    s = side
    tip = Vector((0.169 * s, 0.006, 1.110))
    axis = Vector((-0.075 * s, 0.050, -0.996)).normalized()
    pts = [tip - axis * 0.010, tip - axis * 0.004, tip]
    rs = [(0.0498, 0.0498), (0.0504, 0.0504), (0.0494, 0.0494)]
    ob = tube(pts, rs, seg=40, name=f"cuff_{s}",
              cap_start=False, cap_end=False)
    solidify(ob, 0.002)
    return ob
'''


def main():
    s = io.open(OUTFIT, encoding="utf-8").read()
    if "可见凸出 +3.06mm" in s:
        print("[patch] cuff 已是本版，跳过")
        return 0
    m = re.search(r"def _cuff_ring\(side\):.*?\n    return ob\n", s, re.S)
    if not m:
        print("[patch] FAIL: 找不到 _cuff_ring")
        return 1
    s = s[:m.start()] + NEW_CUFF + s[m.end():]
    io.open(OUTFIT, "w", encoding="utf-8", newline="\n").write(s)
    print("[patch] cuff 已替换（按 48.34mm 可见基准）")
    return 0


if __name__ == "__main__":
    sys.exit(main())