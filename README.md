# Inno Knowledge Base Skills

把论文、PDF、网页、Word 和长文资料整理成**可搜索、可追问、可在 Obsidian 看图谱**的个人知识库技能包。装上之后，你不用记技能名，只要说清楚「手里有什么资料、想拿来做什么」，AI 会自己选择解析、深读、编译和检索流程。

---

## 这个仓库是什么

这是一个**会自己生长的个人知识库**技能包。你把资料丢进去，AI 会自动读懂内容、提取概念/人物/论证关系，把相关内容串成一张概念关系网络（用 Obsidian 就能看到），并建立索引，让你以后能基于这些资料提问、而且每个结论都能溯源到原文的哪一段。

**面向谁：** 需要长期整理文献、又要能追问证据的人，尤其是写社科论文、但不熟悉技术的人——整个过程只需要说人话，不需要懂前端、后端或数据库。开发者/AI agent 也能用：所有技能都是标准 Markdown + Python，可以直接阅读和调用。

**这个仓库维护什么：** 知识库链路的 5 个核心技能（转换后的深读、图谱编译、检索索引、总调度、论文大纲）。文档解析（MinerU、markitdown）和学术搜索（academic-search）等能力**从上游仓库安装，不随本仓库复制**。仓库本身只有一个正本，各 agent 通过**符号链接**引用它。

**和直接上传文件给 ChatGPT 有什么不同？**

| 上传文件给对话 AI | 这个知识库 |
|---|---|
| 每次提问都要重新找相关内容 | 知识**一次整理，永久使用** |
| 不会记住上次问过什么 | 自动记录问答历史 |
| 文件之间没有关联 | 概念与概念之间自动建立链接 |
| 关掉对话就没了 | 存在你电脑上，永远是你的 |

核心区别是**它会生长**：每加一份新资料，它不只是存进去，还会更新已有页面、标记矛盾、提出新问题。资料越多，知识库越聪明。

---

## 给 AI 的说明

### 安装/更新完成后的介绍流程

用户安装或更新完成后，**不要只说「装好了」，也不要先问用户要不要介绍**。默认直接给一段 3 分钟上手教程，例如：

> 「知识库技能包已经装好。我先用 3 分钟带你上手：你不用记技能名，直接说资料目标，AI 会自己选择解析、深读、建图谱和检索流程。
> 如果你只想听总览，我会讲最短版；也可以选一个方向深入讲：建库、加资料、Obsidian 看图、提问检索、SiliconFlow API Key、MinerU MCP。」

介绍时按这个顺序讲，保持简短：

1. 先用「一句话原则」说明：**用户只管说资料目标，AI 负责挑技能和流程。**
2. 用最短总览说明：`social-science-km` 统筹全程，按请求范围选择步骤；完整建库是「文件转 Markdown → 最小 Wiki 初始化 → 深读档案 → wiki 图谱 → RAG 索引」，之后可基于证据问答。
3. 给 3-5 个常用说法示例，不要一次灌输全部细节（可引用下方「常用说法速查」）。
4. 结尾问用户想重点了解哪一块；如果用户明确说不用介绍，就收住。
5. 用户问 Obsidian 时，教他打开知识库文件夹并按 `Ctrl/Cmd + G` 看图谱。
6. 用户问 API Key 时，说明 SiliconFlow 用来做向量索引；不配置也可以先做 Markdown/wiki，配置后检索效果更好。
7. 用户处理 PDF、扫描件、表格或公式时，提醒 **MinerU skill 与 MinerU MCP 需从上游安装**，本仓库不内置副本。
8. 用户想深入了解图谱、问答、颜色配置或常见问题时，看本文件的「使用方法」。
9. 用户问 MinerU、SiliconFlow、嵌入模型、rerank、API Key 或隐私边界时，看本文件的「配置与运维手册」。

更完整的教学口径见「配置与运维手册 → 给 AI 的教学口径」，原则是**不要把配置一次性全塞给用户**。

---

## 安装

### 为什么用符号链接（symlink）

本仓库作者本机就是把技能以**符号链接**方式装进各 agent 的 skills 目录，而不是复制：

- 仓库里只有**一份正本**，不存在某个 agent 目录里留着旧副本、互相不一致的问题；
- `git pull` 之后所有 agent **立即生效**，不需要重新「安装」；
- 卸载技能 = 删掉那条符号链接即可，**仓库本身原封不动**。

复制安装会产生多份副本，容易出现「这个 agent 更新了、那个没更新」的陈旧重复。

### 准备：拿到仓库

```bash
git clone https://github.com/Innoksadk223/kb-skills-repo.git ~/kb-skills
```

下文用 `REPO=~/kb-skills` 指代仓库绝对路径。如果 clone 到别处，把 `REPO` 换成实际路径即可。

> 若目标目录里已存在同名技能（旧副本），先删除那个副本再建链接；`ln -s` 不会覆盖已存在的同名条目。

### 各 agent 的链接命令

本仓库 5 个技能目录分别是：`social-science-km`、`deep-reading-to-wiki`、`karpathy-wiki`、`SiliconFlow-rag`、`wiki-paper-outline`。

**Claude Code —— `~/.claude/skills`（扁平目录）**

```bash
REPO=~/kb-skills
mkdir -p ~/.claude/skills
ln -s "$REPO/skills/social-science-km"    ~/.claude/skills/social-science-km
ln -s "$REPO/skills/deep-reading-to-wiki" ~/.claude/skills/deep-reading-to-wiki
ln -s "$REPO/skills/karpathy-wiki"        ~/.claude/skills/karpathy-wiki
ln -s "$REPO/skills/SiliconFlow-rag"      ~/.claude/skills/SiliconFlow-rag
ln -s "$REPO/skills/wiki-paper-outline"   ~/.claude/skills/wiki-paper-outline
```

**Codex —— `~/.codex/skills`（扁平目录）**

