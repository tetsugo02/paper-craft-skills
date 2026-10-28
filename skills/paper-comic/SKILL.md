---
name: paper-comic
description: |
  论文方法图解——用视觉图解彻底讲清楚一篇论文到底做了什么、怎么做的。
  自动分析论文核心方法，先推荐封面/概述图/机制细节图的生成方案，必须由用户确认范围、张数、语言、风格后再生成。
  支持温暖笔记风和论文框架图风。
  除论文外，也能从源代码（code）、实装途中的方法（文章＋代码，design）、与 agent 的讨论记录（discussion）用同样风格可视化，
  并用 ✅🟡⬜❓ 视觉语言区分已实装/部分实装/计划/未决。输出 Markdown，可选发布到 Notion。
  論文・ソースコード・実装途中の設計メモ・エージェントとの議論ログから手法の構成図／機構図を作る．
---

# Paper Method Illustrated — 论文方法图解

把论文的核心方法用视觉图解彻底讲清楚。

**输入不限于论文**（详见 `references/source-modes.md`）：

| mode | 输入 | 典型用途 |
|------|------|---------|
| `paper` | arXiv / PDF / 论文文本 | 读论文、做分享（原有功能） |
| `code` | 仓库路径 / GitHub URL / 若干源文件 | 把代码实现的方法画成同风格的架构图、数据流图、核心模块图 |
| `design` | 研究计划/设计笔记 ＋ 实装中的代码 | **实装途中的方法**：画出现在的构成，以及哪些已实装/部分实装/计划中/未决 |
| `discussion` | 与 Claude Code / Codex 讨论的结果（当前会话、粘贴的记录、`.jsonl` 日志） | 把讨论中达成共识的方法结构可视化，决策与被否决的方案一并整理 |

所有模式都先整理成中间表示 `method-spec.md`（`references/method-spec.md`），再从它设计图。
`design` / `discussion` 模式是研究推进中反复使用的核心功能：spec 有版本，更新时只重画受影响的图。

## 与其他技能的本质区别

| | 传统paper-comic | baoyu-article-illustrator | **我们：方法图解** |
|---|---|---|---|
| 聊什么 | 什么都聊一点 | 为文章配装饰图 | **只聊方法细节** |
| 深度 | 一页讲很多→浅 | 一张图一段话→中 | **一张图讲透一个机制→深** |
| 页数 | 固定10页 | 按密度5-20张 | **先推荐封面/概述/细节图组合，用户确认后生成1-10张** |
| 重点 | 讲背景+故事 | 美化文章排版 | **可视化"怎么做"** |

## 快速开始

```bash
/paper-comic /path/to/paper.pdf
/paper-comic https://arxiv.org/abs/2512.xxxxx
/paper-comic /path/to/paper.pdf --style sketchnote
/paper-comic /path/to/paper.pdf --style paper-figure --language English --pages 1

# 源代码 → 同风格方法图
/paper-comic ./my-repo --source code
/paper-comic https://github.com/org/repo --source code --style paper-figure

# 实装途中的方法（文章＋代码）
/paper-comic docs/plan.md src/ --source design
/paper-comic docs/plan.md src/ --source design --draft          # 先只出 method-spec + Mermaid 草图（不生图）

# 与 agent 的讨论结果
/paper-comic --source discussion                                 # 用当前会话中的讨论
/paper-comic --source discussion --transcript latest             # 读取本项目最近一次 Claude Code / Codex 会话
/paper-comic discussion.md src/ --source design --output notion  # 讨论记录＋代码，发布到 Notion
```

**参数**（都可省略，省略时自动判断或在确认时询问）：
- `--source paper|code|design|discussion`：输入模式（默认自动判定）
- `--draft`：只生成 `method-spec.md` 和 Mermaid 草图，不调用生图（快速对齐结构用）
- `--output md|notion`：输出到本地 Markdown（默认）或另外发布到 Notion（见 `../notion-publish/SKILL.md`）
- `--update`：基于上一次的 `method-spec.md` 更新（只重画变化的图）
- `--transcript latest|<path.jsonl>`：discussion 模式读取过去的会话日志（`scripts/extract_transcript.py`）

> Codex 中用 `$paper-comic ...` 调用（或直接用自然语言描述，如“把刚才讨论的设计画成图”）。

---

## 图片生成：自动检测

