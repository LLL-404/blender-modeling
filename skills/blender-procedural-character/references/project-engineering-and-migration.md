# 项目工程化与迁入版本库

适用：散在目录里的脚本项目（本仓库的「人物建模」）要「变成正式项目」——整体移入私有工具仓、补 README/依赖/gitignore/CHANGELOG、加统一构建入口与一键探针自检、只提交本次相关文件。

核心判断：**迁移是「不复制、不删除」的物理移动，工程化是「只新建入口、不改业务逻辑」的外壳**；两者都要用迁前/迁后的数字与 `git ls-files --others` 的清单自证，不能靠"看起来都在"。

## 一、整体迁移（mv）的四步

1. **迁前快照**：`find <目录> -type f | wc -l`、`find <目录> -type d | wc -l`、`du -sh`、`ls -la`，并把完整文件清单落到临时目录（如 `.tmp/<项目>-迁移快照-<日期>.txt`）。快照不进仓、不进 `散件归档/`（改基线）。
2. **确认没有在跑的写入者**：看目标目录最近一次写盘时间与当前时间的差。实测安全线：对方任务 `in_progress` 但已 ≥40 分钟无写入才可迁；否则迁移后它会按旧路径**重建**目录，破坏「根目录只放治理件」这类硬约束。
3. **`mv <目录> Tools/<目录>`**（同盘 rename，秒级）。因文件占用失败就等 10 秒重试一次；仍失败直接报告，**不要**退化成 `cp -r` + `rm`（那就成了复制 + 删除，违反纪律）。
4. **迁后逐项核对**：文件数、目录数、体积与迁前完全相同；同时复测根目录文件数（如仍为 3）。之后若继续建工程文件，文件数会涨，要能逐项解释差额：本轮 192 → 216 = +6 个工程文件 + 7 个 `opt/logs/*` + 11 个新 pyc。

**迁移不改变 import**：入口脚本用 `sys.path.insert(0, HERE)`（`HERE = dirname(abspath(__file__))`）、输出目录用 `os.path.dirname(os.path.dirname(abspath(__file__)))/out` 推导时，移动目录后 `import cfg` / `from lib import …` 与产物路径全部照旧，**cwd 无关**。构建入口仍应把 `cwd` 固定为项目根以统一行为。

## 二、`scripts/build.py`（统一入口）的设计要点

- **纯标准库**，绝不 `import bpy`：它只负责起 Blender 进程并转发退出码。
- 可执行文件取环境变量（如 `BLENDER_EXE`），默认本机安装路径；**先 `os.path.exists` 检查**，不存在打印中文提示 + `exit 2`，不静默失败。
- 子命令表 → 入口脚本映射，`all` 的顺序固定且有序（素体→头→着色→头发→服装→骨架），不能按字典顺序跑。
- 每次调用打印一行机器可读的进度：`[build] step=body exit=0 elapsed=4.8s`；任一非 0 立即停止并**返回该退出码**。
- `archive` 类副作用命令：复制（不移动）+ 时间戳子目录 + 文件数与字节计数，目标已存在时加 `-1` 后缀防同秒覆盖。
- `check` 转调自检脚本时用 `sys.executable`，并把 `BLENDER_EXE` 透传进环境，保证两边用同一个 Blender。

## 三、`scripts/check.py`（一键自检）的汇总口径

**不猜语义，只认探针自己打印的显式标记**：

| 行内容 | 归档 |
|---|---|
| 含 `FAIL` | FAIL |
| 含 `PASS` **或 `OK`** | PASS（A4/D 两个探针用 `OK` 当通过标记；漏掉 `OK` 会把达标的探针全算 SKIP） |
| 只有 `[probe]`/`[bprobe]`/`[cprobe]`/`[dprobe]` 的信息行 | SKIP（只记录，不判定） |
| 退出码非 0 **或** stdout 含 `Traceback (most recent call last)` | CRASH，**不计入** PASS/FAIL/SKIP |

- **Blender 脚本抛异常时进程退出码常常仍是 0**——必须同时检查 Traceback，不能只看 returncode。
- FAIL 明细要带**行号**：行号定义为「该探针 stdout 的第 N 行」，同时把完整输出落 `opt/logs/probe_<脚本名>.log`（不入库），文档里写明这个口径，否则无法回查源码位置。
- 报告写 `<logs>/check_report.md`（该目录不入库）：汇总表（探针/状态/exit/耗时/PASS/FAIL/SKIP）+ FAIL 明细表 + CRASH 明细（最后 8 行）+ MISSING 明细。
- 终局退出码：有 FAIL / CRASH / MISSING → 1（"自检未达标"），否则 0。
- **要预期的两种正常结果**：① 纯信息型探针（如面部/质感）没有 PASS/FAIL，整片落 SKIP，这是如实反映，不是 bug——在 README 里点明"这两个探针需按 DESIGN 阈值人工判读"；② 同一批探针里可能既有"达标的 PASS"也有"已知限制的 FAIL"，汇总数字本身就是交付证据。

## 四、被管道吞掉的退出码（本轮踩过）

