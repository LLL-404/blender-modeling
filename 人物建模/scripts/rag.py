# -*- coding: utf-8 -*-
"""RAG context builder：把 catalog / bapi / lib / 手册检索成「写 bapi 代码」的上下文。

定位：本项目缺的不是“让模型自由写 bpy”，而是**给模型一份版本正确、来源可查的
上下文**，再把候选代码交给现有 verifier。`rag.py` 只做检索与上下文打包，不调用
任何 LLM；调用方（人/agent）拿 `context` 的输出去写代码，写完仍走
`BlenderAPI/selftest.py`、`build.py check`、`measure.py` 等门。

索引来源（全部只读）：
  1. `BlenderAPI/catalog/api.json`：5.2.2 实机扫描的修改器/类型/节点/操作符；
  2. `BlenderAPI/catalog/*.md`：按标题切的 API 目录；
  3. `BlenderAPI/bapi/*.py`：封装层函数 + docstring + 源码；
  4. `人物建模/lib/*.py`：仓内已有写法（函数/类/docstring/源码）；
  5. `docs/manual/manual.db`：离线手册 FTS5（由 manual_index.py 建）。

用法（在 `人物建模/` 下执行）：

    python scripts/rag.py build
    python scripts/rag.py query "倒角 宽度"
    python scripts/rag.py query "solidify 厚度" --json
    python scripts/rag.py context "做一个带倒角的立方体" --out out/rag_context.md
    python scripts/rag.py selftest

产物 `人物建模/out/rag/rag.db` 不入库（out/ 已 gitignore）。
"""
import argparse
import ast
import json
import os
import re
import sqlite3
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                       # 人物建模/
PROJECT = os.path.dirname(ROOT)                    # Blender建模/
DOCS_DIR = os.path.join(PROJECT, "docs")
BAPI_DIR = os.path.join(PROJECT, "BlenderAPI", "bapi")
LIB_DIR = os.path.join(ROOT, "lib")
CATALOG_JSON = os.path.join(PROJECT, "BlenderAPI", "catalog", "api.json")
CATALOG_DIR = os.path.join(PROJECT, "BlenderAPI", "catalog")
DEFAULT_DB = os.path.join(ROOT, "out", "rag", "rag.db")

# 中文口头词 -> 英文 API/参数词。只用于本地 FTS 召回，不改变用户原 query。
SYNONYMS = {
    "倒角": "bevel",
    "立方体": "cube box",
    "方块": "cube box",
    "球": "sphere",
    "圆柱": "cylinder",
    "平面": "plane",
    "管": "tube",
    "放样": "loft",
    "扫掠": "tube sweep",
    "实体化": "solidify",
    "厚度": "thickness",
    "细分": "subsurf subdivision",
    "曲面": "surface subdivision",
    "法线": "normal",
    "翻转": "flip",
    "重算": "recalc",
    "合并": "merge",
    "按距离": "distance",
    "uv": "uv unwrap",
    "展开": "unwrap",
    "蒙皮": "skin weight armature",
    "权重": "weight vertex group",
    "骨架": "armature bone",
    "材质": "material principled",
    "节点": "node shader",
    "渲染": "render",
    "相机": "camera",
    "正交": "ortho",
    "灯光": "light sun area",
    "位移": "displace",
    "体素": "voxel remesh",
    "重构网格": "remesh",
    "平滑": "smooth",
    "镜像": "mirror",
    "阵列": "array",
    "布尔": "boolean",
    "曲线": "curve",
    "导出": "export gltf",
}

_MANUAL = None


def _utf8_stdio():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _rel(path):
    return os.path.relpath(path, PROJECT).replace("\\", "/")


def _clip(text, n=1200):
    text = text or ""
    if len(text) <= n:
        return text
    return text[:n].rstrip() + "\n...（截断）"


def _manual_module():
    global _MANUAL
    if _MANUAL is not None:
        return _MANUAL
    if DOCS_DIR not in sys.path:
        sys.path.insert(0, DOCS_DIR)
    import manual_index
    _MANUAL = manual_index
    return _MANUAL


