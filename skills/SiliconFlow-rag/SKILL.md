---
name: siliconflow-rag
description: Use when building, updating, inspecting, or querying local JSONL RAG indexes for social-science Markdown collections, including raw evidence retrieval, source discovery for wiki expansion, wiki-first recall from karpathy-wiki pages, and `检索索引/` maintenance.
---

# SiliconFlow RAG

Build local JSONL indexes from Markdown, query them for evidence snippets, and use raw source chunks as the citation basis.

This skill does not convert source documents and does not build the wiki. Defer conversion to `social-science-km` and its [source-ingestion rules](../social-science-km/references/source-ingestion.md): PDF uses MinerU on the core route; other formats follow the core's format-specific conversion rules. Use `karpathy-wiki` for structured wiki pages.

For user-directed wiki expansion, this skill's role is **source discovery**: return candidate `wiki/raw/` paths, why they matter, key terms, and retrieval limits. It does not create wiki nodes and does not treat wiki hits as proof.

## Load references when needed

- API payloads and privacy surface: [references/api-contract.md](references/api-contract.md)
- Retrieval modes, RRF, multi-query, rerank, evidence boundary: [references/retrieval-architecture.md](references/retrieval-architecture.md)
- Config fields, defaults, index maintenance wording: [references/config-and-maintenance.md](references/config-and-maintenance.md)
- Self-test and syntax checks: [references/testing.md](references/testing.md)
- Core query routing and maintenance: [rag-workflow.md](../social-science-km/references/rag-workflow.md)

## Safety rules

1. Confirm `SILICONFLOW_API_KEY` is available before real indexing or querying.
2. If the user wants to save the key, prefer `~/.hermes/private/siliconflow-rag/config.json` as `{"SILICONFLOW_API_KEY":"..."}`; legacy `~/.codex/siliconflow-rag/config.json` remains supported.
3. Keep private key files owner-only readable on POSIX systems, e.g. `chmod 600 ~/.hermes/private/siliconflow-rag/config.json`; scripts warn if group/other permissions are open.
4. Never put API keys in `rag_config.json`, repo files, skill files, logs, manifests, or examples.
5. Explain the network surface when relevant: indexing sends chunks to embeddings; querying sends the question to embeddings; `--multi-query` sends the question to chat completions; `--rerank` sends candidate snippets to rerank.
6. Continue within existing task authorization without asking again. New external-service scope or long batches must respect the user's authorization boundaries.

Use `python3` in examples because macOS and many Linux systems no longer provide `python`. If a specific machine only exposes `python`, use that interpreter instead; the scripts are Python 3 scripts (`#!/usr/bin/env python3`).

## Common workflow

The skill identifier is `siliconflow-rag`; the repository's script directory is `SiliconFlow-rag` (case-sensitive). Private configuration directories remain lowercase; do not migrate them.

Replace `<skills-repo>` and `<project-root>` with absolute paths. Run the commands below from the knowledge-base project root so relative corpus, index, and configuration paths resolve there:

```bash
cd "<project-root>"
```

### Build or update raw index

```bash
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/build_index.py" \
  --md-dir wiki/raw \
  --index-dir 检索索引/raw \
  --metadata-mode enriched_raw \
  --incremental
```

`--incremental` re-embeds only new/changed files (falls back to a full rebuild automatically when index settings changed). Omit it only for the very first build or a deliberate full rebuild — without it every run re-embeds the whole corpus at full API cost.

Use `enriched_raw` once graph-readable wiki pages exist; use `plain` only for the initial Raw-only stage. Structural precondition for `enriched_raw`: `--md-dir` must be a directory literally named `raw` whose parent contains the wiki page folders (claims/concepts/...); otherwise the build warns and produces a plain-equivalent index. Enriched Raw manifests track both Raw file hashes and the wiki semantic-label dependencies that shaped embedding text.

### Build or update wiki index

Use when `karpathy-wiki` pages exist and the question is conceptual, argumentative, cross-source, or thesis-writing oriented.

```bash
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/build_index.py" \
  --md-dir wiki \
  --index-dir 检索索引/wiki \
  --include-dirs claims,concepts,entities,comparisons,debates,observations,structures,predicts,synthesis,queries \
  --exclude-dirs raw,_archive \
  --metadata-mode wiki \
  --incremental
```

### Query through the core helper

Prefer the maintained helper with an explicit project root. Existing project copies remain compatible; do not overwrite or delete them automatically.

```bash
python3 "<skills-repo>/skills/social-science-km/references/km_query.py" \
  --project-root "<project-root>" "用户的问题"
```

Actual queries select raw/wiki mode before deciding whether stale indexes block execution. Raw mode requires a current raw index, including configuration and `enriched_raw` semantic dependencies; an unrelated stale wiki index does not block it. Wiki-first requires both indexes to be current. Pure `--check` checks both indexes, even with `--raw-only` or `--skip-check`.

```bash
python3 "<skills-repo>/skills/social-science-km/references/km_query.py" \
  --project-root "<project-root>" --check
```

When continuing with old indexes is authorized, explicitly add `--skip-check` to the query and disclose the freshness limitation. Direct `query_index.py` calls below do not perform the helper's freshness gate; check the required indexes before using them.

