# 按对象限制描边壳的世界厚度（Solidify per-object cap）

适用：三渲二描边（反法线 Solidify 壳）已按「恒定像素宽」实现，但某个部件
（手、手指、耳、饰件）的壳在**大 mm/px 机位**上世界厚度变大，戳出相邻部件的
轮廓，视觉上像「接口断了 / 一圈黑横断」。

---

## 1. 根因：像素恒定 ⇒ 世界厚度随机位漂移

按视图换算的写法（本项目 `lib/look.py:set_outline_px`）：

```python
mm_per_px = ortho_scale / float(res_y)
m.thickness = px * k * mm_per_px          # k = optio 注入的比例
```

后果实测（同一份 3.5px）：

| 机位 | mm/px | 壳世界厚度/侧 |
|---|---|---|
| 全身 1.78 / 900 | 1.98 | **6.92mm** |
| 手部近景 0.16 / 900 | 0.178 | 0.62mm |

全身机位下 6.92mm 的壳把「与前臂几乎同宽的手」撑出一圈黑。
**不要靠缩小部件本体规避**（会破坏上游已验收的尺寸），要在描边层截断。

## 2. 实现：换算后 min 一次，默认参数必须不改行为

```python
HAND_OUTLINE_CAP = 0.0035      # 米/侧，模块级常量，注释里写实测推导

def add_outline(ob, mat, thickness=0.005, thickness_cap=None):
    if thickness_cap is not None:
        thickness = min(float(thickness), float(thickness_cap))
    ...

def set_outline_px(objs, mods, ortho_scale, res_y, base_px=3.0,
                   per_obj_px=None, per_obj_cap=None):
    ...
    th = px * k * mm_per_px
    if per_obj_cap:
        cap = per_obj_cap.get(ob.name)
        if cap is not None:
            th = min(th, float(cap))
    m.thickness = th
```

要点：
- **两处都要 min**：`add_outline` 只是初始值兜底；真正生效点在 `set_outline_px`，
  否则后续按机位重设会把它顶回去。
- **默认 `None`** ⇒ 不传就逐位等于旧行为（无配置回退路线必须保留）。
- 用 `dict[对象名] -> cap`，与既有 `per_obj_px` 同构，各入口只加一行。
- cap 上限怎么定：取「相邻部件轮廓余量」与「本部件最小半宽」两者的较小值。
  例：掌/前臂同宽、Body 壳 6.79mm/侧 ⇒ 手壳 ≤3.5mm 即落进前臂壳内；
  手指直径 8mm ⇒ 壳 ≤ 半径 4mm 才不会把指缝描边吞成黑棍。

## 3. Blender API 坑

- **`SolidifyModifier` 不支持 IDProperties**：`m["outline_cap"] = 0.0035` 直接
  抛 `TypeError: this type doesn't support IDProperties`。cap 只能走函数参数
  （或自己维护 `{mod: cap}` 字典），不要试图把配置挂在 modifier 上。
- 临时验证脚本**不能调 `shots.render()`**（它固定写 `out/`）；自己设
  `sc.render.filepath = os.path.join(TMP_DIR, name)` 再 `bpy.ops.render.render(write_still=True)`。

## 4. 验收：几何为主判据，像素只作旁证

**硬判据（跨机位不变）**：含壳的部件外表面不得超出相邻部件的含壳外表面。

```
Hands 腕带（z ∈ [WRIST_Z−5mm, WRIST_Z+5mm]，只取该侧）含壳横向半宽
  ≤ Body 前臂同带含壳横向半宽
```

实测（右手）：

| 项 | before | after |
|---|---|---|
| 壳世界厚度 | 6.922mm/侧 | 3.500mm/侧 |
| 壳 evaluated 实际外扩 | +7.16mm | +3.44mm |
| 手 含壳横向半宽 | 21.78mm | 18.05mm |
| 前臂 含壳横向半宽 | 21.24mm | 21.24mm |
| 差 | **+0.54 FAIL** | **−3.19 PASS** |

做法：`ob.evaluated_get(depsgraph).to_mesh()` 取含壳顶点；把 modifier
`show_viewport` 关/开各取一次即得「壳前/壳后」两套口径（同一条几何规则：
探针索引与量测对象必须同尺度）。

**像素旁证**：近景机位（cap 不生效）应当**逐像素零差异**，这是「没伤到指缝描边」
最硬的证据 —— 实测 620×900 全图 `max|Δ|=0`。
只在全身机位（cap 生效）才可能出现像素变化，且应集中在部件边界框内
（本项目变亮像素 448/643 个全部落在双手腕 bbox，其余画面 mean|d|=0.02）。

## 5. 像素判据的三个陷阱（都会把正常形态误判成缺陷）

1. **「两侧被前景夹住」不足以定义横断**：手与掌之间的**背景透视缝**同样两侧
   是前景、宽度 11~15px。判据必须再加「上下 bh 行同 x 区前景占比 ≥0.7」
   ——真实横断是上下都被皮肤夹住，透视缝上下也是暗的（实测前景比例 0.00、
   段内亮度中位 = 背景色 50）。
2. **腕部带不要含手指区**：腕部带取 `[0.40h, 手指区起点−20px)`。指根处的指缝
   描边本身就是 3~5px 宽的横向暗段，混进腕部带会直接误报（本会话实测 5px 假值）。
3. **指缝不能说「0 条」就判缺陷**：全身 560px 宽的图里每根手指仅约 3px 宽，
   低于「段」判据下限，指缝本来就分辨不出。小图（w ≤ 600）应退回固定口径并
   如实标注「本机位不可分辨」，不要让探针把分辨率不足伪装成「指缝没了」。

## 6. 最小对照场景（归因快、不抢 `out/`）

另写一个 `_stageB/tmp/` 下的临时入口：只建 Body + Hands（不建头/发/裙），
挂同一套壳，命令行参数 `cap=`，渲 `*_before.png` / `*_after.png` 到 tmp 目录。
好处：
- 单变量（只有 cap 不同），像素差可逐位归因；
- 不触发他人正在改的 `hair/outfit/head` 并发风险；
- 不覆盖 `out/` 里的正式产物，`out/` 的同一入口仍可另跑一次做「真入口已生效」的旁证
  （对比 before/after 的差异 bbox 证明改动只落在双手腕）。

## 7. 报告口径

必须分开写清三件事，否则领导会以为「没修好」：
- **几何戳出量**（+0.54 → −3.19mm，机位无关）；
- **像素横断宽度**（近景 0px、全身 2px 且是描边线本身）；
- **任务给的原始数字来源**（本会话：13px 经核查是拇指/掌间透视缝，
  上下前景比例 0.00，不是描边壳）——当任务断言与实测不符时，先纠偏再交付，
  不要为了对齐数字而改判据。