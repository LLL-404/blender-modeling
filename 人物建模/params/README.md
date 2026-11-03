# 外观旋钮（params/profile.json）

`profile.json` 是**人手工调风格**的参数文件；读取层是 `lib/charparams.py`
（`get('appearance.height', 1.62)`，点路径 + 类型校验，缺失/解析失败/类型不符一律回退默认值，永不抛异常）。

> 改参数优先走 `scripts/brief.py`：它按本文件的建议范围校验，未知键/类型不符/超范围会报错，未接线键会警告；默认 dry-run，`--apply` 才写盘并备份。直接手改仍可用，但不会得到这层校验。

**默认值 = 引入旋钮之前代码里的字面量**。所以：

* 删掉 `params/profile.json` → 行为与参数化之前**逐位相同**；
* 只改想改的键，其余键删掉也安全（缺键走调用点的默认值）；
* 临时试一套参数：`PM_PROFILE=params/_tmp/x.json`（相对路径按项目根解释）；
* 改完不需要改任何 `.py`，也不需要重启 shell —— 新起一次 Blender 进程即可
  （模块级常量如 `outfit.SKIRT_SEG` 在 import 时定型，同一进程内不会跟随）。

## appearance（16 键）

| 键 | 现值 | 取值范围（建议） | 影响什么 | 接线位置 |
|---|---|---|---|---|
| `height` | 1.62 | 1.45~1.80 | 头顶高度；同时把 `头部整体 z` 平移到该高度 | `cfg.py:13`、`lib/head.py:45,56` |
| `head_to_body_ratio` | 7.5 | 5.5~8.0 | 头身比（头长 = height / ratio）；改名会缩放整张 HEAD 表，并联动 `lib/look.py` 的头部坐标映射（`_head_scale()` / `_head_shift()` 现算，2026-11-03 起不再冻在 1.063） | `lib/head.py:38,105`、`lib/look.py:_head_scale` |
| `head_width_scale` | 1.0 | 0.95~1.05 | 头宽（HEAD 的 rx 与中线偏移 cy） | `lib/head.py:112` |
| `face_width_scale` | 1.0 | 0.95~1.05 | 脸的前后进深（HEAD 的 ry前/ry后） | `lib/head.py:113` |
| `eye_spacing_scale` | 1.0 | 0.9~1.1 | 眼中心 x（`EYE_X`）与眼窝、眉起点 | `lib/head.py:138,346` |
| `eye_size_scale` | 1.0 | 0.9~1.1 | 眼型外轮廓 + 虹膜/瞳孔/高光等比 | `lib/head.py:143,285` |
| `nose_depth_scale` | 1.0 | 0.8~1.0 | 鼻尖前伸推量（0.0125m 的天花板乘此系数） | `lib/head.py:173` |
| `mouth_width_scale` | 1.0 | 0.8~1.2 | 嘴宽（贴片与 sculpt 的唇部 x 半宽同步） | `lib/head.py:174,367` |
| `ear_scale` | 1.0 | 0.85~1.15 | 耳廓等比（位置不动；归一化基准同比缩放） | `lib/head.py:401` |
| `shoulder_width_scale` | 1.0 | 0.95~1.08 | TORSO 肩段派生宽（z≈1.29，三角权重平滑过渡） | `lib/body.py:48,62` |
| `waist_scale` | 1.0 | 0.9~1.1 | TORSO 腰段派生宽（z≈1.01） | `lib/body.py:48,62` |
| `hip_scale` | 1.0 | 0.95~1.1 | TORSO 髋段派生宽（z≈0.86） | `lib/body.py:48,62` |
| `leg_length_ratio` | 0.469 | 0.42~0.52 | 腿长比：以膝 z=0.425 为铰点缩放膝以上，脚不动 | `lib/body.py:130` |
| `arm_thickness_scale` | 1.0 | 0.9~1.15 | 手臂截面半径（路径/臂长不动） | `lib/body.py:270` |
| `hand_scale` | 1.0 | 0.9~1.15 | 掌宽/掌厚/指粗/拇指径（掌长与指长不动，保证与指骨同源） | `lib/hand.py:416` |
| `foot_size_scale` | 1.0 | 0.9~1.15 | 脚长（y）与脚掌/脚趾半宽（高度 z 不动） | `lib/body.py:202` |

## hair（11 键）

