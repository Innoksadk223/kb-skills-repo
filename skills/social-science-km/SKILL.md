---
name: social-science-km
description: "Use as the coordinator for social-science knowledge bases: choose a bounded conversion, deep-reading, wiki compilation, retrieval, outline, or maintenance route, and coordinate full source-to-wiki workflows only when requested."
---

# Social Science Knowledge Management

Coordinate the layered system and hand work to the appropriate skill. The user's requested scope has priority over the full pipeline; use the cheapest route that preserves evidence quality.

The full chain is **sources → `wiki/raw/` → selected `reading_dossiers/` → formal `wiki/` → raw/wiki indexes**. Discovery is optional upstream work; paper outlining is a separate downstream output. Do not create another orchestration framework, persistent task-state layer, or `资料md/` store.

## 1. Route And Stop

Resolve explicit task scope first, then required prerequisites, then source risk. Do not expand a bounded request into full ingestion merely because the user mentions a knowledge base.

| User intent | Route | Stop point |
|---|---|---|
| Only convert PDFs/documents | [Source ingestion](references/source-ingestion.md); MinerU for PDFs, MarkItDown first for supported non-PDFs | Accepted raw outputs + coverage/failures report; no dossiers, compilation, or indexing |
| Only deep-read / produce a dossier | `deep-reading-to-wiki`, with selected raw and reading mode; standalone allowed | Accepted dossier + limitations/handoff; no formal wiki or index writes |
| Answer an existing-wiki question / find a quote | [RAG workflow](references/rag-workflow.md), mode-appropriate retrieval or permitted local reading | Evidence answer; no re-ingestion |
| Write a paper outline | `wiki-paper-outline` | Skeleton → discussion → fill, output only under `outlines/`; no automatic corpus supplementation |
| Wiki structure/health check, lint only | `karpathy-wiki` maintenance | Findings report; no automatic repairs, ingestion, or index updates |
| Index status only | RAG helper check-only maintenance | Status report; no query/API or index mutation |
| Explicit index update | RAG maintenance within authorized scope | Relevant indexes updated + report |
| Build/expand knowledge base from local sources | Conversion as needed → initialization → batch routing → source-ready dossiers/compilation → relevant index update | Requested chain completed, with partial/blocked sources disclosed |
| Search a field and build from zero | Approved academic acquisition → source folder → full chain | Requested corpus/wiki/index result and coverage report |
| Supplement a stated topic/gap | Gap-driven loop below; stop at shortlist if that is the request | Only the requested discovery or accepted evidence-backed expansion |
| Wiki is shallow after ingest | Retroactive deep reading → revise supported nodes → relevant index check/update | Targeted revision and remaining gaps |
| Retrieval is weak | Required-index freshness → ordinary retrieval → justified escalation | Answer or explicit evidence gap; do not rewrite wiki to fix ranking |

A book, collection, long chapter, theory-heavy or thesis-critical source needs the raw routing gate before formal compilation. A short, narrow, self-contained, low-risk source may qualify for direct wiki compilation; size alone never decides.

Sub-skills remain independently usable. When this coordinator dispatches them, its source routing and acceptance requirements travel in the handoff; standalone “no dossier” paths cannot waive a required dossier here.

## 2. Directory And Evidence Contract

Keep source and knowledge-base folders as siblings:

```text
<source-folder>/                      # original sources, read-only
<source-folder>（知识库）/             # project root for processed outputs
├── reading_dossiers/                 # pre-wiki interpretation, not raw/graph
├── outlines/                         # wiki-paper-outline output
├── wiki/                             # WIKI_PATH, karpathy-wiki root
│   ├── SCHEMA.md                     # structure and conventions
│   ├── index.md                      # content navigation
│   ├── log.md                        # operation log
│   ├── qa-log.md                     # karpathy-wiki question log
│   ├── raw/                          # sole bottom-layer converted text
│   │   ├── <source-folder-name>/     # preserve source-relative paths
│   │   ├── _conversion_manifest.md  # coverage and routing ledger
│   │   ├── _conversion_failures.md  # present when conversion fails
│   │   └── _主题索引.md              # concise corpus inventory
│   ├── claims/                       # theses, support, objections, limits
│   ├── concepts/
│   ├── entities/
│   ├── comparisons/
│   ├── observations/                 # evidence-backed observations
│   ├── structures/                   # structural relationships
│   ├── predicts/                     # predictions with uncertainty
│   ├── debates/                      # optional mature multi-position disputes
│   ├── queries/                      # archived query results
│   └── synthesis/                    # lightweight routes, not evidence banks
└── 检索索引/
    ├── raw/                          # raw evidence recall
    └── wiki/                         # graph-readable wiki recall
```

- Work from `<知识库>/`; set `WIKI_PATH=<知识库>/wiki/` for `karpathy-wiki`.
- Never put the knowledge base inside the source folder or scatter processed layers beside its parent. Sibling separation prevents re-ingesting outputs.
- Original sources remain unchanged. Only approved academic acquisition may add accepted new files to the source folder.
- Dossiers guide interpretation through raw anchors; they are not original evidence and belong in neither default RAG index.
- Wiki nodes and enriched-raw labels aid recall; substantive assertions and quotations require checked `wiki/raw/` evidence.
- Preserve disagreements, attribution, context risks, and uncertainty. Never replace a weak source with confident generated prose.
- `synthesis/` and optional `synthesis/_global/` are route maps linking formal nodes, not durable evidence banks.

## 3. Initialize Only What The Route Needs

For a new wiki-oriented workflow, establish project root, domain, and minimum wiki configuration **before** instructing deep reading to read wiki context. Use `karpathy-wiki` to initialize missing SCHEMA/index/log and required structures, preserving existing files. Then read `wiki/SCHEMA.md`, `wiki/index.md`, and recent `wiki/log.md`.

For an existing wiki, read its existing configuration rather than replacing it. For deep-reading-only, use standalone mode when no target wiki is needed. Conversion-only may create raw output directories without initializing the formal wiki. Query/lint against an absent wiki reports that absence rather than silently starting a build.

Check only route-specific dependencies:

| Route | Required capability |
|---|---|
| Academic discovery/acquisition | Upstream `academic-search` and the approved network boundary |
| PDF conversion / extraction fallback | Upstream `mineru-document-extractor` and usable MinerU MCP or permitted CLI |
| Supported non-PDF conversion | Upstream `markitdown` and needed local dependencies |
| Deep reading | `deep-reading-to-wiki`, usable source, selected reading mode |
| Wiki initialization/compilation/lint | `karpathy-wiki`, appropriate local project context |
| Real indexing/retrieval | `siliconflow-rag`, required index/configuration, approved API use |
| Paper outlining | `wiki-paper-outline`, its read-only source context; small-wiki local-reading exception applies |

Do not assume MinerU skill/MCP installation status. These upstream tools are not vendored; setup references are in repository [README](../../README.md) / [CONFIG](../../CONFIG.md). A missing tool/key blocks only work that depends on it.

## 4. Batch Inventory, Then Source Readiness

Load [raw-routing-gate.md](references/raw-routing-gate.md) before any formal compilation. It owns the size bands and semantic overrides; do not duplicate or weaken them.

1. Inventory **all active-batch** converted content Markdown by bytes/lines, excluding operational `_*.md` files. Account for failed conversions too.
2. Classify source types and logical collection membership; inspect group totals as well as individual files.
3. Record `raw_bytes`, `raw_lines`, `source_type`, `wiki_route`, and `route_reason` in the existing conversion manifest. Every batch content source needs a route before any batch source compiles.
4. After that common inventory, assess readiness per independent source or inseparable logical group, not by waiting for every dossier in the entire batch.

