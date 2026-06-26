# Quality Gates

Use these gates before handing a dossier to `karpathy-wiki`.

**Gate 0 (mechanical):** `scripts/validate_dossier.py` must report `PASS` first — it checks frontmatter, the five blocks, every HV candidate's raw anchor + context capsule, and the self-check. The judgment gates below are what the script cannot automate; each points to its canonical definition in `SKILL.md` instead of restating it.

## Gate 1: Not A Summary

Fail if the output is mainly a book report.

Required signals:

- It names skipped areas and why they were skipped.
- It separates reading map, candidate pool, deep dives, and wiki handoff.
- It includes raw anchors, not only paraphrases.
- If triggered by user-directed expansion, it records the user intent and source-discovery shortlist.

## Gate 2: Enough Richness

For a book or long document, expect at least:

- 1 reading map;
- 3 high-value areas, unless the source is short or weakly relevant;
- 5 candidate concepts, unless the source is narrow;
- 8 candidate claims, unless the source is short or mostly descriptive;
- at least two claim roles among support, objection, limitation, and bridge;
- a skipped-area list.

If the source cannot meet these numbers, explain why instead of padding.

## Gate 2A: Structure-Traceable Selection

Apply the `Structure-First Reading` procedure in `SKILL.md` as the canonical method; this gate only checks its result.

Fail if:

- the reading map does not cover every major chapter/section/argument phase at L0;
- a major unit lacks function and selected/skipped reason, or does not answer what problem it solves / which source thread it advances / which wiki gap it touches;
- a high-value area does not point back to a mapped unit and name its structural role;
- a high-value candidate lacks its compact layered path (whole source / part / section / point);
- the candidate pool jumps from isolated raw excerpts directly to wiki claims.

## Gate 3: Enough Depth

High-value candidates need context capsules. A high-value item without one must be downgraded or re-read.

Depth is not longer prose. Depth means the candidate preserves every field of the `Context Capsules` definition in `SKILL.md` (raw anchor, local context, whole-source role, compression risk, method boundary, RAG follow-up). A capsule missing any field is shallow, not deep.

## Gate 4: Wiki-Oriented

Fail if the dossier only explains the source itself.

Fail if the handoff only lists target paths without enough material to make the wiki nodes deep and rich.

It must say what to do next:

- update existing wiki page;
- create new wiki page;
- challenge or limit an existing claim;
- ignore as duplicate or low relevance;
- verify with RAG before compilation.

For each recommended wiki target, the handoff must carry the full node depth packet defined in `SKILL.md` (`Handoff To Karpathy-Wiki`). Fail if any recommended target lists only a path without that packet.

## Gate 5: Evidence Boundaries

Fail if AI inference is presented as author evidence.

Use this language:

- "作者明确主张" only when anchored in raw text.
- "可推论为" when the agent is interpreting.
- "可用于 wiki" only as a migration suggestion.
- "不能直接入库" when the raw anchor or context is weak.

For user-directed expansion, the user's inclination is never evidence. It may appear as `user_intent`, but every high-value candidate still needs raw support.

## Gate 6: Token Discipline

Fail if the agent reads the full source by default.

Fail if the agent treats structure coverage as permission to read every section in full.

Escalation follows the L0-L3 `Reading Budget` table in `SKILL.md`: L0 maps via cheap structural signals, L1 samples structurally relevant units, L2 builds context only for HV candidates with wiki relevance and structural role, L3 only for thesis-critical sections, major disputes, or high compression risk. Fail if a higher level is used without the lower one being insufficient.

## Stop Conditions

Stop and ask or report the blocker when:

- the raw source path cannot be located;
- a user-directed topic has no usable source-discovery result;
- the wiki target cannot be identified and the user has not allowed a generic dossier;
- no raw anchor supports a high-value candidate;
- the source is too malformed for reliable section mapping;
- all candidates are weak or duplicate existing wiki nodes;
- a full-book read is required to answer the user but the user has not approved that token cost.
