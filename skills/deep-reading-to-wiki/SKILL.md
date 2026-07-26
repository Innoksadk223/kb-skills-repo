---
name: deep-reading-to-wiki
description: Use when books, chapters, papers, source-discovery shortlists, or long Markdown sources must be read before karpathy-wiki, especially when raw-to-wiki ingest risks shallow summaries, missing claims, weak context, or low evidence density.
---

# Deep Reading To Wiki

## Core Idea

This skill is a pre-wiki deep-reading layer. It reads a long source in one of two modes — thorough (segmented sequential reading, the default for books and theory-heavy sources) or budget (L0-L3 sampling) — produces a structured `reading_dossiers/` file, and hands that file to `karpathy-wiki` for graph compilation.

It does not replace `karpathy-wiki`, does not write formal wiki pages, and does not treat the dossier as raw evidence.

The point of depth is to give future wiki nodes depth and richness: definitions with boundaries, claims with support and limits, relationships to existing pages, and raw anchors that preserve context. A dossier that only lists possible page paths is too thin.

It may start from an explicit raw file or from a user-directed expansion shortlist produced by `SiliconFlow-rag`, such as "补充儿童教育" -> candidate `wiki/raw/` sources.

## Output Contract

Write one Markdown dossier under the project root:

```text
reading_dossiers/<source-title>-深读档案.md
```

The dossier must use frontmatter and fixed headings. Load `references/dossier-template.md` before writing.

If the source is later compiled into wiki pages, update the dossier frontmatter:

```yaml
status: compiled
compiled_to:
  - wiki/claims/...
  - wiki/concepts/...
```

Do not delete dossiers by default. Treat them as durable audit and handoff records for how raw evidence was selected, compressed, and compiled.

## Dossier Retention Policy

Default lifecycle:

1. Keep new dossiers in `reading_dossiers/` with `status: draft` until they pass the quality gates.
2. After `karpathy-wiki` compilation, keep the dossier and update frontmatter to `status: compiled` plus `compiled_to:`.
3. If compiled dossiers become noisy, move them to `reading_dossiers/_archive/` and update frontmatter to `status: archived`.
4. Hard-delete a dossier only after explicit user approval.

Prefer archiving over deletion. A compiled dossier may still explain why a claim was created, why a candidate was rejected, what context risks were known, and which raw anchors must be rechecked. It is not raw evidence, not a formal wiki node, and not part of the default RAG index.

Ask the user before deleting any dossier unless the project has an explicit written cleanup policy. Only propose deletion when all of these are true:

- the dossier has been compiled or deliberately rejected;
- the relevant raw sources still exist under `wiki/raw/`;
- any useful wiki outputs are listed in `compiled_to:` or in the dossier handoff section;
- there is no unresolved context risk, pending RAG follow-up, or user-facing writing task depending on it.

Never delete original source files or `wiki/raw/` materials from this skill.

## Input Modes

Use the smallest input that can support a strong dossier:

| Mode | Input | What to do |
|---|---|---|
| Explicit source | One or more `wiki/raw/...md` paths | Create source-specific dossier(s). |
| Source-discovery shortlist | Candidate raw paths from `SiliconFlow-rag` with user intent and key terms | Pick high-value candidates, note weak candidates, then create dossier(s). |
| User-directed gap | A topic/gap from `social-science-km`, such as "补充儿童教育" | Require source discovery first unless raw paths are already known. |
| Retroactive repair | An already-ingested source whose wiki pages feel shallow (`trigger: retroactive_repair`) | Create the dossier the source should have had, then hand back for wiki revision. |

Standalone use (no wiki project): any readable Markdown/text path is a valid explicit source; anchors then point to the actual file path and `validate_dossier.py` reports the non-`wiki/raw/` prefix as a warning, not an error.

Do not deep-read from the user's topic alone. If no raw path is located, stop and report the source-discovery blocker instead of inventing a dossier.

## Multi-Source Merged Dossiers

When the user asks to deep-read multiple raw files and produce a **single merged dossier** (e.g., "深读 01-原典材料 中的 9 个文件，产出一份合并深读档案"), adapt the single-source workflow as follows:

