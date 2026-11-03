# 变更记录

## 2026-11-03 / v0.4.0 — spec 驱动外观验收 + 发型两处遗留修复 + S8/S9 重构收口

本轮不是新造型轮：把 v0.3.0 的成果变成**可复测的验收通道**，修掉两处已登记的 bob 发型硬伤，
并把欠账的 S8/S9 去重（D1–D6 / D11 / D12 / D15）做完、**首次实跑跨仓管线**。

### 新增：外观 spec 体检（形状 → 数字 → 判定）

| 件 | 作用 |
|---|---|
| `spec/reference.json` | 14 指标基准表（12 must + 2 warn），每项带 `target`/`tol`（或 `min`/`max`）、`level`、`source`（数字从哪来） |
| `lib/appearance.py` | 量测层：顶点投影 + z 分桶算头身比/脸宽/五官/发帽/后脑厚宽比/裙摆锥度/头身接缝，**不渲染**；`measure(objs)` 返回纯 Python 类型，`check(spec, measured)` 做 must/warn 判定 |
| `_probe/appearance_probe.py` | 只读探针：打开 `美女.blend`、调 `measure()`、写 `out/appearance.json`；不渲染/不保存/不改物体 |
| `scripts/measure.py` | 入口：跑探针 → 读基准表 → 打「实测/目标/差值/容差/判定」表 → 写 `out/appearance_report.json`；退出码 0 全过 / 1 有 must FAIL / 2 测量失败 |
| `scripts/sweep.py` | 参数响应表：扫一个旋钮、每点重建+量测，输出「参数→形状」矩阵；矩阵**先落盘再恢复配置**（恢复重建几十秒，中断不该丢扫描结果） |

实测（`美女.blend`，7.5 头身 bob 版）：**13 PASS / 0 FAIL / 1 WARN / 0 MISSING**。
唯一 WARN = `hair_over_head_top` 14mm（目标 45mm；bob 贴头皮、没有呆毛，`spec` 里已登记为已知取舍，不拦）。
`build.py` 增加 `measure` 子命令（`python scripts/build.py measure`），与 `check` 平级。

顺带修掉两个只在「AI/管道读输出」路径暴露的缺陷：
- `measure.py` 表格含 `−`(U+2212)，Windows 下 stdout 被管道重定向时默认 cp936，`UnicodeEncodeError`
  直接崩在打印处。新增 `bpyrun.utf8_stdio()`（非 tty 时把 stdout/stderr 切 UTF-8），build / check /
  measure / sweep 四处接入。
- 「容差」列宽 10 装不下 `-12.0 mm~2.0 mm` 这类区间，与「差值」列粘连；加宽到 16。

**head_to_body_ratio 响应表**（4 点实扫，数据 `out/sweep_appearance_head_to_body_ratio_0{0..3}.json`）：

| 指标 | 6.503 | 7.001 | 7.498 | 7.993 |
|---|---|---|---|---|
| 头长 | 249.1mm | 231.4mm | 216.1mm | 202.7mm |
| 可见颈长 | 45.9mm | 63.6mm | 78.9mm | 92.3mm |
| 肩宽/头宽 | 1.086 | 1.162 | 1.237 | 1.311 |
| 头身接缝 | −9.8mm | −9.5mm | −9.4mm | −9.4mm |

接缝在四点上都稳定在 −9.4~−9.8mm，说明 `lib/body.py:neck()` 跟住头底的修复对旋钮是稳健的。

### 修复：bob 发型两处视觉遗留（颅顶「猫耳」+ 太阳穴折面）

两处同根因，`_bob_shell()` 的顶部收口算错了两件事：
1. 收口参数 `_TUCK_IN=-0.003` 的推算**漏了外壳自己那层 Solidify** —— 它沿法线向外长 4.5mm，
   收口段「壳外表面」= 头骨 +3+4.5 = +7.5mm，而发帽只有 +7mm，永远多 0.5mm 收不进去；
2. 收口段截面形状与发帽不一致（发帽是超椭圆 p2.0~2.1 + 前后不同半径 + cy −2mm；外壳是单椭圆
   cy +18mm），同一 (x,z) 处前后最多差 9.6mm。

后果：顶环 144 个顶点里 **74 个戳出发帽（最多 +5.17mm）**，戳出的顶边被描边壳勾黑——侧/3-4 视角
头顶一道横线、两端针状尖刺（即「两个猫耳」），同一条边在太阳穴高度忽进忽出（折面）。

