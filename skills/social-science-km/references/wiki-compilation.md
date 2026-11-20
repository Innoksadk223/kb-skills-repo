# Wiki Initialization, Deep Reading, And Compilation (`local_karpathy` Mode)

Load when building/expanding our **social-science local Wiki (`wiki_mode: "local_karpathy"`)** or preparing a dossier for it. (If the project selected `wiki_mode: "weknora_native"`, skip local `deep-reading-to-wiki` and `karpathy-wiki` compilation; WeKnora generates Web Wiki pages automatically on `<project>-raw`.)

## Initialize Before Wiki-Oriented Reading

1. Establish `<知识库>/` (sibling to read-only `<source-folder>/`), research domain, and scope, with `WIKI_PATH=<知识库>/wiki/`.
2. Load [karpathy-wiki](../../karpathy-wiki/SKILL.md) and initialize missing `wiki/SCHEMA.md`, `wiki/index.md`, `wiki/log.md`, `qa-log.md`, and node directories (`claims`, `concepts`, `entities`, `comparisons`, `observations`, `structures`, `predicts`, `queries`, `synthesis`, plus optional `debates`). Preserve existing files.
3. Read `SCHEMA.md`, `index.md`, and recent `log.md` before wiki-oriented deep reading or compilation.
4. Standalone `deep-reading-to-wiki` requests need no target wiki initialization.

## Inventory And Source Readiness

Follow [raw-routing-gate.md](raw-routing-gate.md) to record a route (`deep-reading` | `direct-wiki` | `blocked`) in `检索索引/_source_manifest.md` (or legacy `wiki/raw/_conversion_manifest.md`) for every active-batch source:

- `direct-wiki`: usable source meeting low-risk single-paper criteria → read original PDF/doc directly (multimodal or via WeKnora chunks) and compile with explicit provenance (`<rel_path>#p.X`).
- `deep-reading`: mandatory for 典籍/注疏, 专著, 教材章节, 论文集, 学位论文, inseparable groups, and thesis-critical/disputed sources → compile only after `validate_dossier.py` PASS and source-anchor verification.

## Create And Accept Dossiers

1. Load [deep-reading-to-wiki](../../deep-reading-to-wiki/SKILL.md) and its [quality gates](../../deep-reading-to-wiki/references/quality-gates.md).
2. Read the original PDF/document directly (multimodal model reading/vision on `<source-folder>/...`, optionally assisted by WeKnora `<project>-raw` chunks) — or read `wiki/raw/*.md` on legacy projects.
3. Default `mode: thorough` (windowed sequential reading) for mandatory deep-reading categories; `mode: budget` (L0–L3 ladder) for prescreening or explicit time-saving requests.
4. Anchor every high-value candidate (`HV-*`) and table row to its exact source path + page/section (`02-学术研究/肖群忠.pdf#p.12`, or legacy `wiki/raw/...md:L117-119`). Include `source_pages` (for PDFs) or `raw_lines` (for Markdown) in dossier frontmatter for tiered quotas.
5. Validate structure:

```bash
python3 <skills-repo>/skills/deep-reading-to-wiki/scripts/validate_dossier.py reading_dossiers/<档案>.md
```

## Formal Compilation & Sync To WeKnora `<project>-wiki`

1. Compile accepted dossiers or `direct-wiki` sources into `wiki/{claims,concepts,entities,comparisons,debates,observations,structures,predicts}/`.
2. **Mandatory provenance**: Every non-stub Wiki card must list its original file path(s) in frontmatter `sources:` (e.g. `sources: [02-学术研究/肖群忠.pdf#p.12]`) and cite file + page/section on key claims/quotes in the body.
3. Update `wiki/index.md`, append `wiki/log.md`, and mark compiled dossiers `status: compiled` with `compiled_to:`.
4. Sync local Wiki cards into WeKnora `<project>-wiki` so two-hop retrieval is fresh AND all cards are directly visible in the WeKnora Web UI (`http://localhost` → `<project>-wiki`):

```bash
python3 <skills-repo>/skills/social-science-km/scripts/check_rebuild_rag.py --project-root "<知识库>"
```

## Bulk Ownership (Parallel Sub-Agents)

- **Deep-reading workers**: Read assigned original sources; write only their exact assigned `reading_dossiers/<name>.md`. Never edit `wiki/` or indexes.
- **Compilation workers**: Return structured candidate analysis only; **write no files**. Parent writes all `wiki/` pages, `index.md`, `log.md`, and runs `check_rebuild_rag.py` once after the batch lands.
