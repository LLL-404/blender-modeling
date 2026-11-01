# -*- coding: utf-8 -*-
"""D3 补丁：翻领开弧（手搓网格，避开 loft 强闭环）+ 衬衫 V 形领口。

为什么用脚本改而不是编辑器：本目录有另一个进程在周期性重写 lib/outfit.py
（mtime 每 1~2 分钟变化一次），按偏移量保存的编辑器会反复失败。
这里用**内容锚点**做幂等替换：同样的内容重复执行不会产生副作用。

用法（工作目录 人物建模/）：
    python _stageD/_patch_d3.py
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(HERE, "lib", "outfit.py")

# ---------------------------------------------------------------- 新的领子块
NEW_COLLAR_BLOCK = '''COLLAR_A0, COLLAR_A1 = 279.0, 621.0   # 开弧：绕过正后方，前中留 ±9° 开口


def _collar_arc(rx, ry, cy, z_back, z_front, seg):
    """一圈**开弧**：从 a=279° 绕过后脑到 621°(=261°)，z 随「离正后方」线性下降。

    角度约定同 superellipse_ring：0°=+x（右）、90°=+y（后）、270°=−y（前）。
    d=0 在正后方、d=1 在正前方，于是后领高、前领低，中间两翼平滑过渡。
    缺口取 ±9°（不是 ±20°）：r=66mm 时 9° 弧长 ≈10mm、x 半宽 ≈10mm，
    刚满足「前中 |x|<6mm 无顶点」的开口判据，又不会裂成一个大豁口。
    """
    pts = []
    for i in range(seg):
        a_deg = COLLAR_A0 + (COLLAR_A1 - COLLAR_A0) * i / (seg - 1)
        a = math.radians(a_deg)
        dd = abs(((a_deg - 90.0) + 180.0) % 360.0 - 180.0)   # 0(后)..180(前)
        d = dd / 180.0
        z = z_back + (z_front - z_back) * d
        pts.append(Vector((rx * math.cos(a), cy + ry * math.sin(a), z)))
    return pts


def _collar():
    """衬衫翻领：后领高、前领开 V、前中留**真空开口**。

    原实现是 3 个同心**闭合**环（z 1.300/1.322/1.336，rx 70/60/52mm），
    放样出来是一个套在脖子上的圈，视觉上是"颈圈"而不是衬衫领 —— 因为
    它既没有前后落差，也没有前中开口，更没有翻折边。

    现在的截面是「立起 → 翻下」三层（半径/高度单位是米）：
        领根   rx 58 ry 48   z 后 1.328 → 前 1.308   （藏进衬衫 V 形领口内侧）
        翻折线 rx 64 ry 53   z 后 1.342 → 前 1.320   （领座顶 = 后领高）
        外翻缘 rx 76 ry 64   z 后 1.334 → 前 1.312   （领尖外翻 12mm，略降）
    于是后领高 1.342、前领口 1.320，V 深 22mm（要求 ≥12）。

    **不能用 `meshkit.loft` 铺这三行**：loft 的桥接是 `j2=(j+1)%seg`，永远
    首尾闭合，会把前中缺口的两侧硬连成一张横跨的布（顶点仍为空、面却闭合，
    探针照样能报「开口」—— 典型假达标）。这里按「角度 × 3 行」手搓四边形，
    开弧两端（前中缺口两侧）保持开放，交给 Solidify 的 use_rim 缝边，
    边界边数仍为 0。
    """
    seg = 44
    rows = [
        _collar_arc(0.058, 0.048, 0.003, 1.328, 1.308, seg),   # 领根
        _collar_arc(0.064, 0.053, 0.003, 1.342, 1.320, seg),   # 翻折线
        _collar_arc(0.076, 0.064, 0.003, 1.334, 1.312, seg),   # 外翻边缘
    ]
    verts = []
    for r in rows:
        verts.extend(r)
    faces = []
    for k in range(seg - 1):                  # 开弧：k 只到 seg-2，不连回起点
        for i in range(len(rows) - 1):
            a = i * seg + k
            b = (i + 1) * seg + k
            faces.append((a, a + 1, b + 1, b))
    ob = mesh_from(verts, faces, name="collar")
    recalc_normals(ob)
    solidify(ob, 0.004)
    return ob


'''

NEW_NECK_HELPER = '''def _shirt_neck_ring(z_back=1.332, z_front=1.312, rx=0.066, ry=0.056, cy=0.002):
    """衬衫领口收口环：**V 形**，前中降到 z_front。

    为什么必须 V 形（D3 实测教训）：衬衫肩部在 z 1.305~1.332 之间从 150mm
    急收到 66mm，是一条很陡的收口锥。翻领前中无论怎么降，只要半径 <120mm
    就整片沉进衬衫内部 —— D3 之前「前领 V 深 24mm」在画面上完全不存在，
    探针量到的 37.8mm 只是领圈上下两环的高度差。收口环本身开 V，翻领的
    V 口才有地方露出来。
    """
    pts = []
    seg = cfg.RING_SEG
    for i in range(seg):
        a = 2.0 * math.pi * i / seg
        d = 0.5 * (1.0 - math.sin(a))       # 前中=1、后中=0
        z = z_back + (z_front - z_back) * d
        ca, sa = math.cos(a), math.sin(a)
        pts.append(Vector((rx * ca, cy + ry * sa, z)))
    return pts


'''

OLD_TOP = '''    # 领口收口：从肩顶收到颈根，避免肩部出现一张平盖
    rings.append(superellipse_ring(1.332, 0.066, 0.056, 0.002, 0.0, 2.0,
                                   cfg.RING_SEG))
'''
NEW_TOP = '''    # 领口收口：从肩顶收到颈根，避免肩部出现一张平盖。
    # D3：收口环做成 **V 形**（前中降到 1.312），否则翻领前中会被这条水平
    # 环整片埋住（见 _shirt_neck_ring 的说明）。
    rings.append(_shirt_neck_ring())
'''


def main():
    src = io.open(PATH, encoding="utf-8").read()
    changed = []

    # ---- 1) 领子块：从 COLLAR_A0 到 SKIRT_CY 之前，整段替换（幂等）
    i0 = src.find("COLLAR_A0")
    i1 = src.find("SKIRT_CY = 0.006")
    if i0 < 0 or i1 < 0 or i1 <= i0:
        print("[patch] FAIL: 找不到 COLLAR_A0 / SKIRT_CY 锚点")
        return 1
    if src[i0:i1] != NEW_COLLAR_BLOCK:
        src = src[:i0] + NEW_COLLAR_BLOCK + src[i1:]
        changed.append("collar")

    # ---- 2) 衬衫 V 形领口
    if OLD_TOP in src:
        src = src.replace(OLD_TOP, NEW_TOP)
        changed.append("shirt_top")
    elif "_shirt_neck_ring()" not in src:
        print("[patch] WARN: 未找到旧的收口环代码，且未见 _shirt_neck_ring 调用")
    else:
        print("[patch] shirt_top 已是 V 形，跳过")

    # ---- 3) 注入 _shirt_neck_ring 定义（放在 _shirt() 之前，幂等）
    if "def _shirt_neck_ring(" not in src:
        anchor = "def _shirt():"
        j = src.find(anchor)
        if j < 0:
            print("[patch] FAIL: 找不到 def _shirt()")
            return 1
        src = src[:j] + NEW_NECK_HELPER + src[j:]
        changed.append("neck_helper")

    io.open(PATH, "w", encoding="utf-8", newline="\n").write(src)
    print(f"[patch] written, changed={changed or 'none(已是最新)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())