改法（只动 `lib/hair.py`）：删 `_TUCK_IN`、新增 `_TUCK_DEPTH=0.014`（收口末端壳外表面 = 发帽 −9.5mm，
扣掉 4.5mm 外壳 + 1.4mm 描边仍余 ≥3.6mm）；收口段环改成**与发帽完全同形**的超椭圆，形状与深度走同一条
smoothstep（t 0.72 → 0.907）；顺带删掉不再被引用的 `_head_rx()` / `_head_ry()`。

实测：顶环戳出发帽 **74/144（max +5.17mm）→ 0/144（全部落在发帽内 4.27~9.64mm）**；渲染上侧视横线 /
猫耳 / 太阳穴台阶全部消失。**指标不回退**：measure 13/0/1 与基线一致（hair_cap_gap 20.2mm、
hair_back_ratio 0.7229、hair_over_head_top 14.0mm 均不变）；六探针 71/1/125 逐项一致；描边 p50=3px 不变。
对比图 `out/fix_before_after_{m4,m5}_face.png`、特写 `out/fix_zoom_{crown,temple}.png`（out/ 不入库）。

残留（风格项，未动）：颅顶**正中**球冠顶点还有一个约 4mm 尖点（`_cap()` 圆顶 profile 在顶点处
r∝(z_top−z)^(2/3)）。磨圆会让颅顶 1.62~1.63 段最宽 +3~4mm = 动剪影，且 `hair_over_head_top` 数字会变，
留给作者定夺。

### 重构：S8/S9 去重收口（D1–D6 / D11 / D12 / D15）

| 项 | 落点 | 验证 |
|---|---|---|
| D1–D6 | 新 `blender-rig/preview_common.py`（清场 / 引擎回退 / 世界包围盒 / 按包围盒架机 / 渲染落盘 / 输出设置），三脚本转调，签名不变 | **实跑通过**（见下） |
| D11 | `stardust/build_portraits.py` 三点灯表提为 `_LIGHT_SPECS` 常量，`build_characters*.py` 共用 | 静态等价（灯位/能量逐值同） |
| D12 | 新 `scripts/bpyrun.py`：Blender 定位单源，build/check 转调；`Blender体检/check.sh` 注释互指 | 实跑 |
| D15 | `lib/shots.py:VIEWS` 机位单源（m2~m5 五个入口共读）；`pixel_probe.py` 按 `m<数字>` 前缀查 `ORTHO_BY_STAGE` | 实跑；px↔世界换算不再偏 6.7% |

**blender-rig 首次在本仓实跑**（此前只验证过路径存在）：`rig_buildings.py` → `core_jade.glb`
(1,115,516 B) / `tower_ballista.glb` (868,328 B)；`preview_anim.py` → 11 张 **560×560** PNG；
`stress_test.py` → 2 张压测图；三者 exit 0。这轮实跑抓到一个**只靠静态审查发现不了的回归**：
`PREVIEW_RES=(560,560)` 定义后无人引用，`reset_scene()` 不传 `res` 就不执行输出设置 → 分辨率会退回
出厂 1920×1080（已修：两处 `pc.reset_scene(res=pc.PREVIEW_RES)`）。

### 新增：BlenderAPI 封装层

`BlenderAPI/`（此前未跟踪、无文档）：`bapi/` 7 子模块 1,621 行（env/obj/mesh/mod/mat/shot/sculpt，
84 个公开函数，全包仅 4 处 `bpy.ops`）+ `catalog/`（在运行中的 Blender 里扫描生成的 5.2.2 API 目录：
1129 操作符 / 562 节点 / 83 修改器）+ `selftest.py` 36 项。

- 首次实跑 selftest：**PASS=30 FAIL=6**。归因后修 1 个真 bug（`shot.setup()` 把 `env.resolution()`
  返回的 `RenderSettings` 当 `Scene` 用，取 `view_settings` 必 AttributeError）+ 5 条 selftest 判据
  自身写错（面数算术、DECIMATE 三角面口径、Modifier 非 ID、sculpt 取样点、`node.type` 实为
  `SHADERTORGB`）；修正版**没放宽判定强度**（decimate 判据反而收紧），依据逐条写进 `BlenderAPI/README.md`。
- 复跑：**PASS=36 FAIL=0 SKIP=0，exit 0，3.23s**。
- 口径校正：全包 `bpy.ops` 实为 **4 处**（旧 docstring 写「三处」，漏了 `save_blend`）。
- **尚未接入任何现有管线**（grep `import bapi` / `from bapi` 只命中 `BlenderAPI/` 自身）。

