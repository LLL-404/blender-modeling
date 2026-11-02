# 变更记录

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