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
| `人物建模/scripts/measure.py` | 外观体检：量测 → 基准表比对 → must/warn 判定（exit 1=有 must FAIL） | `python 人物建模/scripts/measure.py [--cached] [--blend X.blend] [--spec spec/xxx.json]` |
| `人物建模/scripts/brief.py` | **brief → profile 受控补丁**：未知键/类型不符/超范围报错，未接线键警告；默认 dry-run，`--apply` 写盘并备份；`--run` 接 build/measure/check/audit | `python 人物建模/scripts/brief.py briefs/example.json [--json] [--apply [--run [--strict]]]`；自测 `--selftest`（14 项） |
| `人物建模/scripts/rag.py` | **检索 → bapi context**：catalog/bapi/lib/手册建 FTS5，按任务出 Markdown context，含名词同名函数锚点；不调用 LLM，产物仍走 verifier | `python 人物建模/scripts/rag.py build` / `query "倒角 宽度"` / `context "带倒角立方体" --out out/rag_context.md` / `selftest`（11 项） |
| `人物建模/scripts/run_bapi.py` | **候选脚本执行门**：headless Blender 跑候选 bapi 脚本，捕获退出码/耗时/stdout/stderr，检查期望文件非空与期望文本；默认只允许 out/ 下的候选 | `python 人物建模/scripts/run_bapi.py out/candidate.py [--expect-file out/x.png] [--expect-text TEXT] [--json]`；自测 `--selftest`（3 项） |
| `人物建模/scripts/visual_review.py` | **视觉审查问题单**：从 Blender体检 manifest 生成视图清单/渲染检查，校验 problems 字段，出 Markdown 汇总；不做视觉判断 | `init --manifest ../Blender体检/out/<模型>/manifest.json --out out/<模型>_visual_review.json`；`validate` / `summary` / `selftest`（4 项） |
| `人物建模/scripts/bench.py` | **内部执行 benchmark**：逐任务查 RAG 命中，再把手写候选放进独立 run 目录走 `run_bapi`，记录退出码/墙钟/产物；不是 LLM 评测 | `python 人物建模/scripts/bench.py list` / `run [--task id] [--candidate-dir DIR] [--json]` / `selftest`（4 任务 2026-11-03 实测 4/4） |
| `人物建模/scripts/audit.py` | **游戏可用性审计**：面数/四边面/可合并三角/非流形/UV/权重和/骨骼/顶点属性/产物新鲜度，56 项 → PASS/WARN/FAIL（exit 1=有 FAIL） | `python 人物建模/scripts/audit.py [--fast] [--blend X.blend] [--glb X.glb]`；阈值在 `人物建模/spec/game_budget.json` |
| `人物建模/m7_aux.py` | **全向补视角**：顶/斜顶/仰视×2/左脸/仰视上半身/正后 7 机位 + 拼版，补 m2~m5 全平视留下的下半球与正顶盲区；`--nool` 关描边看裸几何 | `python 人物建模/scripts/build.py aux [--nool]`；产物 `out/m7_aux_*` |
| `人物建模/scripts/deliver.py` | **交付闸门**：把外观 spec / 16 机位 / 游戏可用性 / 绑定回归四份产物汇成「进游戏」「进作品集」两个结论（exit 1=有目标未过或产物过期） | `python 人物建模/scripts/deliver.py [--profile game\|portfolio] [--run] [--json]`；配置在 `人物建模/spec/deliver.json` |
| `人物建模/scripts/sweep.py` | 参数→形状响应表（逐点重建+量测，产物 out/sweep_*.json） | `python 人物建模/scripts/sweep.py --param appearance.head_to_body_ratio --values 6.5,7.0,7.5,8.0` |
| `人物建模/scripts/rename_assets.py` | 美女.blend → <角色名>_rig_v001.blend 批量改名（dry-run 默认） | `python scripts/rename_assets.py --to <角色名> [--apply]`，**执行前关前台 Blender** |
| `BlenderAPI/README.md` | headless Blender 程序化建模封装层 bapi 的说明书（7 模块/自测/catalog 口径/已知边界） | 阅读件；自测：`blender -b --factory-startup --python-exit-code 1 --python "…/BlenderAPI/selftest.py"`（2026-11-03 实测 36/0/0，exit 0） |
| `docs/manual_index.py` | 离线 Blender 5.2 中文手册全文检索（2356 页/154 万字）＋ API 名→手册页；补 catalog 缺的「参数什么意思」那一层；纯 Python 无 bpy，索引缺失时自动重建 | `python docs/manual_index.py "实体化 偏移"` / `--api SolidifyModifier` / `--show <页>` / `--selfcheck`（10 项，2026-11-03 实测 10/0，exit 0） |
| `docs/手册学习笔记.md` | 手册包概况、检索词对照（「重新网格化」→「重构网格」）、手册对既有实现的核对结论 | 阅读件 |
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
