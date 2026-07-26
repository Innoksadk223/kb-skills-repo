# Reading Dossier Template

Use this template for `reading_dossiers/<source-title>-深读档案.md`. Load `references/example-dossier.md` to see a real filled example.

```markdown
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
raw_lines: 0 # Step 2 manifest 的源转换总行数（合并档案填各源之和），分档配额检查用
---

# <书名或文献名>深读档案

## 1. 阅读地图

### 结构/问题地图
| 部分 | 功能 | 解决什么问题 | 推进哪条主线 | wiki 缺口 | 覆盖层级 | 选/跳理由 |
|---|---|---|---|---|---|---|
| 导论/第一章 | 开题/定义/问题化 | ... | ... | [[已有页]] / 新缺口 | L1/L2/L3/跳过 | 高相关/重复/低相关 |

### 高价值区域
| 区域 | 结构角色 | 为什么值得深挖 | 预计输出 |
|---|---|---|---|
| 章节/小节 | definition/premise/support/objection/limitation/bridge/conclusion | 能支撑/挑战哪个 wiki 节点 | claim/concept/comparison |

### 放弃清单
| 未深读区域 | 覆盖层级 | 放弃原因 | 重新触发条件 |
|---|---|---|---|
| 章节/小节 | L0/L1 | 低相关/重复/证据不足 | 用户要求/后续检索命中 |

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

## 3. 高价值点深挖

Repeat for each high-value candidate.

### HV-N: <候选点名称>

- 候选类型：claim / concept / comparison / entity
- 价值判断：为什么值得进入或更新 wiki

#### 上下文胶囊（CERIC 结构，10 字段）

**Claim（主张）**
1. raw 锚点：`wiki/raw/...` + 章节
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
- [ ] 3. 结构可追溯：□ 每个主要单元有 Pass 1 选/跳理由 □ 每个高价值候选有分层路径（CERIC 字段 5）
- [ ] 4. 胶囊完整：□ 每个高价值候选 10 字段（CERIC 五组）齐全
- [ ] 5. 交接可执行：□ 每个推荐目标含核心贡献、边界、互链、锚点、入库条件
- [ ] 6. 对抗性自问：如果我是这份档案最大的批评者，我会说哪里肤浅或断章取义？（回答最尖锐的批评并写出 ≥1 条具体批评+改进方向，然后才可勾选。答不上来 = 档案可能太浅。）

任一项不通过 = 不可交接。继续精读或报告阻塞。交接前运行：

```bash
python3 <本技能目录>/scripts/validate_dossier.py reading_dossiers/<档案>.md
```

FAIL = 不得交接。
```
