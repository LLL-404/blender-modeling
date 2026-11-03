# -*- coding: utf-8 -*-
r"""外观测量探针：把 美女.blend 的形状翻译成数字，落盘 out/appearance.json。

用法（在 人物建模/ 下）：
    "D:/Program Files/Blender Foundation/Blender 5.2/blender.exe" \
        -b --factory-startup --python-exit-code 1 --python _probe/appearance_probe.py

可选参数（放在 `--` 之后）：
    --blend <路径>   默认 美女.blend
    --out   <路径>   默认 out/appearance.json

只读：不渲染、不保存、不修改任何物体。产物是一个 JSON，
供 scripts/measure.py 拿去做「实测 vs 目标」比对，也供图表直接画剖面。
"""
import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import appearance  # noqa: E402

PART_NAMES = ('Head', 'Body', 'Hair', 'Outfit', 'Hands')


def _args():
    argv = sys.argv
    argv = argv[argv.index('--') + 1:] if '--' in argv else []
    blend = os.path.join(HERE, '美女.blend')
    out = os.path.join(HERE, 'out', 'appearance.json')
    i = 0
    while i < len(argv):
        if argv[i] == '--blend' and i + 1 < len(argv):
            blend = argv[i + 1]
            i += 2
        elif argv[i] == '--out' and i + 1 < len(argv):
            out = argv[i + 1]
            i += 2
        else:
            i += 1
    return blend, out


def main():
    blend, out_path = _args()
    if not os.path.isabs(blend):
        blend = os.path.join(HERE, blend)
    if not os.path.isabs(out_path):
        out_path = os.path.join(HERE, out_path)

    if not os.path.exists(blend):
        print('[probe] FAIL 找不到 blend：' + blend)
        return 2

    bpy.ops.wm.open_mainfile(filepath=blend)
    scene = bpy.context.scene

    objs = {}
    missing = []
    for name in PART_NAMES:
        ob = scene.objects.get(name)
        if ob is None or ob.type != 'MESH':
            missing.append(name)
            continue
        objs[name] = ob

    if not objs:
        print('[probe] FAIL 场景里一个部件都没找到（期望 %s）' % (PART_NAMES,))
        return 2

    data = appearance.measure(objs)
    data['_meta'] = {
        'blend': os.path.basename(blend),
        'objects_found': sorted(objs),
        'objects_missing': missing,
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    # 控制台只打摘要，细节在 JSON 里
    def g(k):
        v = data.get(k)
        return 'None' if v is None else ('%.4f' % v if isinstance(v, float) else str(v))

    print('[probe] objects: %s%s' % (','.join(sorted(objs)),
                                     ('  MISSING=' + ','.join(missing)) if missing else ''))
    print('[probe] stature=%s head_len=%s heads_ratio=%s' %
          (g('stature'), g('head_len'), g('heads_ratio')))
    print('[probe] head_width=%s head_depth=%s neck_visible=%s' %
          (g('head_width'), g('head_depth'), g('neck_visible')))
    print('[probe] hair_back_ratio=%s @z=%s (厚 %s / 宽 %s)  hair_cap_gap=%s' %
          (g('hair_back_ratio'), g('hair_back_ratio_at_z'),
           g('hair_back_depth'), g('hair_back_width'), g('hair_cap_gap')))
    print('[probe] skirt_taper=%s' % g('skirt_taper'))
    print('[probe] OK -> %s' % out_path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
