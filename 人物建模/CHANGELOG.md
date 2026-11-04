# 变更记录

## 2026-11-04 / v0.13.0 — 动几何：发束非均匀化 + 脸部线稿 + 资产化 LOD

### 验收结论（全链实跑）

| 闸门 | 结果 |
|---|---|
| `scripts/deliver.py` | **进游戏 可以交付 / 进作品集 可以交付**（exit 0） |
| `scripts/visual_gate.py` | PASS 3 / FAIL 0，基线漂移 0.0000 |
| `scripts/visual_gate.py --selftest` | 原图 0 FAIL；抹平细节的退化图 2 FAIL → 判据有效 |
| `scripts/audit.py` | PASS 49 / WARN 7 / FAIL 0 |
| `scripts/check.py` | PASS 71 / FAIL 1 / SKIP 125 / CRASH 0（唯一 FAIL 是已登记豁免 R4） |
| `build.py measure` | 13 PASS / 1 WARN / 0 FAIL |

### 改了什么

| 文件 | 动作 | 实测 |
|---|---|---|
| `lib/hair.py` + `lib/haircard.py` | 18 张等距竖直卡片 → 非均匀发束（间距/宽度/角度/长度/厚度逐束抖动、发梢收尖） | 条纹主峰 0.1696 → 0.0714（参考 0.0768，上限 0.1382） |
| `lib/face_detail.py`（新）+ `lib/head.py` | 独立对象的二次元线稿：睫毛、虹膜放射纹、眉丝、鼻影、唇线、卧蚕/颧骨/鼻翼弧；不参与描边壳 | 脸窗边缘密度 0.0382 → 0.0839（下限 0.0795） |
| `m6_asset.py` | 工作文件与游戏资产分离：`美女.blend` 保持 DCC 精度，另存 `美女_asset.blend` 做封闭 + 减面 + 四边收敛 + 权重归一 + UV；LOD 目标直接取 `game_budget.json` 的 `per_mesh_tri_warn` | 三角面 201,830 → 49,500；Head 非流形 628 → 0；可合并三角 8 → 0 |
| `scripts/visual_gate.py` + `spec/visual_gate.json` | 脸窗 [45%,85%] → [30%,70%]（眼睛→嘴角），重新校准基线 | 参考 0.1325；原窗口把眼睛排除在外，逼建模侧拿脸颊排线凑密度 |
| `scripts/render_visual_front.py`（新） | 固定正面机位出对照图 | — |

### 踩过的坑（别再试）

| 尝试 | 结果 | 处理 |
|---|---|---|
| 距离硬截断换 smoothstep 软衰减，想修屈指 0.582 | min 0.582 → 0.495，拉伸边 21 → 63 | 回退 |
| 短边权重对齐阈值 0.6mm → 2mm，并挪到截断之后 | min → 0.080，max 1.788 → 3.570，拉伸边 → 225 | 回退 |
| 脸颊加 9 条等距长竖线 / 6 条不等距短弧凑边缘密度 | 渲成栅栏 / 划痕，属刷指标 | 全撤；改上移脸窗 + 补真实五官短弧 |
| `quads_converge` 只跑在 UV 展开前 | 展开后 UV 变连续，Head 存盘仍冒出 8 对可合并三角 | 改「展开 → 收敛」固定点循环，第 2 轮归零 |

`lib/hand.py` 最终**零改动**（`git diff` 为空）；R4 屈指保持已登记豁免，未假装修好。

### 已知限制（人眼复核，闸门全过 ≠ 像）

并排看 `out/visual_front.png` 与 `spec/reference/1000139587.jpg`：

| 缺陷 | 性质 |
|---|---|
| 头顶菱形锯齿 + 多发黑色裂纹 | 描边壳 / 发束开放边造成的几何破面 |
| 眼睛是放射纹圆盘（钟表感），无眼窝与眼睑实体 | 脸仍是压平曲面 + 贴片 |
| 鼻子方块 + 两条长影线，嘴两条横线，无耳朵、无下颌 | 五官是线稿，不是实体结构 |
| 发束是粗叶片，不是细密发丝 | hair card 表示法上限 |

这些**加线、调参都盖不住**，要换几何表示法（实体眼窝/下颌 + 更细的发束分层）才解得掉。
本次交付的是「工程不再报假绿 + 资产能进引擎」，**不是**「模型已经像参考图」。

### 未做

推送远端是对外动作，未执行；本地提交等 BOSS 确认后再推。

## 2026-11-04 / v0.12.0 — 视觉闸门：把「像不像参考图」接进交付判定

### 为什么加（根因复盘）

