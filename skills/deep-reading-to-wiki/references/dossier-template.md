# Reading Dossier Template

Use this template for `reading_dossiers/<source-title>-深读档案.md`. Load `references/example-dossier.md` to see a real filled example.

````markdown
---
title: <书名或文献名>深读档案
type: reading_dossier
source_raw:
  - wiki/raw/...
trigger: explicit_source # explicit_source / user_directed_expansion / retroactive_repair
user_intent: ""
source_discovery:
  - path: wiki/raw/...
    reason: ""
    key_terms: []
status: draft
target: karpathy-wiki
created: YYYY-MM-DD
updated: YYYY-MM-DD
compiled_to: []
confidence: medium
raw_lines: 0 # 转换 manifest 的总行数；standalone 直接统计源文件；合并档案填各源之和
reading_mode: thorough # thorough / budget；记录实际采用的模式
---

# <书名或文献名>深读档案

## 1. 阅读地图

记录实际阅读模式与覆盖证据。thorough：每个源按 200-400 行窗口顺序完整阅读，逐窗记录行号、候选与零候选复读结果；所有纳入源全文完成后才选 HV。budget：记录 L0-L3 覆盖，<300 行全文读，300-500 行除弱相关外全文读，>500 行从 L0/L1 开始。合并档案逐文件遵守同一模式规则，raw_lines 配额仍按总行数计算。

### 结构/问题地图
| 部分 | 功能 | 解决什么问题 | 推进哪条主线 | wiki 缺口 | 覆盖层级 | 选/跳理由 |
|---|---|---|---|---|---|---|
| 导论/第一章 | 开题/定义/问题化 | ... | ... | [[已有页]] / 新缺口 | thorough: 已顺读+窗口行号；budget: L0/L1/L2/L3/跳过 | 高相关/重复/低相关 |

### 高价值区域
| 区域 | 结构角色 | 为什么值得深挖 | 预计输出 |
|---|---|---|---|
| 章节/小节 | definition/premise/support/objection/limitation/bridge/conclusion | 能支撑/挑战哪个 wiki 节点 | claim/concept/comparison |

### 放弃清单

thorough 只列已读但未选入 HV 的区域、零候选复读结果，另明确用户排除的文件；不得用放弃清单代替顺读。budget 列未深读/跳过区间与理由。没有放弃项时明确写「无」。

| 未选入/未深读区域（文件+行号） | 覆盖层级/窗口 | 放弃原因 | 重新触发条件 |
|---|---|---|---|
| 章节/小节 | 已顺读/零候选复读 / L0/L1 | 低相关/重复/证据不足 | 用户要求/后续检索命中 |

## 2. 候选节点池

### 候选 Concepts
| 概念 | 作者用法 | 边界/相邻概念 | raw 锚点 | 建议 |
|---|---|---|---|---|
| ... | ... | ... | wiki/raw/... | 新建/更新/忽略 |

### 候选 Claims
| 命题 | 类型 | 支撑/反驳/限制什么 | raw 锚点 | 价值 |
|---|---|---|---|---|
| ... | main/support/objection/limitation/bridge | ... | wiki/raw/... | 高/中/低 |

### 候选 Comparisons / Entities
| 对比或实体 | 类型 | 差异核心/与本库关系 | raw 锚点 | 建议 |
|---|---|---|---|---|
| ... | ... | ... | wiki/raw/... | ... |

### 候选 Observations / Structures / Predictions（有证据需要时才添加）

不要求凑齐类型，不新增配额，也不抵扣 Concepts/Claims 配额。observation 保留观察/数据与方法限制；structure 保留框架组成、关系与适用范围；prediction 保留前提、条件、推理链和不确定性，区分作者预测与 AI 推论。

| 候选点 | 类型 / 目标目录 | 证据及边界 | raw 锚点 | 建议 |
|---|---|---|---|---|
| ... | observation / observations；structure / structures；prediction / predicts | ... | 文件+行号 | 新建/更新/暂不入库 |

## 3. 高价值点深挖

Repeat for each high-value candidate; every type requires the same 10-field capsule.

### HV-N: <候选点名称>

- 候选类型：claim / concept / comparison / entity / observation / structure / prediction
- 价值判断：为什么值得进入或更新 wiki

#### 上下文胶囊（CERIC 结构，10 字段）

