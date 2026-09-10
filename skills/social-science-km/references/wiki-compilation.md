# Wiki Initialization, Deep Reading, And Compilation

Load when building/expanding a wiki or preparing a dossier for a known wiki. Under `social-science-km` coordination the routing gate is mandatory; standalone sub-skill rules do not waive it. A dossier is an interpretation guide pointing to raw evidence, never a replacement for it.

## Initialize Before Wiki-Oriented Reading

1. Establish the sibling knowledge-base project root, research domain, and requested scope. Work from `<知识库>/`, with `WIKI_PATH=<知识库>/wiki/`.
2. Load [karpathy-wiki](../../karpathy-wiki/SKILL.md) and initialize only missing structures, before a deep-reading task is told to read target-wiki context. Preserve existing raw files, configuration, taxonomy, and content.
3. Minimum context is `wiki/SCHEMA.md`, `wiki/index.md`, and `wiki/log.md`; initialize `qa-log.md` and content directories according to that skill. Supported directories are `claims`, `concepts`, `entities`, `comparisons`, `observations`, `structures`, `predicts`, `queries`, and `synthesis`; add `debates` for mature multi-position controversies.
4. Read the resulting/existing SCHEMA, index, and recent log before wiki-oriented deep reading or compilation.
5. A deep-reading-only request may use the deep-reading skill's standalone mode and explicit output location. It need not initialize a wiki, create indexes, or compile formal pages.

Do not require RAG credentials, conversion tooling, or index checks merely to initialize/read local wiki context. Check a dependency when its route is actually needed.

## Inventory And Source Readiness

Follow [raw-routing-gate.md](raw-routing-gate.md) without duplicating its thresholds. Before any compilation, inventory and record a route for **every content source in the active batch**, including collection membership; account for failed conversions separately. Existing corpus content outside the batch is not a global backlog that must first be reread.

After this batch-wide routing inventory, readiness is local to an independent source or an inseparable logical group:

- `direct-wiki`: raw is usable and meets the gate's short, narrow, self-contained, low-risk requirements after checking collection membership.
- `deep-reading`: its corresponding dossier is accepted under the selected reading mode, quality gates, and raw-evidence review below.
- `blocked`, missing route, missing dossier, or failed dossier: hold that source/group with reason and next action.
- An inseparable group advances only when its required members and collective interpretation are ready. Do not split a collection into short files to evade the gate.
- Ready independent sources may compile while other sources remain blocked or await deep reading. Report partial completion explicitly, especially if the user asked for the whole batch.

Use the existing conversion manifest and dossier frontmatter for durable facts. The shared handoff in the core is a checklist, not a new task-state database.

## Create And Accept Dossiers

1. Load [deep-reading-to-wiki](../../deep-reading-to-wiki/SKILL.md) and its [quality gates](../../deep-reading-to-wiki/references/quality-gates.md).
2. Pass exact raw paths, source type, `raw_bytes`, `raw_lines`, route/reason, collection grouping, target-wiki context when applicable, and reading mode. Dossier frontmatter must carry manifest `raw_lines` for tiered quotas.
3. Default `mode: thorough` for the materials the routing gate marks mandatory — 典籍/原典/注疏, 专著, 教材/导论/手册章节, 论文集/合集, 学位论文, and theory-heavy or thesis-critical sources: structure navigation assists window-by-window full reading, followed by selection from the over-complete pool.
4. Use `mode: budget` for rapid prescreening or explicitly requested time savings: L0–L3 structure scan, sampling, and local close reading, retaining the deep-reading skill's short-text full-read exception. A quick request does not silently waive a mandatory deep-reading route.
5. A collection may use a merged dossier when one collective argument map is more useful; its selected mode applies to every member, not an unconditional sampling rule.
6. For user-directed expansion pass `trigger: user_directed_expansion`, `user_intent`, and the `source_discovery` shortlist into dossier frontmatter.
7. Write `reading_dossiers/<source-title>-深读档案.md`. Require raw anchors, context capsules, skipped-area notes, evidence boundaries, candidate nodes, and a wiki handoff checklist.
8. Preserve quotas, anti-slack self-check, and mode-specific quality requirements from the deep-reading skill. Candidate coverage includes claims, concepts, entities, comparisons, observations, structures, and predictions when justified; do not force every type into every dossier.
9. Structural validation command (when execution is authorized):

