# -*- coding: utf-8 -*-
"""bapi · 材质层：Principled 快捷构造、色彩空间、诊断材质、三渲二。

命名映射的意义：Principled 的 socket 名在 4.0 之后改过一轮
（`Subsurface` → `Subsurface Weight`、`Specular` → `Specular IOR Level`、
`Emission` → `Emission Color`）。这里用「短名」做键，写脚本时不用记版本。

传入未知键会**抛错**而不是静默忽略——写错 socket 名是最难查的 bug 之一。
"""

import bpy


# 短名 → 5.2 实际 socket 名
ALIASES = {
    "color": "Base Color",
    "base_color": "Base Color",
    "base": "Base Color",
    "roughness": "Roughness",
    "rough": "Roughness",
    "metallic": "Metallic",
    "metal": "Metallic",
    "ior": "IOR",
    "alpha": "Alpha",
    "specular": "Specular IOR Level",
    "specular_ior_level": "Specular IOR Level",
    "specular_tint": "Specular Tint",
    "emission": "Emission Color",
    "emission_color": "Emission Color",
    "emission_strength": "Emission Strength",
    "subsurface": "Subsurface Weight",
    "subsurface_weight": "Subsurface Weight",
    "subsurface_radius": "Subsurface Radius",
    "subsurface_scale": "Subsurface Scale",
    "coat": "Coat Weight",
    "coat_roughness": "Coat Roughness",
    "sheen": "Sheen Weight",
    "sheen_tint": "Sheen Tint",
    "transmission": "Transmission Weight",
    "anisotropic": "Anisotropic",
    "normal": "Normal",
}


# ---------------------------------------------------------------- 颜色