BOSS 指出模型做得非常差。并排看参考图与当前渲染：参考图是细密分缕、有发旋和高光的
粉色短发 + 完整五官；当前是一顶等距褶皱的灯罩，脸为平板，眼两个圈、鼻一个点、嘴一条线。
而工程同时报 `check.py 71 PASS`、`measure 13 PASS / 0 FAIL`、16 机位一致性全绿。

| 层 | 根因 | 证据 |
|---|---|---|
| 判据 | 14 条 spec 全是宏观比例，0 条量五官 / 发丝 / 材质层次 | `spec/reference.json` |
| 谎报 | 交付配置写「头身比、**脸型、五眼、发型轮廓**」，后三项并不存在 | `spec/deliver.json`（旧版） |
| 空判 | A2 面部 `PASS=0 SKIP=14`、C 三渲二 `PASS=0 SKIP=35`；`parse_rig` 只读 PASS/FAIL，把 SKIP 全吞 | `check_report.md` / `scripts/deliver.py` |
| 无效判据 | 16 机位只判覆盖率与发黑，蘑菇头照样过 | `parse_views` |
| 表示法 | 脸是压平曲面 + 贴片、头发是椭圆壳 + 18 张等距卡片，结构上做不出细发丝和眼窝 | `lib/head.py` / `lib/hair.py` |

一句话：**工程一直在优化「能算的数字」，不是「像不像」**。参考图只在开工时被看了一眼，
之后再没进过任何判据；指标越刷越绿，模型一动不动。

### 做了什么

- 新增 `spec/reference/1000139587.jpg`：参考图入仓，可复现（原先只在剪贴板临时目录）。
- 新增 `scripts/render_visual_front.py`：固定 `m5_face_front` 机位出 `out/visual_front.png`，不新造灯光/不改材质。
- 新增 `scripts/visual_gate.py` + `spec/visual_gate.json`：亮粉种子 + 暗部补全的头发分割、512 宽归一化、3 条可解释特征、`--calibrate` / `--selftest` / `--probe` / 默认判定。
- 剔除 4 条不可靠特征（头发边缘密度、局部梯度、发梢起伏、FFT 主峰周期）：黑色描边壳会制造大量边缘，破面也会制造起伏，这些量分不清「细发丝」与「18 条黑沟槽」；仍作 `diagnostic_only` 输出。
- `scripts/deliver.py` 新增 `parse_visual`；`parse_rig` 在结论里点名零判定探针（只暴露、不阻断，因为 A2/C 设计上就是信息探针）；docstring 表格改掉「像不像参考图」的谎报。
- `spec/deliver.json` 修掉 appearance 的 `why`、新增 portfolio 硬闸门 `visual`。
- `requirements.txt` 补 `opencv-python>=4.8`；`README.md` 补视觉闸门一节与快速开始命令。

### 判据与自测

| 项 | 结果 |
|---|---|
| `visual_gate.py --calibrate` | 基线由参考图自身算出：明暗层次 0.5373 / 条纹主峰 0.0768 / 脸部边缘 0.1256 |
| `visual_gate.py --selftest` | 参考图自己 **3 PASS 0 FAIL**；抹平头发与脸部细节的退化图 **2 FAIL** → 判据有判别力 |
| `visual_gate.py` 当前模型 | **PASS 1 / FAIL 2** → 等距灯罩纹 `0.1696 > 0.1382`、平板脸 `0.0382 < 0.0753` |
| `check.py` | `PASS=71 FAIL=1 SKIP=125 CRASH=0`，与改造前一致，未破坏绑定回归 |
| `deliver.py` | portfolio 卡在 `visual`(FAIL) + `views`(STALE)；game 卡在 `asset`(FAIL) |

阈值 `lower_ratio=0.60` 的来历：初版 0.45 太宽，连「头发/脸部被抹平」的负控制图都能过
（0.504 / 0.432 都判 PASS），按坏例收紧到 0.60 后两项都 FAIL。**不是照当前模型反调**。

### 没做的事（别误读）

**没有改几何**。这次只让工程能自动发现「模型差」，模型本身仍是灯罩。
要真的变像，下一步必须动表示法：`lib/hair.py` 的 18 张等距卡片换成非均匀、带粗细变化
和发梢收尖的发束；`lib/head.py` 补眼窝 / 眼睑 / 下颌的实体结构。
加判据不会让模型变好，只会让它没法再蒙混过关。

## 2026-11-03 / v0.11.0 — 内部执行 benchmark + RAG 名词锚点

### 为什么加