```bash
REPO=~/kb-skills
mkdir -p ~/.codex/skills
ln -s "$REPO/skills/social-science-km"    ~/.codex/skills/social-science-km
ln -s "$REPO/skills/deep-reading-to-wiki" ~/.codex/skills/deep-reading-to-wiki
ln -s "$REPO/skills/karpathy-wiki"        ~/.codex/skills/karpathy-wiki
ln -s "$REPO/skills/SiliconFlow-rag"      ~/.codex/skills/SiliconFlow-rag
ln -s "$REPO/skills/wiki-paper-outline"   ~/.codex/skills/wiki-paper-outline
```

**Hermes —— `~/.hermes/skills/research`（Hermes 按用途分组，研究类技能放在 `research/` 子目录）**

```bash
REPO=~/kb-skills
mkdir -p ~/.hermes/skills/research
ln -s "$REPO/skills/social-science-km"    ~/.hermes/skills/research/social-science-km
ln -s "$REPO/skills/deep-reading-to-wiki" ~/.hermes/skills/research/deep-reading-to-wiki
ln -s "$REPO/skills/karpathy-wiki"        ~/.hermes/skills/research/karpathy-wiki
ln -s "$REPO/skills/SiliconFlow-rag"      ~/.hermes/skills/research/SiliconFlow-rag
ln -s "$REPO/skills/wiki-paper-outline"   ~/.hermes/skills/research/wiki-paper-outline
```

**共享全局目录 —— `~/.agents/skills`（Pi / Codex 的全局技能目录共用）**

```bash
REPO=~/kb-skills
mkdir -p ~/.agents/skills
ln -s "$REPO/skills/social-science-km"    ~/.agents/skills/social-science-km
ln -s "$REPO/skills/deep-reading-to-wiki" ~/.agents/skills/deep-reading-to-wiki
ln -s "$REPO/skills/karpathy-wiki"        ~/.agents/skills/karpathy-wiki
ln -s "$REPO/skills/SiliconFlow-rag"      ~/.agents/skills/SiliconFlow-rag
ln -s "$REPO/skills/wiki-paper-outline"   ~/.agents/skills/wiki-paper-outline
```

**一次装到多个目录（可选批量写法）**

```bash
REPO=~/kb-skills
for SKILL in social-science-km deep-reading-to-wiki karpathy-wiki SiliconFlow-rag wiki-paper-outline; do
  mkdir -p ~/.claude/skills ~/.codex/skills ~/.hermes/skills/research ~/.agents/skills
  ln -s "$REPO/skills/$SKILL" ~/.claude/skills/"$SKILL"
  ln -s "$REPO/skills/$SKILL" ~/.codex/skills/"$SKILL"
  ln -s "$REPO/skills/$SKILL" ~/.hermes/skills/research/"$SKILL"
  ln -s "$REPO/skills/$SKILL" ~/.agents/skills/"$SKILL"
done
```

### 卸载

删除对应的符号链接即可，仓库不受影响：

```bash
rm ~/.claude/skills/social-science-km
```

（只删链接本身；`rm -rf` 打到仓库路径会误删正本，注意别写错目标。）

### 只有 5 个技能随本仓库安装

本仓库安装的就是上面 5 个技能。文档解析与学术搜索等外围能力（`academic-search`、`mineru-document-extractor`、MinerU MCP、`markitdown`、`paper-spine`）**从各自上游安装**，见「技能列表 → 上游 / 第三方」与「配置与运维手册 → 上游组件安装入口」。

---

## 技能列表

### 本仓库安装（5 个）

| 技能 | 负责什么 |
|---|---|
| [`social-science-km`](skills/social-science-km/SKILL.md) | 总调度入口：按用户目标选择转换、深读、编译、检索或维护，并在请求范围内停止 |
| [`deep-reading-to-wiki`](skills/deep-reading-to-wiki/SKILL.md) | 典籍/注疏、专著、教材章节、合集、学位论文等容易被压缩失真的材料，先生成深读档案，避免浅总结直接入库 |
| [`karpathy-wiki`](skills/karpathy-wiki/SKILL.md) | 把原文和深读档案编译成 claims / concepts / entities / comparisons / observations / structures / predicts 等图谱节点 |
| [`siliconflow-rag`](skills/SiliconFlow-rag/SKILL.md) | 建 raw 原文索引 + wiki 结构索引，支持 wiki-first 检索 |
| [`wiki-paper-outline`](skills/wiki-paper-outline/SKILL.md) | 只读已有知识库，经导师式讨论生成有证据出处的社科论文大纲，写入 `outlines/` |

### 大小写契约（务必遵守）

- RAG 技能的**技能标识（frontmatter `name`）是小写** `siliconflow-rag`；
- 它在仓库里的**磁盘目录是大写混合** `skills/SiliconFlow-rag/`；
- **所有命令路径都必须按目录大小写写** `SiliconFlow-rag`（例如 `skills/SiliconFlow-rag/scripts/build_index.py`），写错大小写会导致找不到脚本。
- 私有配置目录保持**全小写**：`~/.hermes/private/siliconflow-rag/`、`~/.codex/siliconflow-rag/`。

### 上游 / 第三方（不随本仓库复制）

| 技能 / 工具 | 负责什么 | 上游 |
|---|---|---|
| `academic-search`（第三方，可选推荐） | 本地资料不足时，搜索相关领域论文、筛选候选文献、判断开放获取 PDF | https://github.com/ustc-ai4science/academic-search |
| `mineru-document-extractor` | PDF、扫描件、表格、公式、多格式文档高保真解析 | https://github.com/opendatalab/MinerU-Ecosystem |
| MinerU MCP | 推荐的文档解析 MCP 服务（知识库工作流优先） | https://github.com/opendatalab/MinerU-Ecosystem/tree/main/mcp |
| `markitdown` | Word、PPT、Excel、HTML、图片等文件轻量转 Markdown | https://github.com/microsoft/markitdown |
| `paper-spine`（第三方，可选推荐） | 需要具体写作时，从材料构筑或改写完整论文，覆盖贡献确认、写作、审计及 LaTeX / PDF / Word 输出 | https://github.com/WUBING2023/PaperSpine |

> **第三方可选推荐：** **Academic-Search Skill** 只在需要搜索、筛选和补充论文资料时使用；已有完整本地资料可直接跳过。**PaperSpine** 只在需要把材料或大纲进一步写成、改成并审计完整论文时使用。两者均由其他项目维护，不属于本仓库。

