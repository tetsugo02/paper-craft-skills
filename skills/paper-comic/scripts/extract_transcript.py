#!/usr/bin/env python3
"""
Claude Code / Codex のセッションログ（.jsonl）から，ユーザーとアシスタントの発言本文だけを
ターン番号付き Markdown に抽出する（paper-comic の discussion mode 用）．

Usage:
  python3 extract_transcript.py session.jsonl [more.jsonl ...]
  python3 extract_transcript.py --latest claude [--cwd /path/to/project]
  python3 extract_transcript.py --latest codex  [--cwd /path/to/project]
  python3 extract_transcript.py --list claude|codex [--cwd /path/to/project]
  options: --since T30  --until T80  --max-chars 4000  -o discussion.md

Log locations:
  Claude Code: ~/.claude/projects/<cwd with / replaced by ->/<session>.jsonl
  Codex:       ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl  (or $CODEX_HOME/sessions)
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

NOISE_PREFIXES = (
    "<environment_context>", "<user_instructions>", "<permissions instructions>",
    "# AGENTS.md instructions", "<command-name>", "<command-message>", "<local-command-stdout>",
    "<local-command-stderr>", "Caveat: The messages below were generated", "<turn_aborted>",
)
TAG_RE = re.compile(r"<(system-reminder|command-args|local-command-caveat)>.*?</\1>", re.S)


def clean(text):
    text = TAG_RE.sub("", text or "").strip()
    if not text or text.startswith(NOISE_PREFIXES):
        return ""
    return text


def _texts(content, kinds):
    if isinstance(content, str):
        return [content]
    out = []
    for c in content or []:
        if isinstance(c, dict) and c.get("type") in kinds and c.get("text"):
            out.append(c["text"])
    return out


def parse_claude(lines):
    turns = []
    for obj in lines:
        if obj.get("isMeta") or obj.get("isSidechain"):
            continue
        t = obj.get("type")
        msg = obj.get("message") or {}
        if t == "user":
            content = msg.get("content")
            if isinstance(content, list) and any(
                    isinstance(c, dict) and c.get("type") == "tool_result" for c in content):
                continue
            for x in _texts(content, {"text"}):
                x = clean(x)
                if x:
                    turns.append(("User", x, obj.get("timestamp")))
        elif t == "assistant":
            txt = "\n".join(_texts(msg.get("content"), {"text"})).strip()
            if txt:
                # consecutive assistant chunks (same message split by tool calls) are merged
                if turns and turns[-1][0] == "Assistant":
                    turns[-1] = ("Assistant", turns[-1][1] + "\n\n" + txt, turns[-1][2])
                else:
                    turns.append(("Assistant", txt, obj.get("timestamp")))
    return turns


def parse_codex(lines):
    turns, fallback = [], []
    for obj in lines:
        t, p = obj.get("type"), obj.get("payload") or {}
        if t == "response_item" and p.get("type") == "message":
            role = p.get("role")
            if role not in ("user", "assistant"):
                continue
            txt = "\n".join(_texts(p.get("content"), {"input_text", "output_text", "text"}))
            txt = clean(txt)
            if not txt:
                continue
            who = "User" if role == "user" else "Assistant"
            if turns and turns[-1][0] == who == "Assistant":
                turns[-1] = (who, turns[-1][1] + "\n\n" + txt, turns[-1][2])
            else:
                turns.append((who, txt, obj.get("timestamp")))
        elif t == "event_msg" and p.get("type") in ("user_message", "agent_message"):
            txt = clean(p.get("message", ""))
            if txt:
                fallback.append(("User" if p["type"] == "user_message" else "Assistant", txt,
                                 obj.get("timestamp")))
        elif obj.get("type") == "message" and obj.get("role") in ("user", "assistant"):  # old format
            txt = clean("\n".join(_texts(obj.get("content"), {"input_text", "output_text", "text"})))
            if txt:
                turns.append(("User" if obj["role"] == "user" else "Assistant", txt, None))
    return turns or fallback


def load(path):
    lines = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                lines.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
    is_codex = any(o.get("type") in ("session_meta", "response_item", "event_msg", "turn_context")
                   for o in lines[:50])
    return (parse_codex if is_codex else parse_claude)(lines), ("codex" if is_codex else "claude")


# --------------------------------------------------------------------------- #
# session discovery
# --------------------------------------------------------------------------- #
def claude_sessions(cwd=None):
    root = Path.home() / ".claude" / "projects"
    if not root.exists():
        return []
    if cwd:
        slug = re.sub(r"[^A-Za-z0-9]", "-", str(Path(cwd).expanduser().resolve()))
        dirs = [d for d in root.iterdir() if d.is_dir() and d.name == slug]
    else:
        dirs = [d for d in root.iterdir() if d.is_dir()]
    return sorted((f for d in dirs for f in d.glob("*.jsonl")), key=lambda f: f.stat().st_mtime)


def codex_cwd(f):
    try:
        with open(f, encoding="utf-8", errors="replace") as fh:
            for _ in range(20):
                ln = fh.readline()
                if not ln:
                    break
                o = json.loads(ln)
                p = o.get("payload") or {}
                if p.get("cwd"):
                    return p["cwd"]
    except (OSError, json.JSONDecodeError):
        pass
    return None


def codex_sessions(cwd=None):
    root = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "sessions"
    if not root.exists():
        return []
    files = sorted(root.rglob("rollout-*.jsonl"), key=lambda f: f.stat().st_mtime)
    if cwd:
        want = str(Path(cwd).expanduser().resolve())
        files = [f for f in files if (codex_cwd(f) or "").rstrip("/") == want.rstrip("/")]
    return files


def first_user_line(path):
    turns, _ = load(path)
    for who, txt, _ts in turns:
        if who == "User":
            return txt.splitlines()[0][:80]
    return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--latest", choices=["claude", "codex"])
    ap.add_argument("--list", choices=["claude", "codex"])
    ap.add_argument("--cwd", help="project directory to filter sessions")
    ap.add_argument("--since", help="first turn to keep, e.g. T30")
    ap.add_argument("--until", help="last turn to keep, e.g. T80")
    ap.add_argument("--max-chars", type=int, default=6000, help="truncate each turn (0 = no limit)")
    ap.add_argument("-o", "--output")
    a = ap.parse_args()

    finder = {"claude": claude_sessions, "codex": codex_sessions}
    if a.list:
        for f in finder[a.list](a.cwd)[-30:]:
            print(f"{f}\t{first_user_line(f)}")
        return
    files = [Path(f) for f in a.files]
    if a.latest:
        cands = finder[a.latest](a.cwd)
        if not cands:
            sys.exit(f"No {a.latest} sessions found" + (f" for cwd={a.cwd}" if a.cwd else ""))
        files.append(cands[-1])
    if not files:
        ap.error("give session file(s) or --latest/--list")

    lo = int(a.since.lstrip("Tt")) if a.since else 1
    hi = int(a.until.lstrip("Tt")) if a.until else 10 ** 9
    out = ["# Discussion transcript", ""]
    n = 0
    for f in files:
        turns, kind = load(f)
        out += [f"<!-- source: {f} ({kind}, {len(turns)} turns) -->", ""]
        for who, txt, ts in turns:
            n += 1
            if not (lo <= n <= hi):
                continue
            if a.max_chars and len(txt) > a.max_chars:
                txt = txt[:a.max_chars] + f"\n…[truncated {len(txt) - a.max_chars} chars]"
            stamp = f" ({ts[:16]})" if isinstance(ts, str) else ""
            out.append(f"### [T{n}] {who}{stamp}\n\n{txt}\n")
    text = "\n".join(out)
    if a.output:
        Path(a.output).write_text(text, encoding="utf-8")
        print(f"wrote {a.output} ({n} turns)", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
