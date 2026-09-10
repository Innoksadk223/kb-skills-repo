# Compile Dossier → Wiki

Consume a `reading_dossiers/<source>-深读档案.md` and compile formal wiki pages from its CERIC context capsules and handoff list.

## When to Use

- User says "compile the dossier" or "把档案编译进 wiki"
- A deep-reading dossier exists with `target: karpathy-wiki` and `status: draft`
- `ingest.md` step ①.5 detects a dossier for a long/theory-heavy source

## ① Validate the Dossier

Before compilation, consume the project/wiki paths, requested scope, source set, route/reason, reading mode, dossier paths and acceptance results, and allowed write scope from the handoff. In orchestrated batches, require all sources to be registered in the existing manifest, then assess this source or inseparable group independently; blocked sources do not hold up unrelated ready sources. Missing required dossiers or an unavailable deep-reading skill never authorize normal-ingest fallback.

Verify the dossier is ready:

1. Check frontmatter: `target: karpathy-wiki` and `status: draft`.
2. Check 硬门禁自检 section: all 6 checkboxes must be `[x]` (checked). If any are `[ ]` (unchecked), stop this source/group and report which gate failed.
3. If `deep-reading-to-wiki` is installed, run its validator (`python3 <deep-reading-to-wiki 安装目录>/scripts/validate_dossier.py <dossier-path>`, 任意 cwd 均可) — FAIL blocks this source/group. PASS means structural checks passed, not that the source supports the claims or that full reading occurred. Under orchestration, missing required validation blocks the affected source/group and returns it for completion; only standalone compilation without the skill may use manual review of all dossier gates, anchors, capsules, quotas, and reading coverage.
4. Read `source_raw`, `user_intent`, `confidence`, `source_discovery`, and the recorded reading mode/coverage. Check that the dossier covers the dispatched source/group and requested scope; merged dossiers obey the same mode-specific gates.
5. Independently read the key raw passages and surrounding context. Verify they support each proposed node, its evidence type, boundaries, and inference chain before writing. An unsupported candidate stays pending or is rejected even with PASS; preserve the reason and next step.

## ② Orient to Wiki

Before writing any pages:

1. Read `SCHEMA.md` — conventions, tag taxonomy, page thresholds
2. Read `index.md` — existing pages, to avoid duplicates
3. Read recent `log.md` — last 20-30 entries
4. For each `互链` target in the dossier's handoff list, check if it exists. Nonexistent targets become stubs.

## ③ CERIC → Wiki Section Mapping

Every high-value candidate in the dossier has a CERIC context capsule (10 fields in 5 groups). Use this mapping to populate wiki page sections:

### For claim pages (`claims/<命题>.md`)

| CERIC Field | Maps to |
|---|---|
| 1. raw anchor + verbatim quote | `## 关键证据` — evidence position line (plain-text raw path) |
| 2. proposition type | `claim_type` frontmatter: `main thesis → main`, `support → support`, `objection → objection`, `limitation → limitation`, `bridge → bridge`, `definition → support` |
| 3. local context | `## 支撑理由` — contextual framing paragraph |
| 4. position in whole work | `## 论证位置` — "在全书中的角色" subsection |
| 5. layered path | `## 论证位置` — "分层路径" subsection |
| 6. reasoning chain | `## 前提与推理` — numbered premises + reasoning bridge |
| 7. compression risk | `## 方法边界` — CRITICAL: this is the anti-shallow field; always include. What the wiki node is most likely to misrepresent. |
| 8. wiki relationships | `## 关系` (body wikilinks) + `supports`/`opposes`/`limits`/`depends_on` frontmatter. Read CERIC field 8（wiki 关系）in the dossier HV capsule for specific page names. |
| 9. method boundary | `## 方法边界` — what the evidence can and cannot prove |
| 10. RAG recall questions | `## 待补证据` or comment in `## 方法边界` — questions to verify later |

### For concept pages (`concepts/<名称>.md`)

| CERIC Field | Maps to |
|---|---|
| 1. raw anchor + verbatim quote | `核心概念` — quoted definition with plain-text raw path |
| 2. proposition type | — (skip for concepts) |
| 3. local context | `核心概念` — contextual framing |
| 4. position in whole work | — (skip for concepts) |
| 5. layered path | — (skip for concepts) |
| 6. reasoning chain | — (skip for concepts) |
| 7. compression risk | `概念厘定` — what this concept is easily confused with; boundary statement |
| 8. wiki relationships | `相关概念` — wikilinks to adjacent concepts, related claims, comparisons |
| 9. method boundary | `## 边界` or `概念厘定` — normative/empirical/conceptual status |
| 10. RAG recall questions | `概念厘定` — "待确认" items |

### For comparison pages (`comparisons/<标题>.md`)

| CERIC Field | Maps to |
|---|---|
| 1. raw anchor + verbatim quote | Evidence anchors for each side of the comparison |
| 2. proposition type | — |
| 3. local context | Context framing paragraph |
| 6. reasoning chain | `## 辨析逻辑` — the logical chain behind the distinction |
| 7. compression risk | `## 易误读点` — what a shallow comparison gets wrong |
| 8. wiki relationships | `## 关联页面` — wikilinks to related claims/concepts |
| 9. method boundary | Level of evidence for each side |

### For optional observation, structure, and prediction pages

Use these types only when the evidence and graph role justify them; there is no per-dossier quota and no need to produce all three. Follow `references/templates/SCHEMA-template.md` for frontmatter and `references/claims.md` for card conventions.

