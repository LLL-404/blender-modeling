# 人物建模

用 Python 脚本在 **headless Blender 5.2** 里程序化生成二次元女性角色（原神式三渲二），不手工雕刻：
`m1~m5_rig` 六个入口 + `lib/` 12 个建模模块 + `opt/` 参数搜索器，全部由 `cfg.py` 的参数表驱动，
跑一次 `python scripts/build.py all` 就能从空场景重建到「45 骨 + 四姿势 + 描边图」。

- 角色设定基准（6.5 头身、五官/发型/服装意图、配色规范）与 A/B/C/D 四阶段验收表：[DESIGN.md](DESIGN.md)
- 变更记录：[CHANGELOG.md](CHANGELOG.md)
- 参数搜索报告：[opt/REPORT.md](opt/REPORT.md)

## 快速开始

| 项 | 要求 |
|---|---|
| Blender | **5.2**（headless 即可，不需要 GUI） |
| Blender 路径 | 默认 `D:\Program Files\Blender Foundation\Blender 5.2\blender.exe`；用环境变量 `BLENDER_EXE` 覆盖 |
| 系统 Python | 3.10+，装 `numpy` + `Pillow`（仅像素统计/独立复算用，见 [requirements.txt](requirements.txt)） |

```bash
cd Tools/人物建模
python -m pip install -r requirements.txt       # 只有系统侧脚本需要
python scripts/build.py all                     # m1 -> m5_rig 全量重建，产物写 out/
python scripts/build.py check                   # 6 个探针自检，报告写 opt/logs/check_report.md
```

单步重建（任一非 0 立即停止并转发退出码）：

```bash
python scripts/build.py body|head|look|hair|outfit|rig
```

- Blender 不存在时 `build.py` 打印中文提示并 **exit 2**，不会静默失败。
- `rig` 会写项目根的 `美女.blend`，并跑 B4 回归断言（4 张姿势图 + 权重和 + 关键骨位移）。
- 构建不依赖当前目录：各入口与 `lib/shots.py:10` 的输出路径都由 `__file__` 推导；`build.py` 仍把 `cwd` 固定为项目根以统一行为。

## 目录结构

| 路径 | 是什么 | 关键点 |
|---|---|---|
| `cfg.py` | 角色参数表（身高、各段 z、半宽、细分、seed） | 改人先改这里；`HEIGHT` 是 `appearance.height` 的默认值（`cfg.py:13`） |
| `m1_body.py` | 素体：四视图 + 手部近景 | 手是独立物体 `Hands`，不 join 进 `Body`（5mm 体素会把手指糊成一根） |
| `m2_head.py` | 头 + 五官（眼/眉/鼻/嘴/耳） | 贴片按材质分槽 |
| `m3_look.py` | 三渲二着色验收：描边 / 色阶 / 面部阴影 / 泛光 | `base_px=3.5`（`lib/look.py:30`） |
| `m4_hair.py` | 头发：发帽 / 后发束 / 刘海 / 侧发 / 呆毛 | 高光带 + 轮廓光验收 |
| `m5_outfit.py` | 服装：衬衫 / 裙 / 领 / 袖口 / 卷边 | 净空断言内联在 `lib/outfit.py` |
| `m5_rig.py` | **45 骨**骨架 + 蒙皮 + 4 姿势（rest/wave/walk/reach）+ B4 断言 | 写 `美女.blend`；`lib/rig.py:38` 为骨表 |
| `lib/`（13 个模块） | `body` `hand` `head` `look` `hair` `outfit` `rig` `mats` `meshkit` `sheet` `shots` `optio` `charparams` | `optio.py` 是搜索器参数注入层（读 `opt/best.json`）；`charparams.py` 是外观旋钮读取层（读 `params/profile.json`），两者都带默认值回退 |
| `opt/` | 参数搜索器：`halton` / `space_geom` / `space_pixel` / `eval_geom` / `eval_pixel` / `search` / `search_pixel` / `best.json` / `REPORT.md` | 见下文「参数搜索器」 |
| `params/` | `profile.json` 外观旋钮（37 键 / 4 组）+ `README.md` 逐键表 | 删掉即回滚到未参数化行为（见下文） |
| `scripts/` | `build.py` 统一入口、`check.py` 探针自检 | 纯标准库，不 import bpy |
| `_stageA/` `_stageB/` `_stageC/` `_stageD/` | 各阶段探针与独立复算脚本（证据链，保留） | 探针日志 `_stage*/logs/` 不入库 |
| `_probe/` | 早期 `rig_probe.py`（已在 B 阶段被 `b_probe.py` 取代，留档） | — |
| `out/` | 渲染产物（png），**不入库** | 可由入口重跑重建 |
| `美女.blend` / `.blend1` | 可编辑工程文件，**不入库** | `m5_rig.py` 重建 |

