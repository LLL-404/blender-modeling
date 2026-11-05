# -*- coding: utf-8 -*-
"""头部基线冻结：把「现在的头」变成可逐点比对的快照。

为什么要这支脚本
----------------
`docs/头部L2拆分.md` 的 phase 0。拆 `lib/head.py` 之前必须有一个**逐顶点**的
对照物，否则「搬代码没改几何」只能靠嘴说。顶点坐标 hash 比 bbox 严格：bbox
不变但顶点挪了 0.3mm 的情况，bbox 查不出来。

输出 `out/head_baseline.json`：
  · hash         Head 全网格顶点坐标（6 位小数）sha1
  · skull_hash   只算颅骨壳（不含眼/眉/嘴/耳）
  · counts       顶点/面数
  · bbox         各部件包围盒（mm）
  · gauges       合同里能直接算的量：头长/宽/深、眼距比、嘴宽比、耳高、鼻尖前伸
  · scale        head_scale / head_shift / sz 采样

用法（项目根下）：
    "D:/Program Files/Blender Foundation/Blender 5.2/blender.exe" \
        -b --factory-startup --python-exit-code 1 --python scripts/head_baseline.py
    python scripts/head_baseline.py --check   # 用系统 Python 比对两次快照

--check 读 out/head_baseline.json 与 out/head_baseline_prev.json，报 hash 是否一致。
"""
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out", "head_baseline.json")
PREV = os.path.join(HERE, "out", "head_baseline_prev.json")


def check():
    """系统 Python 也能跑：只读 JSON，不 import bpy。"""
    if not (os.path.isfile(OUT) and os.path.isfile(PREV)):
        print("[baseline] 需要两次快照：%s 与 %s" % (OUT, PREV))
        return 2
    a = json.load(open(OUT, encoding="utf-8"))
    b = json.load(open(PREV, encoding="utf-8"))
    same = a["hash"] == b["hash"] and a["skull_hash"] == b["skull_hash"]
    print("[baseline] 本次 %s  上次 %s  -> %s" % (
        a["hash"], b["hash"], "一致" if same else "不一致"))
    for k in a["gauges"]:
        va, vb = a["gauges"][k], b["gauges"][k]
        if va != vb:
            print("  gauge %-24s %s -> %s" % (k, vb, va))
    return 0 if same else 1


if "--check" in sys.argv:
    raise SystemExit(check())

import bpy  # noqa: E402

sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import head as headmod   # noqa: E402
import mats as matsmod   # noqa: E402


def _bbox(ob):
    vs = [v.co for v in ob.data.vertices]
    if not vs:
        return None
    return {
        "min": [round(min(v[i] for v in vs) * 1000.0, 3) for i in range(3)],
        "max": [round(max(v[i] for v in vs) * 1000.0, 3) for i in range(3)],
        "n": len(vs),
    }


def _hash(ob, nd=6):
    h = hashlib.sha1()
    for v in ob.data.vertices:
        h.update(("%.*f,%.*f,%.*f;" % (nd, v.co.x, nd, v.co.y, nd, v.co.z)).encode())
    return h.hexdigest()[:16]


def _verts_by_mat(ob, name):
    idx = {i for i, m in enumerate(ob.data.materials)
           if m is not None and m.name.split(".")[0] == name}
    vi = set()
    for p in ob.data.polygons:
        if p.material_index in idx:
            vi.update(p.vertices)
    return [ob.data.vertices[i].co.copy() for i in vi]


def _mid_front_y(cos, lo, hi, xmax=0.003):
    sel = [c.y for c in cos if abs(c.x) < xmax and lo <= c.z <= hi and c.y < 0]
    return min(sel) if sel else None