def _tokenize(text):
    try:
        return _manual_module().tokenize(text)
    except Exception:
        # 兜底：CJK 逐字加空格，英文按原样。
        buf = []
        for ch in text:
            if 0x3000 <= ord(ch) <= 0x9FFF or 0xF900 <= ord(ch) <= 0xFAFF:
                buf.extend((" ", ch, " "))
            else:
                buf.append(ch)
        return " ".join("".join(buf).split())


def _expand_query(q):
    extra = []
    low = q.lower()
    for zh, en in SYNONYMS.items():
        if zh.lower() in low and en.lower() not in low:
            extra.append(en)
    return q if not extra else q + " " + " ".join(extra)


# ---------------------------------------------------------------- 采集

def _prop_text(props):
    out = []
    for p in props or []:
        if not isinstance(p, dict):
            continue
        bits = [str(p.get("id", "?"))]
        if p.get("type"):
            bits.append(str(p["type"]))
        if "default" in p:
            bits.append("default=" + repr(p["default"]))
        if "range" in p:
            bits.append("range=" + repr(p["range"]))
        if "enum" in p:
            enums = p["enum"]
            if isinstance(enums, list) and len(enums) > 12:
                enums = enums[:12] + ["..."]
            bits.append("enum=" + repr(enums))
        out.append("  ".join(bits))
    return "\n".join(out)


def _catalog_chunks():
    with open(CATALOG_JSON, "r", encoding="utf-8") as f:
        api = json.load(f)

    for name, info in sorted(api.get("modifiers", {}).get("detail", {}).items()):
        text = "Modifier {0}\nhost={1}\n{2}".format(
            name, info.get("host", ""), _prop_text(info.get("props")))
        yield ("catalog", _rel(CATALOG_JSON) + "#modifiers." + name,
               "Modifier." + name, text)

    for name, props in sorted(api.get("types", {}).items()):
        yield ("catalog", _rel(CATALOG_JSON) + "#types." + name,
               "Type." + name, "Type {0}\n{1}".format(name, _prop_text(props)))

    for name, info in sorted(api.get("nodes", {}).get("detail", {}).items()):
        text = "Node {0}\ntree={1}\ninputs:\n{2}\noutputs:\n{3}".format(
            name, info.get("tree", ""),
            json.dumps(info.get("in", []), ensure_ascii=False),
            json.dumps(info.get("out", []), ensure_ascii=False))
        yield ("catalog", _rel(CATALOG_JSON) + "#nodes." + name,
               "Node." + name, text)

    for category, items in sorted(api.get("ops", {}).items()):
        for item in items or []:
            if not isinstance(item, dict):
                continue
            name = item.get("name", "?")
            yield ("catalog", _rel(CATALOG_JSON) + "#ops." + category + "." + name,
                   "bpy.ops.{0}.{1}".format(category, name),
                   str(item.get("doc", "")))

    gltf = api.get("gltf", [])
    if gltf:
        yield ("catalog", _rel(CATALOG_JSON) + "#gltf",
               "glTF export options", "glTF export options:\n" + "\n".join(map(str, gltf)))


def _split_text(text, max_len=2400):
    """把长表格/长章节切成可检索的小块；避免一个“83 个修改器”大块霸榜。"""
    if len(text) <= max_len:
        return [text]
    parts = []
    buf = []
    size = 0
    for line in text.splitlines():
        if buf and size + len(line) + 1 > max_len:
            parts.append("\n".join(buf).strip())
            buf = []
            size = 0
        buf.append(line)
        size += len(line) + 1
    if buf:
        parts.append("\n".join(buf).strip())
    return [p for p in parts if p]