def srgb(c):
    """把 sRGB 颜色转成 Blender 的线性值。

    接受 '#2b1d16' / '2b1d16' / (43, 29, 22) / (0.17, 0.11, 0.09)。
    元组里任一分量 > 1 就当作 0-255。

    为什么需要它：调色板里的十六进制是 sRGB 编码的，直接塞进
    Base Color 会偏亮偏灰——这是二次元配色最常见的「脏」的来源。
    """
    if isinstance(c, str):
        s = c.lstrip("#")
        if len(s) == 3:
            s = "".join(ch * 2 for ch in s)
        if len(s) != 6:
            raise ValueError("srgb: 需要 3 或 6 位十六进制，收到 %r" % c)
        vals = [int(s[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    else:
        vals = list(c)[:3]
        if max(vals) > 1.0:
            vals = [v / 255.0 for v in vals]

    out = []
    for v in vals:
        out.append(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
    return tuple(out)


# ---------------------------------------------------------------- 基础

def new(name="mat", use_nodes=True):
    m = bpy.data.materials.new(name)
    m.use_nodes = use_nodes
    return m


def socket_set(sock, value):
    """给 socket 赋值，自动补齐 RGBA 的第四个分量。"""
    if sock.type == 'RGBA' and isinstance(value, (tuple, list)) and len(value) == 3:
        value = (value[0], value[1], value[2], 1.0)
    sock.default_value = value
    return sock


def emit(nt, color=(1.0, 1.0, 1.0), strength=1.0):
    """纯自发光节点链：不受灯光影响，颜色即所见（诊断渲染用）。"""
    out = nt.nodes.get("Material Output") or nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    socket_set(em.inputs["Color"], color)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return em


def principled(name="mat", **kw):
    """建一个 Principled 材质。键用短名（见 ALIASES）。

        principled("skin", base_color=srgb("#f6d7c4"), roughness=0.55)

    未知键会抛 KeyError 并列出全部可用输入——故意做成响的，
    因为 socket 写错时 Blender 本身不会报错，只会静默用默认值。
    """
    m = new(name)
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = nt.nodes.get("Material Output") or nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    valid = {s.name for s in bsdf.inputs}
    for key, value in kw.items():
        target = ALIASES.get(key, key)
        if target not in valid:
            raise KeyError("principled: 未知输入 %r（解析为 %r）。可用：%s"
                           % (key, target, sorted(valid)))
        if target == "Normal":
            continue                      # Normal 是连线口，不设常量
        socket_set(bsdf.inputs[target], value)
    return m


def diffuse(name="mat", color=(0.8, 0.8, 0.8), roughness=0.5):
    """不透明的基础漫反射（clay 风格），给造型阶段看体积用。"""
    return principled(name, base_color=color, roughness=roughness, metallic=0.0)


def assign(ob, mat, slot=None):
    """把材质放进对象的某个槽；槽位不足时追加。"""
    me = ob.data
    if slot is None:
        if not me.materials:
            me.materials.append(mat)
        else:
            me.materials[0] = mat
        return mat
    while len(me.materials) <= slot:
        me.materials.append(None)
    me.materials[slot] = mat
    return mat


# ---------------------------------------------------------------- 诊断材质

def diag(kind="normal", **kw):
    """诊断渲染材质。全部是自发光，不受灯光影响。

    kind:
      normal      法线 xyz → RGB（曲面瑕疵会变成刺眼杂色）
      ao          环境光遮蔽（灰阶，看凹陷/自交/并集残留）
      wire        灰底 + 红边（看拓扑密度与长条面）
      silhouette  纯白（配黑世界出剪影）
      flat        纯色自发光（看形状不看明暗）
      uv          UV 坐标当颜色（看 UV 展平是否合理）

    这些材质是「让 AI 看见瑕疵」的核心工具：软光下看着正常的曲面，
    在 normal 里会直接裂开。
    """
    m = new("diag_" + kind)
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)

    if kind == "normal":
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        vmath = nt.nodes.new("ShaderNodeVectorMath")
        vmath.operation = 'MULTIPLY_ADD'
        vmath.inputs[1].default_value = (0.5, 0.5, 0.5)
        vmath.inputs[2].default_value = (0.5, 0.5, 0.5)
        nt.links.new(geo.outputs["Normal"], vmath.inputs[0])
        em = emit(nt)
        nt.links.new(vmath.outputs["Vector"], em.inputs["Color"])

    elif kind == "ao":
        ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
        ao.inputs["Distance"].default_value = kw.get("distance", 0.2)
        ao.samples = kw.get("samples", 16)
        ao.only_local = kw.get("only_local", True)
        em = emit(nt)
        socket_set(em.inputs["Color"], kw.get("color", (1.0, 1.0, 1.0)))
        # Emission 的 Strength 接 AO：黑的地方暗，缝里最暗
        nt.links.new(ao.outputs["AO"], em.inputs["Strength"])

    elif kind == "wire":
        wf = nt.nodes.new("ShaderNodeWireframe")
        wf.use_pixel_size = kw.get("pixel_size", False)
        wf.inputs["Size"].default_value = kw.get("size", 0.002)
        mix = nt.nodes.new("ShaderNodeMixRGB")
        mix.blend_type = 'MIX'
        socket_set(mix.inputs["Color1"], kw.get("base", (0.55, 0.55, 0.55)))
        socket_set(mix.inputs["Color2"], kw.get("line", (1.0, 0.15, 0.1)))
        nt.links.new(wf.outputs["Factor"], mix.inputs["Factor"])
        em = emit(nt)
        nt.links.new(mix.outputs["Color"], em.inputs["Color"])

    elif kind == "silhouette":
        emit(nt, kw.get("color", (1.0, 1.0, 1.0)))

    elif kind == "flat":
        emit(nt, kw.get("color", (0.8, 0.8, 0.8)))

    elif kind == "uv":
        uvn = nt.nodes.new("ShaderNodeUVMap")
        split = nt.nodes.new("ShaderNodeSeparateXYZ")
        comb = nt.nodes.new("ShaderNodeCombineXYZ")
        nt.links.new(uvn.outputs["UV"], split.inputs["Vector"])
        nt.links.new(split.outputs["X"], comb.inputs["X"])
        nt.links.new(split.outputs["Y"], comb.inputs["Y"])
        em = emit(nt)
        nt.links.new(comb.outputs["Vector"], em.inputs["Color"])

    else:
        raise ValueError("diag: 未知类型 %r（normal/ao/wire/silhouette/flat/uv）" % kind)

    return m


# ---------------------------------------------------------------- 三渲二

def toon(name="toon", light=(1.0, 0.85, 0.75), mid=(0.7, 0.5, 0.45),
         dark=(0.35, 0.22, 0.22), stops=(0.15, 0.45), smooth=0.02):
    """三段式卡通渐变：Diffuse → Shader to RGB → ColorRamp → Emission。

    **只在 EEVEE 有效**：Cycles 下 Shader to RGB 恒为黑（这是引擎约束，
    不是参数问题）。本机 5.2 的引擎枚举只有 BLENDER_EEVEE，所以没问题。

    stops 是两段分界（亮度），介于其间做 smooth 宽的软过渡以减轻锯齿。
    这就是「原神风」里最省事的一层：明暗是离散的，不是连续渐变的。
    """
    m = new(name)
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)

    diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
    socket_set(diff.inputs["Color"], (1.0, 1.0, 1.0))
    s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    em = emit(nt)

    nt.links.new(diff.outputs["BSDF"], s2rgb.inputs["Shader"])
    nt.links.new(s2rgb.outputs["Color"], ramp.inputs["Factor"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])

    cr = ramp.color_ramp
    cr.interpolation = 'B_SPLINE'
    cr.elements[0].position = 0.0
    cr.elements[0].color = (dark[0], dark[1], dark[2], 1.0)
    cr.elements[1].position = max(stops[1], 0.99)
    cr.elements[1].color = (light[0], light[1], light[2], 1.0)
    e = cr.elements.new(stops[0])
    e.color = (mid[0], mid[1], mid[2], 1.0)

    # 软过渡：把每个停靠点两侧做一点羽化，避免硬边锯齿
    if smooth > 0:
        cr.interpolation = 'EASE'
    return m


def outline(name="outline", color=(0.02, 0.02, 0.03)):
    """反向外壳描边材质。

    用法：复制一份网格 → `mod.solidify(thickness=-0.002)` 并 flip normals →
    本材质 + `use_backface_culling=True`。只在 EEVEE 下有效。

    注意：这是「硬描边」。用户明确不要赛璐璐硬描边时，改用轮廓光
    （Fresnel 驱动的 Emission 边缘）会更接近原神的柔边。
    """
    m = new(name)
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    emit(nt, color)
    m.use_backface_culling = True
    m.use_backface_culling_shadow = True
    return m


def rim_light(name="rim", color=(1.0, 0.95, 0.85), power=1.0, fresnel=2.0):
    """轮廓光（Fresnel 驱动的自发光边缘），比反向外壳柔和。

    接在原材质上：把返回的节点组当 Emission 追加。这里直接做成独立材质，
    方便叠一层薄壳或单独给头发用。
    """
    m = new(name)
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.5
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = 'POWER'
    pw.inputs[1].default_value = fresnel
    mult = nt.nodes.new("ShaderNodeMath")
    mult.operation = 'MULTIPLY'
    mult.inputs[1].default_value = power
    em = emit(nt)
    socket_set(em.inputs["Color"], color)
    nt.links.new(lw.outputs["Facing"], pw.inputs[0])
    nt.links.new(pw.outputs["Value"], mult.inputs[0])
    nt.links.new(mult.outputs["Value"], em.inputs["Strength"])
    return m
