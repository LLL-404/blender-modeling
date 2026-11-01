# 参数自动搜索器 · 几何段报告

任务：把「裙腰净空」与「手指蒙皮平滑」两处人肉试参改成可复现的自动搜索，
产物 `opt/best.json` 由搜索器写出，各模块带默认值回退读取，随时可回滚。

* 搜索器入口：`opt/search.py`
* 单次评估：`opt/eval_geom.py`（Blender 进程内，3~5s/次）
* 参数空间：`opt/space_geom.py`，采样：`opt/halton.py`
* 注入层：`lib/optio.py`（`optio.param(key, default)`）
* 搜索日志：`opt/trials.jsonl`（96 行评估 + 2 行 run 标记）

---

## 1. 算法（一句话）

**Halton 低差异采样 32 点 → 按 score 排序取 top-4 → 每个 top 点做 2 轮逐维 ±1 step
的坐标下降 → 输出全局最优。**

1. `halton_seq(32, 5, seed=20261101)` 铺满参数盒（每维都分层；实测 32 点 32 个唯一值，
   每维的取值分布见 §3）；`rng = default_rng(20261101)` **只**用来打乱「维度→底数」
   的顺序和一个跳跃起点，数值本身完全由 Halton 决定性给出，所以 best.json 只记 seed 即可复现。
2. 按 `score = 1e6·硬违规数 + 软代价` 升序排序，取前 4（`--topk`）。
3. 对每个 top 点：逐维试 `±1 个 step`（越界则夹紧；夹紧后等于原值就不试），
   两向取更优、有改善就接受；共 2 轮（`--rounds`）。
4. 全过程中做过评估的参数点按 `JSON` 键去重缓存，重复点不重算。

**为什么不用贝叶斯优化 / CMA-ES**：进程内只有 numpy，**没有 scipy**
（没有 `scipy.optimize` / `scipy.stats`，GP 代理模型要自己手写协方差与 Cholesky）；
维度只有 5（4 数值 + 1 类别）；一次评估 3~5s，总预算百次以内。在这个预算下
代理模型拟合不出可信曲面，收益不如「把 32 个点铺匀 + 局部下坡」来得确定；
而且坐标下降天然产出「每维 ±1 step 是否改善」的敏感性数据，报告里能直接引用。

## 2. 目标函数（按任务书实现，另加 1 条回归护栏）

`score = 1e6 × hard_violations + soft_cost`

**硬约束（每不满足一条 +1，乘 1e6，搜索绝不会选）**

| 判据 | 阈值 | 来源 |
|---|---|---|
| 裙腰四段 net 全部 ≥ +2mm | `0.002 m` | 任务书 / `outfit.assert_skirt_clearance` |
| 权重和 bad == 0 | `|Σw−1|≤0.02` 计数为 0 | `b_probe` weightsum |
| 腕部径向台阶（宽 y / 厚 x 两向，取左右最大值） | ≤ 3mm | `a1_hand_probe` wrist step |
| 裙摆 z<1.04 手臂骨主导比例 | ≤ 5% | `b_probe` B1 |
| `cross_side_leak`（Body，对侧骨权重和>0.10 的顶点占比） | ≤ 0.2% | `b_probe` B2 |
| **（新增）walk 姿势腿/臀顶点越出裙面** | **≤5 个且 ≤2mm** | **`b_probe` R2 leak（B 阶段已达标判据）** |

> 为什么加第 6 条：第一版严格按任务书 5 条跑出来的最优解（peak 口径 + margin 5mm）
> 把裙腰收紧后，b_probe 实测 `R2 leak walk: n=2 worst=4.11mm`（原来 0/0）——
> 即「为了揉好手指而把已达标的穿模判据弄坏了」。任务验收明确要求「已达标项无退化」，
> 所以把它提升为硬约束重跑了全量搜索（两轮搜索的 trials 分别在
> `opt/logs/trials_rerun2_noleakguard.jsonl` 与本轮 `opt/trials.jsonl`）。
> 其余 5 条的公式与阈值一个没动。

**软目标（越小越好）**

| 项 | 公式 | 说明 |
|---|---|---|
| 裙腰过松 | `Σ max(0, net_i − 0.008)`（**米**） | 超 8mm 起罚，防麻袋 |
| 屈指 min 边长比 | `max(0, 0.6 − min)^2 × 4000` | 主攻目标 |
| 屈指 p95 | `max(0, p95 − 1.5)^2 × 400` | |
| 屈指 max | `max(0, max − 2.5)^2 × 400` | |

> 口径提醒：裙腰过松项用**米**（任务书原文），所以量级只有 0.016 分，而屈指 min 项
> 在 baseline 就占 20.24 分 —— 裙腰两个维度在 score 里几乎「不敏感」（见 §4）。
> 这不是 bug，是按指定公式实现的直接后果；如果希望裙腰也参与竞争，需要把该项改成
> 以 mm 计或放大权重，那是**下一个任务**该拍板的事，本轮没有擅自改口径。

## 3. 搜索空间（默认值全部从现网代码读，注释里带 `文件:行`）

| 维度 | 范围 | 步长 | 默认值 | 默认值来源 |
|---|---|---|---|---|
| `skirt_margin` | 0.002 ~ 0.010 m | 0.001 | **0.0030** | `lib/outfit.py:262` `SKIRT_WAIST_MARGIN = 0.0030` |
| `skirt_inner_mode` | `valley` / `peak` | 类别 | **valley** | `lib/outfit.py:320` `inner = margin + amps[i]`（谷+margin，即现网行为） |
| `finger_blend_p` | 2.0 ~ 6.0 | 0.5 | **3.5** | `lib/hand.py:210` `BLEND_P = 3.5`（原 `blend(..., p=3.5)`） |
| `finger_smooth_n` | 2 ~ 12 | 2 | **6** | `lib/hand.py:213` `SMOOTH_ITERS = 6`（原 `f, iters = 0.55, 6`） |
| `joint_blend_mm` | 1.0 ~ 4.0 mm | 0.5 | **1.5** | `lib/hand.py:211` `BLEND_EPS_MM = 1.5`（原 `blend()` 的 `eps=0.0015`） |

