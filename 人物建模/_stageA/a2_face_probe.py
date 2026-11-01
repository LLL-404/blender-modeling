# -*- coding: utf-8 -*-
r"""A2/A6 面部与头身比探针。不渲染，只在同一进程内 import head/look/body 构建后量测。

用法（在 人物建模/ 下）：
    "D:/Program Files/Blender Foundation/Blender 5.2/blender.exe" \
        -b --factory-startup --python _stageA/a2_face_probe.py 2>&1 \
        | grep -E "\[probe\]|Traceback"

量测项（对应 DESIGN 3.1 表 A2/A6 两行）：
  1. 几何头长 / 头身比 / 身高（脚底口径与 A4 对齐后口径各报一次）
  2. 头最大宽 / 最大深
  3. 鼻尖相对额面前伸（x≈0 中线，z 取 sz(1.440)~sz(1.470)）
  4. 嘴宽 · 嘴宽/脸宽 · 唇带 z 跨度
  5. 耳高（单独建一只耳量 z 跨度，同 head.ear 函数）
  6. 内眼角间距 / 眼宽（口径必须是内眼角间距，不是瞳孔间距）
  7. 面中 |x|<13mm 区域法线偏离 −Y 的最大角（flatten_face 之后）
  8. out/m3_face_front.png 的皮肤亮度 p5/p50/p95（基线，供 C 阶段对比）

像素统计优先用 PIL（系统 python 里有 11.3.0）；Blender 自带 python 没有 PIL，
则用 bpy 读图 + 相同的 sRGB 编码，两者口径完全一致。
"""
import os
import sys
import math

import bpy

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import cfg            # noqa: E402
import look           # noqa: E402
import head as headmod  # noqa: E402
import body as bodymod   # noqa: E402


def out(tag, text):
    print(f"[probe] {tag}: {text}")


# ---------------------------------------------------------------- 场景
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.engine = 'BLENDER_EEVEE'

M = look.set_all()
h = headmod.build(M)
look.flatten_face(h)

me = h.data
cos = [v.co.copy() for v in me.vertices]
xs = [c.x for c in cos]
ys = [c.y for c in cos]
zs = [c.z for c in cos]
head_top = max(zs)
head_bot = min(zs)
head_len = head_top - head_bot
head_w = max(xs) - min(xs)
head_d = max(ys) - min(ys)
out("head_box", f"z[{head_bot:+.4f},{head_top:+.4f}] x[{min(xs):+.4f},{max(xs):+.4f}] "
                f"y[{min(ys):+.4f},{max(ys):+.4f}]")
out("head_len", f"geom={head_len:.4f} (目标 0.2492±0.0020, "
                f"cfg 口径 CHIN_Z={cfg.CHIN_Z:.4f} → {head_top - cfg.CHIN_Z:.4f})")
out("head_size", f"width={head_w:.4f} (目标 0.212~0.218) depth={head_d:.4f} "
                 f"(目标 0.182~0.190)")

# ---------------------------------------------------------------- 身高/头身比
b = bodymod.build()
bz = [v.co.z for v in b.data.vertices]
foot_bottom = min(bz)
stature = head_top - foot_bottom
out("stature", f"head_top={head_top:.4f} body_bottom={foot_bottom:+.4f} "
               f"stature={stature:.4f} (目标 1.620±0.005)")
out("stature_aligned", f"若脚底对齐 z=0（A4 目标）: {head_top - 0.0:.4f}")
out("heads_ratio", f"{stature / head_len:.3f} (raw 口径) / "
                   f"{(head_top - 0.0) / head_len:.3f} (A4 对齐口径) "
                   f"(目标 6.50±0.06)")

# ---------------------------------------------------------------- 按材质取贴片顶点
def verts_by_mat(ob, name):
    """按材质名取顶点（join 后 Blender 会按材质数据块合并 slot）。"""
    m = ob.data
    idx = {i for i, mat in enumerate(m.materials)
           if mat is not None and mat.name.split(".")[0] == name}
    vi = set()
    for p in m.polygons:
        if p.material_index in idx:
            vi.update(p.vertices)
    return [m.vertices[i].co.copy() for i in vi]


