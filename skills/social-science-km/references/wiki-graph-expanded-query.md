# Wiki Graph-Expanded Query

Use when the user asks a conceptual question and the answer depends on how concepts relate in the wiki graph — not just keyword overlap with indexed chunks. The agent reads wiki pages to discover graph connections, generates relationship-driven sub-questions, retrieves evidence in parallel, then merges results.

## When to use

- User asks about a concept that has a rich wiki graph neighborhood
- Standard wiki-first (`--wiki-first`) returns shallow or scattered results
- The question involves cross-concept reasoning ("X 和 Y 有什么关系？", "X 在什么条件下成立？")
- User wants to understand a concept in its full context before drilling into evidence

## Procedure

### Phase 1 — Wiki Graph Exploration

1. Search existing graph-page directories for pages mentioning the concept: `wiki/claims/`, `concepts/`, `entities/`, `comparisons/`, `debates/`, `observations/`, `structures/`, and `predicts/`. Scope the search to directories that exist; exclude raw, logs, and archives.
2. Read matching pages; for each neighbor concept found, extract:
   - Wikilinks (`[[...]]`) the page links to
   - Backlinks: search `[[概念名]]` across graph pages to find pages pointing here
   - Frontmatter `relationships.supports/contradicts/derives_from/supersedes`, `follows`, and legacy claim support/oppose/limit/depend links
   - Source anchors for observations, structures and predictions; keep empirical findings distinct from frameworks and unverified implications
   - The **relationship description** — the actual sentence or proposition that explains *how* A relates to B (e.g., "孝以亲亲为大", not just "wikilink")
3. Build a **graph neighborhood table**:

| 邻居概念 | 关系描述 | 关系类型 | 来源页面 | 相关性 |
|---------|---------|---------|---------|--------|
| 亲亲 | 孝以亲亲为大，亲亲是孝的心理基础 | claim-support | wiki/claims/孝以亲亲为大.md | 高 |
| 仁 | 孝悌也者其为仁之本，孝是仁的根基 | claim-depend | wiki/claims/孝为仁之本.md | 高 |
| 爱敬 | 孝包含爱与敬两个维度 | concept-related | wiki/concepts/孝.md | 中 |

Each row must answer: **A 和 B 之间具体是什么关系？** If the wiki page doesn't explain the relationship, mark it "关系未描述" and treat it as low relevance.

### Phase 2 — Query Expansion

From the neighborhood table, generate two kinds of retrieval input:

**Sub-questions (2-4 total):** Turn high-relevance relationships into focused natural-language questions. Each sub-question targets one relationship or a cluster of closely related neighbors.

```
子问题 1: "孝与亲亲的关系是什么？亲亲如何作为孝的心理基础？"
子问题 2: "孝与仁的关系是什么？为什么说孝是仁之本？"
子问题 3: "孝的心理基础包括哪些维度？爱敬与亲亲在孝中的不同作用？"
```

**Consolidated expanded query:** Merge the original question + all sub-questions + neighbor concept names into one query string for broad recall.

```
扩展 query: "孝的心理基础 孝与亲亲的关系 亲亲作为孝的心理基础 孝与仁的关系 孝为仁之本 爱敬 亲亲 仁 道德情感 家庭关系"
```

Rules:
- Sub-questions probe specific relationships discovered in Phase 1
- The consolidated query covers broad recall; sub-questions provide precision
- If fewer than 2 high-relevance relationships exist, fall back to keyword expansion (append neighbor names to original question)

### Phase 3 — Retrieval

Use the existing `km_query.py` helper directly from its installed location with an explicit project root. It forwards project `rag_config.json` and checks the indexes needed by the selected route. Reuse a current check for unchanged inputs; do not update indexes during this read-only flow. If the user has authorized querying existing stale indexes, append `--skip-check` to every query and disclose that limitation. Missing indexes still require maintenance; `--skip-check` cannot create them.

**Step 1 — Broad recall:** Run the consolidated expanded query against raw evidence.

```bash
python3 <skills-repo>/skills/social-science-km/references/km_query.py \
  --project-root "<知识库>" \
  "<扩展 query>" --raw-only --no-lint
```

The graph expansion already supplies related wording. Add `--multi-query` only if recall remains weak or wording mismatch persists. Adjacent context is enabled by the helper by default.

**Step 2 — Precision retrieval:** Query unresolved sub-questions using the same command with `"<子问题 N>"`. Reuse sufficient evidence from Step 1. Add `--rerank --candidates 15` when ordering is inadequate or precise evidence ranking is needed. Use `--deep` only for high-risk citation checks requiring wiki-first, rewriting, ranking and context; omit `--raw-only` for that wiki-first route. Independent queries may run in parallel within the authorized service/batch scope.

**Step 3 — Merge and deduplicate:** After all necessary queries complete:

1. Collect evidence from the broad and targeted queries.
2. Deduplicate by `source_path` + `chunk_no` and record matched sub-questions. Preserve score provenance: rerank and similarity scores are different scales, so do not compare them as one number or treat rank as proof.
3. Select evidence by relevance, source diversity and checked raw context; retain source attribution for disagreements.
4. If fewer than 3 unique sources appear, report the coverage limit. Broaden only when the question needs more sources; check freshness if files changed since the previous check. Increasing rerank candidates is appropriate only when candidate truncation is the issue.

### Phase 4 — Answer

Present results using the **Evidence Answer** template in [rag-workflow.md](rag-workflow.md), with the graph expansion path traced per sub-question:

```markdown
## 图谱扩展路径
- 起始概念：（用户提到的概念）
- 图谱邻居及关系：
  - [[亲亲]]：孝以亲亲为大（来源：wiki/claims/孝以亲亲为大.md）
  - [[仁]]：孝为仁之本（来源：wiki/claims/孝为仁之本.md）
  - [[爱敬]]：孝包含爱与敬（来源：wiki/concepts/孝.md）
- 子问题：
  1. "孝与亲亲的关系是什么？" → 命中 3 个源文件
  2. "孝与仁的关系是什么？" → 命中 2 个源文件
  3. "孝的心理基础包括哪些维度？" → 命中 4 个源文件
- 合并后去重 source：X 个
```

## Guardrails

- Do not create or edit wiki pages during this flow — it's read-only RAG
- Stay within 1-2 hops of the concept; do not traverse the entire wiki graph
- Sub-questions must be traceable back to specific rows in the Phase 1 neighborhood table
- If a sub-question retrieves zero usable results, drop it rather than fabricate evidence
- Wiki page content guides retrieval, but only raw chunks count as evidence
- This is an escalation from standard wiki-first, not a replacement — use when wiki-first alone returns shallow results
