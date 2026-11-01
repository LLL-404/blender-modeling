import json, os, sys
import numpy as np
from PIL import Image

BASE = (sys.argv[1] if len(sys.argv) > 1
        else os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "stardust_props"))
CELL, COLS = 512, 6
ok = True
with open(os.path.join(BASE, "manifest.json"), encoding="utf-8") as fh:
    man = json.load(fh)                                   # 验收脚本独立于 render_views.py，仅只读
names = [s["file"] for s in man["shots"]]                 # view_000..view_015, view_top（16+1）
rows = (len(names) + COLS - 1) // COLS

# --- A. 背景灰底（缺陷1）---
vt = man.get("view_transform")
if vt is None:                                            # v3：前提不可查 = FAIL，不静默降级
    print("FAIL manifest 缺 view_transform（S1-④ 缺失或 S3 未拦住），灰底前提不可查")
    sys.exit(1)
eng = man.get("engine", "")
corners = []
for f in ("view_000.png", "view_008.png", "view_top.png"):
    a = np.asarray(Image.open(os.path.join(BASE, f)).convert("RGB"))
    h, w, _ = a.shape
    cs = [a[0, 0], a[0, w - 1], a[h - 1, 0], a[h - 1, w - 1]]
    corners.append(cs)
    print("CORN", f, [tuple(int(v) for v in c) for c in cs])
if "WORKBENCH" in eng:                                    # v4：engine 分支，与 R6 对齐
    print("NOTE engine=%s：Workbench 不渲染世界着色器，灰底程序化门禁不适用，以看图判定为准" % eng)
elif vt == "Standard":
    for cs in corners:
        for c in cs:
            ok &= all(int(v) >= 220 for v in c)           # v4：三通道同检（0.82/0.84 线性 → ≈234/236）
            ok &= abs(int(c[0]) - int(c[1])) <= 1         # E2 实证 dither ±1，严格相等会假阳性
            ok &= abs(int(c[2]) - int(c[0])) <= 6
else:
    for cs in corners:                                    # 非 Standard：一致性 + 下界双判据
        arr = np.asarray(cs, dtype=int)
        ok &= int((arr.max(axis=0) - arr.min(axis=0)).sum()) <= 6   # 三通道极差之和 ≤6（与 §1.3 同口径）
        ok &= float(arr.mean()) >= 100.0                  # 下界：黑底 (0,0,0) 必炸；0.82 灰经任何合理变换不近黑
    print("NOTE view_transform=%r：一致性+下界已验，看图判定仍必做" % vt)

# --- B. 拼版网格（缺陷2）---
sh = np.asarray(Image.open(os.path.join(BASE, "sheet.png")).convert("RGB"))
assert sh.shape == (rows * CELL, COLS * CELL, 3), sh.shape
n_ok = 0
for i, n in enumerate(names):
    r, c = divmod(i, COLS)
    reg = sh[r * CELL:(r + 1) * CELL, c * CELL:(c + 1) * CELL]
    src = np.asarray(Image.open(os.path.join(BASE, n)).convert("RGB"))
    if np.array_equal(reg, src):
        n_ok += 1
    else:
        print("MISMATCH", i, n, "grid r%d c%d" % (r, c))
ok &= n_ok == len(names)
print("GRID bit-exact %d/%d" % (n_ok, len(names)))

# --- C. 空格 = 0.35 灰（显示网格最末格；契约值与 Q2 绑定，改值须同步改此段并重跑 S3-S5）---
reg = sh[(rows - 1) * CELL:rows * CELL, (COLS - 1) * CELL:COLS * CELL]
uniq = np.unique(reg.reshape(-1, 3), axis=0)
print("EMPTY cell unique:", uniq[:4], "n=", len(uniq))
ok &= len(uniq) == 1 and abs(int(uniq[0][0]) - round(0.35 * 255)) <= 1 \
      and len(set(int(v) for v in uniq[0])) == 1

print("S4", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)

# 注：0.35 float → 8-bit 取整实测（verify-acceptance 回填，2026-10-30）：0.35*255=89.25，S4 实测 EMPTY 格落盘 89 且三通道相等——floor 与 round 在该点同为 89，单点不可分辨方向，89±1 判据命中。
