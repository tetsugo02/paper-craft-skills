#!/usr/bin/env python3
"""
Markdown -> Notion page publisher (stdlib only).

Notion MCP が使えない環境（CI，MCP未設定のCodex/Claude Code 等）向けのフォールバック．
ローカル画像は Notion File Upload API で添付する．

Usage:
  export NOTION_TOKEN=ntn_xxx            # Internal integration token
  python3 notion_publish.py article.md --parent <page-url-or-id>
  python3 notion_publish.py article.md --parent <database-url-or-id> --parent-type database
  python3 notion_publish.py article.md --replace <existing-page-url-or-id>   # 中身を差し替え
  python3 notion_publish.py article.md --replace auto   # 前回公開先（article.notion.json）を更新
  python3 notion_publish.py article.md --dry-run                              # 送信せずブロックJSONを表示

Supported markdown:
  # / ## / ### (#### 以下は heading_3), paragraphs, - / * / 1. lists (1段ネスト),
  - [ ] / - [x] to-do, > quote, > [!NOTE] callout, ``` code (```mermaid 含む),
  $$ ... $$ equation block, | tables |, ![alt](local.png|https://...), ---,
  inline: **bold**, *italic*, _italic_, ~~strike~~, `code`, [text](url), $inline math$
"""

import argparse
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
MAX_TEXT = 1900          # rich_text content limit is 2000
MAX_CHILDREN = 100       # per request

CODE_LANGS = {
    "py": "python", "python": "python", "js": "javascript", "javascript": "javascript",
    "ts": "typescript", "typescript": "typescript", "sh": "shell", "bash": "bash",
    "shell": "shell", "zsh": "shell", "json": "json", "yaml": "yaml", "yml": "yaml",
    "mermaid": "mermaid", "c": "c", "cpp": "c++", "c++": "c++", "cuda": "c++",
    "java": "java", "go": "go", "rust": "rust", "rs": "rust", "html": "html",
    "css": "css", "sql": "sql", "latex": "latex", "tex": "latex", "markdown": "markdown",
    "md": "markdown", "toml": "toml", "r": "r", "julia": "julia", "ruby": "ruby",
    "diff": "diff", "dockerfile": "docker", "makefile": "makefile", "text": "plain text",
    "txt": "plain text", "": "plain text",
}

CALLOUT_ICONS = {"NOTE": "📝", "TIP": "💡", "IMPORTANT": "❗", "WARNING": "⚠️",
                 "CAUTION": "🛑", "TODO": "🚧", "QUESTION": "❓", "DECISION": "✅"}


# --------------------------------------------------------------------------- #
# Inline markdown -> rich_text
# --------------------------------------------------------------------------- #
INLINE_RE = re.compile(
    r"(?P<code>`[^`]+`)"
    r"|(?P<eq>(?<![\\$])\$(?!\s)[^$\n]+?(?<!\s)\$(?!\$))"
    r"|(?P<link>\[[^\]]+\]\([^)\s]+\))"
    r"|(?P<bold>\*\*[^*]+\*\*|__[^_]+__)"
    r"|(?P<strike>~~[^~]+~~)"
    r"|(?P<italic>(?<![*\w])\*[^*\n]+\*(?!\*)|(?<![_\w])_[^_\n]+_(?![_\w]))"
)


def _text(content, ann=None, link=None):
    out = []
    for i in range(0, max(len(content), 1), MAX_TEXT):
        chunk = content[i:i + MAX_TEXT]
        if not chunk:
            continue
        rt = {"type": "text", "text": {"content": chunk}}
        if link:
            rt["text"]["link"] = {"url": link}
        if ann:
            rt["annotations"] = dict(ann)
        out.append(rt)
    return out


def rich(text, ann=None):
    """Convert inline markdown to Notion rich_text array."""
    ann = dict(ann or {})
    out, pos = [], 0
    for m in INLINE_RE.finditer(text):
        if m.start() > pos:
            out += _text(text[pos:m.start()], ann or None)
        kind, tok = m.lastgroup, m.group(0)
        if kind == "code":
            out += _text(tok[1:-1], {**ann, "code": True})
        elif kind == "eq":
            out.append({"type": "equation", "equation": {"expression": tok[1:-1]}})
        elif kind == "link":
            lm = re.match(r"\[([^\]]+)\]\(([^)\s]+)\)", tok)
            label, url = lm.group(1), lm.group(2)
            if re.match(r"https?://", url):
                out += [dict(r, text={**r["text"], "link": {"url": url}}) if r["type"] == "text" else r
                        for r in rich(label, ann)]
            else:
                out += rich(f"{label} ({url})", ann)
        elif kind == "bold":
            out += rich(tok[2:-2], {**ann, "bold": True})
        elif kind == "strike":
            out += rich(tok[2:-2], {**ann, "strikethrough": True})
        elif kind == "italic":
            out += rich(tok[1:-1], {**ann, "italic": True})
        pos = m.end()
    if pos < len(text):
        out += _text(text[pos:], ann or None)
    return out


