import bpy, math, os
from mathutils import Vector

OUT = r"D:\G\github\实用工具\Blender建模\blender-rig\out"
IMG = r"D:\G\github\实用工具\Blender建模\blender-rig\preview"
os.makedirs(IMG, exist_ok=True)


def setup_scene(glb, zoom=3.6):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)

    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    mn = Vector((1e9, 1e9, 1e9)); mx = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mn = Vector((min(mn[i], w[i]) for i in range(3)))
            mx = Vector((max(mx[i], w[i]) for i in range(3)))
    ctr = (mn + mx) * 0.5
    r = max((mx - mn)) * 0.5

    cam_data = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = ctr + Vector((r * zoom * 0.55, -r * zoom, r * zoom * 0.35))
    tgt = bpy.data.objects.new("T", None); bpy.context.collection.objects.link(tgt)
    tgt.location = ctr
    con = cam.constraints.new(type='TRACK_TO'); con.target = tgt
    con.track_axis = 'TRACK_NEGATIVE_Z'; con.up_axis = 'UP_Y'
    bpy.context.scene.camera = cam

    for loc, e in [((r * 3, -r * 3, r * 3), 900), ((-r * 3, -r * 2, r * 1.5), 300)]:
        lt = bpy.data.lights.new("L", type='AREA'); lt.energy = e; lt.size = r * 4
        lo = bpy.data.objects.new("L", lt); lo.location = ctr + Vector(loc)
        bpy.context.collection.objects.link(lo)
        c2 = lo.constraints.new(type='TRACK_TO'); c2.target = tgt
        c2.track_axis = 'TRACK_NEGATIVE_Z'; c2.up_axis = 'UP_Y'

    bpy.ops.mesh.primitive_plane_add(size=r * 20, location=(ctr.x, ctr.y, mn.z - 0.005))
    w = bpy.data.worlds.new("W"); bpy.context.scene.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.06, 0.06, 0.07, 1)

    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x = 560
    sc.render.resolution_y = 560
    sc.render.image_settings.file_format = 'PNG'


def find_arm():
    for o in bpy.context.scene.objects:
        if o.type == 'ARMATURE':
            return o
    return None


def set_action(arm, keyword):
    if arm.animation_data is None:
        arm.animation_data_create()
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)
    acts = [a for a in bpy.data.actions if keyword.lower() in a.name.lower()]
    print("ACTIONS:", [a.name for a in bpy.data.actions], "pick:", acts[0].name if acts else None)
    if acts:
        arm.animation_data.action = acts[0]
        return acts[0].name
    return None


def render_frames(prefix, frames):
    for f in frames:
        bpy.context.scene.frame_set(f)
        bpy.context.scene.render.filepath = os.path.join(IMG, f"{prefix}_{f}.png")
        bpy.ops.render.render(write_still=True)
        print("SHOT", prefix, f)


setup_scene(os.path.join(OUT, "core_jade.glb"))
arm = find_arm()
set_action(arm, "Idle")
render_frames("core_idle", [0, 30, 60, 90])
set_action(arm, "Hit")
render_frames("core_hit", [0, 3, 7])

setup_scene(os.path.join(OUT, "tower_ballista.glb"))
arm = find_arm()
set_action(arm, "Fire")
render_frames("tower_fire", [0, 2, 6, 11])

print("PREVIEW DONE")
