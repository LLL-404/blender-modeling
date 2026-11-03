# -*- coding: utf-8 -*-
"""外观测量：把三维形状翻译成可比较的数字。

三条口径（改之前先读）
----------------------
1. **身高/头身比一律用「骨相头顶」（Head z_max），不用发顶。**
   呆毛比头顶高 46.5mm，用发顶会把 6.505 报成 6.69，和 DESIGN §1.2
   以及 `_stageA/a2_face_probe.py` 的口径全部对不上。发顶口径另报
   `stature_with_hair` / `heads_ratio_with_hair` 供视觉比对。
2. **躯体宽度取参数表（`cfg`），不实测 Body。**
   手臂在胸段已被 5mm 体素和躯干融成一体（间隙只剩 11mm），沿 x 扫描
   分不开；硬取 Body 全宽会把手臂算进腰宽，虚高约 2 倍。DESIGN 同口径。
3. **不渲染。** 剪影用顶点投影 + z 分桶，比像素法少一层采样误差，也快 10 倍。

已知差异（不是 bug，别重复排查）
--------------------------------
* `head_width` 实测 0.2172，`_stageA/logs/accept_geom.json` 记的是 0.2139。
  差 3.3mm 出现在耳部 —— 同一次日志里 `head_depth` 0.1883 与本次**完全一致**，
  说明测量方法没问题，是 A 阶段之后耳部几何被改过。

对外入口 `measure(objs)`：objs 是 {物体名: bpy 物体}。
返回**纯 Python 类型**，可直接 `json.dump`。
"""

# 躯干表顶部（body.TORSO 最高行）。可见颈长从这里量到下巴。
import math

TORSO_TOP_Z = 1.325


def _pts(ob):
    """世界坐标顶点列表 [(x, y, z), ...]。用 ob.data，不含修饰器。"""
    mw = ob.matrix_world
    return [tuple(mw @ v.co) for v in ob.data.vertices]


def _by_mat(ob):
    """按材质槽把网格顶点分桶 —— 眼睛/眉/嘴各有独立材质，能单独量。

    返回 {材质名: [(x,y,z), ...]}。用 ob.data（不含修饰器），与 _pts 同口径。
    """
    me = ob.data
    mw = ob.matrix_world
    slots = [s.material.name if s.material else '' for s in ob.material_slots]
    buckets = {}
    for poly in me.polygons:
        name = slots[poly.material_index] if poly.material_index < len(slots) else ''
        bucket = buckets.setdefault(name, set())
        for vi in poly.vertices:
            bucket.add(vi)
    return {k: [tuple(mw @ me.vertices[i].co) for i in v] for k, v in buckets.items()}


def _bbox(pts):
    if not pts:
        return None
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    return lo, hi


def _band(pts, zlo, zhi):
    return [p for p in pts if zlo <= p[2] <= zhi]


def _r(v, n=4):
    return None if v is None else round(float(v), n)


def profile(pts, n=64, zlo=None, zhi=None):
    """剪影剖面：按 z 等分 n 桶，每桶报 x 宽（正视）、y 厚（侧视）。

    一行同时给出正视宽度和侧视厚度，所以不需要分别跑两张图。
    """
    if not pts:
        return []
    if zlo is None:
        zlo = min(p[2] for p in pts)
    if zhi is None:
        zhi = max(p[2] for p in pts)
    if zhi <= zlo:
        return []
    step = (zhi - zlo) / n
    out = []
    for i in range(n):
        a = zlo + i * step
        b = a + step
        seg = [p for p in pts if a <= p[2] < b]
        if i == n - 1:
            seg = [p for p in pts if a <= p[2] <= b]
        if not seg:
            out.append(None)
            continue
        xs = [p[0] for p in seg]
        ys = [p[1] for p in seg]
        out.append({
            'z': _r((a + b) * 0.5),
            'xw': _r(max(xs) - min(xs)),
            'yd': _r(max(ys) - min(ys)),
            'y0': _r(min(ys)), 'y1': _r(max(ys)),
        })
    return out