### 文档与仓库

- 根 `README.md`：能力面→落点补「量化验收 / 通用封装」两行；组件表加 `BlenderAPI`；目录结构、环境要求、
  快速上手（第 4/5 条）、blender-rig 实跑状态、已知缺口全部对齐。
- `人物建模/README.md`：新增「外观体检（spec 驱动）」整节（链路、判定口径、14 行实测表、参数响应表）；
  目录结构补 `spec/`、`appearance.py`、`measure.py`、`sweep.py`、`_probe/appearance_probe.py`、
  `_bak_before_*`；lib 17→18、profile 37→39 键、hair 10→11 键。
- `params/README.md`：`head_to_body_ratio` 现值 6.505→7.5（并注明头部坐标映射已改为随旋钮现算）；
  hair 补 `hair_ring_color` 行（11 键）。
- `docs/工程梳理与维护指南.md`：速查表补 5 行；六探针数字按最新报告校正（75/1/121 → **71/1/125**）；
  S8/S9 完成状态、R3/R4 结论、BlenderAPI、blender-rig 实跑全部入档。
- `.agent/tools/blender/index.md`：补 measure / sweep / BlenderAPI 三个入口。
- `人物建模/.gitignore`：加 `_bak_before_*/`（改造前快照，磁盘保留、不入库）与 `params/_tmp/`（sweep 临时 profile）。
- **新增 `LICENSE`（MIT，Copyright © 2026 LLL-404）**：根 README 删去「仓库无 LICENSE」缺口并新增
  「许可」一节，写明两条边界——Blender 本体不随本仓分发（外部调用，GPL 独立）；`BlenderAPI/catalog/`
  是在本机 5.2.2 上扫描的 API 元数据（名字/签名/枚举值），不含 Blender 源码或文档正文。

### 验证汇总（2026-11-03 定版轮）

| 检查 | 结果 |
|---|---|
| `python scripts/build.py all` | 六步 exit 0，`[assert] summary: 0 failed` |
| `python scripts/build.py measure` | **PASS 13 / FAIL 0 / WARN 1 / MISSING 0**，exit 0 |
| `python scripts/build.py check` | **PASS=71 FAIL=1 SKIP=125 CRASH=0 MISSING=0**，exit 1（唯一 FAIL=R4 屈指，作者已拍板保留现状） |
| `BlenderAPI/selftest.py` | **PASS=36 FAIL=0 SKIP=0**，exit 0 |
| blender-rig 三脚本 | 全 exit 0（preview 11 张 560×560） |

## 2026-11-03 / v0.3.1 — 文档与代码对齐（纯文档，无几何改动）

README.md / DESIGN.md 还停在「6.5 头身 + 长发 + `hair_color` 未接线」时代，读者按文档走会踩空：

- 仓根 `Blender建模/README.md`：定位重写为「**让 AI 在 Blender 里建模**」（对象：人物/道具/环境等任意 .blend；能力面：网格/骨骼/动作/拓扑/UV/法线），并新增「能力面 → 落点」表，每项主张对应仓内实际模块。

- `README.md`：角色设定基准行注明 6.5 → 7.5 与 `hair.style=bob` 默认；`m4_hair.py` 条目补发型分叉说明；`params` 表 hair 组改「10 键全接线」（`hair_color`/`hair_shadow_color` 已由 `hair_material()` 读取）；「一键复检」实测行更新为 `PASS=71 FAIL=1 SKIP=125`（D 组 5 条按长发型写的判据在 `bob` 下 SKIP，非放宽）；「已知限制」第 1 条法线翻转标记已解决（2026-11-03 复测 `normal_flips=0`），第 2 条屈指补复测数字。
- `DESIGN.md`：开头基线说明从「两个时点」扩为「三个时点」，声明 §1.2 的 6.5 头身等是历史记录、当前值以 CHANGELOG 与 `scripts/measure.py` 为准。

验证：`scripts/check.py` 实跑一遍取数（19s），`PASS=71 FAIL=1 SKIP=125 CRASH=0 MISSING=0`，唯一 FAIL 为既有 R4 屈指 `min=0.582<0.6`。

## 2026-11-03 / v0.3.0 — 按参考图重建外观（鲍伯头 / 收窄脸 / 分缕刘海）

