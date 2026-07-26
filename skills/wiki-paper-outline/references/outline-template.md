# 大纲文档模板

产出路径：`<知识库>/outlines/YYYY-MM-DD-<主题>.md`

## 骨架档（Phase 1，status: skeleton）

只含以下部分，用于讨论，不填充章节细节：

```markdown
---
topic: <主题>
research-question: <一句话研究问题，未定则写 candidates 列表>
paper-type: empirical | theoretical
status: skeleton
wiki-pages-cited: [slug, ...]
index-stale: false        # 仅带旧索引继续时写 true
---

# 核心论点候选
## 候选 1：<一句话主张>
- 论证链：A → B → C
- 主要风险：<一句话，如"依赖的关键 claim 只有单方证据">
## 候选 2：...（可省略）

# 章节树（每章一行论证任务）
1. <章名> — <论证任务>
2. ...

# 冲突论点清单
| 冲突论点 | 正方页面 | 反方页面 | 拟处理章节 |

# 证据缺口初判
- <缺口> → <影响哪个候选/章节>

# 待讨论问题
（质询问题在对话中逐个提出，此处仅存档已讨论的问题与结论）
```

## 完整档（Phase 2，status: filled）

```markdown
---
topic: <主题>
research-question: <一句话研究问题>
paper-type: empirical | theoretical
status: filled
wiki-pages-cited: [slug, ...]
index-stale: false
---

# 一、核心论点（Thesis）
主张一句话 + 论证链概述（A→B→C），注明经讨论在候选中的选择理由。

# 二、逻辑线总览
一段话：从什么张力/缺口出发 → 经过哪些论证节点 → 落到什么贡献。
配缩进列表或 mermaid 论证流。

# 三、章节大纲
## N. <章节标题>
- 本章论证任务：承接上章<X>，交付下章<Y>
- 论证要点：
  - <要点> [wiki:claims/xxx] 或 [raw:文件]（3-5 条；无出处标 [无证据支撑——需讨论或补料]）
- 冲突论点：<反方立场> → 应对策略：反驳 / 限定 / 吸收（经骨架讨论确定）
- 证据状态：充分 / 薄弱（→ 建议补 <方向>）

# 四、全文冲突论点总表
| 冲突论点 | 反方来源页面 | 处理章节 | 应对策略 |

# 五、注意事项（审稿雷区逐条对照）
逐条引用 pitfalls-checklist.md 条目编号，每条写"本文如何应对"：
- P1 理论贡献：本文的贡献一句话是"……"，在引言第X段陈述
- ...

# 六、证据缺口清单
| 缺什么 | 建议检索词 | 建议补料路径 |
|---|---|---|
| ... | ... | Gap-Driven Expansion / 深读 <源> / 新采集 |

# 附：讨论记录摘要
骨架阶段的质询问题与用户结论，逐条一行。
```
