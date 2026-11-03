# BlenderAPI

headless Blender 5.2 的**程序化建模封装层**：`bapi/` 7 个子模块 + `catalog/`（机器扫描的 API 目录，
含修改器参数表与节点端口表）+ `selftest.py`（逐项实测）。2026-11-03 新增，`bapi.__version__ = "0.1.0"`
（`bapi/__init__.py:37`）。

**一句话**：把 `-b` 下能用、该用、坑在哪，封成一组「参数写错会响、返回值可断言」的函数；
并给出一份能自证可用的自测和一份反映本机真实安装的 API 目录。

## 这是什么 / 不是什么

| 是 | 不是 |
|---|---|
| headless（`blender -b --python`）里可用的建模/渲染封装：网格、修改器、材质、机位灯光、渲染、雕刻位移场 | **不是 Blender 插件**：不安装、不注册 addon，`sys.path` 加进 `BlenderAPI/` 就能 `import bapi` |
| 面向「可断言」：封装返回位移量、面数、粗糙度实测值（`bapi/__init__.py:12-13`） | **不替代 bpy**：没封编辑模式、真雕刻笔刷、UI、动画、节点编辑；这些仍要直接写 `bpy` |
| 数据层优先：84 个公开函数里只有 4 处 `bpy.ops` 调用（清场/渲染/落盘/glTF 导出），均已实测 | **不是建模应用框架**：没有统一 CLI、没有配置系统；直接 `import bapi` 按需调函数 |
| 自带可用性证据：`selftest.py` 36 项逐条打印 PASS/FAIL/SKIP + 实测数字；`catalog/` 是扫描产物不是手抄 | **不承诺跨 Blender 版本稳定**：只在 5.2.2 LTS 上实测过（见「已知边界」第 1 条） |

规模（2026-11-03 实测）：`bapi/` 8 个 `.py` 共 **1,621 行**（`__init__` 60 / `env` 92 / `obj` 138 /
`mesh` 264 / `mod` 220 / `mat` 311 / `shot` 260 / `sculpt` 276）；`gen_catalog.py` **866 行**
（15:18 版 315 行 → 19:52 版 866 行，新增修改器参数、节点端口、OCIO 色彩管理三段扫描）；
`selftest.py` 634 行、36 个自测项。

## 环境要求

| 项 | 要求 | 说明 |
|---|---|---|
| Blender | **5.2 LTS**（本机 `5.2.2 LTS`，hash `d13f752e3b9c`，built 2026-09-15） | 二进制默认 `D:\Program Files\Blender Foundation\Blender 5.2\blender.exe`；不用装 GUI |
| 运行方式 | `blender.exe -b --factory-startup --python <脚本>` | catalog 与 selftest 都必须跑在 **Blender 进程内**；用 `--python-exit-code 1` 把脚本异常映射成非 0 退出码 |
| 系统 Python | **不需要** | `bapi/`、`gen_catalog.py`、`selftest.py` 只用 Blender 自带 Python（本机 3.13.13）与标准库；不依赖 numpy/Pillow |
| 第三方包 | **无** | 全部 stdlib + `bpy`/`bmesh`/`mathutils` |
| 操作系统 | Windows 本机实测；无平台相关代码 | 路径是 POSIX/Windows 通用写法，仅本机未在其它系统验证 |

> 不要 `pip install bpy` 后用系统 Python 跑：`pip bpy` 的版本与安装的 Blender 不一致时，
> API 差异（`Image.pixels`、修改器默认值、`--factory-startup` 语义）会让封装层行为漂移。
> 本仓的约定与 `人物建模/README.md` 的「BlenderPy 注意事项」一致：一律用 `blender.exe -b --python`。

## 快速上手

两种跑法，都从 `bapi/__init__.py:15-24` 的用法段扩展：

**A. 写成一个脚本文件**（推荐，可复用、可进 git）：

```python
# my_probe.py —— 用 blender.exe -b --factory-startup --python my_probe.py 跑
import sys
sys.path.insert(0, r"D:\G\github\实用工具\Blender建模\BlenderAPI")
import bapi

bapi.env.reset()                                    # 清空场景（连默认立方体/灯/相机都不建）
ob = bapi.mesh.sphere(0.5, name="head")             # UV 球：482 顶点 / 512 面
bapi.mod.subsurf(ob, 2)                             # SUBSURF ×2 并烘进网格
bapi.mat.assign(ob, bapi.mat.principled("skin", base_color=(0.9, 0.7, 0.6)))
print(bapi.info())
```