上游依据是一张 1600×1600 的参考图（粉发鲍伯头、细长上挑眼、V 形下巴）。
做法不是「照着感觉调」，而是**先把图量成数**再对：ROI 分割 + 扫描线分类
（皮肤 / 粉发 / 黑服 / 背景），以「发顶→下巴」为 1 单位换算成比值，然后拿
模型同口径对比。量出来的差距决定了改什么。

### 量到的差距（比值，单位 = 发顶→下巴）

| 项 | 参考图 | 改前模型 | 改后模型 |
|---|---|---|---|
| 发宽 / 头高 | 0.94 | 1.14 | 0.99 |
| **发宽 / 可见脸宽** | **2.17** | **1.30** | **1.82** |
| 发梢在下巴下的长度 | 0.08 | 0.10 | 0.10 |
| 眼裂 宽×高 | 0.132 × 0.060（宽高比 2.2） | 0.172 × 0.111（1.55） | 0.172 × 0.111 |
| 口宽 | 0.082 | — | — |

眼裂这一行是**关键发现**：模型的眼睛并不小 —— 换算成毫米是 37.2×24mm，
比参考图的 30.3×13.8mm 还大。看起来小是因为**脸宽了 76%**（可见脸宽
175mm vs 99mm）。所以这一轮的重点不是放大眼睛，而是收窄脸。

### 几何改动

| # | 改动 | 位置 |
|---|---|---|
| 1 | **新增 `hair.style` 分叉**：`bob` 走 `_cap + _bob_shell + _fringe`，`long` 保留原路径。默认值仍是 `long`，profile 里显式写 `bob` | `lib/hair.py:build()` |
| 2 | **鲍伯外壳**：19 行 (t, rx, ry, cy) 表 + 线性插值加密到 44 行，截面是**开口弧**（右鬓内缘→后脑→左鬓内缘），手工连四边形带后 Solidify 4.5mm | `lib/hair.py:_bob_shell()` `_bob_dense()` |
| 3 | **开口宽度随高度变化**：眉线附近 0.70×头骨半宽，往下收到 0.56，边界贴合颊线 | 同上 |
| 4 | **整片锯齿刘海**：45 列 × 8 行曲面，下缘余弦锯齿（周期 35.5mm、幅度 4.2mm），叠加两个周期（34.5/19.3mm）的纵向缕槽 | `lib/hair.py:_fringe()` |
| 5 | **下颌收窄**：`HEAD_RAW` 的 1.384~1.444 段 rx 各减 12%~21%，1.472 以上不动（头宽取 1.508 处最宽值，既有判据不受影响） | `lib/head.py:HEAD_RAW` |
| 6 | **眼型收窄**：EYE_W 0.0208→0.0186、EYE_HU 0.0188→0.0150、EYE_HD 0.0110→0.0090；上挑角 0.16→0.24 | `lib/head.py` |
| 7 | **配色换参考图取色**：发 `#FF90A5` / 暗 `#37101B`，肤 `#FFF4F7` / 暗 `#A8808F`，虹膜紫粉，唇 `#ED8594` | `lib/look.py` |
| 8 | **`hair_material()` 真正接线**：原来参数写死、`hair_color` 根本没被读；现在读 profile 并按 `shadow ÷ base` 换算 MULTIPLY ramp 暗端 | `lib/look.py:hair_material()` |

### 踩过的坑（都留在代码注释里）

