---
name: social-science-km
description: Use as the coordinator for social-science knowledge bases: choose a bounded source sync, deep-reading, wiki compilation, retrieval, outline, maintenance, or paper-writing evidence-support route, and coordinate full source-to-wiki workflows only when requested.
---

# Social Science Knowledge Management

Coordinate the layered knowledge-management system and hand work to the appropriate skill. The user's requested scope has priority over the full pipeline; use the cheapest route that preserves evidence quality.

## Skill Architecture: Official Base vs 4 Self-Developed Skills

Do not reinvent atomic WeKnora CRUD. Distinguish generic WeKnora skills from this repository's 4 social-science skills — each self-developed skill works **standalone** OR **orchestrated by `social-science-km`**:

| Layer | Skill | Owner | Role & Standalone / Orchestrated Use |
|---|---|---|---|
| **Official Base** (optional) | `@lyingbug/weknora` (Claw Skill) or `weknora-shared` + `weknora-rag-search` (CLI skills) or built-in WeKnora MCP | **WeKnora Official** | Generic single-KB CRUD, ad-hoc file/URL upload, generic search outside a structured social-science project. |
| **Coordinator & Dual-KB Bridge** | `social-science-km` | **This Repo** | End-to-end routing, source routing gate, `scripts/sync_kb.py`, two-hop `scripts/km_query.py`, freshness `scripts/check_rebuild_rag.py`, and one-click onboarding `scripts/doctor.py`. |
| **Deep Reading** | `deep-reading-to-wiki` | **This Repo** | Segmented/sampled close reading into `reading_dossiers/*.md`. **Standalone** on any PDF/doc, or dispatched by KM for books/classics/collections. |
| **Graph Wiki** | `karpathy-wiki` | **This Repo** | Local 8-type Obsidian graph (`claims`, `concepts`, `entities`, `comparisons`, `debates`, `observations`, `structures`, `predicts`) + `lint.py`. **Standalone** or dispatched by KM. |
| **Paper Outlining** | `wiki-paper-outline` | **This Repo** | Advisor-style thesis skeleton → interrogation → filled outline under `outlines/`. **Standalone** on an existing Wiki or downstream of KM. |

## Choosing `wiki_mode` (`local_karpathy` vs `weknora_native`)

New projects **do not generate a local `wiki/raw/*.md` conversion layer**: original files (`PDF`, `DOCX`, `EPUB`, `MD`, `TXT`, images) stay read-only in `<source-folder>/` and upload directly to WeKnora `<project>-raw` (server-side parsing: per-KB `parser_engine_rules`, default built-in `docreader`; route `pdf` to `mineru_cloud` for scans, since a configured MinerU key alone does not change routing; PDF page locators `p.X` preserved). Existing legacy projects that already have `wiki/raw/*.md` remain untouched and compatible.

Confirm or respect `<知识库>/weknora_config.json` `"wiki_mode"`:

| `wiki_mode` | Pipeline | Visible in WeKnora Web UI (`http://localhost`) | Best For |
|---|---|---|---|
| `local_karpathy`（默认） | `<source-folder>/` → `<project>-raw` → routing gate → `reading_dossiers/` (as needed) → local `karpathy-wiki` (citing `<file>.pdf#p.X`) → `<project>-wiki` KB | Knowledge-base list shows **`<project>-raw`** (original docs) alongside **`<project>-wiki`** (all `claims/`, `concepts/`, `debates/` cards & chunks); local Obsidian renders graph edges | **社科论文写作、典籍/专著精读、学派争鸣梳理、导师式大纲讨论** |
| `weknora_native`（可选） | `<source-folder>/` → `<project>-raw` single KB with `wiki_enabled=true` & `auto_generate=true` (skips local dossiers & `karpathy-wiki`) | Inside **`<project>-raw` → Wiki / 图谱页签**, browse auto-generated `entity/concept/summary` tree, cluster graph, and revision history | **日常文献速览、研究初期摸底、零手工维护卡片** |

## 1. Route And Stop

Resolve explicit task scope first, then required prerequisites, then source risk. Do not expand a bounded request into full ingestion merely because the user mentions a knowledge base.

