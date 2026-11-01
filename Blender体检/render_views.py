# Blender体检 · 多视角渲染脚本（在 Blender 内运行，只读渲染，绝不保存 .blend）
#
# 用法：
#   blender -b <model.blend> [--factory-startup] --python-exit-code 1 \
#       --python render_views.py -- --views 16 --elevation 20 --engine eevee \
#                                 --res 512 --out <目录>
#
# 产物（--out 目录下，PNG 由 Blender 落盘；manifest.json 由驱动 check.sh
# 从本脚本的 stdout 提取 MANIFEST_JSON 行写入）：
#   view_000.png ~ view_NNN.png     环绕视角（默认 16 个，每 360/N 度一张）
#   view_top.png                    正顶视角
#   sheet.png                       拼版总览图（6 列网格）
#   manifest.json                   角度/路径/耗时/包围盒/引擎
#
# 设计要点：
#   - 所有环绕视角共用同一相机半径（按场景包围盒自动取景），各图比例一致便于对照
#   - 隐藏原场景灯光、用「双太阳 + 灰背景世界」提供统一布光，不依赖原场景光照
#   - 只读：不 bpy.ops.wm.save_mainfile，不触碰源文件；本脚本自身无任何文件写 API
#   - 落盘路径全部过守卫：禁穿越组件，且输出目录限制在工具目录或模型目录内
import bpy
import sys
import os
import json
import math
import time
import traceback

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from mathutils import Vector

_TRAVERSAL = os.pardir


def tool_dir():
    try:
        return os.path.abspath(os.path.dirname(__file__))
    except NameError:
        return os.path.abspath(os.getcwd())


def safe_outdir(raw):
    """规范化输出目录：拒绝带穿越组件的路径。"""
    if raw:
        parts = raw.replace("\\", "/").split("/")
        if _TRAVERSAL in parts:
            raise RuntimeError("非法输出目录（含穿越组件）: %s" % raw)
    return os.path.abspath(raw.replace("\\", "/"))


def ensure_within(p, roots):
    """路径必须落在允许目录（工具目录或模型目录）之内。"""
    for r in roots:
        if r and os.path.commonpath([r, p]) == r:
            return
    raise RuntimeError("输出目录不在允许范围内（仅限工具目录或模型目录）: %s" % p)


def safe_join(base, name):
    """base 目录 + 单段文件名：名字不得含分隔符/穿越组件，结果必须落在 base 内。"""
    base_abs = os.path.abspath(base)
    parts = name.replace("\\", "/").split("/")
    if os.path.isabs(name) or _TRAVERSAL in parts or len(parts) != 1:
        raise RuntimeError("非法文件名: %r" % name)
    p = os.path.abspath(os.path.join(base_abs, name))
    if os.path.commonpath([base_abs, p]) != base_abs:
        raise RuntimeError("路径越界: %r" % name)
    return p


def parse_args():
    argv = sys.argv
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    opts = {
        "views": 16,
        "elevation": 20.0,
        "engine": "eevee",
        "res": 512,
        "out": "",
        "sheet": True,
    }
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--views":
            opts["views"] = int(args[i + 1]); i += 2
        elif a == "--elevation":
            opts["elevation"] = float(args[i + 1]); i += 2
        elif a == "--engine":
            opts["engine"] = args[i + 1].lower(); i += 2
        elif a == "--res":
            opts["res"] = int(args[i + 1]); i += 2
        elif a == "--out":
            opts["out"] = args[i + 1]; i += 2
        elif a == "--no-sheet":
            opts["sheet"] = False; i += 1
        else:
            raise RuntimeError("未知参数: %s" % a)
    if opts["views"] < 1 or opts["views"] > 64:
        raise RuntimeError("--views 取值 1..64")
    if opts["engine"] not in ("eevee", "workbench", "cycles"):
        raise RuntimeError("--engine 取值 eevee|workbench|cycles")
    if opts["res"] < 64 or opts["res"] > 4096:
        raise RuntimeError("--res 取值 64..4096")
    return opts


