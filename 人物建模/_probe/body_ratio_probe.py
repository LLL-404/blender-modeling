# -*- coding: utf-8 -*-
"""骨架比例工程师的网格真值探针：量 Body 网格的实测形宽与裆高（stdout 版）。

判据走 cfg 常量口径（lib/appearance.py:320-327 读 cfg.WAIST_RX/HIP_RX/
SHOULDER_RX，不实测 Body），cfg 与网格脱节时 measure 照样 PASS。本探针在
Blender 进程内按 m1/m5 同一构建路径现建 Body（同 profile、同 voxel、同
smooth），量**最终网格**的同口径数字并与 cfg 常量并排打印：
mesh/cfg ≈1.0 才算「判据与几何一致」。

  shoulder_half  肩带半宽：z∈[1.20,1.32] 内 max|x|（肩峰/三角肌带，避开肘部）
  waist_half     腰带半宽：z∈[0.99,1.03]
  hip_half       胯带半宽：z∈[0.80,0.90]
  crotch_z       网格裆高：|x|<0.012 顶点在 z∈(0.30,0.80) 的最低层（缝顶）

用法：blender -b --factory-startup --python-exit-code 1 --python _probe/body_ratio_probe.py
只打印（数据走 stdout），不写盘。
"""
import bpy
import sys

sys.path.insert(0, r"D:\G\github\实用工具\Blender建模\人物建模")
sys.path.insert(0, r"D:\G\github\实用工具\Blender建模\人物建模\lib")

BANDS = {
    'shoulder': (1.20, 1.32),
    'waist':    (0.99, 1.03),
    'hip':      (0.80, 0.90),
}
SLICE = 0.005          # 裆缝扫描层厚


def _pts(ob):
    mw = ob.matrix_world
    return [tuple(mw @ v.co) for v in ob.data.vertices]


def band_half_width(pts, zlo, zhi, split_arms=False):
    """z 带内 max|x|（半宽）。

    split_arms=True 时按 5mm 层逐层做「最大间隙切分」：A 形站姿的前臂在
    腰/胯带是独立壳（|x| 0.17~0.24），与躯干本体（|x|≤表值）之间有一段
    无顶点的空隙——层内 |x| 排序后找最大间隙，间隙 >20mm 且上段起点
    >0.15 就把上段判为手臂、只留下段（躯干/腿）的 max。肩带不能切：
    三角肌与肩帽在那里已经融成一体，切了会把肩宽量小。
    """
    zs_slices = {}
    for p in pts:
        if zlo <= p[2] <= zhi:
            zs_slices.setdefault(round(p[2] / 0.005), []).append(abs(p[0]))
    best = None
    for _, xs in zs_slices.items():
        xs.sort()
        if split_arms and len(xs) >= 4:
            gi, gsize = 0, 0.0
            for i in range(len(xs) - 1):
                if xs[i + 1] - xs[i] > gsize:
                    gi, gsize = i, xs[i + 1] - xs[i]
            if gsize > 0.020 and xs[gi + 1] > 0.15:
                xs = xs[:gi + 1]
        m = max(xs) if xs else None
        if m is not None and (best is None or m > best):
            best = m
    return best


def crotch_z(body_pts):
    """网格裆高：|x|<0.012 的顶点在 z∈(0.30,0.80) 的最低层（缝顶）。"""
    zlo, zhi = 0.30, 0.80
    n = int((zhi - zlo) / SLICE)
    for i in range(n):
        a = round(zlo + i * SLICE, 4)
        b = a + SLICE
        seg = [p for p in body_pts if a <= p[2] < b and abs(p[0]) < 0.012]
        if seg:
            return a
    return None


def main():
    import body as bodymod
    import cfg

    body_ob = bodymod.build()          # 与 m1_body/m5_rig 完全同一构建路径
    pts = _pts(body_ob)

    def half(name):
        zlo, zhi = BANDS[name]
        return band_half_width(pts, zlo, zhi, split_arms=(name in ('waist', 'hip')))

    sh, wa, hi_, cz = half('shoulder'), half('waist'), half('hip'), crotch_z(pts)
    stature = max(p[2] for p in pts) - min(p[2] for p in pts)

    print('[probe] shoulder_half=%.4f (band 1.20-1.32)  cfg.SHOULDER_RX=%.4f  mesh/cfg=%.3f'
          % (sh, cfg.SHOULDER_RX, sh / cfg.SHOULDER_RX))
    print('[probe] waist_half   =%.4f (band 0.99-1.03)  cfg.WAIST_RX   =%.4f  mesh/cfg=%.3f'
          % (wa, cfg.WAIST_RX, wa / cfg.WAIST_RX))
    print('[probe] hip_half     =%.4f (band 0.80-0.90)  cfg.HIP_RX     =%.4f  mesh/cfg=%.3f'
          % (hi_, cfg.HIP_RX, hi_ / cfg.HIP_RX))
    print('[probe] crotch_z     =%s  cfg.CROTCH_Z=%.4f  mesh/cfg=%s'
          % (('%.4f' % cz) if cz else 'None', cfg.CROTCH_Z,
             ('%.3f' % (cz / cfg.CROTCH_Z)) if cz else 'None'))
    print('[probe] stature=%.4f' % stature)
    print('[probe] head-caliber reminder: appearance.json 的 head_width/chin_z 同轮测')
    return 0


if __name__ == '__main__':
    sys.exit(main())
