# 外观旋钮层：把人手工调风格的常量外置成 `params/profile.json`

场景：项目叫「程序化生成」，但实际只有 `cfg.py` 的少量参数外置，`lib/` 里还有上千个浮点字面量。
用户要求先做一层"外观旋钮"：抽出 30~50 个语义明确、改它就是在换风格的高价值参数，
**默认值必须等于现值，文件不存在时行为逐位相同**。截面数据表（HEAD/TORSO/FOOT_ROWS）
与算法系数（混合指数、exp 系数）不抽。

## 1. 与 `optio` 的分工

| 层 | 文件 | 谁改 | 何时变 |
|---|---|---|---|
| `lib/optio.py` | `opt/best.json`（几何段 / pixel 段） | 搜索器 | 跑搜索时 |
| `lib/profile.py` | `params/profile.json`（appearance/hair/outfit/render 四组） | 人 | 手工调风格 |

两套并存、互不替代。共同点是**调用点给「引入前字面量」当默认值**，读盘/解析/键缺失/类型不符一律回退、永不抛异常。

`lib/profile.py` 的最小实现：

```python
import json, os
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REL = os.path.join("params", "profile.json")
_cache, _cache_path = None, None

def profile_path():
    env = os.environ.get("PM_PROFILE")
    if env:
        return env if os.path.isabs(env) else os.path.join(_PROJECT_ROOT, env)
    return os.path.join(_PROJECT_ROOT, DEFAULT_REL)

def _read():
    global _cache, _cache_path
    path = profile_path()
    if _cache is not None and _cache_path == path:   # 缓存必须绑定路径
        return _cache
    doc = {}
    try:
        with open(path, "r", encoding="utf-8") as f:   # Windows 默认 gbk 会炸
            raw = json.load(f)
        if isinstance(raw, dict):
            doc = raw
    except Exception:
        doc = {}
    _cache, _cache_path = doc, path
    return _cache
```

`PM_PROFILE` 让临时 profile 与正式文件隔离：放 `params/_tmp/`（用完删），相对路径按项目根解释。

## 2. 验收核心：三段式快照 diff

"默认值逐位一致"必须用快照证明，不是"看起来没变"：

1. **改前快照**：改动之前，用改动前的代码跑探针，`grep '^\[probe\]' > before_*.txt`（a1/a2/a4/d_probe/b_probe 各一份）。
2. **接线后、不建 JSON**：只改代码，`params/profile.json` 不存在 → 跑同样探针 → diff **必须为空**。
   这一步证明的是"接线本身没有改变行为"（包括 import 顺序、函数内多读了一次 profile 等）。
3. **建全默认 JSON**：`profile.json` 里每个键都写成现值 → 再跑一遍 → diff **仍必须为空**。
   这一步证明的是"默认值抄对了"。

只做 3 与 3 比、或只做 2 与 2 比，都是无效自证。三条探针（a1/a2/a4/d_probe）+ 骨架探针（b_probe）
全空才算过；本项目实测 39/14/30/22/58 行全部零差异。

## 3. 模块级常量 vs 函数体内现读

```python
_DEFAULT_HEIGHT = 1.62                      # 引入旋钮前的字面量
HEIGHT = profile.get("appearance.height", _DEFAULT_HEIGHT)   # 兼容旧引用
def height():                                # 需要"调用时读"的走函数
    return profile.get("appearance.height", _DEFAULT_HEIGHT)
```

判据：**同一进程会不会被反复重建**（搜索器、探针多次评估）→ 会，就在函数体内读；
模块级常量只留给 `import` 时定型也无妨的量（如环采样段数 `SKIRT_SEG = 褶数 × 8`）。

注释要写清"`HEAD` 是 import 时定型的快照，需要现读请用 `head_rows()`"，
否则后续调用点会误以为 `from head import HEAD` 会跟随旋钮。

## 4. 默认路径必须短路，不能"公式反算等于默认"

现网值往往是从公式反算出来的近似：`head_to_body_ratio = 1.62/(0.2344*1.063) = 6.505`，
代回公式得 `1.06295...` 而不是 `1.063` —— 乘回表会让几何差 0.05%，破坏逐位一致。

```python
def _head_scale():
    h = profile.get("appearance.height", _DEFAULT_HEAD_TOP)
    r = profile.get("appearance.head_to_body_ratio", _DEFAULT_HEAD_TO_BODY_RATIO)
    if h == _DEFAULT_HEAD_TOP and r == _DEFAULT_HEAD_TO_BODY_RATIO:
        return _DEFAULT_HEAD_SCALE          # 默认短路，不许走公式
    return max(0.6, min(1.6, (h / r) / _HEAD_RAW_LEN))
```

同类的浮点坑：`1.328 - 0.020 != 1.308`、`0.034 * 3 != 0.102`、
`0.950 - (0.950 - z) != z`。默认分支直接返回原字面量/原表达式，非默认才走重算。

## 5. ×1.0 精确，减法/重映射不精确

| 操作 | 默认 1.0 时 | 结论 |
|---|---|---|
| `rx * k` | `x*1.0 == x` 严格成立 | 可以直接乘 |
| `widths = [w * k ...]` | 同上 | 可以直接乘 |
| `z = 0.425 + (z-0.425)*k` | 不等（差 1 ulp） | 必须 `if k != 1.0:` 才应用 |
| 重映射裙长 `1.045 - (1.045-z)*kz` | 同上 | 同上 |

## 6. 序列/类型校验的坑

`_coerce` 不能只拿 `default[0]` 当原型：颜色默认值若写成 `[0,0,0]`（int 元素），
`0.115` 会被 `int(round())` 静默变成 `0`。正确做法：