### 技能来源一览

| 能力 | 来源 | 是否随本仓库安装 |
|---|---|---|
| `deep-reading-to-wiki` / `karpathy-wiki` / `siliconflow-rag` / `social-science-km` / `wiki-paper-outline` | 本仓库 | 是 |
| `academic-search` | https://github.com/ustc-ai4science/academic-search | 否，第三方可选推荐 |
| `mineru-document-extractor` | https://github.com/opendatalab/MinerU-Ecosystem | 否，上游安装 |
| MinerU MCP | https://github.com/opendatalab/MinerU-Ecosystem/tree/main/mcp | 否，上游配置 |
| `markitdown` | https://github.com/microsoft/markitdown | 否，上游安装 |
| `paper-spine` | https://github.com/WUBING2023/PaperSpine | 否，第三方可选推荐 |

---

## 典型工作流

用户只要说：

> 「帮我把这个文件夹里的论文建个知识库」

`social-science-km` 从接到请求起统筹全程，按场景调用下列能力。完整建库时的顺序是：

1. `academic-search`（上游）—— 可选；本地资料不够时，先找相关领域论文并筛出可合法获取的全文
2. `mineru-document-extractor` / MinerU MCP / `markitdown`（上游）—— 把文件转成 Markdown 原文
3. 新库先确定项目路径、领域和最小 Wiki 配置，由 `karpathy-wiki` 初始化 `wiki/SCHEMA.md`、`wiki/index.md`、`wiki/log.md` 等必要结构；已有库读取现有配置
4. 登记本批全部来源的分流结果；`deep-reading-to-wiki` 对需要深读的来源生成并验收档案
5. `karpathy-wiki` —— 按来源或不可拆分的逻辑集合验收就绪条件，编译 Obsidian 可读的图谱 wiki
6. `siliconflow-rag` —— 更新 raw / wiki 双索引

独立合格来源可先推进；blocked 或待深读来源需保留原因和下一步。

### 停止点：用户可能只要其中一步

用户指定范围时，按以下停止点交付：

| 请求范围 | 停止点 |
|---|---|
| 仅转换 | Markdown 原文（raw）验收后结束 |
| 仅深读 | 深读档案交付后结束；可用 standalone 模式，无需强建 Wiki |
| 仅查询 | 检索并回答后结束，不触发资料摄入；只检查当前查询需要的索引 |
| 仅体检 / lint | Wiki 结构检查交给 `karpathy-wiki`，索引状态检查交给 RAG 维护流程；交付问题清单后结束，修复或更新需属于请求范围 |
| 论文大纲 | 只读已有知识库并写入 `outlines/`，不自动补库 |
| 完整建库 / 补库 | 在请求范围内贯穿分流、深读、编译与索引更新 |

用用户的话说就是：「只把这些 PDF 转成 Markdown」→ 转换验收后停；「只深读这篇文献，交付档案」→ 档案交付后停（独立深读无需先建 Wiki）；「只回答这个问题」→ 回答后停，不自动加资料；「只检查断链和待补页面」→ `karpathy-wiki` 检查结构、交付问题清单后停；「只检查索引是否过期」→ 交付索引状态后停，不自动更新。

### 部分批次必须报告为部分完成

用户要求整批完成时，AI 必须**分别报告已完成和未完成的来源**，列出失败或待深读资料的原因和下一步。**部分成功不能称为整批完成。** 每条来源或不可拆分资料集合按自身就绪条件推进；blocked / 待深读的来源不得被包装成「都做完了」。

### 论文大纲的分工边界

`wiki-paper-outline` 负责基于知识库把论点与证据组织成大纲，**不负责直接写成完整论文**。完整链路可理解为：

> `academic-search`（可选搜集论文）→ 本仓库建知识库 → `wiki-paper-outline` 规划大纲 → `paper-spine` 具体写作。

---

## 深读触发规则

**深读由材料性质决定，不由篇幅决定。** 篇幅只提示「值得打开看一眼」，不决定分流路线。不要把深读描述成「给很长的书用的」。

**必做深读（无论长短）** —— 这些材料一旦压缩，最容易丢掉含义：

| 材料类型 | 说明 |
|---|---|
| 典籍 / 原典 / 注疏 / 古文献及其注疏 | 注疏层本身就是解释，摘要代替不了证据 |
| 专著 / 学术著作 | 用来源专属档案 |
| 教材 / 导论 / 手册章节 | 章节论证建立在前文基础上 |
| 论文集 / 合集 / 文集 | 按整卷做合并档案 |
| 学位论文 | |
| 一个连贯的多文件逻辑组 | 整组作为一个单元处理，许多小文件不能因单篇短而逐个溜过 |

**语义覆盖（任意类型、任意长度）：** 理论性强、对论文关键、论证密集、概念有争议，或容易丢失支持 / 反对 / 限定语境的来源，一律走 `deep-reading`。

**其余分流：**

- 篇幅大但都不属于上述情况（例如 500 行以上的普通单篇论文）→ 先检查，再按需深读；**普通单篇论文默认直接编译**，有人要求时才生成档案。
- 短、窄、自成一体、低风险、约 200 行 / 40 KiB 以下且不属于任何集合 → 直接编译（`direct-wiki`）。
- 空、近空、乱码或结构不可用的原文 → `blocked`，退回上游转换流程处理。

篇幅分档（≥500 行 / ≥100 KiB；200–499 行 / 40–99 KiB；<200 行且 <40 KiB）**只提示打开来源检查**：看标题页、目录、标题层级、摘要、结论和论证密度，再问「是不是必做深读材料？有没有语义覆盖？」都不是就是 `direct-wiki` 候选，并记录理由。只有 `direct-wiki` 可以跳过档案。

分流与记录字段（`raw_bytes` / `raw_lines` / `source_type` / `wiki_route` / `route_reason`）的完整规则见 [`skills/social-science-km/references/raw-routing-gate.md`](skills/social-science-km/references/raw-routing-gate.md)；深读档案的输出、质量门与交接见 [`skills/deep-reading-to-wiki/SKILL.md`](skills/deep-reading-to-wiki/SKILL.md)。

