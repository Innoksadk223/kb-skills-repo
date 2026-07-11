# Raw Size And Deep-Reading Routing Gate

Load this reference after source conversion and before `karpathy-wiki` compilation.

## 1. Inventory Converted Raw

Run from the knowledge-base project root. Inspect converted Markdown, not the original PDF/DOCX byte size:

```bash
find wiki/raw -type f -name '*.md' ! -name '_*' -exec wc -lc {} +
```

Record byte and line counts for every content file. Exclude operational files such as `_conversion_manifest.md`, `_conversion_failures.md`, and `_主题索引.md`.

Classify each source from its manifest entry, path/name, title page, table of contents, and headings as `book/monograph`, `thesis/dissertation`, `chapter`, `paper/report`, `collection/anthology`, `reference material`, or `short note`.

Treat a logical collection as a unit as well as individual files. Sum files belonging to the same anthology, proceedings volume, edited collection, or deliberately grouped source directory. Many small files must not bypass deep reading merely because each file is short.

## 2. Route Each Source Or Group

Use these defaults unless the project has stricter written thresholds:

| Raw state | Default route |
|---|---|
| Book/monograph, thesis/dissertation, anthology/collection, or coherent multi-file source group | `deep-reading` regardless of individual file size; use a source-specific or merged dossier as appropriate |
| At least 500 lines or 100 KiB | `deep-reading` unless inspection shows extraction noise rather than substantive text |
| 200-499 lines or 40-99 KiB | Inspect TOC/headings, introduction/abstract, conclusion, and argument density; use `deep-reading` when theory-heavy, multi-claim, context-sensitive, or central to the research question |
| Under 200 lines and under 40 KiB | `direct-wiki` only when narrow, self-contained, low-risk, and not part of a larger collection |
| Any size: thesis-critical, theory-heavy, argument-rich, conceptually disputed, or likely to lose support/objection/limitation context | `deep-reading` |
| Empty, near-empty, garbled, or structurally unusable Raw | `blocked`; return to Step 1 conversion fallback |

When line and byte bands disagree, use the more cautious band and inspect the source. Size is a routing signal, not a quality verdict: OCR page markers, image links, tables, references, or malformed extraction may inflate it, while a concise foundational text may be small but high-risk.

Only `direct-wiki` may skip a dossier. A quick/rough-ingest request may relax a borderline case, but record the choice and context risk; do not silently bypass a book, collection, thesis-critical source, or other mandatory semantic override.

## 3. Record The Decision

Add or update these fields in `wiki/raw/_conversion_manifest.md` for every successfully converted content source:

| Field | Value |
|---|---|
| `raw_bytes` | Converted Markdown byte count |
| `raw_lines` | Converted Markdown line count |
| `source_type` | Classification above |
| `wiki_route` | `deep-reading`, `direct-wiki`, or `blocked` |
| `route_reason` | Size band, semantic override, collection membership, or conversion problem that determined the route |

For grouped sources, give every member the same group identifier in `route_reason` or the manifest's existing notes field. Step 3 may begin only after all content sources are routed and every `deep-reading` route has an accepted dossier.
