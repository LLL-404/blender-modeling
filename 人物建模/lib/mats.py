# -*- coding: utf-8 -*-
"""材质。M2 先用朴素色块，M3 换成原神风着色。"""
import bpy


def simple(name, color, rough=0.55, metallic=0.0, sss=0.0,
           emit=None, emit_strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    if sss:
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = (0.06, 0.025, 0.015)
    if emit is not None:
        b.inputs["Emission Color"].default_value = (*emit, 1.0)
        b.inputs["Emission Strength"].default_value = emit_strength
    return mat


def set_all():
    return {
        "skin": simple("skin", (0.760, 0.560, 0.480), rough=0.52, sss=0.14),
        "sclera": simple("sclera", (0.860, 0.855, 0.860), rough=0.32),
        "iris": simple("iris", (0.480, 0.240, 0.045), rough=0.25),
        "pupil": simple("pupil", (0.008, 0.008, 0.010), rough=0.22),
        "white_emit": simple("white_emit", (1, 1, 1), rough=0.1,
                             emit=(1, 1, 1), emit_strength=2.2),
        "lash": simple("lash", (0.045, 0.028, 0.028), rough=0.45),
        "lash_soft": simple("lash_soft", (0.180, 0.105, 0.095), rough=0.5),
        "brow": simple("brow", (0.095, 0.055, 0.045), rough=0.5),
        "lip": simple("lip", (0.520, 0.190, 0.185), rough=0.40),
    }
