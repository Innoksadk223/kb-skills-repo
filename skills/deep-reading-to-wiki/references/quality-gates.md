# Quality Gates

Use these gates before handing a dossier to `karpathy-wiki`.

## Gate 1: Not A Summary

Fail if the output is mainly a book report.

Required signals:

- It names skipped areas and why they were skipped.
- It separates reading map, candidate pool, deep dives, and wiki handoff.
- It includes raw anchors, not only paraphrases.
- If triggered by user-directed expansion, it records the user intent and source-discovery shortlist.

## Gate 2: Enough Richness

Quotas scale with converted source size. Read `raw_lines` from the Step 2 manifest (`_conversion_manifest.md`), write it into the dossier frontmatter, and meet the tier:

| raw_lines | 高价值区域 ≥ | 候选概念 ≥ | 候选 claims ≥ |
|---|---|---|---|
| ≤ 500 | 3 | 5 | 8 |
| 501-2000 | 5 | 8 | 14 |
| 2001-8000 | 8 | 12 | 24 |
| > 8000 | 10 | 16 | 32 |

<!-- ponytail: 分档数值是校准旋钮，与 validate_dossier.py QUOTA_TIERS 保持同步 -->

Always required regardless of tier:

- 1 reading map;
- at least two claim roles among support, objection, limitation, and bridge;
- a skipped-area list.

If the source genuinely cannot meet its tier, do NOT pad. Write a `配额豁免：` line in the self-check that names each barren region by line range and reason (e.g. `配额豁免：行 800-2400 为文献列表，行 3100-3600 为附录数据表`). A bare "来源较窄" without line ranges does not qualify. `validate_dossier.py` enforces the tier mechanically and downgrades shortfalls to warnings only when a `配额豁免：` declaration exists.

## Gate 2A: Structure-Traceable Selection

Fail if high-value choices are not traceable to the source structure, or if the dossier jumps from raw excerpts directly to wiki claims.

Required signals:

- The reading map covers every major chapter, section, or argument phase at L0.
- Each major unit has a function, selected/skipped reason, and answers: what problem it solves, what source-level thread it advances, and which wiki gap it touches.
- L1 sampling is tied to structural signals such as definitions, thesis statements, transitions, summaries, objections, limitations, or user-targeted topics.
- Every high-value area points back to a mapped unit and names its structural role.
- Every high-value candidate names a compact layered path: whole source / part or argument phase / chapter or section / candidate point.
- The candidate pool is not built from isolated passages without showing where they sit in the whole source.
- The layered path compresses structure; it does not require reading every section in full.

## Gate 3: Enough Depth

High-value candidates need context capsules. A high-value item without one must be downgraded or re-read.

Depth is not longer prose. Depth means the candidate preserves:

- source position;
- local argumentative function;
- whole-source role;
- evidence type;
- compression risk;
- relationship to existing wiki pages.

## Gate 4: Wiki-Oriented

Fail if the dossier only explains the source itself.

Fail if the handoff only lists target paths without enough material to make the wiki nodes deep and rich.

It must say what to do next:

- update existing wiki page;
- create new wiki page;
- challenge or limit an existing claim;
- ignore as duplicate or low relevance;
- verify with RAG before compilation.

For each recommended wiki target, the handoff must include:

- core contribution: what the page should add to the graph;
- nuance or boundary: what must not be flattened or overgeneralized;
- relationship/backlink suggestions: what existing pages it supports, challenges, limits, or connects;
- required raw anchors: what must be checked before compilation;
- entry condition: what evidence or context is needed before writing the formal node.

## Gate 5: Evidence Boundaries

Fail if AI inference is presented as author evidence.

Use this language:

- "作者明确主张" only when anchored in raw text.
- "可推论为" when the agent is interpreting.
- "可用于 wiki" only as a migration suggestion.
- "不能直接入库" when the raw anchor or context is weak.

For user-directed expansion, the user's inclination is never evidence. It may appear as `user_intent`, but every high-value candidate still needs raw support.

## Gate 6: Reading Discipline (mode-aware)

**Thorough mode**（书、专著、论文集、理论重文献的默认模式）:

- Fail if any window has neither window notes nor a skipped-area entry with line range — coverage must be complete: 窗口笔记覆盖区间 ∪ 放弃清单区间 ≈ 全文.
- Fail if HV selection happened before all windows were read — selection comes from the over-complete pool, not from pre-reading judgment.

**Budget mode**（快速预筛、弱相关源、用户明确要求省时）:

- Fail if the agent reads the full source by default.
- Fail if the agent treats structure coverage as permission to read every section in full.
- Allowed escalation:
  - L0 covers the source map through headings, openings/endings, summaries, and other cheap structural signals.
  - L1 samples structurally relevant units to produce candidates.
  - L2 builds context only for high-value candidates with wiki relevance and structural role.
  - L3 is used only for thesis-critical sections, major disputes, or high compression risk.

## Generic Dossier (degraded gate)

When the user allows a dossier without an identified wiki target (standalone deep reading), Gate 4 degrades:

- the handoff checklist may state 「无 wiki 目标——候选留存，待接入知识库时按交接清单编译」;
- everything else (anchors, capsules, quotas, self-check) still applies;
- raw anchors may point to the actual file path instead of `wiki/raw/` (validate_dossier.py treats non-`wiki/raw/` anchors as warnings).

## Stop Conditions

Stop and ask or report the blocker when:

- the raw source path cannot be located;
- a user-directed topic has no usable source-discovery result;
- the wiki target cannot be identified and the user has not allowed a generic dossier;
- no raw anchor supports a high-value candidate;
- the source is too malformed for reliable section mapping;
- all candidates are weak or duplicate existing wiki nodes;
- (budget mode only) a full-book read is required to answer the user but the user has not approved that token cost — in thorough mode full coverage is the contract, not a blocker.

## Final Check Before Handoff

Run the bundled validator; FAIL blocks the handoff:

```bash
python3 <本技能目录>/scripts/validate_dossier.py reading_dossiers/<档案>.md
```
