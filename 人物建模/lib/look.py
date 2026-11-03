# -*- coding: utf-8 -*-
"""原神风着色：Shader to RGB 软色阶 + 脸部法线扁平化 + 泛光。

EEVEE 专属。所有材质走同一个 toon 骨架：Diffuse → Shader to RGB →
三档 ColorRamp → 乘底色 → Emission。这样色阶是光的函数，不是贴图。
"""
import bpy
import math
from mathutils import Vector

import optio


# ---------------- A6：与 head.py 完全一致的头部坐标映射 ----------------
# head.py 不 import look.py，所以这里必须自己写一份；两处 HEAD_ANCHOR /
# HEAD_SCALE / HEAD_SHIFT 任何一个数变了，都要同步改另一个文件。
_HEAD_ANCHOR = 1.3836
_HEAD_SCALE = 1.063
_HEAD_SHIFT = -0.0127672


def _sz(z):
    """A6 之前的绝对 z → 放大后头骨上的 z（见 head.py:sz 的推导）。"""
    return _HEAD_ANCHOR + (z - _HEAD_ANCHOR) * _HEAD_SCALE + _HEAD_SHIFT


# ---------------- 可注入的像素级默认值（T18 像素段） ----------------
# 这三个是**现网正式入口的实际值**，提成模块常量只为：(a) optio.param 的默认值有据可查，
# (b) space_pixel.verify_defaults() 能在 Blender 里拿它和 DIMS 对一遍。
OUTLINE_PX = 3.5       # m3_look/m4_hair/m5_outfit/m5_rig 传的 base_px（恒定像素宽）
SKIN_POS_MID = 0.62    # skin ramp 中档切分位置（look.set_all 的 pos[1]）
SKIN_POS_LIGHT = 0.68  # skin ramp 亮档切分位置（look.set_all 的 pos[2]）

# ---------------- 手部描边世界的厚度上限（T23） ----------------
# 为什么手要单独限厚：`set_outline_px` 让壳按视图换算成「恒定像素宽」，
# 于是**世界厚度随机位变化**。全身机位 1.78/900（1.98mm/px）下 3.5px = 6.92mm/侧，
# 而手的腕口与 Body 前臂几乎同宽 —— 实测（a1 探针腕带口径 z=0.810~0.820）：
#   Body  前臂半宽 x=10.53mm / y=14.45mm   （不含壳）
#   Hands 腕口半宽 x= 8.77mm / y=14.62mm   （不含壳）
# 手的壳 6.92mm/侧 挂上去后：
#   Body  含壳 y=21.24mm / Hands 含壳 y=21.78mm → **手壳戳出前臂轮廓 +0.54mm**，
#   在腕部形成一圈横向黑带（视觉上像「手腕断了」）。
# 上限取 3.5mm/侧 的依据：
#   1) 任务给的 A1 掌宽口径 23mm vs 前臂末端 30mm，余量 7mm → 每侧 ≤3.5mm；
#   2) 手指直径约 8mm，壳 ≤ 半径 4mm 才不会被壳吞成黑棍，指缝描边仍可见；
#   3) 3.5mm 远小于前臂壳的 6.79mm/侧，手壳整体落在前臂壳轮廓之内（G1 判据）。
# 只在全身这类大 mm/px 机位生效：近景 0.16/900（0.178mm/px）下 3.5px 只有 0.62mm，
# 本来就低于上限，`min()` 不会改动它 —— 近景描边外观逐位不变。
HAND_OUTLINE_CAP = 0.0035


def _rgb(c):
    return (c[0], c[1], c[2], 1.0)


