import bpy, math, os
from mathutils import Vector

SRC = r"D:\G\game\games\reroute-godot\assets\models"
OUT = r"D:\G\github\实用工具\Blender建模\blender-rig\out"
os.makedirs(OUT, exist_ok=True)

FPS = 30


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = FPS


def mesh_objects():
    return [o for o in bpy.context.scene.objects if o.type == 'MESH']


def world_z_range(objs):
    zs = []
    for o in objs:
        mw = o.matrix_world
        for v in o.data.vertices:
            zs.append((mw @ v.co).z)
    return min(zs), max(zs)


def smoothstep(a, b, x):
    if b <= a:
        return 1.0 if x >= b else 0.0
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def make_rig(objs, zmin, zmax, lower_frac, split_lo_f, split_hi_f):
    """两根骨骼：lower 从底到 lower_frac，upper 接上。权重按 z 平滑过渡。"""
    h = zmax - zmin
    z_split = zmin + h * lower_frac
    split_lo = zmin + h * split_lo_f
    split_hi = zmin + h * split_hi_f

    arm = bpy.data.armatures.new("rig")
    rig = bpy.data.objects.new("rig", arm)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    b = arm.edit_bones.new("base")
    b.head = (0, 0, zmin)
    b.tail = (0, 0, z_split)
    c = arm.edit_bones.new("upper")
    c.head = (0, 0, z_split)
    c.tail = (0, 0, zmax)
    c.parent = b
    c.use_connect = True
    bpy.ops.object.mode_set(mode='OBJECT')

    for o in objs:
        vg_lo = o.vertex_groups.new(name="base")
        vg_hi = o.vertex_groups.new(name="upper")
        mw = o.matrix_world
        for i, v in enumerate(o.data.vertices):
            z = (mw @ v.co).z
            w = smoothstep(split_lo, split_hi, z)
            if w < 1.0:
                vg_lo.add([i], 1.0 - w, 'REPLACE')
            if w > 0.0:
                vg_hi.add([i], w, 'REPLACE')
        mod = o.modifiers.new("Armature", 'ARMATURE')
        mod.object = rig
        mod.use_vertex_groups = True
        o.parent = rig

    print("RIG split_z", round(z_split, 4), "weights", round(split_lo, 4), round(split_hi, 4))
    return rig


def key_bone(rig, bone, frame, rot=None, loc=None, scale=None):
    pb = rig.pose.bones[bone]
    pb.rotation_mode = 'XYZ'
    if rot is not None:
        pb.rotation_euler = rot
    if loc is not None:
        pb.location = loc
    if scale is not None:
        pb.scale = scale
    pb.keyframe_insert("rotation_euler", frame=frame)
    pb.keyframe_insert("location", frame=frame)
    pb.keyframe_insert("scale", frame=frame)


def clear_pose(rig):
    for pb in rig.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)


def new_action(rig, name):
    ad = rig.animation_data_create()
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    ad.action = act
    return act


def finish_action(act, end):
    act.use_frame_range = True
    act.frame_start = 0
    act.frame_end = end


def d(v):
    return math.radians(v)


def build_core():
    bpy.ops.import_scene.gltf(filepath=os.path.join(SRC, "core_jade.glb"))
    objs = mesh_objects()
    zmin, zmax = world_z_range(objs)
    print("CORE z range", zmin, zmax)
    rig = make_rig(objs, zmin, zmax, 0.16, 0.10, 0.24)

    act = new_action(rig, "Idle")
    for f, a in [(0, 0.0), (30, 1.0), (60, 0.0), (90, -1.0), (120, 0.0)]:
        key_bone(rig, "upper", f,
                 rot=(d(1.4) * a, d(7.0) * a, d(1.0) * a),
                 loc=(0, 0.010 * a, 0),
                 scale=(1.0 + 0.012 * abs(a), 1.0 + 0.018 * abs(a), 1.0 + 0.012 * abs(a)))
    finish_action(act, 120)

    clear_pose(rig)
    act = new_action(rig, "Hit")
    key_bone(rig, "upper", 0, rot=(0, 0, 0), loc=(0, 0, 0), scale=(1, 1, 1))
    key_bone(rig, "upper", 3, rot=(d(-5.0), d(4.0), d(2.0)), loc=(0, -0.012, 0), scale=(1.05, 0.95, 1.05))
    key_bone(rig, "upper", 7, rot=(d(2.6), d(-2.0), d(-1.0)), loc=(0, 0.006, 0), scale=(0.985, 1.02, 0.985))
    key_bone(rig, "upper", 12, rot=(0, 0, 0), loc=(0, 0, 0), scale=(1, 1, 1))
    finish_action(act, 12)

    export("core_jade")


def build_tower():
    bpy.ops.import_scene.gltf(filepath=os.path.join(SRC, "tower_ballista.glb"))
    objs = mesh_objects()
    zmin, zmax = world_z_range(objs)
    print("TOWER z range", zmin, zmax)
    rig = make_rig(objs, zmin, zmax, 0.42, 0.32, 0.48)

    act = new_action(rig, "Fire")
    key_bone(rig, "upper", 0, rot=(0, 0, 0), loc=(0, 0, 0), scale=(1, 1, 1))
    key_bone(rig, "upper", 2, rot=(d(-5.5), 0, 0), loc=(0, -0.010, 0), scale=(1.02, 0.985, 1.02))
    key_bone(rig, "upper", 6, rot=(d(2.2), 0, 0), loc=(0, 0.004, 0), scale=(0.995, 1.01, 0.995))
    key_bone(rig, "upper", 11, rot=(d(-0.7), 0, 0), loc=(0, 0, 0), scale=(1, 1, 1))
    key_bone(rig, "upper", 18, rot=(0, 0, 0), loc=(0, 0, 0), scale=(1, 1, 1))
    finish_action(act, 18)

    export("tower_ballista")


def export(name):
    bpy.ops.object.select_all(action='SELECT')
    path = os.path.join(OUT, name + ".glb")
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format='GLB',
        use_selection=True,
        export_apply=False,
        export_yup=True,
        export_animations=True,
        export_animation_mode='ACTIONS',
        export_skins=True,
        export_keep_originals=True,
        export_image_format='AUTO',
        export_cameras=False,
        export_lights=False,
        export_extras=False,
    )
    print("EXPORTED", path, os.path.getsize(path))


reset_scene()
build_core()

reset_scene()
build_tower()

print("ALL DONE")