```bash
python3 <skills-repo>/skills/deep-reading-to-wiki/scripts/validate_dossier.py reading_dossiers/<档案>.md
```

A FAIL holds that source/group. PASS is a structural result, not proof of factual support: check high-value candidate claims against their raw anchors and context capsules before accepting for compilation. If validation was not run, report it as unverified; never invent PASS.

Deep reading writes only assigned dossier paths. It must not write any formal wiki node directory, `index.md`, `log.md`, or indexes.

## Formal Compilation

Use `karpathy-wiki` with `WIKI_PATH` pointing at the initialized wiki. For each ready source/group, check its manifest route and accepted dossier when required; a missing dossier cannot be skipped under the coordinator's contract.

1. Compile dossiers plus checked raw anchors, or directly compile accepted `direct-wiki` raw.
2. Use `claims/` for theses, supporting propositions, objections, limitations, and bridge claims; use `concepts/`, `entities/`, and `comparisons/` for their respective graph roles.
3. Carry supported observations into `observations/`, structural relationships into `structures/`, and predictions into `predicts/`, preserving their evidence status and uncertainty.
4. Use `debates/` for durable multi-position disputes with recurring authors, schools, objections, or methodological conflicts. A simple two-term distinction belongs in `comparisons/`.
5. Keep `synthesis/` as lightweight routes, reading order, current state, and gaps, never a durable evidence bank. Optional `synthesis/_global/` for large/mature corpora holds theme/community routes, debate maps, reading paths, clusters, and gaps; link these to formal nodes, including the extended node types where relevant.
6. User-directed expansion admits only candidates backed by accepted dossier entries with checked raw support or checked raw anchors. The user's inclination selects a direction, not a conclusion.
7. Carry interpretation-sensitive context risks into formal pages. Preserve factual disagreements with source attribution rather than smoothing them away.
8. Update `wiki/index.md` and append `wiki/log.md` after ingest. For each actually compiled dossier, set `status: compiled` and list key `compiled_to:` pages; do not mark withheld members compiled.
9. Confirm index/log and intended articles exist. The usual successful foundational compile includes an entity or concept article; a targeted update may instead modify justified existing/extended nodes, so assess its requested output rather than create filler.
10. After actual wiki edits, check relevant index freshness under [rag-workflow.md](rag-workflow.md), including raw enrichment dependencies. Apply updates only within existing authorization.

## Bulk Ownership (50+ Files, Multiple Domains)

The parent completes active-batch inventory and non-overlapping logical grouping before dispatch. Group by domain/source directory (classical texts, secondary scholarship, empirical psychology), usually under about 30 files each; keep an inseparable work/volume together rather than splitting by arbitrary equal counts.

| Stage | Worker permissions | Parent responsibilities |
|---|---|---|
| Deep reading | Read assigned source/group; write only exact assigned dossier path | Review dossiers, raw support, readiness, and blocked/skipped list |
| Wiki compilation | Return structured analysis only; **do not create or write any files** | Write all formal pages, navigation, shared logs, and compiled dossier metadata |
| Index maintenance | No concurrent worker mutations | Coordinate authorized updates after wiki writes |

Deep-reading handoff includes domain, exact input paths, exact dossier path, selected mode, `deep-reading-to-wiki`, and “Do not create or edit wiki pages.” Compilation handoff includes domain, existing wiki targets, exact raw/dossier paths, and requested candidate claims/concepts/entities/comparisons/observations/structures/predictions, cross-links, and context risks, with “Only analyze, do NOT create or write any files.”

The parent identifies cross-group links that individual workers cannot see; writes claims/concepts first, then entities/comparisons and evidence-supported extended nodes, then lightweight synthesis routes if cross-domain themes emerge. Update navigation/log in one pass per accepted compilation batch. Shared filesystem access never grants workers permission to mutate wiki pages.