和paper-analyzer一样，不硬编码任何API。运行时自动检测：

| 环境 | 自动使用 |
|------|---------|
| **Codex** | 内置 `imagegen` skill |
| **Claude Code** | 已安装的生图skill（如baoyu-image-gen） |
| **Cursor/其他** | 自动检测 → 没有则提示安装 |

**不写死任何API key、token或endpoint在SKILL.md里。**

---

## 核心哲学

### 我们只画三样东西

1. **方法流程** — 输入→处理→输出，这方法到底怎么走的
2. **核心机制** — 最创新的那个部分，拆开来看内部构造
3. **关键结果** — 只放最重要的实验结果，不放灌水数据

### 我们不画的东西

- ❌ 相关工作/背景介绍（那是paper-analyzer文字部分的事）
- ❌ 抽象的"灵感来源"（没有信息量的图 = 浪费）
- ❌ 文字就能说清楚的东西（一句话能讲完不需要画）
- ❌ 第N个消融实验的柱状图

### 每一张图的标准

> 一个完全没读过论文的人，只看这张图+图上的标注文字，能不能理解这个机制？

能 → 通过。不能 → 拆成两张，或者加更多标注。

---

## 生成前必须确认

默认**不要直接生成图片**。先读论文、给出推荐方案，再向用户确认。

只有当用户已经明确给出足够完整的生成意图时，才可以跳过确认，例如：
- “生成一张中文 sketchnote 方法总览图”
- “生成 4 张：封面、总览、两个机制细节，英文 paper-figure”
- “按你推荐的全部生成，中文，sketchnote”

如果用户只给了论文链接、只说了风格（如“sketchnote”）、或只说“生成图解”，仍然必须确认，因为**风格不等于范围/张数授权**。

确认时必须覆盖：

0. **（design / discussion 模式）method-spec 摘要**：先给出整理后的构成要素、状态（✅🟡⬜❓）、决策、未决事项，请用户确认“理解是否正确”。可以和下面各项放在同一条消息里
1. **图片语言**：中文 / English / 日本語 / 双语
2. **生成范围**：只要封面图、只要方法总览图，还是概述图 + 若干机制细节图 + 结果图
3. **推荐张数**：基于论文复杂度给出建议，并说明为什么，如“我建议6张，因为这篇论文有整体架构、两个核心attention机制、编码器/解码器结构和关键实验结果”
4. **视觉风格**：`sketchnote` 或 `paper-figure`
5. **用途**：README/文章封面/小红书/演示文稿/论文阅读笔记/研究室内设计共享（用途决定横竖比例和文字密度）
6. **出图方式**：`draft`（只出 Mermaid 草图，秒级、可反复改）还是 `final`（调用生图）。design / discussion 模式建议先 draft 对齐结构，再 final
7. **输出位置**：本地 Markdown，还是也发布到 Notion（需要父页面 URL；不指定则按 notion-publish 规则创建 private 页面）

确认话术示例：

> 我读完后建议生成6张：1张封面、1张方法总览、3张机制细节、1张关键结果。也可以只生成1张总览图，或者扩展到8张把每个机制讲更细。你想生成哪种范围？语言用中文/英文/双语？风格用 sketchnote 还是 paper-figure？

如果用户没有回答，不要继续生成。

---

## 两种视觉风格

| 画风 | 视觉效果 | 适合场景 | 特点 |
|------|---------|----------|------|
| **sketchnote**（默认） | 温暖科研笔记风 | 讲清楚论文在做什么、视频宣传、知识分享 | 工整但有人味，允许小符号、小比喻、小视觉锚点，让人一眼理解 |
| **paper-figure** | 论文框架图风 | README首屏、论文解读文章、方法总览、技术展示 | 像顶会论文里的总览框架图，但更完整、更漂亮、更适合传播 |

默认推荐 **sketchnote**。当用户想要“像论文 Figure 一样专业”“方法框架图”“技术架构图”“放 README 第一屏很震撼”时，推荐 **paper-figure**。

### sketchnote 风详细规范