1. **Filename**: Use a collective title, not one source's name: `reading_dossiers/<collection-name>-深读档案.md` (e.g., `原典材料-深读档案.md`).
2. **Frontmatter**: List all source files under `source_raw:`. Record each file's hit reason and key terms under `source_discovery:`.
3. **Structure map**: Organize the map by thematic layer or source group, not by single-file chapters. For each file, assign an L-level (short files get L3 full read; long files get L0 scan -> L1 key paragraphs -> L2 close reads). Cover every file in the map - none may be silently dropped.
4. **Cross-file candidate synthesis**: Concepts and claims that appear across multiple files should be merged into single candidate rows with multiple raw anchors. Use comparisons to surface divergences between files (e.g., 孝经 "德之本" vs 论语 "仁之本").
5. **High-value deep dives**: Each HV must cite its specific raw file path + line range. When a claim spans multiple files, list all anchors in the context capsule.
6. **Reading budget per file**: In thorough mode, every file goes through windowed sequential reading. In budget mode: files < 300 lines are fully read; 300-500 lines are fully read unless weakly relevant (record skipped parts in 放弃清单); > 500 lines use L0 grep-based structure scan + L1 targeted reads. Batch independent reads across files in parallel.
7. **Exclusion handling**: When the user explicitly excludes some files (e.g., "排除朱子语类4部"), record the exclusion in the structure map and do not read those files.
8. **raw_lines**: Sum the converted line counts of all included files into the frontmatter `raw_lines` so the tiered quota matches the merged scope.

## Role Boundaries

| Layer | Responsibility |
|---|---|
| `wiki/raw/` | Original or converted source text. Never modify for interpretation. |
| `reading_dossiers/` | Pre-compiled deep-reading materials, context capsules, candidate nodes, handoff notes. |
| `karpathy-wiki` | Formal graph nodes, backlinks, `index.md`, `log.md`, claims, concepts, comparisons. |
| RAG index | Evidence recall, context expansion, citation checking, and local zoom-in. |

## Required Orientation

Before reading the long source, orient to the target wiki when available:

1. Read `wiki/SCHEMA.md`.
2. Read `wiki/index.md`.
3. Read the recent part of `wiki/log.md`.
4. Search existing wiki pages for obvious overlapping concepts, authors, claims, and comparisons.

If using the `social-science-km` workflow, run its RAG staleness check before RAG-assisted reading.

For topic-initiated dossiers, preserve the search context in frontmatter:

```yaml
trigger: user_directed_expansion
user_intent: "补充儿童教育"
source_discovery:
  - path: wiki/raw/...
    reason: "命中儿童教育、爱敬、积浸等关键词"
```

## Reading Modes And Budget

Pick the mode first, then apply its discipline (enforced by quality-gates.md Gate 6):

| Mode | When | How |
|---|---|---|
| **thorough**（默认） | Books, monographs, collections, theory-heavy or thesis-critical sources — depth and claim coverage matter more than token cost | Segmented sequential reading below. |
| **budget** | Quick pre-screening, weakly relevant sources, or the user explicitly asks to save time | L0-L3 ladder below. |

`social-science-km` Step 2 may pass `mode: thorough|budget` with the dispatch; when unspecified, default by the table above. Thorough mode costs several times more tokens/time — that trade is deliberate: richness and depth take priority.

### Thorough mode: segmented sequential reading

Designed to stay reliable even for weaker models: small steps, one fixed instruction, mechanical checks — no global judgment before reading.

1. Split the source into fixed windows of 200-400 lines, aligned to headings where possible. <!-- ponytail: 窗口大小是校准旋钮，按模型上下文与源密度调 -->
2. Read windows strictly in order. For every window run the same fixed instruction: extract EVERY claim, concept, entity, and argument relation in this window, each with a line-anchored verbatim excerpt.
3. Append each window's extractions to the candidate node pool as you go (the dossier draft accumulates; work is resumable at any window boundary).
4. A window yielding zero candidates must be re-read once; if still empty, record its line range and a one-line reason in 放弃清单.
5. After all windows, run the merge pass: dedupe candidates, select HV entries from the over-complete pool, build context capsules from the already-read text, and satisfy the quality-gates.md Gate 2 tier for `raw_lines`.
6. Selection happens AFTER reading, from an over-complete pool — never before.

### Budget mode: L0-L3 ladder

Use the cheapest level that can answer the quality gate:

| Level | Read | Purpose |
|---|---|---|
| L0 structure scan | TOC, introduction, conclusion, headings, chapter openings/endings | Map the source and select likely high-value regions. |
| L1 sparse sampling | Definitions, thesis paragraphs, transitions, summaries, tables, key notes | Build the candidate node pool. |
| L2 targeted close reading | Surrounding paragraphs or sections for high-value candidates | Build context capsules and evidence anchors. |
| L3 local full-section/chapter reading | Core claims, major disputes, or thesis-critical chapters | Resolve high-stakes context and compression risk. |

