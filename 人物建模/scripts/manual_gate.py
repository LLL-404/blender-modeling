# -*- coding: utf-8 -*-
r"""改模型前的手册闸门（BOSS 2026-11-05 定：改模型前先过一遍 Blender 技术手册）。

规则由 `scripts/flow.py` 在 `run`（会重建几何）之前强制执行：
没有有效查证记录 → FAIL 且**不执行任何构建**。

判定口径（全部可判定，不看形容词）
--------------------------------
  · 记录文件 `out/flow/<部位>/manual_review.json` 存在
  · `part` 与部位一致
  · `queries` ≥ 2 条检索词
  · `pages` ≥ 2 条，且每条路径必须真实存在于 `docs/manual/manual.db` 的 `pages.path`
  · `conclusion` ≥ 20 字
  · `at` 是 YYYY-MM-DDTHH:MM:SS，且晚于该部位 `sources` 的最新修改时间
    （源码改了却没重查手册 → STALE）

用法（项目根 `人物建模/` 下）
----------------------------
    python scripts/manual_gate.py query "桥接循环边 混合曲面"     # 检索手册，拿真实页路径
    python scripts/manual_gate.py template face                  # 打印该部位的记录模板
    python scripts/manual_gate.py record face --queries "..." --pages "..." --conclusion "..."
    python scripts/manual_gate.py check face                     # 校验一个部位
    python scripts/manual_gate.py check-all                      # 校验全部部位
"""
import argparse
import json
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                    # 人物建模/
PROJECT = os.path.dirname(ROOT)                  # Blender建模/
DOCS = os.path.join(PROJECT, "docs")
MANUAL_DB = os.path.join(DOCS, "manual", "manual.db")
SPEC = os.path.join(ROOT, "spec", "parts.json")
FLOW_OUT = os.path.join(ROOT, "out", "flow")

MIN_QUERIES = 2
MIN_PAGES = 2
MIN_CONCLUSION = 20

SUGGEST = {
    "body": ["按距离合并", "重构网格 丢失数据层", "矫正平滑 钉固边界"],
    "face": ["桥接循环边 混合曲面", "SDF圆角 凹角", "缩裹修改器"],
    "hair": ["实体化修改器 厚度", "曲线 转为 网格", "法线 翻转"],
    "outfit": ["缩裹修改器 顶点组", "布尔修改器 流形", "实体化 厚度"],
    "rig": ["矫正平滑修改器", "骨架修改器 封套", "顶点组 权重"],
    "asset": ["缝合边 UV", "按角度平滑修改器", "三角化修改器"],
}


def _db_paths():
    if not os.path.isfile(MANUAL_DB):
        raise RuntimeError("找不到离线手册索引：%s" % MANUAL_DB)
    con = sqlite3.connect(MANUAL_DB)
    try:
        return {r[0] for r in con.execute("SELECT path FROM pages")}
    finally:
        con.close()


def _newest(sources):
    """源码/目录的最新 mtime；目录递归取文件最大时间（与 flow._mtime 同口径）。"""
    newest = 0.0
    for rel in sources or []:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        try:
            newest = max(newest, os.path.getmtime(p))
        except OSError:
            pass
        if os.path.isdir(p):
            for dirpath, _dirs, files in os.walk(p):
                for name in files:
                    try:
                        newest = max(newest, os.path.getmtime(os.path.join(dirpath, name)))
                    except OSError:
                        pass
    return newest


