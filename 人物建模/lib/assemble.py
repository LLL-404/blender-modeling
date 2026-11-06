# -*- coding: utf-8 -*-
"""整合装配层（2026-11-06，管线整合工程师）。

三路并行交付（马尾 / 旗袍 / 配饰飘袖）在 m3_look / m4_hair / m5_outfit / m5_rig
四个入口要按同一套口径组装——形制分发、配饰锚点落定、骨骼绑定都收在这里，
四个入口各一行调用，不再各抄一份漂移。

内容：
  1. outfit_style() / build_outfit(M)：服装形制分发。qipao（默认，lib/qipao.py）
     / shirt（旧衬衫+A字裙，lib/outfit.py，逐位原样可回退）。
     口径：环境变量 OUTFIT_STYLE > params/profile.json 的 outfit.style > "qipao"。
     环境变量保留最高优先级，OUTFIT_STYLE=shirt 的回退实测路径不受 profile 影响。
  2. hair_stage(M)：头部锚定配饰（蝶饰×2 + 墨镜），m4_hair 用。
  3. full_stage(M)：全套配饰 + 飘袖，m5_outfit / m5_rig 用。吊坠在这是【重锚】的：
     A3 的盘扣坐标是假设值，实坐标取 lib/qipao.py:_clasp_seat 的 cx0（该常量未
     导出，此处镜像登记，qipao 改座标必须同步 PENDANT_ANCHOR 的推导注释）。
  4. closed(pieces)：可挂实心描边壳的闭合件。飘袖是毛边开口网格 + alpha 0.45
     雪纺，套实心黑壳会把半透明袖包成实心黑边（且设定书 §四 只给金属件描边），
     所以描边统一跳过飘袖。
  5. bind_rigid(pieces, arm)：m5_rig 用。蝶饰/墨镜/吊坠 → head 骨（与 Hair 同骨，
     刚性跟随）；飘袖 → 同侧 upper_arm（袖身 2~3 段辅助骨骼是 brief §三.2 的
     B 阶段项，未建——walk/reach 下袖子刚性随大臂，属本轮已知取舍）。
     所有配饰已 _rebase 到自身锚点（lib/accessories.py:_rebase），物体原点即
     锚点，rigid_to 的骨变换绕世界骨枢轴转、rest 位形逐位不动。

锚点数值推导（变化处，其余沿用 lib/accessories.py 模块头 A1~A4）：
  A1 蝶饰  不重锚。实测（out/_v2_probe_anchor.py [bow]）：星座背面沿法向
           108.4mm vs 实马尾发面 107.0mm → 悬 1.4mm，与耳盖/收拢片相切贴服。
  A2 墨镜  重锚 pos=(0,-0.053,1.690)（A2 原值按 +10mm 占位壳校准；实马尾刘海帘
           顶缘 z≈1.654 占据原落位，首渲墨镜被发丝遮成碎块）。抬到发帽冠部
           前坡，背缘贴帽面；tilt 64° 不变。推导见 SUNGLASSES_POS 注释。
  A3 吊坠  盘扣座中心 (0, -0.0355, 1.368)、朝 -Y、厚 3.6mm → 座前表面 y=-0.0373。
           吊坠挂环顶贴座面：anchor=(0, -0.0378, 1.366)（座面外 0.5mm、z 取座中
           稍下）。领面前表面从 z1.358 的 -0.036 前倾到 z1.332 的 -0.056（斜率
           ≈0.77），直垂的吊坠平面在 z<1.35 段会没进领面——故 PENDANT_TILT_DEG
           让水滴绕挂环顶（物体原点）前倾贴领面，倾角首版 -30°（渲染复核定稿）。
  A4 飘袖  center_out 首版维持 0.008；袖根内缘 vs 旗袍 bust 侧的干涉值见
           out/_v2_probe_anchor.py [sleeve]，渲染复核后再定是否外移。
"""
import math
import os

from mathutils import Vector

# ---------------- 服装形制分发 ----------------
_DEFAULT_OUTFIT_STYLE = "qipao"


