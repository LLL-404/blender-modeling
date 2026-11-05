# SDF 融合体调研（2026-11-05，只看，未动建模代码）

> 状态：**调研完成，未实现、未进主链**。对应 BOSS 的「应该是 SDF，你全完事以后可以看看」。
> 证据脚本 `scripts/probe_sdf_nodes.py`（只读，列出本机 Blender 的原生 SDF 节点）。

---

## 0. 结论先行

| # | 结论 |
|---|---|
| 1 | **能做，而且本机免费就能跑。** Blender 5.2.2 LTS 自带 SDF 几何节点，实测 8 个节点可创建，不用装任何库 |
| 2 | 我上一轮说「要装库、整套拓扑/UV/绑定重做」**过时了**：Blender 5.0 起原生支持，成本降到「局部烘焙 + 重传属性」 |
| 3 | 值得做**局部试点**（耳根/手指接缝），**不值得现在替换整条主链** |
| 4 | SDF 修的是「接缝与穿插」，**修不了「丑」**（五官比例、发丝、贴图、配色一条都不碰） |
| 5 | 本机 `SDFGridBoolean` 只有硬 UNION，**没有 smooth-union 选项**；圆滑过渡要走 Fillet 或「膨胀→并集→收缩」 |

---

## 1. 大白话：SDF 是什么

| | 现在的网格 | SDF（有向距离场） |
|---|---|---|
| 记什么 | 一堆顶点的坐标 + 三角形怎么连 | 空间里每个点「离表面多远」：内部为负、外部为正、表面正好是 0 |
| 两个东西合体 | 布尔运算，接缝是硬折角，容易破面 | 两个距离场取 `min` 就是硬并集；换成 `smin` 会让接缝像橡皮泥融在一起 |
| 变回网格 | — | 找 `距离=0` 的那一层（marching cubes），出来一张封闭三角网 |

`k` 是融合带宽度，单位是米；`k` 越大越圆，但形状最多会整体鼓出 `k`。这条是硬约束，选 `k` 时得留量。

```
硬并集   union(a,b) = min(a,b)                          接缝是折角
平滑并集 smin(a,b,k) = min(a,b) - h²·k·0.25            h = max(k-|a-b|,0)/k
等价形式 h = clamp(0.5 + 0.5*(b-a)/k, 0, 1)
         mix(b,a,h) - k·h·(1-h)
```

参考：Inigo Quilez《smooth minimum》（2013，公式与归一化），公开可用。

---

## 2. 本机实测（不是查文档，是跑出来的）

`scripts/probe_sdf_nodes.py` 在 Blender 5.2.2 LTS 下实测，RNA 里 SDF 相关类 10 个，可 `nodes.new()` 的：

| 节点 | 输入 | 用途 |
|---|---|---|
| `GeometryNodeMeshToSDFGrid` | Mesh / Voxel Size(默认 0.3) / Band Width(默认 3) | 网格 → 距离场 |
| `GeometryNodeSDFGridBoolean` | Grid 1 / Grid 2；`operation` = **INTERSECT / UNION / DIFFERENCE** | 硬并集、交、差 —— **没有 SMOOTH** |
| `GeometryNodeSDFGridFillet` | Grid / Iterations | 交线倒圆角 |
| `GeometryNodeSDFGridOffset` | Grid / Distance | 整体膨胀(负)/收缩(正) |
| `GeometryNodeSDFGridMean` | Grid / Width / Iterations | 盒式平滑 |
| `GeometryNodeSDFGridLaplacian` | Grid / Iterations | 拉普拉斯平滑 |
| `GeometryNodeGridToMesh` | Grid / Threshold / Adaptivity | 距离场 → 网格 |
| `GeometryNodeMeshToVolume`、`GeometryNodeVolumeToMesh` | 老的体积路径 | 密度体素，不是 SDF |

**关键限制**：没有原生 `smin` 节点。三条替代路：

| 路 | 做法 | 代价 |
|---|---|---|
| **A 原生 Fillet（推荐先试）** | 两个 grid → UNION → `SDFGridFillet`(Iterations 2~4) → `GridToMesh` | 零依赖、全原生；是「交线倒圆角」，不是严格 smin |
| B 膨胀-并集-收缩 | 两 grid 各 `Offset(−k)` → UNION → `Offset(+k)` | 近似 smin，全原生；体积会轻微变化，`k` 要标定 |
| C 自己算 smin | Python/numpy 采两 grid 值算 `smin` 再写回 | 严格 smin；Blender 的 grid Python API 暴露有限，可能要转 OpenVDB 或用外部库 |

---

## 3. 免费吗 / 许可证

| 方案 | 许可 | 本机状态 |
|---|---|---|
| Blender 原生 SDF 节点 | Blender 本体 GPL；**用它生成的模型不继承 GPL** | **已装，5.2.2 LTS**，直接可用 |
| `fogleman/sdf`（Python + marching cubes） | MIT，约 2k star | 未装，依赖 `scikit-image`/`meshio`（本机缺） |
| `mesh-to-sdf`（任意网格→SDF） | MIT | 未装，依赖 `trimesh`（本机缺） |
| `scikit-image` 的 marching cubes | BSD-3 | 未装，pip 可装 |
| SDFusion 插件（Superhive） | **付费** | 不需要，原生节点够 |
| 本机已有 | `numpy` / `scipy` / `cv2` / `torch` 有；`skimage` / `trimesh` / `openvdb` / `pyvista` 无 | 路 A/B 不需要它们 |

**结论：路 A/B 完全免费、零安装。**

---

## 4. 与当前表示法的冲突（最重要的一节）