def verify(part_id, sources=None):
    """返回 (ok, detail)。被 flow.py 调用。"""
    path = os.path.join(FLOW_OUT, part_id, "manual_review.json")
    if not os.path.isfile(path):
        return False, "缺手册查证记录 %s（先跑 query/template/record）" % os.path.relpath(path, ROOT)
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except Exception as exc:
        return False, "手册记录读不了：%s" % exc
    if doc.get("part") != part_id:
        return False, "part 写成 %r，应为 %r" % (doc.get("part"), part_id)
    queries = [str(q).strip() for q in (doc.get("queries") or []) if str(q).strip()]
    if len(queries) < MIN_QUERIES:
        return False, "检索词只有 %d 条，要求 ≥%d" % (len(queries), MIN_QUERIES)
    pages = [str(p).strip() for p in (doc.get("pages") or []) if str(p).strip()]
    if len(pages) < MIN_PAGES:
        return False, "手册页只有 %d 条，要求 ≥%d" % (len(pages), MIN_PAGES)
    try:
        valid = _db_paths()
    except Exception as exc:
        return False, str(exc)
    missing = [p for p in pages if p not in valid]
    if missing:
        return False, "手册页路径不存在（不许编）：%s" % "、".join(missing[:3])
    conclusion = str(doc.get("conclusion") or "").strip()
    if len(conclusion) < MIN_CONCLUSION:
        return False, "结论只有 %d 字，要求 ≥%d 且要写「查到什么、对改动有什么约束」" % (
            len(conclusion), MIN_CONCLUSION)
    at_raw = str(doc.get("at") or "")
    try:
        at = time.mktime(time.strptime(at_raw, "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return False, "at 不是 YYYY-MM-DDTHH:MM:SS：%r" % at_raw
    src = _newest(sources)
    if src and at < src - 2.0:
        return False, "源码比手册查证新（%s < %s），改完源码要重过一遍手册" % (
            time.strftime("%m-%d %H:%M", time.localtime(at)),
            time.strftime("%m-%d %H:%M", time.localtime(src)))
    return True, "%d 条检索 / %d 页手册（路径已核）/ 结论 %d 字 / %s" % (
        len(queries), len(pages), len(conclusion), at_raw)


def _parts():
    return json.load(open(SPEC, encoding="utf-8"))["parts"]


def cmd_query(q, limit=5):
    sys.path.insert(0, DOCS)
    import manual_index as mi
    rows = mi.search(MANUAL_DB, q, limit=limit)
    print("[manual] query=%r -> %d 条" % (q, len(rows)))
    for r in rows:
        print("  %s" % r.get("path"))
        print("      %s | %s" % (r.get("title"),
                                 (r.get("snippet") or "").replace("\n", " ")[:110]))
    return 0 if rows else 1


def cmd_template(part_id):
    doc = {
        "part": part_id,
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": "docs/manual/manual.db（Blender 5.2 LTS 中文版）",
        "queries": SUGGEST.get(part_id, ["<检索词1>", "<检索词2>"]),
        "pages": ["<用 query 查到的真实页路径1>", "<真实页路径2>"],
        "conclusion": "<查到什么、对这次改动有什么约束，≥20 字>",
    }
    print(json.dumps(doc, ensure_ascii=False, indent=2))
    return 0


def cmd_record(part_id, queries, pages, conclusion):
    doc = {
        "part": part_id,
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": "docs/manual/manual.db（Blender 5.2 LTS 中文版）",
        "queries": list(queries or []),
        "pages": list(pages or []),
        "conclusion": conclusion or "",
    }
    folder = os.path.join(FLOW_OUT, part_id)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "manual_review.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
    sources = next((p.get("sources") or [] for p in _parts() if p["id"] == part_id), [])
    ok, detail = verify(part_id, sources)
    print("[manual] %s -> %s（%s）" % (part_id, "PASS" if ok else "FAIL", detail))
    return 0 if ok else 1


def cmd_check(part_id):
    sources = next((p.get("sources") or [] for p in _parts() if p["id"] == part_id), [])
    ok, detail = verify(part_id, sources)
    print("[manual] %-8s %s  %s" % (part_id, "PASS" if ok else "FAIL", detail))
    return 0 if ok else 1


def cmd_check_all():
    bad = 0
    for part in _parts():
        ok, detail = verify(part["id"], part.get("sources") or [])
        print("[manual] %-8s %s  %s" % (part["id"], "PASS" if ok else "FAIL", detail))
        bad += 0 if ok else 1
    print("[manual] 合计 %d/%d 部位通过" % (len(_parts()) - bad, len(_parts())))
    return 0 if bad == 0 else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="manual_gate.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("query", help="检索离线手册，拿真实页路径")
    q.add_argument("q")
    q.add_argument("--limit", type=int, default=5)
    t = sub.add_parser("template", help="打印某部位的记录模板")
    t.add_argument("part")
    r = sub.add_parser("record", help="写查证记录并立即校验")
    r.add_argument("part")
    r.add_argument("--queries", nargs="+", required=True)
    r.add_argument("--pages", nargs="+", required=True)
    r.add_argument("--conclusion", required=True)
    for name in ("check", "check-all"):
        p = sub.add_parser(name)
        if name == "check":
            p.add_argument("part")
    a = ap.parse_args(argv)
    if a.cmd == "query":
        return cmd_query(a.q, a.limit)
    if a.cmd == "template":
        return cmd_template(a.part)
    if a.cmd == "record":
        return cmd_record(a.part, a.queries, a.pages, a.conclusion)
    if a.cmd == "check":
        return cmd_check(a.part)
    return cmd_check_all()


if __name__ == "__main__":
    raise SystemExit(main())