**B. 不落文件，直接 `--python-expr`**（冒烟用）：

```pwsh
& "D:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup `
  --python-exit-code 1 --python-expr "import sys; sys.path.insert(0, r'…\BlenderAPI'); import bapi; bapi.env.reset(); ob = bapi.mesh.sphere(0.5, name='head'); bapi.mod.subsurf(ob, 2); bapi.mat.assign(ob, bapi.mat.principled('skin', base_color=(0.9, 0.7, 0.6))); print(bapi.obj.stats(ob))"
```

**实测（2026-11-03，同一条命令）**：退出码 0，无报错；返回对象
`verts=7938 / polys=7936 / materials=['skin'] / smooth_polys=7936 / modifiers=[]`（subsurf 已烘焙、
材质槽已挂上）；`bapi.info()` 回 `{'bapi': '0.1.0', 'blender': '5.2.2 LTS', 'engine': 'BLENDER_EEVEE',
'objects': 1, 'binary': 'D:\\Program Files\\…\\blender.exe'}`。

## 模块与关键函数

`bapi/__init__.py:39-45` 导入 7 个子模块；`__all__` 是 `env/obj/mesh/mod/mat/shot/sculpt`。
下表函数名全部来自各模块源码（不含 `_` 前缀的私有函数），`文件:行` 是该函数定义行。

| 模块 | 职责 | 公开函数（全部） |
|---|---|---|
| `env` | 清场、引擎、EEVEE 采样、色彩管理、分辨率、输出目录、帧范围 | `version` `reset` `clear_data` `engine` `eevee` `color_standard` `resolution` `out_dir` `frame` |
| `obj` | 对象创建/挂集合/合并/变换/包围盒/统计/删除 | `link` `new_object` `select_only` `delete` `stats` `bbox` `apply_transform` `join` `duplicate` |
| `mesh` | 顶点建面、超椭圆截面放样、管状扫掠、基本体、法线修复、焊接 | `from_verts_faces` `ring` `loft` `tube` `cube` `plane` `sphere` `cylinder` `resample_path` `recalc_normals` `shade_smooth` `merge_by_distance` `flip_normals` `non_manifold_edges` `flipped_faces` |
| `mod` | 修改器 + 烘焙进网格 + 常用形变封装 | `add` `bake` `subsurf` `smooth` `voxel_remesh` `displace` `shrinkwrap` `solidify` `bevel` `decimate` `mirror` `smooth_corrective` `clear` `explain` |
| `mat` | Principled 短名映射、sRGB 转换、诊断材质、三渲二、描边/轮廓光 | `srgb` `new` `socket_set` `emit` `principled` `diffuse` `assign` `diag` `toon` `outline` `rim_light` |
| `shot` | 世界/地面/灯光/机位/渲染/环绕/落盘/glTF 导出 | `world` `floor` `look_at` `area` `sun` `three_point` `camera_ortho` `camera_persp` `closeup` `setup` `render` `turnaround` `save_blend` `export_gltf` `render_views` |
| `sculpt` | headless 下的「笔刷」替代：位移场 + 量测 | `falloff` `weights` `to_group` `move` `inflate` `pinch` `flatten` `smooth_region` `scale_region` `roughness` `planarity` |

**重点函数**（写脚本最常碰的 12 个）：

| 函数 | 签名 / 语义 | 落点 |
|---|---|---|
| `env.reset(empty=True)` | 清场并返回场景；`empty=True` 连默认物体都不建 | `bapi/env.py:24` |
| `env.engine(name="BLENDER_EEVEE")` | 设渲染引擎；本机 5.2.2 `--factory-startup` 下枚举实测只有 `BLENDER_EEVEE` | `bapi/env.py:43` |
| `mesh.sphere(radius=1.0, seg=32, rings=16, …)` | UV 球；`seg`=经线数、`rings`=纬线数（含两极） | `bapi/mesh.py:142` |
| `mesh.ring(z, rx, ry=None, power=2.0, seg=48)` | Z 平面上超椭圆截面；`power=2` 椭圆、`>2` 越方 | `bapi/mesh.py:28` |
| `mesh.tube(points, radii, seg=16, up=(0,1,0))` | 沿折线放样管；`radii=[(rx,ry),…]` 与 `points` 等长 | `bapi/mesh.py:78` |
| `mod.add(ob, kind, strict=False, **kw)` | 加修改器并设属性；`strict=True` 时属性没设上就抛 `AttributeError` 并撤掉修改器 | `bapi/mod.py:54` |
| `mod.bake(ob, upto=None)` | 用 `evaluated_get()` + `meshes.new_from_object()` 把修改器栈烘进网格，**不调 `modifier_apply`** | `bapi/mod.py:72` |
| `mod.voxel_remesh(ob, voxel_size=0.002)` | 体素重网格，把拼接/自交的多个块焊成单一流形（selftest 实测 2 块→1 块） | `bapi/mod.py:131` |
| `mat.principled(name, **kw)` | 短名建 Principled 材质（`base_color`/`roughness`/`specular`/`subsurface`…）；未知键抛 `KeyError` | `bapi/mat.py:100` |
| `mat.diag(kind)` | 6 种诊断材质：`normal`/`ao`/`wire`/`silhouette`/`flat`/`uv` | `bapi/mat.py:150` |
| `shot.camera_ortho(angle=0, scale=1.9)` | 正交机位，`angle=0` 为正面（-Y 侧看向 +Y）；正交图可逐像素叠差 | `bapi/shot.py:123` |
| `shot.render(path, cam=None, w=None, h=None, samples=None)` | 渲一帧写盘，返回 `(路径, 字节数)`；全包 4 处 ops 之一 | `bapi/shot.py:177` |

- 坐标约定：**Z 轴向上、-Y 是正面**（`bapi/shot.py:4-8`）；渲染诊断材质全部自发光，不受灯光影响。
- 单位：全部是 **米**；selftest 输出里常换算成 mm。

## 实测：selftest

### 复跑命令

```pwsh
& "D:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup `
  --python-exit-code 1 `
  --python "D:\G\github\实用工具\Blender建模\BlenderAPI\selftest.py" 2>&1 |
  Tee-Object -FilePath "D:\G\github\实用工具\Blender建模\BlenderAPI\out\selftest.log"
```