| 现在 | SDF 输出后 | 项目里谁能补 |
|---|---|---|
| 13 环 × 24 段控制笼 + Catmull-Clark | marching cubes 全三角，**参数化没了** | 补不回来。改不了「颧骨 +2.2mm」这种旋钮 |
| 四边拓扑、UV | 全没了 | `lib/asset.py:quads_converge()`、`lib/uvkit.py` 重跑 |
| 顶点组 / 骨骼权重 | 全没了 | `lib/hand.py:233` 有「按空间重建权重」的现成做法 |
| 描边靠 `material_offset` 按材质分层 | 融合区材质边界消失 | `lib/look.py:add_outline_layers()` 要重排 |
| 眼睑厚 **1.2mm** | ≥2mm 体素直接抹平 | 融合区不能碰眼睛 |
| phase 3 的共享曲面 `S(x,z)` 上取深度 | 曲面定义没了，眼/虹膜/睫毛要重贴 | 整个 phase 3 重做 |

一句话：**SDF 的产物是「烘焙好的网格」，不是「可编辑的参数模型」。**
本项目要的是「AI 改参数就能改模型」，两者哲学相反。所以 SDF 只能是
**局部后处理**，不能当主表示法。这一点不会因为原生节点便宜而改变。

---

## 5. 体素成本估算（决定「局部还是整头」）

| 范围 | bbox | 0.5mm 体素 | float32 density 内存 |
|---|---|---|---|
| 整头 | 0.22 × 0.20 × 0.26 m | 440 × 400 × 520 ≈ **9150 万** | ≈ 366 MB |
| 耳根局部 ROI | 0.06 × 0.04 × 0.06 m | 120 × 80 × 120 ≈ **115 万** | ≈ 4.6 MB |
| 手指+掌局部 | 0.06 × 0.05 × 0.12 m | 120 × 100 × 240 ≈ **288 万** | ≈ 11.5 MB |

整头不仅贵，还会把控制笼、UV、权重、描边一次性全毁掉 → **不做**。
局部 ROI 是唯一合理形态。

---

## 6. 最小可行验证（不进主链）

**试点：左耳 + 头骨的接缝。**

| 理由 | 说明 |
|---|---|
| 独立网格 | `headmod.ear(-1, M)` 是一个独立椭球，硬贴在头骨上，接缝真实存在 |
| 不碰敏感区 | 耳与头骨都是 `skin` 材质，不涉及眼睛、发片、描边分层 |
| ROI 小 | 0.5mm 体素只要 4.6 MB |
| 有现成量尺 | `head_baseline.py` 的 `ear_height_mm` / `ear_symmetry_mm` / `head_width` |
| 有现成证据 | `scripts/render_clay.py` 的 `clay_face_side.png` 白模侧视 |

MUST 按顺序：

| 步 | 动作 |
|---|---|
| 1 | 只取 `head_base()+sculpt()` 与 `ear(-1, M)`，裁到耳周 ROI；**不加载眼睛/头发/服装** |
| 2 | 各跑 `MeshToSDFGrid`（Voxel Size `0.0005`、Band Width 3） |
| 3 | 路 A：UNION → `SDFGridFillet`(Iterations 2~4) → `GridToMesh`(Threshold 0, Adaptivity 0) |
| 4 | 出 `out/sdf_probe.json` + 白模对比图 |

判据（不过就停，不在主链上试第三个变体）：

| 项 | 要求 |
|---|---|
| 拓扑 | 非流形边 = 0、无自交（bmesh 统计） |
| 尺寸 | `ear_height_mm` 45.819 ±0.5；`head_width` 变化 <0.5mm |
| 法线 | 耳根接缝处相邻面法线突变 <15° |
| 人眼 | 白模侧视看不到耳根的硬接缝 |
| 成本 | 耗时 / 峰值内存写进报告 |

NEVER：

- 不要把眼睛、发片、描边壳放进融合区
- 不要整头融合
- 不要把 SDF 输出直接接 `m5_rig`（权重全丢）
- 不要因为「白模接缝没了」就说「模型好看了」—— 那两件事无关

---

## 7. 与现有 `voxel_remesh` 的关系

`meshkit.voxel_remesh()` 已经在做「硬体素重网格」（身体 5mm、手 2mm）：
把穿插部件合成一个封闭体，但**没有 smooth-union 的圆滑过渡**，而且是整网格重建，
UV/权重必须重传（`lib/hand.py:233` 明确写了）。

SDF 多给的两样东西：`k` 可控的过渡、只在局部 ROI 做、不必重建整张网格。
**A/B 对照建议**：同一只手，`voxel_remesh` vs SDF Fillet，比白模接缝与
`head_baseline` 量尺，再决定要不要换。

---

## 8. 什么时候才值得进主链

四条**全部满足**才做，现在一条都不满足：

| # | 条件 | 现在 |
|---|---|---|
| 1 | `flow` 至少 body/face 过闸 | **0/6 过闸**（body 手、face 三渲二卡住） |
| 2 | body 的手靠现有 `voxel_remesh` 修不好 | 还没试过修，缺陷仍是「只有 4 根分开手指、拇指未分离、腕部断口」 |
| 3 | 试点证明 UV / 权重 / 描边能无损重传 | 未验证 |
| 4 | 接缝在白模里可见，且真的挡交付 | 未验证 |

所以本轮：**只看，不动代码。**

---

## 9. 复现

```bash
"D:/Program Files/Blender Foundation/Blender 5.2/blender.exe" \
    -b --factory-startup --python-exit-code 1 --python scripts/probe_sdf_nodes.py
```

输出里 `GeometryNodeSDFGridBoolean` 的 `operation` 只有
`INTERSECT / UNION / DIFFERENCE` —— 这就是「没有原生 smooth-union」的实测依据。
