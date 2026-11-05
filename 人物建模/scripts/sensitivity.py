# -*- coding: utf-8 -*-
"""数学模型研究配套工具：L2 参数的 ±10% 数值雅可比扫描。

做什么
------
`spec/head_parts.json` 的合同第 3 条要求「每个参数 ±10% 必须推动至少一条 gauge」。
这条不能靠嘴说，要测。本脚本逐个把参数改成 1.1× / 0.9×，重建头部，量全部
可测 gauge，输出相对变化矩阵：

    S[i][j] = (g_j(1.1p) − g_j(0.9p)) / g_j(p)

判读：
  · 某参数对所有 gauge 的 |S| < 0.001 → 要么它是假参数，要么**缺量尺**。
    两者都要处理：删参数，或补该部件自己的 gauge。
  · |S| 大的参数 = 高杠杆，改它最省事，但也最容易把别的判据带崩。

用法（项目根下，Blender 5.2）：
    "D:/Program Files/Blender Foundation/Blender 5.2/blender.exe" \
        -b --factory-startup --python-exit-code 1 --python scripts/sensitivity.py

产物：out/sensitivity.json
"""
import json
import os
import sys
import time

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "lib"))

import head as headmod          # noqa: E402
import mats as matsmod          # noqa: E402
import head_parts._base as B    # noqa: E402
from head_parts import nose, ear, jaw, cheek   # noqa: E402

OUT = os.path.join(ROOT, "out", "sensitivity.json")

# (合同里的参数名, 模块, 模块属性名)
PARAMS = [
    ("eye.eye_w_r", B, "EYE_W"),
    ("eye.eye_x_mm", B, "EYE_X"),
    ("eye.eye_h_up_r", B, "EYE_HU"),
    ("lips.mouth_w_r", B, "MOUTH_HALF_W"),
    ("nose.tip_fwd_mm", nose, "TIP_FWD"),
    ("nose.bridge_h_mm", nose, "BRIDGE_H"),
    ("ear.ear_h_r", ear, "EAR_RZ"),
    ("ear.rim_mm", ear, "RIM_OUT"),
    ("jaw.jaw_inset_mm", jaw, "JAW_INSET"),
    ("jaw.chin_fwd_mm", jaw, "CHIN_FWD"),
    ("cheek.cheek_out_mm", cheek, "CHEEK_OUT_CAGE"),
    ("cheek.cheek_fwd_mm", cheek, "CHEEK_FWD"),
]


def _verts_by_mat(ob, name):
    idx = {i for i, m in enumerate(ob.data.materials)
           if m is not None and m.name.split(".")[0] == name}
    vi = set()
    for p in ob.data.polygons:
        if p.material_index in idx:
            vi.update(p.vertices)
    return [ob.data.vertices[i].co.copy() for i in vi]


def _front_y(cos, lo, hi, xmax=0.003):
    sel = [c.y for c in cos if abs(c.x) < xmax and lo <= c.z <= hi and c.y < 0]
    return min(sel) if sel else None


def _ring_width(cos, zc, tol=0.008):
    xs = [c.x for c in cos if abs(c.z - zc) <= tol]
    return (max(xs) - min(xs)) if xs else 0.0