v0.9 只证明了「RAG context → 手写 bapi → headless 跑通」能成一次；一次成功不是基线。补一个可重复的内部 benchmark：每个任务先查 RAG 必须命中指定 API，再把候选脚本放进独立 run 目录，用 `run_bapi.py` 的同一套门（退出码 / 期望文件非空 / 期望文本）执行，记录墙钟与产物大小。以后改检索或包装层，能直接看出是「召回掉了」还是「执行坏了」。

第一次跑就暴露一个召回问题：`球体 材质 Principled 渲染` 里 `bapi.mesh.sphere` 掉出 top 12——同时命中 material / principled / render 的通用块，把只命中 sphere 的短函数挤了下去。修法是给查询里的中文名词加「同名函数锚点」，不靠调 bm25 权重碰运气。

### 做了什么

- 新增 `bench/tasks.json` + `bench/candidates/*.py`（4 任务：倒角立方体 / 球体材质 / 圆柱 Solidify / 立方体 Subsurf），候选脚本自带面数、材质槽、产物大小断言。
- 新增 `scripts/bench.py`：`list` / `run [--task] [--candidate-dir] [--timeout] [--json]` / `selftest`；产物落 `out/bench/run-<时间戳>/`，汇总写 `out/bench/latest.json` 与 `latest.md`；`--json` 的进度行改走 stderr，stdout 保持纯 JSON。
- `rag.py` 新增名词锚点：按 `SYNONYMS` 映射出的英文词，取标题末段同名的 bapi/lib 函数（最多 4 条，不参与 bm25 打分）；`query()` 返回 `anchors`，`format_context()` 在 bapi 段前新增「查询名词精确命中（先看签名）」，同一函数不重复列；`selftest` 从 10 项加到 **11 项**。
- 候选断言加强：bevel ≥100 面、solidify ≥180 面、subsurf ≥90 面、材质槽必须为 `bench`，避免「脚本 exit 0 但修改器/材质没生效」也判过。

### 判据

| 项 | 结果 |
|---|---|
| `python scripts/rag.py selftest` | **PASS=11 FAIL=0**（新增「球体 → bapi.mesh.sphere」锚点用例） |
| `python scripts/bench.py selftest` | **PASS cube_bevel rag+exec** |
| `python scripts/bench.py run` | **4/4 全过**：rag 4/4、exec 4/4、pass_rate **1.0**、总墙钟 **6.794s**、平均 **1.686s/任务** |
| cube_bevel | 150 polys / 256,268 B PNG / 1.698s |
| sphere_material | 1152 polys / 275,573 B PNG / 1.634s |
| cylinder_solidify | 192 polys（素圆柱 96，Solidify 后翻倍）/ 287,962 B PNG / 1.716s |
| cube_subsurf | 96 polys / 264,389 B PNG / 1.689s |
| 四张产物 | 逐张读过：倒角立方体、球、圆柱、细分立方体，均不是黑图/空图；圆柱第一版因误用 `camera_ortho(height=...)` 拍成空帧，改成倾斜物体后重渲确认 |

### 边界

- **候选脚本是手写的 golden solution，不是 LLM 生成**。它测的是「RAG 召回 + run_bapi 执行门 + 环境」这条基线，不代表模型写代码的成功率。
- 锚点只认「标题末段 == 名词」，是确定性实体链接，不做语义消歧；同名函数不存在时不补位。
- `bench` 产物全在 `out/`（已 gitignore），不入库；任务定义与候选脚本在 `bench/`，入库。

## 2026-11-03 / v0.10.0 — 视觉审查问题单 + 体检 ignore

### 为什么加

`Blender体检/README.md` 的闭环第 3 步是「按视角列结构化问题」，但产物一直只存在于会话文字。研究对照里的 P2 也是「VLM 审图 → 结构化问题单 → 修复 patch」。这次把问题单落成 schema/validator/summary，并用真实 `美女.blend` 走了一轮「审图 → 判可脚本修 → 改渲染脚本 → 重渲 → 复核」。

### 做了什么

- 新增 `scripts/visual_review.py`：`init` 从 manifest 生成视图清单/渲染完整性检查；`validate` 校验 `id/view/severity/category/status/description/script_fixable` 与渲染文件；`summary` 出计数和 Markdown 表；`selftest` 4 项。
- `Blender体检/render_views.py` + `check.sh` 新增 `--ignore "floor*,ground*"`：按 glob 隐藏辅助对象并排除出取景；只改运行中场景，不保存 `.blend`；manifest 新增 `ignored` 字段。
- `Blender体检/README.md` 参数表/已知限制/闭环第 3 步登记；`人物建模/README.md` 加「视觉审查问题单」段。

### 判据（真实模型，不是合成图）