def _markdown_chunks():
    for name in sorted(os.listdir(CATALOG_DIR)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(CATALOG_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError:
            continue
        title = os.path.splitext(name)[0]
        buf = []

        def flush():
            if not buf:
                return
            text = "".join(buf).strip()
            if not text:
                return
            parts = _split_text(text)
            for i, part in enumerate(parts, 1):
                suffix = "" if len(parts) == 1 else " (part {0})".format(i)
                yield ("catalog", _rel(path), title + suffix, part)

        for line in lines:
            if re.match(r"^#{1,4}\s+", line):
                yield from flush()
                buf = []
                title = line.lstrip("#").strip()
            else:
                buf.append(line)
        yield from flush()


def _signature(node):
    try:
        text = ast.unparse(node)
    except Exception:
        return "def " + getattr(node, "name", "?") + "(...)"
    return text.splitlines()[0]


def _py_chunks(path, kind, prefix):
    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=path)
    except (OSError, SyntaxError):
        return
    lines = source.splitlines()

    doc = ast.get_docstring(tree)
    if doc:
        yield (kind, _rel(path), prefix + " (module)", doc)

    def emit(node, title):
        doc = ast.get_docstring(node) or ""
        start = max(0, node.lineno - 1)
        end = min(len(lines), getattr(node, "end_lineno", start + 120))
        code = "\n".join(lines[start:min(end, start + 160)])
        text = "{0}\n\n{1}\n\n{2}".format(_signature(node), doc, code).strip()
        yield (kind, _rel(path), title, text)

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield from emit(node, prefix + "." + node.name)
        elif isinstance(node, ast.ClassDef):
            yield from emit(node, prefix + "." + node.name)
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if sub.name.startswith("__"):
                        continue
                    yield from emit(sub, "{0}.{1}.{2}".format(prefix, node.name, sub.name))


def collect_chunks():
    rows = {}
    sources = []
    sources.extend(_catalog_chunks())
    sources.extend(_markdown_chunks())
    for name in sorted(os.listdir(BAPI_DIR)):
        if name.endswith(".py"):
            sources.extend(_py_chunks(os.path.join(BAPI_DIR, name), "bapi",
                                      "bapi." + os.path.splitext(name)[0]))
    for name in sorted(os.listdir(LIB_DIR)):
        if name.endswith(".py"):
            sources.extend(_py_chunks(os.path.join(LIB_DIR, name), "lib",
                                      "lib." + os.path.splitext(name)[0]))
    for kind, source, title, text in sources:
        key = (kind, source, title)
        if key not in rows or len(text) > len(rows[key][3]):
            rows[key] = (kind, source, title, text)
    return sorted(rows.values(), key=lambda r: (r[0], r[1], r[2]))


# ---------------------------------------------------------------- 索引

def build(db_path=DEFAULT_DB, verbose=True):
    t0 = time.monotonic()
    rows = collect_chunks()
    if not rows:
        raise RuntimeError("没有采集到任何 chunk，检查 catalog/bapi/lib 路径")
    parent = os.path.dirname(os.path.abspath(db_path))
    os.makedirs(parent, exist_ok=True)
    tmp = db_path + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    try:
        con.execute("PRAGMA journal_mode=OFF")
        con.execute(
            "CREATE VIRTUAL TABLE chunks USING fts5("
            "kind, source, title, text, search_text, tokenize='unicode61')")
        con.executemany(
            "INSERT INTO chunks(kind, source, title, text, search_text)"
            " VALUES (?, ?, ?, ?, ?)",
            [(kind, source, title, text, _tokenize(title + "\n" + text))
             for kind, source, title, text in rows])
        con.commit()
    finally:
        con.close()
    os.replace(tmp, db_path)
    size = os.path.getsize(db_path) / 1048576.0
    if verbose:
        print("[rag] 索引完成：{0} chunks / {1:.1f} MB / {2:.2f}s -> {3}".format(
            len(rows), size, time.monotonic() - t0, db_path))
        by_kind = {}
        for kind, _source, _title, _text in rows:
            by_kind[kind] = by_kind.get(kind, 0) + 1
        print("[rag] 分布：" + ", ".join("{0}={1}".format(k, v) for k, v in sorted(by_kind.items())))
    return db_path


def ensure_db(db_path=None):
    db_path = db_path or DEFAULT_DB
    if os.path.exists(db_path):
        return db_path
    print("[rag] 索引不存在，先 build …", file=sys.stderr)
    return build(db_path, verbose=False)


def _connect(db_path):
    return sqlite3.connect("file:%s?mode=ro" % db_path.replace("\\", "/"), uri=True)


def _snippet(text, q, width=110):
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= width * 2:
        return text
    keys = [w for w in re.split(r"\s+", q) if w]
    low = text.lower()
    pos = -1
    for key in keys:
        i = low.find(key.lower())
        if i >= 0 and (pos < 0 or i < pos):
            pos = i
    if pos < 0:
        return text[:width * 2].rstrip() + "…"
    lo = max(0, pos - width)
    hi = min(len(text), pos + width)
    return ("…" if lo else "") + text[lo:hi] + ("…" if hi < len(text) else "")


# 代码生成场景的排序先验：具体函数/仓内写法优先于“83 个修改器”这类目录大块。
# bm25 的 rank 是负值，score=-rank 越**大**越相关；bonus 是加分。
KIND_BONUS = {"bapi": 10.0, "lib": 4.0, "catalog": 0.0}


def _rank_rows(rows, q, op, limit):
    out = [{
        "kind": r[0], "source": r[1], "title": r[2],
        "score": round(-r[4], 3), "mode": op,
        "snippet": _snippet(r[3], q),
    } for r in rows]
    out.sort(key=lambda item: (
        item["score"] + KIND_BONUS.get(item["kind"], 0.0), item["score"]),
             reverse=True)
    return out[:limit]


def _local_search(con, q, limit=8):
    try:
        mi = _manual_module()
        to_query = mi.to_query
    except Exception:
        to_query = lambda text, op="AND": " ".join(
            '"' + part + '"' for part in text.split())
    expanded = _expand_query(q)
    for op in ("AND", "OR"):
        expr = to_query(expanded, op)
        if not expr:
            return []
        try:
            rows = con.execute(
                "SELECT kind, source, title, text,"
                "       bm25(chunks, 0.0, 0.0, 8.0, 1.0, 4.0) AS rank"
                "  FROM chunks WHERE chunks MATCH ? ORDER BY rank LIMIT ?",
                (expr, max(limit * 3, 20))).fetchall()
        except sqlite3.OperationalError:
            rows = []
        if rows:
            return _rank_rows(rows, q, op, limit)
    return []


def _anchor_terms(q):
    """把 query 里的中文名词映射成英文词，供「精确函数锚点」用。"""
    low = q.lower()
    terms = []
    for zh, en in SYNONYMS.items():
        if zh.lower() not in low:
            continue
        for word in en.split():
            if word.isascii() and word not in terms:
                terms.append(word)
    return terms


def _anchors(con, q, limit=4):
    """给每个查询名词找一个同名函数，保证签名进得了 context。

    为什么不用纯 bm25：query 里同时有多个词时，只命中一个词的短函数
    （如 `bapi.mesh.sphere`）会被命中三四个词的通用块挤下去。锚点只按
    「标题末段 == 名词」取，一条名词最多一个，不参与打分。
    """
    out = []
    seen = set()
    for term in _anchor_terms(q):
        try:
            rows = con.execute(
                "SELECT kind, source, title, text,"
                "       bm25(chunks, 0.0, 0.0, 8.0, 1.0, 4.0) AS rank"
                "  FROM chunks"
                " WHERE chunks MATCH ?"
                "   AND kind IN ('bapi', 'lib')"
                "   AND (title = ? OR title LIKE ? OR title LIKE ?)"
                " ORDER BY CASE kind WHEN 'bapi' THEN 0 WHEN 'lib' THEN 1 ELSE 2 END,"
                "          rank LIMIT 1",
                ('"' + term + '"', term, "%." + term, "% " + term)
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []
        for r in rows:
            if r[2] in seen:
                continue
            seen.add(r[2])
            out.append({
                "kind": r[0], "source": r[1], "title": r[2],
                "score": round(-r[4], 3), "mode": "anchor",
                "snippet": _snippet(r[3], q),
            })
        if len(out) >= limit:
            break
    return out


def _manual_search(q, limit=5):
    try:
        mi = _manual_module()
        rows = mi.search(mi.DB_PATH, q, limit=limit)
    except Exception as exc:
        print("[rag] 手册检索跳过：{0!r}".format(exc), file=sys.stderr)
        return []
    out = []
    for r in rows:
        out.append({
            "kind": "manual",
            "source": r.get("path", ""),
            "title": r.get("title", ""),
            "score": r.get("score", 0),
            "mode": r.get("mode", ""),
            "snippet": r.get("snippet", ""),
        })
    return out


def query(q, limit=8, manual_limit=5, db_path=None):
    db = ensure_db(db_path)
    con = _connect(db)
    try:
        local = _local_search(con, q, limit=limit)
        anchors = _anchors(con, q)
    finally:
        con.close()
    return {"query": q, "expanded": _expand_query(q),
            "local": local, "anchors": anchors,
            "manual": _manual_search(q, limit=manual_limit)}


# ---------------------------------------------------------------- 输出

def format_context(result, top=5, task=None):
    task = task or result["query"]
    lines = [
        "# Blender 5.2 bapi RAG context",
        "",
        "Task: " + task,
        "",
        "## 约束（先读）",
        "- Blender 5.2.2 LTS，headless：`blender -b --factory-startup --python-exit-code 1 --python <脚本>`。",
        "- 优先用 `bapi`（`BlenderAPI/bapi`，84 个公开函数，只有 4 处 `bpy.ops`）；不要新增 `bpy.ops`。",
        "- 坐标：Z 向上、-Y 为正面；单位米。",
        "- 产物只写 `out/` 或临时目录；不碰 `params/profile.json` 以外的配置。",
        "- 生成后必须用 `BlenderAPI/selftest.py` 或独立断言脚本验证，再谈“完成”。",
        "",
    ]
    groups = [
        ("bapi", "## bapi 可用函数（优先用这些）"),
        ("lib", "## 仓内代码范例"),
        ("catalog", "## API 目录（参数名/枚举/默认值）"),
    ]
    anchored = [a for a in result.get("anchors", [])]
    if anchored:
        lines.append("## 查询名词精确命中（先看签名）")
        lines.append("")
        for item in anchored[:top]:
            lines.append("### `{0}`".format(item["title"]))
            lines.append("source: `{0}`".format(item["source"]))
            lines.append("")
            lines.append("```text")
            lines.append(_clip(item["snippet"].replace("```", "'''"), 900))
            lines.append("```")
            lines.append("")
    anchor_titles = set(a["title"] for a in anchored)
    for kind, heading in groups:
        items = [r for r in result["local"]
                 if r["kind"] == kind and r["title"] not in anchor_titles][:top]
        if not items:
            continue
        lines.append(heading)
        lines.append("")
        for item in items:
            lines.append("### `{0}`".format(item["title"]))
            lines.append("source: `{0}`".format(item["source"]))
            lines.append("")
            lines.append("```text")
            lines.append(_clip(item["snippet"].replace("```", "'''"), 900))
            lines.append("```")
            lines.append("")
    if result["manual"]:
        lines.append("## 手册语义（参数什么意思）")
        lines.append("")
        for item in result["manual"][:top]:
            lines.append("### {0}".format(item["title"] or item["source"]))
            lines.append("source: `{0}`".format(item["source"]))
            lines.append("")
            lines.append(_clip(item["snippet"], 600))
            lines.append("")
    lines.extend([
        "## 输出契约",
        "只输出一个 JSON 对象，不要 Markdown 围栏：",
        "```json",
        '{"plan": "一句话方案", "code": "可执行的 bapi 脚本", "checks": ["要断言的数字/对象"]}',
        "```",
        "`code` 必须能在上面的 headless 命令下直接跑；如果用了新 API，先查本 context 的 catalog 段。",
        "",
    ])
    return "\n".join(lines)


def _print_query(result):
    print("[rag] query={0}".format(result["query"]))
    if result.get("expanded") and result["expanded"] != result["query"]:
        print("[rag] expanded={0}".format(result["expanded"]))
    for label, key in (("anchor", "anchors"), ("local", "local"),
                       ("manual", "manual")):
        print("[rag] {0}: {1}".format(label, len(result[key])))
        for item in result[key]:
            print("  {0:<10} {1:<48} {2}".format(
                item["kind"], item["title"][:48], item["source"]))
            print("    " + item["snippet"][:180])


def selftest():
    out_root = os.path.join(ROOT, "out")
    os.makedirs(out_root, exist_ok=True)
    passed = 0
    failed = 0
    with tempfile.TemporaryDirectory(dir=out_root) as td:
        db = os.path.join(td, "rag.db")
        try:
            build(db, verbose=False)
            con = _connect(db)
            n = con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            con.close()
            assert n >= 100, "chunks 太少：{0}".format(n)
            print("[selftest] PASS build chunks={0}".format(n))
            passed += 1
        except Exception as exc:
            print("[selftest] FAIL build: {0}".format(exc))
            failed += 1
            print("[selftest] PASS={0} FAIL={1}".format(passed, failed))
            return 1

        cases = [
            ("倒角 宽度", ("bevel",)),
            ("实体化 厚度", ("solidify",)),
            ("细分 曲面", ("subsurf", "subdivision")),
            ("法线 翻转", ("normal", "flip")),
            ("材质 Principled", ("principled",)),
            ("正交 相机 渲染", ("camera_ortho", "render")),
            ("UV 展开", ("uv",)),
            ("蒙皮 权重", ("rig", "weight")),
        ]
        con = _connect(db)
        try:
            for q, expects in cases:
                rows = _local_search(con, q, limit=8)
                hay = " ".join((r["title"] + " " + r["source"]).lower() for r in rows)
                ok = any(exp.lower() in hay for exp in expects)
                if ok:
                    print("[selftest] PASS query {0!r} -> {1}".format(
                        q, rows[0]["title"] if rows else "<none>"))
                    passed += 1
                else:
                    print("[selftest] FAIL query {0!r}: top={1}".format(
                        q, [r["title"] for r in rows[:3]]))
                    failed += 1
        finally:
            con.close()

        try:
            result = query("球体 材质 Principled 渲染", limit=12,
                           manual_limit=0, db_path=db)
            titles = [a["title"] for a in result.get("anchors", [])]
            assert "bapi.mesh.sphere" in titles, titles
            ctx = format_context(result, top=3)
            assert "bapi.mesh.sphere" in ctx
            print("[selftest] PASS anchors 球体 -> bapi.mesh.sphere")
            passed += 1
        except Exception as exc:
            print("[selftest] FAIL anchors: {0}".format(exc))
            failed += 1

        try:
            result = query("实体化 厚度", limit=5, manual_limit=3, db_path=db)
            ctx = format_context(result, top=3)
            assert "# Blender 5.2 bapi RAG context" in ctx
            assert "bapi" in ctx and "Blender 5.2.2 LTS" in ctx
            assert "输出契约" in ctx
            print("[selftest] PASS context format")
            passed += 1
        except Exception as exc:
            print("[selftest] FAIL context format: {0}".format(exc))
            failed += 1

    print("[selftest] PASS={0} FAIL={1}".format(passed, failed))
    return 0 if failed == 0 else 1


def main(argv=None):
    _utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="rag.py",
        description="Blender 5.2 bapi RAG：catalog/bapi/lib/手册检索与上下文打包")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="重建本地 RAG 索引")
    p_build.add_argument("--db", default=DEFAULT_DB)

    p_query = sub.add_parser("query", help="检索本地代码/API + 手册")
    p_query.add_argument("q")
    p_query.add_argument("--limit", type=int, default=8)
    p_query.add_argument("--manual-limit", type=int, default=5)
    p_query.add_argument("--db", default=DEFAULT_DB)
    p_query.add_argument("--json", action="store_true")

    p_context = sub.add_parser("context", help="输出给 LLM 的 Markdown context")
    p_context.add_argument("q")
    p_context.add_argument("--out", help="写到文件；缺省打印到 stdout")
    p_context.add_argument("--top", type=int, default=5)
    p_context.add_argument("--limit", type=int, default=12)
    p_context.add_argument("--manual-limit", type=int, default=5)
    p_context.add_argument("--db", default=DEFAULT_DB)

    sub.add_parser("selftest", help="建临时索引并跑检索/格式自检")

    args = parser.parse_args(argv)
    if args.cmd == "build":
        build(args.db)
        return 0
    if args.cmd == "query":
        result = query(args.q, limit=args.limit, manual_limit=args.manual_limit,
                       db_path=args.db)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            _print_query(result)
        return 0 if (result["local"] or result["manual"]) else 1
    if args.cmd == "context":
        result = query(args.q, limit=args.limit, manual_limit=args.manual_limit,
                       db_path=args.db)
        text = format_context(result, top=args.top, task=args.q)
        if args.out:
            os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
            with open(args.out, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            print("[rag] context -> {0} ({1} chars)".format(args.out, len(text)))
        else:
            print(text)
        return 0 if (result["local"] or result["manual"]) else 1
    if args.cmd == "selftest":
        return selftest()
    return 2


if __name__ == "__main__":
    sys.exit(main())