| Route/readiness | Compilation decision |
|---|---|
| `direct-wiki`, usable raw, low-risk conditions met | May compile from checked raw |
| `deep-reading`, accepted dossier and checked raw support | May compile that source/group |
| `deep-reading`, missing/failed/unverified dossier | Hold that source/group; name missing acceptance step |
| `blocked` or missing route | Hold and report conversion/routing problem |
| Inseparable source group with a required member unfinished | Hold group; do not bypass collection interpretation |

Ready independent sources may proceed while other sources remain blocked or await deep reading. This is not permission to ignore an unfinished member of a logical collection. Report completed, pending, failed, and blocked coverage explicitly; partial completion is not whole-batch success.

### Reading And Compilation Quality

Load [wiki-compilation.md](references/wiki-compilation.md) for detailed initialization, dossier acceptance, formal writing, and bulk responsibilities.

- `thorough` is the default for books, collections, theory-heavy and thesis-critical material: structure assists sequential full-window reading, then selection.
- `budget` is for rapid prescreening or explicit time savings: L0–L3 sampling/local close reading, with the deep-reading skill's short-text full-read exception.
- The selected mode applies to merged dossiers too. Preserve tiered quotas, raw-line measurements, anchors, context capsules, skipped areas, and anti-slack gates.
- A required dossier needs structural validation PASS and substantive raw-support review before compilation. PASS alone does not prove a claim; unrun validation is unverified.
- Candidates may include observations, structures, and predictions as well as claims/concepts/entities/comparisons. Include types only when evidence warrants them.
- Deep reading writes dossiers only. `karpathy-wiki` writes formal pages and navigation, then marks actually compiled dossiers with `status: compiled` and `compiled_to:`.

## 5. Shared Handoff And Write Ownership

Use this same checklist between stages in prompts/reports and existing manifest/dossier fields. Do not create another durable task-state file or schema.

| Handoff item | Required content |
|---|---|
| Project and scope | Absolute project root, WIKI_PATH when applicable, user request, current route and stop point |
| Sources and group | Exact original/raw paths, active source set, inseparable group membership, failed/pending members |
| Routing | `source_type`, `raw_bytes`, `raw_lines`, `wiki_route`, `route_reason` |
| Reading | Selected mode, research intent, wiki context or standalone, expansion discovery shortlist when used |
| Dossier and acceptance | Exact dossier path(s), structural result, raw-support review, limitations/blockers; compiled pages when applicable |
| Permissions | Exact allowed output paths, shared-file owner, prohibited writes, existing external/index authorization |
| Return | Outputs actually written, ready/blocked sources, reasons and next action; no claim of unverified success |

Parallel ownership is strict:

- Conversion workers own non-overlapping raw subtrees and per-batch reports; parent owns shared conversion ledger, failures, and topic index.
- Deep-reading workers own exact non-overlapping dossier paths only.
- Compilation workers return structured analysis only and write no files; parent owns all wiki pages, navigation, logs, and compiled dossier metadata.
- Parent coordinates index mutation after relevant writes. No concurrent shared navigation/index writes.

## 6. Gap-Driven Expansion

1. Capture user inclination as a research direction, not a conclusion.
2. Initialize missing wiki context if an authorized build/expansion needs it; then inspect SCHEMA/index/recent log and relevant graph pages.
3. Identify a thin concept, missing claim/objection, weak comparison, underused source, or absent raw evidence.
4. Use ordinary wiki-first discovery for conceptual gaps or raw-only for direct sources. Escalate recall/context only as needed under [rag-workflow.md](references/rag-workflow.md).
5. Return raw paths, relevance, keywords, likely deep-reading need, and limitations using the source-discovery template. Stop here if only a shortlist was requested.
6. If candidates remain weak/stale/insufficient, report the gap and check/broaden retrieval; use academic acquisition only within approved scope.
7. For requested expansion, route candidates, create required dossiers with `trigger: user_directed_expansion`, `user_intent`, and `source_discovery`; compile only accepted raw-backed content.
8. Check relevant indexes after wiki writes and apply authorized updates. Keep the loop intent → sources → dossier when needed → formal wiki → indexes.