| 项 | 结果 |
|---|---|
| `python scripts/visual_review.py --selftest` | **PASS=4 FAIL=0** |
| `check.sh 美女.blend --views 8 --res 512` | 8 环绕 + 顶视 + sheet + manifest；3.34s；**角色只占约 40px/512** |
| `visual_review.py init` | 9 views / 11 render checks / 0 problems；validate ok |
| P1（high/camera） | 「大地面 floor 12×12 撑爆取景」→ `check.sh --ignore "floor*"` 重渲 3.08s；角色撑满画幅；manifest.ignored=["floor"]；P1 → fixed |
| P2（low/other） | 「sheet 空白格 0.35 深灰」→ 保留 Q2 契约值，P2 → accepted |
| `visual_review.py validate/summary` | ok=True；counts problems=2/open=0/fixed=1/high=1 |

### 边界

- `visual_review.py` **不做视觉判断**；图仍由人或 VLM 看，它只保证问题单可校验、可计数、可追踪。
- `out/美女_visual_review.json`、`Blender体检/out/美女/` 都是本地证据，不入库。
- `--ignore` 只影响本次渲染的隐藏与取景，不改源 `.blend`；默认仍不忽略任何对象，避免“偷偷少渲染”。

## 2026-11-03 / v0.9.0 — RAG → bapi context（检索层）

### 为什么加

研究对照里最直接的空白不是“模型不会写 bpy”，而是**没有把本仓版本正确的 API/写法喂给它**。BlenderRAG 用 500 个案例把编译成功率从 40.8% 提到 70%；本仓已经有 `catalog/`（5.2.2 实机扫描）、`bapi/`、`lib/` 和离线手册，缺的只是检索与上下文打包。

### 做了什么

- 新增 `scripts/rag.py`：从 `BlenderAPI/catalog/api.json`、`catalog/*.md`、`BlenderAPI/bapi/*.py`、`人物建模/lib/*.py` 采集 2333 个 chunk，建 FTS5；`query` 联合本地索引与 `docs/manual/manual.db`；`context` 输出六段 Markdown（约束 / bapi 函数 / 仓内范例 / API 目录 / 手册语义 / 输出契约）；`selftest` 建临时索引跑 8 条检索用例 + 格式断言。
- 新增 `scripts/run_bapi.py`：候选脚本执行门，headless Blender + `--factory-startup`，捕获退出码/耗时/stdout/stderr，检查期望文件非空与期望文本；默认只允许 `out/` 下的候选，`--allow-any` 才放行其它目录；不做 OS 沙箱。
- 中文查询扩展英文 API 词（倒角→bevel、实体化→solidify、立方体→cube、蒙皮→skin weight 等）；bm25 分数加 kind 先验（bapi +10 / lib +4 / catalog 0），避免“83 个修改器”这类目录大块霸榜。
- **不调用 LLM**：context 交给 agent/人写代码，写完仍走 `BlenderAPI/selftest.py`、`build.py check`、`measure.py`。

### 判据

| 项 | 结果 |
|---|---|
| `python scripts/rag.py build` | 2333 chunks / 3.2 MB / 0.36s |
| `python scripts/rag.py selftest` | **PASS=10 FAIL=0**（8 条检索 + 建索引 + context 格式） |
| `python scripts/rag.py context "做一个带倒角的立方体，正交渲染"` | 2957 chars；bapi 段含 `bapi.mod.bevel` / `bapi.mesh.cube` / `bapi.shot.camera_ortho` |
| 按 context 写 `out/rag_demo.py` 并 headless 跑 | **exit 0**；`beveled_cube` 152 verts / 150 polys；`out/rag_demo.png` 256,268 B；已读图确认是带倒角的立方体，不是黑图 |
| `python scripts/run_bapi.py --selftest` | **PASS=3 FAIL=0**（good candidate / bad exit 3 拒绝 / 缺期望文件拒绝） |
| `python scripts/run_bapi.py out/rag_demo.py --expect-file out/rag_demo.png --expect-text "[demo]" --json` | **exit 0 / elapsed 1.855s / ok=true**；文件 256,268 B 存在；stderr 空 |

### 边界

- 只是检索与上下文打包，不是端到端代码生成器；`out/rag_demo.py` 与 `out/rag_demo.png` 是本地验证产物，不入库。
- 手册索引 `docs/manual/manual.db` 与手册 zip 都不入库；换机器要先按 `docs/manual_index.py` 建索引。
- context 仍可能带无关 catalog 条目；排序先验只保证 bapi/lib 在分数接近时优先，不替代人工判断。

## 2026-11-03 / v0.8.0 — brief→profile 受控参数入口

### 为什么加