# ---------------------------------------------------------------- 鼻子
# 「鼻尖相对额面前伸」= 额面 − 鼻尖。两个窗口都沿用 DESIGN 5.5 缺陷 4 的
# 原始口径：鼻尖 z 1.440~1.470、额面 z 1.520~1.570（不是 1.470~1.520 ——
# 那个窗口含鼻梁最高点，会把额面基准提前 6mm，前伸量算小一半）。
z_nose_lo, z_nose_hi = headmod.sz(1.440), headmod.sz(1.470)
z_fore_lo, z_fore_hi = headmod.sz(1.520), headmod.sz(1.570)


def mid_front_y(lo, hi, xmax=0.003):
    sel = [c.y for c in cos if abs(c.x) < xmax and lo <= c.z <= hi and c.y < 0]
    return (min(sel), len(sel)) if sel else (None, 0)


eye_z = headmod.EYE_Z
nose_y, nose_n = mid_front_y(z_nose_lo, z_nose_hi)
fore_y, fore_n = mid_front_y(z_fore_lo, z_fore_hi)
if nose_y is not None and fore_y is not None:
    out("nose", f"tip_y={nose_y:+.5f}(n={nose_n}) forehead_y={fore_y:+.5f}(n={fore_n}) "
                f"protrusion={1000.0 * (fore_y - nose_y):+.2f}mm "
                f"(目标 8.50~10.00)  [鼻尖 z {z_nose_lo:.4f}~{z_nose_hi:.4f}, "
                f"额 z {z_fore_lo:.4f}~{z_fore_hi:.4f}]")
else:
    out("nose", f"MISS tip={nose_y} forehead={fore_y}")

# ---------------------------------------------------------------- 嘴
lip = verts_by_mat(h, "lip")
if lip:
    lx = [c.x for c in lip]
    lz = [c.z for c in lip]
    mw = max(lx) - min(lx)
    out("mouth", f"width={mw:.4f} ({100.0 * mw / head_w:.2f}% 脸宽, 目标 10~13%) "
                 f"z_span={1000.0 * (max(lz) - min(lz)):.2f}mm "
                 f"z[{min(lz):+.4f},{max(lz):+.4f}] (mouth_z={headmod.sz(1.4305):+.4f})")
else:
    out("mouth", "MISS 找不到 lip 材质顶点")

# ---------------------------------------------------------------- 眼（内眼角口径）
sclera = verts_by_mat(h, "sclera")
if sclera:
    right = [c.x for c in sclera if c.x > 0]
    left = [c.x for c in sclera if c.x < 0]
    inner_gap = min(right) - max(left)
    eye_w = (max(right) - min(right) + max(left) - min(left)) / 2.0
    out("eye", f"inner_gap={inner_gap:.4f} eye_width={eye_w:.4f} "
               f"ratio={inner_gap / eye_w:.3f} (目标 0.85~1.00, 口径=内眼角间距) "
               f"[E]EYE_X={headmod.EYE_X} EYE_W={headmod.EYE_W}")
else:
    out("eye", "MISS 找不到 sclera 材质顶点")

# ---------------------------------------------------------------- 耳高（同 ear() 函数单建）
earL = headmod.ear(-1, M)
ez = [v.co.z for v in earL.data.vertices]
out("ear", f"height={1000.0 * (max(ez) - min(ez)):.2f}mm (目标 45~50) "
           f"z[{min(ez):+.4f},{max(ez):+.4f}] cz={headmod.sz(1.492):+.4f}")

# ---------------------------------------------------------------- 面中法线偏离
def corner_normals(mesh):
    try:
        return [c.vector.copy() for c in mesh.corner_normals]
    except AttributeError:
        return [lp.normal.copy() for lp in mesh.loops]


cn = corner_normals(me)
target = look.Vector((0.0, -1.0, 0.0))


def max_dev(zlo, zhi, xmax):
    worst = 0.0
    worst_at = None
    cnt = 0
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index]
            if abs(v.co.x) < xmax and zlo <= v.co.z <= zhi and v.co.y < -0.02:
                n = cn[li]
                d = max(-1.0, min(1.0, n.dot(target)))
                a = math.degrees(math.acos(d))
                cnt += 1
                if a > worst:
                    worst = a
                    worst_at = (v.co.x, v.co.z)
    return cnt, worst, worst_at