| 键 | 现值 | 取值范围（建议） | 影响什么 | 接线位置 |
|---|---|---|---|---|
| `style` | `bob` | `long` / `bob` | **发型分叉**。`bob` = 一整片锯齿刘海 + 开口外壳（`_cap` + `_bob_shell` + `_fringe`）；`long` = 分组刘海 + 后发束 + 侧发 + 呆毛（旧路径）。切到 `long` 时下面 3 个 `bangs/clump/ahoge` 键才生效，切到 `bob` 时它们全部被忽略 | `lib/hair.py:build()` |
| `hair_color` | `[1.0, 0.565, 0.648]` | RGB 0~1 | 发色底（参考图取色 `#FF90A5`）。**已接线**：`hair_material()` 现读这个值，明暗三档由 `hair_shadow_color ÷ hair_color` 自动推出 | `lib/look.py:hair_material()` |
| `hair_shadow_color` | `[0.216, 0.06, 0.107]` | RGB 0~1 | 发色暗档（参考图 `#37101B`）。toon 是 MULTIPLY 骨架，这里给的是**最终色**，内部会除以 `hair_color` 换成 ramp 暗端 | 同上 |
| `hair_ring_color` | `[0.18, 0.1, 0.14]` | RGB 0~1 | 发丝「天使环」高光带的叠加色（ADD）。带位由世界 z 分带，位置遮罩另在 `hair_material()` 里硬编码 | 同上 |
| `bangs_groups` | 3 | 1~7（奇数更对称） | 刘海**中间组**缕数；左右外撇组恒 2 缕。**仅 `long` 生效** | `lib/hair.py:_bangs()` |
| `clump_count` | 7 | 5~9 | 后发束缕数（x0 步长固定 34mm，围绕中线对称）。**仅 `long` 生效** | `lib/hair.py:_clumps()` |
| `clump_width_scale` | 1.0 | 0.75~1.25 | 后发束半宽（默认 19mm）。**仅 `long` 生效** | `lib/hair.py:_clumps()` |
| `clump_thickness_scale` | 1.0 | 0.8~1.2 | 后发束厚度（默认 9mm，决定沟壑深度上限）。**仅 `long` 生效** | `lib/hair.py:_clumps()` |
| `ahoge_length_scale` | 1.0 | 0.6~1.4 | 呆毛沿轨迹长度（从发根拉伸）。**仅 `long` 生效** | `lib/hair.py:_ahoge()` |
| `ahoge_thickness_scale` | 1.0 | 0.7~1.3 | 呆毛半径（全宽 = 2×半径）。**仅 `long` 生效** | `lib/hair.py:_ahoge()` |
| `twin_tails` | `false` | true/false | 是否加双马尾（现网无，默认关；开时加 2 条下垂发束）。**仅 `long` 生效** | `lib/hair.py:_twin_tails()` |

## outfit（7 键）

| 键 | 现值 | 取值范围（建议） | 影响什么 | 接线位置 |
|---|---|---|---|---|
| `shirt_color` | `[0.93, 0.93, 0.95]` | RGB 0~1 | 衬衫底色（**未接线**，在 `lib/look.py` 里） | `lib/look.py:321` |
| `skirt_color` | `[0.072, 0.105, 0.26]` | RGB 0~1 | 裙子藏青底色（**未接线**） | `lib/look.py:324` |
| `skirt_length` | 0.65 | 0.55~0.72 | 裙摆最低 z（裙腰 1.045 固定，向下线性拉伸；同时改裙截面指数回落区间） | `lib/outfit.py:316,433` |
| `skirt_pleats` | 22 | 12~28 | 褶数；采样点数 = 褶数 ×8（`SKIRT_SEG`） | `lib/outfit.py:24` |
| `skirt_amplitude_scale` | 1.0 | 0.6~1.5 | 褶幅倍数（峰谷差 ≈ 2×amp，默认 25.9mm） | `lib/outfit.py:441` |
| `sleeve_length` | 1.11 | 1.05~1.18 | 袖口末端 z（卷边环跟着走） | `lib/outfit.py:196` |
| `collar_v_depth` | 0.022 | 0.012~0.03 | 前领相对后领的下降量（V 深；默认实测 18.5mm） | `lib/outfit.py:259` |

## render（5 键，**本轮只登记、未接线**）

`outline_px` 3.5 / `skin_pos_mid` 0.62 / `skin_pos_light` 0.68 /
`key_energy` 49.0 / `rim_energy` 80.0。

现值取 `lib/look.py:30-32` 与 `lib/shots.py:15,19`。本轮 `lib/look.py` / `lib/shots.py`
被像素段搜索占用，**没有接读取逻辑** —— 改动这五个键目前对渲染无影响，
等渲染层那一轮再接（届时可与 `optio` 的 `outline_px` / `skin_pos_*` / `rim_energy` 合并口径）。

## 默认值逐位一致的口径

改动后实测（本机）：

| 探针 | 无 `profile.json` | `profile.json` 存在且全默认 |
|---|---|---|
| `a1_hand_probe`（39 行） | diff 空 | diff 空 |
| `a2_face_probe`（14 行，含像素统计） | diff 空 | diff 空 |
| `a4_fit_probe`（30 行） | diff 空 | diff 空 |
| `d_probe`（22 行） | diff 空 | diff 空 |
| `b_probe`（58 行） | diff 空 | diff 空 |

`d_probe` 的 D5 判据把 `pleats = 22` 写死在探针里，改 `skirt_pleats` 后该判据
（`amp22` / 峰谷差）**失效**（DFT 阶次与真实褶数不符）；此时以 `seg = SKIRT_SEG`
（22 褶 → 176、16 褶 → 128）与 `a4` 的 `Outfit z_min`（0.650 → 0.60）为准。