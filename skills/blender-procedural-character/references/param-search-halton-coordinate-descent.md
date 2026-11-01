# 参数自动搜索（Halton + top-k 坐标下降）与可回退注入

适用场景：headless Blender（或任何「一次评估要重建整个场景」的重管线）里，
有几个连续/类别参数一直靠人肉试参、结果不可复现。2026-11-01 在 `人物建模/opt/`
落地过一版：5 维（裙腰 margin、净空口径 valley/peak、手指混合指数 p、
Laplacian 平滑次数、关节混合带宽）、96 次评估、8 分钟、score 20.24 → 1.36。

## 结构（可照抄）

- `halton.py`：`halton(i, base)` + `halton_seq(n, d, seed)`。**seed 只决定两件事**——
  跳跃起点、维度与底数的乱序；数值本身由 Halton 决定性给出。所以 best.json 只记
  seed 就能完全复现，不需要存采样矩阵。
- `space_geom.py`：`DIMS`（key/lo/hi/step/default/**src 写"文件:行"**）+
  `verify_defaults()` 在 Blender 里现场 import 模块、把模块常量与 DIMS 对一遍，
  打印 MATCH/MISMATCH；不一致直接中止搜索。
- `eval_geom.py`：单次评估 = `shots.reset()`（内部即
  `bpy.ops.wm.read_factory_settings(use_empty=True)`）→ 按入口同序重建 →
  6 类指标 → `score = 1e6·硬违规 + 软代价` → 追加一行 `trials.jsonl`。
  任何异常都捕获 traceback 首末行、记 score=1e9，不让单个点拖死整轮搜索。
- `search.py`：baseline → Halton n 点 → 按 score 取 top-k →
  每个 top 点 rounds 轮「逐维 ±1 step（越界夹紧、夹紧后等于原值就不试）」→
  敏感性 → 写 `best.json`。参数点按 JSON 键去重缓存。

## 六个坑（全是本轮真踩的）

1. **归一化坐标 vs 实际值必须分成两个函数**。
   `snap(dim, v)` 收**实际值**，`from_unit(dim, u)` 收 **[0,1)**；
   第一版把归一化坐标直接喂给 `snap()`，32 个采样点被全部夹到参数盒右上角，
   搜索退化成一个角点 —— 而日志看着完全正常（有 `[search] 8/118 best=…` 进度、
   有 score）。自检只要两行：
   `len({json.dumps(p, sort_keys=True) for p in sample(32)}) == 32`，
   并打印每维的取值分布（`Counter`）确认铺满而不是堆在端点。
2. **参数必须在调用时读，不能在 import 时读**。写成
   `SKIRT_WAIST_MARGIN = optio.param("skirt_margin", 0.003)`
   会在 override 之前就定型。正确写法：模块级保留常量作为 default，
   在**函数体内** `margin = optio.param("skirt_margin", SKIRT_WAIST_MARGIN)`。
   这样同一个 Blender 进程里连跑几十次评估才不会串参。
3. **硬约束必须覆盖「已经达标的东西」**。任务书列了 5 条硬约束，
   第一版严格按 5 条跑出的最优解把裙腰收紧后，既有判据
   `b_probe R2 leak walk` 从 0 个/0mm 变成 2 个/4.11mm —— 典型「换一项坏三项」。
   把该判据（≤5 个且 ≤2mm）加为第 6 条硬约束后重跑，最优解自动退回到不破线的区域。
   **规则：开搜之前，把全部"已达标项"逐条翻译成硬约束**，哪怕任务书没列。
4. **软目标单位不统一会让某些维度"假不敏感"**。任务书规定「裙腰过松」以**米**计
   （Σmax(0, net−0.008)），值域约 0.016 分；而「屈指 min」项 baseline 就 20 分。
   裙腰两个维度因此几乎不参与竞争。**不要擅自改口径**，而是在报告里写清
   「该维不敏感，原因是单位/量级差异，若希望参与竞争需改计量单位或权重」。
5. **耦合维度会出现天文数字敏感性 delta**。单独把 `skirt_margin` 退回默认值，
   在 peak 口径下会同时破 net 与 walk 越出两条硬约束 → Δscore ≈ 2e6。
   这不是「这一维很重要」，而是两维耦合（peak 的 inner = margin − 1.25·amp）。
   敏感性表要允许并解释这种数字。
6. **评估次数估计 ≠ 实际**。上限估 118，去重缓存 + 边界夹紧实际只跑 96。
   先 `--n 4` 冒烟（本次 15 次评估 52s、单次 3.4s），确认单次成本与指标口径，
   再上全量（96 次 × 4.3s ≈ 8min）。评估里不要渲染、不要存 blend。

## 注入层（optio）与行为不变性

- `lib/optio.py`：`param(key, default)` —— 文件缺失 / JSON 损坏 / 键不存在 /
  类型转换失败，**一律回退 default**；类型跟随 default（int 取整、str 转字符串、
  bool 先于 int 判断）。另设 `set_overrides()` / `reload()` 给搜索器进程内注入，
  这样搜索期间不写盘、不污染 best.json。本模块**不 import bpy**。
- `LAST_SKIRT_NETS` 这类「构建时就已算好的量」用模块级 dict 暴露给评估器取数，
  比让评估器再复算一遍几何便宜、且口径天然同源。
- 改 lib 之前先采集探针快照（本次 `opt/logs/premod_dprobe.txt` / `premod_bprobe.txt`）；
  改完、best.json 不存在时再跑同一探针，**逐行比对必须 0 差异**
  （本轮 b_probe 97 行数字全同，仅多两条新增打印字段，strip 后缀后 0 diff）。
- **验证注入链路时不能走搜索器的 override**：给评估器加 `--use-best`
  （params=None → 不 `set_overrides`，直接读 best.json），再用已有探针复测同一批指标。
  否则「只在进程内 override 成立」会被误当成「注入生效」。
- 回退路径要单测：缺文件 / 坏 JSON / 缺键 / 类型错 / override 覆盖 / 清空 override。

## 产物与复现

- `trials.jsonl` 追加写，每行含 params/metrics/hard/soft/score/t；
  另加 `{"event":"run_start"}` / `{"event":"run_end"}` 标记。
  跑坏的轮次**mv** 到 `opt/logs/trials_rerunN_<原因>.jsonl` 归档，不要删。
- `best.json`：seed / n_evals / best_params / best_metrics / score /
  baseline_metrics / baseline_score / created(ISO) / sensitivity / elapsed_s。
- 回滚三档：①删 `best.json`（所有 `param()` 回落模块常量，逐位回到手调版）；
  ②只改 `best_params` 里某一个键（缺键按 default 回落）；
  ③代码回滚（`git checkout lib/…`）。

## 报告纪律

- 没达标就写没达标。本次屈指 min 0.529 → 0.582，目标 0.6，**仍未达标**；
  p95 反而 1.182 → 1.208（仍在阈内），要写明这是「少平滑换更小 max」的取舍，
  不能只挑好看的报。
- 偏离任务书的地方逐条写原因与实测后果：维度区间（实测默认值落在示例区间外时
  必须收窄区间，否则默认点不在搜索盒内、坐标下降回不到默认）、新增的第 6 条硬约束、
  单位不统一的软项。
- 结论里区分「量测值」与「推断」，并说明哪些维度「无改善，已是局部最优」。

## 工具纪律

- 归档/清理文件用 `mv` 到 `opt/logs/`；shell 命令里带 `rm -f` 可能被安全策略
  **整条拒绝**（包括同一条命令里的搜索跑批），白跑一轮。
- 生成 best.json 之前，先确认这一轮的 trials 是干净的一轮（坏轮次已归档），
  否则报告引用的 n_evals / 敏感性会对不上。