def _hair_bands(hair_pts, n=40, z_lo=None, z_hi=None):
    """头发剖面，并在指定高度区间里找**最扁的一层**（厚/宽比最小处）。

    为什么用「厚/宽比」而不是绝对厚度：绝对厚度在发梢必然很小（发梢收尖是
    正常形态，实测 17mm / 宽 172mm），拿它当「板」的判据会一直误报。
    真正说明「像一块板」的是**又宽又薄**，即厚宽比塌下去。
    区间由调用方给（后脑中段），把发梢排除在外。
    """
    prof = [r for r in profile(hair_pts, n=n) if r]
    if not prof:
        return {'min_ratio': None, 'rows': []}
    cand = prof
    if z_lo is not None and z_hi is not None:
        cand = [r for r in prof if z_lo <= r['z'] <= z_hi] or prof
    worst = min(cand, key=lambda r: r['yd'] / max(r['xw'], 1e-6))
    return {
        'min_ratio': _r(worst['yd'] / max(worst['xw'], 1e-6)),
        'min_ratio_at_z': _r(worst['z']),
        'depth_there': _r(worst['yd']),
        'width_there': _r(worst['xw']),
        'rows': prof,
    }


def _cap_gap(head_pts, hair_pts):
    """发帽贴合度：头骨上 1/3 区域，头发比头骨多出的前后厚度。

    接近 0 = 头发是一层贴皮；15~25mm = 有体积的正常发帽。
    """
    hb = _bbox(head_pts)
    if hb is None or not hair_pts:
        return None
    lo, hi = hb
    zlo = lo[2] + (hi[2] - lo[2]) * 0.66
    hh = _band(head_pts, zlo, hi[2])
    hr = _band(hair_pts, zlo, hi[2])
    if not hh or not hr:
        return None
    return _r((max(p[1] for p in hr) - min(p[1] for p in hr))
              - (max(p[1] for p in hh) - min(p[1] for p in hh)))


def _skirt(outfit_pts, skirt_top=1.045):
    """裙摆锥度：裙腰与裙中段的半宽比。1.0 = 直筒，>1.1 = A 字外扩。

    采样点必须**紧贴裙腰下方**（1.035），不能取 1.00 —— 那里是衬衫下摆，
    取到的是衬衫宽度，会报出 1.66 这种假锥度（实测踩过）。
    裙中取 0.895，落在裙长区间 1.045~0.65 的前三分之一。
    """
    prof = [r for r in profile(outfit_pts, n=48) if r]
    if not prof:
        return {'taper': None, 'waist_half': None}
    a = min(prof, key=lambda r: abs(r['z'] - (skirt_top - 0.010)))
    b = min(prof, key=lambda r: abs(r['z'] - 0.895))
    if a['xw'] < 1e-6:
        return {'taper': None, 'waist_half': _r(a['xw'] / 2)}
    return {'taper': _r(b['xw'] / a['xw']),
            'waist_half': _r(a['xw'] / 2),
            'mid_half': _r(b['xw'] / 2),
            'waist_z': a['z'], 'mid_z': b['z']}


