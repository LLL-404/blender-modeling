# -*- coding: utf-8 -*-
"""opt/eval_pixel.py —— 单次像素评估（Blender 进程内，含 3 张渲染）。

量什么（全部落到 `[eval] key=value` 单行 + opt/trials_pixel.jsonl）：
  1. **描边暗带**（C1 口径）：`m3_body_q34` 同参数机位，沿每行前景左右边界 ±8px 窗内
     量「亮度<40」的最长连续带，取全图 p50（目标 2~4px）。
  2. **皮肤色阶**（C3 口径）：`m3_face_front` 同参数机位，按 toon 三档显示色分类出皮肤
     像素，量 p5/p50/p95 与 ≥228 占比。
  3. **轮廓亮带**（C4 收口的新口径）：跳过描边壳、沿垂直于轮廓方向向内找「先升后降」的
     亮带，宽度 = 连续 `lum > 主体亮度+8` 的像素数；对**深色区域**分别报
        · 藏青裙 z 0.65~1.05（body_front 正对机位，世界↔像素可精确反投影）
        · 头发   z 1.40~1.62（face_front 正对机位）
     另在 body_q34 上用 c_probe 的 `subject_max=150` 口径报一份，便于与 C 阶段旧数字对照。

渲染纪律：
  * 每次评估开头 `shots.reset()`（= `read_factory_settings(use_empty=True)`），禁止状态复用；
  * 所有图写 `opt/tmp/`，**绝不碰 `out/m3_*.png`**（正式产物只在全部搜索结束后重渲一次）；
  * 分辨率：默认按**正式分辨率**渲染（560×900 / 620×780），因此 px 指标与 out/ 里的
    正式产物同口径、**不需要换算**。若要加速可改 `RES_SCALE`（见下），那时的换算式是
        px_正式 = px_实测 × (res_正式 / res_实测)
    因为描边厚度是按 `set_outline_px(ortho, res_y)` 反算的：**同一视图内线宽的像素数
    与分辨率无关**，但按低分辨率反算会得到更薄的世界厚度，于是实测 px 按比例缩小。
    亮度分位（p50/p5/p95/≥228 占比）与分辨率无关，不需要换算。

进程内只用 numpy，**不 import scipy**。
"""
import argparse
import json
import math
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, ROOT, os.path.join(ROOT, "lib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np          # noqa: E402
import bpy                  # noqa: E402

import optio                # noqa: E402
import space_pixel          # noqa: E402

TMP = os.path.join(HERE, "tmp")
TRIALS_PATH = os.path.join(HERE, "trials_pixel.jsonl")

# 1.0 = 按正式分辨率渲染（px 指标直接可比，无需换算）。设成 0.8 时按上面注释换算。
RES_SCALE = 1.0

# ---------------- 判定门限（与任务书一致） ----------------
HARD = {
    "edge_p50": (2.0, 4.0),      # px
    "skin_p50": (175.0, 215.0),  # 亮度
    "skin_p95_m50": 30.0,        # p95 − p50 >= 30
    "skin_p50_m5": 25.0,         # p50 − p5 >= 25
    "skin_ge228_pct": 35.0,      # >=228 的皮肤像素占比 <= 35%
}
SOFT = {
    "edge_target": 3.0,
    "skin_target": 195.0,
    "skin_scale": 10.0,
    "rim_target_px": 1.0,        # rim_band_px >= 1 才开始不罚
    "rim_weight": 8.0,           # 次要项：远小于 1e6 硬约束
}

# ---------------- 机位（必须与 m3_look.py 的正式机位逐字一致） ----------------
VIEWS = {
    "body_q34": dict(w=560, h=900, ortho=1.78, zc=0.86, frontal=False,
                     cam=(2.3, -2.5, 1.0), tgt=(0.0, 0.0, 0.86)),
    "face_front": dict(w=620, h=780, ortho=0.30, zc=1.4956, frontal=True,
                       cam=(0.0, -2.0, 1.4956), tgt=(0.0, 0.0, 1.4956)),
    "body_front": dict(w=560, h=900, ortho=1.80, zc=0.86, frontal=True,
                       cam=(0.0, -3.4, 0.86), tgt=(0.0, 0.0, 0.86)),
}

# 皮肤 toon 三档显示色（与 _stageC/c_probe.py:63-68 同源）。C3 只改 pos 与灯强，
# 不改 base/ramp 色，所以这三档色全程稳定 —— 用它做分类比绝对亮度阈值稳。
SKIN_TIERS = [
    ("shadow", (198, 175, 191)),
    ("mid", (235, 202, 196)),
    ("light", (247, 224, 211)),
]
TIER_DIST = 38.0


# ================================================================ 场景

def make_scene():
    """按 m3_look.py 的顺序建角色与灯光，返回 {objs, mods}。"""
    import shots
    import look
    import head as headmod
    import body as bodymod
    import hair as hairmod
    import outfit as outfitmod

    shots.reset()                      # = read_factory_settings(use_empty=True)
    shots.setup_studio()
    shots.world(color=(0.035, 0.045, 0.070), strength=1.0)
    shots.stage_c_lights()             # key / rim / rim_azimuth 在这里注入
    sc = bpy.context.scene
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'

    M = look.set_all()                 # skin 三档 pos 在这里注入
    h = headmod.build(M)
    look.flatten_face(h)
    b = bodymod.build()
    b.data.materials.append(M["skin"])
    look.bind_hands(M)
    hair = hairmod.build(M)
    cloth = outfitmod.build(M)

    OL = look.outline_mat()
    objs, mods = [], []
    for ob in (h, b, bpy.data.objects.get("Hands"), hair, cloth):
        if ob is not None:
            objs.append(ob)
            mods.append(look.add_outline(ob, OL, thickness=0.008))
    look.bloom(threshold=0.88, size=8)
    return {"objs": objs, "mods": mods}


def render_view(S, name, tag):
    """按正式机位渲一张到 opt/tmp/，返回路径。"""
    import shots
    import look
    v = VIEWS[name]
    rw = max(64, int(round(v["w"] * RES_SCALE)))
    rh = max(64, int(round(v["h"] * RES_SCALE)))
    shots.set_res(rw, rh)
    look.set_outline_px(S["objs"], S["mods"], v["ortho"], rh, base_px=3.5,
                        per_obj_px={"Head": 3.5})
    cam = shots.camera("cam_" + name, v["cam"], v["tgt"], ortho_scale=v["ortho"])
    sc = bpy.context.scene
    sc.camera = cam
    os.makedirs(TMP, exist_ok=True)
    path = os.path.join(TMP, f"{name}_{tag}.png")
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    return path


# ================================================================ 像素工具

def read_rgb(path):
    """读 PNG → uint8 RGB (top-down)。两个坑：pixels 是 sRGB 编码值、且是 bottom-up。"""
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    a = (np.clip(buf.reshape(h, w, 4)[:, :, :3], 0.0, 1.0) * 255.0 + 0.5
         ).astype(np.uint8)[::-1]
    bpy.data.images.remove(img)
    return a


def lum_of(a):
    af = a.astype(np.float32)
    return 0.2126 * af[:, :, 0] + 0.7152 * af[:, :, 1] + 0.0722 * af[:, :, 2]


def fg_mask(a):
    """前景掩码。背景 = 四角中位色（与 c_probe 一致）；若四角中位色偏亮
    （>120，说明角上已经踩到角色/地板高光）则改用**最暗**那一角，避免整图被判成前景。
    """
    pts = [a[:8, :8].reshape(-1, 3), a[:8, -8:].reshape(-1, 3),
           a[-8:, :8].reshape(-1, 3), a[-8:, -8:].reshape(-1, 3)]
    meds = [np.median(p.astype(np.float32), axis=0) for p in pts]
    lum = lambda c: 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    bg = np.median(np.concatenate([p.astype(np.float32) for p in pts]), axis=0)
    if lum(bg) > 120.0:
        bg = min(meds, key=lum)
    return np.abs(a.astype(np.float32) - bg).max(axis=2) > 18


def skin_tiers(a):
    af = a.astype(np.float32)
    d = np.stack([np.sqrt(((af - np.array(c, dtype=np.float32)) ** 2).sum(axis=2))
                  for _, c in SKIN_TIERS], axis=0)
    idx = np.argmin(d, axis=0)
    dist = d.min(axis=0)
    return dist < TIER_DIST, idx, dist


def edge_dark_width(a, tag_win=8, dark_thr=40.0):
    """C1 口径：每行前景左右边界 ±tag_win 窗内「亮度<dark_thr」的最长连续带。"""
    h, w = a.shape[:2]
    lum = lum_of(a)
    fg = fg_mask(a)
    dark = lum < dark_thr
    runs = []
    for y in range(30, h - 30):
        xs = np.where(fg[y])[0]
        if len(xs) < 8:
            continue
        for xb in (xs[0], xs[-1]):
            if xb < tag_win or xb > w - tag_win - 1:
                continue
            cur = best = 0
            for v in dark[y, xb - tag_win:xb + tag_win + 1]:
                cur = cur + 1 if v else 0
                best = max(best, cur)
            runs.append(best)
    if not runs:
        return None
    r = np.array(runs)
    return dict(n=int(len(r)), p25=float(np.percentile(r, 25)),
                p50=float(np.percentile(r, 50)),
                p75=float(np.percentile(r, 75)), mx=int(r.max()),
                zero=int((r == 0).sum()))


def skin_stats(a):
    """C3 口径：皮肤像素的 p5/p50/p95 与 ≥228 占比。"""
    skin, idx, _ = skin_tiers(a)
    n = int(skin.sum())
    if n == 0:
        return None
    ls = lum_of(a)[skin]
    p5, p50, p95 = np.percentile(ls, [5, 50, 95])
    return dict(n=n, p5=float(p5), p50=float(p50), p95=float(p95),
                ge228=float((ls >= 228).mean() * 100.0),
                p50m5=float(p50 - p5), p95m50=float(p95 - p50),
                tiers={name: float((idx[skin] == i).mean() * 100.0)
                       for i, (name, _) in enumerate(SKIN_TIERS)})


def rim_band(a, zr=None, zc=None, vh=None, ortho=None,
             dark_max=150.0, gain=8.0, scan=14, skip_max=12, step=1):
    """轮廓亮带宽度（px）—— **C4 收口后定义的新口径**。

    步骤（写死，避免口径漂移）：
      1. 逐行（隔 step 行）取前景左右边界 xb；
      2. **跳过描边壳**：从 xb 向内跳过连续 `lum<70` 的像素（最多 skip_max px）；
         不跳的话第一个像素永远是 3~4px 的黑色描边壳，量到的一律是 0；
      3. 主体亮度 base = 向内 [k+6, k+20] 的中位亮度；base > dark_max 的行**跳过**
         （只量深色主体：藏青裙≈44 / 头发≈90。白衬衫与皮肤已在 light 档 ~227，
         rim 加不亮，混进来只会稀释样本）；
      4. 向内扫 scan px，找第一段连续 `lum > base+gain` 的像素，且其后必须**回落到**
         base+gain 以下（「先升后降」）；一直亮到窗口末端的不算（那是整片亮面，不是亮带）；
      5. 宽度 = 该连续段的像素数。

    返回 dict(n, rows, p50, p90, max, zero_pct)。n 是「有亮带可量的行数」，
    rows 是「通过深色主体筛选的行数」。
    """
    h, w = a.shape[:2]
    lum = lum_of(a)
    fg = fg_mask(a)
    widths = []
    rows = 0
    s = (float(vh) / float(ortho)) if (ortho and vh) else None
    for y in range(40, h - 40, max(1, step)):
        if zr is not None:
            if s is None:
                continue
            z = zc + (h / 2.0 - y) / s
            if not (zr[0] <= z <= zr[1]):
                continue
        xs = np.where(fg[y])[0]
        if len(xs) < 20:
            continue
        for xb, d in ((xs[0], 1), (xs[-1], -1)):
            k = 0
            while (k < skip_max and 0 <= xb + d * (k + 1) < w
                   and lum[y, xb + d * (k + 1)] < 70.0):
                k += 1
            i0, i1 = xb + d * (k + 6), xb + d * (k + 20)
            if not (0 <= i0 < w and 0 <= i1 < w):
                continue
            base = float(np.median(lum[y, min(i0, i1):max(i0, i1) + 1]))
            if base > dark_max:
                continue
            rows += 1
            run = best = 0
            dropped = False
            for j in range(k + 1, k + 1 + scan):
                x = xb + d * j
                if not (0 <= x < w):
                    break
                if lum[y, x] > base + gain:
                    run += 1
                    best = max(best, run)
                elif run:
                    dropped = True
                    break
            if best and dropped:
                widths.append(best)
    if not widths:
        return dict(n=0, rows=rows, p50=0.0, p90=0.0, max=0, zero_pct=100.0)
    ww = np.array(widths, dtype=np.float32)
    return dict(n=int(len(ww)), rows=rows,
                p50=float(np.percentile(ww, 50)),
                p90=float(np.percentile(ww, 90)),
                max=int(ww.max()),
                zero_pct=float((ww == 0).mean() * 100.0))


def rim_lit(a_on, a_off, zr=None, zc=None, vh=None, ortho=None,
            dark_max=150.0, gain=8.0, scan=14, skip_max=12, step=1):
    """轮廓光**差分口径**（T20）：同一机位「rim 灯 开(E) / 关(0)」两张图的亮度差。

    为什么必须差分（实测证据）：旧口径（rim_band，绝对亮度）在 **rim_energy=0** 时
    仍量到 rim_skirt_p50=10.0 / rim_hair_p50=11.0，与 rim=80W 完全相同 —— toon 三档把
    「裙褶亮面」渲染成 ≥8 的亮度台阶，绝对亮度口径量的是裙子自身的色阶，不是轮廓光。
    差分后色阶亮面在两张图里完全相同，差值恒为 0，只有 rim 灯真正点亮的像素才计数。

    步骤（与 rim_band 保持同一几何口径，只把「亮度」换成「亮度差」）：
      1. 前景掩码用**关灯图**（rim 灯不应改变 silhouette）；
      2. 跳描边壳：从边界向内跳过连续 `lum_off<70` 的像素（最多 skip_max px）；
      3. base 取**关灯图** [k+6, k+20] 的中位亮度；base > dark_max 的行跳过
         （只量深色主体：藏青裙≈44 / 头发≈90）；
      4. 向内扫 scan px，找第一段连续 `lum_on − lum_off >= gain` 的像素，且其后
         必须**回落到 gain 以下**（「先升后降」；一直亮到窗口末端的是整片抬亮，不算）；
      5. 宽度 = 该连续段的像素数。

    返回 dict(n, rows, p50, p90, max, zero_pct)，语义同 rim_band。
    """
    h, w = a_on.shape[:2]
    lum_on = lum_of(a_on)
    lum_off = lum_of(a_off)
    d = lum_on - lum_off
    fg = fg_mask(a_off)
    widths = []
    rows = 0
    s = (float(vh) / float(ortho)) if (ortho and vh) else None
    for y in range(40, h - 40, max(1, step)):
        if zr is not None:
            if s is None:
                continue
            z = zc + (h / 2.0 - y) / s
            if not (zr[0] <= z <= zr[1]):
                continue
        xs = np.where(fg[y])[0]
        if len(xs) < 20:
            continue
        for xb, dd in ((xs[0], 1), (xs[-1], -1)):
            k = 0
            while (k < skip_max and 0 <= xb + dd * (k + 1) < w
                   and lum_off[y, xb + dd * (k + 1)] < 70.0):
                k += 1
            i0, i1 = xb + dd * (k + 6), xb + dd * (k + 20)
            if not (0 <= i0 < w and 0 <= i1 < w):
                continue
            base = float(np.median(lum_off[y, min(i0, i1):max(i0, i1) + 1]))
            if base > dark_max:
                continue
            rows += 1
            run = best = 0
            dropped = False
            for j in range(k + 1, k + 1 + scan):
                x = xb + dd * j
                if not (0 <= x < w):
                    break
                if d[y, x] >= gain:
                    run += 1
                    best = max(best, run)
                elif run:
                    dropped = True
                    break
            if best and dropped:
                widths.append(best)
    if not widths:
        return dict(n=0, rows=rows, p50=0.0, p90=0.0, max=0, zero_pct=100.0)
    ww = np.array(widths, dtype=np.float32)
    return dict(n=int(len(ww)), rows=rows,
                p50=float(np.percentile(ww, 50)),
                p90=float(np.percentile(ww, 90)),
                max=int(ww.max()),
                zero_pct=float((ww == 0).mean() * 100.0))


def to_official_px(v):
    """低分辨率实测 px → 正式分辨率口径 px（RES_SCALE=1 时是恒等映射）。"""
    return v / RES_SCALE if RES_SCALE else v


# ================================================================ 打分

def score_of(m):
    """score = 1e6·硬违规数 + 软代价。"""
    hard = 0
    e = m.get("outline_p50")
    if e is None or not (HARD["edge_p50"][0] <= e <= HARD["edge_p50"][1]):
        hard += 1
    p50 = m.get("skin_p50")
    if p50 is None or not (HARD["skin_p50"][0] <= p50 <= HARD["skin_p50"][1]):
        hard += 1
    if (m.get("skin_p95_m50") or 0.0) < HARD["skin_p95_m50"]:
        hard += 1
    if (m.get("skin_p50_m5") or 0.0) < HARD["skin_p50_m5"]:
        hard += 1
    if (m.get("skin_ge228_pct") or 0.0) > HARD["skin_ge228_pct"]:
        hard += 1

    soft = 0.0
    if e is not None:
        soft += (e - SOFT["edge_target"]) ** 2
    if p50 is not None:
        soft += ((p50 - SOFT["skin_target"]) / SOFT["skin_scale"]) ** 2
    rim = m.get("rim_band_px") or 0.0
    soft += max(0.0, SOFT["rim_target_px"] - rim) * SOFT["rim_weight"]
    return hard, soft


# ================================================================ 单次评估

def evaluate(params, index=None, label="", write=True):
    """评估一组像素参数；params=None 表示走 opt/best.json（验证注入链路）。"""
    t0 = time.time()
    injection = "override" if params is not None else "best.json"
    if params is None:
        optio.reload()
        params = {d["key"]: optio.param(d["key"], d["default"])
                  for d in space_pixel.DIMS}
    rec = {"i": index, "label": label, "params": dict(params), "injection": injection}
    metrics = {}
    err = None
    try:
        if injection == "override":
            optio.set_overrides(params)
        else:
            optio.set_overrides(None)
            optio.reload()

        S = make_scene()
        tag = f"i{index}" if index is not None else "cli"
        p_q34 = render_view(S, "body_q34", tag)
        p_face = render_view(S, "face_front", tag)
        p_body = render_view(S, "body_front", tag)

        a_q34 = read_rgb(p_q34)
        a_face = read_rgb(p_face)
        a_body = read_rgb(p_body)

        # 轮廓光差分口径：把 rim 灯关掉后在**同两个机位**重渲一次（几何/材质/其它灯
        # 全不变，唯一变量就是 rim 灯能量）。这样色阶亮面在两张图里逐位相同、差值 0，
        # 只有 rim 灯真正点亮的像素进计数 —— 见 rim_lit() 的实测证据注释。
        rim_ob = bpy.data.objects.get("rim")
        rim_e = float(rim_ob.data.energy) if rim_ob is not None else 0.0
        if rim_ob is not None:
            rim_ob.data.energy = 0.0
        p_body_off = render_view(S, "body_front", tag + "_off")
        p_face_off = render_view(S, "face_front", tag + "_off")
        if rim_ob is not None:
            rim_ob.data.energy = rim_e
        a_body_off = read_rgb(p_body_off)
        a_face_off = read_rgb(p_face_off)

        ed = edge_dark_width(a_q34) or {}
        sk = skin_stats(a_face) or {}
        rim_skirt = rim_band(a_body, zr=(0.65, 1.05), zc=0.86,
                             vh=VIEWS["body_front"]["h"],
                             ortho=VIEWS["body_front"]["ortho"])
        rim_hair = rim_band(a_face, zr=(1.40, 1.62), zc=1.4956,
                            vh=VIEWS["face_front"]["h"],
                            ortho=VIEWS["face_front"]["ortho"])
        rim_q34 = rim_band(a_q34)     # 旧口径（不做 z 过滤，只按深色主体筛行）
        lit_skirt = rim_lit(a_body, a_body_off, zr=(0.65, 1.05), zc=0.86,
                            vh=VIEWS["body_front"]["h"],
                            ortho=VIEWS["body_front"]["ortho"])
        lit_hair = rim_lit(a_face, a_face_off, zr=(1.40, 1.62), zc=1.4956,
                           vh=VIEWS["face_front"]["h"],
                           ortho=VIEWS["face_front"]["ortho"])

        metrics = {
            "outline_p50": None if not ed else to_official_px(ed["p50"]),
            "outline_p25": None if not ed else to_official_px(ed["p25"]),
            "outline_p75": None if not ed else to_official_px(ed["p75"]),
            "outline_max": None if not ed else ed["mx"],
            "outline_zero_pct": None if not ed else round(
                100.0 * ed["zero"] / max(1, ed["n"]), 2),
            "outline_n": 0 if not ed else ed["n"],
            "skin_n": sk.get("n", 0),
            "skin_p5": None if not sk else round(sk["p5"], 2),
            "skin_p50": None if not sk else round(sk["p50"], 2),
            "skin_p95": None if not sk else round(sk["p95"], 2),
            "skin_p50_m5": None if not sk else round(sk["p50m5"], 2),
            "skin_p95_m50": None if not sk else round(sk["p95m50"], 2),
            "skin_ge228_pct": None if not sk else round(sk["ge228"], 2),
            "skin_tiers": None if not sk else {k: round(v, 1)
                                               for k, v in sk["tiers"].items()},
            "rim_skirt_p50": round(to_official_px(rim_skirt["p50"]), 2),
            "rim_skirt_max": rim_skirt["max"],
            "rim_skirt_n": rim_skirt["n"],
            "rim_skirt_rows": rim_skirt["rows"],
            "rim_hair_p50": round(to_official_px(rim_hair["p50"]), 2),
            "rim_hair_max": rim_hair["max"],
            "rim_hair_n": rim_hair["n"],
            "rim_hair_rows": rim_hair["rows"],
            "rim_q34_p50": round(to_official_px(rim_q34["p50"]), 2),
            "rim_q34_max": rim_q34["max"],
            "rim_q34_n": rim_q34["n"],
            # 差分口径（T20 起是**唯一**的轮廓光判定口径）
            "rim_lit_skirt_p50": round(to_official_px(lit_skirt["p50"]), 2),
            "rim_lit_skirt_max": lit_skirt["max"],
            "rim_lit_skirt_n": lit_skirt["n"],
            "rim_lit_skirt_rows": lit_skirt["rows"],
            "rim_lit_hair_p50": round(to_official_px(lit_hair["p50"]), 2),
            "rim_lit_hair_max": lit_hair["max"],
            "rim_lit_hair_n": lit_hair["n"],
            "rim_lit_hair_rows": lit_hair["rows"],
            "res_scale": RES_SCALE,
        }
        # 主 rim 指标：**差分口径**两处深色区域的较大者（任一处被 rim 灯点亮即算数）。
        # 旧口径（绝对亮度）保留为 *_legacy 只作历史对照，不参与打分与判定 ——
        # 实测它在 rim_energy=0 时仍报 10~11px（量的是裙子自身色阶），见 rim_lit()。
        metrics["rim_band_px"] = max(metrics["rim_lit_skirt_p50"],
                                     metrics["rim_lit_hair_p50"])
        metrics["rim_band_px_legacy"] = max(metrics["rim_skirt_p50"],
                                            metrics["rim_hair_p50"])
        hard, soft = score_of(metrics)
        score = 1e6 * hard + soft
    except Exception:
        tb = traceback.format_exc()
        lines = [ln for ln in tb.strip().splitlines() if ln.strip()]
        err = {"head": lines[0] if lines else "", "tail": lines[-1] if lines else ""}
        hard, soft, score = 5, 0.0, 1e9
        print(f"[eval] error=1 traceback_head={err['head']}")
        print(f"[eval] traceback_tail={err['tail']}")

    dt = time.time() - t0
    rec.update({"metrics": metrics, "hard": hard, "soft": round(soft, 6),
                "score": round(score, 6), "t": round(dt, 2)})
    if err:
        rec["error"] = err
    _print_eval(rec)
    if write:
        append_trial(rec)
    return rec


def _p(key, value, fmt="{:.4f}"):
    if value is None:
        s = "None"
    elif isinstance(value, float):
        s = fmt.format(value)
    else:
        s = str(value)
    print("[eval] " + key + "=" + s)


def _print_eval(rec):
    for k, v in rec["params"].items():
        _p("param_" + k, v)
    m = rec["metrics"]
    if m:
        _p("outline_p50", m["outline_p50"], "{:.2f}")
        _p("outline_p25", m["outline_p25"], "{:.2f}")
        _p("outline_p75", m["outline_p75"], "{:.2f}")
        _p("outline_zero_pct", m["outline_zero_pct"], "{:.1f}")
        _p("skin_p50", m["skin_p50"], "{:.2f}")
        _p("skin_p5", m["skin_p5"], "{:.2f}")
        _p("skin_p95", m["skin_p95"], "{:.2f}")
        _p("skin_p50_m5", m["skin_p50_m5"], "{:.2f}")
        _p("skin_p95_m50", m["skin_p95_m50"], "{:.2f}")
        _p("skin_ge228_pct", m["skin_ge228_pct"], "{:.2f}")
        _p("rim_skirt_p50", m["rim_skirt_p50"], "{:.2f}")
        _p("rim_skirt_max", m["rim_skirt_max"], "{}")
        _p("rim_hair_p50", m["rim_hair_p50"], "{:.2f}")
        _p("rim_hair_max", m["rim_hair_max"], "{}")
        _p("rim_q34_p50", m["rim_q34_p50"], "{:.2f}")
        _p("rim_lit_skirt_p50", m["rim_lit_skirt_p50"], "{:.2f}")
        _p("rim_lit_skirt_max", m["rim_lit_skirt_max"], "{}")
        _p("rim_lit_skirt_n", m["rim_lit_skirt_n"], "{}")
        _p("rim_lit_hair_p50", m["rim_lit_hair_p50"], "{:.2f}")
        _p("rim_lit_hair_max", m["rim_lit_hair_max"], "{}")
        _p("rim_lit_hair_n", m["rim_lit_hair_n"], "{}")
        _p("rim_band_px", m["rim_band_px"], "{:.2f}")
    _p("hard", rec["hard"], "{}")
    _p("soft", rec["soft"], "{:.4f}")
    _p("score", rec["score"], "{:.4f}")
    _p("t", rec["t"], "{:.2f}")


def append_trial(rec):
    os.makedirs(os.path.dirname(TRIALS_PATH), exist_ok=True)
    with open(TRIALS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")


# ================================================================ CLI

def _args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(prog="eval_pixel")
    ap.add_argument("--params", default=None)
    ap.add_argument("--use-best", action="store_true")
    ap.add_argument("--i", type=int, default=0)
    ap.add_argument("--label", default="cli")
    ap.add_argument("--no-write", action="store_true")
    return ap.parse_args(argv)


def main():
    a = _args()
    space_pixel.verify_defaults()
    if a.use_best:
        params = None
    elif a.params:
        params = json.loads(a.params)
    else:
        params = space_pixel.defaults()
    rec = evaluate(params, index=a.i, label=a.label, write=not a.no_write)
    print("[eval] done " + json.dumps(
        {"score": rec["score"], "params": rec["params"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()