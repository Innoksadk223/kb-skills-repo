# Raw Routing Gate

Load this reference after source conversion and before `karpathy-wiki` compilation.

Deep reading is triggered by **what the material is**, not by how long it is. Size tells you to look; it does not decide the route.

## 1. Inventory Converted Raw

Run from the knowledge-base project root. Inspect converted Markdown, not the original PDF/DOCX byte size:

```bash
find wiki/raw -type f -name '*.md' ! -name '_*' -exec wc -lc {} +
```

Record byte and line counts for every content file. Exclude operational files such as `_conversion_manifest.md`, `_conversion_failures.md`, and `_主题索引.md`.

Classify each source from its manifest entry, path/name, title page, table of contents, and headings as `book/monograph`, `thesis/dissertation`, `chapter`, `paper/report`, `collection/anthology`, `reference material`, or `short note`.

Treat a logical collection as a unit as well as individual files. Sum files belonging to the same anthology, proceedings volume, edited collection, or deliberately grouped source directory. Many small files must not bypass deep reading merely because each file is short.

## 2. Route Each Source Or Group

Use these defaults unless the project has stricter written thresholds.

**Mandatory `deep-reading`, regardless of length** — these materials lose the most when compressed, because their meaning lives in argument order, commentary chains, or cumulative exposition:

| Material | Note |
|---|---|
| 典籍 / 原典 / 注疏 / 古文献及其注疏（classical text, source text, commentary） | Commentary layers are the interpretation; a summary of them is not evidence |
| 专著 / 学术著作（monograph, scholarly book） | Use a source-specific dossier |
| 教材 / 导论 / 手册章节（textbook, introduction, handbook chapter） | Chapter-level exposition builds on earlier chapters |
| 论文集 / 合集 / 文集（anthology, edited collection） | Use a merged dossier for the volume |
| 学位论文（thesis / dissertation） | |
| A coherent multi-file logical group | Route as one unit; many short files must not slip through individually |

**Overrides and the remaining routes:**

| Condition | Route |
|---|---|
| Any type, any size: thesis-critical, theory-heavy, argument-rich, conceptually disputed, or likely to lose support / objection / limitation context | `deep-reading` |
| Large but none of the above — for example an ordinary single paper of 500+ lines | `direct-wiki` candidate; inspect it first, then deep-read only if depth is actually needed (on request, or in `budget` mode) |
| Short, narrow, self-contained, low-risk, under ~200 lines and ~40 KiB, and not part of a collection | `direct-wiki` |
| Empty, near-empty, garbled, or structurally unusable Raw | `blocked`; return to the upstream conversion workflow and its fallback |

### Size is an inspection prompt, not a decision

Line and byte bands — **≥500 lines or ≥100 KiB**, **200–499 lines or 40–99 KiB**, **under 200 lines and 40 KiB** — mean *open the source and look*. Check the title page, table of contents, headings, abstract, conclusion, and argument density, then ask:

1. Is this one of the mandatory materials above, or part of one?
2. Does a semantic override apply?
3. If neither, it is a `direct-wiki` candidate. Record that reason.

Size on its own never forces a dossier. Treat it as a signal rather than a quality verdict: OCR page markers, image links, tables, references, or malformed extraction can inflate it, while a short foundational text can be small yet high-risk.

Only `direct-wiki` may skip a dossier. A quick/rough-ingest request may relax a borderline case, but record the choice and the context risk; never silently bypass a 典籍, 专著, 合集, 学位论文, thesis-critical source, or any other mandatory category.

## 3. Record The Decision

Add or update these fields in `wiki/raw/_conversion_manifest.md` for every successfully converted content source:

| Field | Value |
|---|---|
| `raw_bytes` | Converted Markdown byte count |
| `raw_lines` | Converted Markdown line count |
| `source_type` | Classification above |
| `wiki_route` | `deep-reading`, `direct-wiki`, or `blocked` |
| `route_reason` | The material nature or semantic override that decided the route, plus collection membership or a conversion problem. Mention size only when it triggered an inspection. |

For grouped sources, give every member the same group identifier in `route_reason` or the manifest's existing notes field.

Readiness is then assessed per independent source or inseparable group, not as one batch-wide gate:

- every batch content source must have a recorded route before any of them compiles;
- a `direct-wiki` source may compile once its low-risk conditions are checked;
- a `deep-reading` source or inseparable group may compile once its required dossier is accepted and its key raw support is verified;
- a `blocked`, missing, or unaccepted source/group is held with its reason and next action, without stopping ready independent sources.

Report completed and held sources separately; do not present partial coverage as a finished batch.

## Why the trigger is material nature, not size

Measured on a real 65-source thesis corpus: a pure "≥500 lines → deep-reading" rule swept in 21 files — only 32% of files, but **over 76% of the total text volume**, because the large files hold most of the corpus. Meanwhile 55 of those 65 sources had no route recorded at all, and only 13 dossiers existed against the 21 the size rule demanded.

A rule that expensive stops being followed. Anchoring the trigger to material nature keeps dossiers where they actually pay for themselves — 典籍 and their 注疏, 专著, 教材, 合集, 学位论文, and thesis-critical papers — while ordinary single papers compile directly and only get a dossier when someone needs one.
