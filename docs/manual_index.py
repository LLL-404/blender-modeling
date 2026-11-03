#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把离线 Blender 手册 HTML 包做成可检索的知识库（纯 Python，不需要 Blender）。

为什么需要它
------------
`BlenderAPI/catalog/` 回答「有什么 API、参数叫什么」；
手册回答「这个参数是什么意思、什么时候该用哪个」。
前者是实机扫出来的枚举，后者是人写的语义 —— 写脚本时缺哪一半都不够。

用法
----
    python docs/manual_index.py build                     # 重建索引（约 1~2 分钟）
    python docs/manual_index.py "实体化 厚度"              # 全文检索
    python docs/manual_index.py --api bpy.types.SolidifyModifier
    python docs/manual_index.py --show modeling/modifiers/generate/solidify.html
    python docs/manual_index.py --stats

产物 `docs/manual/manual.db` 不入库（见 .gitignore），随时可从 zip 重建。

两个实现要点（踩过才知道）
--------------------------
1. **中文必须逐字切词**。SQLite FTS5 的 unicode61 分词器把整串汉字当成一个
   token，「厚度模式」是一个词，搜「厚度」永远不命中。所以入库前在每个 CJK
   字符两侧插空格，查询时把词也切碎、再用双引号包成短语查询。
2. **HTML 只解析 <article> 那一段**。每页 440 KB，其中 400 KB 是侧边栏导航树；
   先切出正文再交给解析器，整体快一个数量级。
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
import zipfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
# 两个路径都允许环境变量覆盖：手册包可能在别处、索引可能想放到共享盘。
ZIP_PATH = (os.environ.get("BLENDER_MANUAL_ZIP")
            or os.path.join(HERE, "blender_manual_html.zip"))
DB_PATH = (os.environ.get("BLENDER_MANUAL_DB")
           or os.path.join(HERE, "manual", "manual.db"))

# 这些是导航页/索引页，正文没有内容价值
SKIP = {"404.html", "search.html", "genindex.html", "copyright.html",
        "versions.html", "py-modindex.html"}


# ---------------------------------------------------------------- 分词

def _is_wide(ch):
    """需要逐字切开的字符：汉字、假名、全角标点。"""
    o = ord(ch)
    return (0x3000 <= o <= 0x303F      # CJK 标点
            or 0x3040 <= o <= 0x30FF   # 假名
            or 0x3400 <= o <= 0x4DBF   # 扩展 A
            or 0x4E00 <= o <= 0x9FFF   # 基本区
            or 0xF900 <= o <= 0xFAFF   # 兼容表意
            or 0xFF00 <= o <= 0xFFEF)  # 全角


def tokenize(s):
    """CJK 逐字加空格，其余按原样 —— 得到 unicode61 能吃对的分词串。"""
    buf = []
    for ch in s:
        if _is_wide(ch):
            buf.append(" ")
            buf.append(ch)
            buf.append(" ")
        else:
            buf.append(ch)
    return " ".join("".join(buf).split())


def to_query(q, op="AND"):
    """把用户输入转成 FTS5 查询串。

    每个词一律用双引号包成短语：既让「厚度」变成短语 "厚 度"（连续匹配，
    不会命中「厚…度」分开出现的地方），也顺手消掉了 * ( ) : ^ NEAR 这些
    FTS5 运算符，避免用户随手输入一个 - 号就语法报错。
    """
    q = q.replace('"', " ")
    parts = []
    for raw in q.split():
        t = tokenize(raw)
        if t:
            parts.append('"%s"' % t)
    return (" %s " % op).join(parts)


# ---------------------------------------------------------------- 抽取

def _article_html(html):
    """切出 <article role="main"> 那一段。"""
    i = html.find("<article")
    if i < 0:
        return None
    j = html.find("</article>", i)
    if j < 0:
        return None
    return html[i:j]


_TAG_RE = re.compile(r"<[^>]+>")

# 这些标签前后各补一个换行 —— lxml 的 text_content() 会把全文连成一长串，
# 段落边界全丢，检索片段就没法读了。
_BLOCK = {"p", "div", "section", "article", "li", "ul", "ol", "dl", "dt", "dd",
          "tr", "td", "th", "table", "thead", "tbody", "figure", "figcaption",
          "pre", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "br", "hr"}


