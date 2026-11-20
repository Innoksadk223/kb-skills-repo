# Source Ingestion (WeKnora Direct Parsing)

Load when syncing original source documents into a knowledge base. Requested scope controls the stop point: ingestion-only ends after `<project>-raw` sync and manifest reporting; it does not start deep reading or wiki compilation unless requested.

## Why No Local Markdown Conversion Layer Is Needed

WeKnora ships a built-in multi-format parsing pipeline (`docreader` + optional `mineru_cloud` / self-hosted `mineru`), and modern multimodal LLMs read PDFs and page images directly:

- **No local conversion skills required**: Do **not** ask users to install standalone local conversion skills or plugins; WeKnora handles document parsing server-side.
- **No local `wiki/raw/*.md` layer for new projects**: Original files (`PDF`, `DOCX`, `PPTX`, `XLSX`, `EPUB`, `HTML`, `MD`, `TXT`, `PNG/JPG`) remain untouched in the sibling `<source-folder>/` and upload directly to WeKnora's `<project>-raw` knowledge base.
- **Parser engine priority (`MinerU` first → `builtin` fallback)**:
  - If the WeKnora workspace has `mineru_cloud` (API Key) or self-hosted `mineru` configured in「设置 → 解析引擎」, PDFs and scans automatically route through MinerU for high-precision layout/table/formula extraction.
  - Otherwise, WeKnora automatically falls back to its built-in `docreader` engine, preserving exact PDF page numbers and bounding-box `source_locators` (`p.X`).
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
6. Flag fidelity-risk originals (scans, 古籍/影印本, vertical/commentary-interleaved layouts, dense tables/formulas) in `_source_manifest.md`. If `mineru_cloud` / `mineru` is not yet configured for heavy ancient scans, note that configuring a MinerU API Key in WeKnora Web UI improves OCR fidelity, or inspect the original PDF pages visually via multimodal read before quoting verbatim.
7. If proceeding toward `local_karpathy` Wiki compilation, apply [raw-routing-gate.md](raw-routing-gate.md) to classify each source in `_source_manifest.md` (`source_type`, `wiki_route`, `route_reason`).

## Acceptance And Reporting

- Every active-batch source file is either `completed` in `<project>-raw` (recorded in `检索索引/raw/manifest.json` and `_source_manifest.md`) or explicitly listed as failed/timed-out with its reason.
- Original files in `<source-folder>/` remain unmodified.
- No redundant `wiki/raw/*.md` copies are created for new direct-source projects.
- Report accepted, reused, and failed counts clearly; never present partial ingestion as whole-batch completion.
