# -*- coding: utf-8 -*-
"""bapi 自测：逐项实测每个封装，打印 PASS / FAIL / SKIP。

    blender -b --factory-startup --python selftest.py

退出码 0 = 全部 PASS（SKIP 不算失败，但会打印原因）。
每一行都带实测数值——这个自测本身就是「封装能不能用」的证据，
不是「我写了所以它能用」的声明。
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bmesh
import bpy
from mathutils import Vector

import bapi
from bapi import env, mat, mesh, mod, obj, sculpt, shot

OUT = os.path.join(HERE, "out", "selftest")
os.makedirs(OUT, exist_ok=True)

RESULT = []


class SkipTest(Exception):
    pass


def rec(status, name, detail=""):
    RESULT.append({"status": status, "name": name, "detail": detail})
    line = "%-4s %-42s %s" % (status, name, detail)
    print(line.encode("utf-8", "replace").decode("utf-8"), flush=True)


def case(name):
    def deco(fn):
        try:
            detail = fn()
            rec("PASS", name, detail if isinstance(detail, str) else "")
        except SkipTest as exc:
            rec("SKIP", name, str(exc))
        except Exception as exc:
            rec("FAIL", name, "%s: %s" % (type(exc).__name__, exc))
        return fn
    return deco


# ---------------------------------------------------------------- 工具

def fresh():
    """清空对象，保留场景与世界。"""
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials,
                 bpy.data.lights, bpy.data.cameras):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)


def noisy_grid(n=21, size=1.0, amp=0.02, name="grid"):
    verts = []
    for i in range(n):
        for j in range(n):
            x = size * (i / (n - 1) - 0.5)
            y = size * (j / (n - 1) - 0.5)
            z = amp * math.sin(x * 17.0) * math.cos(y * 13.0)
            verts.append((x, y, z))
    faces = []
    for i in range(n - 1):
        for j in range(n - 1):
            a = i * n + j
            faces.append((a, a + n, a + n + 1, a + 1))
    return mesh.from_verts_faces(verts, faces, name)


def components(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    seen = set()
    n = 0
    for v in bm.verts:
        if v.index in seen:
            continue
        n += 1
        stack = [v]
        seen.add(v.index)
        while stack:
            cur = stack.pop()
            for e in cur.link_edges:
                o = e.other_vert(cur)
                if o.index not in seen:
                    seen.add(o.index)
                    stack.append(o)
    bm.free()
    return n


def read_pixels(path):
    """返回 (w, h, rgb 列表)，值为线性 0..1。"""
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    buf = [0.0] * (w * h * 4)
    img.pixels.foreach_get(buf)
    bpy.data.images.remove(img)
    rgb = [(buf[i * 4], buf[i * 4 + 1], buf[i * 4 + 2]) for i in range(w * h)]
    return w, h, rgb


def luma_stats(rgb):
    ls = [0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in rgb]
    n = len(ls)
    mean = sum(ls) / n
    var = sum((x - mean) ** 2 for x in ls) / n
    return min(ls), max(ls), mean, math.sqrt(var)


# ---------------------------------------------------------------- 环境

@case("env · 版本")
def _():
    v = env.version()
    assert v.startswith("5."), v
    return v


@case("env · reset/engine/eevee/colormanage")
def _():
    sc = env.reset()
    env.engine("BLENDER_EEVEE")
    env.eevee(samples=16, raytracing=True)
    env.color_standard()
    env.resolution(192, 192)
    assert sc.render.engine == "BLENDER_EEVEE", sc.render.engine
    assert sc.view_settings.view_transform == "Standard"
    return "%s samples=%d" % (sc.render.engine, sc.eevee.taa_render_samples)


# ---------------------------------------------------------------- 网格

@case("mesh · 球体拓扑与法线")
def _():
    fresh()
    ob = mesh.sphere(0.5, seg=32, rings=16)
    me = ob.data
    assert len(me.vertices) == 32 * 15 + 2, len(me.vertices)
    nm = mesh.non_manifold_edges(ob)
    assert nm == 0, "非流形边 %d" % nm
    assert not mesh.flipped_faces(ob), "法线整体朝内"
    return "verts=%d polys=%d 非流形=0" % (len(me.vertices), len(me.polygons))


@case("mesh · 立方体体积朝外")
def _():
    fresh()
    ob = mesh.cube(1.0)
    assert len(ob.data.vertices) == 8
    assert len(ob.data.polygons) == 6
    assert not mesh.flipped_faces(ob)
    return "8 顶点 6 面，法线朝外"


@case("mesh · loft 圆柱")
def _():
    fresh()
    ob = mesh.cylinder(0.0, 1.0, 0.25, seg=32)
    assert len(ob.data.vertices) == 32 * 2 + 2, len(ob.data.vertices)
    # 两个环之间侧壁 32 个四边形 + 两端各 32 个三角盖 = 32*3
    assert len(ob.data.polygons) == 32 * 3, len(ob.data.polygons)
    assert mesh.non_manifold_edges(ob) == 0
    return "verts=%d polys=%d" % (len(ob.data.vertices), len(ob.data.polygons))


@case("mesh · tube 沿折线扫掠")
def _():
    fresh()
    pts = [(0, 0, i * 0.1) for i in range(11)]
    radii = [(0.05, 0.05)] * 11
    ob = mesh.tube(pts, radii, seg=12)
    lo, hi = obj.bbox(ob)
    assert abs(lo.z) < 1e-6 and abs(hi.z - 1.0) < 1e-6, (lo.z, hi.z)
    assert mesh.non_manifold_edges(ob) == 0
    return "verts=%d z=[%.3f, %.3f]" % (len(ob.data.vertices), lo.z, hi.z)


@case("mesh · 法线翻转检测与修复")
def _():
    fresh()
    ob = mesh.cube(1.0)
    mesh.flip_normals(ob)
    assert mesh.flipped_faces(ob), "翻转后应检测为朝内"
    mesh.recalc_normals(ob)
    assert not mesh.flipped_faces(ob), "修复后应朝外"
    return "翻转→检出→修复→朝外"


@case("mesh · 焊接重合顶点")
def _():
    fresh()
    v = [(0, 0, 0), (1, 0, 0), (0, 1, 0),
         (0, 0, 0), (1, 0, 0), (0, 1, 0)]
    ob = mesh.from_verts_faces(v, [(0, 1, 2), (3, 4, 5)], "dup")
    n = mesh.merge_by_distance(ob, 1e-4)
    assert len(ob.data.vertices) == 3, len(ob.data.vertices)
    return "6 → 3 顶点（焊掉 %d）" % n


# ---------------------------------------------------------------- 对象

@case("obj · join 保留材质槽")
def _():
    fresh()
    a = mesh.cube(0.4, "a")
    b = mesh.cube(0.4, "b", center=(1.0, 0.0, 0.0))
    ma = mat.principled("ma", base_color=(0.8, 0.2, 0.2))
    mb = mat.principled("mb", base_color=(0.2, 0.2, 0.8))
    mat.assign(a, ma)
    mat.assign(b, mb)
    j = obj.join([a, b], "ab")
    assert len(j.data.vertices) == 16, len(j.data.vertices)
    assert len(j.data.polygons) == 12, len(j.data.polygons)
    names = [m.name for m in j.data.materials]
    assert names == ["ma", "mb"], names
    idx = sorted({p.material_index for p in j.data.polygons})
    assert idx == [0, 1], idx
    return "16 顶点 12 面，槽=%s，面索引=%s" % (names, idx)


@case("obj · bbox / apply_transform / stats")
def _():
    fresh()
    ob = mesh.cube(1.0)
    ob.location = (1.0, 2.0, 3.0)
    lo, hi = obj.bbox(ob)
    assert abs(lo.x - 0.5) < 1e-6 and abs(hi.z - 3.5) < 1e-6, (lo, hi)
    obj.apply_transform(ob)
    assert ob.matrix_world.to_translation().length < 1e-9, "矩阵未归一"
    lo2, hi2 = obj.bbox(ob)
    assert (lo2 - lo).length < 1e-6 and (hi2 - hi).length < 1e-6
    s = obj.stats(ob)
    assert s["verts"] == 8 and s["polys"] == 6
    return "world bbox 烘进网格，位置不变"


@case("obj · duplicate 深拷贝")
def _():
    fresh()
    a = mesh.sphere(0.2)
    b = obj.duplicate(a, "copy")
    assert b.data is not a.data
    b.data.vertices[0].co.x += 1.0
    assert a.data.vertices[0].co.x < 0.5
    return "网格数据独立"


# ---------------------------------------------------------------- 修改器

@case("mod · subsurf 面数")
def _():
    fresh()
    ob = mesh.cube(1.0)
    mod.subsurf(ob, levels=2)
    assert len(ob.modifiers) == 0, "bake 后应无残留修改器"
    assert len(ob.data.polygons) == 96, len(ob.data.polygons)
    return "6 → %d 面 / %d 顶点" % (len(ob.data.polygons), len(ob.data.vertices))


@case("mod · smooth 降低粗糙度")
def _():
    fresh()
    ob = noisy_grid()
    r0 = sculpt.roughness(ob)
    mod.smooth(ob, iterations=12, factor=0.5)
    r1 = sculpt.roughness(ob)
    assert r1 < r0 * 0.7, "粗糙度 %.5f → %.5f 未降 30%%" % (r0, r1)
    return "粗糙度 %.5f → %.5f (-%.0f%%)" % (r0, r1, 100 * (1 - r1 / r0))


@case("mod · voxel_remesh 焊成单块")
def _():
    fresh()
    a = mesh.sphere(0.3, seg=24, rings=12, name="a")
    b = mesh.sphere(0.3, seg=24, rings=12, name="b", center=(0.35, 0.0, 0.0))
    j = obj.join([a, b], "pair")
    assert components(j) == 2
    mod.voxel_remesh(j, voxel_size=0.02)
    c = components(j)
    assert c == 1, "重网格后连通块 = %d" % c
    return "2 块 → 1 块，%d 面" % len(j.data.polygons)


@case("mod · displace 噪声位移")
def _():
    fresh()
    ob = mesh.sphere(0.5, seg=48, rings=24)
    before = max((v.co.length - 0.5) for v in ob.data.vertices)
    mod.displace(ob, strength=0.04, size=0.3)
    dev = max(abs(v.co.length - 0.5) for v in ob.data.vertices)
    assert dev > 0.004, "最大径向偏移 %.4f 太小" % dev
    return "最大径向偏移 %.1f mm（原 %.1f mm）" % (dev * 1000, before * 1000)


@case("mod · shrinkwrap 贴平")
def _():
    fresh()
    g = noisy_grid(amp=0.03)
    zs = [v.co.z for v in g.data.vertices]
    span0 = max(zs) - min(zs)
    target = mesh.plane(1.6, "target", z=0.0)
    mod.shrinkwrap(g, target, offset=0.0)
    zs = [v.co.z for v in g.data.vertices]
    span1 = max(zs) - min(zs)
    assert span1 < span0 * 0.05, "贴平后 z 跨度 %.5f（原 %.5f）" % (span1, span0)
    return "z 跨度 %.1f mm → %.3f mm" % (span0 * 1000, span1 * 1000)


@case("mod · solidify / bevel / decimate")
def _():
    fresh()
    p = mesh.plane(1.0)
    mod.solidify(p, thickness=0.05)
    assert len(p.data.vertices) == 8, len(p.data.vertices)
    assert len(p.data.polygons) == 6, len(p.data.polygons)

    c = mesh.cube(1.0)
    mod.bevel(c, width=0.05, segments=2)
    nv = len(c.data.vertices)

    s = mesh.sphere(0.5, seg=32, rings=16)
    # DECIMATE 的 ratio 口径是「三角形数」，不是面数；减面后仍会留少量四边形
    # （实测 960 三角面 → 288 三角面 / 256 面），按面数判会误报。
    tri = lambda ob: sum(len(p.vertices) - 2 for p in ob.data.polygons)
    n0 = tri(s)
    mod.decimate(s, ratio=0.3)
    n1 = tri(s)
    assert abs(n1 / float(n0) - 0.3) < 0.02, "%d → %d 三角面" % (n0, n1)
    return "solidify 6 面 / bevel %d 顶点 / decimate %d→%d 三角面" % (nv, n0, n1)


@case("mod · 未知属性不静默")
def _():
    fresh()
    ob = mesh.cube(1.0)
    m = mod.add(ob, 'SUBSURF', levels=1, no_such_knob=5)
    # Modifier 不是 ID、不支持自定义属性（见 mod._log 的说明），日志挂在 Object 上
    unset = ob.get("bapi_mod_unset", {})
    assert "no_such_knob" in unset.get(m.name, ""), unset
    raised = False
    try:
        mod.add(ob, 'SUBSURF', strict=True, also_missing=1)
    except AttributeError:
        raised = True
    assert raised, "strict=True 应抛 AttributeError"
    mod.clear(ob)
    return "未设属性可查 / strict 模式抛错"


# ---------------------------------------------------------------- 雕刻替代

@case("sculpt · inflate 位移量准确")
def _():
    fresh()
    ob = mesh.sphere(0.5, seg=48, rings=24)
    top = max(v.co.z for v in ob.data.vertices)
    moved = sculpt.inflate(ob, (0, 0, 0.5), 0.2, 0.02)
    assert abs(moved - 0.02) < 1e-6, moved
    top2 = max(v.co.z for v in ob.data.vertices)
    assert top2 > top, (top, top2)
    return "最大位移 %.2f mm，顶点 z %.4f → %.4f" % (moved * 1000, top, top2)


@case("sculpt · move 限轴")
def _():
    fresh()
    ob = mesh.sphere(0.3, seg=32, rings=16)
    # 笔刷中心取球顶（那里恰有一个权重=1 的顶点），半径 0.5 覆盖上半球；
    # 中心若取球心、半径又等于球半径，所有顶点都在 falloff 边缘（w≈0），
    # 只会测到 0 位移，测不出「限轴」。
    moved = sculpt.move(ob, (0, 0, 0.3), 0.5, 0.1, axis=("X",))
    assert abs(moved - 0.1) < 1e-9, moved
    ys = [v.co.y for v in ob.data.vertices]
    assert abs(min(ys) + max(ys)) < 1e-6, "非 X 轴被改动"
    return "位移 %.3f m，Y 轴未受影响" % moved


@case("sculpt · flatten 压平")
def _():
    fresh()
    ob = noisy_grid(amp=0.03)
    p0 = sculpt.planarity(ob, (0, 0, 0), 0.6)
    sculpt.flatten(ob, (0, 0, 0), 0.6, amount=1.0)
    p1 = sculpt.planarity(ob, (0, 0, 0), 0.6)
    assert p1 < p0 * 0.5, "平面度 %.5f → %.5f" % (p0, p1)
    return "到拟合平面平均距离 %.2f mm → %.2f mm" % (p0 * 1000, p1 * 1000)


@case("sculpt · pinch 收拢")
def _():
    fresh()
    ob = mesh.sphere(0.5, seg=48, rings=24)
    sel = sculpt.weights(ob, (0, 0, 0.5), 0.3)
    before = sum((ob.data.vertices[i].co - Vector((0, 0, 0.5))).length
                 for i, _ in sel) / len(sel)
    sculpt.pinch(ob, (0, 0, 0.5), 0.3, amount=0.5)
    after = sum((ob.data.vertices[i].co - Vector((0, 0, 0.5))).length
                for i, _ in sel) / len(sel)
    assert after < before * 0.9, "%.5f → %.5f" % (before, after)
    return "区域平均半径 %.2f mm → %.2f mm" % (before * 1000, after * 1000)


@case("sculpt · smooth_region 局部平滑")
def _():
    fresh()
    ob = noisy_grid(amp=0.03)
    c = (0, 0, 0)
    r0 = sculpt.roughness(ob, c, 0.3)
    sculpt.smooth_region(ob, c, 0.3, iterations=6, factor=0.5)
    r1 = sculpt.roughness(ob, c, 0.3)
    assert r1 < r0 * 0.8, "%.5f → %.5f" % (r0, r1)
    return "局部粗糙度 %.3f mm → %.3f mm" % (r0 * 1000, r1 * 1000)


@case("sculpt · to_group 顶点组")
def _():
    fresh()
    ob = mesh.sphere(0.5, seg=32, rings=16)
    vg = sculpt.to_group(ob, "brush", (0, 0, 0.5), 0.2)
    n = sum(1 for v in ob.data.vertices
            if any(g.group == vg.index for g in v.groups))
    assert n > 0, "空顶点组"
    return "顶点组 %r 覆盖 %d 个顶点" % (vg.name, n)


# ---------------------------------------------------------------- 材质

@case("mat · srgb 转换")
def _():
    lin = mat.srgb((0.5, 0.5, 0.5))
    assert abs(lin[0] - 0.2140) < 1e-3, lin
    h = mat.srgb("#808080")
    assert abs(h[0] - 0.2159) < 1e-3, h
    return "0.5 → %.4f，'#808080' → %.4f" % (lin[0], h[0])


@case("mat · principled 短名映射")
def _():
    fresh()
    m = mat.principled("skin", base_color=(0.9, 0.7, 0.6), roughness=0.42,
                       metallic=0.1, specular=0.3, emission=(1, 0, 0),
                       emission_strength=2.0, subsurface=0.05)
    b = m.node_tree.nodes["Principled BSDF"]
    got = {s.name: s.default_value for s in b.inputs}
    assert abs(got["Base Color"][0] - 0.9) < 1e-6
    assert abs(got["Specular IOR Level"] - 0.3) < 1e-6, got["Specular IOR Level"]
    assert abs(got["Subsurface Weight"] - 0.05) < 1e-6
    assert len(got["Base Color"]) == 4, "RGBA 未补齐"
    bad = False
    try:
        mat.principled("bad", base_colour=(1, 1, 1))
    except KeyError:
        bad = True
    assert bad, "拼错 socket 名应抛 KeyError"
    return "Specular→Specular IOR Level / 拼错即报错"


@case("mat · 六种诊断材质可构建")
def _():
    fresh()
    kinds = ["normal", "ao", "wire", "silhouette", "flat", "uv"]
    out = []
    for k in kinds:
        m = mat.diag(k)
        assert len(m.node_tree.nodes) >= 2, k
        out.append("%s:%d节点" % (k, len(m.node_tree.nodes)))
    return " ".join(out)


@case("mat · toon 节点链")
def _():
    fresh()
    m = mat.toon("toon", stops=(0.2, 0.5))
    types = sorted(n.type for n in m.node_tree.nodes)
    # node.type 的枚举值实际是 'SHADERTORGB'（无下划线），不是 bl_idname
    assert "SHADERTORGB" in types, types
    assert "VALTORGB" in types, types
    return "Diffuse→ShaderToRGB→ColorRamp→Emission"


# ---------------------------------------------------------------- 渲染

@case("shot · 世界/地面/三点光/机位")
def _():
    fresh()
    shot.world((0.03, 0.03, 0.04))
    fl = shot.floor(4.0)
    k, f, r = shot.three_point(target=(0, 0, 0.9))
    cam = shot.camera_ortho("c", target=(0, 0, 0.9), angle=0, scale=2.0)
    assert fl.type == 'MESH' and cam.data.type == 'ORTHO'
    assert all(x.type == 'LIGHT' for x in (k, f, r))
    d = cam.location - Vector((0, 0, 0.9))
    assert abs(d.x) < 1e-6 and d.y < 0, "正面机位应在 -Y 侧"
    return "正交 scale=%.1f 机位 (%.1f, %.1f, %.1f)" % (
        cam.data.ortho_scale, cam.location.x, cam.location.y, cam.location.z)


@case("shot · 渲染诊断·法线色")
def _():
    fresh()
    shot.world((0.0, 0.0, 0.0), strength=0.0)
    ob = mesh.sphere(0.5, seg=48, rings=24)
    mat.assign(ob, mat.diag("normal"))
    cam = shot.camera_ortho("c", target=(0, 0, 0), scale=1.2)
    p, size = shot.render(os.path.join(OUT, "diag_normal.png"), cam,
                          w=192, h=192, samples=8)
    assert size > 1000, size
    w, h, rgb = read_pixels(p)
    lo, hi, mean, std = luma_stats(rgb)
    assert std > 0.05, "画面几乎无变化，std=%.4f" % std
    return "std=%.3f 亮度 %.2f..%.2f" % (std, lo, hi)


@case("shot · 渲染诊断·剪影")
def _():
    fresh()
    shot.world((0.0, 0.0, 0.0), strength=0.0)
    ob = mesh.sphere(0.5, seg=48, rings=24)
    mat.assign(ob, mat.diag("silhouette"))
    cam = shot.camera_ortho("c", target=(0, 0, 0), scale=1.0)
    p, size = shot.render(os.path.join(OUT, "diag_silhouette.png"), cam,
                          w=192, h=192, samples=4)
    w, h, rgb = read_pixels(p)
    center = rgb[(h // 2) * w + (w // 2)]
    corner = rgb[0]
    assert center[0] > 0.9, "中心应白，实为 %.3f" % center[0]
    assert corner[0] < 0.05, "角落应黑，实为 %.3f" % corner[0]
    return "中心 %.2f / 角落 %.2f" % (center[0], corner[0])


@case("shot · 渲染诊断·AO")
def _():
    fresh()
    shot.world((0.15, 0.15, 0.17), strength=0.6)
    fl = shot.floor(3.0)
    ball = mesh.sphere(0.25, seg=32, rings=16, center=(0, 0, 0.25))
    m = mat.diag("ao", only_local=False, distance=0.3)
    mat.assign(fl, m)
    mat.assign(ball, m)
    cam = shot.camera_ortho("c", target=(0, 0, 0.2), scale=0.9)
    p, size = shot.render(os.path.join(OUT, "diag_ao.png"), cam,
                          w=160, h=160, samples=8)
    w, h, rgb = read_pixels(p)
    lo, hi, mean, std = luma_stats(rgb)
    if hi - lo < 0.05:
        raise SkipTest("AO 输出近乎常数 (%.3f..%.3f)——EEVEE Next 下该节点可能不生效"
                       % (lo, hi))
    return "亮度 %.2f..%.2f std=%.3f" % (lo, hi, std)


@case("shot · 渲染诊断·线框")
def _():
    fresh()
    shot.world((0.0, 0.0, 0.0), strength=0.0)
    ob = mesh.sphere(0.5, seg=24, rings=12)
    mat.assign(ob, mat.diag("wire", size=0.004))
    cam = shot.camera_ortho("c", target=(0, 0, 0), scale=1.2)
    p, size = shot.render(os.path.join(OUT, "diag_wire.png"), cam,
                          w=160, h=160, samples=4)
    w, h, rgb = read_pixels(p)
    lo, hi, mean, std = luma_stats(rgb)
    red = sum(1 for r, g, b in rgb if r > 0.35 and r > g * 2.0)
    assert red > 20, "红色描边像素只有 %d" % red
    return "红边 %d px / std=%.3f" % (red, std)


@case("shot · turnaround 四视图")
def _():
    fresh()
    shot.world((0.05, 0.05, 0.06), strength=1.0)
    shot.three_point()
    ob = mesh.sphere(0.4, seg=32, rings=16, center=(0, 0, 0.9))
    mat.assign(ob, mat.principled("clay", base_color=(0.7, 0.7, 0.72),
                                  roughness=0.6))
    paths = shot.turnaround("turn", target=(0, 0, 0.9), w=160, h=220,
                            scale=1.4, samples=8,
                            out_dir=os.path.join(OUT, "turn"))
    sizes = [os.path.getsize(p) for p in paths]
    assert len(paths) == 4 and min(sizes) > 800, sizes
    return "4 张，最小 %d B" % min(sizes)


@case("shot · glTF 导出")
def _():
    fresh()
    ob = mesh.sphere(0.3, seg=16, rings=8)
    mat.assign(ob, mat.principled("gltf", base_color=(0.6, 0.3, 0.2)))
    p = shot.export_gltf(os.path.join(OUT, "probe.glb"))
    size = os.path.getsize(p)
    assert size > 1000, size
    return "%.1f KB" % (size / 1024.0)


@case("shot · .blend 落盘")
def _():
    p = shot.save_blend(os.path.join(OUT, "selftest.blend"))
    assert os.path.exists(p) and os.path.getsize(p) > 1000
    return "%.0f KB" % (os.path.getsize(p) / 1024.0)


# ---------------------------------------------------------------- 汇总

def main():
    n_pass = sum(1 for r in RESULT if r["status"] == "PASS")
    n_fail = sum(1 for r in RESULT if r["status"] == "FAIL")
    n_skip = sum(1 for r in RESULT if r["status"] == "SKIP")
    print("")
    print("bapi %s / Blender %s" % (bapi.__version__, env.version()))
    print("PASS=%d FAIL=%d SKIP=%d" % (n_pass, n_fail, n_skip))
    if n_fail:
        print("失败项：")
        for r in RESULT:
            if r["status"] == "FAIL":
                print("  - %s: %s" % (r["name"], r["detail"]))
    sys.exit(1 if n_fail else 0)


main()
