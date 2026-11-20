# Source Ingestion (WeKnora Direct Parsing)

Load when syncing original source documents into a knowledge base. Requested scope controls the stop point: ingestion-only ends after `<project>-raw` sync and manifest reporting; it does not start deep reading or wiki compilation unless requested.

## Why No Local Markdown Conversion Layer Is Needed

WeKnora ships a built-in multi-format parsing pipeline (`docreader` + optional `mineru_cloud` / self-hosted `mineru`), and modern multimodal LLMs read PDFs and page images directly:

- **No local conversion skills required**: Do **not** ask users to install standalone local conversion skills or plugins; WeKnora handles document parsing server-side.
- **No local `wiki/raw/*.md` layer for new projects**: Original files (`PDF`, `DOCX`, `PPTX`, `XLSX`, `EPUB`, `HTML`, `MD`, `TXT`, `PNG/JPG`) remain untouched in the sibling `<source-folder>/` and upload directly to WeKnora's `<project>-raw` knowledge base.
- **Parser engine routing (default `builtin`, explicit opt-in for `MinerU`)**:
  - Routing is decided per knowledge base by `chunking_config.parser_engine_rules`. With no rule set, `pdf` goes to the built-in `docreader` engine — **configuring a MinerU API Key alone does not change routing**.
  - `docreader` preserves PDF page numbers and bounding-box `source_locators` (`p.X`) and extracts the text layer of digital-born PDFs. Scanned / image-only PDFs produce image references only (`![…_page_N.jpg]`) with no text layer, which is useless for retrieval and citation.
  - For scans, 古籍/影印本, and vertical or commentary-interleaved layouts, explicitly route `pdf` to `mineru_cloud` (or self-hosted `mineru`) for the knowledge base — in the Web UI per-KB「解析引擎」setting, or by `PATCH /api/v1/knowledge-bases/{kb_id}` with `{"parser_file_types": ["pdf"], "parser_engine": "mineru_cloud"}`; then reparse existing documents (`POST /api/v1/knowledge/batch-reparse` with `{"kb_id", "ids"}`) so previously indexed scans get a real text layer.
  - Always verify after upload: sample a middle chunk of each PDF. If it is all `![…jpg]` with almost no CJK characters, the file was routed to a parser without OCR.
- **Legacy compatibility**: Existing knowledge bases that already have `wiki/raw/*.md` stay untouched; never delete or migrate existing `wiki/raw/` directories.

## Ingestion Procedure

1. Run `python3 <skills-repo>/skills/social-science-km/scripts/doctor.py` when server/parser status is unknown.
2. Verify sibling separation: `<source-folder>/` (read-only originals) sits beside `<source-folder>（知识库）/`. Never write processed outputs inside `<source-folder>/`.
3. Inventory supported files in `<source-folder>/` (`PDF`, `DOCX`, `PPTX`, `XLSX`, `EPUB`, `MD`, `TXT`, `HTML`, images).
4. Sync original files directly into WeKnora `<project>-raw` (incremental SHA256 ledger + automatic reuse of completed server docs):

```bash
python3 <skills-repo>/skills/social-science-km/scripts/sync_kb.py \
  --project-root "<知识库>" \
  --source-dir "<原始资料夹>" \
  --wiki-mode local_karpathy \
  --incremental
```

   *(If the user chose `weknora_native` automated Web Wiki mode, pass `--wiki-mode weknora_native`; WeKnora will parse the files AND automatically build Web Wiki pages in `<project>-raw`.)*

5. Inspect outputs written under `<知识库>/检索索引/`:
   - `检索索引/raw/manifest.json`: maps each relative source path (`02-学术研究/肖群忠.pdf`) to its SHA256 and WeKnora `knowledge_id`.
   - `检索索引/_source_manifest.md`: human-readable table of source paths, formats, byte sizes, WeKnora `knowledge_id`, and parse status.
6. Flag fidelity-risk originals (scans, 古籍/影印本, vertical/commentary-interleaved layouts, dense tables/formulas) in `_source_manifest.md`, and make sure those files are parsed by an OCR-capable engine (`mineru_cloud` / `mineru`) rather than the default `docreader`; otherwise inspect the original PDF pages visually via multimodal read before quoting verbatim.
7. If proceeding toward `local_karpathy` Wiki compilation, apply [raw-routing-gate.md](raw-routing-gate.md) to classify each source in `_source_manifest.md` (`source_type`, `wiki_route`, `route_reason`).

## Acceptance And Reporting

- Every active-batch source file is either `completed` in `<project>-raw` (recorded in `检索索引/raw/manifest.json` and `_source_manifest.md`) or explicitly listed as failed/timed-out with its reason.
- Original files in `<source-folder>/` remain unmodified.
- No redundant `wiki/raw/*.md` copies are created for new direct-source projects.
- Report accepted, reused, and failed counts clearly; never present partial ingestion as whole-batch completion.