退出码语义（`selftest.py:6-8`）：**0 = 全部 PASS**；有 FAIL 返回 1；SKIP 不算失败但会打印原因。
`--python-exit-code 1` 让脚本内的未捕获异常也映射成退出码 1，不会「报错但返回 0」。

### 本轮结果（2026-11-03，5.2.2 LTS）

| 项 | 值 |
|---|---|
| PASS | **36** |
| FAIL | **0** |
| SKIP | **0** |
| 退出码 | **0** |
| 耗时 | **3.23 s**（含 4 张诊断渲染 + 4 张 turnaround + glTF/.blend 落盘） |
| 日志 | `BlenderAPI/out/selftest.log`（4,964 B） |

36 项的覆盖分布：`env` 2、`mesh` 6、`obj` 3、`mod` 7、`sculpt` 6、`mat` 4、`shot` 8。
每项都打印实测值（例：`loft 圆柱 verts=66 polys=96`、`voxel_remesh 2 块 → 1 块，6570 面`、
`decimate 960→288 三角面`；渲染项还报像素亮度统计，如法线色的 `std=0.258`）。

### 首跑不是全绿：6 条 FAIL 的归因与处置

第一次跑（2026-11-03 18:36）是 **PASS=30 / FAIL=6 / SKIP=0，exit=1**。逐条查过后：
**1 条是真 bapi bug（已修），5 条是 selftest 判据自己写错（已按实测依据修正，未放宽判定强度）**。