def outfit_style():
    """生效的服装形制名：'qipao' | 'shirt'。优先级 env > profile > 默认。"""
    env = os.environ.get("OUTFIT_STYLE")
    if env:
        return env
    import charparams
    return charparams.get("outfit.style", _DEFAULT_OUTFIT_STYLE)


def build_outfit(mats):
    """按形制建服装，返回 join 后的 "Outfit"（两条路径同签名同契约）。"""
    if outfit_style() == "shirt":
        import outfit as outfitmod
        return outfitmod.build(mats)
    import qipao as qipaomod
    return qipaomod.build(mats)


# ---------------- 配饰锚点（落定值；推导见文件头） ----------------
import accessories as acc   # noqa: E402  锚点常量与其同源，放 import 后便于对照

PENDANT_ANCHOR = Vector((0.0, -0.0378, 1.366))   # A3 重锚：盘扣座前表面
PENDANT_TILT_DEG = -30.0                          # 绕挂环顶前倾，贴领面前倾斜面
SLEEVE_CENTER_OUT = 0.008                         # A4：袖根外移（bust 侧干涉实测后调）
# A2 重锚（2026-11-06 探针 + m5 首渲）：A2 原值 (0,-0.050,1.660) 按「颅顶+10mm
# 光滑占位壳」校准；实马尾的刘海帘顶缘在 z≈1.654、前缘 y≈-83mm（z1.56-1.62），
# 墨镜背缘 (z1.632,y-63.6) 落在刘海帘**后方**，正面被发丝遮成黑蓝碎块
# （out/m5_face_front.png 首渲）。抬到发帽冠部前坡（z1.66 前缘 -69.9mm）上：
# 背缘落位 (z≈1.662, y≈-66.5)，贴帽面 3mm 内；取 pos=(0,-0.053,1.690)、tilt 64° 不变。
SUNGLASSES_POS = Vector((0.0, -0.053, 1.690))


def hair_stage(mats=None):
    """头部锚定配饰：蝶饰×2 + 墨镜。返回 [物体]。"""
    pieces = list(acc.butterfly_pair(mats))
    pieces.append(acc.sunglasses(mats, pos=SUNGLASSES_POS))
    _summarize("hair_stage", pieces)
    return pieces


def full_stage(mats=None):
    """全套：hair_stage + 吊坠（重锚+前倾）+ 飘袖×2。返回 [物体]。"""
    pieces = hair_stage(mats)
    pd = acc.pendant(mats, anchor=PENDANT_ANCHOR)
    if abs(PENDANT_TILT_DEG) > 1e-9:
        # 前倾贴领面：_rebase 已把物体原点放到挂环顶，绕 X 旋转即绕挂环顶摆动。
        pd.rotation_euler.x = math.radians(PENDANT_TILT_DEG)
    pieces.append(pd)
    sleeves = acc.sleeve_pair(mats, center_out=SLEEVE_CENTER_OUT)
    pieces.extend(sleeves.values())
    _summarize("full_stage", pieces)
    return pieces


def closed(pieces):
    """可挂实心描边壳的闭合件（跳过飘袖，理由见文件头）。"""
    return [ob for ob in pieces if not ob.name.startswith("AccSleeve")]


def bind_rigid(pieces, arm):
    """m5_rig：配饰挂骨架。蝶饰/墨镜/吊坠 → head；飘袖 → 同侧 upper_arm。"""
    import rig
    for ob in pieces:
        if ob.name.startswith("AccSleeve"):
            side = ".L" if ob.name.endswith("_L") else ".R"
            rig.rigid_to(ob, arm, "upper_arm" + side)
        else:
            rig.rigid_to(ob, arm, "head")
    return pieces


def _summarize(tag, pieces):
    total = sum(len(ob.data.polygons) for ob in pieces)
    print(f"[assemble] {tag}: pieces={len(pieces)} faces={total} "
          f"(配饰+飘袖预算 ≤3000)")
