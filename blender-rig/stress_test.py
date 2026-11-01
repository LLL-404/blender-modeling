import bpy, math, os
from mathutils import Vector

OUT = r"D:\G\github\实用工具\Blender建模\blender-rig\out"
IMG = r"D:\G\github\实用工具\Blender建模\blender-rig\preview"
os.makedirs(IMG, exist_ok=True)


def setup(glb):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mn = Vector((min(mn[i], w[i]) for i in range(3)))
            mx = Vector((max(mx[i], w[i]) for i in range(3)))
    ctr = (mn + mx) * 0.5
    r = max(mx - mn) * 0.5
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    bpy.context.collection.objects.link(cam)
    cam.location = ctr + Vector((r * 2.2, -r * 4.0, r * 1.2))
    tgt = bpy.data.objects.new("T", None); bpy.context.collection.objects.link(tgt); tgt.location = ctr
    con = cam.constraints.new(type='TRACK_TO'); con.target = tgt
    con.track_axis = 'TRACK_NEGATIVE_Z'; con.up_axis = 'UP_Y'
    bpy.context.scene.camera = cam
    lt = bpy.data.lights.new("L", type='AREA'); lt.energy = 900; lt.size = r * 4
    lo = bpy.data.objects.new("L", lt); lo.location = ctr + Vector((r * 3, -r * 3, r * 3))
    bpy.context.collection.objects.link(lo)
    c2 = lo.constraints.new(type='TRACK_TO'); c2.target = tgt
    c2.track_axis = 'TRACK_NEGATIVE_Z'; c2.up_axis = 'UP_Y'
    bpy.ops.mesh.primitive_plane_add(size=r * 20, location=(ctr.x, ctr.y, mn.z - 0.005))
    w = bpy.data.worlds.new("W"); bpy.context.scene.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.06, 0.06, 0.07, 1)
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x = 560; sc.render.resolution_y = 560
    sc.render.image_settings.file_format = 'PNG'
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
    bpy.context.scene.render.filepath = os.path.join(IMG, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("STRESS", name, deg)


stress(os.path.join(OUT, "core_jade.glb"), "stress_core", 20)
stress(os.path.join(OUT, "tower_ballista.glb"), "stress_tower", 18)
print("DONE")