研究对照发现，本项目缺的不是“更会写 bpy 的模型”，而是**把自然语言先落成受控参数**的那一层。让 LLM 直接写代码会把 API 错用、部件悬空引进产线；先把意图落成 `profile.json` 的点路径，再用现有 `build`/`measure`/`audit` 验收，风险最低。

### 做了什么

- 新增 `scripts/brief.py`：读 brief JSON，按当前 profile 的键/类型/`params/README.md` 建议范围做校验；未知键、类型不符、超范围直接报错；未接线键、`hair.style != long` 下无效的发束键给 warning；默认 dry-run，`--apply` 备份到 `out/brief/` 后原子写盘；`--json` 供 agent 消费。
- `--run`：写盘后按 `build.py all`（blocking）→ `measure.py`（blocking）→ `build.py check`（advisory）→ `audit.py --fast`（advisory）跑验证链；`--strict` 把 advisory 升级为失败。
- 新增 `briefs/example.json`：7.5 头身 / bob / 藏青裙的示例 brief。
- `README.md`、`params/README.md`、`.agent/tools/blender/index.md`、`docs/工程梳理与维护指南.md` 登记入口与用法。

### 判据

| 项 | 结果 |
|---|---|
| `python scripts/brief.py --selftest` | **PASS=14 FAIL=0**（校验/类型/范围/未接线 warning/写盘+备份/非法 patch 拒写，加 4 条验证链 blocking/advisory/strict 行为） |
| `python scripts/brief.py briefs/example.json` | dry-run 出 4 行差值表；`appearance.height` 1.62→1.68、`hair.style` cards→bob、`outfit.skirt_length` 0.65→0.62，exit 0 |
| 临时 profile `--apply` | 写入 1.68/bob，其他键保持不变，备份存在，exit 0 |

### 边界

- **不解析自然语言**：`brief` 字段只作记录，真正的意图要先由人或 LLM 写成 `set` 点路径；本脚本只负责校验和落盘。
- 不代表外观已经达标：写盘后仍要跑 `build.py all` → `check` → `measure`；`audit`/`deliver` 另算。

## 2026-11-03 / v0.7.0 — 头发换成 hair card 表示法（CHARM 5 参数）

### 为什么换

旧的鲍伯壳是「一圈椭圆环按高度缩放」再放样：每一层截面都是椭圆，**结构上不可能
有分缕**；而且必须封顶，封顶就一定有瑕 —— 颅顶那个旋涡/肚脐，改到第 4 次
（抬收口半径、改平滑方式、合并顶环、加步数）仍然在，只是从一个坑变成另一个坑。

调研后发现二次元头发有公认表示法：**CHARM**（SIGGRAPH Asia 2025，清华）用
「控制点 + 宽 + 厚」5 参数描述一张发片，截面是菱形，变换完全可逆；
**HairDeck**（2026-10-29，Apache-2.0）实测平均每个发型约 70 张 card，
AnimeHair 数据集有 37K 个。按 CHARM 的公式实现，见 `lib/haircard.py`。

### 结构

```
_cap()          发帽      —— 头皮底色，盖住顶部
_bob_shell()    壳        —— 提供体积与轮廓
_cards_bob()    18 张卡片 —— 贴在壳外的表面分缕
_cards_fringe() 7 张卡片  —— 刘海
```

壳负责「看起来有体积」，卡片只负责「表面有一绺一绺」。只要卡片、不要壳，
两侧和后面会是空心薄片阵列，读成贴纸或湿发（实测 v2/v3）。

`hair.style` 新增第三个取值 `cards`（`bob` / `long` 保留不动）。
`params/profile.json` 的默认值改为 `cards`。

### 三个把卡片「变没」的 bug（都靠图才发现）

| 症状 | 根因 |
|---|---|
| 卡片整圈被埋，只有头顶露一点（花冠） | 卡片半径只跟 `_BOB_ROWS` 表值，而壳里是 `max(表值×_RX_K, 头骨+_HAIR_T)` —— 中下段壳被头骨撑大，卡片反而更小 |
| 同上，且卡片退化成等半径竖柱 | `_bob_dense()` 返回**升序**（-0.09 → 0.907），`at()` 的插值按降序写，每个 t 都命中第一个分支、全返回最低处半径 |
| 抬高卡片后仍被埋 | 壳有 `Solidify(thickness=0.0045, offset=-1)`，卡片外表面要超过「壳基准面 + 4.5mm」才看得见 |

### 判据