# --------------------------------------------------------------------------- #
# Block-level markdown -> blocks
# --------------------------------------------------------------------------- #
def _is_cjk(ch):
    return bool(re.match(r"[　-ヿ㐀-鿿豈-﫿＀-￯]", ch))


def blk(btype, **payload):
    return {"object": "block", "type": btype, btype: payload}


def strip_html(line):
    return re.sub(r"<[^>]+>", "", line)


def parse_table(lines):
    rows = []
    for ln in lines:
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        rows.append(cells)
    width = max(len(r) for r in rows)
    children = []
    for r in rows:
        r = r + [""] * (width - len(r))
        children.append({"object": "block", "type": "table_row",
                         "table_row": {"cells": [rich(c) for c in r]}})
    return blk("table", table_width=width, has_column_header=True,
               has_row_header=False, children=children)


def md_to_blocks(md, base_dir, uploader):
    lines = md.replace("\r\n", "\n").split("\n")
    # front matter
    if lines and lines[0].strip() == "---":
        for j in range(1, len(lines)):
            if lines[j].strip() == "---":
                lines = lines[j + 1:]
                break
    blocks, i, para = [], 0, []

    def flush_para():
        nonlocal para
        if para:
            text = ""
            for part in (x.strip() for x in para):
                if text and not (_is_cjk(text[-1]) and part and _is_cjk(part[0])):
                    text += " "
                text += part
            text = text.strip()
            if text:
                blocks.append(blk("paragraph", rich_text=rich(text)))
            para = []

    list_re = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
    while i < len(lines):
        line = lines[i]
        s = line.strip()

        # fenced code
        fm = re.match(r"^\s*(`{3,}|~{3,})\s*([\w+#-]*)", line)
        if fm:
            flush_para()
            fence, lang = fm.group(1), fm.group(2).lower()
            buf, i = [], i + 1
            while i < len(lines) and not re.fullmatch(re.escape(fence) + r"[`~]*", lines[i].strip()):
                buf.append(lines[i])
                i += 1
            i += 1
            code = "\n".join(buf)
            blocks.append(blk("code", language=CODE_LANGS.get(lang, "plain text"),
                              rich_text=_text(code) or _text(" ")))
            continue
        # html <pre class="mermaid">
        if s.startswith('<pre class="mermaid">'):
            flush_para()
            buf = [s[len('<pre class="mermaid">'):]]
            i += 1
            while i < len(lines) and "</pre>" not in buf[-1]:
                buf.append(lines[i])
                i += 1
            code = "\n".join(buf).replace("</pre>", "").strip()
            blocks.append(blk("code", language="mermaid", rich_text=_text(code)))
            continue
        # equation block
        if s.startswith("$$"):
            flush_para()
            if s.endswith("$$") and len(s) > 4:
                expr = s[2:-2]
                i += 1
            else:
                buf, i = [s[2:]], i + 1
                while i < len(lines) and not lines[i].strip().endswith("$$"):
                    buf.append(lines[i])
                    i += 1
                if i < len(lines):
                    buf.append(lines[i].strip()[:-2])
                i += 1
                expr = "\n".join(buf)
            blocks.append(blk("equation", expression=expr.strip()))
            continue
        if not s:
            flush_para()
            i += 1
            continue
        # headings
        hm = re.match(r"^(#{1,6})\s+(.*)$", s)
        if hm:
            flush_para()
            level = min(len(hm.group(1)), 3)
            blocks.append(blk(f"heading_{level}", rich_text=rich(hm.group(2).strip())))
            i += 1
            continue
        # divider
        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", s):
            flush_para()
            blocks.append(blk("divider"))
            i += 1
            continue
        # image (standalone)
        im = re.fullmatch(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", s)
        if im:
            flush_para()
            blocks.append(image_block(im.group(2), im.group(1), base_dir, uploader))
            i += 1
            continue
        # table
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            flush_para()
            buf = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                buf.append(lines[i])
                i += 1
            blocks.append(parse_table(buf))
            continue
        # quote / callout
        if s.startswith(">"):
            flush_para()
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].strip())
                i += 1
            cm = re.match(r"^\[!(\w+)\]\s*(.*)$", buf[0]) if buf else None
            if cm:
                kind = cm.group(1).upper()
                body = " ".join([cm.group(2)] + buf[1:]).strip()
                blocks.append(blk("callout", rich_text=rich(body),
                                  icon={"type": "emoji", "emoji": CALLOUT_ICONS.get(kind, "📌")}))
            else:
                blocks.append(blk("quote", rich_text=rich(" ".join(buf))))
            continue
        # lists
        lm = list_re.match(line)
        if lm:
            flush_para()
            base_indent = len(lm.group(1))
            while i < len(lines):
                lm = list_re.match(lines[i])
                if not lm:
                    # continuation line of previous item
                    if lines[i].startswith("  ") and lines[i].strip() and blocks:
                        tgt = blocks[-1]
                        if tgt.get("_children"):
                            tgt = tgt["_children"][-1]
                        tgt[tgt["type"]]["rich_text"] += rich(" " + lines[i].strip())
                        i += 1
                        continue
                    break
                indent, marker, body = len(lm.group(1)), lm.group(2), lm.group(3)
                todo = re.match(r"^\[([ xX])\]\s+(.*)$", body)
                if todo:
                    b = blk("to_do", rich_text=rich(todo.group(2)), checked=todo.group(1) != " ")
                elif marker[0].isdigit():
                    b = blk("numbered_list_item", rich_text=rich(body))
                else:
                    b = blk("bulleted_list_item", rich_text=rich(body))
                if indent > base_indent and blocks and blocks[-1]["type"] in (
                        "bulleted_list_item", "numbered_list_item", "to_do"):
                    blocks[-1].setdefault("_children", []).append(b)
                else:
                    blocks.append(b)
                i += 1
            continue
        # html-only lines (e.g. <div>) -> strip tags
        if s.startswith("<") and s.endswith(">"):
            t = strip_html(s).strip()
            if t:
                para.append(t)
            i += 1
            continue
        para.append(line)
        i += 1
    flush_para()

    # move nested children into proper place
    for b in blocks:
        ch = b.pop("_children", None)
        if ch:
            b[b["type"]]["children"] = ch
    return blocks


