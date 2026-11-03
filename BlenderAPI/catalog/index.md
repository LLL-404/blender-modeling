# Blender API 目录

由 `gen_catalog.py` 在运行中的 Blender 内扫描生成，**不是手抄文档**。

| 项 | 值 |
|---|---|
| Blender | 5.2.2 LTS |
| binary | `D:\Program Files\Blender Foundation\Blender 5.2\blender.exe` |
| 生成时间 | 2026-11-03T15:18:36 |
| factory_startup | True |
| 渲染引擎 | BLENDER_EEVEE |
| 修改器类型 | 83 |
| bmesh 算子 | 83 |
| 节点类型 | 562 |
| 操作符 | 1129 |

## 分域

| 文件 | 内容 |
|---|---|
| [01_env.md](01_env.md) | 渲染引擎、色彩管理、EEVEE 旋钮、图像格式 |
| [02_types.md](02_types.md) | 核心类型的属性表（Object/Mesh/Material/…） |
| [03_modifiers.md](03_modifiers.md) | 修改器与约束的完整类型枚举 |
| [04_bmesh.md](04_bmesh.md) | bmesh 算子及签名首行 |
| [05_nodes.md](05_nodes.md) | 着色/几何/合成/函数节点清单 |
| [06_ops.md](06_ops.md) | 操作符清单（含 headless 可用性提示） |
| [07_gltf.md](07_gltf.md) | glTF 导出参数 |

> 判读原则：**目录只证明「存在」，不证明「能用」**。
> 无头可用性见 `../bapi/` 的封装与 `../selftest.py` 的实测。
