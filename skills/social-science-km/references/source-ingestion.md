# Source Ingestion

Load for discovery, conversion, or conversion coverage work. The requested scope controls the stop point: conversion-only ends after raw acceptance and coverage reporting; it does not start deep reading, wiki compilation, or indexing.

## Optional Academic-Search Acquisition

Use `academic-search` when the user asks for related papers or local raw/indexed sources cannot fill a stated gap. This is an upstream capability, not shipped by this repository; check availability only when this route needs it. Follow its discipline profile before searching.

1. Search with 2–3 focused queries. Return a shortlist with title, year, venue/source, relevance, citation count when available, DOI/arXiv ID, and legal full-text status.
2. Before external search, downloads, or a long batch, check the user's existing authorization. Ask only for a boundary not already approved.
3. Acquire only accepted `open_pdf` or otherwise legally accessible full text; never bypass paywalls.
4. Save accepted files preferably under `<source-folder>/academic-search/<topic>/...`. This approved acquisition is the only source-folder mutation; never move, delete, or rewrite existing sources.
5. Convert PDFs through MinerU and non-PDF/HTML through the routing below into `wiki/raw/<source-folder-name>/academic-search/<topic>/...`.
6. Record query/topic, DOI/arXiv ID, source/PDF URL, download status, converter, and output path in the conversion manifest.

Metadata, abstracts, and candidate lists are acquisition leads, not raw evidence. Formal wiki nodes require converted full text or an accepted dossier whose claims are checked against raw anchors.

## Conversion Procedure

Check dependencies for the current input types only. MinerU skill/MCP availability is environment-specific; do not assume either is installed. Consult the repository [README](../../../README.md) for upstream setup. A missing capability blocks only sources needing it.

1. Recursively inventory the active source batch: PDF, DOCX, PPTX, XLSX, HTML, TXT, Markdown, and other supported formats. Keep source and knowledge-base folders as siblings under the core directory contract.
2. Read `mineru-document-extractor` for PDF/fallback extraction and `markitdown` for non-PDF conversion when needed.
3. For a non-PDF route, check the active Python environment with `python -m markitdown --version`; install MarkItDown and necessary optional dependencies only if missing and within existing authorization.
4. Route **every PDF to MinerU first**, especially scans, 古籍/影印本, tables, formulas, and complex layouts. MarkItDown is not the default PDF route.
5. Route supported **non-PDF documents to MarkItDown first**. Empty/near-empty output, boilerplate/page markers only, widespread `�`, mojibake, or text unreadable in the source language triggers MinerU fallback.
6. Prefer MinerU MCP when available. Use CLI when MCP is unavailable, explicitly requested, or cannot satisfy the task. Long batches and token-backed network extraction must remain inside the approved scope.
7. Write `.md` outputs to `<知识库>/wiki/raw/<source-folder-name>/...`, preserving relative structure. Existing Markdown may be copied without changing content. Never overwrite originals.
8. If primary conversion and fallback fail, record source path, target path, attempted tools, and errors in `wiki/raw/_conversion_failures.md`; report them explicitly.
9. Generate/update `wiki/raw/_conversion_manifest.md`: source path, output path, converter, status, source size/hash when cheap, language/OCR mode when known, and failure reason. Markdown tables are fine; retain existing JSONL format if the project uses it.
10. Generate/update `wiki/raw/_主题索引.md` with concise coverage and rough topic groups when filenames/headings support them.
11. If proceeding toward wiki compilation, apply [raw-routing-gate.md](raw-routing-gate.md) to all active-batch content outputs and add `raw_bytes`, `raw_lines`, `source_type`, `wiki_route`, and `route_reason`. Conversion-only may stop after raw acceptance; do not launch downstream work just to populate future routes.

Do not create `资料md/` or another durable intermediate text layer. `wiki/raw/` is the sole bottom-layer converted text store.

## Batch Conversion Ownership

For large folders, split independent batches by directory, format, or topic:

- Give each subagent a non-overlapping file list and matching `wiki/raw/` output subtree.
- Workers may convert only assigned files and write their own raw outputs plus a small per-batch report.
- The parent merges reports into `_conversion_failures.md`, `_conversion_manifest.md`, and `_主题索引.md`, and owns final coverage.
- Workers must not concurrently edit those shared files, wiki pages, navigation, or RAG indexes.
- Before downstream routing, reconcile missing inputs, duplicate outputs, conversion failures, and remaining garbled MarkItDown output. Failed inputs remain visible; independent accepted outputs can advance once the whole batch has been accounted for and routed.

## Acceptance And Reporting

- Every source is represented by one accepted Markdown output or an explicit failure record with attempted tools/errors. The manifest is the coverage source of truth; filename resemblance is insufficient.
- `wiki/raw/` exists; it contains at least one `.md` unless all conversions failed.
- PDF entries identify MinerU unless an explicit exception is documented.
- Each MarkItDown failure/garbled output has been replaced by usable MinerU output or recorded as failed.
- A durable manifest exists after batch conversion or conversion of more than a few files; failures file exists whenever any source ultimately failed.
- Report accepted, failed, and pending counts and paths; never describe partial coverage as a fully successful batch.
- For the next stage, hand off the core's shared checklist through existing manifest/report/dossier fields; do not add a persistent task-state layer.
