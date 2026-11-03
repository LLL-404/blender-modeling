import bpy, math, os, sys
from mathutils import Vector

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import preview_common as pc  # noqa: E402  D1-D6 共享层（blender-rig 三脚本同源）

OUT = r"D:\G\github\实用工具\Blender建模\blender-rig\out"
IMG = r"D:\G\github\实用工具\Blender建模\blender-rig\preview"
os.makedirs(IMG, exist_ok=True)


def setup(glb):
    pc.reset_scene(res=pc.PREVIEW_RES)   # D1+D2+D6：清场 + EEVEE 回退挑选 + 560×560 PNG
    bpy.ops.import_scene.gltf(filepath=glb)
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    mn, mx = pc.world_bounds(objs)   # D3
    ctr = (mn + mx) * 0.5
    r = max(mx - mn) * 0.5
    tgt = bpy.data.objects.new("T", None); bpy.context.collection.objects.link(tgt); tgt.location = ctr
    # 机位乘子 (0.55,1.0,0.30)×zoom 4.0 = 抽取前字面 (2.2, -4.0, 1.2)
    pc.frame_on_bounds(ctr, r, offset=(0.55, 1.0, 0.30), zoom=4.0, target=tgt)   # D4
    lt = bpy.data.lights.new("L", type='AREA'); lt.energy = 900; lt.size = r * 4
    lo = bpy.data.objects.new("L", lt); lo.location = ctr + Vector((r * 3, -r * 3, r * 3))
    bpy.context.collection.objects.link(lo)
    c2 = lo.constraints.new(type='TRACK_TO'); c2.target = tgt
    c2.track_axis = 'TRACK_NEGATIVE_Z'; c2.up_axis = 'UP_Y'
    bpy.ops.mesh.primitive_plane_add(size=r * 20, location=(ctr.x, ctr.y, mn.z - 0.005))
    w = bpy.data.worlds.new("W"); bpy.context.scene.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.06, 0.06, 0.07, 1)
    arm = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE'][0]
    if arm.animation_data:
        arm.animation_data.action = None
        for tr in list(arm.animation_data.nla_tracks):
            arm.animation_data.nla_tracks.remove(tr)
    return arm, r


def stress(glb, name, deg):
    arm, r = setup(glb)
    pb = arm.pose.bones["upper"]
    pb.rotation_mode = 'XYZ'
    pb.rotation_euler = (math.radians(deg), 0, 0)
    bpy.context.view_layer.update()
    pc.render_still(os.path.join(IMG, name + ".png"))   # D5：落盘单源
    print("STRESS", name, deg)


stress(os.path.join(OUT, "core_jade.glb"), "stress_core", 20)
stress(os.path.join(OUT, "tower_ballista.glb"), "stress_tower", 18)
print("DONE")
