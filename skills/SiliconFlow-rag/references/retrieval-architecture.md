# Retrieval Architecture

Use two retrieval modes. Wiki pages guide recall; raw chunks provide evidence.

## Raw-only retrieval

Use when the user wants direct evidence from source materials.

```text
question → embedding → vector + BM25 → RRF → optional rerank → evidence
```

## Wiki-first retrieval

Use when a `karpathy-wiki` structure exists and the user asks conceptual, argumentative, cross-source, or thesis-writing questions.

```text
question
→ retrieve wiki index
→ extract titles/frontmatter/wikilinks/claim relations
→ build expanded query locally
→ retrieve raw index
→ optional rerank raw candidates
→ output Wiki Hits + Expanded Query + Raw Evidence
```

Recommended layout:

```text
检索索引/wiki    # claims/concepts/entities/comparisons/debates/observations/structures/predicts/synthesis/queries
检索索引/raw     # wiki/raw original evidence
```

## RAG norm

- **Dual retrieval**: vector similarity + lightweight BM25 lexical search.
- **RRF**: vector and BM25 ranks are fused with `1/(k+rank)`.
- **Multi-query**: optional; disabled by default; calls chat completions to generate 3 additional queries.
- **Rerank**: optional; it only reorders candidates. Start with ordinary retrieval and escalate only when recall, ordering or evidence risk demands it — which upgrade to add, and when, is defined once in the [rag-workflow.md escalation table](../../social-science-km/references/rag-workflow.md#query-routing-and-escalation). The user need not name a flag or use special wording.

## Evidence boundary

- Wiki hits are recall guides, not proof.
- Raw evidence is the citation basis.
- Do not claim a paper says something unless raw evidence supports it.

## Source-discovery mode

```text
question → optional wiki expansion → retrieve Raw candidates
→ aggregate chunks by source_path → attach local Raw line/byte counts
→ shortlist for social-science-km material-type routing
```

Source aggregation prevents one long document from occupying every shortlist row. The emitted size band is advisory — it only prompts inspection of a source; material type and context-loss risk decide whether `deep-reading-to-wiki` is required ([raw-routing-gate.md](../../social-science-km/references/raw-routing-gate.md)).