`optio.param()` 读取时**类型跟随 default**：int 维取整、类别维取字符串、其余 float。
`space_geom.verify_defaults()` 每次搜索/评估都会现场 import `outfit`/`hand` 把模块常量
和 DIMS 对一遍，5 项全部 `MATCH`（代码改了默认值而这里忘同步会立刻 MISMATCH 中止）。

**两处与任务示例的偏离，都写在这里**

1. `joint_blend_mm` 任务示例给 3.0~9.0 / 默认 5.0；现网实现里「关节混合带宽度」是
   反距离权重的 `eps=1.5mm`，默认点 1.5 落在示例区间外、连坐标下降都回不到默认值。
   按「默认值必须实测」的纪律，区间改为 **1.0~4.0**（含默认 1.5），语义不变：
   eps 越大，相邻两根骨的权重过渡越宽。
2. `skirt_inner_mode` 由任务要求新增（不是任务书 DIMS 示例里的 4 维之一），
   `valley` = 波谷也留够净空（`inner = margin + amp`，现网行为）；
   `peak` = 只保波峰（`inner = margin − 1.25·amp`，1.25 = 1 + 二次谐波系数 0.25）。

## 4. baseline vs best

baseline = `optio` 未注入时的现网手调默认值（`skirt_margin=0.003, valley, p=3.5,
smooth=6, joint_blend=1.5`）；best = `opt/best.json` 里的最优解
（**margin=0.008, peak, p=4.5, smooth=2, joint_blend=3.0**）。

| 指标 | 阈值 | baseline | best | 判定 |
|---|---|---|---|---|
| skirt net z[0.920,0.960] | ≥+2mm | +14.24mm | +14.24mm | PASS（未变） |
| skirt net z[0.960,1.000] | ≥+2mm | +14.70mm | +11.05mm | PASS（收窄 3.6mm） |
| skirt net z[1.000,1.040] | ≥+2mm | +7.73mm | +6.65mm | PASS（收窄 1.1mm） |
| skirt net z[1.040,1.060] | ≥+2mm | +14.15mm | +14.73mm | PASS（未变） |
| 裙腰过松 Σmax(0,net−8mm) | 越小越好 | 19.09mm | **16.02mm** | 略好 |
| 屈指 min 边长比 | ≥0.6 | 0.5289 | **0.5817** | 改善 10%，**仍未达标** |
| 屈指 p95 | ≤1.5 | 1.1818 | 1.2081 | PASS（略差，仍在阈内） |
| 屈指 max | ≤2.5 | 2.3159 | **1.7877** | PASS（改善 23%） |
| 屈指 edges>1.5× | — | 35 条 | **21 条** | 改善 40% |
| 腕部台阶（厚 x / 宽 y） | ≤3mm | +1.755 / +0.00mm | +1.755 / +0.00mm | PASS（未变，几何量） |
| 权重和 bad（Body+Outfit+Hands） | =0 | 0 | 0 | PASS（未变） |
| 裙摆手臂骨主导比例 | ≤5% | 0.00% | 0.00% | PASS（未变） |
| cross_side_leak | ≤0.2% | 0.000% | 0.000% | PASS（未变） |
| walk 腿/臀越出裙面 | ≤5 个且 ≤2mm | 0 个 / 0.00mm | 1 个 / 1.45mm | PASS（余量消耗，仍在阈内） |
| **score** | 越小越好 | **20.2399** | **1.3556** | 降 93.3% |

`b_probe` 独立复测（不带 1mm 过滤，口径见 §6）与上表一致：
`R4 finger_bend 45/30: p95=1.181→1.207 max=2.316→1.788 min=0.529→0.582 edges>1.5x=37→21`；
`[fit] skirt` 四段 `+14.2/+14.7/+7.7/+14.2` → `+14.2/+11.1/+6.6/+14.7`。

## 5. 评价次数、耗时、每维敏感性

* **评价次数**：96 次唯一评估（含 baseline 与 5 次敏感性补充；总和上限估计 118，
  实际因去重缓存 + 夹紧跳过省掉 22 次）。0 次异常，14 次落在硬违规区（噪声点，被 score 淘汰）。
* **耗时**：单次中位数 **4.28s**、最慢 15.41s（个别 peak 小 margin 点），全程 **488s**（8 分 09 秒，
  含 Blender 启动）。`--n 4` 冒烟 15 次评估 52s。
* **每维敏感性**（把该维固定在默认值 vs 最优值，score 差；>0 表示最优值更好）：

| 维度 | 默认 | 最优 | 固定默认时的 score | Δscore |
|---|---|---|---|---|
| `finger_smooth_n` | 6 | 2 | 11.041 | **+9.685** |
| `finger_blend_p` | 3.5 | 4.5 | 6.740 | **+5.384** |
| `joint_blend_mm` | 1.5 | 3.0 | 5.581 | **+4.226** |
| `skirt_inner_mode` | valley | peak | 1.373 | +0.017 |
| `skirt_margin` | 0.003 | 0.008 | 2 000 001.35 | +2 000 000（**耦合**） |

`skirt_margin` 的 Δ 巨大不是「单独这一维多重要」，而是**两维耦合**：peak 口径下
`inner = margin − 1.25·amp`，把 margin 退回 0.003 会让 z[1.000,1.040] 的 net 与
walk 越出同时破线（hard=2）。也就是说 peak 口径必须配 ≥0.007 左右的 margin 才成立。

## 6. 未改善 / 未达标的项（如实写）

1. **屈指 min 边长比仍未达标**：0.5289 → 0.5817，目标是 ≥0.6。改善是实的（+10%，
   >1.5× 的边从 35 条降到 21 条，max 从 2.32 降到 1.79），但搜遍 5 维也没进 0.6。
   最差边位于掌根/近节交界（`palm.L` ↔ `index_proximal.L`，rest 长 1.53mm），
   属于「2mm 体素 remesh 的短边 + 两骨权重差」的结构性问题；本轮 5 个参数只调
   「混合锐度/带宽/平滑次数」，动不到那条边所在的硬边界，因此只能改善不能消除。
   要真正达标需要改 `assign_groups` 的算法本身（例如按骨段投影参数做 1D 混合，
   而不是三维反距离），那超出本任务的文件边界，留作下一项。