---

## 使用方法

### 三步上手

**第一步：丢资料进去。** 跟 AI 说：

> 「帮我把这个文件夹里的论文建个知识库」

AI 会自动：

1. 新库先确定知识库保存路径、研究领域，并初始化最小 Wiki 配置；已有知识库则读取现有配置，不覆盖；
2. 优先用 MinerU 把 PDF 转成可读文本；扫描件、古籍影印本、表格/公式多的资料都走 MinerU；其他格式才优先用 MarkItDown，失败或乱码时也交给 MinerU 兜底；
3. 登记这一批全部资料的处理路线；典籍/注疏、专著、教材章节、合集、学位论文这类材料，以及理论性强、容易被压缩失真的文献，会先生成 `reading_dossiers/` 深读档案；普通单篇论文默认直接编译，你需要时也可以要求深读；
4. 提取概念、实体、比较关系和论证命题；有证据时也提取 observations / structures / predicts 节点；
5. 生成可以在 Obsidian 图谱中看到的 claims / concepts / entities / comparisons 等页面；
6. 建立 raw 原文索引 + wiki 结构索引，后续提问先定位论证路径，再回到原文证据。

已合格的资料会先入库；失败或还没深读完成的资料会列出原因和下一步。如果你要求整批完成，AI 必须说明哪些完成、哪些没完成——部分成功不等于整批成功。建好后 AI 会告诉你知识库在哪个文件夹。

> PDF 解析依赖 **MinerU skill + MinerU MCP（推荐）**，二者均从上游安装，不在本仓库内置：
> - 生态：https://mineru.net/ecosystem
> - 技能：https://github.com/opendatalab/MinerU-Ecosystem/blob/main/skills/SKILL.md
> - MCP：https://github.com/opendatalab/MinerU-Ecosystem/tree/main/mcp
>   README：https://github.com/opendatalab/MinerU-Ecosystem/blob/main/mcp/README.md

**第二步：打开 Obsidian 看图。** 见下方「在 Obsidian 里看图谱」。

**第三步：提问。**

> 「这个概念在哪些论文里出现过？」
> 「A 和 B 有什么区别？」
> 「总结一下这个领域的共识和争议」

AI 不会凭空回答——每个结论都能溯源到具体论文的哪一段。

### 在 Obsidian 里看图谱