### Query raw-only mode

```bash
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/query_index.py" \
  --index-dir 检索索引/raw \
  --question "用户的问题"
```

### Query wiki-first mode

```bash
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/query_index.py" \
  --wiki-first \
  --wiki-index-dir 检索索引/wiki \
  --raw-index-dir 检索索引/raw \
  --question "用户的问题"
```

### Source discovery for wiki expansion

Use when the user names a direction they want to deepen, such as "补充儿童教育", and the next step is to find which raw files deserve `deep-reading-to-wiki`.

Start from ordinary wiki-first retrieval if the direction is conceptual or argumentative:

```bash
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/query_index.py" \
  --wiki-first \
  --wiki-index-dir 检索索引/wiki \
  --raw-index-dir 检索索引/raw \
  --question "哪些原始资料可以补充儿童教育在孝、亲亲、修身中的作用？" \
  --source-discovery
```

Then broaden with raw-only when source wording may differ from the wiki wording. Add multi-query when recall is insufficient or wording mismatch is likely:

```bash
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/query_index.py" \
  --index-dir 检索索引/raw \
  --question "儿童教育 家庭教育 爱敬 积浸 身教 保傅 内则 小学" \
  --source-discovery \
  --multi-query \
  --expand-context \
  --context-window 1
```

Return a shortlist, not a final wiki answer:

| Field | Meaning |
|---|---|
| source path | Candidate `wiki/raw/...md` file. |
| why relevant | Which user intent or wiki gap it may address. |
| key terms | Terms that made the source retrievable. |
| Raw size | Converted line/byte count when the source file is locally available. |
| size gate | Size-only `deep-reading` candidate, inspect band, `direct-wiki` candidate, or blocked. |
| next step | Apply `social-science-km` source-type/context-risk overrides, then use `deep-reading-to-wiki`, direct `karpathy-wiki`, or ignore weak evidence. |
| limits | Missing context, weak hit, stale index, or needs broader query. |

If fewer than three usable raw sources appear, report that limitation and broaden the query or check index freshness before sending anything to deep reading.

`--source-discovery` aggregates multiple retrieved chunks from the same file into one candidate source. Its size gate is not a final routing decision: books, theses, collections, theory-heavy sources, and thesis-critical texts still require the semantic overrides in `social-science-km`.

### Optional query modes

Default to ordinary retrieval. Escalate to rerank when candidate ordering is inadequate or the task needs precise, high-stakes evidence selection, including critical thesis claims. The user need not name a flag or use special wording; choose based on evidence quality requirements within existing authorization.

```bash
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/query_index.py" \
  --wiki-first \
  --wiki-index-dir 检索索引/wiki \
  --raw-index-dir 检索索引/raw \
  --question "用户的问题" \
  --rerank
```

Use multi-query only when recall is weak or wording mismatch is likely:

```bash
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/query_index.py" \
  --index-dir 检索索引/raw \
  --question "用户的问题" \
  --multi-query
```

The core helper's `--deep` combines multi-query, rerank, and context (wiki-first when a wiki manifest exists, unless `--raw-only` is set). Reserve it for evidence tasks that need this combined escalation; do not apply it to every initial retrieval or every outline query.

Add adjacent chunks when the answer needs local context:

```bash
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/query_index.py" \
  --index-dir 检索索引/raw \
  --question "用户的问题" \
  --expand-context \
  --context-window 1
```

### Inspect index health

Use the helper's `--check` above for freshness. Inspect index statistics with:

```bash
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/query_index.py" --index-dir 检索索引/raw --stats
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/query_index.py" --index-dir 检索索引/wiki --stats
```

## Answering rules

- Treat script output as evidence, not as the final answer.
- In wiki-first mode, use `# Wiki Hits` to understand the conceptual/argument path and `# Raw Evidence` for citable evidence.
- In source-discovery mode, answer with candidate raw files first; do not synthesize final claims before `deep-reading-to-wiki` or `karpathy-wiki`.
- Cite source paths shown by the script.
- Do not claim a paper says something unless raw evidence supports it.
- If retrieval returns weak or empty evidence, say so and suggest updating the relevant index or broadening the question.
- Reranking is optional. If reranking fails, continue with local similarity results and mention the fallback.

## Common pitfalls

- Indexing only `wiki/raw/` when the user asks conceptual or argumentative questions. Build the wiki index too.
- Mixing raw and wiki into one index too early. Prefer two indexes so wiki explains and raw proves.
- Treating wiki hits as proof. Wiki pages guide recall; raw snippets provide evidence.
- Sending a user's topic directly to wiki writing before locating raw sources.
- Forgetting `--exclude-dirs raw,_archive` when building the wiki index.
- Treating Raw file hashes as the only dependency of `enriched_raw`. Wiki labels also shape enriched embedding text; keep `semantic_source_hashes` and `semantic_hint_hashes` in the manifest and refresh affected Raw chunks when those labels change.
- Returning six chunks from one file as six "candidate sources". Use `--source-discovery` to aggregate by source before selecting deep-reading inputs.
- Relying on rerank for recall. Rerank only reorders candidates; retrieval and wiki expansion decide what enters the candidate pool.