2. **屈指 p95 反而略升** 1.1818 → 1.2081（仍在 ≤1.5 阈内）。原因是 smooth_n 从 6 降到 2、
   带宽从 1.5mm 抬到 3.0mm：少平滑换来了更小的 max / 更小的压缩底，代价是 95 分位略抬。
   这是软目标之间的真实取舍，不是噪声。
3. **裙腰两维几乎不敏感**：`skirt_inner_mode` 只贡献 0.017 分、`skirt_margin` 只在
   peak 口径下被「够不够破线」约束。原因见 §2 的口径提醒（过松项以米计）。
   最优解从 valley+3mm 换成 peak+8mm，net 只是从 `14.2/14.7/7.7/14.2` 变成
   `14.2/11.1/6.6/14.7`，谈不上质变 —— **不要把它读成「裙腰被显著优化了」**。
4. **walk 越出从 0/0 变成 1 个 / 1.45mm**：b_probe 判据（≤5 个且 ≤2mm）仍是 PASS，
   但余量确实被消耗了。若要严格零越出，把 `opt/best.json` 的 `skirt_inner_mode`
   改回 `"valley"` 即可（敏感性实测该点 score 1.3726，比最优只差 0.017 分）。
5. **R3 交叉姿势 60/30 的 17 个法线翻转是既有缺陷**，注入前后逐字相同
   （`2.877/0/0` 与 `3.967/0/17`），与本轮参数无关（Body 权重公式未动）。
6. 采样器自身的一个真 bug（已修，记录在此）：第一版把「归一化坐标」直接喂给
   `snap()`（它期望实际值），32 个采样点被全部夹到参数盒右上角，搜索退化成一个角点。
   修法是把 `snap(实际值)` 与 `from_unit(归一化)` 拆开，`from_unit` 负责
   `lo + u·(hi−lo)`。坏的 trials 留在 `opt/logs/trials_rerun1_cornerbug.jsonl`。

## 7. 行为不变性（无 best.json 时逐位一致）与注入链路验证

* **改动前快照**：`opt/logs/premod_dprobe.txt` / `opt/logs/premod_bprobe.txt`（改 lib 之前采集）。
* **改完 lib、best.json 不存在时**：`opt/logs/before.txt`（d_probe）、`opt/logs/before_bprobe.txt`（b_probe）。
  * d_probe：22 行 **逐字相同**。
  * b_probe：97 行里所有数字 **逐行相同（0 处差异）**，仅多两条新增日志
    `[hint] hand weights… p=3.5 eps=1.5mm smooth_n=6` 与 `[fit] skirt_ring … inner=… mode=valley`
    （只加打印字段，不改几何/权重）。
* **注入链路真的生效**（不是只在搜索器的进程内 override 里成立）：
  `blender -b --factory-startup --python opt/eval_geom.py -- --use-best`
  复现出 best 的全部指标（`14.24/11.05/6.65/14.73`、`0.5817/1.2081/1.7877`、`score=1.3556`）；
  `b_probe` 在 best.json 存在时打到同一批数字（见 §4 独立复测一行）。
* 入口回归：`m5_outfit.py`、`m1_body.py` 均正常结束（`[done] M5 outfit` / 四张 png），
  `grep Traceback` 无输出。**未运行 `m5_rig.py`**（共享产物 `美女.blend` 不动）。
* `_stageD/d_probe.py` 注入前后输出 **完全一致** → D 阶段（刘海分组/发束/翻领/卷边/裙褶）无退化。

## 8. 回滚方法

任选其一，都不需要改任何调用点：

1. **删文件回滚（首选）**：删掉 `opt/best.json` → 所有 `optio.param()` 立刻回落到
   `lib/outfit.py` / `lib/hand.py` 里实测的模块常量，构建结果与手调版逐位一致（§7 已验证）。
   进程内已加载的模块需要重新跑一次 Blender（缓存只在首次读取时建立）。
2. **改字段回滚（单维）**：直接编辑 `opt/best.json` 的 `best_params`（例：把
   `skirt_inner_mode` 改回 `"valley"`，或删掉 `finger_smooth_n` 这一条）。缺失键按
   `optio.param(key, default)` 回落到 default。搜索器不会自动重写，改了就生效。
3. **代码回滚**：`git checkout lib/outfit.py lib/hand.py` 并删除 `lib/optio.py` 的
   两个 import（本工作区尚未初始化为 git 仓，回滚靠 `opt/logs/` 里的快照文本对照）。

`--use-best` 之外的所有评估路径都不会写 `opt/best.json`（搜索器只在跑完时写一次），
所以「误改」只可能来自手工编辑。

## 9. 复跑命令

```bash
cd 人物建模

# 冒烟（15 次评估、约 52s）
"D:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
    --python opt/search.py -- --n 4

# 全量（96 次唯一评估、约 8min）
"D:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
    --python opt/search.py -- --n 32 --topk 4 --rounds 2

# 单点评估（默认参数 / 指定参数 / 走 best.json）
blender -b --factory-startup --python opt/eval_geom.py
blender -b --factory-startup --python opt/eval_geom.py -- --params '{"finger_smooth_n":2}'
blender -b --factory-startup --python opt/eval_geom.py -- --use-best

# 独立复核
blender -b --factory-startup --python _stageB/b_probe.py 2>&1 | grep -E "^\[bprobe\]"
blender -b --factory-startup --python _stageD/d_probe.py 2>&1 | grep -E "^\[dprobe\]"
```

`--n / --topk / --rounds / --seed / --out` 均可覆盖；seed 固定时采样与下降路径完全可复现
（评估顺序里唯一的时间因素是 mesh 构建耗时，不影响数值）。

## 10. 产物清单