| # | 首跑 FAIL 原文 | 归因 | 处置 |
|---|---|---|---|
| 1 | `mesh · loft 圆柱: AssertionError: 96` | 判据算错：两个环之间侧壁 32 面 + 两端各 32 个三角盖 = **96** 面；原判据写 `32*2+32*2=128` 没有几何依据 | 判据改为 `32*3`（`selftest.py` loft 项） |
| 2 | `mod · solidify / bevel / decimate: AssertionError: 512 → 256` | 判据用「面数」判 `DECIMATE.ratio`，而该 ratio 的口径是**三角形数**。实测 960 三角面 → 288 三角面（恰 0.30），但 288 个三角面装进了 **256 个面**（减面保留 32 个四边形） | 改为按三角面判 `0.30±0.02`（从「面数 < 50%」换成「三角面 = 30%±2%」，更贴近契约） |
| 3 | `mod · 未知属性不静默: TypeError: this type doesn't support IDProperties` | 判据想在 Modifier 上读日志。Modifier 不是 ID、不支持自定义属性（`bapi/mod.py:39-51` 已写明），日志按设计挂在 **Object** 上 | 判据改读 `ob.get("bapi_mod_unset")` |
| 4 | `sculpt · move 限轴: AssertionError: `（空消息） | 判据把笔刷中心放球心、半径又等于球半径 → 所有顶点落在 falloff 边缘（权重≈0），位移必然≈0；且标题写「限轴」却没传 `axis` | 中心改球顶 `(0,0,0.3)`、半径 0.5、标量位移 0.1 + `axis=("X",)`；实测 `位移 0.100 m，Y 轴未受影响` |
| 5 | `mat · toon 节点链: AssertionError: ['BSDF_DIFFUSE', 'EMISSION', 'OUTPUT_MATERIAL', 'SHADERTORGB', 'VALTORGB']` | 判据查 `'SHADER_TO_RGB'`，但 5.2.2 运行时 `node.type` 实际是 **`'SHADERTORGB'`**（节点链本身是对的：Diffuse→ShaderToRGB→ColorRamp→Emission 全在） | 改查 `'SHADERTORGB'` |
| 6 | `shot · turnaround 四视图: AttributeError: 'RenderSettings' object has no attribute 'view_settings'` | **真 bapi bug**：`shot.setup()` 把 `env.resolution()` 返回的 `RenderSettings` 当成 `Scene` 用，`sc.view_settings` 必然不存在。之前只有这个自测走到 `setup()`，所以一直没暴露 | 修 `bapi/shot.py:165-174`：`sc = bpy.context.scene` 后再设 `view_settings`；复跑 4 张图最小 26,507 B |

不遮掩口径：除这 6 条外首跑的 30 条本来就是 PASS；修正后的 36 条**没有一条是被放宽到「必然通过」**的阈值
（第 2 条甚至从「面数过半」收紧成「三角面比例精确到 ±2%」）。

### 产物落点

| 产物 | 说明 | 大小（本轮） |
|---|---|---|
| `out/selftest.log` | 完整 stdout（含每条 PASS 的实测值） | 4,964 B |
| `out/selftest/diag_{normal,silhouette,ao,wire}.png` | 4 张诊断渲染（法线色/剪影/AO/线框） | 16,520 ~ 36,104 B |
| `out/selftest/turn/turn_{000,090,180,270}.png` | 四视图 turnaround | 26,507 ~ 29,613 B |
| `out/selftest/probe.glb` | glTF 导出成品 | 5,160 B（约 5.0 KB） |
| `out/selftest/selftest.blend` | `.blend` 落盘 | 91,354 B（约 89 KB） |
| `out/selftest/selftest.blend1` | 上一次 `.blend` 的备份（Blender 自动写） | 91,344 B |

`out/` 已在 `.gitignore` 内（`out/` 整个被忽略），不要求入库；诊断图可重跑再生。

## catalog：API 目录