[Obsidian](https://obsidian.md) 是一个免费的笔记软件，用来看你的知识图谱。

1. 下载安装 Obsidian
2. 打开 Obsidian → 点击「Open folder as vault」
3. 选择 AI 建好的知识库文件夹
4. 按 `Ctrl/Cmd + G` → 你就能看到一张概念关系网络

**配置颜色（可选，但很好看）：** 图谱视图 → 右上齿轮 → Groups →

- 新建组：`path:claims/` → 紫色
- 新建组：`path:entities/` → 蓝色
- 新建组：`path:concepts/` → 绿色
- 新建组：`path:comparisons/` → 橙色
- 新建组：`path:synthesis/` → 灰色
- 可选：`path:debates/`、`path:observations/`、`path:structures/`、`path:predicts/` → 自选颜色（有这类页面时再加）

### 图谱能看什么

| 你看到的 | 含义 |
|---|---|
| 🟣 紫色节点 | 论证命题、支持、反对、限定关系（`claims/`） |
| 🔵 蓝色节点 | 人物、机构、模型（`entities/`） |
| 🟢 绿色节点 | 理论、概念、方法（`concepts/`） |
| 🟠 橙色节点 | 对比分析（`comparisons/`，概念 A vs 概念 B） |
| ⚪ 灰色节点 | 轻量入口页 / 阅读路线图（`synthesis/`） |
| 其他颜色（可选） | 争议谱系（debates）、经验观察（observations）、理论框架（structures）、预测命题（predicts）——有证据时才会出现 |
| 虚线边框的节点 | 待补充页面——被引用但还没详细内容 |
| 节点之间的连线 | 两份资料之间存在关系 |

**图谱的价值：** 一篇论文提到「确认偏误」，另一篇也提到——你会看到两条线汇聚到同一个绿色节点。这就是 AI 帮你做的事情，靠人眼翻几百页论文做不到。

### 节点类型说明

以上节点位于 `wiki/` 下，按证据需要创建；论文大纲单独放在项目根目录的 `outlines/`。

| 类型 | 含义 |
|---|---|
| `claims/` | 论证命题、支持、反对、限定关系 |
| `concepts/` | 理论、概念、方法 |
| `entities/` | 人物、机构、模型、地点 |
| `comparisons/` | 概念或理论之间的对比 |
| `observations/` | 有来源的观察、事实与现象（可选） |
| `structures/` | 机制、关系与结构解释（可选） |
| `predicts/` | 带前提和验证条件的预测（可选） |
| `synthesis/` | 综述、路线图、阶段性总结 |

### 提问示例

- **建库**：「帮我把 Downloads 里的论文文件夹建个知识库」「这个文件夹叫『认知心理学文献』」
- **加料**：「把这 5 篇新论文也加进去」「继续处理这个文件夹，旧资料不要重跑」
- **查问**：「确认偏误在哪些论文里被讨论过？」「可得性启发和确认偏误有什么关系？」「这个领域目前有什么争议？」
- **体检**：「检查一下知识库有没有断链或矛盾」「有没有哪些概念被多次引用但还没详细页面？」
- **综述**：「总结一下认知偏差这个领域的现状」「帮我写一份这个知识库的综述」
- **大纲**：「基于这个知识库，和我讨论一篇关于 X 的论文大纲」「先给我两个核心论点候选，再一起收敛论文结构」

基于知识库提问时，AI 按问题选择「先查 wiki 结构再回到 raw 原文证据」或「直接检索原文」，并且只检查当前查询需要的索引。小型 Wiki 可直接阅读，回答仍需引用证据。

### 论文大纲流程

`wiki-paper-outline` 只读已有知识库，先检索 wiki 和原文索引、提出骨架与质询，一次讨论一个关键选择；你确认方向后才填充完整大纲，并写入项目根目录的 `outlines/`，**不自动补库**。查证时也会按需利用 `wiki/observations/`、`wiki/structures/`、`wiki/predicts/` 并沿链接核对原文；小型 Wiki 可直接阅读。

要从材料或大纲继续完成论文写作、改稿、审稿审计和 LaTeX / PDF / Word 输出，可选用第三方独立项目 [PaperSpine](https://github.com/WUBING2023/PaperSpine)。

### 常用说法速查

| 你想做 | 直接这样说 |
|---|---|
| 新建知识库 | 「帮我把这个文件夹建成知识库」 |
| 加新资料 | 「把这些新论文加进去」 |
| 看图谱 | 「教我在 Obsidian 打开这个知识库」 |
| 查证据 | 「回答这个问题，并引用原文证据」 |
| 做综述 | 「基于这个知识库写一份文献综述」 |
| 规划论文大纲 | 「基于这个知识库，和我讨论并规划论文大纲」 |
| 写成完整论文 | 「把这些材料和大纲交给 PaperSpine，继续写成论文」 |
| 查断链 | 「检查知识库有没有断链或待补页面」 |
| 配 API Key | 「帮我配置 SiliconFlow API Key，用 BAAI/bge-m3 建索引」 |
| 处理扫描 PDF | 「这批 PDF 是扫描件，优先用 MinerU」 |

不确定怎么说？直接说目标就行：「我有一堆论文，想以后方便提问」「我想把这些资料整理成图谱」「我想知道这些作者之间的观点差异」。AI 应该先判断该走建库、补库、查询、体检还是综述流程，再问必要的问题。

### 常见问题（FAQ）

**Q: 文件存在哪里？**
A: 你电脑上。知识库就是一个普通文件夹，里面的 Markdown 文件可以用任何编辑器打开。

**Q: 我的论文会上传到云端吗？**
A: 只有向量化时会发送文本片段给硅基流动（为了让它能理解内容）。不会存储你的原文。如果介意，可以先问 AI 具体哪些内容会被发送。详见「配置与运维手册 → 隐私与网络边界」。

**Q: 支持什么格式？**
A: PDF、Word、网页文章、纯文本。PDF 默认优先用 MinerU 处理，尤其是扫描版 PDF、古籍影印本、论文、表格和公式；MarkItDown 只作为非 PDF 的轻量转换工具，失败、空输出或乱码时再用 MinerU 兜底。

**Q: 能多人协作吗？**
A: 知识库就是一个文件夹。放在 iCloud 或 Dropbox 里就可以多设备同步。放在 GitHub 上可以协作（注意不要把 API Key 一起提交）。

**Q: 会不会越用越慢？**
A: 不会。新文件加入是增量处理，不重跑旧内容。知识库规模到几百篇论文都没问题。

**Q: 硅基流动（SiliconFlow）是什么？**
A: 知识库背后用的服务，把资料和 wiki 结构「翻译」成数学表示（向量），让 AI 能**理解内容**而不是只匹配关键词。现在会建立两类索引：raw 原文索引（找可引用的原始证据）和 wiki 结构索引（先定位概念、命题、争议和论证路径）。所以提问时通常是先从 wiki 找到问题属于哪个论证网络，再回到 raw 原文找证据。`reading_dossiers/` 只是深读中间层，用来帮助 AI 编译 wiki，**不会被当成原始证据**。硅基流动免费额度够日常用。

---

## 配置与运维手册

技能装好后，外部服务仍需单独配置：MinerU 负责解析复杂文档，SiliconFlow 负责 RAG 向量索引和可选 rerank。

### 最小可用配置

| 能力 | 是否必需 | 需要配置什么 | 不配置会怎样 |
|---|---:|---|---|
| 普通文档转 Markdown | 否 | 上游安装 Microsoft `markitdown` Python 包 | 只能处理已经是 Markdown/文本的资料 |
| MinerU Flash 解析 | 否 | 上游安装 MinerU MCP 或 CLI | 小 PDF/图片/Office 仍可走 flash 模式，但需要工具本身可用 |
| MinerU 高级解析 | 可选 | `MINERU_API_TOKEN`（MCP）或 `MINERU_TOKEN`（CLI） | 无法用更高额度、多格式输出和高级解析 |
| RAG 向量索引 | 是 | `SILICONFLOW_API_KEY` | 只能做 Markdown/wiki，不能建真实语义检索索引 |
| Rerank 精排 | 可选 | 同一个 `SILICONFLOW_API_KEY` | 查询仍可用，只是不做二次精排 |

### 上游组件安装入口

| 组件 | 上游地址 |
|---|---|
| academic-search | https://github.com/ustc-ai4science/academic-search |
| mineru-document-extractor skill | https://github.com/opendatalab/MinerU-Ecosystem/blob/main/skills/SKILL.md |
| MinerU MCP | https://github.com/opendatalab/MinerU-Ecosystem/tree/main/mcp |
| MinerU MCP README | https://github.com/opendatalab/MinerU-Ecosystem/blob/main/mcp/README.md |
| MinerU 生态总入口 | https://mineru.net/ecosystem |
| markitdown | https://github.com/microsoft/markitdown |
| PaperSpine | https://github.com/WUBING2023/PaperSpine |

### MinerU 配置

MinerU 有两条路：MCP 和 CLI。知识库工作流优先用 MCP；MCP 不可用时再用 CLI。**本仓库不内置 MinerU skill 副本**——请从上游安装 skill，并按下方配置 MCP。

**推荐：MinerU MCP。** 安装 `uv` 后，MCP 客户端可以用 `uvx` 直接启动最新版：

```json
{
  "mcpServers": {
    "mineru": {
      "command": "uvx",
      "args": ["mineru-open-mcp"],
      "env": {
        "MINERU_API_TOKEN": "your_token_here",
        "OUTPUT_DIR": "~/mineru-downloads"
      }
    }
  }
}
```

说明：

- `MINERU_API_TOKEN` 可不填；不填时走 **Flash mode**，免费、免注册，但额度和输出能力较低。
- 填 token 后可用更高额度、更多输出格式和更完整的解析能力。Token：https://mineru.net/apiManage/token
- `OUTPUT_DIR` 是批量解析或内容过长时保存结果的目录。
- 有些 MCP 客户端会把拖入的文件放进临时沙盒；让用户尽量给出文件的**完整路径**。

**Streamable HTTP 模式**（需要手动启动 MCP 服务、再让客户端连接）：

```bash
MINERU_API_TOKEN=your_token_here mineru-open-mcp --transport streamable-http --port 8001
```

```json
{
  "mcpServers": {
    "mineru": {
      "type": "streamableHttp",
      "url": "http://127.0.0.1:8001/mcp"
    }
  }
}
```

**备用：MinerU CLI。**

```bash
npm install -g mineru-open-api
mineru-open-api version
```

或 macOS/Linux 使用 Go：

```bash
go install github.com/opendatalab/MinerU-Ecosystem/cli/mineru-open-api@latest
```

认证：

```bash
mineru-open-api auth
export MINERU_TOKEN="your_token_here"
```

CLI token 读取顺序：`--token` 参数 > `MINERU_TOKEN` 环境变量 > `~/.mineru/config.yaml`。

常用命令：

```bash
mineru-open-api flash-extract paper.pdf -o ./out/
mineru-open-api extract paper.pdf -o ./out/ -f md,json --model pipeline
mineru-open-api extract paper.pdf -o ./out/ -f md --model vlm
```

模型选择：

- `pipeline`：更稳，适合要求不幻觉的解析。
- `vlm`：版式理解更强，适合复杂排版，但极少数情况下可能生成幻觉文本。
- `html` / MinerU-HTML：适合需要 HTML 结构的场景。

**MinerU skill 安装（上游）：**

```bash
git clone --depth 1 https://github.com/opendatalab/MinerU-Ecosystem.git /tmp/MinerU-Ecosystem
mkdir -p ~/.claude/skills/mineru-document-extractor
cp /tmp/MinerU-Ecosystem/skills/SKILL.md ~/.claude/skills/mineru-document-extractor/SKILL.md
# Codex: ~/.codex/skills/mineru-document-extractor
# Hermes: ~/.hermes/skills/productivity/mineru-document-extractor
```

### markitdown 配置

```bash
python -m pip install 'markitdown[all]'
python -m markitdown --version
```

上游：https://github.com/microsoft/markitdown
（官方以 CLI/Python 包为主；agent 需要 skill 目录时，可按官方 CLI 写薄封装，不要依赖本仓库内置副本。）

### academic-search 配置（第三方可选推荐）

仅在本地论文资料不足、需要搜索和筛选候选文献时配置；已有完整资料集可跳过。

```bash
# Claude Code
git clone https://github.com/ustc-ai4science/academic-search.git ~/.claude/skills/academic-search
bash ~/.claude/skills/academic-search/scripts/check-deps.sh

# Codex
git clone https://github.com/ustc-ai4science/academic-search.git ~/.codex/skills/academic-search

# Hermes
git clone https://github.com/ustc-ai4science/academic-search.git ~/.hermes/skills/research/academic-search
```

上游：https://github.com/ustc-ai4science/academic-search
建议申请 Semantic Scholar API Key 以提高配额：https://www.semanticscholar.org/product/api#api-key-form

获取全文时**只使用合法的开放获取渠道，不绕过付费墙**。

### PaperSpine 安装（第三方可选推荐）

```bash
git clone https://github.com/WUBING2023/PaperSpine.git
cd PaperSpine
bash install.sh
```

### SiliconFlow RAG 配置

`siliconflow-rag` 用 SiliconFlow embeddings 给 Markdown/wiki 建本地向量索引。**技能标识为小写 `siliconflow-rag`，仓库磁盘目录为 `skills/SiliconFlow-rag/`**（命令按目录大小写写）。索引文件保存在本地。

官方说明：

- Embeddings API：https://docs.siliconflow.cn/en/api-reference/embeddings/create-embeddings
- Rerank API：https://docs.siliconflow.cn/en/api-reference/rerank/create-rerank
- API Key：https://cloud.siliconflow.cn/account/ak

下文 Python 示例中的 `<skills-repo>` 请替换为技能仓库的绝对路径，`<知识库项目>` 替换为知识库根目录。先 `cd "<知识库项目>"`，使 `wiki/`、`检索索引/` 和 `rag_config.json` 均相对该项目解析；脚本从技能仓库直接调用。

#### API Key

推荐用环境变量，最简单也最通用：

```bash
export SILICONFLOW_API_KEY="your_key_here"
```

如果要保存到本地私有文件，当前脚本优先读取（目录全小写）：

```bash
mkdir -p ~/.hermes/private/siliconflow-rag
cat > ~/.hermes/private/siliconflow-rag/config.json <<'JSON'
{
  "SILICONFLOW_API_KEY": "your_key_here"
}
JSON
chmod 600 ~/.hermes/private/siliconflow-rag/config.json
```

兼容旧路径（同样小写，不需要迁移已有配置）：

```text
~/.codex/siliconflow-rag/config.json
```

> **安全红线：** 不要把真实 key 写进仓库、`rag_config.json`、README、日志或索引 manifest。key 只放环境变量或本地私有 config，且私有 config 必须 `chmod 600`。

#### 隐私与网络边界

建索引和查询时，**离开本机发往 SiliconFlow 的内容**只有：用于生成向量的文本片段、查询文本，以及开启 rerank 时的候选片段。原始文件、索引文件、`rag_config.json` 都留在本机。发送之前可以问 AI 具体哪些片段会被发送；对敏感资料可先用 `--mock` 走通流程（见下文）。

#### 默认模型

| 用途 | 默认值 | 说明 |
|---|---|---|
| 嵌入模型 | `BAAI/bge-m3` | 官方 embeddings API 支持；输入上限 8192 tokens，适合中英混合语料 |
| 可选 rerank | `Qwen/Qwen3-Reranker-8B` | 查询时加 `--rerank` 才会调用 |

替换嵌入模型（示例）：

```bash
cd "<知识库项目>"
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/build_index.py" \
  --md-dir wiki/raw \
  --index-dir 检索索引/raw \
  --model BAAI/bge-m3
```

**换模型会导致已有索引需要重建**（见「增量更新 vs 重建」）。

#### `rag_config.json` 字段

非密钥参数可以写在知识库项目根目录的 `rag_config.json`：

```json
{
  "build": {
    "model": "BAAI/bge-m3",
    "chunk_size": 1200,
    "overlap": 200,
    "batch_size": 16,
    "timeout": 60,
    "sleep": 0,
    "dimensions": 1024,
    "encoding_format": "base64"
  },
  "query": {
    "embedding_model": "BAAI/bge-m3",
    "rerank_model": "Qwen/Qwen3-Reranker-8B",
    "top_k": 6,
    "candidates": 12,
    "wiki_top_k": 5,
    "timeout": 60,
    "expand_context": true,
    "context_window": 1,
    "multi_query": false,
    "dimensions": 1024
  }
}
```

- **命令行参数覆盖配置文件的值。**
- 建索引时仍要明确指定数据与索引目录：

```bash
cd "<知识库项目>"
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/build_index.py" \
  --config rag_config.json --md-dir wiki/raw --index-dir 检索索引/raw
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/query_index.py" \
  --config rag_config.json --index-dir 检索索引/raw --question "A 和 B 有什么区别？"
```

- `Qwen/Qwen3-Embedding-*` 支持 Matryoshka 降维；build 与 query 要用**同一个显式维度**（1024 是大语料下实用的存储/传输默认值）。`base64` 响应可减少 JSON 传输开销，不改本地向量格式。
- 建索引会重试瞬时断连、HTTP 429、HTTP 5xx 最多三次（指数退避）。连接不稳或大模型可降低 `batch_size`、增大 `timeout`。
- 长任务会在目标索引目录写 `.embedding_checkpoint.jsonl`，按 chunk ID 断点续跑；仅在 `chunks.jsonl`、`embeddings.jsonl`、`manifest.json` 成功提交后才删除。
- **索引文件不要手工编辑**：每个索引目录的 `manifest.json` / `chunks.jsonl` / `embeddings.jsonl` 要成套保留，需要改就重跑 `build_index.py`。

#### 建两个索引

完整建库或首次索引时，知识库推荐建两个索引：

```bash
cd "<知识库项目>"
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/build_index.py" \
  --md-dir wiki/raw \
  --index-dir 检索索引/raw \
  --metadata-mode enriched_raw \
  --incremental

python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/build_index.py" \
  --md-dir wiki \
  --index-dir 检索索引/wiki \
  --metadata-mode wiki \
  --include-dirs claims,concepts,entities,comparisons,debates,observations,structures,predicts,synthesis,queries \
  --exclude-dirs raw,_archive \
  --incremental
```

- 默认输入 `wiki/raw/`，默认索引输出 `检索索引/`，推荐 `检索索引/raw` 与 `检索索引/wiki`。
- Wiki 索引覆盖 `wiki/` 下的图谱页面，包括按证据需要创建的 `observations/`、`structures/`、`predicts/`；项目根目录的论文大纲 `outlines/` **不在**该索引范围内。
- `enriched_raw` 给 raw chunk 加上取自正式 wiki 节点的检索标签；引用证据永远是原始 raw chunk，绝不是生成的标签。
- **不要把 `reading_dossiers/` 编入任一默认索引**：它是编译指南，既不是原始证据也不是正式图谱。
- 还没有图谱页面时，可先用 `--metadata-mode plain` 建临时 raw 索引；一旦任一支持的图谱目录有页面，就改用 `enriched_raw` 并按需更新/重建原索引；有图谱页面后再建 wiki 索引。

查询时可先用 wiki，再回到 raw 原文证据：

```bash
cd "<知识库项目>"
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/query_index.py" \
  --wiki-first \
  --wiki-index-dir 检索索引/wiki \
  --raw-index-dir 检索索引/raw \
  --question "这个领域的主要争议是什么？"
```

需要精排时加 `--rerank`（何时升级检索方式，见「检索升级规则」）。无论用哪种方式，都要遵守当前任务的外部服务授权范围。

#### 通过总入口检查与查询

`social-science-km` 的 helper 可直接从技能仓库调用并指定项目，无需复制到知识库。已有项目副本仍兼容，不自动覆盖或删除。

```bash
cd "<知识库项目>"
python3 "<skills-repo>/skills/social-science-km/references/km_query.py" \
  --project-root "<知识库项目>" --check
python3 "<skills-repo>/skills/social-science-km/references/km_query.py" \
  --project-root "<知识库项目>" "这个领域的主要争议是什么？"
```

`--check` 检查 raw / wiki 双索引后结束，**不更新索引**。实际查询先选择 raw / wiki 模式，再检查必要索引；直接查 raw 不受无关 Wiki 索引过期阻塞，但仍检查 raw 自身及其 `enriched_raw` 依赖。仅查询不触发摄入；仅 Wiki 结构体检交给 `karpathy-wiki`，报告后结束。获准沿用旧索引查询或写大纲时，应显式加 `--skip-check` 并说明证据可能滞后。

检查与更新索引（当很可能需要更新时，优先用 `check_rebuild_rag.py`，它与 `km_query.py --check` 共享检查/应用逻辑，`--raw-only` / `--wiki-only` 可限定范围）：

```bash
# 仅检查，不更新
python3 "<skills-repo>/skills/social-science-km/references/check_rebuild_rag.py" \
  --project-root "<知识库项目>" --check

# 授权后应用更新（内部用 build_index.py --incremental，路径与 metadata 模式保持一致）
python3 "<skills-repo>/skills/social-science-km/references/check_rebuild_rag.py" \
  --project-root "<知识库项目>"
```

内容新鲜度用 **SHA256** 判断，不看 mtime。raw 索引用 `wiki/raw/` 对比 `检索索引/raw/manifest.json`；`enriched_raw` 还会跟踪 wiki 标签的 `semantic_source_hashes`。wiki 索引对比图谱可读目录与 `检索索引/wiki/manifest.json`（含 `observations`、`structures`、`predicts` 以及 claims/concepts/entities/comparisons/debates/synthesis/queries）。wiki 过期时，先在授权范围内跑可用的 `karpathy-wiki` lint，报告断链、来源漂移、缺失的 claim 结构和 frontmatter 问题，再嵌入；非严重的 lint 问题不阻塞紧急的 raw-only 查询；缺 lint 工具要如实报告，不要和缺 RAG 凭据混为一谈。

**增量更新 vs 重建：**

- `wiki/raw/` 有实质变化 → 更新 raw 索引。工具报告普通的新增/变更文件时，这叫**「新增到索引」或「增量更新」**，不要叫「重建」。
- `claims/`、`concepts/`、`entities/`、`comparisons/`、`debates/`、`observations/`、`structures/`、`predicts/`、`synthesis/`、`queries/` 有实质变化 → 更新 wiki 索引。如果只是文件变了，叫**「增量更新 wiki 索引」**。删除的文件则移除其条目。
- **只有**下列情况才用「**重建**」：索引为空/缺失时的首次构建，或因为 `metadata_mode`、嵌入模型、mock/真实模式、chunk size、overlap、include/exclude 目录、源目录、索引格式变化而触发自动回退的整库重建。显式比较 `model`、`chunk_size`、`overlap`、`dimensions`、`encoding_format` 与 manifest 不一致时，必须整库重建。

索引若过期，除非更新已获授权、或用户明确接受旧索引，否则应停止基于过期索引的检索；后者要在**每次受影响的查询**上加 `--skip-check`，并把「证据可能滞后」的说明带进答案，不得暗示索引是最新的。

#### 不调用 API 的 mock 测试

只想跑通脚本流程、不想调用 SiliconFlow：

```bash
cd "<知识库项目>"
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/build_index.py" \
  --md-dir wiki/raw --index-dir 检索索引/raw --mock
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/query_index.py" \
  --index-dir 检索索引/raw --question "测试" --mock
```

### 给 AI 的教学口径

安装完成后，AI 不要把配置一次性全塞给用户。按这个顺序讲：

1. 先告诉用户：本仓库只装 5 个知识库技能；academic-search 是其他项目维护的可选论文搜集入口，MinerU / markitdown 按文档类型从上游安装。
2. 先告诉用户：不配 API Key 也能整理 Markdown/wiki，但真实语义检索需要 SiliconFlow。
3. 处理 PDF、扫描件、表格、公式时，先问是否已有 MinerU skill + MCP；没有就给上游 skill 安装命令和 MCP 的 `uvx` 配置（见上文）。
4. 用户要建 RAG 索引时，再指导配置 `SILICONFLOW_API_KEY`。
5. 解释默认嵌入模型是 `BAAI/bge-m3`，适合中英文资料；换模型会导致已有索引需要重建。
6. 强调密钥只放环境变量或本地私有 config，不要写进仓库。

### 快速体检

```bash
cd "<知识库项目>"
mineru-open-api version
mineru-open-api auth --verify
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/build_index.py" --help
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/query_index.py" --help
```

### 排障清单

- **`siliconflow-rag` 找不到脚本**：检查大小写——命令必须写 `skills/SiliconFlow-rag/...`（目录名），技能标识才是小写 `siliconflow-rag`。
- **查询/建索引报缺少凭据**：确认 `SILICONFLOW_API_KEY` 环境变量已 export，或私有 config 路径（全小写）正确且 `chmod 600`。
- **建索引中断后重跑**：目录里有 `.embedding_checkpoint.jsonl` 会自动续跑；成功提交后该文件应消失。
- **大批量容易超时/429**：降低 `batch_size`、增大 `timeout`。
- **文件明明存在却搜不到**：路径含空格、括号、中文或 iCloud 同步路径时，文件搜索工具可能返回 0 结果。不要据此判断文件为空或缺失，改为直接读文件，或用 shell `grep -n` 找关键词行号再定位读取；批量 grep 可放在一次 shell 调用里省往返。
- **MCP 读不到拖入的文件**：有些客户端把拖入文件放进临时沙盒，让用户提供完整路径。
- **索引过期阻塞查询**：先更新索引；确需旧索引，显式加 `--skip-check` 并在答案里说明证据可能滞后。

---

## 检索升级规则

**默认先用普通检索，只有当召回、排序或证据风险确实要求时才升级。** 完整的升级条件、模式与参数是单一权威定义，见 [`skills/social-science-km/references/rag-workflow.md#query-routing-and-escalation`](skills/social-science-km/references/rag-workflow.md#query-routing-and-escalation)；本文件不重复其阈值。

---

## 目录结构

```text
kb-skills-repo/
├── README.md                     # 本文件：唯一的权威总文档
├── skills/
│   ├── deep-reading-to-wiki/     # 深读档案层
│   ├── karpathy-wiki/            # 图谱编译
│   ├── SiliconFlow-rag/          # RAG 双索引（注意目录大小写）
│   ├── social-science-km/        # 总调度入口
│   └── wiki-paper-outline/       # 论文大纲
└── docs/                         # 设计与规格记录
```

每个技能目录内通常有 `SKILL.md`（入口）、`references/`（参考规则）与 `scripts/`（可执行脚本）。

---

## 更新与维护

本仓库通过符号链接安装，所以更新只需拉取正本，各 agent 立即生效：

```bash
cd ~/kb-skills
git pull
```

- **技能更新**：`git pull` 后无需重新建链接，符号链接自动指向新内容。
- **新增技能**：若上游新增了技能目录，按「安装」一节给对应 agent 补一条 `ln -s` 即可。
- **移除技能**：删掉对应符号链接，例如 `rm ~/.claude/skills/<技能名>`；仓库不受影响。
- **上游技能**：在你 clone 的上游仓库里各自 `git pull`，或按上游文档升级；MinerU MCP 用 `uvx` 时会自动取最新版。
- **知识库索引维护**：资料或图谱页面变化后，按「配置与运维手册 → 通过总入口检查与查询」检查并按需做增量更新；只有设置/模型/索引格式变化才重建。

> 提交到公开仓库前，务必确认没有把真实 API Key、私有 config 或敏感资料一起提交（见「隐私与网络边界」）。