| 文件 | 说明 |
|---|---|
| `opt/halton.py` | Halton 序列（seed 只决定跳跃起点 + 维度乱序） |
| `opt/space_geom.py` | 5 维参数空间、默认值（带 `文件:行`）、`snap/from_unit/sample`、默认值自检 |
| `opt/eval_geom.py` | 单次评估：重建全场景 → 6 类指标 → score → 追加 `trials.jsonl`；`--use-best` 走注入链路 |
| `opt/search.py` | Halton → top-k → 坐标下降 → `best.json`（含敏感性） |
| `opt/best.json` | 搜索器写出：最优参数、best/baseline 指标与 score、每维敏感性、seed、耗时 |
| `opt/trials.jsonl` | 本轮 96 次评估逐行记录（params/metrics/hard/soft/score/t）+ run_start/run_end |
| `lib/optio.py` | 注入层（缺失/解析失败/缺键 → default；`set_overrides` 供搜索器进程内注入） |
| `lib/outfit.py` | `skirt_margin` / `skirt_inner_mode` 注入；新增 `LAST_SKIRT_NETS` 供评估取数；新增打印字段 |
| `lib/hand.py` | `BLEND_P` / `BLEND_EPS_MM` / `SMOOTH_FACTOR` / `SMOOTH_ITERS` 提为常量并注入；新增打印字段 |
| `opt/logs/` | 改动前快照、before/after 探针输出、坏采样的 trials 归档、搜索日志 |
---

# 参数自动搜索器 · 像素段报告（T20 收口）

几何段（T17）与像素段（T18/T20）**共用 `opt/best.json` 这一份文件、各写自己那一段**。
本文只写像素段；几何段的一切数字与结论见上文。

* 搜索器入口：`opt/search_pixel.py`
* 单次评估：`opt/eval_pixel.py`（Blender 进程内，**5 张渲染/次**：q34 + face_front +
  body_front + 同机位 rim 关灯版 face_front/body_front，实测 2.3~3.5s/次）
* 参数空间：`opt/space_pixel.py`（6 维：4 连续 + 1 连续 + 1 枚举）
* 注入层：`lib/optio.py`，查找顺序 **`pixel.best_params` → 顶层 `best_params` → default**
  （`lib/optio.py:100-121`，其中 `lib/optio.py:106` 是 pixel 优先那一行）
* 搜索日志：`opt/trials_pixel.jsonl`（每轮 run_start/run_end + 逐次评估）

## 1. 算法与预算

**baseline → Halton 采样 16 点 → `rim_azimuth` 在默认点上 4 方位全枚举 → 按 score 排序取
top-1 → 连续维逐维 ±1 step 坐标下降 → 全局最优（score 打平时取 rim 亮带更宽者）。**

与几何段的三处差异：

1. **枚举维只全枚举，不参与 ±1**（任务书要求）。`rim_azimuth` 从 `DIM_ORDER` 里拿掉
   （`opt/search_pixel.py:77`），改在 Halton 之后对 `space_pixel.defaults()` 做 4 方位全枚举
   （`opt/search_pixel.py:294-301`）。**这一改动不是形式上的**：见 §7.3，最优解正是在这一步
   被发现的（默认方位 `back_left` → `back_right`）。
2. **预算硬上限 24 次**。每次评估前查预算，超了就停，没试到的维度写进 `skipped_dims`。
3. **score 打平要 tie-break**（`opt/search_pixel.py:249-274` 的 `offer()`）：score 相同
   （Δ≤1e-9）时取 `rim_band_px` 更大者。实测 `back_right` 与 `back_left` 的 score
   **完全相同（都 4e-06）**，严格 `<` 会永远停在 baseline，把零代价的轮廓光改进丢掉。

| 轮次 | 实际评估次数（按 `trials_pixel.jsonl` 统计） | 单次耗时 | 墙钟 |
|---|---|---|---|
| 冒烟 `--n 2` | 16（1 baseline + 2 halton + 13 邻域） | 1.7~2.4s | **29.8s** |
| 全量 `--n 16`（正式，`opt/logs/px_full3.log`） | **24**（1 baseline + 16 halton + 3 枚举新增 + 4 邻域） | 2.3~3.5s | **71.5s** |

全量跑了 3 次：前两次用于暴露并修掉 §7.1 的口径缺陷（旧口径是假达标），正式结果是第 3 次。
本轮**所有** Blender 评估调用合计 107 次（含冒烟 16、3 次全量 72、受控探针 13、注入验证 1、
早期诊断 5），墙钟约 12 分钟，均在 30 分钟预算内。

## 2. 目标函数（5 条硬约束 + 软目标）

`score = 1e6 × hard_violations + soft_cost`（`opt/eval_pixel.py:503-527`）

| 硬约束 | 阈值 | 实测来源 |
|---|---|---|
| 描边暗带 `outline_p50` | ∈ [2, 4] px | `m3_body_q34` 同参数机位 |
| 皮肤 `skin_p50` | ∈ [175, 215] | `m3_face_front` toon 三档分类后的亮度中位 |
| `skin_p95 − skin_p50` | ≥ 30 | 同上 |
| `skin_p50 − skin_p5` | ≥ 25 | 同上 |
| `skin_ge228_pct` | ≤ 35% | 同上 |

软目标：`(outline_p50 − 3)² + ((skin_p50 − 195)/10)² + max(0, 1 − rim_band_px) × 8`。
**rim 项系数 8 与硬约束 1e6 相差 5 个数量级**，rim 永远不会把搜索推到违反硬约束的解上
（实测 rim 最高那组 `back_right@80W` 的 hard=0，见 §4）。

## 3. 搜索空间与采样自检（每维唯一值数）

| 维 | 范围 / 枚举 | step | 默认值 | 本轮 24 次实测唯一值数 |
|---|---|---|---|---|
| `outline_px` | 2.0 ~ 4.5 | 0.5 | 3.5 | **6**（2.0/2.5/3.0/3.5/4.0/4.5） |
| `key_energy` | 40 ~ 60 | 5 | 49 | **6** |
| `skin_pos_mid` | 0.56 ~ 0.70 | 0.02 | 0.62 | **7** |
| `skin_pos_light` | 0.66 ~ 0.84 | 0.02 | 0.68 | **9** |
| `rim_energy` | 80 ~ 400 | 80 | 80 | **5** |
| `rim_azimuth` | {back, back_left, left, back_right} | — | back_left | **4**（全枚举） |