- 明亮温暖的浅米白底（接近 #FFF8EA / #FAF4E6），像干净的手抄报纸或课堂讲义
- 不要牛皮纸、旧羊皮纸、暗角、污渍、泛黄边缘或明显做旧纹理
- 主体是黑色手绘线条+文字，有墨迹粗细变化
- 重点概念用清爽的彩铅/马克笔质感强调（深蓝/珊瑚红/橄榄绿/柔和黄色），颜色轻快但不过饱和
- 箭头和连线带有手绘的不完美感
- 文字是手写体（英文可选手写风格，中文保持清晰可读）
- 整体像一份明亮、温暖、信息充实的研究手抄报，不是复古笔记、不是幼稚漫画
- 可以加入少量帮助理解的趣味符号：放大镜、星号、便签、圈注、手绘小灯泡、简化小图标
- 趣味元素必须服务理解，不能抢走方法图主体
- 主体图解应占画面 75%-85%，避免大块空白；如果页面留白明显，优先增加局部放大框、小例子、维度标注或对比说明
- 每一页右下角有"手写"页码

### paper-figure 风详细规范

- 白底或极浅灰底，像 NeurIPS / Nature / Science 论文中的高质量方法总览图
- 使用干净的矢量感模块：圆角矩形、矩阵小格、流程箭头、分组框、编号步骤
- 配色克制但现代：黑/深灰为主，1-2个强调色（蓝、青、橙、紫任选其一到两种）
- 结构比原论文图更清楚：保留核心机制，重新组织布局，避免照抄原图
- 可以有小型结果示意、矩阵热力图、token序列、模块堆叠、对比路径
- 标注像论文图注中的短标签：精准、短、专业
- 适合横版 16:9、4:3 或竖版 2:3；README 首屏优先横版或宽图

---

## 工作流程

### Step 1：读取输入 → 写 method-spec → 提取"可图解内容"

先判定 source mode，然后按 `references/source-modes.md` 对应章节读取：

| mode | 读取要点 |
|------|---------|
| `paper` | 读全文（同下） |
| `code` | 运行 `scripts/code_map.py <repo>` 得到代码地图 → 找入口 → 追踪一次 forward/推理/训练 step 的形状变化 → 找出与 baseline 不同的核心部分 |
| `design` | 从文章抽取构成与意图，从代码判定每个要素的实装状态（✅🟡⬜❓），记录文章与代码的矛盾 |
| `discussion` | 取得讨论记录（当前会话 / 粘贴 / `scripts/extract_transcript.py`）→ 给发言编号 → 抽取共识构成、决策、被否决方案、未决事项；**后面的发言覆盖前面的**；未被用户明确接受的提案记为 ❓ |

然后把结果写成 `comic/<slug>/method-spec.md`（格式见 `references/method-spec.md`）。每个要素必须带 status 和 evidence（论文章节 / `file:line` / 讨论轮次 `T12`）。没有依据的要素不画。

若已存在上一版 `method-spec.md`（`--update` 或同一 slug），先把旧版移到 `spec-history/vN.md`，再写新版并列出差异。

以下以论文为例说明“只保留需要图解的部分”；code / design / discussion 模式的推荐图见 `references/source-modes.md` 各节的表格。

读完论文后，列出论文的所有内容点，然后**只保留需要图解的部分**：

**必须图解（每个1-2页）：**
- 方法的整体流程/架构（输入→各模块→输出）
- 每个核心创新机制（拆开看内部）
- 最有说服力的那个实验结果

**可选图解（如果方法复杂才加）：**
- 方法的变体/扩展
- 关键的数据处理流程
- 与baseline的可视化对比

**不图解：**
- 相关工作（文字提一句就行）
- 多个类似的消融实验
- 背景知识介绍

### Step 2：给出推荐并确认需求

先输出一个简短推荐，不要立刻生成：

```markdown
我建议生成 6 张：
1. 封面图：论文一句话贡献 + 视觉锚点
2. 方法总览图：解释整体输入、核心模块、输出
3. 核心机制A：拆开最重要的创新点
4. 核心机制B：解释训练/推理/数据流中的关键环节
5. 核心机制C：补足容易误解的内部细节
6. 关键结果图：用一张图说明为什么有效

也可以：
- 只生成 1 张总览图
- 生成 3 张：总览 + 2 张核心机制
- 扩展到 8-10 张，把每个机制讲得更细

请确认：
- 语言：中文 / English / 双语
- 风格：sketchnote / paper-figure
- 范围：只要封面/总览，还是生成全部推荐图？
```

如果用户没有回答，不要继续生成。

### Step 3：确定页数