| Target / type | Evidence and CERIC mapping |
|---|---|
| `observations/` / `observation` | Empirical findings or qualitative observations: fields 1/3 preserve raw evidence and collection context; 7/9 preserve sample, method, and generalization limits; 8 links the claims supported or challenged. Do not recast normative arguments as empirical findings. |
| `structures/` / `structure` | Frameworks, models, or typologies: fields 1/5/6 preserve the source, components, and their relationships; 7/9 preserve scope and assumptions; 8 links concepts and claims. Label an AI-reconstructed framework as interpretation. |
| `predicts/` / `prediction` | Conditional implications or forecasts: fields 1/6 retain anchored premises and the inference chain; 7/9 state conditions, uncertainty, and what would falsify the prediction; 8 links its basis. Distinguish author predictions from AI inference; never present an extrapolation as an observed fact. |

Use only fields that apply to the formal page type; retain all 10 fields in every HV dossier capsule. Preserve raw anchors, compression risks, and evidence boundaries in every compiled node.

## ④ Consume the Handoff List

### 建议新建 — create new pages

| Dossier Column | Use as |
|---|---|
| `目标路径` | Resolve against the dispatched project/wiki roots. Template paths beginning `wiki/` are project-relative; do not create `wiki/wiki/`. Create parent directories only within the allowed write scope. |
| `类型` | Page `type` frontmatter: `claim` / `concept` / `comparison` / `entity` / `observation` / `structure` / `prediction` (`prediction` files live in `predicts/`). |
| `核心贡献` | Page title (for claims) or `## 命题` one-liner |
| `边界/微妙之处` | `## 方法边界` or `概念厘定` — nuance that survives compression |
| `互链` | Body wikilinks; create stubs for nonexistent targets |
| `必查锚点` | Verify against raw source BEFORE writing the page; record as plain-text path in evidence |
| `入库条件` | Gate check before considering the page done |

### 建议更新 — update existing pages

| Dossier Column | Action |
|---|---|
| `现有页面` | Read the page first; never overwrite without reading |
| `深化方向` | Scope of update — don't expand beyond this |
| `核心贡献` | What new info is added |
| `来源候选` | Which HV candidate provides the evidence |
| `互链` | New wikilinks to add to the page |
| `注意` | Caution: things to preserve or avoid |

### 必查 raw 锚点

Before writing each page, check the corresponding raw source at the specified location. The dossier's context capsule is a guide, not a substitute for the source. If the raw source contradicts or doesn't support the capsule, flag it — don't compile blindly.

### 暂不进入 wiki

Log these to `log.md` but do not create pages. Include the `后续条件` so a future agent can re-evaluate.

## ⑤ Cross-Link

After creating all pages:

1. Scan every `[[wikilink]]` in new/updated pages
2. For each wikilink pointing to a nonexistent page: create a minimal stub
3. Add backlinks from core related pages (see `references/claims.md` → Backlink Rules)
4. Core claims get backlinks from their `related_concepts` / `related_entities` / `related_comparisons`

## ⑥ Update Navigation

- Add new pages to `index.md` under the correct section, sorted by pinyin
- Only `core: true` claims go in the Claims section of `index.md`
- Update "总页数" and "最后更新" in index header
- Append to `log.md`: `## [YYYY-MM-DD] compile-dossier | <dossier-title>`
- List every file created or updated in the log entry

## ⑦ Verify

1. Run `python scripts/lint.py <wiki_path>` — address any new errors
2. Check each compiled claim page: does `## 方法边界` contain the compression risk (CERIC field 7)? If not, the page is shallow — go back.
3. Check each compiled concept page: does `概念厘定` or `## 边界` contain the boundary statement (CERIC field 9)?
4. Verify no `[[raw/...]]` wikilinks in claim evidence sections — raw paths must be plain text.

## ⑧ Finalize the Dossier

Set `status: compiled` only when all accepted actions within the dossier's scope have been resolved. For partial compilation, retain `status: draft`, record completed paths in `compiled_to`, and record pending/rejected candidates with reasons and next steps in the handoff section. Do not mark an inseparable group complete while a required source is blocked. Report completed and pending sources separately; partial delivery is not whole-batch success.

For a completed dossier:

```yaml
status: compiled
compiled_to:
  - wiki/claims/<slug>.md
  - wiki/concepts/<slug>.md
  - wiki/comparisons/<slug>.md
updated: YYYY-MM-DD
```

Do not delete or archive the dossier. It stays in `reading_dossiers/` as a traceable pre-compilation record.

## Quick Reference: CERIC Fields

| # | Group | Field | Purpose |
|---|---|---|---|
| 1 | Claim | Raw anchor + verbatim quote | Source traceability |
| 2 | Claim | Proposition type | Role in argument structure |
| 3 | Evidence | Local context | What problem this passage solves |
| 4 | Evidence | Position in whole work | Premise/support/objection/conclusion |
| 5 | Reasoning | Layered path | Full → part → chapter → candidate |
| 6 | Reasoning | Reasoning chain | Premises → conclusion |
| 7 | Implications | Compression risk | What the wiki node is most likely to misread |
| 8 | Implications | Wiki relationships | Update/new/challenge/ignore existing pages |
| 9 | Context | Method boundary | Normative/empirical/conceptual/interpretive/analogy |
| 10 | Context | RAG recall questions | Questions to recover source context |