**自检结论：没有任何一维塌缩成单值。** 这一步是必须做的 —— 第一版把「归一化坐标」
直接传给 `snap(实际值)` 时，所有采样点会吸附到参数盒的同一角，而进度行看起来完全正常。
现在的分工是 `space_pixel.snap(实际值)` 与 `space_pixel.from_unit(归一化值)`
（`opt/space_pixel.py:57-84`）两个函数，唯一值数是它们的验收判据（数据来自
`best.json` 的 `pixel.dim_stats[*].uniq`）。

`rim_azimuth` 的 4 个方位在 24 次评估里**全部被点到**，所以 §7 的方位对比不是靠推断。

## 4. baseline vs best 五条硬指标

| 判据 | 阈值 | baseline（默认参数） | best（搜索选出） | 判定 |
|---|---|---|---|---|
| 描边暗带 p50 | 2 ~ 4 px | **3.00** | **3.00** | PASS |
| 皮肤 p50 | 175 ~ 215 | **195.02** | **195.02** | PASS |
| p95 − p50 | ≥ 30 | **32.00** | **32.00** | PASS |
| p50 − p5 | ≥ 25 | **26.82** | **26.82** | PASS |
| ≥228 占比 | ≤ 35% | **4.77%** | **4.77%** | PASS |
| rim 亮带（差分口径，软） | ≥ 1 px | 3.00 | **10.00** | 改善 7px |

`best_params`（即 `opt/best.json` 的 `pixel.best_params`）：

```json
{"key_energy": 49.0, "outline_px": 3.5, "rim_azimuth": "back_right",
 "rim_energy": 80.0, "skin_pos_light": 0.68, "skin_pos_mid": 0.62}
```

**与默认参数的唯一差别是 `rim_azimuth: back_left → back_right`**，其余五维全部等于默认值。
所以五条硬指标**逐位相同**（不是"相近"：195.02/168.19/227.02/26.82/32.00/4.77 与
描边 3.00 都完全不变）—— 这就是 §7.3 说的「零代价」。

独立复核（不经 Blender 的 `Image.pixels`，用 PIL 直接读 `out/` 正式产物，避开 bottom-up 坑）：

```
out/m3_body_q34.png   (560×900)  描边暗带 p50=3.00 p25=2.00 p75=4.00 max=9 n=1383 zero=12.5%
out/m3_face_front.png (620×780)  皮肤 n=152689 p5=168.19 p50=195.02 p95=227.02
                                 p95−50=32.00  p50−5=26.82  ge228=4.77%
                                 三档占比 shadow 44.3% / mid 49.1% / light 6.6%
```

与 Blender 内部量测**逐位一致**，证明 `read_rgb` 的 `[::-1]` 翻转正确（否则同一 ROI 会报
168.2 vs 195.9 这类上下颠倒的差值）。

## 5. 每维敏感性（受控探针：固定其余五维，只变一维）

全部来自 13 次定点评估（`--no-write`，回显在 `opt/logs/px_table.log` 与
`opt/logs/px_ctrl.log`，该目录被 gitignore）。**混在一起变的是 Halton 点，不能直接当敏感性读**，
所以这一节的数据是控制变量的。

### 5.1 `outline_px`（rim 固定 240W / back_left / key 55 / skin 0.68,0.70）

| `outline_px` 参数 | 实测描边 p50 | rim 亮带 | hard |
|---|---|---|---|
| 2.0 | **1.00（违反 ≥2 硬约束）** | 5.0 | **1** |
| 3.0 | 2.00 | 6.0 | 0 |
| 3.5 | 2.00 | 7.0 | 0 |
| 4.0 | 3.00 | 8.0 | 0 |
| 4.5 | 3.00 | 9.0 | 0 |

**参数名义值与实测值差 ≤1px**：`outline_px=4.5` 实测只有 3.00px，因为背面剔除吃掉了
抗锯齿边缘（`lib/look.py:196-223` 的注释里记过同一现象：球体扫描 8mm→3px）。所以可用档位
是 3.0~4.5；**2.0 档不可用**（实测描边 1px，直接硬违规）。

### 5.2 `rim_energy`（outline 固定 4.5 / back_left / key 55）

| `rim_energy` | 描边 p50 | rim 亮带 | hard |
|---|---|---|---|
| 80 | 4.00 | 9.0 | 0 |
| 160 | 3.00 | 9.0 | 0 |
| 240 | 3.00 | 9.0 | 0 |
| 320 | 3.00 | 9.0 | 0 |
| 400 | 3.00 | 9.0 | 0 |

**rim 亮带在 ≥160W 后完全饱和（恒 9.0px）**：toon 三档把连续亮度量化了 —— 一旦 Fac 越过
mid 阈值，亮带宽度就由「几何上超阈值的区域」决定，与灯强无关。同时可见**rim 越强、量到的
描边暗带越窄**（80W 时 4.0px → ≥160W 时 3.0px）：rim 把边缘像素抬过 `亮度<40` 的判据，
削薄了可见描边。这就是「轮廓光与描边互相抵消」，二者在同一张图上争的是同一批边缘像素。

### 5.3 `key_energy`（其余 = 默认）

| `key_energy` | 描边 p50 | 皮肤 p50 | p95−p50 | p50−p5 | rim 亮带 | hard |
|---|---|---|---|---|---|---|
| 40 | 3.00 | 189.67 | **6.20** | **21.47** | 10.0 | **2** |
| 49（默认） | 3.00 | 195.02 | 32.00 | 26.82 | 3.00 | 0 |
| 60 | 3.00 | **228.02** | **2.00** | 59.61 | 6.00 | **3** |

**key 是这套色阶里最敏感的一维**：下调 9W 就把 p95−p50 从 32 打到 6.2，上调 11W 就把皮肤
p50 顶到 228（>215 硬约束）且 ≥228 占比 50.8%。默认 49W 是硬约束窗口的中间，动它立刻违规。

### 5.4 `skin_pos_mid` / `skin_pos_light`（其余 = 默认）

