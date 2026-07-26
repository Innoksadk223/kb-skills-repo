# wiki-paper-outline 技能设计

日期：2026-07-26
状态：已与用户确认设计，待实现

## 目标

wiki 建成后，基于用户需求 + wiki 关系网 + RAG 检索，通过"学生-导师式讨论"生成社科论文大纲。大纲包含：核心论点、逻辑线、章节结构、冲突论点、审稿注意事项、证据缺口。

## 定位与边界

- **只读消费** `<知识库>/wiki/` 和 `<知识库>/检索索引/`；产出写入 `<知识库>/outlines/YYYY-MM-DD-<主题>.md`
- 不写 wiki 页、不建/改索引、不自动补料、运行时不联网
- 目标场景：社科实证/理论论文（期刊论文骨架：引言-文献综述-理论框架-论证-讨论）
- 证据缺口只标注 + 建议走 social-science-km 的 Gap-Driven Expansion，不自动触发

## 核心交互模式：导师式讨论

整个流程模拟学生与导师讨论论文构思。Phase 1 结束的 checkpoint 不是"给用户过目"，而是一轮质询讨论：

- 骨架草稿必须附带 2-4 个导师质询问题（选题聚焦度、论点风险、冲突论点应对策略等）
- 一次只讨论一个问题（AskUserQuestion 或对话）
- 方向收敛后才进入 Phase 2；用户可多轮调整骨架

## 流程（人机两阶段）

```
Phase 0  需求对齐
  - 解析用户输入：研究问题、论文取向（empirical/theoretical）、篇幅预期
  - python km_query.py --check 确认索引未过期；过期则提示先重建，不硬查

Phase 1  骨架阶段
  1. 图谱勘探：grep 主题相关 wiki 页 → 读页面 → 构建图谱邻域表
     （复用 social-science-km/references/wiki-graph-expanded-query.md 的 Phase 1；
      重点提取类型化关系 supports/contradicts/derives_from/follows）
  2. 初轮检索：生成 2-4 个关系驱动子问题，km_query.py --deep 并行查
  3. 产出骨架草稿：thesis 候选 1-2 个、章节树（每章一句话论证线）、
     冲突论点清单（来自 debates/ + contradicts 关系）、证据缺口初判
  4. 导师式讨论 checkpoint（天然断点，无 state 文件）

Phase 2  填充阶段
  5. 逐章节：沿该章关系链再发 1-3 个 km_query.py --deep 查询
  6. 填充每章：论证要点、wiki/raw 引用、本章注意事项
  7. 缺口标注 + Gap-Driven Expansion 建议
  8. 写入 outlines/，跑自检清单
```

**自检清单**（写入前）：
- 每个核心论点有 wiki/raw 出处
- 每个冲突论点两方立场都有页面支撑
- 章节间论证线连贯（上章结论是下章前提）
- 缺口显式标注，无静默略过

## 大纲文档模板

```markdown
---
topic: <主题>
research-question: <一句话研究问题>
paper-type: empirical | theoretical
status: skeleton | filled
wiki-pages-cited: [slug, ...]
---

# 一、核心论点（Thesis）
主张一句话 + 论证链概述（A→B→C）

# 二、逻辑线总览
从张力/缺口出发 → 论证节点 → 贡献（mermaid 或缩进列表）

# 三、章节大纲
每章：
  ## N. 章节标题
  - 本章论证任务：承接上章什么、交付下章什么
  - 论证要点：3-5 条，每条标注 [wiki:claims/xxx] 或 [raw:文献]
  - 冲突论点：反方立场 + 应对策略（反驳/限定/吸收）
  - 证据状态：充分 / 薄弱（→ 建议补料方向）

# 四、全文冲突论点总表
| 冲突论点 | 反方来源 | 处理章节 | 应对策略 |

# 五、注意事项（审稿雷区逐条对照）
固化 8-10 条，生成时逐条写"本文如何应对"，不空泛复述

# 六、证据缺口清单
缺什么 → 建议检索词 → 建议补料路径
```

## 固化的规范与审稿雷区来源

提炼进 `references/pitfalls-checklist.md`（实证/理论两套侧重）：
- Matsueda, Notes on Structuring a Conventional Empirical Social Science Article
- USC Libraries, Organizing Your Social Sciences Research Paper
- Campbell & Aguilera (2022), Why I Rejected Your Paper, AMR 47(4)
- Bem (2004), Writing the Empirical Journal Article

核心条目示例：理论贡献可一句话陈述（头号拒稿原因）、文献综述须有立场的综合而非罗列、引言前段交代 gap+贡献、概念定义前后一致、方法与研究问题匹配、讨论回扣理论而非重复结果。

## 文件结构

```
skills/wiki-paper-outline/
├── SKILL.md                      # Phase 0-2 主流程 + 导师式讨论规则
└── references/
    ├── outline-template.md       # 大纲模板
    ├── pitfalls-checklist.md     # 固化规范与审稿雷区
    └── advisor-questions.md      # 导师质询问题库（按阶段分组）
```

SKILL.md 遵循生态通用范式：YAML frontmatter（name + description 触发词）→ 核心原则 → reference 路由表 → 分阶段 procedure → 自检清单 → Common Pitfalls。

## 生态接入（改动仅两处）

1. `skills/social-science-km/SKILL.md` Workflow Router 表加一行：
   用户要写论文大纲/构思论文 → 路由到 wiki-paper-outline
2. 检索统一走 `social-science-km/references/km_query.py`（`--deep` 档），
   索引 staleness 由其自带检查兜底；不新写检索脚本

## 明确不做

- state/ 文件断点续跑（两阶段流程的讨论 checkpoint 即天然断点）
- 自动补料闭环（发现缺口自动深读→补 wiki→重建索引）
- 运行时联网查规范
- 大纲写入 wiki/synthesis/（保持图谱纯净；大纲是写作中间产物）
- 学位论文章节级/综述类专用模板（当前只做期刊论文骨架，需要时再扩）
