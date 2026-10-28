#!/usr/bin/env python3
"""
リポジトリの「地図」を Markdown で出力する（paper-comic の code / design mode 用）．

- ファイル別の行数
- Python: クラス（基底クラス）・関数・メソッド（行番号，forward/__call__ のシグネチャ）・ローカル import 依存
- その他の言語: class / def / function / fn / func を正規表現で抽出
- エントリポイント候補（__main__, argparse, hydra, click/typer）
- 実装状態の手がかり: TODO / FIXME / XXX / NotImplementedError / `pass` だけの関数 / `...` 本体

Usage:
  python3 code_map.py <repo_dir> [--max-files 400] [--include-tests] > code-map.md
"""

import argparse
import ast
import os
import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv", "env",
             ".mypy_cache", ".pytest_cache", ".tox", "build", "dist", ".idea", ".vscode",
             "wandb", "outputs", "logs", "checkpoints", "data", "datasets", ".ipynb_checkpoints",
             "site-packages", ".eggs", "target"}
CODE_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".go", ".java", ".kt", ".c", ".cc",
            ".cpp", ".h", ".hpp", ".cu", ".jl", ".rb", ".swift", ".scala", ".m", ".sh"}
CONF_EXT = {".yaml", ".yml", ".toml", ".json", ".cfg", ".ini"}
GENERIC_DEF = re.compile(
    r"^\s*(?:export\s+)?(?:pub(?:\(crate\))?\s+)?(?:async\s+)?"
    r"(class|struct|enum|trait|interface|impl|function|fn|func|def)\s+([A-Za-z_][\w:<>]*)")
MARK_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b[:\s]*(.*)")


def iter_files(root, include_tests):
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS and not d.startswith("."))
        if not include_tests:
            dns[:] = [d for d in dns if d not in ("tests", "test", "__tests__")]
        for fn in sorted(fns):
            p = Path(dp) / fn
            if p.suffix in CODE_EXT | CONF_EXT or fn in ("Makefile", "Dockerfile"):
                if not include_tests and re.match(r"(test_.*|.*_test)\.py$", fn):
                    continue
                try:
                    if p.stat().st_size > 1_500_000:
                        continue
                except OSError:
                    continue
                yield p


def is_stub(fn):
    body = [b for b in fn.body if not (isinstance(b, ast.Expr) and isinstance(getattr(b, "value", None), ast.Constant)
                                       and isinstance(b.value.value, str))]
    if not body:
        return True
    if len(body) == 1:
        b = body[0]
        if isinstance(b, ast.Pass):
            return True
        if isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant) and b.value.value is Ellipsis:
            return True
        if isinstance(b, ast.Raise):
            exc = b.exc
            name = getattr(getattr(exc, "func", exc), "id", "")
            return name == "NotImplementedError"
    return False


def sig(fn):
    try:
        args = ast.unparse(fn.args)
    except Exception:
        args = ", ".join(a.arg for a in fn.args.args)
    ret = ""
    if fn.returns is not None:
        try:
            ret = " -> " + ast.unparse(fn.returns)
        except Exception:
            pass
    return f"({args}){ret}"


