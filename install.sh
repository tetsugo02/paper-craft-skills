#!/usr/bin/env bash
# paper-craft-skills installer (Claude Code / Codex)
#   ./install.sh            # Claude Code + Codex（既定）
#   ./install.sh --claude   # ~/.claude/skills のみ
#   ./install.sh --codex    # ~/.agents/skills のみ（Codex のユーザースキル）
#   ./install.sh --copy     # symlink ではなくコピー
#   ./install.sh --project <dir>  # <dir>/.claude/skills と <dir>/.agents/skills に入れる（リポジトリ単位）
# 既定は symlink なので，`git pull` だけで全マシンのスキルが更新される．
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$REPO_DIR/skills"
targets=()
mode="link"
base="$HOME"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --claude) targets+=("claude") ;;
    --codex) targets+=("codex") ;;
    --copy) mode="copy" ;;
    --project) base="$(cd "$2" && pwd)"; shift ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 1 ;;
  esac
  shift
done
[[ ${#targets[@]} -eq 0 ]] && targets=("claude" "codex")

install_to() {
  local dest="$1"
  mkdir -p "$dest"
  for skill in "$SRC"/*/; do
    skill="${skill%/}"
    local name; name="$(basename "$skill")"
    [[ -f "$skill/SKILL.md" ]] || continue
    local target="$dest/$name"
    if [[ -e "$target" && ! -L "$target" ]]; then
      echo "  skip  $target (既存のディレクトリ．手動で退避してから再実行してください)"
      continue
    fi
    if [[ "$mode" == "copy" ]]; then
      rm -f "$target"
      cp -R "$skill" "$target"
      echo "  copy  $name -> $target"
    else
      ln -sfn "$skill" "$target"
      echo "  link  $name -> $target"
    fi
  done
}

for t in "${targets[@]}"; do
  case "$t" in
    claude) echo "[Claude Code] $base/.claude/skills"; install_to "$base/.claude/skills" ;;
    codex)  echo "[Codex] $base/.agents/skills";       install_to "$base/.agents/skills" ;;
  esac
done

cat <<'MSG'

Done. Claude Code / Codex を再起動するとスキルが読み込まれます．
Notion 出力を使う場合（任意）:
  Claude Code: claude mcp add --transport http notion https://mcp.notion.com/mcp
  Codex:       codex mcp add notion --url https://mcp.notion.com/mcp && codex mcp login notion
  または export NOTION_TOKEN=ntn_xxx （skills/notion-publish/SKILL.md 参照）
MSG