| 项 | 值 |
|---|---|
| 来源 | `gen_catalog.py` 在运行中的 Blender 内扫描生成，**不是手抄文档**（`gen_catalog.py:1-16`） |
| 生成时间 | **2026-11-03T19:52:21**（`catalog/index.md`） |
| Blender | **5.2.2 LTS**，binary `D:\Program Files\Blender Foundation\Blender 5.2\blender.exe`，`factory_startup=True` |
| 产物 | `catalog/` 共 9 个文件：`index.md` + 7 个分域 md + `api.json`（781,564 B） |
| 覆盖统计 | 修改器 **83 类 / 1219 条参数**；节点 **540 个可实例化 / 2526 个 socket**（另 22 个不可实例化）；bmesh 算子 83；操作符 1129；核心类型 24 类 |
| 分域 | `01_env` 引擎/色彩（**view_transform + look 按 view_transform 分组**）/EEVEE 旋钮、`02_types` 核心类型属性表、`03_modifiers` 枚举 **+ 每类参数表**、`04_bmesh` 算子签名、`05_nodes` 清单 **+ 每节点端口表**、`06_ops` 操作符（sculpt/view3d 标 ⚠）、`07_gltf` 导出参数 |
| 重生成命令 | `blender -b --factory-startup --python "D:\G\github\实用工具\Blender建模\BlenderAPI\gen_catalog.py"`（约 40 s，2026-11-03 19:52 重跑过） |

**怎么读这份目录**：`03_modifiers.md` 查修改器参数名，`05_nodes.md` 查节点端口名，`api.json` 查结构化全量（含默认值/枚举/范围）。名单类信息（`06_ops` / `04_bmesh`）只证明「存在」。

**口径**（原文在 `catalog/index.md`）：

> **目录只证明「存在」，不证明「能被 headless 调用」。** 参数与端口是从真实实例上读的
> （试建 → 读 RNA → 删除），比名单可信；但 `bpy.ops` 的 poll 结果仍要看 `bapi/` 与 `selftest.py`。

具体到本目录有六个使用陷阱，全部实测过：

1. **`view_transform` / `look` 的 RNA 枚举是假的**：`bl_rna.properties[...].enum_items` 只返回一条占位
   `NONE`，而实际当前值是 `AgX`。**已解决**：`01_env.md` 改从 OCIO 的 `displays:` 段读，再逐个写回验证，
   现在给出 9 个真实 view_transform。**别再照 `enum_items` 判断可用值。**
2. **`look` 的可用性由 `view_transform` 决定**：OCIO 里共 27 个 look，但 `AgX` 下只有 `AgX - *` 那 9 个能写；
   切到 `Filmic` / `Standard` / `Raw` 只剩 Filmic 那 7 个。写错直接 `TypeError`。`01_env.md` 已按
   view_transform 分组列出。
3. **修改器的参数不在 `bpy.ops` 里**：`bpy.ops.modifier` 命名空间在 5.2 实测 **0 条**。加修改器一律
   `ob.modifiers.new(name, 'SOLIDIFY')` 再赋属性，属性名查 `03_modifiers.md`。
4. **节点端口名带空格**：Principled BSDF 的是 `inputs["Base Color"]`，不是 `inputs["base_color"]`。
   `05_nodes.md` 的端口表就是按真实名字写的，照抄即可。
5. **`nodes.new()` 有 22 个类型会报 `Node type … undefined`**：它们是基类（`ShaderNode`）、
   `node_tree` 类型（`ShaderNodeTree`）和 `CustomGroup`，本来就没有实例，不是扫描失败。
   清单列在 `05_nodes.md` 的「不可实例化」一节。
6. **ops 清单 ≠ headless 可用清单**：`06_ops.md` 给 `sculpt`/`view3d` 标了 ⚠，但其余命名空间里同样可能有
   poll 失败的操作符；bapi 的取舍是「只在没有数据层替代的 4 个入口用 ops」。

另外：**目录绑定这一次安装**。换 Blender 版本、装扩展（如 Cycles 以 addon 形式注册引擎）后必须重扫，
否则会拿旧枚举当可用值。

### 扫描器实现要点（改 `gen_catalog.py` 前必读）

修改器参数与节点端口都**挂在实例上**，不在类型上（`Modifier` 基类只有 13 条通用属性），所以扫描方式是
「试建 → 读 RNA → 删除」：

| 扫描对象 | 必须造什么才能读全 | 覆盖结果 |
|---|---|---|
| 修改器 | 4 种宿主：`mesh` / `curve` / `grease_pencil` / `volume`（`MESH_TO_VOLUME`、`VOLUME_DISPLACE` 只在 volume 上能建） | 83/83，0 失败 |
| 节点 | 4 种 tree：shader / geometry / **compositor（`node_groups.new(..., 'CompositorNodeTree')`）** / texture | 540/562，另 22 个不可实例化 |
| 色彩管理 | OCIO `config.ocio` 的 `displays:` / `looks:` 段 + 逐值写回验证 | view 9 个 / look 27 个 |