| 现象 | 根因 | 结论 |
|---|---|---|
| 鲍伯壳把脸整个包住，渲成头盔 | `meshkit.loft` 的 `j2=(j+1)%seg` **总是闭合环**，开口弧首尾被连成一张挡在脸前的平板 | 开口几何必须手工连四边形带，不能用 `loft` |
| 颅顶渲成一颗「馒头」 | 头骨最上一刀极陡（1.6034 rx=64.5mm → 1.6200 rx=25.8mm）。`_cap` 用 10mm 步长重采样把头骨跳过去了，剩一条 16.6mm 高的圆台，圆台上再接球冠 | 重采样步长 0.010→0.004；dome 收缩曲线 `sqrt(1−t²)`（t=0 斜率 0）改成 `(1−t)^1.5`（t=0 斜率 −1.5，正好等于圆台斜率），接缝才连续 |
| 颅顶前方一道弧形明暗交界 | 头骨自身在 1.600→1.618 有折角，发帽照着走就带着折角 | 头骨是共用几何、动它会连锁改五官位置，所以在**发帽**上做 3 轮 factor 0.35 的拉普拉斯平滑；同时外扩 6→7mm 对冲收缩量 |
| 耳上一块 V 形折片 | 分色渲染定位：**发帽**（不是外壳）。`_cap` 里「把额头压回头内」的操作没有 |x| 限制，耳朵上方也被压平，台阶露在刘海盖不到的地方 | 维持无条件压平 —— 加横向渐变反而在太阳穴造出一块更显眼的朝前斜面（试过） |
| 侧面/背面一圈水平台阶线 | 外壳在颅顶收进发帽（比发帽窄 11mm）后突然结束 | 径向差压到 4mm（`_TUCK_IN = −0.003`），落在描边壳厚度内才被吃掉 |
| 脸颊侧出现锯齿和透光小洞 | 把开口端点强行贴到脸表面（`_head_front_y`）比真实网格浅，端点穿进脸产生自交 | 回退。开口端点悬在脸前虽然留一条断口边，但不破面 |
| 刘海变一排等距「肋骨」 | 单一 30mm 周期、3.4mm 幅度的缕槽 | 幅度降到 1.6mm、叠加两个周期打散规律性、顶端乘 `tt^1.3` 不起伏 |

### 判据口径的更正（不是放宽，是原来就不适用）

- `_hair_bands` 的测量区间从「下巴下 120mm」改到「下巴上 30mm → 颅顶下 40mm」，
  桶数 40→12。旧区间是给长发披肩用的，鲍伯头发梢在下巴附近就收口，把收边
  算进来会把正常收口误判成「薄板」（实测 0.1163 → 修正后 0.6619）
- `_stageD/d_probe.py` 的 D1/D2 五条判据（刘海 3 组分组、后发束半宽/半厚、
  刘海额盖率）全部照长发型写的。`hair.style=bob` 时这 5 条标 SKIP 并指向
  真正管用的口径（`bangs_bottom_z` / `bangs_over_eye` / `hair_back_ratio`），
  **不假装通过**
- `skin_mask` 的皮肤色距阈值 38 把头发亮面 `(250,193,206)` 判成皮肤
  （到皮肤档 `(247,224,211)` 距离仅 31），导致额盖率报 4.4%。加 `R−G ≤ 45`
  判据（发色 53~58、皮肤 23~33）后恢复正常

### 验证

- 外观体检 **13 PASS / 0 FAIL / 1 WARN**（WARN = 发顶高出头骨 14mm，鲍伯头贴
  头皮、本来就没有长发的 45mm 蓬松量，属已知取舍）
- 六探针 **71 PASS / 1 FAIL / 125 SKIP**。唯一 FAIL 是 B 探针 R4 屈指最小边
  0.582 < 0.6（既有问题，本轮未动 `lib/hand.py`、`lib/rig.py`）
- 重导 `build.py all` 六步全过，断言 0 failed

### 已知遗留

1. 颅顶收口处有一个约 4mm 的小尖（描边壳在球冠顶点汇聚，几何上是一个点）
2. 3/4 视角太阳穴附近有一小块折面（发帽超椭圆截面与外壳椭圆截面形状不同，
   交界处裙边宽度不均）
3. 发丝**没有分层**：参考图是多层发片叠出来的层次，现在是一整块外壳
4. 服装未动（本轮范围只有发型+配色+五官）

## 2026-11-03 / v0.2.1 — 外观硬伤三修（刘海 / 鼻阴影 / 头顶）

三处都是「材质与掩码贴错位置」类问题，不动比例、不动骨架。前后对比见
`out/_before_after_face.png`（左 BEFORE / 右 AFTER）。

### 修了什么

| # | 现象 | 根因 | 改法 |
|---|---|---|---|
| 1 | **刘海整片发白，像贴了张纸条** | `hair_material` 的天使环 ADD 只按世界 z 分带，带位置 `0.803~0.915` = z 1.520~1.600 是**A 阶段把头部下移 12.7672mm 之前**定的；头下移后整条带落到刘海（z 1.512~1.588）上，近黑发色 + 0.64 的 ADD 直接到 0.69 线性（sRGB≈215） | 环带按 6.5 头身重算并降到微光 `(0.06,0.055,0.075)`；另加**位置遮罩**（y<−0.02 且 z<1.584 不叠色） |
| 2 | **鼻梁上一个灰色矩形** | `NOSE_BAND` 用 `_zone_mask` 硬盒（GREATER/LESS_THAN），边界零衰减 + bias −0.60，在浅色平滑脸上就是一块贴片 | 新增 `_nose_mask()` 椭圆径向软衰减（feather 0.6），bias 降到 −0.32 |
| 3 | 3/4 视角头顶是**一块平板** | `_cap()` 直接放样 `head_rows()` 到最上一环，`loft` 把它封成平顶 | 顶部补 10mm 半球圆顶（`sqrt(1−t²)` 收缩），只用于收平顶的边 |