| 项 | 结果 |
|---|---|
| `measure.py` | **13 PASS / 0 FAIL / 1 WARN**（WARN = 发顶高出头骨 14.0mm） |
| `check.py` | **PASS 71 / FAIL 1 / SKIP 125 / CRASH 0**（唯一 FAIL 是既有的 R4 屈指 min=0.582） |
| `m7_aux` 七机位 | 0 failed |
| `audit.py --fast` | PASS 45 / WARN 8 / FAIL 3（面数、Head 非流形为既有；「产物新鲜度」是改了 blend 没重跑 asset，属预期） |

两处口径随之更新，理由都写在文件里：

1. **`hair_cap_gap` 目标 17mm → 48±14mm**。这条量的是「上 1/3 高度里 Hair 与 Head
   的前后跨度差」，Hair 现在含卡片（壳外 5.5mm + 半厚 1.8mm），实测 20.2 → 44.9mm。
   44.9mm 不是缺陷：鲍伯头头发深度 ≈ 头高的 0.97。旧 target 是「单层发帽」的口径。
2. **`d_probe.py` 的 D1/D2 五条在 `cards` 下同样 SKIP**（`bob` 与 `cards` 都没有
   long 专用的后发束与 3 组刘海）。

### 已知遗留（都在图上看得到）

| 位置 | 现象 |
|---|---|
| 整个头发 | 分缕的沟偏深偏规则，读成「南瓜瓣/大蒜」，参考图是几道浅沟 |
| 正面刘海 | 7 绺竖条末端平齐，像梳齿；参考图的刘海有长短参差与内扣 |
| 侧面 | 中下段有一处凸起/撕裂（壳与卡片的交叠） |
| 顶视 | 发帽圆盘与周围卡片之间有一圈台阶，圆盘中心仍有小凹 |

这些都是「调参 + 局部几何」级别的问题，不再是范式问题。

## 2026-11-03 / v0.6.0 — 全向补视角（m7_aux.py）：补掉仰角盲区

起因是一句追问：「你有几个机位来确认建模？」把 27 个命名机位逐个抽出 `loc`/`zc`
算出方位角与仰角之后，答案很难看：

| 体系 | 机位数 | 方位角 | 仰角 |
|---|---|---|---|
| `lib/shots.py` 命名机位 | 27 | 只有 0° / 31.4° / 42.6° / 90° / 180° 五档 | **全部 +0°~+4°** |
| `m6_multiview.py` 环绕 | 16 | 22.5° 全覆盖 | +2° |
| `Blender体检` 环绕 + 顶视 | 17 | 22.5° 全覆盖 | **+20° 俯视 / +90° 正顶**（但 `out/` 是空的，**从未在人物上真跑过**） |

也就是说：**下半球和正顶从来没有被渲染过**。下颌底面、腋下、袖口内壁、颅顶收口
这些位置出问题，四个判据入口一个都看不见。另外 27 个机位的 x 全是正数，
高清侧脸只有**右脸**。

### 补了哪 7 台

按正交补全定数量，不按「哪有缺陷」定 —— 缺陷会变，判据得稳定。
±x / ±y / +z 每个方向至少一台，另加斜上、斜下各一台：

| 机位 | 方向 | 查什么 |
|---|---|---|
| `aux_face_top` | +z 正顶 | 颅顶收口、左右对称 |
| `aux_face_top_q34` | 斜上 48° | 颅顶小尖、发帽与外壳交界 |
| `aux_face_low_front` | 仰视 30° | 下颌底、下巴-颈交界、鼻底 |
| `aux_face_low_q34` | 仰视 28° 3/4 | 下颌底 + 颊下沿 |
| `aux_face_side_l` | −x 左 | 左脸（此前只有右脸有 0.52mm/px 精度） |
| `aux_upper_low` | 仰视 31° 上半身 | 腋下、袖口内壁、锁骨下 |
| `aux_body_back` | +y 正后全身 | 腰背、腿后侧、后颈 |

`−z` 正下方没做：站姿的人物从正下看只有脚底，没有信息量，用仰视两台代表下半球。

### 两个必须记的实现细节

1. **照明必须统一，否则图不能互比**。场景三点光固定在世界坐标（key 在左前），
   从 −x 看就是纯背光：实测 `p50=0.570`，而正前是 `0.876` —— 同一个发色差 0.3，
   肉眼是两种颜色，判不了对称。改成每台相机挂一盏**同功率相机灯**
   （14W / size 3.0），`p50` 收到 0.651~0.864，`dark` 全 0.0000。
2. **`--nool` 不能按材质名 hide 对象**。描边不是独立物体，而是每个网格上挂的
   `Solidify` 修改器（名字 `Outline`，`offset=+1`，靠 `material_offset` 指向
   `outline` 材质槽）。按「材质名含 outline」去 `hide_render` 会把整个人藏掉
   —— 首次实测七张全空、`cov=0.0000`。正确做法是关掉该修改器的 `show_render`。
   `--nool` 的产物带 `_nool` 后缀，两种模式共存，便于并排判「是描边还是几何」。