> **CRLF 坑**：OCIO 配置是 CRLF。必须用 `splitlines()` 或 text mode 读，`split('\n')` 会留下行尾 `\r`，
> 让 `re.match(..., '$')` 匹配不上（Windows 的 text mode 会自动转换所以侥幸不报错，**Linux 上必踩**）。

## 已知边界（诚实清单）

1. **只实测过一个版本**：Blender 5.2.2 LTS。封装层用「属性不存在就报错/记录」当版本漂移的防线，
   但这只是防线不是保证——换版本请先复跑 `selftest.py`。
2. **参数校验强度不统一**（有意，但要知道）：
   - `mat.principled` 未知 socket → 抛 `KeyError` 并列出可用输入（`bapi/mat.py:117-121`）；
   - `mat.diag`、`mat.toon` 未知类型/参数 → 抛 `ValueError`；
   - `mod.add` 未知属性 → **默认只记录在对象上**（`ob["bapi_mod_unset"]`，`bapi/mod.py:39-51`），
     传 `strict=True` 才抛 `AttributeError` 并撤掉修改器；
   - `env.eevee()` / `env.color_standard()` 对版本差异参数用 `hasattr` 守卫（`bapi/env.py:56,58,67`），
     **可能静默不生效**——检查时以返回值/实测为准。
3. **`sculpt` 是位移场近似，不是真笔刷**：`bpy.ops.object.mode_set(mode='SCULPT')` 在 `-b` 下能成功，
   但 `bpy.ops.sculpt.brush_stroke.poll()` 抛 `RuntimeError: context is incorrect`，且 `-b` 下
   `bpy.data.brushes` 只有一个 `Draw`——**一笔都落不下去**（`bapi/sculpt.py:4-9` 实测记录）。
   因此这里用「权重 × 方向」的顶点位移场替代：可复现、可参数化、可喂搜索器，但没有笔刷动态、对称、
   Dyntopo、笔刷预设。所有 `center/radius` 是**对象本地坐标**（`bapi/sculpt.py:19`），带
   `matrix_world` 的对象先 `obj.apply_transform()`。
4. **`obj.join()` 不是完整合并**：数据层自拼，只保留顶点/面/材质槽/平滑标记
   （`bapi/obj.py:88-131`），**不搬 UV、顶点色、形态键、自定义法线**。需要完整数据合并的场景别用它。
5. **`obj.apply_transform()` 会改动共享网格**：`me.transform(matrix_world)` 直接写网格数据，
   若网格被多个对象共享会一起被改（`bapi/obj.py:75-85` 已注明）。
6. **`mesh.tube` 的标架是逐点近似**：每个点用固定参考上向量叉乘算局部标架（`bapi/mesh.py:101-105`），
   不是严格的平行传输；极端扭转/回折路径未做验收。
7. **引擎面很窄**：本机 `scene.render.engine` 枚举实测只有 `BLENDER_EEVEE`（5.2.2 `--factory-startup`），
   所以 `env.engine()` 实际只能设这一个；`mat.toon` 的 Shader to RGB 只在 EEVEE 有效
   （Cycles 下恒黑，是引擎约束不是参数问题，`bapi/mat.py:228-233`）。
8. **4 处 ops 调用点**：`env.reset()`（`bpy.ops.wm.read_factory_settings`）、`shot.render()`
   （`bpy.ops.render.render`）、`shot.save_blend()`（`bpy.ops.wm.save_as_mainfile`）、
   `shot.export_gltf()`（`bpy.ops.export_scene.gltf`）。全部在 4 个对应的自测项里实测通过；
   但 `save_blend()` **会改变当前文件的路径**（`bapi/shot.py:224-228`），批量渲染后别随手调。
9. **selftest 覆盖不等于全部函数实测**：36 项覆盖了大部分常用路径，但 84 个公开函数里仍有
   **17 个没有直接落点**（也未在其它项里被间接调用）：`env.clear_data`、`env.frame`、
   `obj.select_only`、`obj.delete`、`mesh.resample_path`、`mesh.shade_smooth`、`mod.mirror`、
   `mod.smooth_corrective`、`mod.explain`、`mat.diffuse`、`mat.outline`、`mat.rim_light`、
   `shot.sun`、`shot.camera_persp`、`shot.closeup`、`shot.render_views`、`sculpt.scale_region`。
   用这些函数前先自己冒烟一遍。

