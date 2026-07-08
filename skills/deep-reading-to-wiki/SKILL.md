---
name: deep-reading-to-wiki
description: Use when books, chapters, papers, source-discovery shortlists, or long Markdown sources must be read before karpathy-wiki, especially when raw-to-wiki ingest risks shallow summaries, missing claims, weak context, or low evidence density.
---

# Deep Reading To Wiki

Pre-wiki deep-reading layer. 唯一目的：让 `karpathy-wiki` 能写出丰富、有深度的 wiki 词条。一个只给 karpathy-wiki 留下路径名的档案是失败的——它必须留下具体的素材、边界、关系和风险。

Reads a long source with a limited token budget, produces `reading_dossiers/<source-title>-深读档案.md`. Does not write formal wiki pages, does not treat the dossier as raw evidence.

## 反摘要警示

这不是写书评。失败档案三特征：大段复述无逐字摘录和锚点；只列概念名不写边界/反例/上下文；交接清单只有路径名没有内容素材。

成功档案是精读加工件：结构地图 → 候选池（带锚点） → 深挖点（带上下文胶囊） → 可执行交接清单。

摘要 vs 深度判定线：如果一个候选只能写成"X 主张 Y"，却答不出"在原文哪个位置、解决什么问题、压缩成 wiki 节点会误读什么"，那是摘要不是深度——必须补上下文胶囊，否则降级。

## 核心规则

1. **结构优先**：先 Pass 1 扫描全源结构单元，标注功能、相关度、选/跳理由。
2. **分层追溯**：每个高价值候选必须有分层路径（全文 → 部分/论证阶段 → 章节 → 候选点），不从孤立段落建候选池。
3. **三遍递进**：Pass 1 (L0) 结构扫描 → Pass 2 (L1) 稀疏采样建候选池 → Pass 3 (L2/L3) 定向精读高价值候选。不跳级，只在上一遍无法支撑时升级。
4. **无锚点不入选**：候选 claims/concepts 必须有 raw 锚点（文件路径 + 逐字摘录）和上下文胶囊，否则降级。
5. **交接可执行**：每个建议目标含核心贡献、边界/微妙之处、互链建议、必查锚点、入库条件。只有路径名 = 失败。

## 必读定位

阅读源文件前先定位 wiki：

1. 读 `wiki/SCHEMA.md`（域、惯例、分类法）
2. 读 `wiki/index.md`（现有页面和核心 claims）
3. 读 `wiki/log.md` 最近条目
4. 搜索 wiki 中可能重叠的概念、作者、claims、comparisons

不知道 wiki 里已有什么 = 候选重复或漏掉该连接的节点。深读不只是读懂原文，是读懂原文和现有图谱的关系。

## 角色边界

| 层 | 职责 |
|---|---|
| `wiki/raw/` | 原始/转换后源文本，永不修改 |
| `reading_dossiers/` | 预编译精读材料、上下文胶囊、候选节点、交接笔记。不是 raw 证据 |
| `karpathy-wiki` | 正式图谱节点、互链、index.md、log.md、claims、concepts、comparisons |
| RAG 索引 | 证据召回、上下文扩展、引文检查 |

## 阅读预算（三遍递进）

| 遍次 | 级别 | 读什么 | 目的 |
|---|---|---|---|
| Pass 1 | L0 结构扫描 | 目录、导论、结论、章节首尾、标题 | 绘制全源结构地图，标注每个单元的选/跳理由 |
| Pass 2 | L1 稀疏采样 | 定义段、论题段、过渡段、摘要、表格 | 建立候选节点池（concepts / claims / comparisons / entities） |
| Pass 3 | L2 定向精读 | 高价值候选的上下文段落 | 为每个高价值候选制作完整的上下文胶囊 |
| Pass 3 | L3 局部通读 | 核心论证章、主要争议段 | 解决高风险压缩，仅在 L2 不足以支撑胶囊时升级 |

升级条件：低级别无法支撑候选的上下文胶囊时再升级。Pass 1 必须覆盖所有主要单元，Pass 3 (L2/L3) 是局部例外。

## 输出契约

文件：`reading_dossiers/<source-title>-深读档案.md`。加载 `references/dossier-template.md` 获取模板。

必填块：阅读地图 → 候选节点池 → 高价值点深挖 → wiki 交接清单 → 硬门禁自检。

条件模块（仅触发时增加）：

