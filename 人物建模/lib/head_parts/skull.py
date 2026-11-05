# -*- coding: utf-8 -*-
"""L2 部件 1/8：颅骨壳（控制笼 + Catmull-Clark）。

phase 1 只搬函数，数值一字未改。`grow_x/grow_y` 由门面传入，
因为 `scripts/probe_cage.py` 会在运行时改 `head.CAGE_GROW_X/Y`。
"""
import bpy

from . import _base as B
from meshkit import superellipse_ring, loft, resample, select_only


def head_cage(grow_x, grow_y):
    """稀疏控制笼。形状仍由 HEAD 表决定，只是采样点变少。"""
    rows = resample(B.head_rows(), "z", B.CAGE_STEP)
    rings = [superellipse_ring(z, rx * grow_x, ryf * grow_y,
                               cy * grow_y, 0.0, p, B.CAGE_SEG,
                               ry_back=ryb * grow_y)
             for z, rx, ryf, ryb, cy, p in rows]
    return loft(rings, name="head")


def subdivide(ob, levels=B.CAGE_SUBDIV):
    """控制笼 → Catmull-Clark 极限曲面，直接 apply 成实体网格。

    必须 apply：后续 sculpt() 按顶点坐标做高斯位移、conform() 用 BVH 贴五官，
    留修改器会读到未细分的笼面。
    """
    m = ob.modifiers.new("cage_subdiv", 'SUBSURF')
    m.subdivision_type = 'CATMULL_CLARK'
    m.levels = levels
    m.render_levels = levels
    m.use_limit_surface = True
    select_only(ob)
    bpy.ops.object.modifier_apply(modifier=m.name)
    return ob