def image_block(src, alt, base_dir, uploader):
    caption = rich(alt) if alt else []
    if re.match(r"https?://", src):
        return blk("image", type="external", external={"url": src}, caption=caption)
    path = (base_dir / src).resolve()
    if not path.exists():
        return blk("callout", rich_text=rich(f"[missing image] {src}"),
                   icon={"type": "emoji", "emoji": "🖼️"})
    fid = uploader(path)
    if fid is None:  # dry-run
        return blk("image", type="file_upload", file_upload={"id": f"<upload:{path.name}>"},
                   caption=caption)
    return blk("image", type="file_upload", file_upload={"id": fid}, caption=caption)


# --------------------------------------------------------------------------- #
# Notion API
# --------------------------------------------------------------------------- #
class Notion:
    def __init__(self, token):
        self.token = token

    def req(self, method, path, body=None, raw=None, ctype="application/json"):
        url = path if path.startswith("http") else API + path
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        headers = {"Authorization": f"Bearer {self.token}", "Notion-Version": NOTION_VERSION}
        if data is not None:
            headers["Content-Type"] = ctype
        for attempt in range(5):
            r = urllib.request.Request(url, data=data, method=method, headers=headers)
            try:
                with urllib.request.urlopen(r, timeout=120) as resp:
                    txt = resp.read().decode()
                    return json.loads(txt) if txt else {}
            except urllib.error.HTTPError as e:
                msg = e.read().decode(errors="replace")
                if e.code in (429, 500, 502, 503, 504) and attempt < 4:
                    time.sleep(float(e.headers.get("Retry-After", 2 ** attempt)))
                    continue
                raise SystemExit(f"Notion API error {e.code} on {method} {path}: {msg}")

    def upload(self, path: Path):
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        fu = self.req("POST", "/file_uploads", {"filename": path.name, "content_type": ctype})
        boundary = uuid.uuid4().hex
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
                f"filename=\"{path.name}\"\r\nContent-Type: {ctype}\r\n\r\n").encode()
        body += path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        self.req("POST", f"/file_uploads/{fu['id']}/send", raw=body,
                 ctype=f"multipart/form-data; boundary={boundary}")
        return fu["id"]

    def append(self, block_id, blocks):
        for k in range(0, len(blocks), MAX_CHILDREN):
            self.req("PATCH", f"/blocks/{block_id}/children", {"children": blocks[k:k + MAX_CHILDREN]})

    def clear(self, block_id):
        cursor = None
        while True:
            q = f"/blocks/{block_id}/children?page_size=100" + (f"&start_cursor={cursor}" if cursor else "")
            res = self.req("GET", q)
            for b in res.get("results", []):
                self.req("DELETE", f"/blocks/{b['id']}")
            if not res.get("has_more"):
                break
            cursor = res.get("next_cursor")

    def title_prop(self, database_id):
        db = self.req("GET", f"/databases/{database_id}")
        for name, p in db.get("properties", {}).items():
            if p.get("type") == "title":
                return name
        return "Name"


