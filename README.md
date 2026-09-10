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

这一节是给 AI agent 的操作契约：先看「怎么用这套技能」，再看安装完成后怎么向用户介绍。

### 怎么用这套技能

**入口只有一个。** 用户提出任何与知识库相关的事——建库、加资料、提问、体检、写作辅助——都先走 `social-science-km`：由它判断该走哪条路线、按需调用其他技能、并在用户要求的范围内停下。不要自己另拼一套流程。

**这份 README 是地图，操作规程在技能里。** 动手前先读要用到的那个技能的 `SKILL.md`，以及它指向的 `references/`。README 只讲「这个仓库有什么、边界在哪、命令长什么样」；具体步骤以技能文件为准，两者冲突时也以技能文件为准。

**先判断请求范围，再动手。** 用户可能只要其中一步（只转换 / 只深读 / 只回答一个问题）。见「典型工作流 → 停止点」：到了那个点就交付并停止，不要顺手把整条链路跑完。

**下面这些动作要先问用户**：把资料发往外部服务、下载论文、增删或重建索引、长时间批量转换、批量改动 10 个以上 wiki 页面或改动 SCHEMA 分类、移动或删除原始文件。已经在当前任务里授权过的，不必重复追问。

**如实汇报。** 部分完成就说部分完成，列清楚哪些好了、哪些卡住及原因；没跑过的验证不要写成通过；缺某个工具或 key 只阻塞依赖它的那部分工作，不要当成全局中止。

**用户只说人话时**，用「使用方法 → 怎么提问」的对照表判断意图，再补齐必要信息（资料在哪、想拿它做什么）。缺信息就问，不要猜。

### 安装/更新完成后的介绍流程

用户安装或更新完成后，**不要只说「装好了」，也不要先问用户要不要介绍**。默认直接给一段 3 分钟上手教程，例如：

> 「知识库技能包已经装好。我先用 3 分钟带你上手：你不用记技能名，直接说资料目标，AI 会自己选择解析、深读、建图谱和检索流程。
> 如果你只想听总览，我会讲最短版；也可以选一个方向深入讲：建库、加资料、Obsidian 看图、提问检索、SiliconFlow API Key、MinerU MCP。」

介绍时按这个顺序讲，保持简短，**不要把配置一次性全塞给用户**：

1. 先用「一句话原则」说明：**用户只管说资料目标，AI 负责挑技能和流程。**
2. 说明本仓库只装 5 个知识库技能；`academic-search` 是其他项目维护的可选论文搜集入口，MinerU / markitdown 按文档类型从上游安装（见「技能列表」）。
3. 用最短总览说明：`social-science-km` 统筹全程，按请求范围选择步骤；完整建库是「文件转 Markdown → 最小 Wiki 初始化 → 深读档案 → wiki 图谱 → RAG 索引」，之后可基于证据问答。
4. 给 3-5 个常用说法示例，不要一次灌输全部细节（见「使用方法 → 怎么提问」）。
5. 用户问 Obsidian 时，教他打开知识库文件夹并按 `Ctrl/Cmd + G` 看图谱。
6. 用户问 API Key 时，先说明不配置也能整理 Markdown/wiki，但真实语义检索需要 SiliconFlow；再指导配置 `SILICONFLOW_API_KEY`，并强调密钥只放环境变量或本地私有 config，不要写进仓库（见「RAG 配置（SiliconFlow）」）。
7. 用户处理 PDF、扫描件、表格或公式时，先问是否已有 MinerU skill + MCP；没有就给出上游安装命令和 MCP 的 `uvx` 配置，并提醒本仓库不内置副本（见「技能列表 → 上游 / 第三方」）。
8. 解释默认嵌入模型是 `BAAI/bge-m3`，适合中英文资料；换模型会导致已有索引需要重建。
9. 结尾问用户想重点了解哪一块；如果用户明确说不用介绍，就收住。

---

## 安装

把本仓库 `skills/` 下的 5 个技能目录放进你所用 AI agent 的技能目录即可——目录在哪、怎么加载，按你那份 agent 的文档来，不确定就交给 AI 办。仓库用 `git clone https://github.com/Innoksadk223/kb-skills-repo.git` 取得，之后更新就是 `git pull`。

文档解析、学术搜索等外围能力不随本仓库提供，见「技能列表 → 上游 / 第三方」。

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

---

## 典型工作流

用户只要说：

> 「帮我把这个文件夹里的论文建个知识库」

`social-science-km` 从接到请求起统筹全程，按场景调用下列能力。完整建库时的顺序是：