## 与现有管线的关系

**结论：新层尚未被现有管线引用。** 2026-11-03 在本仓根扫描 Python 文件：

```pwsh
Get-ChildItem -Recurse -File -Filter *.py |
  Select-String -Pattern 'import bapi|from bapi'
# BlenderAPI\selftest.py:23: import bapi
# BlenderAPI\selftest.py:24: from bapi import env, mat, mesh, mod, obj, sculpt, shot
# BlenderAPI\bapi\__init__.py:19: import bapi
```

只有 3 行，且全部在 `BlenderAPI/` 内部：selftest 自己导入 + `__init__.py` docstring 里的用法示例
（后者不是可执行导入）。即 `人物建模/`、`stardust/`、`blender-rig/`、`Blender体检/` 全部 **0 命中**。

- `人物建模/lib/`（18 个模块，含新增的 `appearance.py`）有自己的 `meshkit`/`mats`/`look`/`shots` 等实现，
  与 `bapi` **没有 import 关系**，能力面部分重叠（网格、材质、机位渲染），但两套各自独立。
- 因此当前不要把 `bapi` 当成「人物建模的下一版」：它是 2026-11-03 新起的一层，可用性证据只有
  本目录的自测；要接管现有管线，前置条件是先在本机复跑 `selftest.py` 全绿，再按模块逐个替换并保留旧实现。

## 维护

| 场景 | 动作 |
|---|---|
| 改 `bapi/` 任何一个模块后 | 必须复跑 selftest（命令见上），确认 `PASS=36 FAIL=0 SKIP=0`、退出码 0，再更新 `out/selftest.log` |
| selftest 报 FAIL | **先判归因**：是封装 bug 还是判据写错（本轮 6 条里 1 条真 bug、5 条判据错）。修判据要给出实测依据，禁止把阈值放宽到「必然通过」 |
| 换 Blender 版本 / 装扩展后 | 先 `blender … --python gen_catalog.py` 重扫 catalog，再跑 selftest；旧 catalog 的枚举可能已失效 |
| 改 `catalog/` 的扫描逻辑后 | 跑 `python verify_catalog.py` 做独立核对（48 项判据：产物齐全、未改分域逐字节不变、SOLIDIFY/Principled 数值、view/look 分组、md 反引号配对）。**不要只看「生成成功」**。回归对比需要 `catalog_bak/` 基线，没有就跳过那 7 项 |
| 新增封装函数 | 同时加自测项（每项都要打印可测数值），并更新本 README 的模块函数表 |
| 文档口径 | 「4 处 ops」与 `bapi/__init__.py:8-9`、`bapi/env.py:4-7` 两处 docstring 保持同步（2026-11-03 已从「三处」校正为「四处」并点名 `shot.save_blend()`） |

变更记录：

| 日期 | 事件 |
|---|---|
| 2026-11-03 | `bapi 0.1.0` 建立；catalog 扫描（15:18）；selftest 首跑 30 PASS / 6 FAIL / 0 SKIP（exit 1） |
| 2026-11-03 | 修 `shot.setup()` 的 `view_settings` 真 bug；按实测依据修正 5 条 selftest 判据；复跑 **36 PASS / 0 FAIL / 0 SKIP（exit 0，3.23 s）** |
| 2026-11-03 | 补本 README；校正两处 docstring 的 ops 数量口径（三→四）；未重生成 catalog |
| 2026-11-03 | **catalog 补全**（`gen_catalog.py` 315 → 866 行）：新增修改器参数扫描（83 类 / 1219 条）、节点端口扫描（540 个 / 2526 socket）、色彩管理改从 OCIO 读（view_transform 9 个、look 27 个按 view_transform 分组）。`api.json` 392,771 → 781,564 B；`03_modifiers.md` 1.6K → 71.7K；`05_nodes.md` 14.7K → 64.6K。外部核对 39 项全过，未改动的 4 个分域逐字节不变 |