def _text_of(el):
    """带块级换行的纯文本。"""
    out = []

    def walk(e):
        if not isinstance(e.tag, str):        # 注释 / 处理指令
            return
        blk = e.tag in _BLOCK
        if blk:
            out.append("\n")
        if e.text:
            out.append(e.text)
        for c in e:
            walk(c)
            if c.tail:
                out.append(c.tail)
        if blk:
            out.append("\n")

    walk(el)
    return "".join(out)


def parse_page(html):
    """返回 (title, text)。text 是去掉标签、保留段落换行的纯文本。"""
    frag = _article_html(html)
    if frag is None:
        return None, None
    try:
        from lxml import html as lhtml
    except ImportError:
        return _parse_page_regex(frag)
    doc = lhtml.fromstring(frag)
    # 章节标题后面那个 ¶ 锚点、脚本样式的残留，先摘掉
    for el in doc.xpath('.//a[contains(@class,"headerlink")]'
                        ' | .//script | .//style | .//nav'):
        par = el.getparent()
        if par is not None:
            if el.tail:
                el.tail = ""
            par.remove(el)
    hs = doc.xpath(".//h1")
    title = re.sub(r"\s+", " ", _text_of(hs[0])).strip() if hs else ""
    # 标题单独存了一列，正文里不要再重复一遍（否则 --show 会打两行一样的）。
    # Sphinx 生成的 h1 后面紧跟块级元素，tail 只有空白，直接丢。
    for h in hs:
        par = h.getparent()
        if par is not None:
            par.remove(h)
    return title, _clean(_text_of(doc))


def _parse_page_regex(frag):
    """没有 bs4 时的退路：粗暴去标签。"""
    m = re.search(r"<h1[^>]*>(.*?)</h1>", frag, re.S)
    title = _TAG_RE.sub("", m.group(1)).strip() if m else ""
    return title, _clean(_TAG_RE.sub("\n", frag))


def _clean(raw):
    out = []
    for line in raw.split("\n"):
        s = line.strip()
        if not s:
            continue
        s = s.rstrip("¶").strip()          # 标题锚点符号
        if not s or s in ("¶", "\\", "--"):
            continue
        out.append(s)
    return "\n".join(out)


def iter_pages(zip_path):
    z = zipfile.ZipFile(zip_path)
    names = [n for n in z.namelist() if n.endswith(".html")]
    if not names:
        return
    root = names[0].split("/")[0] + "/"
    for n in sorted(names):
        rel = n[len(root):]
        if rel in SKIP or "/" in rel and rel.split("/")[-1] in SKIP:
            continue
        if rel.startswith("_sources/") or rel.startswith("_static/"):
            continue
        try:
            html = z.read(n).decode("utf-8", errors="replace")
        except Exception:
            continue
        title, text = parse_page(html)
        if not text:
            continue
        section = rel.split("/")[0] if "/" in rel else "(root)"
        if not title:
            m = re.search(r"<title>(.*?)</title>", html, re.S)
            title = _TAG_RE.sub("", m.group(1)).strip() if m else rel
            title = re.sub(r"\s*[-—]\s*Blender.*$", "", title)
        yield rel, section, title, text


# ---------------------------------------------------------------- anchors

def read_inventory(zip_path):
    """解析 objects.inv：Sphinx 交叉引用清单，含 3311 条 bpy.types.* 锚点。

    格式：4 行文本头 + zlib 压缩的 `名字 类型 优先级 位置 显示名` 文本。
    """
    z = zipfile.ZipFile(zip_path)
    names = [n for n in z.namelist() if n.endswith("objects.inv")]
    if not names:
        return []
    raw = z.read(names[0])
    head, body = raw.split(b"\n", 4)[:4], raw.split(b"\n", 4)[4]
    if b"version 2" not in head[0]:
        return []
    txt = zlib.decompress(body).decode("utf-8", errors="replace")
    rows = []
    for line in txt.splitlines():
        if not line.strip():
            continue
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        name, kind, _prio, loc, disp = parts
        if kind.startswith("py:"):
            # 函数签名在名字后面，截断到 '(' 之前
            name = name.split("(")[0]
        anchor = ""
        if "#" in loc:
            loc, anchor = loc.split("#", 1)
        rows.append((name, kind, loc, anchor, disp if disp != "-" else ""))
    return rows


# ---------------------------------------------------------------- 构建