File-length rules: < 300 lines read fully (counts as L3, a length special case); 300-500 lines read fully unless weakly relevant, recording skipped parts in 放弃清单; > 500 lines start at L0 + L1.

Escalation is mechanical, not a judgment call:

- any structure-map unit with zero candidates after L1 → sample it once more at L1 before accepting zero;
- any HV candidate whose capsule cannot be filled from what was read → escalate that region to L2/L3.

## Tooling Pitfall: file search on Complex Paths

File-search tools may return zero results when the path contains spaces, parentheses, Chinese characters, or iCloud-synced paths (e.g., `/Users/.../Library/Mobile Documents/com~apple~CloudDocs/...`). When a search returns 0 hits on a file you know exists:

1. **Do not assume the file is empty or missing.** Verify by reading the file directly first.
2. **Fall back to shell `grep -n`** to find keyword line numbers, then read the file with an offset/limit around those lines.
3. **Batch independent grep calls** across multiple files in one shell invocation to save round-trips.

This is a path-resolution limitation, not a content problem. The files are readable directly even when search tools cannot index them.

## Structure-First Reading

Read structure-first, value-second. Do not build the candidate pool from isolated passages that only look interesting.

Before selecting high-value candidates:

1. Map the source's major units: chapters, sections, argument phases, or document headings.
2. Give every major unit an L0 classification: function, likely wiki relevance, selected/skipped reason, and re-trigger condition.
3. In the structure/problem map, answer for each major unit: what problem it solves, what source-level thread it advances, and which wiki gap it touches.
4. For each high-value candidate, record a compact layered path: whole source -> part or argument phase -> chapter or section -> candidate point.
5. Apply L1 sampling to units that define terms, state a thesis, summarize evidence, mark transitions, raise objections, or carry the user's target topic.
6. Select high-value areas only when they have both wiki relevance and a clear structural role in the source.
7. Escalate to L2/L3 only for structurally justified candidates, not because a passage is rhetorically attractive.

Structure coverage is not full-source reading. L0 covers the map; L1 samples key points; L2/L3 remain local exceptions.

Do not jump from raw excerpt to wiki claim. A high-value candidate must preserve its compact layered path.

## Minimum Dossier Blocks

Every dossier must include only these default blocks:

1. Reading map.
2. Candidate node pool.
3. High-value deep dives.
4. Wiki handoff checklist.
5. Anti-slack self-check.

Conditional modules are allowed only when triggered:

| Trigger | Add |
|---|---|
| A concept has conflicting meanings, translations, or measurements | Concept lineage module. |
| The source challenges existing wiki claims or authors | Dispute / objection module. |
| One section is thesis-critical | Local full-section reading module. |
| The user is writing prose now | Writing-use module. |

## Context Capsules

The capsule's canonical layout is the **CERIC 10-field structure** in `references/dossier-template.md` — that template is the single authority for field names and numbering. The list below is only the semantic summary. Each high-value candidate claim, concept, or comparison must include a context capsule:

- raw anchor: file path, chapter/section if available, and short exact excerpt;
- local context: what problem the passage addresses and what it leads to;
- whole-source role: definition, premise, support, bridge, objection, limitation, conclusion, or method note;
- compression risk: what would be distorted if compressed into a wiki node;
- method boundary: normative claim, empirical finding, concept definition, interpretation, analogy, or AI inference;
- RAG follow-up questions: questions that can recover the source context later.

If a candidate lacks a raw anchor and context capsule, do not label it high value.

## Quality Gates

Load `references/quality-gates.md` before finalizing the dossier.

At minimum, the dossier must show:

- high-value areas and skipped areas;
- candidate concepts and claims;
- at least two of support, objection, limitation, or bridge claims when the source supports them;
- context capsules for high-value candidates;
- wiki relationship notes: update existing, create new, challenge existing, ignore as duplicate;
- clear separation between author claims, raw evidence, AI inference, and wiki migration suggestions.

If the gate fails, do not hand the dossier to `karpathy-wiki`. Continue targeted reading or report the blocker.

## Handoff To Karpathy-Wiki

The final section must tell the next agent:

- which existing wiki pages to update;
- which new `concepts/`, `claims/`, `comparisons/`, or `entities/` pages may be needed;
- which candidates are too weak for wiki entry;
- which raw anchors must be checked before formal compilation;
- which context risks must be preserved in formal wiki pages;
- for each recommended wiki target, the node depth packet: core contribution, nuance or boundary, relationship/backlink suggestions, required raw anchors, entry condition, and what would make the node shallow or misleading.

Formal wiki writing remains the job of `karpathy-wiki`.