def pick_engine(want):
    """按偏好顺序挑一个本版本 Blender 可用的引擎枚举名（4.2+ 里 EEVEE Next 改过名）。"""
    prefs = {
        "eevee": ["BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"],
        "workbench": ["BLENDER_WORKBENCH"],
        "cycles": ["CYCLES"],
    }[want]
    items = {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
    for p in prefs:
        if p in items:
            bpy.context.scene.render.engine = p
            return p
    for p in prefs:  # 兜底：动态注册的引擎可能不在静态 RNA 枚举里，直接试赋值
        try:
            bpy.context.scene.render.engine = p
            return p
        except Exception:
            pass
    raise RuntimeError("引擎不可用: %s（本版可选: %s）" % (want, sorted(items)))


def tune_engine(scene, eid):
    if "EEVEE" in eid:
        try:
            scene.eevee.taa_render_samples = 32
        except Exception:
            pass
    elif eid == "CYCLES":
        scene.cycles.samples = 32
    elif "WORKBENCH" in eid:
        sh = scene.display.shading
        sh.light = "STUDIO"
        sh.color_type = "MATERIAL"
        try:
            sh.show_cavity = True
            sh.cavity_type = "SCREEN"
        except Exception:
            pass


def setup_lighting(scene):
    """灰背景世界 + 主/辅两盏太阳，隐藏原场景灯光，保证各视角布光一致。"""
    for ob in scene.objects:
        if ob.type == "LIGHT":
            ob.hide_render = True
    scene.render.film_transparent = False  # 会话级：不透传天空，画面背景来自世界灰底

    w = scene.world
    if w is None:
        w = bpy.data.worlds.new("CHECK_WORLD")
        scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = next((n for n in nt.nodes if n.type == "BACKGROUND"), None)
    if bg is None:
        bg = nt.nodes.new("ShaderNodeBackground")
        out_node = next((n for n in nt.nodes if n.type == "OUTPUT_WORLD"), None)
        if out_node is None:
            out_node = nt.nodes.new("ShaderNodeOutputWorld")
        nt.links.new(bg.outputs["Background"], out_node.inputs["Surface"])
    # 防御B：复用已有 Background 时补链——World Output 的 Surface 必须由本 bg 驱动
    outs = [n for n in nt.nodes if n.type == "OUTPUT_WORLD"]
    out_node = next((n for n in outs if getattr(n, "is_active_output", False)), None)
    if out_node is None and outs:
        out_node = outs[0]
    if out_node is None:
        out_node = nt.nodes.new("ShaderNodeOutputWorld")
    surf = out_node.inputs["Surface"]
    if surf.is_linked and surf.links[0].from_node.name != bg.name:
        nt.links.remove(surf.links[0])  # 非 Background 的 Surface 链路（如经 Mix）显式移除；按 name 比较，节点包装器非稳定标识
    if not surf.is_linked:
        nt.links.new(bg.outputs["Background"], surf)
    # 防御A：改写 bg 参数前，断开进入 Color/Strength 的所有旧链接
    for sock in (bg.inputs["Color"], bg.inputs["Strength"]):
        for lk in list(sock.links):
            nt.links.remove(lk)
    bg.inputs["Color"].default_value = (0.82, 0.82, 0.84, 1.0)
    bg.inputs["Strength"].default_value = 1.0

    for name, energy, rot in (("CHECK_KEY", 3.0, (math.radians(50), 0.0, math.radians(35))),
                              ("CHECK_FILL", 1.0, (math.radians(55), 0.0, math.radians(-140)))):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy = energy
        ld.angle = math.radians(15)
        so = bpy.data.objects.new(name, ld)
        scene.collection.objects.link(so)
        so.rotation_euler = rot


def scene_bounds(scene):
    """可见几何对象的包围盒：返回 (center Vector, size Vector, 半径 float)。"""
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for ob in scene.objects:
        if ob.type not in {"MESH", "CURVE", "SURFACE", "META", "FONT", "VOLUME"}:
            continue
        try:
            if not ob.visible_get():
                continue
        except Exception:
            pass
        ob_eval = ob.evaluated_get(dg)
        for c in ob_eval.bound_box:
            pts.append(ob_eval.matrix_world @ Vector(c))
    if not pts:  # 兜底：不筛可见性
        for ob in scene.objects:
            if ob.type in {"MESH", "CURVE", "SURFACE", "META", "FONT", "VOLUME"}:
                for c in ob.bound_box:
                    pts.append(ob.matrix_world @ Vector(c))
    if not pts:
        raise RuntimeError("场景里没有可渲染的几何对象")
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    center = (mn + mx) / 2.0
    size = mx - mn
    radius = max(size.length / 2.0, 1e-4)
    return center, size, radius


def do_render(scene, path, res):
    scene.render.resolution_x = res
    scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    return time.time() - t


def render_views(scene, opts, out_dir, center, radius):
    cam_data = bpy.data.cameras.new("CHECK_CAM")
    cam_data.lens = 50
    cam = bpy.data.objects.new("CHECK_CAM", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    half_fov = math.atan(cam_data.sensor_width / 2.0 / cam_data.lens)
    dist = radius / math.sin(half_fov) * 1.12  # 1.12 = 留边
    cam_data.clip_start = max(0.001, dist * 0.001)
    cam_data.clip_end = dist * 5.0 + radius * 10.0

    shots = []
    el = math.radians(opts["elevation"])
    for i in range(opts["views"]):
        az = 2.0 * math.pi * i / opts["views"]
        pos = center + dist * Vector((math.cos(el) * math.sin(az),
                                      -math.cos(el) * math.cos(az),
                                      math.sin(el)))
        d = (center - pos).normalized()
        cam.location = pos
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        name = "view_%03d.png" % i
        dur = do_render(scene, safe_join(out_dir, name), opts["res"])
        shots.append({"file": name, "azimuth_deg": round(math.degrees(az), 1),
                      "elevation_deg": opts["elevation"], "seconds": round(dur, 2)})

    # 顶视：正上方垂直往下看
    pos = center + dist * Vector((0.0, 0.0, 1.0))
    d = (center - pos).normalized()
    cam.location = pos
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    dur = do_render(scene, safe_join(out_dir, "view_top.png"), opts["res"])
    shots.append({"file": "view_top.png", "azimuth_deg": 0.0,
                  "elevation_deg": 90.0, "seconds": round(dur, 2)})
    return shots, dist


def make_shot_sheet(files, out_dir, cell):
    """把已渲 PNG 拼成 6 列网格总览图（bpy 像素直拼，Non-Color 免伽马往返失真）。"""
    import numpy as np
    imgs = []
    for f in files:
        im = bpy.data.images.load(safe_join(out_dir, f))
        im.colorspace_settings.name = "Non-Color"
        imgs.append(im)
    cols = 6
    rows = math.ceil(len(imgs) / cols)
    W, H = cols * cell, rows * cell
    sheet = bpy.data.images.new("CHECK_SHEET", width=W, height=H, alpha=False)
    sheet.colorspace_settings.name = "Non-Color"
    grid = np.full((H, W, 4), 0.35, dtype=np.float32)  # 空格填 0.35 灰（契约值 Q2）
    grid[:, :, 3] = 1.0
    for i, im in enumerate(imgs):
        iw, ih = im.size[0], im.size[1]
        if (iw, ih) != (cell, cell):  # 尺寸守卫：失败由 main() 的拼版 try/except 容错只弃 sheet
            raise RuntimeError("拼版单元尺寸不符: %s %dx%d != %d" % (files[i], iw, ih, cell))
        px = np.empty(iw * ih * 4, dtype=np.float32)
        im.pixels.foreach_get(px)
        px = px.reshape(ih, iw, 4)[::-1]  # 源图自底向上 → 显示方向（正立）
        r, c = divmod(i, cols)
        grid[r*cell:r*cell+ih, c*cell:c*cell+iw, :] = px  # grid=阅读顺序（首行=view_000..005）
    sheet.pixels.foreach_set(np.flipud(grid).reshape(-1))  # 显示方向 → bpy 自底向上（关键一行）
    sheet.filepath_raw = safe_join(out_dir, "sheet.png")
    sheet.file_format = "PNG"
    sheet.save()


def main():
    opts = parse_args()
    scene = bpy.context.scene

    eid = pick_engine(opts["engine"])
    tune_engine(scene, eid)
    setup_lighting(scene)
    center, size, radius = scene_bounds(scene)

    roots = [tool_dir()]
    model_path = bpy.data.filepath
    if model_path:
        roots.append(os.path.dirname(os.path.abspath(model_path)))
    if opts["out"]:
        out_dir = safe_outdir(opts["out"])
    else:
        out_dir = safe_outdir(os.path.join(roots[-1], "_views"))
    ensure_within(out_dir, roots)
    os.makedirs(out_dir, exist_ok=True)

    t0 = time.time()
    shots, cam_dist = render_views(scene, opts, out_dir, center, radius)
    files = [s["file"] for s in shots]
    for f in files:
        p = safe_join(out_dir, f)
        if not os.path.isfile(p) or os.path.getsize(p) == 0:
            raise RuntimeError("渲染产物缺失或为空: %s" % f)

    sheet_made = False
    if opts["sheet"]:
        try:
            make_shot_sheet(files, out_dir, opts["res"])
            sheet_made = os.path.isfile(safe_join(out_dir, "sheet.png"))
        except Exception as e:
            print("[blender体检] 拼版失败（不影响单图）: %s" % e, file=sys.stderr)

    manifest = {
        "model": model_path,
        "blender_version": bpy.app.version_string,
        "engine": eid,
        "view_transform": scene.view_settings.view_transform,
        "look": scene.view_settings.look,
        "views": opts["views"],
        "elevation_deg": opts["elevation"],
        "resolution": opts["res"],
        "out_dir": out_dir,
        "camera_distance": round(cam_dist, 4),
        "bbox_center": [round(v, 4) for v in center],
        "bbox_size": [round(v, 4) for v in size],
        "total_seconds": round(time.time() - t0, 2),
        "shots": shots,
    }
    # manifest 不在本脚本落盘（无文件写 API），整行打给驱动提取
    print("MANIFEST_JSON " + json.dumps(manifest, ensure_ascii=False))
    print("CHECK_OK " + json.dumps({
        "out_dir": out_dir,
        "views": len(files),
        "sheet": sheet_made,
        "engine": eid,
        "seconds": manifest["total_seconds"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        print("CHECK_FAIL 渲染失败，详见上方堆栈", file=sys.stderr)
        sys.exit(1)