DDL = [
    """CREATE TABLE pages (
           id INTEGER PRIMARY KEY,
           path TEXT UNIQUE, section TEXT, title TEXT,
           nchar INTEGER, text TEXT)""",
    """CREATE VIRTUAL TABLE pages_fts USING fts5(
           path UNINDEXED, title, body, tokenize='unicode61 remove_diacritics 2')""",
    """CREATE TABLE anchors (
           name TEXT, kind TEXT, page TEXT, anchor TEXT, disp TEXT)""",
    "CREATE INDEX ix_anchors_name ON anchors(name COLLATE NOCASE)",
    "CREATE INDEX ix_pages_section ON pages(section)",
]


def build(zip_path=ZIP_PATH, db_path=DB_PATH, verbose=True):
    if not os.path.exists(zip_path):
        raise SystemExit("找不到手册包：%s" % zip_path)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    tmp = db_path + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)

    con = sqlite3.connect(tmp)
    for sql in DDL:
        con.execute(sql)

    t0 = time.time()
    n_char = 0
    n = 0
    for i, (rel, section, title, text) in enumerate(iter_pages(zip_path), 1):
        cur = con.execute(
            "INSERT INTO pages(path, section, title, nchar, text) VALUES (?,?,?,?,?)",
            (rel, section, title, len(text), text))
        con.execute(
            "INSERT INTO pages_fts(rowid, path, title, body) VALUES (?,?,?,?)",
            (cur.lastrowid, rel, tokenize(title), tokenize(text)))
        n_char += len(text)
        n += 1
        if verbose and n % 300 == 0:
            print("  %4d 页  %6.1f 万字  %.1fs" % (n, n_char / 10000, time.time() - t0))

    inv = read_inventory(zip_path)
    con.executemany(
        "INSERT INTO anchors(name, kind, page, anchor, disp) VALUES (?,?,?,?,?)", inv)
    con.commit()
    con.execute("INSERT INTO pages_fts(pages_fts) VALUES('optimize')")
    con.commit()
    con.close()

    os.replace(tmp, db_path)
    if verbose:
        print("索引完成：%d 页 / %.1f 万字 / %d 条 API 锚点 / %.1f MB / %.0fs"
              % (n, n_char / 10000, len(inv),
                 os.path.getsize(db_path) / 1048576, time.time() - t0))
    return db_path


# ---------------------------------------------------------------- 检索

def ensure_db(db_path=None, auto=True):
    """索引不存在时尽量自愈：有手册包就直接建，没有就给出明确指令。

    没有自愈的话，任何「新会话第一次用」都会撞在 build 提示上，而那条提示
    对不知道手册包在哪的人是死路。
    """
    db_path = db_path or DB_PATH
    if os.path.exists(db_path):
        return db_path
    if auto and os.path.exists(ZIP_PATH):
        print("索引不存在，正在从手册包建立（约 4 秒）…", file=sys.stderr)
        build(ZIP_PATH, db_path, verbose=False)
        return db_path
    raise SystemExit(
        "索引不存在：%s\n"
        "  有手册包时：python docs/manual_index.py build\n"
        "  没有手册包：从 docs.blender.org 取 blender_manual_v520_zh-hans 离线包，\n"
        "              解出 blender_manual_html.zip 放到 docs/，\n"
        "              或用环境变量 BLENDER_MANUAL_ZIP / BLENDER_MANUAL_DB 指到别处"
        % db_path)


def _connect(db_path):
    con = sqlite3.connect("file:%s?mode=ro" % ensure_db(db_path).replace("\\", "/"),
                          uri=True)
    return con


def _snippet(text, terms, width=64):
    """在原文里定位，抓一段上下文。FTS 的 snippet() 用的是切碎后的文本，
    显示出来字间带空格，所以自己按原串找位置。"""
    low = text.lower()
    keys = [t.lower() for t in terms if t]
    best, best_score = 0, -1
    for k in keys:
        start = 0
        while True:
            i = low.find(k, start)
            if i < 0:
                break
            lo = max(0, i - width)
            win = low[lo:i + len(k) + width]
            score = sum(1 for kk in keys if kk in win)
            if score > best_score:
                best, best_score = i, score
            start = i + 1
            if best_score >= len(keys):
                break
        if best_score >= len(keys):
            break
    lo = max(0, best - width)
    hi = min(len(text), best + width * 2)
    s = text[lo:hi].replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return ("…" if lo > 0 else "") + s + ("…" if hi < len(text) else "")


