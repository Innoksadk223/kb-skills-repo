# Config and Index Maintenance

## Config example

Reusable non-secret parameters can go into `rag_config.json`:

```json
{
  "build": {
    "chunk_size": 1200,
    "overlap": 200,
    "batch_size": 16,
    "timeout": 60,
    "sleep": 0,
    "dimensions": 1024,
    "encoding_format": "base64"
  },
  "query": {
    "top_k": 6,
    "candidates": 12,
    "wiki_top_k": 5,
    "timeout": 60,
    "expand_context": true,
    "context_window": 1,
    "multi_query": false,
    "dimensions": 1024
  }
}
```

Command-line flags override config values.

Embedding builds retry transient disconnects, HTTP 429, and HTTP 5xx failures up to three times with exponential backoff. For unstable connections or large embedding models, reduce `batch_size` and increase `timeout` in the project config before retrying.

`Qwen/Qwen3-Embedding-*` supports reduced Matryoshka dimensions. Use an explicitly configured dimension for both build and query; 1024 is a practical storage/transfer default for large local corpora. `base64` build responses reduce JSON transfer overhead without changing the stored float-vector format.

Long builds write `.embedding_checkpoint.jsonl` inside the target index directory after each successful batch. A retry with the same model reuses matching chunk IDs and reports resume progress. The checkpoint is deleted only after `chunks.jsonl`, `embeddings.jsonl`, and `manifest.json` are committed successfully.

## Defaults

- Raw input: `wiki/raw/`
- Default index output: `检索索引/`
- Recommended raw index: `检索索引/raw`
- Recommended wiki index: `检索索引/wiki`
- API key env var: `SILICONFLOW_API_KEY`
- Private key config: `~/.hermes/private/SiliconFlow-rag/config.json` preferred; `~/.codex/SiliconFlow-rag/config.json` legacy fallback
- Embedding model: `BAAI/bge-m3`
- Optional rerank model: `Qwen/Qwen3-Reranker-8B`

## Maintenance wording

- When `wiki/raw/` changes materially, update the raw index. If the tool reports ordinary new/changed files, call this "新增到索引" or "增量更新", not "重建".
- When `claims/`, `concepts/`, `entities/`, `comparisons/`, `synthesis/`, or `queries/` change materially, update the wiki index. If only files changed, call this "增量更新 wiki 索引".
- An `enriched_raw` index also depends on wiki labels from `claims/`, `concepts/`, `comparisons/`, `entities/`, and `debates/`. The manifest records `semantic_source_hashes` and per-Raw `semantic_hint_hashes`; wiki-label changes must mark Raw stale and re-embed only affected Raw sources when possible.
- Use "重建" only for a full rebuild: initial build from an empty/missing index, or automatic fallback caused by changed `metadata_mode`, embedding model, mock/real mode, chunk size, overlap, include/exclude dirs, source dir, or index format.

## Index file rules

Keep each index directory's files together:

```text
manifest.json
chunks.jsonl
embeddings.jsonl
```

Do not edit index files by hand. Re-run `build_index.py` instead.
