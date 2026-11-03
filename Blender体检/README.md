# Blender体检

对任意 `.blend` 一条命令渲出 **16 个环绕视角 + 顶视 + 拼版总览图**，供 AI 或人校对建模成果。配套一套「渲染 → AI 读图挑错 → 脚本化修复 → 复渲复检」的自检闭环协议。

与 `Word体检` 同款定位：体检不治病，报告开出来，能开药方的（可脚本修的）才动手。

## 快速上手

```bash
# 最常用：对模型跑 16 视角体检（产物落在本工具 out/<模型名>/ 下）
bash "D:/G/github/实用工具/Blender建模/Blender体检/check.sh" "D:/G/game/games/stardust/tools/blender/stardust_props.blend"

# 指定参数
bash check.sh model.blend --views 8 --elevation 15 --engine workbench --res 1024

# 产物放别处（仅限工具目录或模型所在目录内）
bash check.sh model.blend --out "D:/some/dir"
```

- Blender 自动探测 `D:/Program Files/Blender Foundation/*/blender.exe`，探测不到时用环境变量 `BLENDER_EXE` 指定。
- 引擎默认 EEVEE；headless 下 EEVEE 出问题时换 `--engine workbench`（快、纯看形）或 `--engine cycles`（慢、看质感）。

## 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--views N` | 16 | 环绕视角数量（每 360/N 度一张） |
| `--elevation 度` | 20 | 环绕相机仰角 |
| `--engine` | eevee | `eevee` / `workbench` / `cycles` |
| `--res N` | 512 | 渲染边长（正方形，也是拼版单元尺寸） |
| `--out 目录` | `out/<模型名>` | 产物目录 |
| `--ignore "floor*,ground*"` | 空 | 逗号分隔 glob；隐藏辅助对象（如地面）并排除出取景；只改运行中场景，不保存 `.blend` |
| `--factory` | 关 | 加 `--factory-startup` 启动（排除用户插件干扰） |
| `--no-sheet` | 关 | 跳过拼版总览图 |

## 产物

```
out/<模型名>/
├── view_000.png ~ view_015.png   环绕 16 视角（方位角 0/22.5/.../337.5°）
├── view_top.png                  正顶视角
├── sheet.png                     拼版总览（6 列网格，一眼看全）
└── manifest.json                 角度/耗时/包围盒/引擎（驱动从渲染日志提取）
```

取景规则：按全场景可见几何的包围盒自动算相机距离，**所有视角同一半径**，各图模型比例一致，翻页对比不跳。布光用「双太阳 + 灰背景世界」，原场景灯光一律隐藏，保证任何模型的体检图风格统一。

## AI 自检闭环协议

本工具是闭环的「渲染」半边；「挑错与修复」由 AI（ZCode 会话内直接读图）执行：

1. **渲染**：`check.sh` 跑完，17+1 张图 + manifest 齐全。
2. **读图**：AI 读 `sheet.png` 总览，可疑处再读对应单图细看。
3. **问题单**：按视角列结构化问题——每条含「视角 / 严重度 / 描述 / 能否脚本修」。典型检查项：轮廓走形、比例失调、部件穿插、法线翻黑面、贴图错位/丢失、材质异常、构图裁切。机器可读落点：`python ../人物建模/scripts/visual_review.py init --manifest <out>/manifest.json --out <out>/visual_review.json`，填 `problems[]` 后 `validate` / `summary`；字段见脚本头。
4. **修复**：只有「可脚本修」的（缩放、位移、旋转、法线重算、修改器、命名）才写 bpy 修复脚本执行；造型/拓扑/贴图绘制类只提意见不动手。
5. **复渲复检**：修复后重跑 `check.sh`，对照上一轮，最多 3 轮。
6. **报告**：输出 `out/<模型名>/report_round<k>.md`，最终通过或把剩余问题列入手工清单。

   > 可复用会话提示词模板：[`prompts/审图自检闭环.md`](../prompts/审图自检闭环.md)（口径以本节为准，改口径先改这里）。

## 安全纪律

- **渲染永远只读**：`--background` headless，不保存 `.blend`；`check.sh` 会核对源文件 mtime 前后不变，变了就报警。
- **修复轮才写回**：写回主项目前必须确认该文件没有前台 Blender 窗口开着（CLI 无法感知窗口内未保存状态）；有则按 blender:cli 的关窗流程处理，禁止 taskkill。
- **落盘白名单**：渲染脚本内输出目录限制在「工具目录 ∪ 模型所在目录」，路径拼接全走守卫（禁穿越组件）。
- 产物落在工具自己的 `out/`，不污染游戏工程仓库。

## 接入现有流水线

- **stardust**（`D:/G/game/games/stardust/tools/blender/`）：`build_props.py` 建完模后接一句 `bash "D:/G/github/实用工具/Blender建模/Blender体检/check.sh" stardust_props.blend`，AI 复检通过再 `export_props_glb.py` 导出。
- **blender-rig**（reroute 建筑）：`rig_buildings.py` 产出的 glb 前身 `.blend` 同理，先体检后导出。

## 已知限制

- 拼版单元 = 渲染分辨率，不缩放；`--res 2048` 时 sheet 会很大，慎用。
- EEVEE headless 依赖 GPU 上下文，个别驱动/远程环境渲不出来，换 workbench 或 cycles。
- 场景里所有可见几何一起取景（没有按对象单独体检）；单件体检请拆场景或隐藏无关对象。角色/道具场景里的地面可用 `--ignore "floor*,ground*"` 排除（2026-11-03 实测：不加时角色只占画面中心约 40px，加了之后撑满取景）。