- 先比长度：`len(raw) != len(default)` → 回退；
- 逐项按 proto 校验：`int` 原型只收 `int`（不接 float），`float` 原型接 int/float，`bool` 必须先于 int 判断；
- 元素类型不符 → 抛给 `get()` 统一回退 default。

## 7. 一个键改了，所有派生量都要跟着重算（实测 bug）

`height` 与 `head_to_body_ratio` 共同决定 `sz()`：`scale = (h/r)/raw_len`、`shift = h - (anchor + raw_len*scale)`。
只改 ratio 时，如果 `_head_shift()` 的短路条件只判 `h == 默认`，它会返回旧 shift、
而 `_head_scale()` 已变 → 头顶实测 **1.6023 而不是 1.6200（偏 17.7mm）**。
修法：短路条件同时覆盖两个键。

**规则：改单个键要真跑一次探针看派生量**（头顶、头长、头身比），不能只看代码自洽。

## 8. 「只缩一部分」是保持同源的技巧

- `hand_scale` 只乘掌/指截面半径，**不动掌长与指长** —— `PALM_BOT_Z`、`joints_for()` 与 rig 指骨坐标因此仍与网格同源。若要缩放掌长，必须同时改 `joints_for()` 的基准函数，否则骨与网格分家。
- `foot_size_scale` 只缩 y 长与半宽，**不动 z** —— 脚底 `align_floor` 与踝柱接合都依赖 z。
- `leg_length_ratio` 以膝 `z=0.425` 为铰点只缩放膝以上，脚与踝不动。
- `arm_thickness_scale` 只乘截面半径，路径点（臂长/肘位）不动。

凡是"尺度"类旋钮，先问：**它缩了之后，还有谁按旧尺度推导坐标？**（骨架、探针、对手件的接合）

## 9. 探针里写死的参数会在旋钮改值后失效

`d_probe` 的 D5 把 `pleats = 22` 硬编码做 DFT；把 `skirt_pleats` 改成 16 后，
DFT 阶次与真实褶数对不上，`amp22 = 0 → diff = 0 → FAIL`。

这时不要改探针去凑，也不要据此判旋钮失效；用**能反映变化的量**交接：
`SKIRT_SEG = 褶数 × 8`（176 → 128）、`a4` 的 `Outfit z_min`（0.6494 → 0.5995）、
`Outfit verts`（9424 → 8656）。并在 README 写明"该判据在改此键后失效"。

## 10. 接线清单模板（照抄可避免漏项）

| 组 | 键 | 接线位置（本项目实测） |
|---|---|---|
| appearance | height / head_to_body_ratio | `cfg.py:13,49`、`lib/head.py:45-46,56-57` |
| appearance | head_width / face_width | `lib/head.py:112-113`（`head_rows()`；发帽也要改走 `head_rows()` 才跟随） |
| appearance | eye_spacing / eye_size | `lib/head.py:138`、`:143,285`（眼型外轮廓 + 虹膜/瞳孔/高光等比） |
| appearance | nose_depth / mouth_width | `lib/head.py:173`、`:174,367`（口宽要同时改 sculpt 的唇部高斯宽度） |
| appearance | ear_scale | `lib/head.py:401`（归一化基准 `0.0190*k` 必须同比，否则 r 不在 [0,1]） |
| appearance | shoulder/waist/hip | `lib/body.py:68-70` `torso_rows()`（梯形权重加权；`outfit._shirt` 也改走它） |
| appearance | leg_length_ratio / arm_thickness / foot_size | `lib/body.py:130,202,270` |
| appearance | hand_scale | `lib/hand.py:416` |
| hair | bangs_groups / clump_count / width / thick / ahoge / twin_tails | `lib/hair.py:111,114,115,149,207,208,223` |
| hair/outfit 颜色 | 4 个 RGB | **只登记不接线**（在 `lib/look.py`，若渲染层被并发占用） |
| outfit | skirt_length/pleats/amp、sleeve_length、collar_v_depth | `lib/outfit.py:26,196,259,316,433,441` |
| render | 5 个像素/灯光键 | 只登记，等渲染层那一轮接（`look.py` / `shots.py`） |

## 11. 并发场景下的做法

- 只改任务清单里的文件；**不跑渲染入口**（会与像素段的 `out/` 撞、抢 Blender 资源），只用探针拍快照。
- 探针若因对方改 `look.py` 而报错：等 30 秒重试一次，仍失败就只报"该探针受并发影响未测"，**不要去改别人的文件**。
- `a2` 的像素行会读 `out/m3_face_front.png`：若对方重渲会同步漂移，diff 非空时先看图片 mtime/哈希再归因。
- 临时 profile 用 `PM_PROFILE` 指向 `params/_tmp/`，验证完删除；正式 `profile.json` 全程不被污染。

## 12. 交付物

- `lib/profile.py`：`get(点路径, default)`（含 stop at 首个非 dict 层）、`reload()`、`all_params()`（扁平化便于打印/校验键数）、`profile_path()`、`active_source()`。
- `params/profile.json`：分组结构，**37 键**（appearance 16 / hair 9 / outfit 7 / render 5），JSON 不带注释。
- `params/README.md`：逐键「键名 / 现值 / 建议范围 / 影响什么 / `文件:行`」四张表 + 未接线键说明 + 零差异口径表。
- 项目 `README.md` 加一节（≤20 行）：怎么换 profile（`PM_PROFILE=...`）、怎么回滚（删文件或删键）、哪些键未接线。
- 总结：接线键数、逐文件 `file:line`、五条探针 diff 结果、换旋钮前后实测数字、未接线键与原因、`py_compile` 结果。