根据论文复杂度，AI只做**推荐**，最终由用户确认：

| 论文复杂度 | 推荐页数 | 内容分配 |
|-----------|---------|---------|
| 封面/传播图 | 1页 | 一张封面或高层总览，讲清楚论文做了什么 |
| 快速理解 | 2-3页 | 总览+核心机制+结果 |
| 中等（2个核心方法） | 4-6页 | 封面/总览+2-3个机制+关键结果 |
| 复杂（3+个核心方法） | 6-10页 | 封面/总览+每个机制1页+对比/结果 |

**规则**：最少1页，最多10页。宁少勿多——1张总览图讲清楚，比10张讲糊涂好。

### Step 4：为每一页写详细的内容描述

不是"生成prompt"，而是先用自然语言描述清楚**这一页到底要表达什么**：

```
第3页：多头注意力机制的内部构造

这一页要讲清楚：Q、K、V是怎么算出来的，它们之间怎么交互。

画面布局（从左到右）：
- 左侧：输入x，一个向量表示
- 中间上方：三条线分别到三个方框（Linear_Q, Linear_K, Linear_V）
- 三个方框各产出Q、K、V三个矩阵
- 中间核心区域：Q和K做点积→除以√dk→softmax→得到注意力权重
- 权重和V相乘→输出
- 右侧：多个这样的"头"并行排列，最后拼接

关键标注：
- 每个方框旁标运算和维度（如"Linear_Q: x→Q(d×dk)"）
- Q×K^T的计算用可视化的矩阵乘法图（小格图）
- softmax后的权重用颜色深浅表示（越深=越关注）
```

**要求**：描述要具体到"这个箭头从哪到哪，这个方框里写什么字"。

同时检查每页的信息密度：
- 如果只是大标题 + 少量模块，说明这一页太空，必须补充机制小例子、局部放大、输入输出维度或关键对比
- 如果内容超过一页可读范围，拆成两页，不要把所有文字塞进同一张图
- 封面图可以更概念化；机制细节图必须优先讲清楚“怎么做”

### Step 5：生成图片

**draft 模式**（`--draft` 或用户选择 draft）：不调用生图。只输出 `method-spec.md` 中的 Mermaid 草图（可按图拆成多个 Mermaid 块），用 `classDef` 区分状态。明确告诉用户这是草图，不是最终图。用户确认结构后再进入 final。

**final 模式**：根据当前运行环境自动选择生图后端。为每一页创建prompt文件（`comic/<slug>/prompts/NN-*.md`）→ 用结构化prompt生成。

design / discussion / code 模式的图必须遵循 `references/status-visuals.md` 的状态视觉语言（✅ 实线 / 🟡 WIP / ⬜ 虚线 / ❓ 便签或分支 / ✕ 被否决方案放在侧边小面板），并带一行小图例和版本号。

**结构化prompt格式**（参考但不照抄baoyu）：
```
【类型】流程分解图
【风格】sketchnote
【语言】中文
【主题】多头注意力机制内部构造
【视觉结构】
- 水平布局，从左到右5个区域
- 每个区域用虚线框隔开
- 关键路径用粗箭头连接

【要标注的文字】
1. Input: x ∈ R^(n×d)
2. Q = xW_Q ... (完整标注)
...

【状态标记】（仅 code / design / discussion 模式）
- M1 Patch Encoder：✅ 实线
- M2 Sparse Router：🟡 WIP 标签
- M3 Consistency Loss：⬜ 虚线框
- τ schedule：❓ 便签“linear? / cosine?”
- 右下角图例：✅ done 🟡 WIP ⬜ planned ❓ open · design v3

【颜色限制】
- 背景：明亮浅米白，不要泛黄旧纸
- 主色：黑色手绘线条
- 强调色：深蓝/珊瑚红/橄榄绿/柔和黄色，少量使用
- 其他：保持清爽手抄报感，避免复古暗色

【禁止】
- 不要代码块
- 不要照片写实
- 不要3D渲染
- 不要生成用户没有确认的额外页面
- 不要旧羊皮纸、暗角、污渍、重纸纹、黄褐色复古调
- 不要大面积空白；主体图解占画面75%-85%
```

### Step 6：输出

输出目录统一为 `comic/<slug>/`：