# 主口径：面中鼻唇区 sz(1.440)~sz(1.500)。下巴/下颌在 z<sz(1.410) 处本身
# 法线就偏离 −Y 很大（曲面转折），且 flatten 的 wz 渐入带里权重接近 0，
# 把它算进来会让「面中法线」这个指标失去意义 —— 所以主口径不含下巴。
cnt, worst, wat = max_dev(headmod.sz(1.440), headmod.sz(1.500), 0.013)
if wat:
    out("normals_mid", f"|x|<13mm z∈[sz1.440,sz1.500] loop={cnt} "
                       f"max_dev={worst:.2f}deg (目标 ≤25) "
                       f"at x={wat[0]:+.4f} z={wat[1]:+.4f}")
else:
    out("normals_mid", "|x|<13mm 面中区 loop=0")

# 参考口径：整张脸 sz(1.400)~sz(1.550)（含下巴，仅供定位硬边）
cnt2, worst2, wat2 = max_dev(headmod.sz(1.400), headmod.sz(1.550), 0.013)
if wat2:
    out("normals_face", f"|x|<13mm z∈[sz1.400,sz1.550] loop={cnt2} "
                        f"max_dev={worst2:.2f}deg (参考) "
                        f"at x={wat2[0]:+.4f} z={wat2[1]:+.4f}")

# ---------------------------------------------------------------- 像素统计
PNG = os.path.join(HERE, "out", "m3_face_front.png")



def _skin_percentiles(rgb_u8):
    """皮肤判据（0~255）：r≥180 且 g≥160 且 b≥140 且 r≥g≥b−10。

    这个判据能排掉背景(≈53,59,74)、地板(≈97)、头发最亮档(≈174,158,166)、
    虹膜(≈247,178,77)；会把眼白算进来（面积 <1%，可接受）。C 阶段沿用同一判据。
    """
    import numpy as np
    a = rgb_u8.astype(np.float32)
    r, g, bl = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    m = (r >= 180) & (g >= 160) & (bl >= 140) & (r >= g) & (g >= bl - 10)
    sel = a[m]
    if sel.size == 0:
        return None, 0
    lum = 0.2126 * sel[:, 0] + 0.7152 * sel[:, 1] + 0.0722 * sel[:, 2]
    p5, p50, p95 = np.percentile(lum, [5, 50, 95])
    return (float(p5), float(p50), float(p95)), int(sel.shape[0])


def pixel_stats(path):
    if not os.path.exists(path):
        return f"MISS {path}"
    try:
        from PIL import Image
        import numpy as np
        im = Image.open(path).convert("RGB")
        arr = np.asarray(im, dtype=np.uint8)
        src = "PIL"
    except ImportError:
        import numpy as np
        img = bpy.data.images.load(path)
        w, hgt = img.size
        buf = np.empty(w * hgt * 4, dtype=np.float32)
        img.pixels.foreach_get(buf)
        # 实测：Blender 5.2 对 8-bit sRGB PNG，Image.pixels 返回的就是
        # sRGB 编码后的 0~1 值（0.9765 = 249/255），不是线性值 ——
        # 所以这里直接 ×255，不要再做 sRGB 编码，否则亮度会被抬高约 5%。
        lin = buf.reshape(-1, 4)[:, :3]
        arr = (np.clip(lin, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8).reshape(hgt, w, 3)
        bpy.data.images.remove(img)
        src = "bpy"
    pct, n = _skin_percentiles(arr)
    if pct is None:
        return f"src={src} 无皮肤像素"
    hgt, wid = arr.shape[0], arr.shape[1]
    return (f"src={src} size={wid}x{hgt} skin_px={n} "
            f"lum_p5={pct[0]:.1f} p50={pct[1]:.1f} p95={pct[2]:.1f} "
            f"(p50-p5={pct[1] - pct[0]:.1f}, p95-p50={pct[2] - pct[1]:.1f})")


out("pixels", pixel_stats(PNG))
print("[probe] done")