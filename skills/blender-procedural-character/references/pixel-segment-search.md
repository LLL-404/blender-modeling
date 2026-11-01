# 像素段参数搜索（渲染参数）—— 与几何段共用同一套 Halton / 坐标下降

适用：**只有渲染完才有指标**的参数（描边线宽、灯功率与方位、色阶切分位置、rim 强度）。
几何段那套 `Halton → 按 score 取 top-k → 逐维 ±1 step 坐标下降` 可以直接复用，真正的
新增成本与坑都在「评估器要渲染」和「一份配置文件被两段共享」上。几何段本身的机制与
采样坑见 `references/param-search-halton-coordinate-descent.md`。

单次评估 = `read_factory_settings(use_empty=True)` → 建角色与灯光 → 渲 N 张 → 读图统计 →
打分 → 追加 trials。本次实测：6 维、3 张 560×900/620×780 渲染，**4.3s/次**（中位），
24 次预算约 2 分钟；几何段同级评估只要 3.4s 且无渲染。

## 1. 两段共享一份 best.json：读-改-写，绝不覆盖

结构：

```json
{ "best_params": {...},                // 几何段（先写）
  "baseline_metrics": {...}, ...,
  "pixel": {"best_params": {...}, "best_metrics": {...}, "score": ..., "n_evals": ..., "elapsed_s": ...} }
```

* **写**：`read → 只替换 doc["pixel"] → 原样写回`。落盘前打印 `before_keys / after_keys`
  并断言 `"best_params" in after`，否则「几何段的 5 个最优值被一次像素搜索抹掉」这种事故
  要到下一次几何探针才暴露。
* **读**：`optio.param(key, default)` 查找顺序改成 **pixel.best_params → 顶层 best_params
  → default**。pixel 优先的理由是「更晚写、更专指」；两段键名不重叠时该顺序无副作用。
* 同一进程里还有第三条路：`set_overrides()`（搜索器用，不落盘）优先级最高。
* **写完必须重跑上一段的探针**证明旧段仍生效（本次：注入 pixel 段后 `d_probe` 输出与
  注入前逐字相同，裙腰仍是几何段最优的 14.24/11.05/6.65/14.73mm）。
* 两段各自的 `--use-best` 路径（见 §9）读同一份文件，因此「删 best.json 回滚」对两段同时成立。

## 2. 注入点：在函数内部用「调用方传入值」当 default

不要改调用点，也不要另建一份参数表；在每个消费函数里读一次：

```python
# look.set_outline_px(objs, mods, ortho, res_y, base_px=3.5, per_obj_px={...})
px_base = optio.param("outline_px", float(base_px))
k = px_base / float(base_px) if base_px else 1.0
for ob, m in zip(objs, mods):
    px = per_obj_px.get(ob.name, base_px) if per_obj_px else base_px
    m.thickness = px * k * ortho_scale / float(res_y)
```

要点：
* 用**调用方传入的值**当 default → 所有入口（m3/m4/m5/m5_rig）自动生效，且无 best.json
  时逐位不变，不需要逐个改调用点。
* `per_obj_px`（例如头部单独 3.5）按同一比例 `k` 缩放，保留「头比身体略粗」的相对关系；
  不要只替换 base 而让 per_obj 保持绝对值，那会改变相对线宽。
* 灯参数同理：`stage_c_lights()` 里 `vals["key"] = optio.param("key_energy", vals["key"])`。
* 色阶同理：`set_all()` 里 `pos=(0.0, optio.param("skin_pos_mid", SKIN_POS_MID), ...)`。
* **加「默认值锚点常量」**（`OUTLINE_PX / SKIN_POS_MID / SKIN_POS_LIGHT / RIM_AZIMUTH`），
  并在 `space_pixel.verify_defaults()` 里现场 import 后逐项 MATCH/MISMATCH。
  这是防止「代码默认值改了、搜索盒的 default 忘了同步」的唯一手段；搜索器开头不一致就中止。

## 3. 枚举维不要当连续维做 ±1

`rim_azimuth ∈ {back, back_left, left, back_right}`：坐标下降遇到 choices 维时**除当前值外
全枚举**（3 次），只在 top-k 点上扫一遍，不要映射成 0..3 的整数做 ±1——那会把「正后 ↔ 左后」
和「左后 ↔ 左」当成等距邻居，语义上不成立。