def measure(objs):
    """主入口。缺部件不报错，对应指标返回 None —— 要能在半成品场景上跑。"""
    import cfg

    P = {k: _pts(v) for k, v in objs.items()}
    res = {'parts': {k: len(v) for k, v in P.items()}}

    body = P.get('Body') or []
    head = P.get('Head') or []
    hair = P.get('Hair') or []
    outfit = P.get('Outfit') or []

    floor_z = min(p[2] for p in body) if body else 0.0
    hb = _bbox(head)
    head_len = (hb[1][2] - hb[0][2]) if hb else None
    skull_top = hb[1][2] if hb else None
    hair_top = max((p[2] for p in hair), default=None)

    # ---------------- 整体比例（骨相口径）----------------
    res['stature'] = _r(skull_top - floor_z) if skull_top else None
    res['stature_with_hair'] = _r(hair_top - floor_z) if hair_top else None
    res['head_top_z'] = _r(skull_top)
    res['chin_z'] = _r(hb[0][2]) if hb else None
    res['head_len'] = _r(head_len)
    res['heads_ratio'] = _r((skull_top - floor_z) / head_len) if head_len else None
    res['heads_ratio_with_hair'] = (_r((hair_top - floor_z) / head_len)
                                    if head_len and hair_top else None)
    res['leg_ratio'] = (_r(cfg.CROTCH_Z / (skull_top - floor_z))
                        if skull_top and skull_top > floor_z else None)

    # ---------------- 头 ----------------
    if hb:
        res['head_width'] = _r(hb[1][0] - hb[0][0])
        res['head_depth'] = _r(hb[1][1] - hb[0][1])
        res['head_w_over_len'] = _r((hb[1][0] - hb[0][0]) / head_len)
        res['head_len_over_depth'] = _r(head_len / (hb[1][1] - hb[0][1]))
    res['neck_visible'] = _r(hb[0][2] - TORSO_TOP_Z) if hb else None
    res['neck_over_head'] = (_r((hb[0][2] - TORSO_TOP_Z) / head_len)
                             if hb and head_len else None)

    # ---------------- 脸型（可见脸宽，避开耳廓）----------------
    # head_width 是整颗头含耳的包围盒宽度，和参考图里「能看见的脸」不是一个量。
    # 下脸区（下巴上 24%~46% 头长）耳廓已经不占宽度，这一带才是可比的脸宽。
    if hb and head_len:
        chin_z = hb[0][2]

        def _w_band(lo_f, hi_f):
            seg = [p for p in head if chin_z + lo_f * head_len <= p[2] <= chin_z + hi_f * head_len]
            if not seg:
                return None
            return max(p[0] for p in seg) - min(p[0] for p in seg)

        res['face_width_cheek'] = _r(_w_band(0.24, 0.46))
        res['face_width_jaw'] = _r(_w_band(0.10, 0.22))
        res['face_w_over_head'] = (_r(res['face_width_cheek'] / head_len)
                                   if res['face_width_cheek'] else None)
        res['jaw_over_cheek'] = (_r(res['face_width_jaw'] / res['face_width_cheek'])
                                 if res.get('face_width_cheek') else None)

    # ---------------- 五官（按材质槽分层量，参考图可比口径）----------------
    head_ob = objs.get('Head')
    if head_ob is not None and head_len:
        mats = _by_mat(head_ob)
        res['mat_names'] = sorted(k for k in mats if k)

        def _side_pts(pts):
            return ([p for p in pts if p[0] < 0], [p for p in pts if p[0] > 0])

        def _ext(pts):
            xs = [p[0] for p in pts]
            zs = [p[2] for p in pts]
            return {'w': max(xs) - min(xs), 'h': max(zs) - min(zs),
                    'cx': (max(xs) + min(xs)) / 2, 'cz': (max(zs) + min(zs)) / 2,
                    'x0': min(xs), 'x1': max(xs)}

        def _tilt(pts):
            """外眼角相对内眼角的高度差 → 上挑角（度）。正 = 外眼角高。"""
            if len(pts) < 6:
                return None
            xs = [p[0] for p in pts]
            x0, x1 = min(xs), max(xs)
            span = x1 - x0
            if span < 1e-6:
                return None
            left_eye = (sum(xs) / len(xs)) < 0
            if left_eye:
                outer = [p[2] for p in pts if p[0] <= x0 + span * 0.34]
                inner = [p[2] for p in pts if p[0] >= x1 - span * 0.34]
            else:
                outer = [p[2] for p in pts if p[0] >= x1 - span * 0.34]
                inner = [p[2] for p in pts if p[0] <= x0 + span * 0.34]
            if not outer or not inner:
                return None
            return math.degrees(math.atan2(sum(outer) / len(outer) - sum(inner) / len(inner),
                                           span * 0.66))

        iris = mats.get('iris') or []
        if iris:
            li, ri = _side_pts(iris)
            if li and ri:
                L, R = _ext(li), _ext(ri)
                eye_w = (L['w'] + R['w']) / 2
                eye_h = (L['h'] + R['h']) / 2
                res['eye_w'] = _r(eye_w)
                res['eye_h'] = _r(eye_h)
                res['eye_w_over_head'] = _r(eye_w / head_len)
                res['eye_h_over_w'] = _r(eye_h / eye_w) if eye_w else None
                res['eye_gap'] = _r(R['cx'] - L['cx'])
                res['eye_gap_over_head'] = _r((R['cx'] - L['cx']) / head_len)
                res['eye_cz'] = _r((L['cz'] + R['cz']) / 2)
                res['eye_from_chin'] = _r((res['eye_cz'] - hb[0][2]) / head_len)

        sclera = mats.get('sclera') or []
        if sclera:
            ls, rs = _side_pts(sclera)
            tl = [t for t in (_tilt(ls), _tilt(rs)) if t is not None]
            if tl:
                res['eye_tilt_deg'] = _r(sum(tl) / len(tl), 2)
            SL, SR = _ext(ls), _ext(rs)
            res['eye_slit_w'] = _r((SL['w'] + SR['w']) / 2)
            res['eye_slit_h'] = _r((SL['h'] + SR['h']) / 2)

        lip = mats.get('lip') or []
        if lip:
            LP = _ext(lip)
            res['mouth_w'] = _r(LP['w'])
            res['mouth_h'] = _r(LP['h'])
            res['mouth_w_over_head'] = _r(LP['w'] / head_len)
            res['mouth_from_chin'] = _r((LP['cz'] - hb[0][2]) / head_len)

        brow = mats.get('brow') or []
        if brow:
            lb, rb = _side_pts(brow)
            if lb and rb:
                BL, BR = _ext(lb), _ext(rb)
                res['brow_len'] = _r((BL['w'] + BR['w']) / 2)
                res['brow_th'] = _r((BL['h'] + BR['h']) / 2)
                res['brow_th_over_head'] = _r(res['brow_th'] / head_len)
                res['brow_from_chin'] = _r(((BL['cz'] + BR['cz']) / 2 - hb[0][2]) / head_len)
                tb = [t for t in (_tilt(lb), _tilt(rb)) if t is not None]
                if tb:
                    res['brow_tilt_deg'] = _r(sum(tb) / len(tb), 2)

    # 头身接缝：头底相对颈柱顶的空隙。正值 = 露缝（头浮起来），负值 = 插进身体。
    # 这个指标是 7.5 头身改造时抓到的：脖子是 body.py 里一段硬编码的柱，
    # 头缩了下巴上移 33mm，柱却没跟上，实测缝 8.7mm。
    if body and hb:
        neck_band = [p for p in body if abs(p[0]) < 0.06 and abs(p[1]) < 0.08]
        if neck_band:
            res['head_body_gap'] = _r(hb[0][2] - max(p[2] for p in neck_band))
            res['body_top_z'] = _r(max(p[2] for p in neck_band))

    # ---------------- 躯干（参数表口径，见模块头 口径 2）----------------
    res['shoulder_width'] = _r(2 * cfg.SHOULDER_RX)
    res['waist_width'] = _r(2 * cfg.WAIST_RX)
    res['hip_width'] = _r(2 * cfg.HIP_RX)
    res['waist_over_hip'] = _r(cfg.WAIST_RX / cfg.HIP_RX)
    res['waist_over_shoulder'] = _r(cfg.WAIST_RX / cfg.SHOULDER_RX)
    res['shoulder_over_headw'] = (_r(2 * cfg.SHOULDER_RX / (hb[1][0] - hb[0][0]))
                                  if hb else None)
    res['crotch_z'] = _r(cfg.CROTCH_Z)

    # ---------------- 头发 ----------------
    if hair:
        # 区间：下巴下方 120mm 到头顶 —— 「后脑+披肩」那一段，排除发梢
        # 区间：[下巴上 30mm, 颅顶下 40mm]。旧值「下巴下 120mm」是给长发披肩
        # 用的；鲍伯头的发梢在下巴附近收口，把它算进来会把收边误判成「薄板」
        # （实测 0.116）。同时把桶数从 40 降到 12 —— 40 桶时每桶 6mm，小于
        # 刘海与后壳的高度间隙，会出现「只有刘海没有后壳」的空桶。
        hp = _hair_bands(hair, n=12,
                         z_lo=(hb[0][2] + 0.03) if hb else None,
                         z_hi=(skull_top - 0.04) if skull_top else None)
        res['hair_back_ratio'] = hp['min_ratio']
        res['hair_back_ratio_at_z'] = hp['min_ratio_at_z']
        res['hair_back_depth'] = hp.get('depth_there')
        res['hair_back_width'] = hp.get('width_there')
        res['hair_cap_gap'] = _cap_gap(head, hair)
        res['hair_top_z'] = _r(hair_top)
        res['hair_bottom_z'] = _r(min(p[2] for p in hair))
        res['hair_over_head_top'] = _r(hair_top - skull_top) if skull_top else None

        # ---- 发型轮廓：参考图（剪影）唯一能对齐的几项 ----
        hair_h = (hair_top - hb[0][2]) if hb else None
        widths = [r['xw'] for r in hp['rows'] if r]
        if widths:
            res['hair_width_max'] = _r(max(widths))
            res['hair_w_over_h'] = _r(max(widths) / hair_h) if hair_h else None
        if hair_h:
            res['hair_below_chin'] = _r((hb[0][2] - res['hair_bottom_z']) / hair_h)
        # 刘海下缘：正前方（y<0）且落在脸宽内的最靠下头发。
        # bangs_over_eye > 0 表示刘海压到眼睛中线以下（遮眼）。
        half = (res.get('face_width_cheek') or 0) * 0.5
        if hb and half:
            front = [p for p in hair if p[1] < 0.0 and abs(p[0]) < half]
            if front:
                res['bangs_bottom_z'] = _r(min(p[2] for p in front))
                if res.get('eye_cz'):
                    res['bangs_over_eye'] = _r((res['eye_cz'] - res['bangs_bottom_z']) / head_len)
        res['hair_rows'] = hp['rows']

    # ---------------- 服装 ----------------
    if outfit:
        sk = _skirt(outfit)
        res['skirt_taper'] = sk['taper']
        res['skirt_waist_half'] = sk.get('waist_half')
        res['skirt_mid_half'] = sk.get('mid_half')
        res['skirt_waist_z'] = sk.get('waist_z')
        res['outfit_rows'] = profile(outfit, n=40)

    # ---------------- 全身剪影（正视宽 + 侧视厚，一份数据两用）----------------
    res['silhouette'] = profile(body + head + hair + outfit, n=64)
    return res