def py_info(path, text, local_mods):
    info = {"defs": [], "imports": set(), "stubs": [], "entry": []}
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        info["defs"].append(f"- ⚠ SyntaxError: {e}")
        return info
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            bases = ", ".join(ast.unparse(b) for b in node.bases) if node.bases else ""
            info["defs"].append(f"- class `{node.name}`({bases}) L{node.lineno}-{node.end_lineno}")
            for m in node.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    show_sig = m.name in ("forward", "__call__", "__init__", "step", "loss",
                                          "compute_loss", "training_step", "predict", "sample")
                    s = sig(m) if show_sig else ""
                    info["defs"].append(f"  - `{m.name}{s}` L{m.lineno}")
                    if is_stub(m):
                        info["stubs"].append(f"L{m.lineno} {node.name}.{m.name}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            info["defs"].append(f"- def `{node.name}{sig(node)}` L{node.lineno}-{node.end_lineno}")
            if is_stub(node):
                info["stubs"].append(f"L{node.lineno} {node.name}")
        elif isinstance(node, ast.If):
            try:
                if "__main__" in ast.unparse(node.test):
                    info["entry"].append(f"`__main__` L{node.lineno}")
            except Exception:
                pass
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                top = n.name.split(".")[0]
                if top in local_mods:
                    info["imports"].add(n.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                info["imports"].add("." * node.level + (node.module or ""))
            elif node.module and node.module.split(".")[0] in local_mods:
                info["imports"].add(node.module)
        elif isinstance(node, ast.Raise) and node.exc is not None:
            name = getattr(getattr(node.exc, "func", node.exc), "id", "")
            if name == "NotImplementedError":
                info["stubs"].append(f"L{node.lineno} raise NotImplementedError")
    for kw, label in (("argparse", "argparse"), ("@hydra.main", "hydra"), ("typer", "typer"),
                      ("@click.", "click")):
        if kw in text:
            info["entry"].append(label)
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--max-files", type=int, default=400)
    ap.add_argument("--include-tests", action="store_true")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    files = list(iter_files(root, a.include_tests))[:a.max_files]
    local_mods = {p.relative_to(root).parts[0].removesuffix(".py") for p in files if p.suffix == ".py"}
    local_mods |= {p.parent.name for p in files if p.name == "__init__.py"}

    out = [f"# Code map: {root.name}", "", f"- root: `{root}`", f"- files scanned: {len(files)}", ""]
    readme = next((root / n for n in ("README.md", "README.rst", "README") if (root / n).exists()), None)
    if readme:
        out.append(f"- README: `{readme.name}`")
    out += ["", "## Files", "", "| file | lines |", "|---|---|"]
    texts = {}
    for p in files:
        try:
            t = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        texts[p] = t
        out.append(f"| `{p.relative_to(root)}` | {t.count(chr(10)) + 1} |")

    entries, marks, stubs, deps = [], [], [], []
    out += ["", "## Definitions", ""]
    for p, t in texts.items():
        rel = p.relative_to(root)
        if p.suffix in CONF_EXT:
            continue
        if p.suffix == ".py":
            info = py_info(p, t, local_mods)
            if info["defs"]:
                out += [f"### `{rel}`", *info["defs"], ""]
            entries += [f"`{rel}`: {e}" for e in info["entry"]]
            stubs += [f"`{rel}` {s}" for s in info["stubs"]]
            deps += [f"`{rel}` → {', '.join(sorted(info['imports']))}"] if info["imports"] else []
        else:
            defs = []
            for i, ln in enumerate(t.splitlines(), 1):
                m = GENERIC_DEF.match(ln)
                if m:
                    defs.append(f"- {m.group(1)} `{m.group(2)}` L{i}")
                if re.search(r"\bfn\s+main\b|\bfunc\s+main\b|\bint\s+main\s*\(", ln):
                    entries.append(f"`{rel}`: main L{i}")
            if defs:
                out += [f"### `{rel}`", *defs[:80], ""]
        for i, ln in enumerate(t.splitlines(), 1):
            m = MARK_RE.search(ln)
            if m and ("#" in ln or "//" in ln or "/*" in ln or '"""' in ln):
                marks.append(f"`{rel}:L{i}` {m.group(1)} {m.group(2).strip()[:100]}")

    out += ["## Entry points", ""] + [f"- {e}" for e in entries] + [""]
    out += ["## Local import graph", ""] + [f"- {d}" for d in deps] + [""]
    out += ["## Implementation status hints", "", "### Stubs (pass / ... / NotImplementedError)", ""]
    out += [f"- {s}" for s in stubs] or ["- (none)"]
    out += ["", "### TODO / FIXME / XXX / HACK", ""]
    out += [f"- {m}" for m in marks[:200]] or ["- (none)"]
    print("\n".join(out))


if __name__ == "__main__":
    main()
