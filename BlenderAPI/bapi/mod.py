# -*- coding: utf-8 -*-
"""bapi · 修改器层：加修改器、烘焙进网格、常用形变。

核心是 `bake()`——用 `evaluated_get()` + `meshes.new_from_object()`
把整个修改器栈的结果变成真实网格，**不调用 `modifier_apply`**。
后者依赖 active/selected，headless 下会静默返回 `{'CANCELLED'}`。

为什么不直接用 ops：
    bpy.ops.object.modifier_apply(modifier=...) 要求对象被选中且是 active，
    且对象不在编辑模式。批量处理时每次都要重置上下文，容易漏。
"""

import bpy


# ---------------------------------------------------------------- 底层

def _set(holder, **kw):
    """只在属性存在时才赋值。返回 (已设, 缺失)。

    版本漂移的防线：调用方可以传一堆同义参数，不存在的会被记下来
    而不是抛 AttributeError。
    """
    applied, missing = [], []
    for k, v in kw.items():
        if v is None:
            continue
        if not hasattr(holder, k):
            missing.append((k, "no such property"))
            continue
        try:
            setattr(holder, k, v)
            applied.append(k)
        except Exception as exc:                     # 类型不符 / 只读
            missing.append((k, "%s: %s" % (type(exc).__name__, exc)))
    return applied, missing


def _log(ob, mod_name, applied, missing):
    """把「设上了什么 / 没设上什么」记在对象上。

    注意：Modifier 不是 ID，不支持自定义属性（实测会抛
    `TypeError: id properties not supported for this type`），
    所以日志只能挂在 Object 上。
    """
    for key, val in (("bapi_mod_set", ", ".join(applied)),
                     ("bapi_mod_unset", "; ".join("%s (%s)" % (k, v)
                                                  for k, v in missing))):
        d = dict(ob.get(key, {}))
        d[mod_name] = val
        ob[key] = d


def add(ob, kind, name=None, strict=False, **kw):
    """加一个修改器并设属性。

    kind 用大写枚举名（'SUBSURF' / 'REMESH' / ...），完整列表见
    `catalog/03_modifiers.md` 或 `bpy.types.Modifier.bl_rna.properties['type']`。

    strict=True 时，任何一个属性没设上就抛 AttributeError——
    用来抓拼写错误，避免「以为设了其实没设」。
    """
    mod = ob.modifiers.new(name or kind.lower(), kind)
    applied, missing = _set(mod, **kw)
    if strict and missing:
        ob.modifiers.remove(mod)
        raise AttributeError("%s 不支持参数 %s" % (kind, [k for k, _ in missing]))
    _log(ob, mod.name, applied, missing)
    return mod


def bake(ob, upto=None, keep_uv=True):
    """把修改器栈烘进网格数据。

    upto=None  应用全部修改器
    upto=N     只应用前 N 个，其余留在栈上（用来「分层落地」）

    返回同一个对象（就地修改）。语义等价于逐个 modifier_apply，
    但不碰 context。
    """
    mods = list(ob.modifiers)
    if upto is not None and upto < len(mods):
        saved = [(m, m.show_viewport) for m in mods]
        for i, m in enumerate(mods):
            m.show_viewport = i < upto
    else:
        saved = None
        upto = len(mods)

    vl = bpy.context.view_layer
    vl.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    try:
        me = bpy.data.meshes.new_from_object(
            ev, preserve_all_data_layers=keep_uv, depsgraph=dg)
    except TypeError:                                # 老版本没有这两个关键字
        me = bpy.data.meshes.new_from_object(ev)

    if saved is not None:
        for m, vis in saved:
            m.show_viewport = vis

    old = ob.data
    for m in mods[:upto]:
        ob.modifiers.remove(m)
    ob.data = me
    me.name = (old.name if old else ob.name) + "_baked"
    if old is not None and old.users == 0:
        bpy.data.meshes.remove(old)
    return ob


# ---------------------------------------------------------------- 形变封装

def subsurf(ob, levels=2, render_levels=None, bake_it=True):
    """细分曲面。levels 是视口级数，渲染级数默认与之一致。"""
    add(ob, 'SUBSURF', levels=levels,
        render_levels=levels if render_levels is None else render_levels,
        use_limit_surface=True)
    return bake(ob) if bake_it else ob


