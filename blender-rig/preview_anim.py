import bpy, math, os, sys
from mathutils import Vector

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import preview_common as pc  # noqa: E402  D1-D6 共享层（blender-rig 三脚本同源）

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
IMG = os.path.join(HERE, "preview")
os.makedirs(IMG, exist_ok=True)


def setup_scene(glb, zoom=3.6):
    pc.reset_scene(res=pc.PREVIEW_RES)   # D1+D2+D6：清场 + EEVEE 回退挑选 + 560×560 PNG
    bpy.ops.import_scene.gltf(filepath=glb)

    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    mn, mx = pc.world_bounds(objs)   # D3
    ctr = (mn + mx) * 0.5
    r = max((mx - mn)) * 0.5

    tgt = bpy.data.objects.new("T", None); bpy.context.collection.objects.link(tgt)
    tgt.location = ctr
    pc.frame_on_bounds(ctr, r, zoom=zoom, target=tgt)   # D4

    for loc, e in [((r * 3, -r * 3, r * 3), 900), ((-r * 3, -r * 2, r * 1.5), 300)]:
        lt = bpy.data.lights.new("L", type='AREA'); lt.energy = e; lt.size = r * 4
        lo = bpy.data.objects.new("L", lt); lo.location = ctr + Vector(loc)
        bpy.context.collection.objects.link(lo)
        c2 = lo.constraints.new(type='TRACK_TO'); c2.target = tgt
        c2.track_axis = 'TRACK_NEGATIVE_Z'; c2.up_axis = 'UP_Y'

    bpy.ops.mesh.primitive_plane_add(size=r * 20, location=(ctr.x, ctr.y, mn.z - 0.005))
    w = bpy.data.worlds.new("W"); bpy.context.scene.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.06, 0.06, 0.07, 1)


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
        pc.render_still(os.path.join(IMG, f"{prefix}_{f}.png"))   # D5：落盘单源
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