def search(db_path, q, limit=8, section=None):
    terms = [raw for raw in q.split() if raw.strip()]
    if not terms:
        return []
    con = _connect(db_path)

    def run(expr, op):
        sql = ("SELECT f.path, p.section, p.title, p.text,"
               "       bm25(pages_fts, 0.0, 8.0, 1.0) AS rank"
               "  FROM pages_fts f JOIN pages p ON p.path = f.path"
               " WHERE pages_fts MATCH ?")
        args = [expr]
        if section:
            sql += " AND p.section = ?"
            args.append(section)
        sql += " ORDER BY rank LIMIT ?"
        args.append(limit)
        out = []
        for path, sec, title, text, rank in con.execute(sql, args):
            out.append({"path": path, "section": sec, "title": title,
                        "score": round(-rank, 3), "mode": op,
                        "snippet": _snippet(text, terms)})
        return out

    # 多个词先按 AND；全落空时退到 OR，并在结果里标明 —— 比直接回「没有命中」
    # 有用，因为手册用词和用户用词常常对不上（「重新网格化」手册写「重构网格」）。
    rows = run(to_query(q, "AND"), "AND")
    if not rows and len(terms) > 1:
        rows = run(to_query(q, "OR"), "OR")
    con.close()
    return rows


def api_lookup(db_path, name):
    """API 名 → 手册页。接受 `bpy.types.SolidifyModifier` / `SolidifyModifier` 两种写法。"""
    name = name.strip()
    cands = [name]
    if "." not in name:
        cands.insert(0, "bpy.types." + name.lower())
    con = _connect(db_path)
    rows = []
    for c in cands:
        rows = con.execute(
            "SELECT name, kind, page, anchor, disp FROM anchors"
            " WHERE name = ? COLLATE NOCASE"
            " ORDER BY length(name) LIMIT 20", (c,)).fetchall()
        if rows:
            break
    if not rows:
        rows = con.execute(
            "SELECT name, kind, page, anchor, disp FROM anchors"
            " WHERE name LIKE ? ORDER BY length(name) LIMIT 20",
            ("%" + name + "%",)).fetchall()
    con.close()
    return [{"name": r[0], "kind": r[1], "page": r[2], "anchor": r[3],
             "disp": r[4]} for r in rows]


def show(db_path, path):
    con = _connect(db_path)
    r = con.execute("SELECT section, title, nchar, text FROM pages WHERE path = ?",
                    (path,)).fetchone()
    con.close()
    return r


def stats(db_path):
    con = _connect(db_path)
    n, ch = con.execute("SELECT COUNT(*), SUM(nchar) FROM pages").fetchone()
    secs = con.execute("SELECT section, COUNT(*), SUM(nchar) FROM pages"
                       " GROUP BY section ORDER BY SUM(nchar) DESC").fetchall()
    kinds = con.execute("SELECT kind, COUNT(*) FROM anchors GROUP BY kind"
                        " ORDER BY COUNT(*) DESC").fetchall()
    con.close()
    return {"pages": n, "chars": ch, "sections": secs, "anchor_kinds": kinds,
            "size_mb": round(os.path.getsize(db_path) / 1048576, 1)}


# 自检用例：查询词 → 必须出现在 top5 里的页面。
# 挑的是手册里改不了的固定术语，不是「大概相关」的模糊词 —— 免得手册更新一次就红一片。
SELFCHECK_QUERIES = [
    ("重构网格", "modeling/modifiers/generate/remesh.html"),
    ("四边面 三角面", "modeling/meshes/editing/face/triangles_quads.html"),
    ("偏移 实体化", "modeling/modifiers/generate/solidify.html"),
    ("自动权重", "animation/armatures/skinning/parenting.html"),
    ("按距离合并", "modeling/meshes/editing/mesh/merge.html"),
]
SELFCHECK_APIS = [
    ("bpy.types.SolidifyModifier", "modeling/modifiers/generate/solidify.html"),
    ("SolidifyModifier", "modeling/modifiers/generate/solidify.html"),   # 短名也要能查
]