## 阶段与验收

完整表在 [DESIGN.md §3](DESIGN.md)（A/B/C/D 各一张，含技术做法、阈值、风险/回退）。下面是收口后的代表性实测
（2026-11-01，证据在 `_stageA/logs/`、`opt/REPORT.md`、探针 stdout）：

| 阶段 | 做了什么 | 代表性实测（阈值） | 证据 |
|---|---|---|---|
| **A 修硬伤** | 手/脚趾重建、鼻/嘴/耳、头身比 6.95→6.5、衬衫净空、袖口、呆毛 | 每手 **4 指 × 3 段 + 拇指**（13 骨/13 组，`lib/hand.py:205,217`）；指尖 4 分量；腕部台阶 **+1.75mm**（≤3）；头身比 **6.505**（6.50±0.06）；鼻尖 **9.70mm**（8.5~10.0）；嘴宽 **11.22%**（10~13%）；耳高 **45.82mm**（45~50）；脚底 `z_min=0.0mm`（±2） | `DESIGN.md` §3.1、`_stageA/logs/accept_geom.json` |
| **B 骨架** | 分带权重、左右侧向约束、每手 13 骨替换 `hand.L/R`、Hands 挂骨架 | **45 骨**（fingers=24；21−2+2×13）；裙摆手臂骨主导 **0.00%**（≤5%）；左右串权 **0.000%**（≤0.2%）；Hands 权重和 **bad=0/5540，min=max=1.0000**；Hands rest→wave 的 evaluated bbox 角点位移 **761.3mm**（>50）；每手 13 组与骨名一一对应 | `_stageB/b_probe.py`、`opt/REPORT.md` §4 |
| **C 三渲二** | 反法线描边、面部阴影层、色阶重标定、头发高光 | 描边暗带 **p50=3px**（全身/上身，目标 2~4）；皮肤 **p50=195.0**（175~215）、**p95−p50=32.0**（≥30）、**p50−p5=26.8**（≥25）、≥228 占 **4.8%**（≤35%）；鼻下 median **168.2**（≤175）；下巴 shadow **77.1%**（≥8%）；手 vs 同侧前臂 **6.8 / 2.0**（≤8）；头发高光 **97.4%** 落在 z∈[1.52,1.60]（≥60%） | `_stageC/c_probe.py`、`opt/trials_pixel.jsonl` |
| **D 细节** | 刘海分组、后发束减薄、衬衫翻领、袖口卷边、裙褶非对称 | 刘海 **3 组（2/3/2）**、组间缝 **1.5mm**、覆盖额头 **85.2%**（≥70%）；后发束半宽 **19.0mm**（18~24）、厚 **9.0mm**（8~10）、沟壑 **5.6mm**；翻领 **V 深 18.5mm**（≥12）、后领高 **+18.5mm**（≥+8）；卷边可见凸出 **3.3mm**（2~4）、边界边 **0**；裙褶峰谷差 **25.9mm**（≥10）、正面中线为峰 | `_stageD/d_probe.py` |

**一键复检**：

```bash
python scripts/build.py check
```

它依次跑 `_stageA/a1_hand_probe.py`、`a2_face_probe.py`、`a4_fit_probe.py`、`_stageB/b_probe.py`、
`_stageC/c_probe.py`、`_stageD/d_probe.py`，把 PASS/FAIL 汇总到 `opt/logs/check_report.md`，
终端打印 `PASS=n FAIL=m SKIP=k` 与每个 FAIL 的行号。判定口径（不猜语义）：含 `FAIL` 记 FAIL；
含 `PASS` 或 `OK` 记 PASS（A4/D 两个探针用 `OK`）；只有 `[probe]/[bprobe]/...` 的信息行记 SKIP；
探针崩溃（非 0 退出或含 Traceback）单列 CRASH，不算进 SKIP。行号 = 该探针 stdout 的第 N 行，
完整输出落在 `opt/logs/probe_<脚本名>.log`。

存在 FAIL / CRASH / MISSING 时 `check` 退出码为 **1**（表示自检项未达标，不是构建本身崩溃）。
当前实测：`PASS=74 FAIL=2 SKIP=122`，两条 FAIL 就是下面「已知限制」的第 1、2 条。
注意 `A2` 与 `C` 两个探针只用 `[probe]` / `[cprobe]` 信息行、不打印 PASS/FAIL，
所以它们的行全部落进 SKIP（如实反映：这两个探针的判读要按 DESIGN 阈值人工做）。

## 产物与归档