灯位枚举的**对照公平性**：半径与高度固定（沿用现网 `hypot(2.2,2.0)=2.974`、z=2.2），只改
方位角。否则「把灯挪远/挪高」会和方位混在一起，无法归因。

## 4. 采样与邻域都要做物理合法性 fixup

本次坑：`skin_pos_mid / skin_pos_light` 是 ColorRamp 的元素位置，必须严格递增
`0 < mid < light`。只渲染端夹紧不够——夹紧后「评估记录的参数」与「实际生效的参数」分叉，
指标无法归因给某一维。

```python
def fixup(p):                      # 采样点与每个邻域候选都要过一遍
    q = dict(p)
    if q["skin_pos_light"] < q["skin_pos_mid"] + 0.02 - 1e-9:
        q["skin_pos_light"] = snap(dim("skin_pos_light"), q["skin_pos_mid"] + 0.02)
    return q
```

**浮点噪声**：`0.68 + 0.02 == 0.7000000000000001`，于是 `light(0.7) < mid+0.02` 判真，
采样器与约束互相打架。修法：比较加 `1e-9` 容差，落盘/注入前 `round(x, 6)`。

## 5. 预算受限：维度顺序 + 如实记 skipped

总预算 24 次时：baseline 1 + Halton n 16 = 17，只剩 7 次给下降。
* 每次 `ev()` 前查 `budget_left()`，超了就**停**并返回 None（调用方 `break`）。
* 维度按「与本次交付判定直接相关」排序：`rim_energy → rim_azimuth → outline_px → key →
  skin_pos_light → skin_pos_mid`。这个顺序保证预算不会先花在「已经不达标但影响很小」的维上。
* 没试到的维写 `skipped_dims=["top1r1:skin_pos_mid(budget)", ...]`，报告里如实写「未试」，
  **不要**用相邻维的数字推断它的敏感性。
* 采样阶段也要查预算（`if budget_left() <= 0: break`），否则 Halton 点数会被静默截断。
* 冒烟 `--n 2` 先确认单次评估能跑通、指标量级合理，再 `--n 16`。

## 6. 像素指标口径（可直接照抄的三类）

1. **描边暗带**（C1 口径）：逐行取前景左右边界，在边界 ±8px 窗内量 `lum<40` 的最长连续带，
   全图取 p50。目标 2~4px。别忘 `Image.pixels` 是 bottom-up，读图后要 `[::-1]`。
2. **皮肤色阶**（C3 口径）：按 toon 三档**显示色**（shadow/mid/light 的 RGB）最近邻分类出
   皮肤像素（距离 <38），再量 p5/p50/p95 与 ≥228 占比。用三档色分类比绝对亮度阈值稳，
   因为色阶重标定会整体移动亮度。
3. **轮廓亮带**（C4 收口后的新口径，必须写死）：
   1. 逐行取前景左右边界；
   2. **跳过描边壳**：从边界向内跳过连续 `lum<70`（最多 12px）——不跳的话第一个像素永远是
      3~4px 的黑描边壳，量到的一律是 0；
   3. 主体亮度 `base` = 再向内 6~20px 的中位亮度；`base > 150` 的行**跳过**（只量深色主体：
      藏青裙≈44 / 头发≈90。白衬衫与皮肤已在 light 档 ~227，rim 加不亮，混进来只会稀释样本）；
   4. 向内扫 14px，找第一段连续 `lum > base+8`，且其后必须**回落到** base+8 以下
      （「先升后降」）；一直亮到窗口末端的不算——那是整片亮面而不是亮带；
   5. 宽度 = 该连续段的像素数；对「有亮带的行」取 p50。
   深色区要**分别报**：藏青裙 z 0.65~1.05（用正对机位，世界↔像素可精确反投影
   `z = zc + (h/2 − py)/s, s = h/ortho`）、头发 z 1.40~1.62；再报一份 q34 旧口径
   （只按 `base≤150` 筛行、不做 z 过滤）便于与历史数字对照。

## 7. 分辨率与 px 换算（必须写进报告）

描边厚度是**按像素反算**的：`thickness = px × ortho/res_y`（`look.set_outline_px`）。由此：

* 用**同一视图、同一 res_y** 反算 ⇒ 屏幕上线宽恒为 px，**线宽像素数与分辨率无关**。
  据此可以直接用低分辨率渲染并声明「px 无需换算」。