| 维 | 取值 | 描边 p50 | 皮肤 p50 | p95−p50 | p50−p5 | hard |
|---|---|---|---|---|---|---|
| `skin_pos_mid` | 0.58 | 3.00 | 195.94 | 32.07 | 27.75 | 0 |
| | 0.62（默认） | 3.00 | 195.02 | 32.00 | 26.82 | 0 |
| `skin_pos_light` | 0.68（默认） | 3.00 | 195.02 | 32.00 | 26.82 | 0 |
| | 0.76 | 3.00 | 195.02 | **13.21** | 26.82 | **1** |

`mid` 往低挪 0.04 只让 p50 漂 +0.92（软代价 0.0088，仍在窗口内）；`light` 往高挪 0.08
直接把 p95−p50 压到 13.21（硬违规）—— 亮档切分位置抬得越高，light 档吃到的像素越少，
上四分位塌下来。**默认 0.62/0.68 都在硬约束的可行域内，且 `light` 只有很窄的余量。**

### 5.5 `rim_azimuth`（rim 80W，其余 = 默认）

| 方位 | 描边 p50 | 皮肤 p50 | p50−p5 | p95−p50 | rim 亮带 | hard |
|---|---|---|---|---|---|---|
| `back` | 3.00 | 195.02 | 26.82 | 32.00 | **0.00** | 0 |
| `back_left`（默认） | 3.00 | 195.02 | 26.82 | 32.00 | 3.00 | 0 |
| `left` | 3.00 | 195.94 | 27.75 | 33.07 | 5.00 | 0 |
| `back_right` | 3.00 | 195.02 | 26.82 | 32.00 | **10.00** | 0 |

**方位是唯一一个"改了不花钱"的维**：`back_right` 与 `back_left` 的皮肤四项逐位相同
（rim 灯在背后，正面机位看不到它对皮肤的作用），描边同为 3.00px。

## 6. `skipped_dims`（预算不够，如实写）

`opt/best.json` → `pixel.skipped_dims`：

```json
["top1r1:key_energy(budget)", "top1r1:skin_pos_light(budget)", "top1r1:skin_pos_mid(budget)"]
```

24 次评估的分配是 1 baseline + 16 halton + 3 枚举 + 4 邻域（`rim_energy` ±1 两次、
`outline_px` ±1 两次），**预算在第 4 次邻域后就耗尽**，所以 `key_energy`、`skin_pos_light`、
`skin_pos_mid` 三维的坐标下降没做。这不是"已经最优所以不试"，是纯预算。

补足方式：这三维的取值域被 16 个 Halton 点覆盖（唯一值数 6/9/7，见 §3），
受控探针也给了它们的单维影响（§5.3/5.4）；但「三维联合的邻域下坡」确实没做。
若要补，把 `--budget` 提到 32~36 重跑即可（每 8 次约 25s）。

## 7. 轮廓光判定（本任务核心交付）

### 7.1 旧口径是**假达标**（实测证据）

`eval_pixel` 原先的 `rim_band` 用**绝对亮度**找亮带（`opt/eval_pixel.py:233`，仍是保留的
`*_legacy` 口径）。实测：

| 条件 | `rim_skirt_p50` | `rim_hair_p50` | 旧口径 rim |
|---|---|---|---|
| `rim_energy = 0`（灯关掉） | **10.00** | **11.00** | **11.00** |
| `rim_energy = 80`（默认） | 10.00 | 11.00 | 11.00 |
| `rim_energy = 400` | 9.00 | 11.00 | 11.00 |

**关灯和 80W 逐位相同** —— 旧口径量的根本不是轮廓光，而是**裙褶/头发自身的 toon 色阶亮面**：
todon 三档把暗→中→亮渲染成 ≥8 的亮度台阶，绝对阈值一跨过去就成"亮带"，与哪盏灯照的无关。
按旧口径，「轮廓光 11px、可达」是个虚假结论。

### 7.2 差分口径（现在唯一的判定口径）

`opt/eval_pixel.py:303-390` 的 `rim_lit()`：同一机位渲染**两张**图 —— rim 灯开（E）与关（0），
其余一切（几何/材质/其它灯/相机/描边）完全相同，逐像素取亮度差 `d = lum_on − lum_off`。
色阶亮面在两张图里逐位相同，差恒为 0；只有 rim 灯真正点亮的像素才进计数。

判据写死（与旧口径同一几何流程，只把"亮度"换成"亮度差"）：

1. 前景掩码用**关灯图**（rim 灯不应改变 silhouette）；
2. 跳过描边壳：从边界向内跳过连续 `lum_off < 70` 的像素（最多 12px）；
3. `base` 取关灯图 `[k+6, k+20]` 中位，`base > 150` 的行跳过（只量深色主体：藏青裙/头发）；
4. 向内扫 14px，找第一段连续 `d ≥ 8` 的像素，且其后必须**回落到 8 以下**（"先升后降"）；
5. 宽度 = 该连续段像素数。

**自检**（这是差分口径能成立的前提，也是它比旧口径诚实的地方）：

| 条件 | `rim_lit_skirt` | `rim_lit_hair` | 判定 |
|---|---|---|---|
| `rim_energy = 0`（开=关，两张同图） | **0.00（n=0）** | **0.00（n=0）** | 恒 0 ✓ |
| `rim_energy = 80`（back_left） | 2.00（n=40） | 3.00（n=11） | 有贡献 |
| `rim_energy = 80`（back_right） | 2.00（n=33） | **10.00（n=46）** | 有贡献 |
| `rim_energy = 400`（back_left） | 3.00（n=51） | 3.00（n=11） | 有贡献但饱和 |

关灯时严格为 0，说明口径不会被色阶亮面骗到。

### 7.3 判定：**局部可达，但不是整圈连续轮廓光**

**结论不是"不可达"**（任务书的兜底写法不适用），但也**不能**简单写"可达 10px"。
完整判定分三层：

1. **可达**：`rim_azimuth=back_right` + `rim_energy=80`（其余 = 默认）实测
   `rim_band_px = 10.00`（头发区），且五条硬约束全过、皮肤/描边与 baseline **逐位相同**。
   这个组合已写进 `pixel.best_params`。
2. **但它只是局部**：头发区的 46 行亮带**全部集中在 z 1.6025~1.6198**（颅顶下方约 17mm 的
   高度带），占该区域轮廓行数 46/511 = **9.0%**；藏青裙区 33 行在 z 0.75~0.83，
   占 33/185 = 17.8%，宽度只有 2px。**不是沿整圈轮廓的连续勾边。**