| 产物 | 来源 | 入库 |
|---|---|---|
| `out/m1_body_{front,side,back,q34}.png`、`out/m1_hand.png`、`out/m1_sheet.png` | `m1_body.py` | 否 |
| `out/m2_face_*.png`、`out/m2_body*.png`、`out/m2_*.png` | `m2_head.py` | 否 |
| `out/m3_*.png` | `m3_look.py` | 否 |
| `out/m4_*.png` | `m4_hair.py` | 否 |
| `out/m5_face_*.png`、`out/m5_body_*.png`、`out/m5_body.png` | `m5_outfit.py` | 否 |
| `out/m5_pose_{rest,wave,walk,reach}.png`、`out/m5_poses.png`、`美女.blend` | `m5_rig.py` | `out/`、`*.blend` 否 |

按工作区 AGENTS.md 归档（**复制，不移动**，带时间戳子目录，不动工作副本）：

```bash
python scripts/build.py archive
# -> ../../散件归档/人物建模/20261101-113000/  （out/ + *.blend，复制不移动）
```

实现状态：已实现（`scripts/build.py` 的 `run_archive()`）。2026-11-01 用重定向目标
（`.tmp/人物建模-archive-test/`）实测过复制路径：`copytree` + `copy2` + 时间戳子目录 + 计数，
`rc=0`、`files=5 bytes=47165`；**没有**往真实的 `散件归档/` 写测试副本。

## 参数化旋钮（params/profile.json）

`params/profile.json` 是**手工调风格**的旋钮表（37 键 / 4 组），读取层 `lib/charparams.py`
提供 `get('appearance.height', 1.62)`（点路径 + 类型校验，缺失/坏 JSON/类型不符一律回退默认值，永不抛异常）。
默认值 = 引入旋钮之前的字面量，所以 **删掉 profile.json 就回到未参数化的行为（逐位一致）**。

```bash
# 换一套参数（不改任何 .py，新起一次 Blender 进程即可）
PM_PROFILE=params/_tmp/knobs.json blender -b --factory-startup --python _stageA/a2_face_probe.py
# 回滚：删文件，或把键删掉/改回默认值
rm params/profile.json
```

| 组 | 键数 | 状态 |
|---|---|---|
| `appearance` | 16（身高、头身比、头/脸宽、眼距/眼大小、鼻深、嘴宽、耳、肩/腰/髋、腿长比、臂粗、手/脚尺寸） | 已接线 |
| `hair` | 9（发色×2、刘海组数、发束缕数/宽/厚、呆毛长/粗、双马尾） | 7 个已接线；`hair_color` / `hair_shadow_color` 未接线（在 `lib/look.py`） |
| `outfit` | 7（衬衫/裙色、裙长、褶数、褶幅、袖长、领 V 深） | 5 个已接线；`shirt_color` / `skirt_color` 未接线（在 `lib/look.py`） |
| `render` | 5（`outline_px`、`skin_pos_mid/light`、`key_energy`、`rim_energy`） | **只登记，未接线**（`lib/look.py` / `lib/shots.py`） |

逐键现值/取值范围/影响面/`文件:行` 见 [params/README.md](params/README.md)；验证口径见该文末表
（`profile.json` 不存在 / 全默认时，`a1` `a2` `a4` `d_probe` `b_probe` 五行快照逐行零差异）。

## 参数搜索器

两段搜索器共用一份 `opt/best.json`（读-改-写，互不覆盖）：

| 段 | 入口 | 搜索维度 | 落盘 |
|---|---|---|---|
| 几何段 | `opt/search.py`（`--n --topk --rounds --seed`，`search.py:81-86`） | 裙腰 `SKIRT_WAIST_MARGIN` 与 inner 口径、手指混合指数 p、平滑次数、关节混合带宽 | `trials.jsonl`、`opt/best.json` 顶层 `best_params` |
| 像素段 | `opt/search_pixel.py`（`--n --topk --rounds --budget --tag`，`search_pixel.py:120-125`） | `outline_px`、`key_energy`、skin 三档 pos、`rim_energy`、`rim_azimuth` | `trials_pixel.jsonl`、`best.json` 的 `pixel.best_params` |

```bash
# 下文 blender 指 %BLENDER_EXE%（cmd）或 $BLENDER_EXE（git-bash），默认安装路径见「快速开始」
# 冒烟（每次约 4s/次评估）
blender -b --factory-startup --python opt/search.py -- --n 4
# 全量（实测 96 次唯一评估、488s）
blender -b --factory-startup --python opt/search.py -- --n 32 --topk 4 --rounds 2
# 验证注入链路（不重跑搜索，用 best.json 的值渲染/量测一遍）
blender -b --factory-startup --python opt/eval_geom.py -- --use-best
```