### 连带修掉的一条皮肤缝

`_cap()` 原先把 `z<1.582 且 y<−0.004` 的前脸顶点折回脑后，于是刘海与帽檐之间
**必然**露出一条皮肤（渲出来是 #C8B4C2，正好等于皮肤 shadow 档）。把折返线放到
眉线 `1.534` 后，帽体自己盖住额头，那条缝从几何上不存在；刘海 3 组之间的
1~2mm 真空缝也因此从「露出一排皮肤」变成「发缕之间的暗沟」，D1 判据仍成立。

### 顺带

- `head.brow()` 眉厚 4.9mm → 3.5mm，外端再收 45%，去掉楔形厚条感。
- 刘海起点按**实测额面轮廓**重摆（`head_rows()`：z 1.586 ryf=0.0510、z 1.6009 ryf=0.0425），
  落在帽面前 3mm。此前写 −0.052 会埋进头骨、从帽檐下钻出形成「帽舌」；
  写 −0.077 则悬在脸前 26mm，斜侧能看见后面的额头皮肤。两条都实测踩过。

### 验证

- 六探针：**75 PASS / 1 FAIL / 121 SKIP**（唯一 FAIL 仍是 B 探针 R4 屈指最小边 0.529<0.6，
  属骨架权重范围，本轮未动 `lib/hand.py`、`lib/rig.py`）
- 资产重导：E1 UV 12.6s / E3 贴图 AO 32.6s / E4 glb 5.2s / E5 16 机位 12.3s 全过，
  16/16 机位暗像素 0，无破面

## 2026-11-02 / v0.2.0 — M6 资产化（UV / 贴图 / AO / glb）

在 M1~M5_rig 不动的前提下，新增**导出资产管线**：`m6_asset.py`（E1+E2）→
`m6_bake.py`（E3）→ `m6_export.py`（E4），统一入口 `python scripts/build.py asset`。
原三渲二渲染链路（`m1~m5_rig`、`out/m*.png`、`美女.blend`）逐位不变。

### 新增

- **`lib/uvkit.py`**：智能展开 + 打包；UV 岛数（并查集）、拉伸分位（sqrt(UV面积/3D面积)）、
  退化三角、UV 顶点比；numpy 光栅化 UV 布局图（`uv.export_layout` 依赖 GPU，headless 会报
  `gpu.init` 错误，故不用）。
- **`lib/retopo.py`**：面型统计、三角按材质归因、`tris_convert_to_quads`。
- **`lib/bake.py`**：色板贴图、AO 烘焙、法线一致性。`material_albedo()` 取
  toon 的 **base × ramp light**（不是只取 ramp light）；`_dilate()` 做 12px 边缘扩张；
  保存前手动做线性→sRGB（实测 `image.save()` 对 float 缓冲是线性直通）。
- **`lib/asset.py`**：剥离非 Armature 修改器、整网格换单一 PBR 材质、glTF 导出、回读统计。
- **入口**：`m6_asset.py` / `m6_bake.py` / `m6_export.py`；`scripts/build.py` 新增 `asset` 步骤
  （多脚本步骤，不并入 `all`）。

### 实测（2026-11-02，`美女.blend` → `美女_asset.blend` → `out/美女.glb`）