def measure():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    M = matsmod.set_all()

    skull = headmod.head_base()
    headmod.sculpt(skull)
    cos = [v.co.copy() for v in skull.data.vertices]
    xs = [c.x for c in cos]
    ys = [c.y for c in cos]
    zs = [c.z for c in cos]
    head_len = max(zs) - min(zs)
    head_w = max(xs) - min(xs)
    head_d = max(ys) - min(ys)

    z_nose = (_mid_front_y(cos, headmod.sz(1.440), headmod.sz(1.470)),
              _mid_front_y(cos, headmod.sz(1.520), headmod.sz(1.570)))
    nose_mm = (1000.0 * (z_nose[1] - z_nose[0])
               if None not in z_nose else None)

    h = headmod.build(M)          # 含眼/眉/嘴/耳，join 成 Head
    # 口径：spec/reference.json 的「头宽」是含耳的 Head bbox（历史值 0.2139 vs
    # 头骨 0.2062，耳贡献 5.75mm/侧）。骨架宽度单独记，别混。
    hx = [v.co.x for v in h.data.vertices]
    hy = [v.co.y for v in h.data.vertices]
    hz = [v.co.z for v in h.data.vertices]
    head_w_full = max(hx) - min(hx)
    head_d_full = max(hy) - min(hy)
    head_len_full = max(hz) - min(hz)
    sclera = _verts_by_mat(h, "sclera")
    mouth_w = None
    eye_ratio = None
    eye_w = None
    eye_aspect = None
    if sclera:
        rx = [c.x for c in sclera if c.x > 0]
        lx = [c.x for c in sclera if c.x < 0]
        inner = min(rx) - max(lx)
        eye_w = (max(rx) - min(rx) + max(lx) - min(lx)) / 2.0
        eye_ratio = inner / eye_w if eye_w else None
        ehs = [c.z for c in sclera]
        # ew 已是单眼全宽（almond 的 x = w·cos，跨度 2w），不要乘 2。
        eye_aspect = ((max(ehs) - min(ehs)) / eye_w) if eye_w else None
    lip = _verts_by_mat(h, "lip")
    if lip:
        mouth_w = max(c.x for c in lip) - min(c.x for c in lip)

    # 灵敏度研究补的量尺：这些之前全缺，导致 eye_h_up / cheek_fwd 被误判成
    # 「假参数」。颧骨必须只取 x 带，取整个 z 环的 min(y) 会被鼻尖主导。
    skull_w = max(c.x for c in cos) - min(c.x for c in cos)

    def ring_width(zc, tol=0.008):
        xs = [c.x for c in cos if abs(c.z - zc) <= tol]
        return (max(xs) - min(xs)) / skull_w if xs else None

    jaw_w_r = ring_width(headmod.sz(1.440))
    cheek_w_r = ring_width(headmod.sz(1.472))
    chin_pts = [c.y for c in cos if c.z < headmod.sz(1.410) and abs(c.x) < 0.020]
    cheek_pts = [c.y for c in cos if abs(c.z - headmod.sz(1.472)) <= 0.008
                 and 0.060 <= abs(c.x) <= 0.095 and c.y < 0]

    ear = headmod.ear(-1, M)
    ezs = [v.co.z for v in ear.data.vertices]
    exs = [v.co.x for v in ear.data.vertices]

    doc = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "blender": bpy.app.version_string,
        "hash": _hash(h),
        "skull_hash": _hash(skull),
        "counts": {"head_v": len(h.data.vertices), "head_f": len(h.data.polygons),
                   "skull_v": len(skull.data.vertices), "skull_f": len(skull.data.polygons)},
        "bbox_mm": {"skull": _bbox(skull), "head": _bbox(h), "ear_L": _bbox(ear)},
        "scale": {"head_scale": round(headmod._head_scale(), 6),
                  "head_shift": round(headmod._head_shift(), 6),
                  "sz_1.500": round(headmod.sz(1.500), 6),
                  "sz_1.440": round(headmod.sz(1.440), 6)},
        "gauges": {
            "head_len": round(head_len, 6),
            "head_width": round(head_w_full, 6),
            "head_depth": round(head_d_full, 6),
            "head_w_over_len": round(head_w_full / head_len_full, 6),
            "head_len_over_depth": round(head_len_full / head_d_full, 6),
            "skull_width": round(head_w, 6),
            "skull_w_over_len": round(head_w / head_len, 6),
            "inner_eye_over_eye_width": round(eye_ratio, 6) if eye_ratio else None,
            "eye_width_mm": round(1000.0 * eye_w, 3) if eye_w else None,
            "eye_aspect": round(eye_aspect, 6) if eye_aspect else None,
            "mouth_over_face": round(mouth_w / head_w_full, 6) if mouth_w else None,
            "ear_height_mm": round(1000.0 * (max(ezs) - min(ezs)), 3),
            "ear_x_span_mm": round(1000.0 * (max(exs) - min(exs)), 3),
            "nose_protrusion_mm": round(nose_mm, 3) if nose_mm is not None else None,
            "jaw_width_r": round(jaw_w_r, 6) if jaw_w_r else None,
            "cheek_width_r": round(cheek_w_r, 6) if cheek_w_r else None,
            "chin_front_y_mm": round(1000.0 * min(chin_pts), 3) if chin_pts else None,
            "cheek_front_y_mm": round(1000.0 * min(cheek_pts), 3) if cheek_pts else None,
        },
        "_caliber": "head_width/depth/w_over_len 用含耳的 Head bbox（与 spec/reference.json 同口径）；skull_* 是头骨本体。cheek_front_y 只取 |x|∈[60,95]mm 的颧骨带，避免被鼻尖主导。",
        "_note": "phase 0 基线。拆 head.py 之后要求 hash 完全一致；归一化阶段允许变，但要逐条报哪些 gauge 动了。",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if os.path.isfile(OUT):
        os.replace(OUT, PREV)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
    print("[baseline] hash=%s skull=%s v=%d f=%d" % (
        doc["hash"], doc["skull_hash"], doc["counts"]["head_v"], doc["counts"]["head_f"]))
    for k, v in doc["gauges"].items():
        print("  %-26s %s" % (k, v))
    print("[baseline] -> %s" % OUT)


if __name__ == "__main__":
    measure()