### 一跑就暴露的三个问题（都不是机位问题）

| 位置 | 现象 | 归因（用 `--nool` 对比确认） |
|---|---|---|
| 左侧头顶 | 一条横贯的水平黑线 | **描边壳**：发帽与鲍伯壳交界处的开放边被勾出来，关描边即消失 |
| 头顶 / 斜顶 | 纵向折痕 + Y 形褶皱 | **真几何**：发帽球冠收口不规则，关描边后更清楚 |
| 侧脸 | 一道"抓痕"状浅凹 | **真几何**（浅） |
| 仰视全角度 | 下颌几乎没有立体结构 | **真几何**：平视时靠脸颊收窄"装"出的尖下巴，一仰视就露馅 |

第 4 条是平视机位在原理上永远查不到的，也是这轮加机位最直接的收益。

### 接口

```
python 人物建模/scripts/build.py aux           # 7 机位 → out/m7_aux_*.png + sheet + stats
python 人物建模/scripts/build.py aux --nool    # 关描边看裸几何
```

`build.py` 的 `run_script` 增加了 `extra` 参数用于透传 `--` 之后的参数（18.9s / exit 0）。
产物清单：7 张单图 + `m7_aux_sheet.png`（4×2 拼版）+ `m7_aux_stats.json`（与 m6 同口径的
`cov`/`dark`/`black`/`p50`，便于以后并入交付闸门）。

断言语义只判「相机没拍空」`cov>0.02` 与「没有大面积纯黑」`black<=0.45`。
没有沿用 m6 的 `dark<=0.12`：顶视与仰视本来就会拍到背光面，用那个阈值会全红，
红色警报不区分「真破面」和「这一面本来就暗」。

## 2026-11-03 / v0.5.1 — 交付闸门（scripts/deliver.py）

到 v0.5.0，项目里有**四个**判据入口、四份产物，但没有一个回答「**现在能不能交付**」：

| 入口 | 产物 | 判什么 |
|---|---|---|
| `build.py measure` | `out/appearance_report.json` | 像不像参考图 |
| `build.py asset` | `out/m6_16_stats.json` | 16 机位渲染有没有硬伤 |
| `scripts/audit.py` | `out/audit.json` | 能不能进引擎 |
| `build.py check` | `opt/logs/check_report.md` | 绑定有没有坏 |

新增 `scripts/deliver.py` + `spec/deliver.json`。BOSS 2026-11-03 定：**进游戏和进作品集两个都要**，所以闸门给两个结论而不是一个。

- **不重新测量**：只读已有产物、判新鲜度、套已知例外、给结论。跑一次毫秒级；产物过期就说「重跑哪条命令」，`--run` 直接补跑（按 `sources` 数组顺序，`views` 排在 `asset` 前，因为它的 producer 会重出 glb）。
- **新鲜度判定**：产物 mtime 必须不早于 `美女.blend`。改完模型不重跑 → 直接 STALE，不给「拿旧数据报捷」的机会。
- **已知例外显式化**：`rig` 的 `R4 finger_bend`（屈指最小边比 0.582 < 0.6）写在 `spec/deliver.json` 里，带理由和待办。豁免必须留证据，不能在代码里硬编码忽略。

首次结论（2026-11-03 20:55）：

| 目标 | 结论 | 卡在哪 |
|---|---|---|
| 进游戏 | **还不行** | 总三角面 201,830（预算 60,000）、Head 非流形边 628 |
| 进作品集 | **可以交付** | 外观 13 PASS / 1 WARN、16 机位最大覆盖率差 0.0222（阈 0.03）、绑定回归经豁免后全过 |

踩坑一条：状态最初在套例外**之前**算，结果 FAIL 被摘掉了、`ok` 还留在 False，界面同时显示「PASS 71 / FAIL 1」和红色。改成豁免后再统一重算状态（`blocking - excused <= 0 and extra == 0`）。

## 2026-11-03 / v0.5.0 — 游戏可用性审计（scripts/audit.py）

目标从这一版起明确为「**真进游戏用**」，原来三个判据入口各管一段，没有任何一个回答「能不能塞进引擎」：

| 入口 | 判什么 | 不管什么 |
|---|---|---|
| `measure.py` | 像不像参考图（14 项外观） | 面数、UV、拓扑 |
| `check.py` | 绑定有没有坏（六探针） | 资产预算 |
| `m6_export.py` | 导出这一步有没有崩（自带断言） | 只在导出时跑，平时看不见 |