| 段 | 实测 |
|---|---|
| **E1 UV** | Body/Hands/Head/Hair/Outfit 五网格全部展开；岛数 **156 / 93 / 46 / 164 / 174**；UV 顶点比 **0.270 / 0.327 / 0.302 / 0.333 / 0.342**；拉伸 spread **1.18 / 1.22 / 1.21 / 1.22 / 1.21**；退化三角 **0** |
| **E2 面型** | Body/Hands **100% 四边**；Head **89.18%**（520 tri，均 skin/sclera/white_emit/iris/pupil）、Hair **94.54%**（628 tri，均 hair）、Outfit **96.66%**（320 tri，均 cloth_white）；`tris_convert_to_quads` 合并 **0** —— 残余三角是五官扇形贴片与发片尖端，不是脏拓扑 |
| **E3 贴图** | 色板 5 张 1024²（Body 肤色 sRGB **(247,224,208)**，占 82.1%，背景 17.9%）；AO 5 张 512²/8spp（Body 133KB、Hands 220KB、Head 98KB、Hair 105KB、Outfit 153KB）；rest 法线修正 **Head 377 / Hair 9828 / Outfit 1280**，Body/Hands 0 |
| **E4 导出** | `out/美女.glb` **8,633,028 B**；回读 **5 网格**（Body/Hands/Head/Hair/Outfit）、**45 骨**、每网格 1 层 `UVMap` + 1 个 `pbr_*` 材质、图像 5 张；顶点权重和 **bad=0**（78527/7232/5642/15106/12973）；glb 内 mesh 名 `torso/hair_cap/palm_-1/head/shirt` |
| **E5 16 机位** | 每 22.5° 一台正交相机，隐藏地板 + `film_transparent`，用 alpha 分割前景。前后前景覆盖率差 **0.0137~0.0221**（≤0.03，差全部来自 3.5px 描边壳外扩）；回读后 **16/16 机位**暗像素占比 **0.0000**（<0.02）、纯黑像素 **0.0000**（<0.005）；`out/m6_16_after.png` 逐格人工复核无破面/缺发/缺衣/悬空 |

### 已知限制（M6）

- **glb 不含描边**：三渲二的黑色轮廓是 Solidify 反法线壳，导出时已剥离；引擎侧需后处理描边
  （或自定义 shader），不能指望 glb 自带。
- **AO 未嵌入 glb**：`out/tex_*_ao.png` 单独落盘，供引擎手动接 occlusion；glb 只带 albedo。
- **PBR 观感比三渲二浅**：同一 albedo 在三点光 PBR 下头发偏灰棕（三渲二为深棕近黑），属光照/材质
  差异，不是贴图错误；需要接近原观感时在引擎侧压环境光或降低 key。
- **回读多一个 Icosphere**：glTF 导入器生成的骨骼辅助网格（42v/80f），不在 glb 内，回读统计已归 `extras`。

## 2026-11-01 / v0.1.0

首版入库。项目此前在工作区根 `D:\G\github\人物建模` 内迭代，本次工程化并迁入 `Tools/人物建模`。

### 新增

- **程序化管线 m1~m5_rig**：`cfg.py` 参数表 + `lib/` 12 个模块（`body` / `hand` / `head` / `look` /
  `hair` / `outfit` / `rig` / `mats` / `meshkit` / `sheet` / `shots` / `optio`），六个入口：
  `m1_body.py`（素体）、`m2_head.py`（头/五官）、`m3_look.py`（着色）、`m4_hair.py`（头发）、
  `m5_outfit.py`（服装）、`m5_rig.py`（45 骨骨架 + 4 姿势）。
- **`DESIGN.md`**：角色设定基准（6.5 头身比例表、五官/发型/服装意图、配色规范）+ 技术方案
  （模块职责、参数化硬约束、Blender 5.2 API 坑）+ A/B/C/D 四阶段量化验收表 + 验收方法论 + 偏离记录。
- **`opt/` 参数搜索器**：`halton.py`（低差异采样）、`space_geom.py` / `space_pixel.py`（参数空间）、
  `eval_geom.py` / `eval_pixel.py`（目标函数：硬约束惩罚 + 加权和）、`search.py` / `search_pixel.py`
  （Halton 采样 + top-k 邻域坐标下降）、`best.json`（最优参数，可回滚）、`REPORT.md`（几何段报告）。
- **`scripts/` 统一入口与自检**：`build.py`（`body|head|look|hair|outfit|rig|all|check|archive`，
  纯标准库，`BLENDER_EXE` 可覆盖，Blender 缺失 exit 2）；`check.py`（跑 6 个探针，汇总
  `opt/logs/check_report.md`，FAIL 计数只取探针自己的 PASS/FAIL 标记，崩溃单列 CRASH）。
- **工程化文件**：`README.md`（门面）、`requirements.txt`（numpy + Pillow）、项目级 `.gitignore`、
  本 `CHANGELOG.md`。

### 变更

