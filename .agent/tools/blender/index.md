# Blender 建模工具入口索引（机器可读）

> 本文件只是**入口索引**；方法论与闭环协议唯一口径在 `skills/blender-procedural-character/SKILL.md` 与
> `Blender体检/README.md`——改口径去那边，这里跟着更新，防双源。

| 路径 | 用途 | 调用方式 |
|---|---|---|
| `Blender体检/check.sh` | 任意 .blend → 16 环绕+顶视+拼版+manifest（只读渲染） | `bash "…/Blender体检/check.sh" "<模型>.blend" [--engine eevee/workbench/cycles] [--views N]` |
| `Blender体检/render_views.py` | 渲染本体（由 check.sh 驱动，勿直跑） | — |
| `Blender体检/appendix_a.py` | stardust_props 渲染的独立验收 | `python appendix_a.py`（读 out/…/manifest.json） |
| `人物建模/scripts/build.py` | 人物建模统一入口：body/head/look/hair/outfit/rig/check/all/archive | `python 人物建模/scripts/build.py <cmd>`（ROOT 按 __file__ 推导，cwd 无关） |
| `人物建模/scripts/check.py` | 六探针自检 → opt/logs/check_report.md | 经 `build.py check` 或直跑 |
| `人物建模/scripts/rename_assets.py` | 美女.blend → <角色名>_rig_v001.blend 批量改名（dry-run 默认） | `python scripts/rename_assets.py --to <角色名> [--apply]`，**执行前关前台 Blender** |
| `stardust/build_props.py` | 星尘道具批量建模+渲染（产物落游戏仓 render_src/） | `blender --background --python "…/stardust/build_props.py"` |
| `stardust/build_characters.py` | 星尘角色四向帧渲染（→ render_body/ → 游戏仓 char_sheet.gd） | 同上形态，`-- lila` 单人 |
| `stardust/build_characters_mpfb.py` | MPFB 人体版角色（WIP，未接游戏） | 同上 |
| `stardust/build_portraits.py` | 星尘立绘 3渲2（→ 游戏仓 tools/portrait/raw） | 同上，`-- lila normal` 单张 |
| `stardust/gen_human.py` | MPFB 基础人体 OBJ 生成（→ 游戏仓 mpfb/human.obj） | 同上（需 MPFB 扩展） |
| `stardust/export_props_glb.py` | stardust_props.blend → 游戏仓 assets/models/*.glb | `blender --background stardust_props.blend --python …` |
| `blender-rig/rig_buildings.py` | reroute-godot 建筑两骨绑扎（SRC=游戏仓 assets/models） | `blender --background --python …` |
| `blender-rig/fix_textures.py` | glb 贴图二进制直修 | `python fix_textures.py` |
| `blender-rig/preview_anim.py` / `stress_test.py` | 绑骨预览/应力压测渲染 | `blender --background --python …` |
| `prompts/审图自检闭环.md` | 会话速用提示词（来源=Blender体检/README.md） | 复制进会话 |
| `prompts/程序化角色DESIGN先行.md` | 会话速用提示词（来源=SKILL.md） | 复制进会话 |
| `docs/工程梳理与维护指南.md` | 结构树/脚本速查/SOP/防污染规则 | 阅读件 |

跨仓契约提醒：stardust 6 脚本与 blender-rig 的 SRC/OUT 指向游戏工程是**有意设计**，勿"规范化"；CodeArts junction（`.codeartsdoer/skills/blender-procedural-character` → 本仓 `skills/…`）勿改名勿挪。
