# RAG Workflow And Answer Contracts

Use the skill identifier `siliconflow-rag`; its repository directory is [SiliconFlow-rag](../../SiliconFlow-rag/SKILL.md). Commands must preserve that disk-path case. Private configuration directories remain lowercase; do not migrate user configuration.

## Dependencies, Privacy, And Scope

Before a real build/query, resolve `SILICONFLOW_API_KEY` from the environment, then `~/.hermes/private/siliconflow-rag/config.json`, then legacy `~/.codex/siliconflow-rag/config.json`, matching the scripts. If missing, stop that real API operation and request private configuration; never fabricate an index or put a real key in repository files.

Explain the relevant external boundary before its first unapproved use: raw Markdown chunks/questions go to SiliconFlow for embeddings; wiki retrieval text is sent when building the wiki index; multi-query sends questions for rewriting; rerank sends candidate snippets. Existing authorization persists. Ask for new service/privacy scope, long batches, or index mutation only when not already authorized. Local status inspection does not require an API key.

Check indexes when retrieval needs them, during index maintenance, or after relevant wiki edits. Merely mentioning a knowledge base, converting files, preparing local dossiers, or reading local wiki configuration does not require a dual-index scan.

## Preferred Helpers And Status

Prefer direct calls to bundled helpers with an explicit project root. `<skills-repo>` is the installed repository root, not the knowledge-base root; `KB_SKILLS_DIR=<skills-repo>/skills` may assist script discovery. Existing project-local helper copies remain compatible; do not automatically overwrite or delete them.

```bash
python3 <skills-repo>/skills/social-science-km/references/km_query.py \
  --project-root "<知识库>" "亲亲与仁的关系"

python3 <skills-repo>/skills/social-science-km/references/check_rebuild_rag.py \
  --project-root "<知识库>" --check
```

- Query first chooses raw/wiki mode, then enforces freshness of the indexes that mode needs. Raw-only uses raw; wiki-first/deep use both. Unrelated wiki staleness must not block an otherwise usable raw query.
- Raw freshness still includes raw content, settings, stage metadata mode, and `enriched_raw` semantic-source dependencies. Wiki changes affecting raw enrichment can legitimately make raw stale.
- Pure `km_query.py --check` checks both indexes. Prefer `check_rebuild_rag.py --check` when an update is likely; it shares check/apply logic. Its `--raw-only` / `--wiki-only` scope maintenance.
- If current, avoid unnecessary status chatter. If stale, name the index and cause. New/changed files mean “新增到索引 / 增量更新”; deleted files mean removing their entries. Reserve “重建” for settings/model/index-format changes forcing full rebuild.
- Stop stale-index retrieval unless an update is authorized or the user explicitly accepts old-index retrieval. For the latter pass `--skip-check` on **every affected query**, carry the stale caveat into the answer, and do not imply freshness. This cannot supply a missing/unusable index.
- If `<知识库>/rag_config.json` exists, helpers pass it to build/query scripts. Direct script calls must also pass `--config "<知识库>/rag_config.json"` to preserve project models and chunk/query settings.
- Compare explicit `model`, `chunk_size`, `overlap`, `dimensions`, and `encoding_format` against manifests. Mismatch requires full rebuild.

Apply an authorized update with:

```bash
python3 <skills-repo>/skills/social-science-km/references/check_rebuild_rag.py \
  --project-root "<知识库>"
```

The helper uses `SiliconFlow-rag/scripts/build_index.py --incremental` with matching paths and metadata modes. Content freshness uses SHA256, not mtime. Raw compares `wiki/raw/` with `检索索引/raw/manifest.json`; enriched raw also tracks wiki-label `semantic_source_hashes`. Wiki compares graph-readable directories with `检索索引/wiki/manifest.json`, including `observations`, `structures`, and `predicts` alongside claims/concepts/entities/comparisons/debates/synthesis/queries.

When wiki is stale, run available `karpathy-wiki` lint before updating its index, within execution authorization. Report broken links, source drift, missing claim structure, and frontmatter issues before embedding. Non-severe wiki lint findings do not block urgent raw-only queries. Missing lint tooling should be reported, not confused with a missing RAG credential.

## Initial Build And Metadata Stages

Run direct build commands from `<知识库>/`; append `--config` as above if present:

```bash
python3 <skills-repo>/skills/SiliconFlow-rag/scripts/build_index.py \
  --md-dir wiki/raw --index-dir 检索索引/raw --metadata-mode enriched_raw

python3 <skills-repo>/skills/SiliconFlow-rag/scripts/build_index.py \
  --md-dir wiki --index-dir 检索索引/wiki \
  --include-dirs claims,concepts,entities,comparisons,debates,observations,structures,predicts,synthesis,queries \
  --exclude-dirs raw,_archive --metadata-mode wiki
```

Before graph-readable pages exist, a temporary raw index with `--metadata-mode plain` is acceptable. Once any supported graph directory contains pages, require `enriched_raw` and update/rebuild the prior plain raw index as appropriate. Build wiki index when graph pages exist.

`enriched_raw` adds retrieval-only labels from formal wiki nodes to raw chunks. Quoted/cited evidence remains the original raw chunk, never the generated label. Do not index `reading_dossiers/` in either default index: dossiers guide compilation but are neither raw evidence nor the formal graph.

## Query Routing And Escalation

This section is the single authoritative definition of retrieval escalation. Other skills and references state the principle — start with ordinary retrieval, escalate only when recall, ordering or evidence risk demands it — and link here instead of restating the thresholds.

Start with ordinary retrieval; do not default every question or an outline batch to `--deep`.

| Need / observed result | Mode or escalation |
|---|---|
| 原文、出处、哪一段、引用、证据; source/quote/passage lookup | Raw-only |
| Conceptual, argumentative, comparison, cross-source, thesis questions | Wiki-first when available |
| Broad terms, vocabulary mismatch, or fewer than 3 usable raw sources | Add `--multi-query` |
| Relevant hits poorly ranked, final prose needs precise evidence order | Add `--rerank` |
| Pronouns, previous/next paragraph, table or transition context matter | Add adjacent context before changing chunk size |
| Final citation verification or high-risk thesis claims | `--deep`: wiki-first + multi-query + rerank + context, 20 candidates |
| Wiki-first remains shallow because graph relationships matter | [wiki-graph-expanded-query.md](wiki-graph-expanded-query.md) |

Graph expansion reads wiki neighbors/relationships, generates relationship-specific subquestions, retrieves in parallel, then merges/deduplicates evidence. It is an escalation, not the initial mode for every conceptual question. A small wiki may be read directly when its skill permits, with checked local raw anchors and no invented index requirement.

`km_query.py` options:

- `--raw-only`: raw evidence lookup.
- `--multi-query`, `--rerank`: selective recall/ranking upgrades under existing authorization.
- `--deep`: combined high-quality writing mode, default `candidates=20`.
- `--no-context`: disable helper's neighboring-chunk context; direct query script uses `--expand-context --context-window 1` to request it.
- `--source-discovery`: aggregate hits into candidate raw sources, including local byte/line size hints. Those hints only prompt inspection of a source; material type and context-loss risk decide the route (see [raw-routing-gate.md](raw-routing-gate.md)).
- `--skip-check`: explicitly authorized old-index use; never an automatic fallback.

Direct script alternatives, after mode-appropriate freshness checks, from project root:

```bash
python3 <skills-repo>/skills/SiliconFlow-rag/scripts/query_index.py \
  --index-dir 检索索引/raw --question "用户的问题"

python3 <skills-repo>/skills/SiliconFlow-rag/scripts/query_index.py \
  --wiki-first --wiki-index-dir 检索索引/wiki \
  --raw-index-dir 检索索引/raw --question "用户的问题"
```

For justified deep retrieval append `--multi-query --rerank --candidates 20 --expand-context --context-window 1` to wiki-first. Append project `--config` when present. Raw-only prints `# RAG Evidence`; wiki-first prints `# Wiki Hits`, `# Expanded Query`, and `# Raw Evidence`. Do not infer factual support merely from those headings.

## Lightweight Evaluation And Acceptance

Retain a small retrieval regression set when changing metadata mode, chunk size/overlap, include/exclude directories, wiki structure rules, or query routing. Run it only when tests/API use are authorized; this recommendation is not permission to execute. Ordinary new/changed raw files need freshness checks and incremental updates, not a full evaluation each time.

Start from [rag_eval_set.example.jsonl](rag_eval_set.example.jsonl); create `eval/rag_eval_set.jsonl` in the knowledge-base root with 10–20 high-value questions:

```jsonl
{"question":"孝为什么不能只基于生育事实？","mode":"wiki","expected_sources":["wiki/raw/...md"],"expected_terms":["照料","生育事实"],"notes":"核心论证召回"}
{"question":"这段关于亲亲的原文出处在哪里？","mode":"raw","expected_sources":["wiki/raw/...md"],"expected_terms":["亲亲"],"notes":"直接证据查找"}
```

Minimum pass rule: expected source appears in retrieved raw evidence and at least one expected term appears in evidence text. LLM-judge/RAGAS-style faithfulness scoring is optional for larger revisions or high-stakes writing, subject to its privacy/cost authorization.

Acceptance when applicable:

- Raw index has `manifest.json`, `chunks.jsonl`, and `embeddings.jsonl`; wiki has the same when graph pages exist.
- Raw metadata is `enriched_raw` after the graph stage; wiki metadata is `wiki`.
- Wiki-first output includes the three headings above, source paths, and snippets.
- After helper changes, the recommended local regression command is `python3 <skills-repo>/skills/social-science-km/references/km_query_self_test.py`, only when execution is authorized. Distinguish static review, skipped checks, and executed PASS; do not claim unrun tests passed.

## Answering Templates

Choose the smallest template matching intent. Evidence and interpretation remain separate; weak evidence must be reported.

### Evidence Answer

Every substantive claim must cite raw evidence. Wiki hits explain retrieval/argument paths; they never prove a claim alone.

```markdown
## 检索摘要
- 查询意图：（一句话概括用户想知道什么）
- Wiki 命中节点：（列出命中的 claim/concept/comparison/entity 或其他节点；如 raw-only 则写「未使用」）
- Raw 命中源文件：X 个（列出文件名）
- 索引状态：当前 / 过期（如过期已提醒用户）/ 未使用（直接阅读）

## Wiki 路径
- 命中的 claim / concept / comparison 等如何帮助扩展问题
- 相关的支持、反对、限定或依赖关系
- 注意：这里是召回路径，不是最终证据

## 原始证据
（每条证据一个子标题，来自不同源文件时分开展示）

### 观点／发现 A
- 来源：`wiki/raw/xxx/xxx.md`（chunk N；直接阅读时给出原文锚点）
> 原文引用

解读：（用 1-2 句话说明这段原文与问题的关系）

### 观点／发现 B
- 来源：`wiki/raw/yyy.md`（chunk N）
> 原文引用

解读：...

## 综合解读
- 只基于 Raw Evidence 回答问题
- 可以说明 Wiki Hits 帮助定位了哪些概念或论证节点
- 不把 wiki 页面当作原始证据引用

## 不确定项
- 哪些推论证据不足、需要更多查证
- 哪些概念在知识库中未覆盖
- 建议的后续检索方向
```

Rules:

- All five sections are required. Empty sections (e.g. raw-only Wiki 路径) say `（无）` rather than disappearing.
- Copy raw quotations verbatim from Raw Evidence output, or the explicitly checked raw passage in direct reading; never paraphrase inside quotation marks.
- Interpretation may use your own words but must faithfully reflect the source.
- Wiki Hits explain recall and argument structure; they cannot independently support thesis assertions.
- Uncertainties are mandatory; never fabricate coverage or evidence.

### Source-Discovery Shortlist

Use for supplementing, deepening, or rebalancing a topic when the immediate output is candidate raw sources.

```markdown
## 候选来源
| raw 路径 | 为什么可能有用 | 命中关键词 | 建议下一步 | 限制 |
|---|---|---|---|---|

## 初步缺口判断
- 薄弱概念 / 缺失 claim / 缺少反方 / 比较不足 / 原始证据不足

## 下一步
- deep-reading-to-wiki / 直接 karpathy-wiki / 继续扩大检索 / 暂停等待新来源
```

The shortlist is a routing artifact, not final evidence or permission to write wiki pages.

### Operational Status

Use for index status, conversion coverage, helper failures, API-key blockers, or batch progress.

```markdown
## 状态
- 当前结果：
- 需要用户确认的动作：
- 不会做的事：

## 证据
- 命令 / 文件 / manifest：

## 下一步
- 最小可执行动作：
```

For partial batches name completed, blocked, failed, and pending sources/groups with reasons and next actions. No confirmation needed within existing authorization should be represented as a new blocker.