新增 `scripts/audit.py` + `spec/game_budget.json`：一次跑完 **56 项**，给 PASS/WARN/FAIL 与退出码。

- **双模式单文件**：外层系统 Python 解 glb（不启动 Blender，`--fast` 亚秒级），带 `--blender-side` 时在 Blender 里量结构。避免「探针与外层判据不同步」。
- **阈值全在 `spec/game_budget.json`**，脚本不写死数字；每项带 `why` 说明为什么卡这个数。
- **判据两处按事实修正**（不是放宽）：
  - 「四边面百分比 ≥90%」降为 warn。`Head` 实测 89.2%，差的那部分是**五官扇形贴片**，结构上合并不了；拿百分比当硬判据会天天报假警。
  - 改成 **「可合并三角面 = 0」** 做硬判据：在网格**副本**上真跑 `tris_convert_to_quads`，数实际能合并掉多少，原网格不动。实测五个网格全是 0，与 `m6_asset.py` 的 E2 结论一致。
  - 「每顶点最多 4 骨」降为 warn：glTF 导出器会按权重截断并重新归一化，资产不会崩，但与 DCC 预览会有形变差。真硬判据改成**在 glb 里验 `WEIGHTS_0` 之和**（引擎真正拿到的那份）。
- **新增「产物新鲜度」检查**：`美女.blend → 美女_asset.blend → out/美女.glb` 时间戳必须递进。拿 6 小时前的旧 glb 判「能进游戏」比不判更糟。

首次审计结论（2026-11-03，重跑 M6 资产链后的新鲜产物，共 56 项）：

- **FAIL 2**：
  - 总三角面 **201,830**（预算 60,000，超 3.4 倍）
  - Head **非流形边 628 条**（预算 0）
- **WARN 8**：5 个网格单项面数全超预算（躯干 146,044 占 **72.4%**、服装 18,828、头发 17,560、手 11,072、头 8,326）；Body/Hands 每顶点 **5 根**骨影响；Head 四边面 88.2%
- **PASS 46**：5 网格 × 5 组顶点属性齐全、45 骨 / 1 skin、5 材质 5 贴图、8.2 MB、UV 全有、**glb 权重和 0 偏离**、产物时间戳递进

结论直白：**技术链路是通的，卡在面数**。躯干一项就吃掉 72%，是唯一值得先动的地方；Head 那 628 条非流形边是第二优先。

第一次跑时审计对象搞错了两次，记下来免得有人重犯：

1. 默认拿 `美女.blend`（工作文件）去查 UV → 四个网格全 FAIL。UV 是 `m6_asset.py` 阶段才展开的，结构审计必须看 `美女_asset.blend`。
2. 「可合并三角面」最初用几何近似（相邻 + 法线夹角 ≤40°），报出 Head 520 / Hair 626 / Outfit 320，与 `m6_asset.py` 的「实测 0 合并」矛盾。原因：算子还看四边形形状与 UV/锐边/材质边界。改成**在副本上真跑一次算子**，结果归零 —— 判据必须和工程实际用的算子一致，近似比不查更糟。

审计没覆盖的项（UV 重叠面积、贴图色彩空间、LOD、引擎内实渲染）写在报告的最后一节，避免「全绿＝能上线」的误读。

## 2026-11-03 / v0.4.1 — 仓独立化：路径可配置（默认值不变）

`stardust/`、`blender-rig/` 原来把本机绝对路径写死在代码里，clone 到别处就跑不了，与「独立项目」的定位矛盾。改法保持**默认行为逐字符不变**，只增加覆盖能力：

- `blender-rig/`（4 脚本）：`OUT` / `IMG` 改由 `__file__` 推导（原本写死 `D:\G\github\实用工具\Blender建模\blender-rig\...`），与 README 已声明的「输出路径由 `__file__` 推导」一致。
- `stardust/`（5 脚本）：游戏工程根改为 `os.environ.get("STARDUST_DIR", <原路径>)`；`blender-rig/rig_buildings.py` 同理用 `REROUTE_GAME_DIR`。不设变量时解析结果与原硬编码路径**逐字符相同**，游戏仓 `AGENTS.md` 的调用契约不受影响。
- 文档：仓根 README 跨仓契约段从「绝对路径是刻意设计，不要顺手规范化」改为「默认值是本机路径、可被环境变量覆盖」；`docs/工程梳理与维护指南.md` 第 63 条同步。

验证：9 个脚本 `py_compile` 全过；用 AST 求值（真实执行 `os.environ.get` + `os.path.join`）逐条比对，默认值下 9 条路径与原值完全一致；设 `STARDUST_DIR=E:/other/stardust` 后派生路径整体跟随。

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