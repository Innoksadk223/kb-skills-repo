# Wiki Graph-Expanded Query

Use when the user asks a conceptual question and the answer depends on how concepts relate in the wiki graph — not just keyword overlap with indexed chunks. The agent reads wiki pages to discover graph connections, generates relationship-driven sub-questions, retrieves evidence in parallel, then merges results.

## When to use

- User asks about a concept that has a rich wiki graph neighborhood
- Standard wiki-first (`--wiki-first`) returns shallow or scattered results
- The question involves cross-concept reasoning ("X 和 Y 有什么关系？", "X 在什么条件下成立？")
- User wants to understand a concept in its full context before drilling into evidence

## Procedure

### Phase 1 — Wiki Graph Exploration

1. Search wiki for pages mentioning the concept:
   ```bash
   grep -rl "概念名" wiki/claims/ wiki/concepts/ wiki/entities/ wiki/comparisons/
   ```
2. Read matching pages; for each neighbor concept found, extract:
   - Wikilinks (`[[...]]`) the page links to
   - Backlinks: search `[[概念名]]` across wiki to find pages pointing here
   - Claim relations from frontmatter: support/oppose/limit/depend links
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

Three-step retrieval using the existing `query_index.py`:

**Step 1 — Broad recall:** Run the consolidated expanded query to cast a wide net.

```bash
python skills/SiliconFlow-rag/scripts/query_index.py \
  --index-dir 检索索引/raw \
  --question "<扩展 query>" \
  --multi-query \
  --expand-context \
  --context-window 1 \
  --top-k 20
```

**Step 2 — Precision retrieval:** For each sub-question, run a targeted query with rerank to surface the most relevant evidence for that specific relationship.

```bash
python skills/SiliconFlow-rag/scripts/query_index.py \
  --index-dir 检索索引/raw \
  --question "<子问题 N>" \
  --rerank \
  --candidates 15 \
  --expand-context \
  --context-window 1
```

**Step 3 — Merge and deduplicate:** After all queries complete:

1. Collect all evidence items from Step 1 and each Step 2 run
2. Deduplicate by `source_path` + `chunk_no`: keep the item with the highest `rerank_score` (or `similarity` if no rerank), and record which sub-questions it matched
3. Sort merged results: reranked items first, then by similarity descending
4. If fewer than 3 unique sources appear, escalate: check index freshness (`check_rebuild_rag.py --check`), broaden sub-questions, or increase `--candidates`

### Phase 4 — Answer

Present results using the **Evidence Answer** template from the parent skill, with the graph expansion path traced per sub-question:

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
