---
name: notion-publish
description: |
  Markdown（paper-analyzer の記事，paper-comic の図解，paper-deck のスライド一覧，設計メモなど）を Notion ページとして公開・更新する．
  Notion MCP があればそれを使い，なければ NOTION_TOKEN による同梱スクリプトで公開する．数式・Mermaid・表・ローカル画像に対応．
  「Notionに出力」「Notionに保存」「Notionページにして」「publish to Notion」で使う．
---

# Notion Publish — Markdown → Notion ページ

paper-craft-skills の各スキルの成果物（`article.md`，`*-illustrated.md`，`deck-notion.md` など）を Notion に出すための共通スキル．
単独でも，任意の Markdown に対して使える．

```text
/notion-publish path/to/article.md                                       # Claude Code
$notion-publish path/to/article.md                                       # Codex
/notion-publish path/to/article.md --parent https://www.notion.so/xxxx   # 親ページ指定
/notion-publish path/to/article.md --update                             # 前回公開したページを更新
```

---

## 0. 公開ルートの選択

| 条件 | ルート |
|------|--------|
| Notion MCP のツール（`notion-create-pages` / `notion-update-page` / `notion-fetch` 等，名前に `notion` を含む）が使える | **A: MCP**（推奨．トークン不要） |
| MCP がない，または **ローカル画像を含み，MCP にファイルアップロード手段がない** | **B: スクリプト**（`NOTION_TOKEN` が必要） |
| どちらも使えない | セットアップ手順（下記）を案内し，Markdown/HTML の成果物だけ渡して止まる |

ルートを決めたらユーザーに一言伝える（例：「Notion MCP で `研究ノート` ページの下に作成します」）．

### 公開先（親）の決め方

1. ユーザーが URL / ページ名 / データベースを指定 → それを使う（ページ名なら MCP の search で特定）．
2. 指定がない → 1回だけ聞く．返答がない・無人実行のときは：
   - ルート A：親なし（ワークスペース直下の private ページ）で作成し，URL と「private で作成した」ことを伝える．
   - ルート B：`$NOTION_PARENT_ID` を使う．未設定なら止めて親ページの URL を尋ねる．
3. 同じ Markdown を以前公開している（隣に `<stem>.notion.json` がある）→ 新規作成ではなく **そのページを更新** するのが既定．新しいページにしたい場合だけ新規作成．

---

## ルート A：Notion MCP

1. Markdown を Notion-flavored Markdown に整える：
   - 先頭の `# タイトル` はページタイトルにし，本文からは除く．
   - `$$...$$` のブロック数式・`$...$` のインライン数式はそのまま使える．
   - ```` ```mermaid ```` コードブロックはそのまま（Notion がダイアグラムとして描画する）．
   - HTML タグ（`<div class="summary-box">` 等）は使わない．要約ボックスは callout（`> [!NOTE]` 相当）に置き換える．
   - 表は Markdown 表のまま．
2. **ローカル画像**（`![](01-overview.png)` など）：
   - MCP にファイルアップロード系ツール（例：`notion-create-file-upload`）があれば，それでアップロードして画像ブロックとして埋め込む．
   - なければ：`NOTION_TOKEN` があればルート B に切り替える．無ければ，画像の位置に「🖼️ 画像: `01-overview.png`（ローカル）」の callout を置いて公開し，ユーザーに画像は手動ドラッグ＆ドロップが必要と伝える．
   - `https://` の画像はそのまま埋め込める．
3. `notion-create-pages`（新規）または `notion-update-page`（更新：内容を置換）を呼ぶ．
4. 公開後，Markdown の隣に `<stem>.notion.json` を書く：`{"page_id": "...", "url": "...", "title": "...", "updated": "..."}`．次回の更新で使う．

## ルート B：同梱スクリプト

```bash
SKILL_DIR=<このSKILL.mdがあるディレクトリ>
python3 "$SKILL_DIR/scripts/notion_publish.py" article.md --parent <page-url-or-id>
python3 "$SKILL_DIR/scripts/notion_publish.py" article.md --parent <db-url> --parent-type database
python3 "$SKILL_DIR/scripts/notion_publish.py" article.md --replace auto      # 前回のページを更新
python3 "$SKILL_DIR/scripts/notion_publish.py" article.md --dry-run           # 送信せず変換結果を確認
```

- Python 標準ライブラリのみ．ローカル画像は Notion File Upload API で添付（1ファイル 20MB まで）．
- 成功すると URL を標準出力に出し，`<stem>.notion.json` を書く．
- 対応記法：見出し，段落，箇条書き（1段ネスト），番号付き，ToDo，引用，`> [!NOTE|TIP|WARNING|TODO|QUESTION|DECISION]` callout，コード（mermaid含む），`$$` 数式，表，画像，区切り線，インライン（太字・斜体・取り消し・コード・リンク・インライン数式）．

---

## セットアップ（ユーザー向けに案内する内容）

**Notion MCP（推奨・トークン不要）**

```bash
# Claude Code
claude mcp add --transport http notion https://mcp.notion.com/mcp
# Codex
codex mcp add notion --url https://mcp.notion.com/mcp
codex mcp login notion
```

**API トークン（スクリプト用）**

1. https://www.notion.so/profile/integrations で Internal integration を作成し，トークンを取得．
2. 公開先の親ページで「…」→「接続」からその integration を追加．
3. `export NOTION_TOKEN=ntn_xxx`（必要なら `export NOTION_PARENT_ID=<親ページURL>`）．

---

## 品質チェック

- [ ] タイトルが本文に重複していない
- [ ] 数式が Notion の数式として表示される（`$` が生のまま残っていない）
- [ ] Mermaid がコードブロック（language=mermaid）になっている
- [ ] 画像がすべて表示される，または手動対応が必要な画像をユーザーに伝えた
- [ ] 公開した URL をユーザーに伝え，`<stem>.notion.json` を保存した
