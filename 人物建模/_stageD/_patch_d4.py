# -*- coding: utf-8 -*-
"""D4 补丁：卷边造型（内厚外薄）+ 探针改用「可见凸出」口径。

为什么改口径：A5 的 3.2mm 是相对**裸管 47mm（环层）**算的；solidify 之后
袖筒外表面已经到 48.34mm，所以肉眼可见的凸出只有 1.65mm。「卷边凸出 2~4mm」
这条验收如果按环层量，会一直把 1.65mm 读成 3.2mm —— 量到的不是要量的东西。

用法（工作目录 人物建模/）：
    python _stageD/_patch_d4.py
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTFIT = os.path.join(HERE, "lib", "outfit.py")
PROBE = os.path.join(HERE, "_stageD", "d_probe.py")

OLD_CUFF = '''def _cuff_ring(side):
    """袖口卷边：半径 48mm（= 袖口 47 + 1mm）、沿袖轴高 8mm 的一圈厚箍。

    卷边半径必须 >= 袖口半径，否则会嵌进袖筒内部（一种看不见的穿模）；
    这里靠 solidify 后内表面 47mm 正好贴合袖口外表面。
    """
    s = side
    tip = Vector((0.169 * s, 0.006, 1.110))
    axis = Vector((-0.075 * s, 0.050, -0.996)).normalized()
    back = tip - axis * 0.008
    ob = tube([back, tip], [(0.048, 0.048), (0.048, 0.048)],
              seg=40, name=f"cuff_{s}", cap_start=False, cap_end=False)
    solidify(ob, 0.002)
    return ob
'''

NEW_CUFF = '''def _cuff_ring(side):
    """袖口卷边：**内缘略厚、外缘略薄**的翻折环（不是一根等粗的箍）。

    A5 做的是一根半径恒定 48mm 的直筒（solidify 后外表面 50.0mm），几何上
    是个"套在袖口上的橡皮筋"，没有翻折形态。D4 只做造型，不动半径量级：

        内端  r 49.4   （外表面 51.4，比袖口外的箍更厚，压住袖筒边）
        mid   r 50.2   （最鼓，外表面 52.2）
        外缘  r 48.6   （收薄，外表面 50.6 —— 布边折进去的那一圈）

    实测基准：袖筒 solidify 后的末端外表面 **48.34mm**（裸管 47mm 是环层，
    不是可见表面）。于是三段可见凸出 = +3.06 / +3.86 / +2.26mm，全部落在
    [2,4]mm；内缘 − 外缘 = 0.80mm 的收薄，形成折返斜面（渲染上是一条暗带）。
    边缘比 mid 低 1.6mm、跨 4mm 轴向长度，坡度约 22°，足以产生明暗转折。

    三段共线、同一 axis，tube 的切线一致，不会扭结；cap 两端仍关闭后交给
    solidify 缝边，边界边数保持 0。
    """
    s = side
    tip = Vector((0.169 * s, 0.006, 1.110))
    axis = Vector((-0.075 * s, 0.050, -0.996)).normalized()
    pts = [tip - axis * 0.008, tip - axis * 0.003, tip + axis * 0.001]
    rs = [(0.0494, 0.0494), (0.0502, 0.0502), (0.0486, 0.0486)]
    ob = tube(pts, rs, seg=40, name=f"cuff_{s}",
              cap_start=False, cap_end=False)
    solidify(ob, 0.002)
    return ob
'''

OLD_D4_START = "    # D4 卷边凸出 + 边界边数（复用 A5 的 sleeve 采样口径）"
OLD_D4_END = ("    out(\"D4 cuff boundary_edges\", f\"{n_bound} "
              "{'OK' if n_bound == 0 else 'FAIL'}\")")

NEW_D4 = '''    # D4 卷边凸出 + 边界边数。
    # 口径（2026-11-01 修）：A5 拿「裸管 47mm（环层）」当基准，报出凸出 3.2mm；
    # 但 solidify 之后袖筒外表面是 48.34mm，真实可见凸出只有 1.65mm。
    # D4 的造型验收按可见凸出 = 卷边外表面 − 袖筒 solidify 后末端外表面。
    import bmesh
    from mathutils import Vector as _V
    SEG = 40
    tube_ob = outfitmod._sleeve(1, solid=False, cuff=False)   # 环层（A5 旧口径）
    vs = cos_of(tube_ob)
    ring = vs[-(SEG + 2):-2]
    cen = [sum(p[i] for p in ring) / len(ring) for i in range(3)]
    prev = vs[-(2 * SEG + 2):-(SEG + 2)]
    cen_p = [sum(p[i] for p in prev) / len(prev) for i in range(3)]
    axis = [cen[i] - cen_p[i] for i in range(3)]
    ln = math.sqrt(sum(a * a for a in axis)) or 1.0
    axis = [a / ln for a in axis]
    r_tube = max(math.sqrt(sum(((p[i] - cen[i]) - sum((p[j] - cen[j]) * axis[j]
                                                    for j in range(3)) * axis[i]) ** 2
                              for i in range(3))) for p in ring)
    drop(tube_ob)

    # 可见基准：同轴同面、solidify 之后的袖筒末端（tip ±6mm 带内的最大垂轴半径）
    _tip = _V((0.169, 0.006, 1.110))
    _ax = _V((-0.075, 0.050, -0.996)).normalized()
    sol_ob = outfitmod._sleeve(1, solid=True, cuff=False)
    _band = []
    for c in cos_of(sol_ob):
        d = c - _tip
        if abs(d.dot(_ax)) <= 0.006:
            _band.append((d - d.dot(_ax) * _ax).length)
    r_solid = max(_band) if _band else None
    drop(sol_ob)

    band = []
    for c in ccos2:
        if c.x <= 0.13:
            continue
        d = [c.x - cen[0], c.y - cen[1], c.z - cen[2]]
        if abs(sum(d[i] * axis[i] for i in range(3))) <= 0.010:
            perp = [d[i] - sum(d[j] * axis[j] for j in range(3)) * axis[i]
                    for i in range(3)]
            band.append(math.sqrt(sum(x * x for x in perp)))
    r_out = max(band) if band else None
    vis = None if (r_out is None or r_solid is None) else r_out - r_solid
    out("D4 cuff ring bulge",
        f"tube_r={mm(r_tube)}mm outfit_r_max={mm(r_out)}mm "
        f"sleeve_solid_r={mm(r_solid)}mm visible={mm(vis)}mm "
        f"(旧环层口径={mm(None if r_out is None else r_out - r_tube)}mm) "
        f"{'OK' if (vis is not None and 0.002 <= vis <= 0.004) else 'FAIL'}"
        f"（可见凸出要求 2~4mm）")
    # 造型验收：内缘厚、外缘薄，且都仍 >=2mm 可见
    segs = []
    for lo, hi, tag in ((-0.009, -0.006, "inner"), (-0.006, -0.001, "mid"),
                        (0.0, 0.004, "outer")):
        b = []
        for c in ccos2:
            if c.x <= 0.13:
                continue
            d = [c.x - cen[0], c.y - cen[1], c.z - cen[2]]
            t = sum(d[i] * axis[i] for i in range(3))
            if lo <= t < hi:
                perp = [d[i] - t * axis[i] for i in range(3)]
                b.append(math.sqrt(sum(x * x for x in perp)))
        if b and r_solid is not None:
            segs.append((tag, max(b) - r_solid))
    if segs:
        detail = " ".join(f"{t}:{v * 1000:+.2f}" for t, v in segs)
        dmap = dict(segs)
        ok = (dmap.get("inner", 0) > dmap.get("outer", 0) + 0.0003
              and all(v >= 0.002 for _, v in segs))
        out("D4 cuff shape", f"{detail}mm "
            f"{'OK(内厚外薄)' if ok else 'FAIL'}（要求 inner>outer+0.3mm 且均>=2mm）")

    bm = bmesh.new()
    bm.from_mesh(cloth.data)
    n_bound = sum(1 for e in bm.edges if e.is_boundary)
    bm.free()
    out("D4 cuff boundary_edges", f"{n_bound} {'OK' if n_bound == 0 else 'FAIL'}")
'''


def patch_outfit():
    s = io.open(OUTFIT, encoding="utf-8").read()
    if NEW_CUFF in s:
        print("[patch] cuff 已是最新")
    elif OLD_CUFF in s:
        s = s.replace(OLD_CUFF, NEW_CUFF)
        print("[patch] cuff 已替换")
    else:
        print("[patch] FAIL: _cuff_ring 锚点不匹配")
        return 1
    io.open(OUTFIT, "w", encoding="utf-8", newline="\n").write(s)
    return 0


def patch_probe():
    s = io.open(PROBE, encoding="utf-8").read()
    i0 = s.find(OLD_D4_START)
    i1 = s.find(OLD_D4_END, i0)
    if i0 < 0 or i1 < 0:
        print("[patch] FAIL: probe D4 锚点未找到")
        return 1
    i1 += len(OLD_D4_END)
    if NEW_D4.strip() in s:
        print("[patch] probe D4 已是最新")
        return 0
    s = s[:i0] + NEW_D4.rstrip("\n") + s[i1:]
    io.open(PROBE, "w", encoding="utf-8", newline="\n").write(s)
    print("[patch] probe D4 已替换")
    return 0


if __name__ == "__main__":
    patch_outfit()
    sys.exit(patch_probe())