def gauges():
    """重建一次头部，返回全部可测量尺。"""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    M = matsmod.set_all()

    skull = headmod.head_base()
    headmod.sculpt(skull)
    cos = [v.co.copy() for v in skull.data.vertices]
    xs = [c.x for c in cos]
    ys = [c.y for c in cos]
    zs = [c.z for c in cos]
    head_len = max(zs) - min(zs)
    skull_w = max(xs) - min(xs)

    ny = _front_y(cos, B.sz(1.440), B.sz(1.470))
    fy = _front_y(cos, B.sz(1.520), B.sz(1.570))
    nose_mm = 1000.0 * (fy - ny) if None not in (ny, fy) else 0.0

    jaw_w = _ring_width(cos, B.sz(1.440)) / skull_w
    cheek_w = _ring_width(cos, B.sz(1.472)) / skull_w

    h = headmod.build(M)
    hx = [v.co.x for v in h.data.vertices]
    hy = [v.co.y for v in h.data.vertices]
    head_w = max(hx) - min(hx)
    head_d = max(hy) - min(hy)

    sclera = _verts_by_mat(h, "sclera")
    eye_ratio = eye_w_mm = 0.0
    eye_aspect = 0.0
    if sclera:
        rx = [c.x for c in sclera if c.x > 0]
        lx = [c.x for c in sclera if c.x < 0]
        inner = min(rx) - max(lx)
        ew = (max(rx) - min(rx) + max(lx) - min(lx)) / 2.0
        eye_ratio = inner / ew if ew else 0.0
        eye_w_mm = 1000.0 * ew
        ehs = [c.z for c in sclera]
        # ew 已经是单眼全宽（almond 的 x = w·cos，跨度 2w），不要再乘 2。
        eye_aspect = ((max(ehs) - min(ehs)) / ew) if ew else 0.0
    lip = _verts_by_mat(h, "lip")
    mouth_ratio = ((max(c.x for c in lip) - min(c.x for c in lip)) / head_w) if lip else 0.0

    eo = headmod.ear(-1, M)
    ez = [v.co.z for v in eo.data.vertices]
    ex = [v.co.x for v in eo.data.vertices]
    chin_pts = [c.y for c in cos if c.z < B.sz(1.410) and abs(c.x) < 0.020]
    # 颧骨专属量尺：只取颧骨 x 带。取整个 z 环的 min(y) 会被鼻尖主导，
    # 测不到颧骨前推 —— 这就是「参数假」与「量尺缺」最容易混淆的地方。
    cheek_pts = [c.y for c in cos if abs(c.z - B.sz(1.472)) <= 0.008
                 and 0.060 <= abs(c.x) <= 0.095 and c.y < 0]

    return {
        "head_len": head_len,
        "head_width": head_w,
        "head_depth": head_d,
        "head_w_over_len": head_w / head_len,
        "skull_width": skull_w,
        "inner_eye_over_eye_width": eye_ratio,
        "eye_width_mm": eye_w_mm,
        "eye_aspect": eye_aspect,
        "mouth_over_face": mouth_ratio,
        "ear_height_mm": 1000.0 * (max(ez) - min(ez)),
        "ear_x_span_mm": 1000.0 * (max(ex) - min(ex)),
        "nose_protrusion_mm": nose_mm,
        "jaw_width_r": jaw_w,
        "cheek_width_r": cheek_w,
        "chin_front_y_mm": 1000.0 * min(chin_pts) if chin_pts else 0.0,
        "cheek_front_y_mm": 1000.0 * min(cheek_pts) if cheek_pts else 0.0,
    }


def main():
    t0 = time.monotonic()
    base = gauges()
    print("[sens] 基线量尺：" + "  ".join("%s=%.4f" % (k, v) for k, v in base.items()))

    rows = []
    for label, mod, attr in PARAMS:
        p0 = getattr(mod, attr)
        out = {"param": label, "default": p0, "sensitivity": {}}
        gp, gm = {}, {}
        try:
            setattr(mod, attr, p0 * 1.1)
            gp = gauges()
            setattr(mod, attr, p0 * 0.9)
            gm = gauges()
        finally:
            setattr(mod, attr, p0)
        for k in base:
            denom = abs(base[k]) if abs(base[k]) > 1e-9 else 1.0
            s = (gp[k] - gm[k]) / denom
            if abs(s) > 1e-5:
                out["sensitivity"][k] = round(s, 6)
        moved = [k for k, v in out["sensitivity"].items() if abs(v) >= 0.001]
        out["moved"] = moved
        out["verdict"] = "OK" if moved else "NO-GAUGE"
        rows.append(out)
        print("[sens] %-24s %-10s %s" % (
            label, out["verdict"], ", ".join("%s=%+.3f" % (k, v) for k, v in
                                           list(out["sensitivity"].items())[:6])))

    doc = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "baseline": {k: round(v, 6) for k, v in base.items()},
        "note": "S[i][j] = (g(1.1p)-g(0.9p))/g(p)；NO-GAUGE 表示 ±10% 推不动任何已实现的量尺 —— 要么参数假，要么缺量尺。",
        "rows": rows,
        "elapsed_s": round(time.monotonic() - t0, 1),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(doc, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    n_dead = sum(r["verdict"] == "NO-GAUGE" for r in rows)
    print("[sens] %d 个参数中 %d 个 NO-GAUGE；耗时 %.1fs；报告 %s"
          % (len(rows), n_dead, doc["elapsed_s"], OUT))


if __name__ == "__main__":
    main()
