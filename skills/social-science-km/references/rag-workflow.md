# RAG Workflow, Dual Wiki Modes, And Answer Contracts

All WeKnora sync, retrieval, freshness, and onboarding scripts are bundled directly inside `skills/social-science-km/scripts/` (stdlib Python 3 only; zero Go or third-party dependencies).

Projects support two selectable Wiki modes via `<知识库>/weknora_config.json` `"wiki_mode"` (or CLI `--wiki-mode`):
- **`local_karpathy`（默认）**：适合论文写作与严谨社科研究（深读档案 + 本地 `karpathy-wiki` 8 类卡片 + WeKnora `<project>-raw` & `<project>-wiki` 双库检索；网页端知识库列表可直接查看 `<project>-wiki` 卡片库）。
- **`weknora_native`（可选）**：适合日常资料速览与初期摸底（原始文献直传 `<project>-raw` 单库并开启 `indexing_strategy.wiki_enabled=true` 自动生成概念/人物/摘要页；直接在 `<project>-raw` 的「Wiki / 图谱」页签浏览）。

> **Ad-hoc single-KB operations outside a structured KM project**: When the user simply wants to upload a stray file or run a one-off search on an arbitrary WeKnora KB without a `<知识库>` directory, you may use the official WeKnora skill (`@lyingbug/weknora` Claw Skill, `weknora-shared` / `weknora-rag-search` CLI skills, or WeKnora built-in MCP).

## Dependencies, Onboarding, And Privacy

1. **One-click readiness check**: Run `python3 <skills-repo>/skills/social-science-km/scripts/doctor.py` when server/auth/model/parser status is unknown.
2. **Credentials**: Resolved from `WEKNORA_HOST` + `WEKNORA_API_KEY` (or `WEKNORA_TOKEN`), `~/.hermes/private/weknora-rag/config.json` (`chmod 600`), or `weknora` CLI profile. Never write real keys into repository files.
3. **Pure retrieval in Agent chat**: In `local_karpathy` mode, WeKnora only runs document parsing (`mineru_cloud` / `mineru` priority → `builtin` fallback), `pgvector` embedding, `ParadeDB BM25`, RRF fusion, and optional `Rerank`. **No chat LLM needs to be configured inside WeKnora** for Agent conversations (`Web UI 对话不可用` is expected when no chat model is set; the current Agent synthesizes the answer from returned chunks). Only `weknora_native` automated Wiki generation requires a generation model in WeKnora.
4. **Privacy boundary**: Uploading files or running queries sends text/files to `WEKNORA_HOST` and its configured Embedding/Rerank/MinerU model providers. Local freshness checks (`--check`) are offline.

## Preferred Commands

Run bundled scripts from `skills/social-science-km/scripts/` with `--project-root "<知识库>"`:

```bash
# 1. One-click environment & setup doctor
python3 <skills-repo>/skills/social-science-km/scripts/doctor.py

# 2. Check index freshness (offline SHA256 check)
python3 <skills-repo>/skills/social-science-km/scripts/check_rebuild_rag.py \
  --project-root "<知识库>" --check

# 3. Sync new/changed original PDFs/docs & local Wiki cards into WeKnora
python3 <skills-repo>/skills/social-science-km/scripts/check_rebuild_rag.py \
  --project-root "<知识库>" [--source-dir "<原始资料夹>"]

# 4. Two-hop evidence retrieval for Agent answering
python3 <skills-repo>/skills/social-science-km/scripts/km_query.py \
  --project-root "<知识库>" "孝为什么可以成为仁之本？学界有哪些反对意见？"
```

### Direct Low-Level Sync (`sync_kb.py`)

**Option A: `local_karpathy` (Default — New project without `wiki/raw/`, direct PDF/doc upload + `<project>-wiki` KB)**
```bash
# Step 1: Sync original read-only folder (<资料夹>/) -> WeKnora <project>-raw KB
python3 <skills-repo>/skills/social-science-km/scripts/sync_kb.py \
  --project-root "<知识库>" --source-dir "<原始资料夹>" \
  --wiki-mode local_karpathy --incremental

# Step 2 (after karpathy-wiki cards exist): Sync local wiki/ -> WeKnora <project>-wiki KB
python3 <skills-repo>/skills/social-science-km/scripts/sync_kb.py \
  --project-root "<知识库>" --wiki-mode local_karpathy \
  --md-dir wiki --index-dir 检索索引/wiki \
  --include-dirs claims,concepts,entities,comparisons,debates,observations,structures,predicts,synthesis,queries \
  --exclude-dirs raw,_archive --metadata-mode wiki --incremental
```

