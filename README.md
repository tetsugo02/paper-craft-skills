# paper-craft-skills

English | [中文](./README.zh.md)

**Turn academic papers into polished method figures, visual slide decks, and in-depth articles — zero config, one command.**

<p align="center">
  <img src="examples/paper-illustrated/attention-is-all-you-need/transformer-overview-paper-figure.png" width="700" alt="Transformer architecture — generated from Attention Is All You Need"/>
</p>

<p align="center">
  From arxiv link to publication-ready visuals, AIGC slide decks, and deep-dive articles.<br/>
  Drop a paper, pick a style, get output that looks like a human expert made it.
</p>

---

## How to install

> This is a fork of [zsyggg/paper-craft-skills](https://github.com/zsyggg/paper-craft-skills) with Notion output,
> code / work-in-progress design / agent-discussion visualization, and first-class Codex support.

### Option A — Ask your agent (Claude Code or Codex)

```
Please install tetsugo02/paper-craft-skills for me.
GitHub: https://github.com/tetsugo02/paper-craft-skills
Follow the "How to install" section of the README (clone, then run ./install.sh).
```

### Option B — Clone + install script (recommended for multiple machines)

```bash
git clone https://github.com/tetsugo02/paper-craft-skills.git ~/workspace/paper-craft-skills
cd ~/workspace/paper-craft-skills
./install.sh            # Claude Code (~/.claude/skills) + Codex (~/.agents/skills)
./install.sh --claude   # Claude Code only
./install.sh --codex    # Codex only
```

Skills are **symlinked**, so `git pull` updates every machine. Restart Claude Code / Codex afterwards.
Use `./install.sh --project <repo>` to install into a single project (`<repo>/.claude/skills`, `<repo>/.agents/skills`).

### Option C — Plugin marketplace

```bash
# Claude Code
/plugin marketplace add tetsugo02/paper-craft-skills
/plugin install paper-craft-skills@paper-craft-skills

# Codex (then install "paper-craft-skills" from the Plugins directory)
codex plugin marketplace add tetsugo02/paper-craft-skills
```

Or with the [skills CLI](https://github.com/vercel-labs/skills): `npx skills add tetsugo02/paper-craft-skills`

> Pick one method per agent — installing both as a plugin and via `install.sh` shows each skill twice.

### Optional — Notion output

```bash
# Claude Code
claude mcp add --transport http notion https://mcp.notion.com/mcp
# Codex
codex mcp add notion --url https://mcp.notion.com/mcp && codex mcp login notion
```

No MCP? Set `NOTION_TOKEN` (internal integration) and the bundled script is used instead — see [`skills/notion-publish`](./skills/notion-publish/SKILL.md).

**Works with:** Codex · Claude Code · Cursor · Windsurf

### Invoking skills

| | Claude Code | Codex |
|--|--|--|
| explicit | `/paper-comic ...` | `$paper-comic ...` (or `/skills`) |
| implicit | describe the task ("visualize the design we just discussed") | same |

---

## What's new in this fork

| Feature | Skill |
|---------|-------|
| **Notion output** — publish articles / figures / decks as Notion pages (MCP or API token), update the same page later | `notion-publish`, `paper-analyzer --output notion`, `paper-comic --output notion`, `paper-deck` |
| **Code → figures** — visualize a repository's method (architecture, data flow with tensor shapes, core modules) in the same styles | `paper-comic --source code` |
| **Work-in-progress design → figures** — combine notes + partial code; components are marked ✅ implemented / 🟡 WIP / ⬜ planned / ❓ open | `paper-comic --source design` |
| **Agent discussion → figures** — turn a Claude Code / Codex discussion (current session or `.jsonl` log) into the agreed method structure, decisions and open questions | `paper-comic --source discussion` |
| **Versioned `method-spec.md`** + fast Mermaid `--draft` mode — iterate on the structure before generating images; only changed figures are regenerated | `paper-comic --draft / --update` |

```bash
/paper-comic ./my-repo --source code --style paper-figure
/paper-comic docs/plan.md src/ --source design --draft
/paper-comic --source discussion --output notion
/paper-analyzer https://arxiv.org/abs/1706.03762 --output notion
```

---

## What's inside

<table>
<tr>
<td width="50%" align="center" valign="top">

### 🎨 paper-comic
**Paper / Code / Design / Discussion → Method Figures**

<img src="examples/paper-illustrated/attention-is-all-you-need/transformer-overview-paper-figure.png" width="380"/><br/>
<sub>Transformer architecture — generated from <i>Attention Is All You Need</i></sub>

<br/>

Reads your paper → proposes what to draw → you confirm → generates.

| Style | Vibe |
|-------|------|
| **paper-figure** | Publication-grade diagrams |
| **sketchnote** | Bright, warm hand-drawn study notes |

</td>
<td width="50%" align="center" valign="top">

### 📄 paper-analyzer
**Paper → Deep Articles**

<img src="images/hero_banner.png" width="380"/><br/>
<sub>Paper → polished HTML article with formulas, code cross-reference, and choice of style</sub>

<br/>

Reads the full paper → searches GitHub for code → writes in your chosen style.

| Feature | |
|---------|--|
| 🌐 Output | **HTML** or **Notion page** |
| 📐 Formulas | **KaTeX** rendering |
| 📊 Diagrams | **Mermaid** architecture charts |
| ⚡ Setup | **Zero config** — no API keys |

</td>
</tr>
<tr>
<td width="50%" align="center" valign="top">

### 🖼️ paper-deck
**Paper → Visual Slide Deck**

<img src="images/paper_deck_intro.png" width="380"/><br/>
<sub>Paper/article → analysis → outline → visual prompts → PPTX/PDF</sub>

<br/>

Reads your paper → plans the deck → generates slide images → exports PPTX/PDF.

| Output | |
|--------|--|
| 🎞️ Slides | 16:9 visual pages |
| 📦 Export | `.pptx` + `.pdf` |
| 🛠️ Edits | Regenerate any page |

</td>
<td width="50%" align="center" valign="top">

</td>
</tr>
</table>

---

## paper-deck — Visual slide decks that don't look like templates

`paper-deck` turns a paper, article, or technical note into a designed slide deck. It first builds a deck brief and slide-by-slide outline, then writes reproducible visual prompts, generates polished 16:9 slide images, and merges them into `.pptx` and `.pdf`.

It is built for iteration: every page has its own prompt, so you can ask for precise changes like “make slide 5 more journal-like”, “replace slide 8 with a real benchmark chart”, or “keep the layout but switch the cover to liquid glass”.

<p align="center">
  <img src="images/paper_deck_styles.png" width="640"/>
  <br/><sub>Four compact style presets for the same paper topic</sub>
</p>

| Style | Best for |
|-------|----------|
| **journal-minimal** | Nature/IEEE-inspired academic decks and thesis defenses |
| **business-research** | Strategy memos, industry research, investor/client briefings |
| **warm-notes** | Study-note explanations, teaching, approachable paper walkthroughs |
| **liquid-glass** | Apple-inspired visual chapters, covers, and high-impact section pages |

It also supports real source visuals. When a PDF contains strong figures, tables, plots, or screenshots, the skill plans which slides should use them, where they should be cropped, and how they should be framed. Real visuals can be mounted into clean academic panels, evidence blocks, or glass-style layouts instead of being hallucinated from scratch.

```bash
/paper-deck https://arxiv.org/abs/1706.03762
/paper-deck /path/to/paper.pdf --style journal-minimal --slides 12
/paper-deck notes.md --style liquid-glass
```

---

## paper-comic — How it works

```text
/paper-comic https://arxiv.org/abs/1706.03762

Reads the paper, then recommends:

  I suggest 6 figures:
  1. Cover: one-line contribution + visual anchor
  2. Transformer architecture overview
  3. Self-attention mechanism
  4. Multi-head attention detail
  5. Encoder / Decoder Block
  6. Key results

  Or generate only 1 overview figure, or expand to 8 detailed mechanism figures.
  Language? [Chinese / English]  Style? [sketchnote / paper-figure]  Scope and count?
```

### Example outputs

<p align="center">
  <img src="examples/paper-illustrated/attention-is-all-you-need/transformer-overview-paper-figure.png" width="550"/>
  <br/><b>paper-figure</b> — clean, publication-grade
</p>

<p align="center">
  <img src="examples/paper-illustrated/attention-is-all-you-need/self-attention-sketchnote.png" width="350"/>
  <br/><b>sketchnote</b> — bright, warm, approachable
</p>

> Full walkthrough: [examples/paper-illustrated/attention-is-all-you-need](./examples/paper-illustrated/attention-is-all-you-need)

---

## paper-analyzer — Deep articles that read like a human expert wrote them

**Not a paper translator — a re-interpreter.** It reads the full paper, searches GitHub for open-source implementations, cross-references code with the paper, and writes in your chosen style.

### Three writing styles

<p align="center">
  <img src="images/styles_comparison.png" width="700"/>
</p>

| Style | Reads like | Use it for |
|-------|-----------|------------|
| **storytelling** | A viral blog post — hooks, analogies, golden takeaway | WeChat, Twitter, blogs |
| **academic** | A peer-reviewed deep dive — KaTeX formulas, comparison tables | Lab meetings, lit reviews |
| **concise** | A cheat sheet — Mermaid diagram + key data table | Quick understanding |

### Features

<table>
<tr>
<td width="50%" align="center">
<img src="images/formula_feature.png" width="360"/><br/>
<b>Formula Explanation</b><br/>
Extracted paper formulas with symbol-by-symbol breakdown
</td>
<td width="50%" align="center">
<img src="images/code_feature.png" width="360"/><br/>
<b>Code Analysis</b><br/>
Aligns paper concepts with the GitHub source code
</td>
</tr>
</table>

```bash
/paper-analyzer https://arxiv.org/abs/1706.03762     # arxiv link
/paper-analyzer /path/to/paper.pdf                     # local PDF
/paper-analyzer                                         # then paste text
```

---

## License

MIT

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=zsyggg/paper-craft-skills&type=Date)](https://star-history.com/#zsyggg/paper-craft-skills&Date)
