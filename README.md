# Blender建模

AI 用 Blender 建模的工具集：全部以 headless Blender（`--background --python`）为唯一驱动方式，覆盖「程序化生成 → 视觉体检 → 脚本化修复 → 复检」闭环。2026-11-01 由散在三处的五个组件整合建仓（公开仓 [LLL-404/blender-modeling](https://github.com/LLL-404/blender-modeling)），整合对照见文末。

## 组件

| 目录 | 是什么 | 详见 |
|---|---|---|
| `Blender体检/` | 对任意 `.blend` 一条命令渲 16 环绕 + 顶视 + 拼版总览，供 AI 读图挑错；配套「渲染 → 读图开问题单 → 只修可脚本修的 → 复渲复检，最多 3 轮」自检闭环协议 | 见其 README |
| `人物建模/` | headless 程序化生成二次元角色：m1~m5_rig 六阶段 + opt 参数搜索器 + scripts 入口/自检（6 入口 + cfg + 12 lib 模块） | 见其 README |
| `skills/blender-procedural-character/` | 程序化角色方法论 skill：249 行 SKILL.md + 11 篇 references + 2 个验收探针，沉淀 Blender 5.2 API 坑与假达标识别 | 见 SKILL.md |
| `stardust/` | 星尘游戏 Blender 建模管线脚本：道具批量建模渲染 / 角色四向帧 / 立绘 3渲2 / MPFB 人体 / glb 导出，共 6 个 | 见「下游与契约」 |
| `blender-rig/` | reroute-godot 建筑两骨绑扎（z 向 smoothstep 权重）+ glb 修贴图 + 预览/压测，4 个脚本 | 见「下游与契约」 |

## 快速上手

环境要求：Blender 5.2.2 LTS（各工具自动探测 `D:/Program Files/Blender Foundation/*/blender.exe`，探测不到用环境变量 `BLENDER_EXE`）；人物建模另需系统侧 Python + numpy/Pillow。

```bash
# 体检：对任意 .blend 出 17 张图 + manifest（产物落 Blender体检/out/<模型名>/）
bash "D:/G/github/实用工具/Blender建模/Blender体检/check.sh" "<模型>.blend"

# 人物建模：全量重建 / 六探针自检（详见 人物建模/README.md）
python "D:/G/github/实用工具/Blender建模/人物建模/scripts/build.py" all
python "D:/G/github/实用工具/Blender建模/人物建模/scripts/build.py" check

# skill：CodeArts(Doer) 经 D:/G/github/.codeartsdoer/skills/ 下的 junction 启用；
# 其他宿主把 skills/blender-procedural-character 复制或链接进各自 skills 目录即可。
```

## 下游与契约

**stardust（切面：脚本在本仓，模型与产物在游戏工程）**：`D:/G/game/games/stardust/tools/blender/` 留着 `.blend`（stardust_props.blend，.gdignore 不入 Godot 导入管线）、渲染产物 `render_src/`、`render_body/` 与 MPFB 人体 `mpfb/human.obj`；本仓脚本以绝对路径读写它们。消费链：`build_props.py` → `render_src/` → 游戏 `post_props.gd` → `assets/sprites/props/`；`build_characters.py` → `render_body/` → 游戏 `char_sheet.gd` → `assets/sprites/characters/`；`export_props_glb.py` 读 `.blend` → 游戏 `assets/models/`。调用命令见游戏 `AGENTS.md`「本机工具」。

**blender-rig（依赖方向：本仓 → reroute-godot，单向）**：`rig_buildings.py` 读 reroute-godot `assets/models` 出绑骨 glb 落本仓 `out/`；入库真身在 reroute-godot 自己的 `assets/models/`（不经本仓中转）；`backup/` 是 2026-10-17 两栋建筑的历史快照。cashline 的 `docs/ART-PLAN-20261031.md` 把四脚本列为可用资产。

## 旧 → 新路径对照（2026-11-01 整合）

| 旧位置 | 新位置 |
|---|---|
| `D:/G/github/Tools/Blender体检/` | 本仓 `Blender体检/` |
| `D:/G/github/Tools/人物建模/` | 本仓 `人物建模/`（58 个跟踪文件的 git 历史保留在 Tools 仓） |
| `D:/G/github/.codeartsdoer/skills/blender-procedural-character/` | 本仓 `skills/blender-procedural-character/`（原位留 junction，CodeArts 照常启用） |
| `D:/G/game/games/stardust/tools/blender/*.py` | 本仓 `stardust/`（`.blend` 与渲染产物留在游戏工程） |
| `D:/G/game/games/blender-rig/` | 本仓 `blender-rig/`（4 脚本的 OUT/IMG 已改指新位置） |

## 安全纪律

渲染永远只读（headless、核对源文件 mtime 不变）；只有修复轮才写回 `.blend`，且写回前必须确认没有前台 Blender 窗口开着；修复只动「可脚本修」的（缩放/位移/旋转/法线/修改器/命名），造型与贴图绘制类只提意见不动手。