def selfcheck(db_path=DB_PATH, limit=5):
    """回归自检：索引是否完整、已知问题的答案是否还查得到。

    和 BlenderAPI 那边的 verify_catalog.py 一个思路 —— 不只看「跑通了」，
    要能判定「查出来的东西对不对」。
    """
    tally = {"ok": 0, "fail": 0}

    def rep(name, good, detail):
        tally["ok" if good else "fail"] += 1
        print("%s  %-30s %s" % ("PASS" if good else "FAIL", name, detail))

    s = stats(db_path)
    rep("页数", s["pages"] >= 2300, "%d 页（要求 ≥2300）" % s["pages"])
    rep("正文字数", s["chars"] >= 1400000,
        "%.1f 万字（要求 ≥140 万）" % (s["chars"] / 10000.0))
    con = _connect(db_path)
    na = con.execute(
        "SELECT COUNT(*) FROM anchors WHERE name LIKE 'bpy.types.%'").fetchone()[0]
    con.close()
    rep("API 锚点", na >= 3000, "%d 条 bpy.types.*（要求 ≥3000）" % na)

    for q, want in SELFCHECK_QUERIES:
        got = [r["path"] for r in search(db_path, q, limit)]
        good = want in got
        rep("查「%s」" % q, good,
            want if good else "top%d 里没有它，实际前两条：%s" % (limit, got[:2]))

    for a, want in SELFCHECK_APIS:
        got = [r["page"] for r in api_lookup(db_path, a)]
        good = want in got
        rep("锚点「%s」" % a, good,
            want if good else "实际：%s" % got[:2])

    print("\nPASS %d / FAIL %d" % (tally["ok"], tally["fail"]))
    return 0 if tally["fail"] == 0 else 1


# ---------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="离线 Blender 手册检索（先 build 一次，之后只读）")
    ap.add_argument("query", nargs="*", help="检索词；多个词是 AND 关系")
    ap.add_argument("--build", action="store_true", help="重建索引")
    ap.add_argument("--api", metavar="NAME", help="按 API 名查手册锚点，如 bpy.types.SolidifyModifier")
    ap.add_argument("--show", metavar="PATH", help="打印整页正文")
    ap.add_argument("--stats", action="store_true", help="索引概况")
    ap.add_argument("--selfcheck", action="store_true",
                    help="回归自检：索引完整性 + 已知问题的答案是否还查得到")
    ap.add_argument("--section", help="限定一级目录，如 modeling")
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    a = ap.parse_args(argv)

    # 允许 `manual_index.py build` 这种子命令写法，和 --build 等价
    if a.query == ["build"] and not (a.api or a.show or a.stats or a.selfcheck):
        a.build, a.query = True, []

    if a.build:
        build()
        return 0
    if a.selfcheck:
        return selfcheck(limit=a.limit)
    if a.stats:
        s = stats(DB_PATH)
        if a.json:
            print(json.dumps(s, ensure_ascii=False, indent=1))
        else:
            print("%d 页 / %.1f 万字 / %.1f MB" % (s["pages"], s["chars"] / 10000, s["size_mb"]))
            for sec, n, ch in s["sections"]:
                print("  %-20s %5d 页  %7.1f 万字" % (sec, n, ch / 10000))
            print("锚点：" + "  ".join("%s=%d" % (k, n) for k, n in s["anchor_kinds"]))
        return 0
    if a.api:
        rows = api_lookup(DB_PATH, a.api)
        if a.json:
            print(json.dumps(rows, ensure_ascii=False, indent=1))
        elif not rows:
            print("未找到锚点：%s" % a.api)
        else:
            for r in rows:
                print("%-44s %s" % (r["name"], r["disp"]))
                print("   %s#%s" % (r["page"], r["anchor"]))
        return 0 if rows else 1
    if a.show:
        r = show(DB_PATH, a.show)
        if not r:
            print("没有这一页：%s" % a.show, file=sys.stderr)
            return 1
        print("# %s  [%s]  %d 字\n" % (r[1], r[0], r[2]))
        print(r[3])
        return 0
    if not a.query:
        ap.print_help()
        return 0

    q = " ".join(a.query)
    rows = search(DB_PATH, q, a.limit, a.section)
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0
    if not rows:
        print("没有命中：%s" % q)
        return 1
    if rows[0]["mode"] == "OR":
        print("（没有页面同时包含全部检索词，以下按「任一命中」列出）\n")
    for i, r in enumerate(rows, 1):
        print("%d. [%s] %s" % (i, r["section"], r["title"]))
        print("   %s  (score %.1f)" % (r["path"], r["score"]))
        print("   %s\n" % r["snippet"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