1. `academic-search`（上游）—— 可选；本地资料不够时，先找相关领域论文并筛出可合法获取的全文
2. `mineru-document-extractor` / MinerU MCP / `markitdown`（上游）—— 把文件转成 Markdown 原文
3. 新库先确定项目路径、领域和最小 Wiki 配置，由 `karpathy-wiki` 初始化 `wiki/SCHEMA.md`、`wiki/index.md`、`wiki/log.md` 等必要结构；已有库读取现有配置
4. 登记本批全部来源的分流结果；`deep-reading-to-wiki` 对需要深读的来源生成并验收档案（哪些来源需要深读，见「深读触发规则」）
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

AI 会按「典型工作流」自动走完转换、深读、编译和索引；你也可以只要求其中一步，停止点见「典型工作流 → 停止点」。哪些资料需要深读，见「深读触发规则」。完成后 AI 会告诉你知识库在哪个文件夹。

> PDF 解析依赖 **MinerU skill + MinerU MCP（推荐）**，二者均从上游安装，不在本仓库内置；安装与配置见「技能列表 → 上游 / 第三方」。

**第二步：打开 Obsidian 看图。** 见下方「在 Obsidian 里看图谱」。

**第三步：提问。** AI 不会凭空回答——每个结论都能溯源到具体论文的哪一段。常用说法见「怎么提问」。

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

### 节点类型与颜色

图谱页面都位于 `wiki/` 下，按证据需要创建；论文大纲单独放在项目根目录的 `outlines/`。

| 目录 | 图谱颜色 | 含义 |
|---|---|---|
| `claims/` | 🟣 紫色 | 论证命题、支持、反对、限定关系 |
| `entities/` | 🔵 蓝色 | 人物、机构、模型、地点 |
| `concepts/` | 🟢 绿色 | 理论、概念、方法 |
| `comparisons/` | 🟠 橙色 | 概念或理论之间的对比（概念 A vs 概念 B） |
| `synthesis/` | ⚪ 灰色 | 综述、路线图、阶段性总结（轻量入口页） |
| `debates/`、`observations/`、`structures/`、`predicts/`（可选） | 自选颜色 | 争议谱系、经验观察、理论框架、预测命题——有证据时才会出现 |
| 虚线边框的节点（非目录） | — | 待补充页面：被引用但还没详细内容 |
| 节点之间的连线（非目录） | — | 两份资料之间存在关系 |

**图谱的价值：** 一篇论文提到「确认偏误」，另一篇也提到——你会看到两条线汇聚到同一个绿色节点。这就是 AI 帮你做的事情，靠人眼翻几百页论文做不到。

### 怎么提问

| 你想做 | 直接这样说 |
|---|---|
| 新建知识库 | 「帮我把这个文件夹建成知识库」「这个文件夹叫『认知心理学文献』」 |
| 加新资料 | 「把这些新论文加进去」「继续处理这个文件夹，旧资料不要重跑」 |
| 看图谱 | 「教我在 Obsidian 打开这个知识库」 |
| 查证据 | 「确认偏误在哪些论文里被讨论过？」「可得性启发和确认偏误有什么关系？」「这个领域目前有什么争议？」 |
| 做综述 | 「基于这个知识库写一份文献综述」「总结一下这个领域的现状」 |
| 规划论文大纲 | 「基于这个知识库，和我讨论并规划论文大纲」「先给我两个核心论点候选，再一起收敛论文结构」 |
| 写成完整论文 | 「把这些材料和大纲交给 PaperSpine，继续写成论文」 |
| 查断链 / 体检 | 「检查一下知识库有没有断链或矛盾」「有没有哪些概念被多次引用但还没详细页面？」 |
| 配 API Key | 「帮我配置 SiliconFlow API Key，用 BAAI/bge-m3 建索引」 |
| 处理扫描 PDF | 「这批 PDF 是扫描件，优先用 MinerU」 |

基于知识库提问时，AI 按问题选择「先查 wiki 结构再回到 raw 原文证据」或「直接检索原文」，并且只检查当前查询需要的索引。小型 Wiki 可直接阅读，回答仍需引用证据。

不确定怎么说？直接说目标就行：「我有一堆论文，想以后方便提问」「我想把这些资料整理成图谱」「我想知道这些作者之间的观点差异」。AI 应该先判断该走建库、补库、查询、体检还是综述流程，再问必要的问题。

### 论文大纲流程

`wiki-paper-outline` 只读已有知识库，先检索 wiki 和原文索引、提出骨架与质询，一次讨论一个关键选择；你确认方向后才填充完整大纲，并写入项目根目录的 `outlines/`，**不自动补库**。查证时也会按需利用 `wiki/observations/`、`wiki/structures/`、`wiki/predicts/` 并沿链接核对原文；小型 Wiki 可直接阅读。