| User intent | Route | Stop point |
|---|---|---|
| Check environment / new user setup | Run `scripts/doctor.py` | 5-point readiness report + copyable fix steps |
| Only ingest/parse documents into WeKnora | [Source ingestion](references/source-ingestion.md) (`scripts/sync_kb.py --source-dir`) | Synced `<project>-raw` + `_source_manifest.md`; no dossiers or local wiki compilation |
| Only deep-read / produce a dossier | `deep-reading-to-wiki` (reads original PDF/doc directly via multimodal/chunks; standalone allowed) | Accepted dossier citing `<source>#p.X` + limitations/handoff; no formal wiki writes |
| Answer an existing-wiki question / find a quote | [RAG workflow](references/rag-workflow.md) (`scripts/km_query.py`) or permitted small-wiki local read | Evidence answer citing original file + page/chunk; no re-ingestion |
| Write a paper outline | `wiki-paper-outline` (best with `local_karpathy`; if `weknora_native`, warn and offer switching or summary+raw fallback) | Skeleton → discussion → fill under `outlines/`; no automatic corpus supplementation |
| Write, revise, or adjust a paper draft | `scripts/km_query.py` supplies evidence & revision notes (+ `wiki-paper-outline` if structure wanted); prose drafting goes to user's writer | Evidence and revision notes handed off; this repo writes no paper prose |
| Wiki structure/health check, lint only | `karpathy-wiki` maintenance (`lint.py`) | Findings report; no automatic repairs, ingestion, or index updates |
| Index status only | `scripts/check_rebuild_rag.py --check` | Status report; no query/API or index mutation |
| Explicit index update | `scripts/check_rebuild_rag.py` within authorized scope | Relevant KBs updated + report |
| Build/expand knowledge base from local sources | Sync `<source-folder>/` to `<project>-raw` → choose `wiki_mode`: (`local_karpathy`: routing gate → dossiers/compilation → sync `<project>-wiki`) OR (`weknora_native`: auto-wiki ON) | Requested chain completed, with partial/blocked sources disclosed |
| Supplement a stated topic/gap | Gap-driven loop below; stop at shortlist if that is the request | Requested discovery shortlist or accepted evidence-backed expansion |
| Wiki is shallow after ingest | Retroactive deep reading on original source → revise supported nodes → sync `<project>-wiki` | Targeted revision and remaining gaps |
| Retrieval is weak | Required-index freshness → ordinary retrieval → justified escalation | Answer or explicit evidence gap; do not rewrite wiki to fix ranking |

A 典籍／原典／注疏、专著、教材／导论／手册章节、论文集／合集、学位论文 source — or any coherent multi-file group read as one unit — needs the routing gate before formal compilation in `local_karpathy` mode, whatever its length; so does any source carrying a semantic override (thesis-critical, theory-heavy, argument-rich, conceptually disputed, or likely to lose support/objection/limitation context). A narrow, self-contained, low-risk single paper outside those categories may compile directly to wiki ([raw-routing-gate.md](references/raw-routing-gate.md)).

## 2. Directory And Evidence Contract

Keep source and knowledge-base folders as siblings:

```text
<source-folder>/                      # original sources (PDF/DOCX/EPUB/MD/TXT), read-only
<source-folder>（知识库）/             # project root for processed outputs
├── weknora_config.json               # optional: wiki_mode, source_dir, chunk/query settings
├── reading_dossiers/                 # pre-wiki close reading (local_karpathy), not indexed
├── outlines/                         # wiki-paper-outline output
├── wiki/                             # WIKI_PATH, karpathy-wiki root (local_karpathy)
│   ├── SCHEMA.md                     # structure and conventions
│   ├── index.md                      # content navigation
│   ├── log.md                        # operation log
│   ├── qa-log.md                     # question log
│   ├── claims/                       # theses, support, objections, limits (cite <source>#p.X)
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
    ├── _source_manifest.md           # source inventory & routing ledger (new projects)
    ├── raw/manifest.json             # <project>-raw KB ledger (SHA256 ↔ knowledge_id)
    └── wiki/manifest.json            # <project>-wiki KB ledger (local_karpathy mode)
```

- **Legacy compatibility**: Existing knowledge bases that already contain `wiki/raw/*.md` and `wiki/raw/_conversion_manifest.md` keep working as-is; never delete or migrate existing `wiki/raw/` unless explicitly requested.
- Work from `<知识库>/`; set `WIKI_PATH=<知识库>/wiki/` for `karpathy-wiki`.
- Never put the knowledge base inside `<source-folder>/`. Original sources remain read-only.
- Every formal Wiki page in `local_karpathy` mode **must declare its provenance** (`sources:` in frontmatter + file path and page/section in body, e.g. `02-学术研究/肖群忠.pdf#p.12`).
- Wiki hits (local cards or `weknora_native` pages) explain conceptual/argument paths; substantive assertions and quotations require checked source evidence from `<project>-raw` (or direct inspection of the cited original PDF/file).

## 3. Initialize Only What The Route Needs

For a new `local_karpathy` workflow, establish project root, domain, and minimum wiki configuration (`SCHEMA.md`, `index.md`, `log.md`) via `karpathy-wiki` **before** wiki-oriented deep reading. For an existing wiki, read its configuration rather than replacing it. For `weknora_native`, local `wiki/` initialization is unnecessary. Standalone `deep-reading-to-wiki` needs no target wiki.

Check only route-specific dependencies (`scripts/doctor.py` verifies all at once):