```text
comic/<slug>/
├── method-spec.md          # 正本（所有模式）
├── spec-history/v1.md ...  # 旧版本（design / discussion 反复更新时）
├── code-map.md             # code / design 模式
├── discussion.md           # discussion 模式（抽取的讨论记录）
├── prompts/NN-*.md         # final 模式的每页 prompt
├── NN-*.png                # 生成的图
└── <slug>-illustrated.md   # 汇总页（下方格式）
```

code / design / discussion 模式的汇总页在“讲解”后追加：
- **对应关系**：图中每个模块 → `file:line` / 讨论轮次 / 笔记章节
- **决策与未决**：来自 method-spec 的 Decisions / Open questions / Next actions
- **本版变化**：与上一版 spec 的差异（若有）
- draft 模式下，图片位置放 Mermaid 代码块

**Notion 输出**（`--output notion` 或用户要求）：按 `../notion-publish/SKILL.md` 发布 `<slug>-illustrated.md`。Mermaid 草图在 Notion 中直接渲染为图；本地 PNG 需要上传（MCP 有上传工具则用，否则用 `notion_publish.py`）。已存在 `<slug>-illustrated.notion.json` 时默认更新同一页面，这样设计图在 Notion 上始终是最新版。

论文模式的汇总页格式（`[topic]-illustrated.md`）：

```markdown
# [论文标题] — 图解

## 论文信息
- 论文：[链接]
- 风格：sketchnote
- 页数：6

## 封面
![封面](00-cover.png)
**一句话**：[论文做了什么，为什么重要]

## 第1页：方法总览
![方法流程](01-method-overview.png)
**讲解**：整个方法从输入到输出的完整流程。关键看第X步，这是本文的创新。

## 第2页：核心机制A — [名称]
![核心机制A](02-mechanism-a.png)
**讲解**：这个机制解决了XX问题。具体做法是...关键设计在于...

[重复...]

## 总结：3个核心要点
1. [要点1]
2. [要点2]  
3. [要点3]
```

### Step 7：随研究推进更新（design / discussion）

1. 用户说“设计变了 / 又讨论了一轮 / 代码更新了”→ 重新读取新增的输入（只读新讨论轮次 `--since`、`git diff`、更新的笔记）
2. 旧 spec 移到 `spec-history/`，写新 spec，列出 Changes since previous version
3. 只重新生成受影响的图（构成变化 → 概览图；某机制变化 → 该机制图；状态变化 → 只改状态标记的图）。不受影响的图保留
4. 先给用户看差异和计划重画的图，确认后再生成；Notion 页面用同一页更新

---

## 质量标准

### 好的图解
- ✅ 一张图只看一眼就知道在讲什么
- ✅ 标注文字精确、简练、不啰嗦
- ✅ 流程箭头清晰，有明确的"从这里到那里"
- ✅ 关键部分用颜色/大小做了视觉强调
- ✅ 不看论文原文也能理解
- ✅ （code / design / discussion）每个模块都能追溯到 `file:line` / 讨论轮次；状态标记和图例一致
- ✅ （discussion）画的是最终共识，不是被推翻的中间方案

### 差的图解
- ❌ 信息堆砌，什么都想画进去
- ❌ 文字太多，图变成了装饰
- ❌ 流程不清晰，不知道先看哪后看哪
- ❌ 画了但没解释——放了一张架构图但没标注关键点
- ❌ 和论文Figure 1一模一样——那你画的有什么意义
- ❌ （code）画成文件目录树或 UML 类图——要画“方法”，不是“代码结构”
- ❌ （design）把计划中的部分画得和已实装一样，读者误以为已经能跑

---

## 参考文件

- `references/base-prompt.md` — 图解生成基础规范（结构、文字、色彩要求）
- `references/styles/sketchnote.md` — 温暖科研笔记风
- `references/styles/paper-figure.md` — 论文框架图风
- `references/source-modes.md` — paper / code / design / discussion 各模式的读取方法与推荐图
- `references/method-spec.md` — 中间表示 method-spec 的模板
- `references/status-visuals.md` — 已实装/部分/计划/未决/否决 的视觉语言
- `scripts/code_map.py` — 代码地图（定义、依赖、入口、TODO/stub）
- `scripts/extract_transcript.py` — 从 Claude Code / Codex 会话日志抽取讨论
- `../notion-publish/SKILL.md` — Notion 发布