## 7. Retrieval And Maintenance Contract

Load [rag-workflow.md](references/rag-workflow.md) for commands, index settings/staleness, privacy, escalation, evaluation, and required answer templates.

- Skill identifier: `siliconflow-rag`; repository script directory: `skills/SiliconFlow-rag/`; private config directories: lowercase `siliconflow-rag`. Do not migrate keys/configs.
- Prefer direct bundled `km_query.py` / `check_rebuild_rag.py` calls with `--project-root "<知识库>"`. Existing project copies remain compatible; do not automatically replace them.
- Check indexes for retrieval, index maintenance, or after relevant wiki edits, not every session mentioning a knowledge base.
- Query mode is selected before freshness gating: raw needs raw; wiki-first/deep need both. Raw enrichment dependencies remain part of raw freshness.
- Pure `--check` reports both indexes. Current indexes need no chatter; stale status names the cause and smallest required update.
- Preserve project `rag_config.json`. New/changed files mean incremental update; deleted files mean entry removal; settings/model/index-format changes may force rebuild.
- Start ordinary retrieval. Add multi-query for recall gaps, rerank for ordering/precise evidence, context for neighboring passages, deep for high-risk/final citation checks.
- Use [wiki-graph-expanded-query.md](references/wiki-graph-expanded-query.md) only when standard wiki-first is too shallow and relationships matter.
- Explicit old-index approval requires `--skip-check` on affected queries plus a freshness caveat. Never bypass stale checks by default.
- Missing required keys/indexes stop the dependent operation; permitted local reading and unrelated tasks remain available.
- Wiki lint is maintenance, not ingestion. Report lint findings before relevant index updates; non-severe wiki lint does not block urgent usable raw-only queries.

## 8. User-Facing Boundaries And Completion

Explain progress in plain Chinese and choose the evidence answer, source shortlist, or operational status template in [rag-workflow.md](references/rag-workflow.md#answering-templates). Evidence answers retain all five sections, verbatim raw quotes, separate interpretation, and explicit uncertainty.

Honor authorization already given; ask only when the following boundary is not covered:

| Boundary | Action requiring prior authorization |
|---|---|
| External privacy | Sending raw chunks, questions, wiki retrieval text, rewrite prompts, or rerank snippets to external APIs |
| Academic acquisition | Sending search queries, downloading legal full texts, adding accepted new source files |
| Index mutation | Updating, removing, or rebuilding raw/wiki index entries |
| Long conversion | Long MinerU/MarkItDown batches or token-backed extraction |
| Mass wiki change | Editing 10+ existing pages or changing SCHEMA taxonomy |
| Original material | Moving/deleting/modifying originals, normally prohibited |

Do not repeat permission requests for approved work. Never write real API keys to repository files. Do not automatically run tests/builds/evaluations without authorization; report static inspection separately from executed validation.

At each requested stop point, name outputs, coverage, blockers, and the next minimal action. Cite failure manifests when conversion fails. A missing external dependency or one failed source must not silently become a global stop for unrelated authorized work.

## Reference Map

| Load when | Reference |
|---|---|
| Acquiring/converting sources, coverage, parallel conversion | [source-ingestion.md](references/source-ingestion.md) |
| Deciding raw size/type routes | [raw-routing-gate.md](references/raw-routing-gate.md) |
| Initializing wiki, accepting dossiers, compiling, bulk ownership | [wiki-compilation.md](references/wiki-compilation.md) |
| Checking/updating/querying indexes, answering, privacy, evaluation | [rag-workflow.md](references/rag-workflow.md) |
| Escalating through wiki relationships | [wiki-graph-expanded-query.md](references/wiki-graph-expanded-query.md) |