3. **方位决定哪一侧亮，不是随机**：`back_left` 的 11 行亮带全在**左边界**（L=11/R=0），
   `back_right` 的 46 行全在**右边界**（L=0/R=46）。灯在哪侧、亮带就在哪侧 —— 这反过来
   证明差分口径抓的是真轮廓光，而不是别的像素结构。

**为什么是研判而非"达标"**：10px 是这 46 行内部的宽度中位；把覆盖率和位置一起看，
视觉上是"颅顶右缘的一抹高光"，不是原神式整圈描边。若验收口径要求"整圈连续"，
那仍然**未达标**，需要多盏 rim 灯（左后 + 右后各一盏）或环形灯，见 §11 未完成项。

### 7.4 亮带位置实测（行分布，来自 `opt/tmp/*_i990.png` 的开/关两张图）

```
back_right（best）  头发: 46 行，z∈[1.6025, 1.6198]，宽 p50=10px max=13px，全部右边界
                    裙:   33 行，z∈[0.752, 0.834]  ，宽 p50=2px  max=2px ，全部右边界
back_left（默认）   头发: 11 行，z∈[1.6075, 1.6114]，宽 p50=3px  max=11px，全部左边界
                    裙:   40 行，z∈[0.752, 0.834]  ，宽 p50=2px  max=6px ，全部左边界
```

（`face_front` 机位 ortho 0.30 / 780px ⇒ 0.385mm/px，所以头发区 10px ≈ 3.85mm；
`body_front` ortho 1.80 / 900px ⇒ 1.80mm/px，裙区 2px ≈ 3.6mm。）

## 8. 描边宽度 → rim 亮带对照表

受控条件（6 次定点评估，`opt/logs/px_table.log`）：`key=55, skin 0.68/0.70, back_left`。

### 8.1 三档描边宽度（`rim_energy = 240W` 固定）

| `outline_px` 参数 | 实测描边 p50 | rim 亮带 | hard | 皮肤 p50 |
|---|---|---|---|---|
| **2.0** | **1.00** | **5.0** | **1（描边 <2px）** | 195.94 |
| **3.0** | **2.00** | **6.0** | 0 | 195.94 |
| **4.5** | **3.00** | **9.0** | 0 | 195.94 |

**怎么读这张表**：rim 亮带随描边名义值单调上升（5/6/9 @ 2.0/3.0/4.5），但**这不是
"描边越厚轮廓光越亮"的物理结论** —— 差分口径里描边壳本身 `d≡0`（关灯时严格 0 已验证），
所以偏差来自「跳过描边壳」那一步对厚度的敏感性：壳越厚，从前景边界向内数的起点越靠内，
扫描窗口整体右移 1~2px，把更多 d≥8 的像素纳入连续段。**物理量与量测口径在这里耦合了**，
所以这张表只能当"同一口径下的相对比较"，跨分辨率/跨描边方案的绝对值不可直接搬。
（同样条件下 `outline_px=3.5/4.0` 的实测是 7.0/8.0，见 §5.1，单调性一致。）

**可用档位**：2.0 档实测描边只有 1px，硬违规，不可用；3.0 / 4.5 两档都在硬约束内。

### 8.2 rim 强度梯度（`outline_px = 4.5` 固定）

| `rim_energy` | 描边 p50 | rim 亮带 |
|---|---|---|
| 80 | 4.00 | 9.0 |
| 160 | 3.00 | 9.0 |
| 240 | 3.00 | 9.0 |
| 320 | 3.00 | 9.0 |
| 400 | 3.00 | 9.0 |

**≥160W 后饱和**（toon 三档量化，见 §5.2）。80W 那行的描边 4.00 是因为 rim 太弱、
边缘像素没被抬过 `亮度<40` —— rim 与描边争同一批像素的直接证据。

## 9. 几何段完好性（证明没被像素段覆盖）

`opt/best.json` 是**读-改-写**：`opt/search_pixel.py:228-244` 的 `write_best()` 只替换
`pixel` 键，顶层 20 个几何键原样保留。落盘后断言（搜索器自己打印）：

```
[searchp] top-level keys after = [algorithm, baseline_metrics, baseline_score, best_label,
  best_metrics, best_params, created, elapsed_s, hard_violations_baseline, hard_violations_best,
  n_evals, n_halton, pixel, rounds, score, seed, sensitivity, soft_baseline, soft_best, topk, trials]
  (best_params 是否保留=True)
```

**重跑 `_stageD/d_probe.py` 的裙腰四段（几何段 best 注入后的值）**：

| z 带 | 本次实测（x=−40mm） | `best.json` 几何 `skirt_net_mm` | 判定 |
|---|---|---|---|
| 0.920~0.960 | +14.2mm | 14.24 | 一致 |
| 0.960~1.000 | +11.1mm | 11.05 | 一致 |
| 1.000~1.040 | +6.6mm | 6.645 | 一致 |
| 1.040~1.060 | +14.7mm | 14.73 | 一致 |

（`d_probe` 打印 1 位小数，与 `best.json` 的 2~3 位按四舍五入对齐；四段全 ≥ +2mm 阈值。）
`d_probe` 其余项也全 OK（D1 刘海 3 组缝 1.5mm / D2 半宽 19mm 厚 9mm 沟壑 5.6mm /
D3 前领 V 深 18.5mm / D4 卷边凸出 3.3mm 边界边 0 / D5 褶峰谷差 25.9mm 中线是峰）。

### 9.1 作业期间有并发写入者（复核记录）

11:46~11:49 期间，**另一个 agent** 在本工程写了 `cfg.py`、`lib/body.py`、`lib/head.py`，
并新增 `lib/profile.py`（**不是本次改动，未提交**）。其中 `lib/head.py` 一度出现
`IndentationError: unexpected indent`（11:49:06 快照，第 168 行 `z_cheek = sz(1.4720)`），
11:49:41 停笔后语法恢复正常。

在这一版代码上复测（这是本文数字的有效性边界）：

