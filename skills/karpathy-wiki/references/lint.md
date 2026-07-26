# Lint

Health-check the wiki for issues and research opportunities.

## Run the Script

```bash
python3 scripts/lint.py <wiki_path>
```

The script scans all wiki pages and raw files, outputs a JSON report. Parse the JSON and present findings to the user grouped by severity:

**broken_links > follows > supersedes_consistency > orphans > source_drift > contradictions > claim_structure > index > last_verified > stale > frontmatter > quality > oversized > tag_issues > stub_upgrades > stub_cleanup**

## Report Format

Translate JSON findings into a human-readable report:

1. **断链** — wikilinks pointing to non-existent pages (list each broken target + which pages link to it)
2. **孤立页面** — pages with zero inbound links
3. **来源漂移** — raw/ files whose content changed (sha256 mismatch)
4. **矛盾页面** — pages marked `contested: true` or with `contradictions:` field
5. **Claim 结构问题** — claim 缺少必填 frontmatter、`## 命题`、`## 关系`，核心 claim 无证据，或 raw 被 wikilink
6. **陈旧内容** — pages not updated in >90 days
7. **Frontmatter 问题** — missing required fields, tags outside taxonomy
8. **质量信号** — `confidence: low` pages, single-source pages without confidence field
9. **超大页面** — pages over 200 lines (candidates for splitting)
10. **Tag 审计** — tags not in SCHEMA.md taxonomy
11. **Stub 升级候选** — stubs referenced by 2+ full pages
12. **Stub 清理** — stubs whose all referrers are archived
13. **Follows 序列** — `follows:` 指向不存在页面（悬空边）；报告顶层 `followed_by` 为 lint 推导出的反向索引（谁接着我）
14. **Supersedes 一致性** — `supersedes` 与目标页 `superseded-by` 双向不一致
15. **Index 完整性** — 应入 index 的页面缺失 / index 条目无对应页面
16. **Last-verified 过期** — `last-verified` 超过 12 个月的页面

Stub 判定条件：`confidence: low` 且正文含 📝 标记（SCHEMA-template 的 stub 约定；若项目 SCHEMA 移除了该标记，stub 相关检查会静默失效）。

Append to log.md: `## [YYYY-MM-DD] lint | N issues found`

## What The Script Scans

- Wiki pages under `entities/`, `concepts/`, `comparisons/`, optional `debates/`, `claims/`, `observations/`, `structures/`, `predicts/`, `queries/`, and `synthesis/`.
- Raw Markdown files recursively under `raw/`, excluding hidden directories and `raw/assets/`.
- `index.md` entries against real wiki pages.

Index rule: standard pages should be listed in `index.md`; for claims/observations/structures/predicts only `core: true` pages are required in `index.md` — ordinary ones are discoverable through their folders and graph links.

## Self-Test

After changing `scripts/lint.py`, run:

```bash
python3 scripts/lint_self_test.py
```

The self-test covers recursive raw scanning, `synthesis/` scanning, ordinary claim index rules, bilingual taxonomy tags, contested claim status, and source drift.

## Research Leads

After presenting findings, review the JSON for research opportunities. The Obsidian graph view already surfaces these signals visually — you are naming them explicitly:

- **Stub 升级**: for each `stub_upgrades` entry, suggest finding a source covering that concept. A stub with 3+ inbound links is a knowledge gap the user likely cares about.
- **矛盾页面**: for each page with `contested: true` or `contradictions:`, suggest finding a third-party source to break the tie.
- **孤立页面**: for each orphan, suggest which existing page(s) could naturally link to it — the content is there, just disconnected.
- **高频 tag 缺概念页**: scan all tags in use. If a tag appears on 5+ pages but has no dedicated concept page in `concepts/`, suggest creating one to synthesize the scattered references.
- **概念密集领域缺入口页**: scan `concepts/` for clusters of 5+ pages sharing 2+ tags but with no corresponding lightweight page in `synthesis/`. Flag these as entry-page candidates; if the cluster contains thesis/objection/limitation logic, recommend extracting `claims/` first.
- **单来源页面**: pages with only one source and `confidence: low` or missing confidence field — suggest finding corroborating sources.