* 若改成「按正式 res_y 反算厚度、却用低分辨率渲染」⇒ 世界厚度不变而像素变小，
  `px_实测 = px_正式 × res_实测/res_正式` ⇒ 必须换算 `px_正式 = px_实测 × res_正式/res_实测`。
  两种实现都可，但报告必须写清是哪一种；本次用前者（直接按正式分辨率渲染），
  换算公式仍写进报告备低分辨率复跑。
* **亮度分位（p50/p5/p95/占比）与分辨率无关**，不需要换算；但 ROI 反投影要用渲染时的
  真实 `h/ortho`，否则 z 映射会偏。

## 8. 渲染卫生

* 每次评估 `shots.reset()`（内部即 `read_factory_settings(use_empty=True)`），**禁止复用**。
* 全部图写 `opt/tmp/`；正式产物（`out/m3_*.png`）**只在全部搜索结束后**用最优参数重渲一次。
* 读完图立刻 `bpy.data.images.remove(img)`，否则同一进程内 datablock 会一路累积。
* 前景掩码：背景取四角**中位色**；若该色亮度 >120（角上已踩到角色/地板高光）改用**最暗**那一角。
  本次三种机位四角都是背景，两条判据同值，但写上 fallback 避免换机位时整图被判成前景。

## 9. 目标函数：量纲与次要项

`score = 1e6 × 硬违规数 + soft`。硬约束 5 条（描边 p50∈[2,4]、皮肤 p50∈[175,215]、
p95−p50≥30、p50−p5≥25、≥228 占比≤35%）。

* **次要项必须远小于硬约束**：轮廓亮带 `max(0, 1 − rim_px) × 8` —— 最大只值 8 分，
  换不来一条硬违规（1e6），符合「rim 只是次要目标」。
* **量纲陷阱**：几何段「裙腰过松」以**米**计，贡献只有 0.016 分；而屈指项
  `(0.6−min)²×4000` 在 baseline 就占 20 分 ⇒ 裙腰那两个维度在 score 里几乎不敏感。
  按任务指定的公式实现，然后在报告里**如实标注量纲后果**，不要擅自改权重
  （改权重是产品决策，不是实现细节）。
* **耦合维**：把某一维固定在默认值会同时破两条硬约束时，Δscore = 2e6。报告里要写
  「这是两维耦合（peak 口径必须配 margin≥0.007），不是单维重要性」，否则读者会误读。

## 10. 验证链条：两条注入路径都要单独测

* 搜索器走**进程内 override**（`set_overrides`），**完全绕过 best.json** ⇒ 若只跑搜索器，
  你验证的只是 override 路径，`pixel→顶层→default` 的读盘顺序一条都没走到。
* 因此评估器必须再给一条入口：`--use-best` → `params=None` → `optio.reload()` +
  `set_overrides(None)`，然后复现 best 的全部指标（本次逐项复现：描边 3.00、皮肤
  195.0/26.8/32.0/4.8%、rim 0，score 完全一致）。
* 再跑一次**旧段的探针**证明共享文件没被覆盖（本次 d_probe 22 行逐字相同）。
* 回滚：删 `opt/best.json` → 两段同时回落默认；单维回滚 = 改/删 `best_params` 里的一个键。
  归档旧 trials / 旧 best 用 `mv` 改名（本机工具安全策略会拒绝 `rm -f`），保留复现历史。

## 11. 可复现性与「采样器到底铺没铺开」

* `seed` 只决定 Halton 的跳跃起点与「维度→底数」乱序，数值本身决定性 ⇒ best.json 只记 seed。
* trials 每次评估一行（params/metrics/hard/soft/score/t），另写 `run_start` / `run_end`
  标记行，同一文件里可以容纳多轮（坏采样那轮用 `mv` 归档而不是删掉）。
* **覆盖度自检**（这次真抓到过）：`len({json.dumps(p, sort_keys=True) for p in sample(n)})`
  应等于 n，且逐维打印取值分布（Counter）。本次第一次跑出「32 个采样点 → 2 个唯一值、
  全挤在参数盒右上角」，原因是把**归一化坐标**直接喂给了期望**实际值**的 `snap()`。
  这类 bug 的症状很有欺骗性：搜索照常跑完、有 best.json、有进度行，只是实际只测了一个角点。
  因此「唯一值数 + 每维 Counter」应做成**每次搜索开头的固定自检**，而不是出事后再查。