| 项 | 11:43 状态（正文数字来源） | 11:49 之后（含并发改动） | 判定 |
|---|---|---|---|
| 描边 p50 / 皮肤 p50 / p95−50 / p50−5 / ≥228 | 3.00 / 195.02 / 32.00 / 26.82 / 4.77% | **逐位相同** | 结论不变 |
| rim 亮带（差分口径） | 10.00 | **10.00** | 结论不变 |
| 裙腰四段（x=−40mm） | 14.2 / 11.1 / 6.6 / 14.7mm | **14.2 / 11.1 / 6.6 / 14.7mm** | 一致 |

所以本文所有数字对「11:49 之后的 head/body/cfg」仍成立；但这批改动落地后若**继续**改几何，
需要重跑 `opt/eval_pixel.py -- --use-best --no-write`（单次约 5s）与 `_stageD/d_probe.py` 再确认。

## 10. 行为不变性、注入链路与回滚

**无 `pixel` 段时逐位不变**：`lib/look.py:239` 的 `optio.param("outline_px", float(base_px))`
在 best.json 缺键时回退到调用方传的 `base_px`（m3_look 传 3.5），`k = px_base/base_px = 1.0`，
厚度逐位不变；`lib/shots.py:44-46`、`lib/look.py:290-291` 同理。删掉 `opt/best.json`
就回到全部手调默认值，不需要改任何调用点。

**注入链路实测**（`--use-best` 走读盘）：

```
blender -b --factory-startup --python opt/eval_pixel.py -- --use-best --no-write
[eval] param_rim_azimuth=back_right     ← 从 best.json 的 pixel 段读出
[eval] outline_p50=3.00  skin_p50=195.02  skin_p50_m5=26.82  skin_p95_m50=32.00
[eval] skin_ge228_pct=4.77  rim_band_px=10.00  hard=0
```

**查找顺序实测**（`lib/optio.py:100-121`）：

```
optio.param('outline_px',  3.0)   → 3.5    （pixel 段赢）
optio.param('skirt_margin', 0.0)  → 0.008  （顶层几何段）
optio.param('not_exist',   42)    → 42     （default）
```

**回滚三档**：

| 想要的状态 | 操作 |
|---|---|
| 回到默认轮廓方位（`back_left`），保留其余像素最优 | `pixel.best_params.rim_azimuth` 改回 `"back_left"` |
| 回到「没有像素段」的手调默认 | 删掉 `best.json` 的 `pixel` 键（`python -c` 读改写，别手删整段 JSON） |
| 回到搜索前（几何段也要保留） | `git checkout -- opt/best.json` 然后重跑 `opt/search.py` |

## 11. 产物清单与未完成项

| 文件 | 说明 |
|---|---|
| `opt/space_pixel.py` | 6 维参数空间、默认值（带 `文件:行`）、`snap`/`from_unit` 分工、`fixup`（mid<light）、默认值自检 |
| `opt/eval_pixel.py` | 单次评估：5 张渲染（含 rim 开/关差分对）→ 五条硬指标 + `rim_lit` 差分口径 → score |
| `opt/search_pixel.py` | baseline → Halton → `rim_azimuth` 全枚举 → top-k 坐标下降 → 读-改-写 `best.json` |
| `opt/best.json` | 顶层几何段（20 键，未动）+ `pixel` 段（best/baseline 指标、`rim_verdict`、`dim_stats`、`outline_px_controlled_table`、`skipped_dims`） |
| `opt/trials_pixel.jsonl` | 逐次评估记录（含本轮 3 次全量 run 的全部 72 条） |
| `lib/optio.py` | 注入层：override → `pixel` → 顶层 → default |
| `opt/logs/` | `px_full3.log`（正式全量）、`px_table.log`（6 次受控）、`px_ctrl.log`（7 次受控）、`d_probe.log`、`m3_rerender.log` |

复跑命令：

```bash
cd /d/G/github/Tools/人物建模

# 冒烟（16 次评估、约 30s）
"D:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
    --python opt/search_pixel.py -- --n 2

# 全量（24 次评估、约 72s）
"D:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
    --python opt/search_pixel.py -- --n 16

# 单点（默认 / 指定 / 走 best.json）—— 后者验证读盘注入链路
... --python opt/eval_pixel.py -- 
... --python opt/eval_pixel.py -- --params '{"rim_energy":400}' --no-write
... --python opt/eval_pixel.py -- --use-best --no-write

# 受控对照（固定其余五维，只变一维；生成 §8 的表）
... --python opt/eval_pixel.py -- --no-write --params \
    '{"key_energy":55,"skin_pos_mid":0.68,"skin_pos_light":0.70,"rim_azimuth":"back_left",
      "outline_px":4.5,"rim_energy":240}'

# 独立复核（不用 Blender 的 pixels，用 PIL 直接读 out/）
python -c "..."   # 见 §4 的复核数字；口径与 eval_pixel.edge_dark_width/skin_stats 同源
```

### 未完成项（如实）

1. **`key_energy` / `skin_pos_light` / `skin_pos_mid` 三维的坐标下降没做**（预算，见 §6）。
2. **整圈连续轮廓光未实现**：当前只是「朝向 rim 灯那一侧、颅顶下方 17mm 高度带」的局部亮边
   （覆盖 9.0% 轮廓行数）。要做整圈，需要左后 + 右后两盏 rim（或把 rim 改成环形灯），
   这超出本次「只扫已有 6 维」的范围。
3. **左右不对称未查**：同一灯距/同高度下 `back_right` 的头发亮带 p50=10px、`back_left` 只有
   3px（max 分别是 13 / 11）。两侧 max 接近但 p50 差 3 倍，可能是 D 阶段侧发/分缝的左右
   几何差异，也可能是掠射角对机位的不对称响应 —— 本轮没做几何级定位，不能给结论。
4. **`rim_lit` 对描边厚度敏感**（§8.1）：跨描边方案比较时该口径需重新标定，不能直接搬绝对值。
5. **受控探针 13 次不在 24 次搜索预算内**：它们是交付必需的对照数据，但与搜索的 24 次是
   两次独立的评估批次；报告里所有 "受控" 数字都注明来源日志，不与搜索点混用。