def check(spec, measured):
    """拿 spec 判 measured，返回 [dict]。

    spec 每项：{'target', 'tol', 'unit', 'label', 'level', 'source'}
    level: 'must'（不达标算 FAIL）/ 'warn'（只记录，算 WARN）
    指标缺失记 MISSING —— 不静默放过。
    """
    rows = []
    for key, item in spec.items():
        if key.startswith('_'):
            continue
        target = item.get('target')
        tol = item.get('tol')
        level = item.get('level', 'must')
        got = measured.get(key)
        label = item.get('label', key)
        if got is None:
            verdict = 'MISSING' if level == 'must' else 'SKIP'
            rows.append({'key': key, 'label': label, 'got': None, 'target': target,
                         'tol': tol, 'diff': None, 'level': level, 'verdict': verdict,
                         'unit': item.get('unit', '')})
            continue
        # 支持 target±tol（双侧）与 min/max（下限/上限型）。
        # 「后脑厚宽比」这类指标没有上限，越饱满越好，双侧判据会把它误判成 FAIL。
        lo = item.get('min', (target - tol) if (target is not None and tol is not None) else None)
        hi = item.get('max', (target + tol) if (target is not None and tol is not None) else None)
        ok = True
        if lo is not None and got < lo:
            ok = False
        if hi is not None and got > hi:
            ok = False
        diff = (got - target) if target is not None else None
        if ok:
            verdict = 'PASS'
        else:
            verdict = 'FAIL' if level == 'must' else 'WARN'
        rows.append({'key': key, 'label': label, 'got': got, 'target': target,
                     'tol': tol, 'lo': lo, 'hi': hi, 'diff': _r(diff), 'level': level,
                     'verdict': verdict, 'unit': item.get('unit', '')})
    return rows