| 触发条件 | 模块 |
|---|---|
| 概念有冲突定义/翻译/测量方式 | 概念谱系模块 |
| 源挑战现有 wiki 主张 | 争议/反驳模块 |
| 某一节是论题核心 | 局部通读模块 |
| 用户正在写论文 | 写作使用模块 |

## 上下文胶囊（CERIC 结构）

每个高价值候选必须按 CERIC 逻辑链填写 5 组字段。这条链就是 karpathy-wiki 用来写深 wiki 词条的素材：

**Claim（主张）** — 作者主张了什么？
1. raw 锚点：文件路径 + 章节 + 逐字摘录
2. 命题类型：main thesis / support / objection / limitation / bridge / definition

**Evidence（证据）** — 作者用什么支撑？
3. 局部语境：该段前后在解决什么问题，导向什么结论
4. 全书位置：这一段在全书论证结构中的角色（premise / support / objection / conclusion / method note）

**Reasoning（推理）** — 论证如何展开？
5. 分层路径：全文 → 部分/论证阶段 → 章节 → 候选点
6. 论证链条：该候选依赖什么前提，推导出什么结论

**Implications（含义）** — 对 wiki 图谱意味着什么？
7. 压缩风险：写成 wiki 节点最容易误读什么——这是反摘要的核心字段
8. wiki 关系：可更新 / 可新建 / 可挑战 / 可忽略的现有 wiki 页面

**Context（边界）** — 什么不是这个主张说的？
9. 方法边界：normative / empirical / conceptual / interpretive / analogy / AI inference
10. RAG 回查问题：可恢复源上下文的问题列表

缺少任一字段不是高价值候选，降为普通候选。这 10 个字段就是交给 karpathy-wiki 的"词条深度素材"——每个 wiki 页面应该能从对应的胶囊字段中直接取材。

## 硬门禁

提交档案前机械检查 + 人工判断：

机械检查：`python skills/deep-reading-to-wiki/scripts/validate_dossier.py <档案路径>`。PASS = frontmatter 完整 + 5 个必备块齐全 + 每个 HV 候选有锚点和胶囊 + 自检有勾选项。FAIL 禁止交接。

人工判断（6 项，参考 `references/example-dossier.md` 对照）：

1. **不是摘要**：有放弃清单 + 有逐字摘录锚点 + 区分了作者主张/AI 推论/迁移建议
2. **足够丰富**：≥ 3 高价值区域 + ≥ 5 候选概念 + ≥ 8 候选 claims + ≥ 2 种 claim 角色（support/objection/limitation/bridge），不达标须解释
3. **结构可追溯**：每个主要单元有 Pass 1 分类和选/跳理由；每个高价值候选有分层路径
4. **胶囊完整**：每个高价值候选 10 字段齐全；缺字段 = 浅，不是深
5. **交接可执行**：每个推荐目标含核心贡献 + 边界 + 互链 + 锚点 + 入库条件；只列路径名 = 不通过
6. **对抗性自问**：回答"如果我是这份档案最大的批评者，我会说哪里肤浅或断章取义？"——如果答不上来，档案可能太浅；如果答上来了，把最尖锐的批评和改进方向写进自检

任一项不通过 = 不可交接。继续精读或报告阻塞。

## 交接清单

交给 karpathy-wiki 必须回答：

- 哪些现有 wiki 页面需更新（页名 + 深化方向 + 来源候选）
- 哪些新页面需创建（目标路径 + 核心贡献 + 边界 + 互链 + 必查锚点 + 入库条件）
- 哪些候选太弱不能入库（原因 + 后续条件）
- 哪些 raw 锚点编译前必查（必查原因）
- 哪些上下文风险必须保留在正式 wiki 页中

## 档案生命周期

draft → compiled（karpathy-wiki 编译后） → archived（移入 `_archive/`） → 硬删除（用户明确批准）。优先存档，不默认删除。

## 输入模式

| 模式 | 条件 | 动作 |
|---|---|---|
| 显式源文件 | 已知 raw 路径 | 直接创建档案 |
| 源发现短名单 | SiliconFlow-rag 候选 + 用户意图 | 筛选后建档 |
| 用户定向缺口 | 只有话题无路径 | 先做源发现，找不到报告阻塞 |

无 raw 路径不建档。

## 必读

写档案前加载：`references/dossier-template.md`（模板）、`references/example-dossier.md`（范例）。

提交档案前：运行 `scripts/validate_dossier.py`，对照 6 项硬门禁。