要从材料或大纲继续完成论文写作、改稿、审稿审计和 LaTeX / PDF / Word 输出，可选用第三方独立项目 [PaperSpine](https://github.com/WUBING2023/PaperSpine)。

### 常见问题（FAQ）

**Q: 文件存在哪里？**
A: 你电脑上。知识库就是一个普通文件夹，里面的 Markdown 文件可以用任何编辑器打开。

**Q: 我的论文会上传到云端吗？**
A: 只有做向量化时，文本片段和查询文本会发往硅基流动，不会存储你的原文；原始文件、索引文件和 `rag_config.json` 都留在本机。详见「RAG 配置（SiliconFlow）」的隐私边界。

**Q: 支持什么格式？**
A: PDF、Word、网页文章、纯文本；PDF 默认优先用 MinerU，非 PDF 走 MarkItDown 轻量转换，失败、空输出或乱码时再用 MinerU 兜底。安装见「技能列表 → 上游 / 第三方」。

**Q: 能多人协作吗？**
A: 知识库就是一个文件夹。放在 iCloud 或 Dropbox 里就可以多设备同步。放在 GitHub 上可以协作（注意不要把 API Key 一起提交）。

**Q: 会不会越用越慢？**
A: 不会。新文件加入是增量处理，不重跑旧内容。知识库规模到几百篇论文都没问题。

**Q: 硅基流动（SiliconFlow）是什么？**
A: 知识库背后用的服务，把资料和 wiki 结构「翻译」成数学表示（向量），让 AI 能**理解内容**而不是只匹配关键词。现在会建立两类索引：raw 原文索引（找可引用的原始证据）和 wiki 结构索引（先定位概念、命题、争议和论证路径）。所以提问时通常是先从 wiki 找到问题属于哪个论证网络，再回到 raw 原文找证据。`reading_dossiers/` 只是深读中间层，用来帮助 AI 编译 wiki，**不会被当成原始证据**。硅基流动免费额度够日常用。

---

## RAG 配置（SiliconFlow）

> 这一节只讲「这是什么、要准备什么、边界在哪、细节在哪」；具体命令与运维步骤以技能文件为准，本文件不复述。

知识库的**语义检索**靠 `siliconflow-rag` 调用 SiliconFlow embeddings，给 Markdown 与 wiki 建本地向量索引；不配置它，仍然可以整理 Markdown 与 wiki 图谱，但没有真正的语义检索。

其余外围能力（MinerU 文档解析、markitdown 轻量转换、academic-search 学术搜索、PaperSpine 论文写作）都**从上游安装**，入口见「技能列表 → 上游 / 第三方」。

**要准备什么：** 把 API Key 放环境变量 `SILICONFLOW_API_KEY`，或存到本地私有 config `~/.hermes/private/siliconflow-rag/config.json` 并 `chmod 600`。

**安全红线：** 不要把真实 key 写进仓库、`rag_config.json`、README、日志或索引 manifest；key 只放环境变量或本地私有 config。

**隐私边界：** 建索引和查询时，离开本机的只有用于生成向量的文本片段、查询文本，以及开启 rerank 时的候选片段；原始文件与索引文件都留在本机。对敏感资料可先用 `--mock` 走通流程；把资料发往外部服务前，遵守当前任务的授权范围。

**默认模型：** 嵌入 `BAAI/bge-m3`，可选 rerank `Qwen/Qwen3-Reranker-8B`（查询时加 `--rerank` 才调用）；**换嵌入模型会导致已有索引需要重建**。非密钥参数写在知识库项目根目录的 `rag_config.json`。

**细节在技能里：** 建 raw / wiki 两个索引、检查与更新索引、增量更新与重建的区分、参数调整、断点续跑等具体操作，以技能本体为单一权威定义——[`skills/SiliconFlow-rag/SKILL.md`](skills/SiliconFlow-rag/SKILL.md) 与 [`skills/social-science-km/references/rag-workflow.md`](skills/social-science-km/references/rag-workflow.md)；AI 按需读取这两处。

**官方文档：** [Embeddings API](https://docs.siliconflow.cn/en/api-reference/embeddings/create-embeddings)｜[Rerank API](https://docs.siliconflow.cn/en/api-reference/rerank/create-rerank)｜[API Key](https://cloud.siliconflow.cn/account/ak)

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
- **知识库索引维护**：资料或图谱页面变化后，按 [`skills/SiliconFlow-rag/SKILL.md`](skills/SiliconFlow-rag/SKILL.md) 与 [`skills/social-science-km/references/rag-workflow.md`](skills/social-science-km/references/rag-workflow.md) 里的索引维护流程检查并按需做增量更新；只有设置/模型/索引格式变化才重建。

> 提交到公开仓库前，务必确认没有把真实 API Key、私有 config 或敏感资料一起提交（见「RAG 配置（SiliconFlow）」）。