def smooth(ob, iterations=5, factor=0.5, axes=(True, True, True), bake_it=True):
    """拉普拉斯式平滑（SMOOTH 修改器），会轻微收缩体积。"""
    add(ob, 'SMOOTH', iterations=iterations, factor=factor,
        use_x=axes[0], use_y=axes[1], use_z=axes[2])
    return bake(ob) if bake_it else ob


def voxel_remesh(ob, voxel_size=0.002, adaptivity=0.0, smooth_shade=True,
                 remove_disconnected=False, bake_it=True):
    """体素重网格：把重叠/自交的一堆面片重建成单一流形表面。

    这是程序化拼接多个部件后「焊成一体」的主力手段。
    voxel_size 越小越保细节，代价是面数按 (1/size)^2 涨。
    """
    add(ob, 'REMESH', mode='VOXEL', voxel_size=voxel_size,
        adaptivity=adaptivity, use_smooth_shade=smooth_shade,
        use_remove_disconnected=remove_disconnected)
    return bake(ob) if bake_it else ob


def displace(ob, strength=0.01, texture='CLOUDS', size=0.3, mid_level=0.5,
             coords='LOCAL', bake_it=True, name="bapi_tex"):
    """程序化噪声位移。texture 取 Texture 枚举里的程序纹理名。"""
    tex = bpy.data.textures.get(name)
    if tex is None:
        tex = bpy.data.textures.new(name, texture)
    _set(tex, noise_scale=size, noise_depth=2, contrast=1.0)
    add(ob, 'DISPLACE', texture=tex, strength=strength,
        mid_level=mid_level, texture_coords=coords)
    return bake(ob) if bake_it else ob


def shrinkwrap(ob, target, offset=0.0, method='NEAREST_SURFACEPOINT',
               bake_it=True):
    """把 ob 的表面吸到 target 上。做「贴脸」「贴衣」用。"""
    add(ob, 'SHRINKWRAP', target=target, offset=offset, wrap_method=method,
        wrap_mode='ON_SURFACE')
    return bake(ob) if bake_it else ob


def solidify(ob, thickness=0.002, offset=-1.0, rim=True, bake_it=True):
    """加厚成壳。offset=-1 向内长，+1 向外长，0 两侧各半。"""
    add(ob, 'SOLIDIFY', thickness=thickness, offset=offset, use_rim=rim,
        use_even_offset=True, use_quality_normals=True)
    return bake(ob) if bake_it else ob


def bevel(ob, width=0.002, segments=2, angle_limit=None, bake_it=True):
    """倒角。angle_limit 单位是弧度，None 表示只倒锐边（默认 30°）。"""
    kw = {"width": width, "segments": segments, "limit_method": 'ANGLE'}
    if angle_limit is not None:
        kw["angle_limit"] = angle_limit
    add(ob, 'BEVEL', **kw)
    return bake(ob) if bake_it else ob


def decimate(ob, ratio=0.5, bake_it=True):
    """按比例减面。ratio ∈ (0, 1]。"""
    add(ob, 'DECIMATE', ratio=ratio, decimate_type='COLLAPSE')
    return bake(ob) if bake_it else ob


def mirror(ob, axis='X', merge=True, bake_it=True):
    """镜像。注意镜像的是网格本地坐标，且需要对象原点在对称面上。"""
    add(ob, 'MIRROR', use_axis=(axis == 'X', axis == 'Y', axis == 'Z'),
        use_mirror_merge=merge)
    return bake(ob) if bake_it else ob


def smooth_corrective(ob, factor=0.5, iterations=1, scale=1.0, bake_it=True):
    """Corrective Smooth：保体积的平滑，比 SMOOTH 更不容易缩水。"""
    add(ob, 'CORRECTIVE_SMOOTH', factor=factor, iterations=iterations,
        scale=scale, smooth_type='LENGTH_WEIGHTED')
    return bake(ob) if bake_it else ob


def clear(ob):
    """清空修改器栈（不烘焙，直接丢弃）。"""
    for m in list(ob.modifiers):
        ob.modifiers.remove(m)
    return ob


def explain(ob):
    """返回修改器栈的可读描述，用于事后核对「到底加了什么」。"""
    sets = dict(ob.get("bapi_mod_set", {}))
    unsets = dict(ob.get("bapi_mod_unset", {}))
    out = []
    for m in ob.modifiers:
        out.append({
            "name": m.name,
            "type": m.type,
            "show_viewport": m.show_viewport,
            "set": sets.get(m.name, ""),
            "unset": unsets.get(m.name, ""),
        })
    return out