**`best.json` 的作用**：`lib/optio.py:100` 的 `param(key, default)` 按「进程内 override → `pixel.best_params` →
顶层 `best_params` → 模块默认值」取值，任何读盘/解析/类型失败都回退默认值。
**回滚方法：删掉 `opt/best.json` 即回到手调默认值**（`lib/optio.py:43-66`），不用改任何调用点；
单维回滚就直接改该文件里的字段（缺失键自动落回默认）。

**如实说明当前状态**：

- **几何段已实跑**：96 次唯一评估（488s，单次中位数 4.28s），score **20.2399 → 1.3556**（降 93.3%），
  best = `margin=0.008 / peak / p=4.5 / smooth=2 / joint_blend=3.0`。明细见 [opt/REPORT.md](opt/REPORT.md) §4–§5。
- **像素段只跑了冒烟**：`opt/trials_pixel.jsonl` 只有 1 条 baseline 记录（`n=2`，10:27，`score≈4e-6`），
  `best.json` 里**还没有 `pixel` 段**。全量（`--budget 24`）未跑完，像素段最优参数尚不存在。
- `opt/logs/`、`opt/tmp/`、`opt/trials*.jsonl` 都不入库；`opt/best.json` 与 `opt/REPORT.md` **必须入库**。

## 已知限制

如实列出，不美化：

1. **交叉姿势 60°/30° 的法线翻转 17 条**（几何穿模）。`b_probe` R3 实测 `3.967/0/17`，注入 `best.json` 前后逐字相同，
   属 Body 权重公式的既有缺陷，与搜索参数无关（`opt/REPORT.md` §6 第 5 条）。
2. **屈指最小边长比 0.582，阈 0.6**，仍未达标。搜索已把它从 0.5289 改善到 0.5817（`>1.5×` 的边 35→21 条），
   但最差边位于掌根/近节交界（`palm.L ↔ index_proximal.L`，rest 长 1.53mm），是 2mm 体素短边 + 两骨权重差的**拓扑硬边界**；
   要真正过 0.6 需要改 `assign_groups` 的算法本身（`opt/REPORT.md` §6 第 1 条）。
3. **轮廓光在 3px 描边下判定不可达**：`c_probe` 实测 `rim` 亮带 `p50=0px`、`rim_dark p50=0px`（目标 2~6px），
   `trials_pixel` baseline 里 `rim_hair_n=1`（只 1 个像素）。描边与轮廓光在深色区域互相抵消，
   当前参数下只能二选一（取舍与证据见 `opt/REPORT.md`）。
4. **描边像素宽只在全身/上身达标**：`m3_body_q34` / `m3_upper` / `m5_body_front` 的暗带 **p50=3px**，
   但脸部特写 `m3_face_front` **p50=7px**、`m4_face_front` **p50=0px**（`c_probe` 2026-11-01 实测，目标 2~4）。
   `Head` 的线宽在 `lib/look.py` 的 `_OL_PX` 里单列，是为两个视图分别换算的，不是同一口径。

## 依赖与版本

| 依赖 | 版本（本机实测 2026-11-01） | 用途 | 备注 |
|---|---|---|---|
| Blender | 5.2（`blender.exe` 113MB） | 全部构建与几何探针 | headless：`-b --factory-startup --python` |
| 系统 Python | 3.14.4 | `scripts/*.py`、`accept_pixels.py`、`d_probe.py` 纯 Python 模式 | 只要求标准库 + 下面两个包 |
| numpy | 2.4.4 | 所有量测/像素统计 | Blender 自带一份，系统侧另装 |
| Pillow | 11.3.0 | `accept_pixels.py` / `accept_b_pixels.py` / `d_probe.py` 读 png | Blender 自带的 Pillow 不保证有 |

**BlenderPy 注意事项**：本项目的所有拟合/渲染都假设运行在 `blender.exe` 进程内（`bpy` 版本与 5.2 严格对齐）。
如果用 `pip install bpy` 在系统 Python 里跑，版本与安装的 Blender 不一致会出现 API 差异（`Image.pixels` 编码、
`Solidify` 默认值、`--factory-startup` 语义），**不要混用**；请直接用 `blender.exe -b --python ...`。

## 迁移记录

2026-11-01 自工作区根 `D:\G\github\人物建模` **整体 mv** 到 `D:\G\github\Tools\人物建模`：
代码一行未改，`from lib import ...` / `import cfg` 全部照旧有效（各入口用 `sys.path.insert(0, HERE)` 自定位）；
`out/` 与 `*.blend` 交给 `.gitignore`，不做删除。