`python scripts/build.py check | tail -30; echo $?` 打印的 `EXIT_CODE=0` 是 **`tail` 的**退出码，不是 build 的（build 实际返回 1）。验证命令若必须用管道裁输出，用 `${PIPESTATUS[0]}`，或以脚本自己打印的 `[build] step=… exit=…` 为准；写进总结的数字要与其中一个对齐。

## 五、.gitignore 与「add 前预览」

- Tools 根 `.gitignore` 已有 `out/`、`__pycache__/`、`*.py[cod]`、`*.tmp` 时，项目级仍重写一遍（从子目录 `git check-ignore -v` 与 IDE 都看得清），并把 `opt/tmp/`、`opt/logs/`、`opt/trials*.jsonl`、各 `_stage*/logs/`、`*.blend`、`*.blend1` 列全。
- **还要补探针自己产生的中间目录**：本轮 `_stageB/tmp/` 有 4 张 2.1MB 的同机位对照 png，不在任务清单里，但必须忽略（与 `out/` 同类，可重跑）。
- **必入库项不要误伤**：`opt/best.json`（配置，删它=回默认值）、`opt/REPORT.md`、`DESIGN.md`、所有 `*.py`、`_stage*/` 下的探针脚本。
- `git add` 之前先预览：`git ls-files --others --exclude-standard -- <目录>`（比 `git status` 精确，直接列出将入库的 54 个文件），发现 png/日志就补规则再 add。

## 六、提交纪律（本轮实测有效）

```bash
git add <目录> README.md
git status --porcelain                      # 确认他人的改动仍是 M/??，没被带进来
git diff --cached --name-only               # 逐条核对，55 个文件里不应出现别人的族目录
git commit -m "<族目录>: 做了什么"
```

- 不使用 `git add -A`；`git status` 里出现别人的 `M WorkBuddy额度/…`、`?? Blender体检/` 时**不要** reset 整个索引，只别 add 它们即可。
- **不 amend**：提交后发现文档要回填实测值，就再开一笔小 commit（本轮 3 笔：主体工程化 → README 回填 b_probe 实测 → README 补 archive 口径）。amend 只在用户明说或 hook 自动改动时用。
- 只 add 本次相关，不等于"只 add 一个文件"：`git add 人物建模` 会把目录内所有未忽略文件（含 `_stageB/_tail.txt` 这类小日志）一起收；愿不愿意收由 .gitignore 决定，不由手工挑文件决定。

## 七、归档功能不要往真实归档写测试副本

`archive` 的测试若直接跑，会在 `散件归档/` 下新开一个 30MB 目录，打乱 AGENTS.md 里「142 个数据件」的复测基线。正确做法是**加载模块 + 改常量重定向**，真实跑到复制分支：

```python
spec = importlib.util.spec_from_file_location('b', r'scripts/build.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.ARCHIVE_REL = os.path.join('..', '..', '.tmp', '<项目>-archive-test')
m.ARCHIVE_OUT_DIR = 'scripts'          # 走 copytree 分支
m.ARCHIVE_BLEND_GLOB = 'requirements.txt'  # 走 copy2 分支
print(m.run_archive())                 # rc=0、files=5、bytes=47165
```

README 里如实写「已实现、已重定向实测、未往真实归档写测试副本」。

## 八、文档回填要先用探针拿实测数字

写 README/CHANGELOG 前先跑一次对应探针（本轮 `d_probe` / `c_probe` 各一次，14s 级），拿当下的数字再落笔：

- 阶段表列「阶段 | 做了什么 | 代表性实测（阈值） | 证据位置」，每条数字后跟 `文件:行` 或 `_stageX/logs/…` / `opt/REPORT.md §…`。
- 已知限制里**区分两类**：任务/设计文档已列的（如法线翻转 17 条、屈指 min 0.582、轮廓光 0px），与自己实测新发现的（如脸部特写描边 p50=7px、m4 脸 p50=0px，超出 2~4px 目标）。只抄前者等于瞒报。
- 未完成项要写清"跑到哪一步"：像素段只落 1 条 baseline（`n=2`、`score≈4e-6`、`best.json` 无 `pixel` 段），不能说"已实现"。
- 参数搜索器章节必须写**回滚方法**（删 `opt/best.json` 即回模块默认值，依据 `lib/optio.py` 的 `param()` 查找顺序），这是配置类文件的验收项。
- 迁移记录单独一节：迁前后文件数、代码一行未改、`out/` 与 `*.blend` 由 .gitignore 决定去留而不删除。

## 九、验收清单（本轮全部通过的具体口径）

```bash
python -m py_compile cfg.py m1_*.py … lib/*.py opt/*.py scripts/*.py     # 覆盖全部 .py
python scripts/build.py body            # exit=0，产物写 out/
python scripts/build.py check           # 生成 check_report.md
git check-ignore -v <out图> <*.blend> __pycache__ <logs报告> <探针tmp图>  # 每条都要有输出
find <工作区根> -maxdepth 1 -type f | wc -l                              # 仍为 3
ls <旧路径>                                                              # 不存在
```

`git check-ignore -v` 的额外价值：它会打印命中的规则行号（`:11:out/`、`:30:*.blend`、`:9:__pycache__/`、`:18:opt/logs/`、`:14:_stageB/tmp/`），可直接证明不是"碰巧没进暂存区"。