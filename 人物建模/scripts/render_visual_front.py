# -*- coding: utf-8 -*-
"""视觉闸门专用渲染：固定一台正面机位，出 out/visual_front.png。

为什么单独一支
--------------
`visual_gate.py` 要把参考图和当前模型放在同一套图像特征上比。
比对用的图必须满足三点，否则特征漂移没法判：
  1. 机位固定 —— 直接复用 shots.VIEWS['m5_face_front']，不再临时调相机；
  2. 分辨率固定 —— 620×780，与 VIEWS 表一致；
  3. 产物新鲜 —— 由 visual_gate.py 比对 美女.blend 的 mtime 决定是否重渲染。

不新造灯光、不改材质、不关描边：与 m5 阶段各正面图同口径，
肉眼看到的 m5_face_front.png 和这里应当是同一张脸。

用法（由 visual_gate.py 调，也可手动跑）：
    blender -b --factory-startup --python scripts/render_visual_front.py
    blender -b --factory-startup --python scripts/render_visual_front.py -- --blend X.blend
"""
import bpy
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import shots  # noqa: E402

DEFAULT_BLEND = os.path.join(HERE, "美女.blend")
OUT_NAME = "visual_front.png"
VIEW_KEY = "m5_face_front"


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = {"blend": DEFAULT_BLEND}
    for i, a in enumerate(argv):
        if a == "--blend" and i + 1 < len(argv):
            o["blend"] = argv[i + 1]
    return o


def main():
    o = parse_args()
    if not os.path.exists(o["blend"]):
        print("[visual] 源文件不存在：%s" % o["blend"])
        return 2
    bpy.ops.wm.open_mainfile(filepath=o["blend"])

    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'

    v = shots.VIEWS[VIEW_KEY]
    shots.set_res(v["w"], v["h"])
    cam = shots.camera("visual_gate_front", v["loc"], (0, 0, v["zc"]),
                       ortho_scale=v["ortho"])
    path = shots.render(cam, OUT_NAME)
    print("[visual] rendered %s (%d x %d)" % (path, v["w"], v["h"]))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