def _zone_mask(nt, x0, y0, z_lo, z_hi, x_half, y_max):
    """返回一个 0/1 的 Math socket：z∈[z_lo,z_hi] 且 |x|<x_half 且 y<y_max。

    C2 方案 B 的区域判据。全部用 Geometry.Position（世界坐标），所以头骨
    几何怎么改都不用动这段逻辑 —— 只要 z 阈值过 `_sz()`。
    """
    def _node(kind, loc):
        n = nt.nodes.new(kind)
        n.location = loc
        return n

    geo = _node("ShaderNodeNewGeometry", (x0, y0))
    sep = _node("ShaderNodeSeparateXYZ", (x0 + 150, y0))
    nt.links.new(geo.outputs["Position"], sep.inputs["Vector"])

    def _cmp(op, sock, val, loc):
        n = _node("ShaderNodeMath", loc)
        n.operation = op
        nt.links.new(sock, n.inputs[0])
        n.inputs[1].default_value = val
        return n.outputs[0]

    def _mul(a, b, loc):
        n = _node("ShaderNodeMath", loc)
        n.operation = 'MULTIPLY'
        nt.links.new(a, n.inputs[0])
        nt.links.new(b, n.inputs[1])
        return n.outputs[0]

    g_lo = _cmp('GREATER_THAN', sep.outputs["Z"], z_lo, (x0 + 300, y0))
    g_hi = _cmp('LESS_THAN', sep.outputs["Z"], z_hi, (x0 + 300, y0 - 90))
    z_ok = _mul(g_lo, g_hi, (x0 + 450, y0 - 45))
    ax = _node("ShaderNodeMath", (x0 + 300, y0 - 200))
    ax.operation = 'ABSOLUTE'
    nt.links.new(sep.outputs["X"], ax.inputs[0])
    x_ok = _cmp('LESS_THAN', ax.outputs[0], x_half, (x0 + 450, y0 - 200))
    xy_ok = _mul(z_ok, x_ok, (x0 + 600, y0 - 120))
    y_ok = _cmp('LESS_THAN', sep.outputs["Y"], y_max, (x0 + 450, y0 - 300))
    return _mul(xy_ok, y_ok, (x0 + 750, y0 - 180))


def _nose_mask(nt, x0, y0, zc, z_half, x_half, feather=0.55, y_max=-0.02):
    """鼻下**椭圆软阴影**掩码（返回 0~1 标量 socket）。

    为什么不用 `_zone_mask`：那个是硬盒（GREATER_THAN × LESS_THAN），在光滑的
    浅色脸上会渲成一个边界锐利的灰色矩形贴片 —— 2026-11-03 的实拍就是这个问题。
    这里改成径向椭圆：r = sqrt((x/x_half)^2 + ((z−zc)/z_half)^2)，r 在
    [1−feather, 1] 之间做 smoothstep 渐灭，读起来才是「鼻子底下的影」。
    """
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    geo.location = (x0, y0)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (x0 + 150, y0)
    nt.links.new(geo.outputs["Position"], sep.inputs["Vector"])

    def _m(op, loc):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        n.location = loc
        return n

    ux = _m('DIVIDE', (x0 + 300, y0))
    nt.links.new(sep.outputs["X"], ux.inputs[0])
    ux.inputs[1].default_value = x_half
    ux2 = _m('POWER', (x0 + 450, y0))
    nt.links.new(ux.outputs[0], ux2.inputs[0])
    ux2.inputs[1].default_value = 2.0

    dz = _m('SUBTRACT', (x0 + 300, y0 - 150))
    nt.links.new(sep.outputs["Z"], dz.inputs[0])
    dz.inputs[1].default_value = zc
    uz = _m('DIVIDE', (x0 + 450, y0 - 150))
    nt.links.new(dz.outputs[0], uz.inputs[0])
    uz.inputs[1].default_value = z_half
    uz2 = _m('POWER', (x0 + 600, y0 - 150))
    nt.links.new(uz.outputs[0], uz2.inputs[0])
    uz2.inputs[1].default_value = 2.0

    s = _m('ADD', (x0 + 750, y0 - 75))
    nt.links.new(ux2.outputs[0], s.inputs[0])
    nt.links.new(uz2.outputs[0], s.inputs[1])
    r = _m('SQRT', (x0 + 900, y0 - 75))
    nt.links.new(s.outputs[0], r.inputs[0])

    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.location = (x0 + 1050, y0 - 75)
    mr.interpolation_type = 'SMOOTHSTEP'
    mr.inputs["From Min"].default_value = 1.0 - feather
    mr.inputs["From Max"].default_value = 1.0
    mr.inputs["To Min"].default_value = 1.0
    mr.inputs["To Max"].default_value = 0.0
    mr.clamp = True
    nt.links.new(r.outputs[0], mr.inputs["Value"])

    y_ok = _m('LESS_THAN', (x0 + 900, y0 - 300))
    nt.links.new(sep.outputs["Y"], y_ok.inputs[0])
    y_ok.inputs[1].default_value = y_max

    out = _m('MULTIPLY', (x0 + 1200, y0 - 150))
    nt.links.new(mr.outputs["Result"], out.inputs[0])
    nt.links.new(y_ok.outputs[0], out.inputs[1])
    return out.outputs[0]


