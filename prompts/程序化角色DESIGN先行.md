# 提示词模板：程序化二次元角色（DESIGN 先行）

> 来源：`skills/blender-procedural-character/SKILL.md`。**规范口径以来源为准**，本文件是可直接粘贴的会话模板；改口径先改来源，再同步本模板。

---

为 `<角色名>` 程序化生成二次元人物（headless Blender 5.2 + bpy，参照 `人物建模/` 现有工程形态）：

0. **概念图先行（2026-11-05 起为第 0 步）**：动手前先落一张 **3D 可实现的三视图概念图**（正面/45°/背面并排 + A-pose + 纯白背景 + 平光，赛璐璐平涂），存 `人物建模/spec/reference/`，作为**验收的唯一视觉基准**——宏观文字描述（"银发少女"）不能当靶子（Goodhart 陷阱教训，见 `docs/工程梳理与维护指南.md`）。随后才出 DESIGN.md：角色设定基准（比例表：头身比/各部件尺寸 mm + 配色规范 hex）+ 技术方案（模块职责与参数化硬约束）+ A/B/C/D 分阶段量化验收表 + 验收方法论与口径陷阱。概念图与 DESIGN.md 经确认后才进入建模；视觉门基线必须由概念图自身 `--calibrate` 算出，禁止照模型数值反调。
1. **阶段顺序固定**：几何（A）→ 骨架（B）→ 材质（C）→ 细节（D），**不可先做质感**。
2. **每阶段跑验收探针**（`skills/blender-procedural-character/scripts/geometry_probe.py`、`pixel_probe.py`），量化判据不过即修；分辨率不足时如实报「不可分辨」，禁止硬凑达标。
3. **已知坑直接查 SKILL.md 与 references/**：Image.pixels 的 sRGB 与 bottom-up、正交 ROI 须机位水平、Solidify 壳厚按对象 cap、参数搜索 Halton+坐标下降、三类「假达标」识别、收口/接管先跑探针拿基线。
4. **收口/接管半成品**：先跑探针拿基线再补缺失项；终局重建先核对材质/灯光/描边三件套。
5. **产物纪律**：工程与代码在 `人物建模/`（入库），`out/`、`*.blend` 不入库；定稿后 `python 人物建模/scripts/build.py archive` 出时间戳归档副本（落散件归档）。