**Claim（主张）**
1. raw 锚点：`wiki/raw/...` + 行号区间 + 章节（standalone 使用实际文件路径；跨源候选列全相关锚点）
   > 逐字摘录
2. 命题类型：main thesis / support / objection / limitation / bridge / definition

**Evidence（证据）**
3. 局部语境：这段前后在解决什么问题，导向什么结论
4. 全书位置：definition / premise / support / bridge / objection / limitation / conclusion / method note

**Reasoning（推理）**
5. 分层路径：全文 → 部分/论证阶段 → 章节 → 候选点
6. 论证链条：该候选依赖什么前提，推导出什么结论

**Implications（含义）**
7. 压缩风险：写成 wiki 节点最容易误读什么——反摘要核心字段
8. wiki 关系：可更新 / 可新建 / 可挑战 / 可忽略（具体页面和理由）

**Context（边界）**
9. 方法边界：normative / empirical / conceptual / interpretive / analogy / AI inference
10. RAG 回查问题：
   - 问题 1
   - 问题 2

## 4. wiki 交接清单

- 项目根 / Wiki 路径：...（standalone 无目标时明确说明）
- 请求范围 / 停止点：...
- 原文路径与来源集合：...（含不可拆分组）
- route / reason：...（核心调度时沿用 manifest）
- 阅读模式 / 覆盖记录：...
- 档案路径 / 门禁结果：...（结构验收与原文证据核验分别记录；未执行标明原因）
- 允许写入范围：...
- 已完成 / 阻塞项与下一步：...

### 建议新建
| 目标路径 | 类型 | 核心贡献 | 边界/微妙之处 | 互链 | 必查锚点 | 入库条件 |
|---|---|---|---|---|---|---|
| wiki/claims/... | claim | ... | ... | [[...]] | `wiki/raw/...` | ... |

### 建议更新
| 现有页面 | 深化方向 | 核心贡献 | 来源候选 | 互链 | 注意 |
|---|---|---|---|---|---|
| wiki/concepts/... | 补定义边界/反例/限制 | ... | HV-1 | [[...]] | ... |

### 必查 raw 锚点
| raw 锚点 | 支撑哪个 wiki 动作 | 必查原因 |
|---|---|---|
| `wiki/raw/...` | 新建/更新 `wiki/...` | 防止断章取义/保留限制条件 |

### 暂不进入 wiki
| 内容 | 原因 | 后续条件 |
|---|---|---|
| ... | 证据弱/重复/偏离主题 | ... |

## 5. 硬门禁自检

对每项写"通过/不通过 + 证据"。**通过必须把勾选框打为 `- [x]`**；任何一项保持 `- [ ]` 即视为未通过，`validate_dossier.py` 与 karpathy-wiki 编译端都会拒收。

- [ ] 1. 不是摘要：□ 有放弃清单 □ 有逐字摘录锚点 □ 区分了作者主张/AI推论/迁移建议
- [ ] 2. 足够丰富：达到 raw_lines 分档配额（见 quality-gates.md Gate 2 分档表）+ ≥ 2 种 claim 角色。确实达不到时写「配额豁免：<逐条指认贫瘠行号区间与原因>」后仍可勾选
- [ ] 3. 结构可追溯：□ 每个主要单元有功能与选/弃理由 □ 每个高价值候选有分层路径（CERIC 字段 5）□ 模式纪律满足 Gate 6（thorough 完整顺读后选 HV；budget 按结构采样并保留短文全文读例外；合并档案逐源记录）
- [ ] 4. 胶囊完整：□ 每个高价值候选 10 字段（CERIC 五组）齐全
- [ ] 5. 交接可执行：□ 每个推荐目标含核心贡献、边界、互链、锚点、入库条件
- [ ] 6. 对抗性自问：如果我是这份档案最大的批评者，我会说哪里肤浅或断章取义？（回答最尖锐的批评并写出 ≥1 条具体批评+改进方向，然后才可勾选。答不上来 = 档案可能太浅。）

任一项不通过 = 不可交接。继续精读或报告阻塞。交接前运行：

```bash
python3 <本技能目录>/scripts/validate_dossier.py reading_dossiers/<档案>.md
```

FAIL = 不得交接。PASS 仅代表结构检查通过；正式编译前仍须核对关键原文、上下文、阅读覆盖与候选主张是否相符，不能把勾选或 PASS 当作证据成立。
````