**Option B: `weknora_native` (Optional — Automated WeKnora Built-in Wiki + Single KB)**
```bash
python3 <skills-repo>/skills/social-science-km/scripts/sync_kb.py \
  --project-root "<知识库>" --source-dir "<原始资料夹>" \
  --wiki-mode weknora_native --incremental
```

*(Legacy compatibility: existing projects with `wiki/raw/*.md` omit `--source-dir`; `check_rebuild_rag.py` and `sync_kb.py` automatically preserve `enriched_raw` header injection & stripping on `wiki/raw/`.)*

## Query Routing And Escalation

This table is the single authoritative definition of retrieval escalation across all skills:

| Need / observed result | Mode or escalation |
|---|---|
| 原文、出处、哪一段、引用、页码; direct quote/page lookup | `--raw-only` |
| Conceptual, argumentative, comparison, cross-source, thesis questions | Wiki-first (default when wiki exists) |
| Broad terms, vocabulary mismatch, or fewer than 3 usable sources | Add `--multi-query` |
| Relevant hits poorly ranked, final prose needs precise evidence order | Add `--rerank` |
| Pronouns, previous/next paragraph, table or transition context matter | Neighboring chunk context (enabled by default in `km_query.py`; `--no-context` disables) |
| Final citation verification or high-risk thesis claims | `--deep`: wiki-first + multi-query + rerank + context, 20 candidates |
| Wiki-first remains shallow because graph relationships matter | [wiki-graph-expanded-query.md](wiki-graph-expanded-query.md) |

- If a required index is stale, stop and sync (or pass `--skip-check` **only** when the user explicitly approves querying stale indexes, and note the caveat in the answer).
- Offline regression tests (run when authorized): `python3 <skills-repo>/skills/social-science-km/scripts/self_test.py`.

## Answering Templates

Choose the smallest template matching user intent. Separate raw evidence from interpretation; state uncertainties explicitly.

### Evidence Answer

Every substantive claim must cite original source evidence (`# Raw Evidence`, e.g. `02-学术研究/肖群忠.pdf#p.12` or legacy `wiki/raw/...md`). Wiki hits explain recall/argument paths; they never prove a claim alone.

```markdown
## 检索摘要
- 查询意图：（一句话概括用户想知道什么）
- Wiki 命中节点：（列出命中的本地卡片或 weknora_native 页面；raw-only 写「未使用」）
- 命中源文献：X 篇（列出原文件名与页码）
- 索引状态：当前 / 过期（已提醒用户）/ 未使用（小库直接阅读）

## Wiki 路径
- 命中的命题 / 概念 / 争议页如何展开了正反方或关联概念
- 注意：这里是论证导航路径，不是最终原文证据

## 原始证据

### 观点／发现 A
- 来源：`02-学术研究/xxx.pdf#p.12`（chunk N）
> 原文逐字引用

解读：（1-2 句话说明这段原文与问题的关系）

## 综合解读
- 严格基于原始证据作答，可结合 Wiki 路径说明学理脉络

## 不确定项
- 证据边界、未覆盖文献或建议补充检索方向
```

### Source-Discovery Shortlist

```markdown
## 候选来源
| 源文件路径 | 为什么相关 | 命中关键词 | 建议路由 | 限制 |
|---|---|---|---|---|

## 初步缺口判断
- 薄弱概念 / 缺失正反方命题 / 原始文献缺口

## 下一步
- deep-reading-to-wiki / 直接 karpathy-wiki / 补充新文献
```

### Operational Status

```markdown
## 状态
- 当前结果：
- 需要用户确认的动作：

## 证据
- 命令 / 清单 / WeKnora 库状态：

## 下一步
- 最小可执行动作：
```
