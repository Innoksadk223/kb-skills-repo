---
name: wiki-paper-outline
description: Use when a knowledge-base wiki already exists and the user wants to plan, outline, or structure a social-science paper from it — e.g. "帮我做论文大纲", "构思一篇关于X的论文", "基于知识库规划论文结构", paper outline, thesis planning, 论文选题讨论.
---

# Wiki Paper Outline

基于已建成的 wiki 关系网 + RAG 检索，通过**学生-导师式讨论**生成社科论文大纲。你扮演导师：不是替学生一次性写完大纲，而是检索→提出骨架→质询讨论→收敛→填充。

## 核心原则

1. **禁止一次性生成完整大纲。** 必须先产出骨架草稿并与用户讨论至少一轮，用户确认方向后才能填充章节。跳过讨论直接交付完整大纲 = 违反本技能。
2. **只读消费。** 读 `wiki/` 和 `检索索引/`，写 `outlines/`。不写 wiki 页、不建/改索引、不做网络搜集。RAG 查询会向已配置的 SiliconFlow 服务发送查询文本，启用改写或精排时还会发送相应文本；沿用已授权的服务范围，不能把“只读”说成“离线”。
3. **检索优先于通读。** 除非 wiki 页面总数 < 15，否则必须通过 `km_query.py` 检索定位相关页面，而不是通读整个 wiki。
4. **缺口标注，不自动补料。** 证据薄弱处显式标注并建议走 social-science-km 的 Gap-Driven Expansion，不自行触发深读或索引重建。
5. **每个论证要点必须有出处标注**（`[wiki:claims/xxx]` 或 `[raw:文件]`），无出处的要点标 `[无证据支撑——需讨论或补料]`。

## Reference 路由

| 时机 | 加载 |
|---|---|
| Phase 1 出骨架草稿、Phase 2 写最终大纲 | [references/outline-template.md](references/outline-template.md) |
| Phase 1/2 讨论环节选质询问题 | [references/advisor-questions.md](references/advisor-questions.md) |
| Phase 2 写"注意事项"节 | [references/pitfalls-checklist.md](references/pitfalls-checklist.md) |

## Phase 0：需求对齐

1. 从用户输入提取：主题、研究问题（若无则待 Phase 1 讨论确定）、paper-type（empirical/theoretical，不明则问）。已有明确方向直接沿用。
2. 确定 `<知识库>` 与技能安装位置。页面数只统计正式图谱页面，不计 raw、配置、日志或归档。小 wiki（< 15 页）允许直接通读正式页面，并按关键主张读取其 raw 出处；此例外贯穿 Phase 1/2，无需索引检查或 RAG 查询，向用户说明即可。
3. 使用 RAG 时，从技能原位置执行 `python3 <skills-repo>/skills/social-science-km/references/km_query.py --project-root "<知识库>" --check --no-lint`。不复制 helper；已有项目副本仍可使用。索引过期 → 建议通过 social-science-km 索引维护流程更新；用户允许带旧索引继续时，记录 `index-stale: true`，后续每条查询追加 `--skip-check`。必要索引不存在且 wiki 页面 ≥ 15 → 报告阻塞并交回核心，不把跳过检查当成缺失索引的替代办法。

以下查询命令均使用该 helper 完整路径及 `--project-root "<知识库>"`。默认追加 `--no-lint`，避免大纲检索顺带触发结构检查；它不绕过索引新旧检查。仅小 Wiki 直接阅读路径跳过各阶段检索，讨论、出处与缺口要求仍适用。

## Phase 1：骨架阶段