- **A 阶段（修硬伤）**：手重建为每手 1 掌 + 4 指 × 3 段 + 拇指（13 骨，独立物体不 join 进 Body）；
  脚加 3 组脚趾、脚底 `z_min` 归零；鼻尖前伸 9.70mm、嘴宽收窄到脸宽 11.22%、上唇薄于下唇、耳高 45.82mm；
  头表绕 1.5857 缩放 ×1.0631（等价绕 1.3836 放大 + 下移 12.77mm），头身比 **6.95 → 6.505**；
  衬衫 `grow` 分 z 段加宽（三带 ≥ +10mm）、裙腰让出净空（四段 ≥ +2mm）、袖口收到 47mm 并闭合、
  呆毛半宽 0.008→0.0035。
- **B 阶段（骨架）**：骨架 **21 → 45 骨**（每手 `palm + 4 指 × 3 段` 替换 `hand.L/R`）；
  新增 `weight_nearest_banded`（z<1.05 只允许 hips/spine/chest 主导，裙摆臂骨主导 55.1%→0.00%）；
  候选骨加 x 符号约束（左右串权 1.23%→0.000%，过渡带 25~55mm smoothstep）；
  手指关节改 2 骨混合（屈指 45° 硬折 36.4×→ p95 1.21 / max 1.79）；Hands 挂上骨架并复用自带 13 组权重；
  B4 判据从「跨机位像素差」改为「关键骨世界位移 ≥100mm」（旧判据实测的是机位差）。
- **C 阶段（三渲二质感）**：C1 反法线 Solidify 描边（黑 Emission + backface culling，按视图换算成
  恒定 **3.5px** 线宽，全身/上身实测暗带 p50=3px）；C2 把 `Hands` 接进 `look.set_all()` 的 skin toon
  （手 vs 同侧前臂亮度差 6.8 / 2.0，≤8）+ 面部 ramp 偏移与鼻底阴影带；C3 色阶重标定
  （key 70W→49W、skin ramp pos 提到 0.62/0.68，皮肤 p50 **229.7 → 195.0**、p95−p50 **0.3 → 32.0**、
  ≥228 占比 **82.9% → 4.8%**）；C4 头发高光带上边界 0.845→0.90、rim 80W 并移到侧后方；
  D0 修 `head.py` 耳 rim/concha 局部坐标 bug（耳轮外推 5.05mm、耳甲内凹 2.29mm，头宽 0.2172 保住）。
- **D 阶段（发型与服装细节）**：D1 刘海分 3 组（2/3/2，组间缝 1.5mm，覆盖额头 85.2%）；
  D2 后发束减薄（半宽 19.0mm、厚 9.0mm、沟壑 5.6mm）；D3 衬衫翻领（V 深 18.5mm、后领高 +18.5mm、前中开口）；
  D4 袖口卷边造型（可见凸出 3.3mm、内厚外薄、边界边 0）；D5 裙褶非对称（`SKIRT_SEG 176`、
  二次谐波 0.25，峰谷差 25.9mm、正面中线为峰）。

### 已知问题

- **交叉姿势 60°/30° 的法线翻转 17 条**（几何穿模），与搜索参数无关（`opt/REPORT.md` §6 第 5 条）。
- **屈指最小边长比 0.582，阈 0.6**：搜索从 0.5289 改善到 0.5817，但最差边在掌根/近节交界
  （`palm.L ↔ index_proximal.L`，rest 1.53mm），属 2mm 体素短边的拓扑硬边界，需改 `assign_groups` 算法才能过阈。
- **轮廓光在 3px 描边下判定不可达**：`c_probe` 实测 rim 亮带 p50=0px（目标 2~6px），
  `trials_pixel` baseline 的 `rim_hair_n=1`；描边与轮廓光在深色区互相抵消，需二选一，见 `opt/REPORT.md`。
- 补充（实测）：描边像素宽只在全身/上身达标（p50=3px），脸部特写 `m3_face_front` p50=7px、
  `m4_face_front` p50=0px，未落在 2~4px 目标内。
- 补充（流程）：像素段搜索只跑了冒烟（`trials_pixel.jsonl` 仅 1 条 baseline），全量未完成，
  `best.json` 尚无 `pixel` 段。

### 迁移

- 自 `D:\G\github\人物建模` **整体 mv** 到 `Tools/人物建模`（192 个文件 / 21 个目录 / 45MB，迁前后一致），
  **代码一行未改**，`import cfg` / `from lib import ...` 路径不变；
  `__pycache__`、`美女.blend1` 等原样保留，去留由 `.gitignore` 决定（不删除）。
- 工作区根目录文件数复测仍为 3（`AGENTS.md` / `README.md` / `.zcodeignore`）。