def toon(name, base, shadow, mid, light,
         pos=(0.0, 0.46, 0.74), strength=1.0, rough=0.5,
         face_bias=0.0, nose_band=None):
    """toon 骨架。

    C2 面部阴影层（DESIGN §2.4.4 方案 B，纯材质节点、不加几何）：
      - `face_bias`：整张脸的 ramp Fac 偏移（z > sz(1.38) 且 y < -0.02）。
        符号：ramp 的 light 在 pos[2]，**Fac 越大越亮**，所以「让脸更早进
        shadow」要取负值。DESIGN §2.4.4 写的 +0.15 在数学上方向是反的，
        见 set_all() 的常量注释。
      - `nose_band`：鼻下硬阴影带，dict(bias=..., z=(lo,hi), x_half=...)。
        这是 DESIGN 「辅：鼻底 3~5mm 硬阴影带」的**材质实现**（不是贴片），
        因为本轮没有 head.py 权限；效果等价于解剖固定的方向光阴影。
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (900, 0)
    diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
    diff.location = (-200, 0)
    diff.inputs["Color"].default_value = (1, 1, 1, 1)
    diff.inputs["Roughness"].default_value = rough
    s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    s2rgb.location = (30, 0)
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    bw.location = (220, 0)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (400, 0)
    cr = ramp.color_ramp
    cr.interpolation = 'EASE'
    cr.elements[0].position = pos[0]
    cr.elements[0].color = _rgb(shadow)
    cr.elements[1].position = pos[2]
    cr.elements[1].color = _rgb(light)
    e = cr.elements.new(pos[1])
    e.color = _rgb(mid)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    mix.blend_type = 'MULTIPLY'
    mix.location = (620, 0)
    mix.inputs["Factor"].default_value = 1.0
    mix.inputs[6].default_value = _rgb(base)
    em = nt.nodes.new("ShaderNodeEmission")
    em.location = (760, 0)
    em.inputs["Strength"].default_value = strength

    fac_socket = bw.outputs["Val"]
    zones = []
    if face_bias != 0.0:
        zones.append((_zone_mask(nt, -700, -260, _sz(1.38), 9.0, 9.0, -0.02),
                      face_bias))
    if nose_band:
        zones.append((_nose_mask(nt, -700, -520, nose_band["zc"],
                                 nose_band["z_half"], nose_band["x_half"],
                                 feather=nose_band.get("feather", 0.55)),
                      nose_band["bias"]))
    if zones:
        loc_y = -100
        for mask, bias in zones:
            m = nt.nodes.new("ShaderNodeMath")
            m.operation = 'MULTIPLY'
            m.name = "ZoneBias"
            m.location = (60, loc_y)
            nt.links.new(mask, m.inputs[0])
            m.inputs[1].default_value = bias
            a = nt.nodes.new("ShaderNodeMath")
            a.operation = 'ADD'
            a.location = (220, loc_y + 40)
            nt.links.new(fac_socket, a.inputs[0])
            nt.links.new(m.outputs[0], a.inputs[1])
            fac_socket = a.outputs[0]
            loc_y -= 160

    l = nt.links
    l.new(diff.outputs["BSDF"], s2rgb.inputs["Shader"])
    l.new(s2rgb.outputs["Color"], bw.inputs["Color"])
    l.new(fac_socket, ramp.inputs["Fac"])
    l.new(ramp.outputs["Color"], mix.inputs[7])
    l.new(mix.outputs[2], em.inputs["Color"])
    l.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


def flat(name, color, strength=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = _rgb(color)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


# ---------------- C1：描边（Solidify 反法线外壳 + 背面剔除） ----------------

def outline_mat(name="outline", color=(0.005, 0.005, 0.005)):
    """描边材质：纯黑 Emission + 背面剔除。

    颜色取**线性 0.005** 而不是 DESIGN 里写的 0.02：0.02 经 Standard 视图
    变换编码出来是 sRGB≈41，正好落在验收判据「亮度 <40」的上方 —— 实测
    球体扫描线判据恒为 0。0.005 → sRGB≈15，给抗锯齿混色留余量。
    """
    mat = flat(name, color, strength=1.0)
    mat.use_backface_culling = True
    try:
        mat.use_backface_culling_shadow = True
    except AttributeError:
        pass
    return mat


def add_outline(ob, mat, thickness=0.005, thickness_cap=None):
    """给对象挂一层「反法线外扩壳」，壳面指到描边材质槽。

    参数是实测出来的，**不是 DESIGN §2.4.3 的字面值**（实测记录见
    `_stageC/c_probe.py` 的注释）：
      - `offset=+1`（DESIGN 写 -1）：offset=-1 时壳朝内长，完全被本体挡住，
        球体扫描线实测暗带 **0px**；offset=+1 才有轮廓线。
      - `use_flip_normals=True` + 材质 `use_backface_culling=True` 才能
        只留下轮廓一圈；flip=False + cull=False 时外壳正面遮挡本体 → 整对象
        变黑（实测中心亮度 194→39）。
      - 厚度：球体 240px/0.5m（2.08mm/px）下 5mm→1px、8mm→3px、10mm→4px。
        宽度与厚度近似线性但比理论少约 1px（背面剔除吃掉了抗锯齿边缘）。

    `thickness_cap`（T23）：这层壳**世界厚度**的上限（米/侧）。只在该对象
    需要「不戳出邻居轮廓」时给值（目前只有 Hands 给 HAND_OUTLINE_CAP）。
    这里做一次 min 只是兜底 —— 真正生效的点在 `set_outline_px()`：按视图
    换算后的厚度还会再被 cap 截一次（否则后续 set_outline_px 会把它顶回去）。
    """
    if thickness_cap is not None:
        thickness = min(float(thickness), float(thickness_cap))
    m = ob.modifiers.new("Outline", 'SOLIDIFY')
    m.thickness = thickness
    m.offset = 1.0
    m.use_flip_normals = True
    m.use_rim = False
    try:
        m.use_quality_normals = True
    except (AttributeError, TypeError):
        pass
    slots = [s.name for s in ob.data.materials if s is not None]
    if mat.name not in slots:
        ob.data.materials.append(mat)
    # 新生成的外壳面走 material_offset，指向最后那个槽位（描边）
    m.material_offset = len(ob.data.materials) - 1
    return m


def set_outline_px(objs, mods, ortho_scale, res_y, base_px=3.0, per_obj_px=None,
                   per_obj_cap=None):
    """按视图把描边厚度换算成「恒定像素宽」。

    方案 A 的厚度是世界单位（米），同一 thickness 在不同 ortho_scale 下的
    像素宽会差好几倍：0.008m 在 560×900 / ortho 1.78 上是 3px，在
    620×780 / ortho 0.30 的脸部特写上变成 **20px** —— 脸会被一圈粗黑框死。
    所以按每个视图的 mm/px 反算 thickness，让所有机位的线宽一致。

    `per_obj_cap`（T23）：{对象名: 世界厚度上限(米/侧)}，换算完再 min 一次。
    「恒定像素宽」的代价就是世界厚度随机位漂移 —— 全身机位 3.5px=6.92mm，
    近景 3.5px=0.62mm。手与前臂几乎同宽，只在误差小的机位需要限厚，
    所以按对象给 cap，而不是把 px 调小（调小会让近景的手也没描边）。
    """
    # 参数注入（T18 像素段）：outline_px 覆盖调用方给的 base_px，
    # 默认值仍是调用方传进来的值 —— 没有 opt/best.json 时行为逐位不变。
    # per_obj_px（m3_look 的 Head=3.5）按同一比例缩放，保留「头比身体略粗」的相对关系。
    if base_px is None:
        base_px = OUTLINE_PX
    px_base = optio.param("outline_px", float(base_px))
    if base_px:
        k = px_base / float(base_px)
    else:
        k = 1.0
    mm_per_px = ortho_scale / float(res_y)
    for ob, m in zip(objs, mods):
        px = base_px
        if per_obj_px:
            px = per_obj_px.get(ob.name, base_px)
        th = px * k * mm_per_px
        if per_obj_cap:
            cap = per_obj_cap.get(ob.name)
            if cap is not None:
                th = min(th, float(cap))
        m.thickness = th


def bind_hands(mats):
    """把 body.build() 里建出的 "Hands" 从占位 Principled 换成 toon 皮肤。

    C2 硬要求：Hands 原先用 hand.py 的 `hand_skin_placeholder`（Principled，
    不经过 toon 色阶），导致同一张图里手与前臂/脸是两种皮肤色（实测
    m5_body_front 手−脸亮度差 17.9 / 9.6）。这里把它接进 `set_all()` 的
    材质表，和 Body/Head 走完全相同的 skin 材质。

    手不需要 flatten_face（那是脸部法线压平专用），也不需要描边以外的处理。
    """
    ob = bpy.data.objects.get("Hands")
    if ob is None:
        return False
    ob.data.materials.clear()
    ob.data.materials.append(mats["skin"])
    return True


def set_all():
    # C2 面部阴影层（方案 B，DESIGN §2.4.4）：脸区 Fac 整体偏移。
    # 符号：ramp 的 shadow 在 pos[0]=0.0、light 在 pos[2]=0.62，所以
    # **Fac 越大越往 light 端走**。DESIGN §2.4.4 写的「+0.15 让脸更早进
    # shadow」在数学上是反的 —— 真正的「更早进 shadow」要减小 Fac。
    # 实测 -0.15：shadow 档占比 9.1%→11.8%、light 82.5%→77.7%。
    FACE_BIAS = -0.15
    # 鼻下硬阴影带（DESIGN 的「辅」项，本轮用材质节点实现，不动 head.py）。
    # 原始口径 z 1.437~1.452（鼻底内收 1.446 下方 3~5mm），过 _sz 映射。
    # 鼻下阴影：2026-11-03 由硬盒（z 区间 + x 半宽，边界零衰减）改为椭圆软衰减。
    # 原实现 bias=-0.60 在浅色脸上渲成一块边界锐利的灰色矩形；现取 -0.32 + 径向渐灭，
    # 读作「鼻底下的影」而不是「贴上去的灰方块」。中心 z 取原区间中点。
    NOSE_BAND = dict(zc=_sz(1.4445), z_half=0.0075, x_half=0.011,
                     feather=0.60, bias=-0.32)
    # C3 色阶重标定：ramp 切分位置 (0.0, 0.35, 0.62) → (0.0, 0.55, 0.85)。
    # 色值本身不动（mid−shadow 26.3%、light−mid 17.7% 都合格），只让 mid 档
    # 吃到的像素变多。配合 shots.KEY_ENERGY 70→49W 一起作用。
    # shadow 乘数 (0.58,0.55,0.72) → (0.50,0.47,0.64)：三档显示亮度从
    # 182.2/208.5/227.7（跨度 45.5）扩到 ~170/208.5/227.7（跨度 57.6）。
    # 必须扩：C3 要求 p95−p50≥30 **且** p50−p5≥25，两者相加需要总跨度 ≥55，
    # 而原跨度只有 45.5 —— 不改 shadow 这一档，两个阈值在数学上不可能同时满足。
    # 方向仍是「让 mid−shadow 更大」，符合 DESIGN §1.6 的 ≥15% 规范（现 30.2%）。
    # T18 像素段：skin ramp 的中/亮两档切分位置可注入（默认 0.62 / 0.68 = 现网值）。
    # 三档位置必须严格递增（0 < mid < light），否则 ColorRamp 的元素顺序会乱。
    mid_pos = optio.param("skin_pos_mid", SKIN_POS_MID)
    light_pos = optio.param("skin_pos_light", SKIN_POS_LIGHT)
    # round 到 1e-6 再比较：0.68+0.02 在二进制下是 0.7000000000000001，
    # 直接把 0.7 顶上去会让「记录的参数」与「生效的参数」差 1e-16（归因时看不出，但很脏）。
    mid_pos = round(max(0.02, min(0.96, mid_pos)), 6)
    light_pos = round(max(mid_pos + 0.02, min(0.99, light_pos)), 6)
    if light_pos < mid_pos + 0.02 - 1e-9:
        light_pos = round(mid_pos + 0.02, 6)
    skin = toon("skin", (0.96, 0.80, 0.72),
                shadow=(0.485, 0.455, 0.625), mid=(0.752, 0.647, 0.664),
                light=(0.97, 0.93, 0.88), pos=(0.0, mid_pos, light_pos),
                face_bias=FACE_BIAS, nose_band=NOSE_BAND)
    return {
        "skin": skin,
        "sclera": toon("sclera", (0.98, 0.97, 0.98),
                       shadow=(0.60, 0.64, 0.78), mid=(0.88, 0.89, 0.93),
                       light=(1.0, 1.0, 1.0), pos=(0.0, 0.3, 0.55)),
        "iris": toon("iris", (0.93, 0.55, 0.10),
                     shadow=(0.32, 0.11, 0.02), mid=(0.80, 0.35, 0.03),
                     light=(1.0, 0.72, 0.22), pos=(0.02, 0.45, 0.70),
                     strength=1.15),
        "iris_dark": flat("iris_dark", (0.22, 0.08, 0.02)),
        "pupil": flat("pupil", (0.02, 0.015, 0.02)),
        "white_emit": flat("white_emit", (1, 1, 1), strength=2.4),
        "lash": flat("lash", (0.10, 0.06, 0.09)),
        "lash_soft": flat("lash_soft", (0.34, 0.16, 0.17)),
        "brow": flat("brow", (0.24, 0.13, 0.10)),
        "lip": toon("lip", (0.98, 0.44, 0.42),
                    shadow=(0.55, 0.16, 0.20), mid=(0.90, 0.34, 0.34),
                    light=(1.0, 0.62, 0.60), pos=(0.0, 0.4, 0.7)),
        "hair": hair_material(),
        "cloth_white": toon("cloth_white", (0.93, 0.93, 0.95),
                            shadow=(0.60, 0.63, 0.77), mid=(0.85, 0.86, 0.91),
                            light=(1.0, 1.0, 1.0), pos=(0.0, 0.34, 0.60)),
        "cloth_navy": toon("cloth_navy", (0.072, 0.105, 0.260),
                           shadow=(0.025, 0.040, 0.115), mid=(0.060, 0.090, 0.225),
                           light=(0.145, 0.205, 0.410), pos=(0.0, 0.30, 0.58)),
    }


def hair_material(name="hair",
                  base=(0.115, 0.088, 0.105),
                  shadow=(0.055, 0.050, 0.090),
                  mid=(0.190, 0.150, 0.200),
                  light=(0.430, 0.360, 0.395),
                  ring=(0.060, 0.055, 0.075)):
    """深棕黑发 + 天使环：在 z≈1.54 / 1.34 两道横向高光带。"""
    mat = toon(name, base, shadow=shadow, mid=mid, light=light,
               pos=(0.0, 0.34, 0.62), strength=1.0)
    nt = mat.node_tree
    links = nt.links
    em = nt.nodes["Emission"]

    geo = nt.nodes.new("ShaderNodeNewGeometry")
    geo.location = (-600, -320)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-420, -320)
    links.new(geo.outputs["Position"], sep.inputs["Vector"])

    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.location = (-240, -320)
    mr.inputs["From Min"].default_value = 0.95
    mr.inputs["From Max"].default_value = 1.66
    mr.inputs["To Min"].default_value = 0.0
    mr.inputs["To Max"].default_value = 1.0
    links.new(sep.outputs["Z"], mr.inputs["Value"])

    band = nt.nodes.new("ShaderNodeValToRGB")
    band.location = (-60, -320)
    band.color_ramp.interpolation = 'EASE'
    cr = band.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0, 0, 0, 1)
    # C4：MapRange 0.95→1.66 ⇒ p = (z − 0.95)/0.71。
    # ---- 2026-11-03 重标定：环带位置随 6.5 头身重算 ----
    # 旧值 0.803/0.845/0.858/0.915 → z 1.520/1.550/1.559/1.600，是**A 阶段把整个人头
    # 绕 z=1.5857 放大 1.0631 并下移 12.7672mm 之前**定的。头骨下移后这两条带没跟着
    # 重算，于是整块落到了刘海（世界 z 1.512~1.588）上 —— 正面渲成一条白纸带。
    # 现按「颅顶前五分之一」重算：头顶 1.6200、下巴 1.3710，前五分之一 = z 1.570~1.620；
    # 带放 1.594~1.610 与 1.618~1.632，正好在刘海顶端（1.588）之上、颅顶壳上。
    #   带1 [0.907, 0.930] → z 1.594~1.610
    #   带2 [0.941, 0.961] → z 1.618~1.632
    # 单环 + EASE 软边：z 1.598~1.616（p 0.913~0.938）。
    # 两条硬边厚带（1.594~1.610 + 1.618~1.632，CONSTANT）实测在正面渲成一整条白护额，
    # 改成单条 + 软边 + 降亮后才是「头顶的一道光」。环色默认值同时从
    # (0.640,0.560,0.820) 降到 (0.340,0.290,0.420)：ADD 是加在近黑的发色（≈0.05）上，
    # 加 0.64 直接到 0.69 线性（sRGB≈215），必然烧白。
    # 单环 + 软边：0.905 黑 → 0.925 白 → 0.945 黑（z 1.593~1.621，峰在 1.607）。
    # **必须在环起点前再放一个黑元素**：ColorRamp 的 EASE 只在相邻两元素之间插值，
    # 若只有「0.0 黑 → 0.913 白」，整段 z 0.95~1.60 都会被插成渐变，渲出来是
    # 头顶一大片灰白雾（2026-11-03 实测踩过，见 out/m4_face_front.png 的中间版本）。
    cr.elements[1].position = 0.910
    cr.elements[1].color = (0, 0, 0, 1)
    e1 = cr.elements.new(0.924)
    e1.color = (1, 1, 1, 1)
    e2 = cr.elements.new(0.938)
    e2.color = (0, 0, 0, 1)
    links.new(mr.outputs["Result"], band.inputs["Fac"])

    # ---- 天使环的**位置**遮罩（2026-11-03）----
    # 原实现只按 z 分带，而刘海整块落在 z 1.512~1.588 里，于是刘海正面也吃到 ADD
    # 环色，渲成一条发白的纸带/护额（out/m5_face_front.png 实拍）。
    # 为什么不用表面法线：纯绿环实测（out/_test_ring_green.png）显示刘海可见面的
    # 法线 +Z 分量 >0.55，法线遮罩对它们等于全放行 —— 这批 strand 的法线不能用。
    # 所以改成位置判据：**y<−0.02（脸前）且 z<1.592（低于颅顶环）的地方不叠环色**，
    # 颅顶那一圈（z>1.598）与后脑（y>−0.01）照常保留。
    yf = nt.nodes.new("ShaderNodeMapRange")
    yf.location = (-420, -700)
    yf.interpolation_type = 'SMOOTHSTEP'
    yf.inputs["From Min"].default_value = -0.040
    yf.inputs["From Max"].default_value = -0.010
    yf.inputs["To Min"].default_value = 1.0
    yf.inputs["To Max"].default_value = 0.0
    yf.clamp = True
    links.new(sep.outputs["Y"], yf.inputs["Value"])

    zl = nt.nodes.new("ShaderNodeMapRange")
    zl.location = (-240, -700)
    zl.interpolation_type = 'SMOOTHSTEP'
    zl.inputs["From Min"].default_value = 1.584
    zl.inputs["From Max"].default_value = 1.590
    zl.inputs["To Min"].default_value = 1.0
    zl.inputs["To Max"].default_value = 0.0
    zl.clamp = True
    links.new(sep.outputs["Z"], zl.inputs["Value"])

    blk = nt.nodes.new("ShaderNodeMath")
    blk.operation = 'MULTIPLY'
    blk.location = (-60, -700)
    links.new(yf.outputs["Result"], blk.inputs[0])
    links.new(zl.outputs["Result"], blk.inputs[1])

    nmask = nt.nodes.new("ShaderNodeMath")
    nmask.operation = 'SUBTRACT'
    nmask.location = (120, -700)
    nmask.inputs[0].default_value = 1.0
    links.new(blk.outputs[0], nmask.inputs[1])

    b_bw = nt.nodes.new("ShaderNodeRGBToBW")
    b_bw.location = (120, -320)
    links.new(band.outputs["Color"], b_bw.inputs["Color"])
    fac = nt.nodes.new("ShaderNodeMath")
    fac.operation = 'MULTIPLY'
    fac.location = (300, -420)
    links.new(b_bw.outputs["Val"], fac.inputs[0])
    links.new(nmask.outputs[0], fac.inputs[1])

    add = nt.nodes.new("ShaderNodeMix")
    add.data_type = 'RGBA'
    add.blend_type = 'ADD'
    add.location = (760, -120)
    add.inputs["Factor"].default_value = 1.0
    add.inputs[7].default_value = _rgb(ring)
    src = em.inputs["Color"].links[0].from_socket
    links.new(src, add.inputs[6])
    links.new(fac.outputs[0], add.inputs["Factor"])
    links.new(add.outputs[2], em.inputs["Color"])
    return mat


def flatten_face(ob, x_half=0.078, z0=(1.398, 1.425), z1=(1.575, 1.600),
                 y_front=-0.020, blend=0.028):
    """把脸前半部法线压向 -Y：原神脸没有硬明暗线的关键。

    入参一律用「A6 之前」的原始坐标；函数内部统一过 _sz() 映射到头骨放大后
    的位置。这样调用方不需要知道头部缩放，缩放参数改动只需要同步本文件与
    head.py 两处（head.py 不 import look.py，所以不能共用一份）。
    """
    z0 = (_sz(z0[0]), _sz(z0[1]))
    z1 = (_sz(z1[0]), _sz(z1[1]))
    x_half = x_half * _HEAD_SCALE
    y_front = y_front * _HEAD_SCALE
    blend = blend * _HEAD_SCALE
    nose_z = _sz(1.456)

    me = ob.data
    me.calc_loop_triangles()
    normals = []
    target = Vector((0.0, -1.0, 0.0))
    for v in me.vertices:
        x, y, z = v.co
        wy = max(0.0, min(1.0, (-y - y_front) / blend))
        wx = 1.0 - _smooth(abs(x) / x_half)
        wz = _smooth((z - z0[0]) / (z0[1] - z0[0])) * \
             (1.0 - _smooth((z - z1[0]) / (z1[1] - z1[0])))
        w = wy * wx * wz
        # 鼻梁/鼻头保留原始法线，否则前脸一压平，鼻子就从画面上消失。
        # A2：保护带 x/0.013→0.008、z/0.016→0.010，系数 0.88→0.75。
        # 原来的 0.013×0.016 覆盖约 26×32mm 的整个面中，等于「面中保留原法线、
        # 四周压平」，明暗交界正好落在保护带边缘 → 一条硬边，鼻子反而不可读。
        # 收窄到 16×20mm 后，交界跑到鼻梁侧面，鼻子才有连续的明暗过渡。
        nose = math.exp(-((x / 0.008) ** 2 + ((z - nose_z) / 0.010) ** 2))
        w *= 1.0 - 0.75 * nose
        if wy <= 0.0 or wz <= 0.0:
            normals.append(v.normal.copy())
            continue
        n = v.normal.lerp(target, min(1.0, w))
        normals.append(n.normalized())
    for p in me.polygons:
        p.use_smooth = True
    try:
        me.normals_split_custom_set_from_vertices(normals)
    except Exception as exc:
        print("[flatten] skipped:", exc)


def _smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def bloom(threshold=0.9, size=7, mix=0.0):
    sc = bpy.context.scene
    try:
        if hasattr(sc, "compositing_node_group"):
            ng = sc.compositing_node_group
            if ng is None:
                ng = bpy.data.node_groups.new("Compositing", "CompositorNodeTree")
                sc.compositing_node_group = ng
            if not any(s.name == "Image" for s in ng.interface.items_tree):
                ng.interface.new_socket("Image", in_out='OUTPUT',
                                        socket_type='NodeSocketColor')
            nodes = ng.nodes
            rl = nodes.get("Render Layers") or nodes.new("CompositorNodeRLayers")
            rl.scene = sc
            glare = nodes.get("Glare") or nodes.new("CompositorNodeGlare")
        else:
            sc.use_nodes = True
            nt = sc.node_tree
            rl = nt.nodes.get("Render Layers")
            glare = nt.nodes.get("Glare") or nt.nodes.new("CompositorNodeGlare")
            nt.nodes.get("Composite")
            nt.links.new(glare.outputs["Image"], nt.nodes["Composite"].inputs["Image"])

        if hasattr(glare, "glare_type"):
            for kind in ("BLOOM", "FOG_GLOW"):
                try:
                    glare.glare_type = kind
                    break
                except TypeError:
                    continue
            glare.quality = 'HIGH'
            glare.threshold = threshold
            glare.size = size
            glare.mix = mix
        else:
            glare.inputs["Type"].default_value = "Bloom"
            glare.inputs["Quality"].default_value = "High"
            glare.inputs["Threshold"].default_value = threshold
            glare.inputs["Size"].default_value = min(1.0, size / 10.0)
            glare.inputs["Strength"].default_value = 0.35

        if hasattr(sc, "compositing_node_group"):
            out = ng.nodes.get("Group Output") or ng.nodes.new("NodeGroupOutput")
            ng.links.new(rl.outputs["Image"], glare.inputs["Image"])
            ng.links.new(glare.outputs["Image"], out.inputs[0])
        else:
            nt.links.new(rl.outputs["Image"], glare.inputs["Image"])
        return True
    except Exception as exc:
        print("[bloom] skipped:", exc)
        return False