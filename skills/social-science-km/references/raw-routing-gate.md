# Source Routing Gate (`local_karpathy` Mode)

Load this reference before formal `karpathy-wiki` compilation in `local_karpathy` mode. (Not needed when `wiki_mode: "weknora_native"` is selected.)

Deep reading is triggered by **what the material is**, not by how long it is. File size or page count tells you to look; it does not decide the route.

## 1. Inventory Active Sources

Inspect the active source batch in `<source-folder>/` (recorded in `检索索引/_source_manifest.md`), or `wiki/raw/*.md` for legacy projects:

- For new direct-source projects: inspect file sizes, PDF page counts / table of contents / headings (directly on the PDF/document or via `list_chunks_for_doc` / WeKnora UI).
- For legacy `wiki/raw/` projects: `find wiki/raw -type f -name '*.md' ! -name '_*' -exec wc -lc {} +`.

Classify each source as `book/monograph`, `thesis/dissertation`, `chapter`, `paper/report`, `collection/anthology`, `classical/commentary`, `reference material`, or `short note`.

Treat a logical collection as one unit as well as individual files. Sum files belonging to the same anthology, edited volume, or grouped classical chapters so many short files do not bypass deep reading individually.

## 2. Route Each Source Or Group

**Mandatory `deep-reading`, regardless of length** — these materials lose core meaning when compressed without window-by-window close reading:

| Material | Note |
|---|---|
| 典籍 / 原典 / 注疏 / 古文献及其注疏 | Commentary layers are the interpretation; a summary is not evidence |
| 专著 / 学术著作（monograph, scholarly book） | Use a source-specific dossier |
| 教材 / 导论 / 手册章节（textbook, handbook chapter） | Chapter exposition builds on cumulative concepts |
| 论文集 / 合集 / 文集（anthology, edited collection） | Use a merged dossier for the volume |
| 学位论文（thesis / dissertation） | |
| A coherent multi-file logical group | Route as one unit |

**Overrides and remaining routes:**

| Condition | Route |
|---|---|
| Any type, any size: thesis-critical, theory-heavy, argument-rich, conceptually disputed, or likely to lose support / objection / limitation context | `deep-reading` |
| Ordinary single paper outside the categories above (e.g. standard journal article) | `direct-wiki` candidate; inspect abstract, headings, and conclusion first, then deep-read only if depth is needed |
| Short, narrow, self-contained, low-risk note/article not part of a collection | `direct-wiki` |
| Unreadable, corrupted, or failed WeKnora parse | `blocked`; fix parse or inspect original PDF |

## 3. Record The Decision

Record in `检索索引/_source_manifest.md` (or legacy `wiki/raw/_conversion_manifest.md`):

| Field | Value |
|---|---|
| `source_bytes` (or `raw_bytes` / `raw_lines`) | File size / page or line count |
| `source_type` | Classification above |
| `wiki_route` | `deep-reading`, `direct-wiki`, or `blocked` |
| `route_reason` | Material nature or semantic override that decided the route (+ group ID if grouped) |

Readiness is assessed per independent source or inseparable group:
- every active-batch source has a recorded route before compilation starts;
- `direct-wiki` sources compile directly from the checked original file/chunks with explicit provenance (`<rel_path>#p.X`);
- `deep-reading` sources compile once their dossier passes `validate_dossier.py` and source anchors are verified;
- `blocked` or unfinished items are held and reported separately without stalling independent ready sources.
