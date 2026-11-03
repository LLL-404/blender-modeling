# Blender建模

**让 AI 在 Blender 里建模**：用 **headless Blender**（`--background --python`）驱动建模全流程 —— 网格生成、骨骼绑定、动作/姿势、拓扑、UV、法线、材质贴图、导出；对象不限人物，道具/物品、环境等任意 `.blend` 都能接。全程不开图形界面、不靠人工拖窗口，覆盖 `生成 → 视觉体检 → 脚本化修复 → 复检` 闭环；产物与判据都是文件（PNG / JSON / PASS-FAIL 报告），能被 AI 直接读取和判定。

2026-11-01 由散在三处的五个组件整合建仓（公开仓 [LLL-404/blender-modeling](https://github.com/LLL-404/blender-modeling)），旧→新路径对照见文末。
2026-11-03 增补：外观重设定（**7.5 头身 / bob 发型 / 参考图配色**）、**spec 驱动的外观体检**（`spec/reference.json` + `measure.py`）、**`BlenderAPI/` 封装层**，以及 S8/S9 去重（D1–D6 / D11 / D12 / D15）——详见各组件 README 与 `人物建模/CHANGELOG.md`。

## 这是什么 / 不是什么

| 是 | 不是 |
|---|---|
| 一套 headless 批处理脚本 + 一套「AI 读图挑错」方法论，能力面覆盖网格/骨骼/动作/拓扑/UV/法线 | Blender 插件，不需要安装到 Blender 里 |
| 面向「机器判定」：每条命令都产出可核对的文件（PNG / manifest.json / PASS-FAIL 报告） | 面向「出成品图」：不做后期、不替代美术 |
| 六个独立模块（`Blender体检` / `人物建模` / `BlenderAPI` / `skills` / `stardust` / `blender-rig`），可单独用，互不依赖 | 一条龙框架，没有共享 SDK，也没有统一 CLI |
| 与具体工程解耦：脚本本身无凭据、无业务字段 | 完全自包含：`stardust/`、`blender-rig/` 与本机游戏工程有硬编码契约，见「跨仓契约」 |

## 能力面 → 落点

定位里说的每项能力，在仓内部有对应实现（不写没有落点的主张）：

| 能力 | 落点（人物/道具/环境） |
|---|---|
| 网格（程序化生成） | `人物建模/lib/meshkit.py`（放样/超椭圆/裁剪）；`stardust/build_props.py`（道具） |
| 骨骼（绑定/蒙皮） | `人物建模/lib/rig.py`（45 骨 + 每手 13 骨 + 分带权重）；`blender-rig/rig_buildings.py`（建筑绑骨） |
| 动作/姿势 | `人物建模` rest/wave/walk/reach 四姿势 + B4 回归断言；`blender-rig/preview_anim.py`（动画预览） |
| 拓扑 | `人物建模/lib/retopo.py`；E1/E2 UV 展开与残余三角归因（Body/Hands 100% quad） |
| UV | `人物建模/lib/uvkit.py`；`m6_asset.py` 五网格展开 |
| 法线 | `m6_bake.py` 法线一致性修正（Head 377 / Hair 9828 / Outfit 1280）；反法线描边壳 |
| 视觉体检（对象无关，任意 .blend） | `Blender体检/check.sh`：16 环绕 + 顶视 + 拼版 + manifest，供 AI 读图挑错 |
| 量化验收（形状 → 数字 → 判定） | `人物建模/spec/reference.json`（14 指标基准表）+ `scripts/measure.py`（差值表/PASS-FAIL）+ `lib/appearance.py`（顶点投影量测，不渲染） |
| 通用封装（headless 常用面） | `BlenderAPI/bapi`：env/obj/mesh/mod/mat/shot/sculpt 七子模块 + `catalog/`（扫描的 5.2 API 目录）+ 36 项自测 |

## 环境要求

| 项 | 要求 | 说明 |
|---|---|---|
| Blender | **5.2 LTS**（`D:\Program Files\Blender Foundation\Blender 5.2\blender.exe`） | 各脚本自动探测；探测不到时用环境变量 `BLENDER_EXE` 指定绝对路径 |
| Python | 系统侧 Python 3.10+ | 仅 `人物建模/scripts/` 下入口（`build` / `check` / `measure` / `sweep` / `rename_assets`）需要；纯标准库 |
| Python 包 | `numpy`、`Pillow` | 只有人物建模需要，见 `人物建模/requirements.txt` |
| BlenderAPI 依赖 | 无 | 只用 Blender 自带 Python（5.2 自带 3.13），不需要 numpy / Pillow |
| Shell | bash（Git Bash 即可） | 只有 `Blender体检/check.sh` 需要 |
| 可选扩展 | MPFB | 只有 `stardust/gen_human.py`、`stardust/build_characters_mpfb.py` 需要 |

## 快速上手

四条命令足以判断这个仓在你机器上能不能跑：

```bash
# 1) 视检任意 .blend：17 张图 + manifest，约 5 秒
bash "D:/G/github/实用工具/Blender建模/Blender体检/check.sh" "<任意模型>.blend"

# 2) 程序化生成一个角色（六阶段全跑）
python "D:/G/github/实用工具/Blender建模/人物建模/scripts/build.py" all

# 3) 六探针自检，PASS/FAIL 汇总到 opt/logs/check_report.md
python "D:/G/github/实用工具/Blender建模/人物建模/scripts/build.py" check

# 4) 外观 spec 体检：实测 vs spec/reference.json 的 14 条基准，出差值表
python "D:/G/github/实用工具/Blender建模/人物建模/scripts/build.py" measure
```

封装层活得到不到，另有第 5 条：`& "<blender>" -b --factory-startup --python-exit-code 1 --python "…/BlenderAPI/selftest.py"`（实测 PASS=36 FAIL=0 SKIP=0，exit 0，约 3.2s）。

体检产物落在 `Blender体检/out/<模型名>/`：`view_000.png` … `view_015.png` + `view_top.png` + `sheet.png`（拼版总览）+ `manifest.json`（相机参数与文件清单）。

## 组件

| 目录 | 是什么 | 规模 | 详见 |
|---|---|---|---|
| `Blender体检/` | 对任意 `.blend` 渲 16 环绕 + 顶视 + 拼版总览，供 AI 读图挑错 | 1 驱动 + 2 脚本 | 其 `README.md` |
| `人物建模/` | headless 程序化生成二次元角色：六阶段 + 参数搜索器 + 资产化 + spec 外观体检 | 6 入口 + `cfg` + 18 lib + `scripts/` + `spec/` | 其 `README.md` |
| `BlenderAPI/` | headless 程序化建模封装层：`bapi` 7 子模块（env/obj/mesh/mod/mat/shot/sculpt）+ 扫描的 5.2 API 目录 + 逐项自测 | 8 个 `.py` + `catalog/` 9 件 | 其 `README.md` |
| `skills/blender-procedural-character/` | 程序化角色方法论 skill：Blender 5.2 API 坑、假达标识别 | 253 行 + 11 篇 references + 2 探针 | `SKILL.md` |
| `stardust/` | 星尘游戏建模管线：道具 / 角色四向 / 立绘 / MPFB 人体 / glb 导出 | 6 脚本 | 见「跨仓契约」 |
| `blender-rig/` | reroute-godot 建筑两骨绑扎 + glb 修贴图 + 预览/压测 | 4 脚本 | 见「跨仓契约」 |

三层辅助件：

| 目录 | 用途 |
|---|---|
| `docs/工程梳理与维护指南.md` | 结构树、脚本速查、**AI 建模标准 SOP**、上下文防污染规则 |
| `prompts/` | 两份会话速用提示词（审图自检闭环 / 程序化角色 DESIGN 先行），来源指向 SKILL.md 与体检 README |
| `.agent/tools/blender/index.md` | 机器可读的入口索引（每个脚本一行调用方式） |

> **口径单一来源**：闭环协议与判据只在 `Blender体检/README.md` 和 `skills/…/SKILL.md`；`prompts/` 与 `.agent/` 是转发件，改口径要回源头改。

## 目录结构

```
Blender建模/
├── README.md                 本文件
├── docs/                     维护指南（SOP + 防污染规则）
├── prompts/                  会话提示词模板 ×2
├── .agent/tools/blender/     机器可读入口索引
├── Blender体检/               check.sh + render_views.py + appendix_a.py
│   └── out/                  体检产物（gitignored）
├── 人物建模/                  m1~m5_rig 六入口 + m6 资产化四步 + cfg + lib(18) + scripts + spec(外观基准)
│   ├── scripts/              build.py（统一入口）/ check.py（六探针）/ measure.py（外观 spec）/
│   │                         sweep.py（参数响应表）/ bpyrun.py（Blender 定位单源）/ rename_assets.py
│   ├── params/profile.json   39 键外观旋钮
│   ├── spec/reference.json   14 指标外观验收基准（must/warn）
│   └── opt/                  参数搜索器（halton 采样 + 几何/像素双评估）
├── BlenderAPI/               headless 封装层：bapi 7 模块 + catalog/（扫描的 API 目录）+ selftest.py
│                            （2026-11-03 新增；尚未被现有管线引用）
├── skills/blender-procedural-character/   SKILL.md + references(11) + scripts(2)
├── stardust/                 6 个游戏管线脚本（模型与产物在游戏仓）
├── blender-rig/              4 个绑骨脚本 + preview_common.py（D1-D6 共享层）+ backup/ + godot-test/
└── out/                      审计报告与临时件（gitignored）
```

## 组件用法

### Blender体检

```bash
bash "D:/G/github/实用工具/Blender建模/Blender体检/check.sh" "<模型>.blend" [参数]
```

| 参数 | 默认 | 什么时候改 |
|---|---|---|
| `--views N` | 16 | 每 360/N 度一张，调小加快 |
| `--elevation 度` | 20 | 环绕相机仰角 |
| `--engine` | `eevee` | headless 下 EEVEE 报错就换 `workbench`（快、只看形）或 `cycles`（慢、看质感） |
| `--res N` | 512 | 渲染边长，也是拼版单元尺寸 |
| `--out 目录` | `Blender体检/out/<模型名>/` | 换落点 |
| `--no-sheet` | 关 | 不要拼版总览 |
| `--factory` | 关 | 模型自带场景污染画面时用出厂设置重开 |

**只读保证**：`check.sh` 记录源 `.blend` 的 mtime，渲染后比对，变了就报警。它不会写模型文件。

### 人物建模

```bash
python "…/人物建模/scripts/build.py" <step>
```

`ROOT` 按 `__file__` 推导，在哪个目录执行都行。

| step | 做什么 |
|---|---|
| `body` `head` `look` `hair` `outfit` `rig` | 六阶段逐段重建（m1→m5_rig），每步单独出图 |
| `all` | 依次跑上面六步（**不含** asset） |
| `asset` | M6 资产化四步，顺序不可打乱：`m6_asset`（E1+E2 UV 展开与残余三角归因）→ `m6_bake`（E3 色板贴图 + AO + 法线一致性）→ `m6_export`（E4 去描边壳 + PBR + glb 导出与回读）→ `m6_multiview`（E5 16 机位环绕复核，toon vs glb 对照） |
| `check` | 六探针自检，PASS/FAIL 汇总到 `opt/logs/check_report.md` |
| `measure` | 外观 spec 体检：量 `美女.blend` → 对 `spec/reference.json` 判 → 出差值表与 `out/appearance_report.json`（must 级 0 FAIL 才过） |
| `archive` | 把 `out/` 与 `*.blend` **复制**（不移动）到 `D:\G\github\散件归档\人物建模\<时间戳>\` |

`lib/` 18 个模块分两类：**建模**（`body` `head` `hand` `hair` `outfit` `look` `mats` `meshkit` `rig` `shots` `charparams` `optio`）、**资产化与出图/量测**（`asset` `bake` `retopo` `uvkit` `sheet` `appearance`）。

外观旋钮：`params/profile.json`（39 键）→ `lib/charparams.py` 读取；参数搜索结果落 `opt/best.json`，由 `lib/optio.py` 注入。外观基准：`spec/reference.json`（14 指标）→ `scripts/measure.py` 判定；参数连带影响用 `scripts/sweep.py` 扫描量出（响应表），别靠读代码猜。

### stardust（6 个脚本）

```bash
blender --background --python "D:/G/github/实用工具/Blender建模/stardust/<脚本>.py" [-- 参数]
```

| 脚本 | 产物 | 备注 |
|---|---|---|
| `build_props.py` | 游戏仓 `tools/blender/render_src/*.png` | 道具批量，2048 宽正交透明底 |
| `build_characters.py` | 游戏仓 `render_body/` | 角色四向，`-- lila` 单人 |
| `build_characters_mpfb.py` | 同上 | MPFB 人体版，**WIP 未接游戏** |
| `build_portraits.py` | 游戏仓 `tools/portrait/raw/` | 立绘 3渲2，`-- lila normal` 单张 |
| `gen_human.py` | 游戏仓 `mpfb/human.obj` | 需 MPFB 扩展 |
| `export_props_glb.py` | 游戏仓 `assets/models/*.glb` | `blender --background <blend> --python …` |

**这 6 个脚本没有命令行参数**，读写哪个文件由文件头常量决定。要换模型就改头几行的 `BLEND_PATH` / `OUT_DIR`。

### blender-rig（4 个脚本 + 1 共享层）

| 脚本 | 作用 | 调用 |
|---|---|---|
| `rig_buildings.py` | 建筑两骨绑扎（z 向 smoothstep 权重） | `blender --background --python …`，读 `reroute-godot/assets/models`，写本仓 `out/` |
| `fix_textures.py` | glb 贴图二进制直修 | `python fix_textures.py` |
| `preview_anim.py` | 绑骨预览渲染（输出 `preview/*.png` 560×560） | `blender --background --python …` |
| `stress_test.py` | 应力压测渲染 | `blender --background --python …` |
| `preview_common.py` | D1-D6 共享层：清场 / 引擎回退 / 世界包围盒 / 按包围盒架机 / 渲染落盘 / 输出设置 | 被上面三个脚本转调，不直跑 |

同样无 CLI 参数，`SRC` / `OUT` / `IMG` 是文件头常量。

**实跑状态（2026-11-03）**：三脚本在本仓依次实跑通过（`rig_buildings` → 2 个 glb；`preview_anim` → 11 张 560×560 PNG；`stress_test` → 2 张压测图，均 exit 0）。这次实跑抓到一个重构回归：`PREVIEW_RES` 定义后无人引用，分辨率会退回出厂 1920×1080（已修，见 `人物建模/CHANGELOG.md` v0.4.0）。

### BlenderAPI

`bapi` 是「能用 `bpy.data` 就不碰 `bpy.ops`」的 headless 封装层，与其它组件的脚本无关、可独立用：

```python
import sys; sys.path.insert(0, r"D:/G/github/实用工具/Blender建模/BlenderAPI")
import bapi
bapi.env.reset()
ob = bapi.mesh.sphere(0.5, name="head")
bapi.mod.subsurf(ob, 2)
bapi.mat.assign(ob, bapi.mat.principled("skin", base_color=(0.9, 0.7, 0.6)))
```

自测：`blender -b --factory-startup --python-exit-code 1 --python "…/BlenderAPI/selftest.py"` → 实测 **PASS=36 FAIL=0 SKIP=0**（2026-11-03，3.23s）。`catalog/` 是脚本在运行中的 Blender 里扫描出的 API 目录（5.2.2：1129 操作符 / 562 节点 / 83 修改器），**只证明 API 存在，不证明 headless 可用**——可用性以 selftest 为准。详见 `BlenderAPI/README.md`。

### skill

不是"跑"的，是给 AI 读的。CodeArts(Doer) 经 `D:/G/github/.codeartsdoer/skills/blender-procedural-character` 的 junction 自动加载（junction 指向本仓 `skills/…`）。换其他宿主就把该目录复制或链接进它的 skills 目录。

## 跨仓契约

**这一节是硬约束，脚本里的绝对路径是刻意设计，不要"顺手规范化"。**

| 契约 | 内容 |
|---|---|
| stardust 模型与产物 | `.blend`、`render_src/`、`render_body/`、`mpfb/human.obj` 全在 `D:/G/game/games/stardust/tools/blender/`（该目录有 `.gdignore`，**勿删**）。本仓只放脚本 |
| stardust 消费方 | `build_props.py` → `render_src/` → 游戏 `post_props.gd` → `assets/sprites/props/`；`build_characters.py` → `render_body/` → 游戏 `char_sheet.gd` → `assets/sprites/characters/`；`export_props_glb.py` → `assets/models/` |
| blender-rig 依赖方向 | **单向**：本仓 → `reroute-godot/assets/models`。入库真身在 reroute-godot 自己的 `assets/models/`，不经本仓中转 |
| CodeArts junction | `.codeartsdoer/skills/blender-procedural-character` → 本仓 `skills/…`。**勿改名、勿挪目录**，断了要在原位重建 |
| 游戏仓调用 | `stardust/AGENTS.md:12` 以绝对路径调用本仓 `stardust/build_props.py`。挪本仓目录要同步改它 |

## 资产命名约定

资产文件 = **角色名_资产类型_版本**（如 `<角色名>_rig_v001.blend`）。批量改名用 `人物建模/scripts/rename_assets.py`（**默认 dry-run**，只打印计划；`--apply` 才动文件；角色名由作者提供，本仓无任何名字字段可依）。

目录名**维持现状**不改：`skills/…` 被 CodeArts junction 锁定、`stardust/…` 被游戏仓 AGENTS.md 绝对路径调用、`人物建模/`、`blender-rig/` 是模块锚点。

`m1~m5`（部件码_部件名）与 `_stageA~D`（阶段码_阶段名）是**正式约定**，勿按「不合规」误改；`lib/` 下 18 个模块同理。

临时/中间 blend 不入库（`.gitignore` 全局忽略 `*.blend`），定稿走 `build.py archive` 出时间戳副本落 `散件归档`。

## 安全纪律

1. **渲染只读**：所有渲染走 headless，`check.sh` 有 mtime 守卫，渲染后源文件被改会报警。
2. **只有修复轮才写回 `.blend`**，且写回前必须确认没有前台 Blender 窗口开着（CLI 感知不到窗口内未保存状态）。
3. **修复只动「可脚本修」的**：缩放 / 位移 / 旋转 / 法线 / 修改器 / 命名。造型与贴图绘制类只提意见，不动手。
4. **临时件只落 `out/`**（已 gitignored），产物可由脚本再生，不把渲染 PNG / base64 灌进对话上下文。

## AI 建模标准 SOP

完整版见 `docs/工程梳理与维护指南.md`，摘要：

1. **读索引** → `.agent/tools/blender/index.md`
2. **选通道** → 建模 QA 用 `check.sh` + 读 `sheet.png` 开问题单（复渲 ≤3 轮）；程序化角色先写 DESIGN（比例表 + 配色 + 分阶段量化验收）再动手
3. **验收** → 人物建模改动后跑 `build.py check`（六探针）+ `build.py measure`（外观比例，must 级 0 FAIL）；渲染一律 headless 并核对 mtime
4. **归档** → 定稿跑 `build.py archive`
5. **收尾** → 临时件只留 `out/`

## 从旧位置迁移（2026-11-01）

| 旧位置 | 新位置 |
|---|---|
| `D:/G/github/Tools/Blender体检/` | 本仓 `Blender体检/` |
| `D:/G/github/Tools/人物建模/` | 本仓 `人物建模/`（58 个跟踪文件的 git 历史保留在 Tools 仓） |
| `D:/G/github/.codeartsdoer/skills/blender-procedural-character/` | 本仓 `skills/blender-procedural-character/`（原位留 junction） |
| `D:/G/game/games/stardust/tools/blender/*.py` | 本仓 `stardust/`（`.blend` 与渲染产物留在游戏工程） |
| `D:/G/game/games/blender-rig/` | 本仓 `blender-rig/`（4 脚本的 `OUT`/`IMG` 已改指新位置） |

## 已知缺口

| 缺口 | 影响 |
|---|---|
| **D7–D16 里语义重的 6 项仍延后** | D1–D6 / D11 / D12 / D15 已于 2026-11-03 完成（清单与理由见 `docs/工程梳理与维护指南.md` §六）；剩 D7 / D8 / D9 / D13 / D14 / D16（材质创建 / 描边接线 / m 入口描边块 / 头部坐标映射 / glTF 旗标 / bpy 像素读图）语义重，六探针门覆盖不到 stardust / blender-rig，要配管线回归专项做 |
| **机位表仍保留 face 0.30 / 0.32 分档** | D15 已把机位表收成 `人物建模/lib/shots.py:VIEWS` 单源、`skills/…/scripts/pixel_probe.py` 按 `m<数字>` 前缀查 `ORTHO_BY_STAGE` 取档，px↔世界换算不再偏 6.7%；m2/m3=0.30、m4/m5=0.32 的分档本身是否统一仍待作者定 |
| **stardust 未在本仓真实跑过** | `blender-rig` 三脚本已于 2026-11-03 实跑通过（见上文）；stardust 6 个脚本会往游戏仓写产物，仍留给游戏工程验证（硬编码目标已逐一存在性验证） |
| **`rename_assets.py` 只做过 dry-run** | 改名未执行，等角色名定下 |
| **BlenderAPI 尚未接入任何管线** | 目前只有自身 36 项 selftest 证据；要接管须先复跑 selftest 再按模块替换（`catalog/` 只证明 API 存在，不证明 headless 可用） |
| **仓库无 LICENSE** | 未声明开源许可，默认保留所有权利。要开放请先补 `LICENSE` |