1. **图谱勘探**：按主题词搜索实际存在的 `wiki/claims/ concepts/ debates/ comparisons/ entities/ observations/ structures/ predicts/` 相关页 → 读页面 → 构建图谱邻域表（复用 [图谱查询 Phase 1](../social-science-km/references/wiki-graph-expanded-query.md) 的表格式）。重点提取 `relationships.supports / contradicts / derives_from / supersedes`、`follows` 及已有 claim 的支持/反对/限定关系。`contradicts` 与 `debates/` 页提供冲突线索；观察、框架和预测页分别提供经验、分析结构与待检验推论，须沿各页原文出处核查，不能把预测当发现。
2. **初轮检索**：由邻域表生成 2-4 个关系驱动子问题，先逐个执行 `python3 <skills-repo>/skills/social-science-km/references/km_query.py --project-root "<知识库>" "<子问题>" --no-lint`。小 Wiki 直接阅读时跳过。召回不足或措辞差异明显时加 `--multi-query`；候选排序不足时加 `--rerank`；高风险核心论据核查才用 `--deep`。已获准使用旧索引时，每条查询加 `--skip-check`。
3. **产出骨架草稿**（用 outline-template.md 的骨架档结构，status: skeleton）：
   - thesis 候选 1-2 个（每个附一句论证链 A→B→C 和主要风险）
   - 章节树：每章仅一行论证任务
   - 冲突论点清单：来自 debates/ + contradicts 关系，注明两方立场页面
   - 证据缺口初判
4. **导师式讨论（强制 checkpoint）**：骨架附带 2-4 个质询问题（从 advisor-questions.md 选贴合的，或自拟同等锐度的），**一次只问一个**（用 AskUserQuestion 或对话）。必问维度：
   - thesis 选择与聚焦度（两个候选选哪个？范围要不要收窄？）
   - 冲突论点应对策略（正面反驳 / 限定范围 / 吸收进论证？）
   讨论持续到用户明确认可骨架方向为止。用户每轮反馈后更新骨架再问下一个问题。

## Phase 2：填充阶段

用户确认骨架后：

1. 逐章复用已检索证据，只对尚未解决的关系或出处执行 1-3 个定向查询；命令路径、项目根、旧索引参数及升级规则沿用 Phase 1。高风险核心论据才加 `--deep`。小 Wiki 已通读时跳过查询，读取页面所指的关键 raw 段落。
2. 按 outline-template.md 完整结构（status: filled）填充：每章论证任务（承接/交付）、论证要点（3-5 条带出处）、本章冲突论点与应对策略、证据状态。
3. "注意事项"节：逐条对照 pitfalls-checklist.md，写"本文如何应对"，禁止空泛复述雷区本身。
4. 缺口清单：缺什么 → 建议检索词 → 建议补料路径（Gap-Driven Expansion / 深读 / 新采集）。
5. 写入 `<知识库>/outlines/YYYY-MM-DD-<主题>.md`。

## 写入前自检清单

- [ ] frontmatter 五字段齐全（topic / research-question / paper-type / status / wiki-pages-cited）
- [ ] 每个核心论点有 wiki/raw 出处
- [ ] 每个冲突论点两方立场都有页面支撑（单方缺失 → 进缺口清单）
- [ ] 章节论证线连贯：每章"承接"与上一章"交付"对得上
- [ ] 缺口全部显式标注，无静默略过
- [ ] 注意事项逐条有"本文如何应对"，非复述
- [ ] 经历过至少一轮骨架讨论（status 曾为 skeleton）

## Common Pitfalls

| 错误 | 纠正 |
|---|---|
| 一次性交付完整大纲，"用户可以事后改" | 违反核心原则 1。删掉，回到骨架 + 讨论 |
| 骨架讨论只走过场（"这样可以吗？"） | 质询必须是实质选择题：thesis 二选一、冲突应对三选一 |
| 通读全 wiki 代替检索 | 仅 < 15 页允许；否则用 km_query.py，并说明检索路径 |
| 把 wiki 页当最终证据引用 | wiki 页是论证路径；关键主张尽量落到 raw 出处，落不到就标缺口 |
| 发现缺口后自己去补 wiki/建索引 | 只标注 + 建议，路由回 social-science-km |
| 注意事项抄 checklist 原文 | 每条必须写本文的具体应对 |