def notion_id(s):
    m = re.findall(r"[0-9a-fA-F]{32}|[0-9a-fA-F-]{36}", s or "")
    if not m:
        raise SystemExit(f"Cannot parse Notion id from: {s}")
    h = m[-1].replace("-", "")
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("markdown")
    ap.add_argument("--parent", default=os.environ.get("NOTION_PARENT_ID"),
                    help="parent page/database URL or id (default: $NOTION_PARENT_ID)")
    ap.add_argument("--parent-type", choices=["page", "database"], default="page")
    ap.add_argument("--replace", help="existing page URL/id, or 'auto' to reuse <md>.notion.json")
    ap.add_argument("--title", help="page title (default: first H1)")
    ap.add_argument("--icon", default="📄")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = Path(a.markdown).resolve()
    md = src.read_text(encoding="utf-8")
    title = a.title
    if not title:
        m = re.search(r"^#\s+(.+)$", md, re.M)
        title = m.group(1).strip() if m else src.stem
        if m:  # H1 becomes the page title; drop it from body
            md = md[:m.start()] + md[m.end():]

    if a.dry_run:
        blocks = md_to_blocks(md, src.parent, lambda p: None)
        print(json.dumps({"title": title, "blocks": blocks}, ensure_ascii=False, indent=2))
        print(f"\n# {len(blocks)} top-level blocks", file=sys.stderr)
        return

    token = os.environ.get("NOTION_TOKEN") or os.environ.get("NOTION_API_KEY")
    if not token:
        raise SystemExit("NOTION_TOKEN is not set. Create an internal integration at "
                         "https://www.notion.so/profile/integrations and share the parent page with it.")
    api = Notion(token)
    blocks = md_to_blocks(md, src.parent, api.upload)

    sidecar = src.with_suffix(".notion.json")
    if a.replace == "auto":
        if not sidecar.exists():
            raise SystemExit(f"--replace auto: {sidecar.name} not found (publish once without --replace)")
        a.replace = json.loads(sidecar.read_text())["page_id"]
    if a.replace:
        pid = notion_id(a.replace)
        api.req("PATCH", f"/pages/{pid}", {"properties": {"title": {"title": _text(title)}}})
        api.clear(pid)
        api.append(pid, blocks)
        page = api.req("GET", f"/pages/{pid}")
    else:
        if not a.parent:
            raise SystemExit("--parent (or $NOTION_PARENT_ID) is required")
        parent_id = notion_id(a.parent)
        if a.parent_type == "database":
            parent = {"database_id": parent_id}
            props = {api.title_prop(parent_id): {"title": _text(title)}}
        else:
            parent = {"page_id": parent_id}
            props = {"title": {"title": _text(title)}}
        page = api.req("POST", "/pages", {
            "parent": parent, "properties": props,
            "icon": {"type": "emoji", "emoji": a.icon},
            "children": blocks[:MAX_CHILDREN]})
        api.append(page["id"], blocks[MAX_CHILDREN:])
    sidecar.write_text(json.dumps({"page_id": page["id"], "url": page.get("url"), "title": title,
                                   "updated": time.strftime("%Y-%m-%dT%H:%M:%S")},
                                  ensure_ascii=False, indent=2))
    print(page.get("url", page.get("id")))


if __name__ == "__main__":
    main()
