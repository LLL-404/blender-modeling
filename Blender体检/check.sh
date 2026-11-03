#!/usr/bin/env bash
# Blender体检 · 驱动脚本：一条命令渲 16 视角 + 顶视 + 拼版 + manifest
# 用法: bash check.sh <model.blend> [--views 16] [--elevation 20] [--engine eevee]
#                     [--res 512] [--out <目录>] [--factory] [--no-sheet]
#                     [--ignore "floor*,ground*"]   # 逗号分隔 glob，隐藏辅助对象并排除出取景
# 环境变量 BLENDER_EXE 可指定 blender.exe 绝对路径；默认自动探测。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

find_blender() {
  if [[ -n "${BLENDER_EXE:-}" ]]; then
    printf '%s\n' "$BLENDER_EXE"
    return 0
  fi
  local base hit
  # 默认值与 人物建模/scripts/bpyrun.py 同源，改一处须对另一处。
  for base in "D:/Program Files/Blender Foundation" "C:/Program Files/Blender Foundation"; do
    hit="$(ls -d "$base"/*/blender.exe 2>/dev/null | sort -V | tail -1)"
    if [[ -n "$hit" ]]; then
      printf '%s\n' "$hit"
      return 0
    fi
  done
  command -v blender || {
    echo "找不到 blender.exe（可用 BLENDER_EXE 环境变量指定）" >&2
    return 1
  }
}

usage() {
  sed -n '2,5p' "$0"
  exit 0
}
[[ $# -lt 1 ]] && usage
case "$1" in
  -h | --help) usage ;;
esac

MODEL="$1"
shift
[[ -f "$MODEL" ]] || { echo "模型不存在: $MODEL" >&2; exit 1; }

views=16
elevation=20
engine=eevee
res=512
out=""
factory=0
sheet=1
ignore=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --views) views="$2"; shift 2 ;;
    --elevation) elevation="$2"; shift 2 ;;
    --engine) engine="$2"; shift 2 ;;
    --res) res="$2"; shift 2 ;;
    --out) out="$2"; shift 2 ;;
    --ignore) ignore="$2"; shift 2 ;;
    --factory) factory=1; shift ;;
    --no-sheet) sheet=0; shift ;;
    *) echo "未知参数: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$out" ]]; then
  base="$(basename "$MODEL")"
  base="${base%.*}"
  out="$SCRIPT_DIR/out/$base"
fi
mkdir -p "$out"

BLENDER="$(find_blender)"
MTIME_BEFORE="$(stat -c %Y "$MODEL")"

extra=()
[[ $factory == 1 ]] && extra+=(--factory-startup)
pyargs=(--views "$views" --elevation "$elevation" --engine "$engine" --res "$res" --out "$out")
[[ -n "$ignore" ]] && pyargs+=(--ignore "$ignore")
[[ $sheet == 0 ]] && pyargs+=(--no-sheet)

echo "[blender体检] $BLENDER"
echo "[blender体检] 模型: $MODEL"
start="$(date +%s)"

# 只读渲染：捕获全部日志，CHECK_OK / MANIFEST_JSON 从 stdout 提取
log="$("$BLENDER" -b "$MODEL" "${extra[@]}" --python-exit-code 1 \
  --python "$SCRIPT_DIR/render_views.py" -- "${pyargs[@]}" 2>&1)" || {
  printf '%s\n' "$log"
  echo "[blender体检] 渲染失败（见上方日志）" >&2
  exit 1
}
printf '%s\n' "$log" | grep -a '^CHECK_OK' || true

manifest_line="$(printf '%s\n' "$log" | grep -a '^MANIFEST_JSON ' | tail -1 || true)"
[[ -n "$manifest_line" ]] || { echo "[blender体检] 未取到 MANIFEST_JSON" >&2; exit 1; }
printf '%s\n' "${manifest_line#MANIFEST_JSON }" >"$out/manifest.json"

MTIME_AFTER="$(stat -c %Y "$MODEL")"
if [[ "$MTIME_BEFORE" != "$MTIME_AFTER" ]]; then
  echo "[blender体检] 警告: 源 .blend 的 mtime 变了（渲染应当只读，请排查）" >&2
fi

missing=0
for ((i = 0; i < views; i++)); do
  f="$(printf '%s/view_%03d.png' "$out" "$i")"
  [[ -s "$f" ]] || { echo "缺失: $f" >&2; missing=1; }
done
[[ -s "$out/view_top.png" ]] || { echo "缺失: $out/view_top.png" >&2; missing=1; }
[[ -s "$out/manifest.json" ]] || { echo "缺失: $out/manifest.json" >&2; missing=1; }
[[ $missing == 0 ]] || exit 1

elapsed=$(( $(date +%s) - start ))
echo "[blender体检] 完成: $out"
echo "[blender体检] 耗时: ${elapsed}s | 产物: ${views} 张环绕 + view_top.png + sheet.png + manifest.json"