| Route | Required capability |
|---|---|
| Document parsing & RAG indexing/query | Running WeKnora server (`http://localhost:8080`), API Key, configured Embedding model (parsing is per-KB `parser_engine_rules`; default `docreader`, route `pdf` to `mineru_cloud`/`mineru` for scans — **no local conversion skills required**) |
| `weknora_native` automated Wiki | Same WeKnora server + a configured generation (`KnowledgeQA`) model |
| Deep reading | `deep-reading-to-wiki`, readable original PDF/source (multimodal read or WeKnora chunks) |
| Local Wiki compilation / lint | `karpathy-wiki` |
| Paper outlining | `wiki-paper-outline`, read-only wiki/RAG context |

## 4. Batch Inventory, Then Source Readiness (`local_karpathy`)

Load [raw-routing-gate.md](references/raw-routing-gate.md) before formal compilation:

1. Inventory all active-batch source files in `<source-folder>/` (or legacy `wiki/raw/`).
2. Classify source types and logical collection membership; record `source_bytes`, `source_type`, `wiki_route` (`deep-reading` | `direct-wiki` | `blocked`), and `route_reason` in `检索索引/_source_manifest.md` (or existing `_conversion_manifest.md`).
3. Assess readiness per independent source or inseparable logical group:
   - `direct-wiki` + usable source → compile from checked original source;
   - `deep-reading` + accepted dossier (`validate_dossier.py` PASS + source-anchor check) → compile;
   - missing/failed dossier or unfinished inseparable collection member → hold and report explicitly.

Load [wiki-compilation.md](references/wiki-compilation.md) for reading modes (`thorough` default for books/classics/collections; `budget` for prescreening), dossier acceptance, and compilation ownership.

## 5. Shared Handoff And Write Ownership

Carry project root, `WIKI_PATH`, requested scope/stop point, exact source paths + group membership, routing fields, reading mode, dossier path/validation status, and allowed output paths in stage handoffs. Do not invent another persistent task-state file.

- Deep-reading workers write only their assigned non-overlapping `reading_dossiers/*.md` path.
- Compilation workers return structured analysis only and write no files; parent writes all `wiki/` pages, `index.md`, `log.md`, and `compiled_to:` metadata.
- Parent runs `scripts/check_rebuild_rag.py` after wiki writes to sync `<project>-wiki` (visible in WeKnora Web UI).

## 6. Gap-Driven Expansion

1. Treat user inclination as a research direction, not a predetermined conclusion.
2. Inspect `wiki/index.md` and relevant graph pages (in `local_karpathy`) to locate thin concepts, missing objections, or weak evidence.
3. Run `scripts/km_query.py --source-discovery` to shortlist candidate files already in `<project>-raw`. Stop here if only a shortlist was requested.
4. If corpus sources cannot fill the gap, report the exact missing topic/literature so the user can add sources to `<source-folder>/`.
5. For authorized expansion on existing sources, apply the routing gate → required dossiers (`trigger: user_directed_expansion`) → `karpathy-wiki` compilation → `scripts/check_rebuild_rag.py`.

## 7. Retrieval And Maintenance Contract

Load [rag-workflow.md](references/rag-workflow.md) for commands, freshness rules, escalation, and answer templates.

- Bundled scripts live in `skills/social-science-km/scripts/` (`km_query.py`, `check_rebuild_rag.py`, `sync_kb.py`, `query_kb.py`, `doctor.py`). Credentials live in `~/.hermes/private/weknora-rag/config.json` or `WEKNORA_HOST` + `WEKNORA_API_KEY`.
- **Pure retrieval in Agent chat**: WeKnora returns ranked chunks (with PDF page locators `p.X` and optional server-side `Rerank`); the current Agent synthesizes the answer. No chat LLM is required inside WeKnora for `local_karpathy` retrieval.
- Answer only from executed evidence (`km_query.py` output or permitted small-wiki + original-source inspection). Never answer from memory or skill docs.
- Query mode precedes freshness gating: `raw-only` needs `raw`; `local_karpathy` `wiki-first` needs both `raw` and `wiki`; `weknora_native` `wiki-first` needs `raw`.

## 8. User-Facing Boundaries And Completion

Explain progress in plain Chinese using the templates in [rag-workflow.md](references/rag-workflow.md#answering-templates). Supply evidence and revision notes for paper drafting without claiming prose was rewritten.

Ask prior authorization only when not already covered for: sending private documents/queries to external model APIs, mutating WeKnora indexes, editing 10+ existing wiki pages, or modifying original files (normally prohibited). Never write API keys into repository files.

## Reference Map

| Load when | Reference |
|---|---|
| Syncing original PDFs/docs into WeKnora `<project>-raw` | [source-ingestion.md](references/source-ingestion.md) |
| Deciding `deep-reading` vs `direct-wiki` by material nature | [raw-routing-gate.md](references/raw-routing-gate.md) |
| Initializing wiki, accepting dossiers, compiling local cards | [wiki-compilation.md](references/wiki-compilation.md) |
| Checking/updating/querying WeKnora KBs & formatting answers | [rag-workflow.md](references/rag-workflow.md) |
| Escalating through wiki relationships | [wiki-graph-expanded-query.md](references/wiki-graph-expanded-query.md) |
