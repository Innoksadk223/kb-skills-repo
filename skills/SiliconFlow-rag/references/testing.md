# Testing

Run the self-test without a real API key:

```bash
python3 skills/SiliconFlow-rag/scripts/self_test.py
```

The self-test uses mock embeddings and validates:

- full raw indexing;
- incremental indexing;
- context expansion;
- stats output;
- wiki include/exclude filters;
- wiki metadata-mode retrieval text;
- wiki-first query expansion and raw evidence retrieval;
- default multi-query behavior;
- unknown config key failure;
- evidence path normalization.
- `_*.md` operational-file exclusion;
- source-discovery aggregation and Raw size hints;
- enriched-Raw semantic dependency invalidation and metadata-only refresh;
- resumable embedding checkpoints and successful checkpoint cleanup;
- `debates/` wiki routing.

Also run syntax checks after script edits:

```bash
python3 -m py_compile \
  skills/SiliconFlow-rag/scripts/build_index.py \
  skills/SiliconFlow-rag/scripts/query_index.py \
  skills/SiliconFlow-rag/scripts/self_test.py
```

Do not add dependencies for tests. Keep tests runnable with the Python standard library only.
