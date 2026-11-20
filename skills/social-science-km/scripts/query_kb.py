#!/usr/bin/env python3
"""Query WeKnora-backed RAG indexes and print structured evidence for agents.

Supports:
- Raw-only retrieval (``--index-dir 检索索引/raw``)
- ``local_karpathy`` Wiki-first retrieval (``<project>-wiki`` KB → local ``wiki/``
  expansion → ``<project>-raw`` KB + automatic ``KM_ENRICHED_HEADER`` stripping
  + PDF/document page locator extraction ``p.X``)
- ``weknora_native`` Wiki-first retrieval (WeKnora native ``/wiki/search`` →
  ``<project>-raw`` KB)
- ``--rerank``, ``--multi-query``, ``--expand-context``, ``--source-discovery``, ``--stats``
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from weknora_client import (  # noqa: E402
    DEFAULT_WIKI_MODE,
    TEXT_SOURCE_EXTS,
    VALID_WIKI_MODES,
    WeKnoraError,
    bm25_tokenize,
    extract_page_label,
    load_project_config,
    make_backend,
    resolve_project_config_path,
    strip_enriched_header,
)

QUERY_DEFAULTS = {
    "index_dir": "检索索引/raw",
    "top_k": 6,
    "candidates": 12,
    "wiki_top_k": 5,
    "timeout": 60,
    "expand_context": False,
    "context_window": 1,
    "wiki_index_dir": None,
    "raw_index_dir": None,
    "wiki_first": False,
    "multi_query": False,
    "source_discovery": False,
}


def load_manifest(index_dir: str | Path) -> dict:
    mpath = Path(index_dir).expanduser().resolve() / "manifest.json"
    if not mpath.is_file():
        raise SystemExit(f"Manifest not found: {mpath} (run sync_kb.py or check_rebuild_rag.py first)")
    return json.loads(mpath.read_text(encoding="utf-8"))


def map_doc_to_rel_path(manifest: dict) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for rel_path, info in (manifest.get("remote_docs") or {}).items():
        if isinstance(info, dict) and info.get("knowledge_id"):
            mapping[str(info["knowledge_id"])] = rel_path
    return mapping


def generate_multi_queries(question: str) -> list[str]:
    queries = [question.strip()]
    parts = [p.strip() for p in re.split(r"[？?；;，,、\s]+", question) if len(p.strip()) >= 2]
    if len(parts) >= 2:
        joined = " ".join(parts)
        if joined not in queries:
            queries.append(joined)
    tokens = []
    for tok in bm25_tokenize(question):
        if len(tok) >= 2 and tok not in tokens:
            tokens.append(tok)
    if len(tokens) >= 3:
        kw_query = " ".join(tokens[:10])
        if kw_query not in queries:
            queries.append(kw_query)
    return queries[:3]


def normalize_hit(raw_row: dict, doc_map: dict[str, str], strip_header: bool, backend) -> dict:
    doc_id = str(raw_row.get("knowledge_id") or "")
    rel_path = doc_map.get(doc_id) or str(raw_row.get("knowledge_title") or raw_row.get("knowledge_filename") or "?")
    chunk_no = int(raw_row.get("chunk_index") or 0)
    raw_content = str(raw_row.get("content") or "")
    clean_text = strip_enriched_header(raw_content) if strip_header else raw_content.strip()
    page_label = extract_page_label(raw_row)

    if strip_header and not clean_text.strip() and doc_id:
        siblings = backend.list_chunks_for_doc(doc_id)
        for sib in siblings:
            if int(sib.get("chunk_index") or 0) > chunk_no:
                cand = strip_enriched_header(str(sib.get("content") or "")).strip()
                if cand:
                    clean_text = cand
                    chunk_no = int(sib.get("chunk_index") or chunk_no)
                    page_label = page_label or extract_page_label(sib)
                    break

    item: dict = {
        "id": str(raw_row.get("id") or f"{doc_id}:{chunk_no}"),
        "knowledge_id": doc_id,
        "source_path": rel_path,
        "page": page_label,
        "chunk_no": chunk_no,
        "text": clean_text,
        "similarity": float(raw_row.get("score") or 0.0),
    }
    if "rerank_score" in raw_row and raw_row["rerank_score"] is not None:
        item["rerank_score"] = float(raw_row["rerank_score"])
    return item


def retrieve_from_kb(
    backend,
    manifest: dict,
    query_text: str,
    top_k: int,
    candidates: int,
    rerank: bool,
    rerank_model_id: str | None,
    multi_query: bool,
    expand_context: bool,
    context_window: int,
) -> tuple[list[dict], str | None]:
    kb_id = str(manifest["kb_id"])
    doc_map = map_doc_to_rel_path(manifest)
    strip_header = manifest.get("metadata_mode") == "enriched_raw"

    queries = generate_multi_queries(query_text) if multi_query else [query_text]
    fused_by_id: dict[str, dict] = {}
    rrf_scores: dict[str, float] = {}
    note_parts: list[str] = []

    for q in queries:
        rows, meta = backend.hybrid_search(
            kb_id=kb_id,
            query_text=q,
            match_count=max(candidates, top_k),
            rerank=rerank,
            rerank_model_id=rerank_model_id,
        )
        outcome = meta.get("outcome")
        if rerank and outcome and outcome not in ("ok", "disabled", "no_candidates"):
            msg = f"WeKnora rerank outcome={outcome}"
            if msg not in note_parts:
                note_parts.append(msg)
        for rank, row in enumerate(rows, start=1):
            item = normalize_hit(row, doc_map, strip_header=strip_header, backend=backend)
            if not item["text"].strip():
                continue
            cid = item["id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (60 + rank)
            if cid not in fused_by_id:
                fused_by_id[cid] = item
            else:
                prev = fused_by_id[cid]
                if item.get("rerank_score", -1) > prev.get("rerank_score", -1):
                    prev["rerank_score"] = item["rerank_score"]
                if item["similarity"] > prev["similarity"]:
                    prev["similarity"] = item["similarity"]

    results = list(fused_by_id.values())
    if len(queries) > 1:
        for it in results:
            it["rrf_score"] = round(rrf_scores.get(it["id"], 0.0), 4)
        results.sort(key=lambda x: (x.get("rerank_score", -1.0), x.get("rrf_score", 0.0), x["similarity"]), reverse=True)
    else:
        results.sort(key=lambda x: (x.get("rerank_score", -1.0), x["similarity"]), reverse=True)

    final = results[:top_k]

    if expand_context and final:
        expanded: list[dict] = []
        seen_ids = {it["id"] for it in final}
        doc_chunk_cache: dict[str, dict[int, dict]] = {}
        win = max(1, context_window)

        for it in final:
            did = it.get("knowledge_id") or ""
            if did and did not in doc_chunk_cache:
                doc_chunk_cache[did] = {
                    int(c.get("chunk_index") or 0): c for c in backend.list_chunks_for_doc(did)
                }
            cmap = doc_chunk_cache.get(did, {})
            cno = it["chunk_no"]

            for off in range(win, 0, -1):
                sib = cmap.get(cno - off)
                if sib:
                    ctx = normalize_hit(sib, doc_map, strip_header=strip_header, backend=backend)
                    if ctx["id"] not in seen_ids and ctx["text"].strip():
                        ctx["is_context"] = True
                        ctx["context_for_chunk"] = cno
                        expanded.append(ctx)
                        seen_ids.add(ctx["id"])

            it["is_context"] = False
            expanded.append(it)

            for off in range(1, win + 1):
                sib = cmap.get(cno + off)
                if sib:
                    ctx = normalize_hit(sib, doc_map, strip_header=strip_header, backend=backend)
                    if ctx["id"] not in seen_ids and ctx["text"].strip():
                        ctx["is_context"] = True
                        ctx["context_for_chunk"] = cno
                        expanded.append(ctx)
                        seen_ids.add(ctx["id"])
        final = expanded

    return final, ("; ".join(note_parts) if note_parts else None)


def extract_expansion_terms(wiki_hits: list[dict], local_wiki_dir: Path | None = None, limit: int = 30) -> list[str]:
    terms: list[str] = []
    labels = (
        "标题：",
        "命题：",
        "支撑：",
        "反对：",
        "限定：",
        "依赖：",
        "承接论证：",
        "理论来源：",
        "相关概念：",
        "相关人物：",
        "相关辨析：",
        "来源：",
        "正文链接：",
    )

    def add_term(val: str) -> None:
        t = val.strip().removeprefix("[[").removesuffix("]]")
        if "|" in t:
            t = t.split("|", 1)[-1].strip()
        if t and len(t) <= 80 and t not in terms:
            terms.append(t)

    for item in wiki_hits:
        if item.get("title"):
            add_term(str(item["title"]))
        text = str(item.get("text") or "")
        if local_wiki_dir and item.get("source_path"):
            local_card = local_wiki_dir / str(item["source_path"])
            if local_card.is_file():
                text = text + "\n" + local_card.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            for lb in labels:
                if line.startswith(lb):
                    val = line[len(lb) :].strip()
                    for part in val.replace("，", "、").split("、"):
                        add_term(part)
        for wl in re.findall(r"\[\[([^\]]+)\]\]", text):
            add_term(wl)
        if len(terms) >= limit:
            break
    return terms[:limit]


def extract_raw_evidence_paths(wiki_hits: list[dict], local_wiki_dir: Path | None = None) -> list[str]:
    paths: list[str] = []
    for item in wiki_hits:
        for sref in item.get("source_refs") or []:
            if "|" in str(sref):
                p = str(sref).split("|", 1)[1].strip()
                if p and p not in paths:
                    paths.append(p)
        text = str(item.get("text") or "")
        if local_wiki_dir and item.get("source_path"):
            local_card = local_wiki_dir / str(item["source_path"])
            if local_card.is_file():
                text = text + "\n" + local_card.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if line.startswith("来源："):
                for src in line[len("来源：") :].split("、"):
                    s = src.strip()
                    if s and s not in paths:
                        paths.append(s)
        for marker in ("证据位置：`", "evidence: `", "来源：`"):
            idx = 0
            while True:
                pos = text.find(marker, idx)
                if pos == -1:
                    break
                rest = text[pos + len(marker) :]
                raw = rest.split("`", 1)[0].strip()
                if raw and raw not in paths:
                    paths.append(raw)
                idx = pos + len(marker)
        for raw in re.findall(r"`([^`\n]+?\.(?:pdf|docx|epub|md|txt))(?:#[^`\n]*|:[^`\n]*)?`", text, flags=re.IGNORECASE):
            if raw not in paths:
                paths.append(raw)
    return paths


def normalize_evidence_path(path: str) -> str:
    cleaned = path.split("#", 1)[0].split(":", 1)[0].strip().removeprefix("./")
    return cleaned.removeprefix("wiki/raw/").removeprefix("raw/")


def _match_remote_key(target: str, remote_docs: dict[str, dict]) -> str | None:
    if target in remote_docs:
        return target
    t_name = Path(target).name
    t_stem = Path(target).stem
    for key in remote_docs:
        if Path(key).name == t_name or Path(key).stem == t_stem:
            return key
    return None


def boost_cited_raw_sources(
    backend,
    raw_manifest: dict,
    raw_hits: list[dict],
    evidence_paths: list[str],
    expanded_query: str,
    max_additions: int = 3,
) -> list[dict]:
    if not evidence_paths:
        return raw_hits
    remote_docs = raw_manifest.get("remote_docs") or {}
    targets: set[str] = set()
    for p in evidence_paths:
        if not p:
            continue
        norm = normalize_evidence_path(p)
        resolved = _match_remote_key(norm, remote_docs) or norm
        targets.add(resolved)

    hits = list(raw_hits)
    seen_ids = {it["id"] for it in hits}
    covered: set[str] = set()
    for it in hits:
        if it.get("source_path") in targets:
            it["wiki_evidence_boost"] = True
            covered.add(str(it["source_path"]))

    doc_map = map_doc_to_rel_path(raw_manifest)
    strip_header = raw_manifest.get("metadata_mode") == "enriched_raw"
    q_tokens = set(bm25_tokenize(expanded_query))
    added = 0

    for target in sorted(targets - covered):
        if added >= max_additions:
            break
        info = remote_docs.get(target)
        if not isinstance(info, dict) or not info.get("knowledge_id"):
            continue
        doc_id = str(info["knowledge_id"])
        chunks = backend.list_chunks_for_doc(doc_id)
        scored: list[tuple[int, dict]] = []
        for ch in chunks:
            norm = normalize_hit(ch, doc_map, strip_header=strip_header, backend=backend)
            if norm["id"] in seen_ids or not norm["text"].strip():
                continue
            lex = len(q_tokens & set(bm25_tokenize(norm["text"])))
            scored.append((lex, norm))
        scored.sort(key=lambda x: x[0], reverse=True)
        if scored and scored[0][0] > 0:
            lex_score, best = scored[0]
            best["wiki_evidence_boost"] = True
            best["wiki_evidence_lexical_score"] = lex_score
            hits.append(best)
            seen_ids.add(best["id"])
            added += 1
    return hits


def retrieve_wiki_first_local_karpathy(
    args: argparse.Namespace,
    backend,
    rerank_model_id: str | None,
) -> tuple[dict, list[dict], dict, list[dict], str, str | None]:
    if not args.wiki_index_dir or not args.raw_index_dir:
        raise SystemExit("--wiki-first in local_karpathy mode requires --wiki-index-dir and --raw-index-dir")
    wiki_manifest = load_manifest(args.wiki_index_dir)
    raw_manifest = load_manifest(args.raw_index_dir)
    local_wiki_dir = Path(wiki_manifest["md_dir"]) if wiki_manifest.get("md_dir") else None

    wiki_hits, wiki_note = retrieve_from_kb(
        backend=backend,
        manifest=wiki_manifest,
        query_text=args.question,
        top_k=args.wiki_top_k,
        candidates=max(args.wiki_top_k, args.candidates),
        rerank=False,
        rerank_model_id=None,
        multi_query=args.multi_query,
        expand_context=False,
        context_window=1,
    )
    terms = extract_expansion_terms(wiki_hits, local_wiki_dir=local_wiki_dir)
    expanded_query = args.question + ("\n" + "\n".join(terms) if terms else "")
    raw_top_k = args.candidates if args.source_discovery else args.top_k

    raw_hits, raw_note = retrieve_from_kb(
        backend=backend,
        manifest=raw_manifest,
        query_text=expanded_query,
        top_k=raw_top_k,
        candidates=max(args.candidates, raw_top_k),
        rerank=bool(args.rerank),
        rerank_model_id=rerank_model_id,
        multi_query=bool(args.multi_query),
        expand_context=bool(args.expand_context),
        context_window=args.context_window,
    )
    ev_paths = extract_raw_evidence_paths(wiki_hits, local_wiki_dir=local_wiki_dir)
    raw_hits = boost_cited_raw_sources(backend, raw_manifest, raw_hits, ev_paths, expanded_query)
    note = "; ".join(n for n in (wiki_note, raw_note) if n) or None
    return wiki_manifest, wiki_hits, raw_manifest, raw_hits, expanded_query, note


def retrieve_wiki_first_weknora_native(
    args: argparse.Namespace,
    backend,
    rerank_model_id: str | None,
) -> tuple[dict, list[dict], dict, list[dict], str, str | None]:
    raw_dir = args.raw_index_dir or args.index_dir
    if not raw_dir:
        raise SystemExit("--wiki-first in weknora_native mode requires --raw-index-dir (or --index-dir)")
    raw_manifest = load_manifest(raw_dir)
    kb_id = str(raw_manifest["kb_id"])

    pages = backend.wiki_search(kb_id=kb_id, query=args.question, limit=args.wiki_top_k)
    stats = backend.wiki_stats(kb_id)
    notes: list[str] = ["Wiki source: weknora_native (automated Web Wiki)"]
    if stats.get("is_active") or int(stats.get("pending_tasks") or 0) > 0:
        notes.append(f"WeKnora native Wiki ingestion still active (pending_tasks={stats.get('pending_tasks')})")

    wiki_hits: list[dict] = []
    for idx, p in enumerate(pages):
        body = str(p.get("content") or p.get("summary") or "")
        wiki_hits.append(
            {
                "id": str(p.get("id") or p.get("slug") or idx),
                "source_path": f"[weknora_wiki] {p.get('slug', '?')}",
                "title": p.get("title", ""),
                "chunk_no": 0,
                "similarity": 1.0,
                "text": f"标题：{p.get('title', '')}\n类型：{p.get('page_type', '')}\n摘要：{p.get('summary', '')}\n\n{body[:1200]}",
                "source_refs": p.get("source_refs") or [],
            }
        )

    terms = extract_expansion_terms(wiki_hits, local_wiki_dir=None)
    expanded_query = args.question + ("\n" + "\n".join(terms) if terms else "")
    raw_top_k = args.candidates if args.source_discovery else args.top_k

    raw_hits, raw_note = retrieve_from_kb(
        backend=backend,
        manifest=raw_manifest,
        query_text=expanded_query,
        top_k=raw_top_k,
        candidates=max(args.candidates, raw_top_k),
        rerank=bool(args.rerank),
        rerank_model_id=rerank_model_id,
        multi_query=bool(args.multi_query),
        expand_context=bool(args.expand_context),
        context_window=args.context_window,
    )
    if raw_note:
        notes.append(raw_note)
    ev_paths = extract_raw_evidence_paths(wiki_hits, local_wiki_dir=None)
    raw_hits = boost_cited_raw_sources(backend, raw_manifest, raw_hits, ev_paths, expanded_query)
    return raw_manifest, wiki_hits, raw_manifest, raw_hits, expanded_query, "; ".join(notes)


# ---------------------------------------------------------------------------
# Output formatters (compatible with social-science-km evidence templates)
# ---------------------------------------------------------------------------

def _format_source_display(item: dict) -> str:
    src = str(item.get("source_path") or "?")
    page = item.get("page")
    return f"{src}#{page}" if page else src


def print_evidence(question: str, manifest: dict, results: list[dict], note: str | None) -> None:
    print("# RAG Evidence")
    print()
    print(f"Question: {question}")
    print(f"WeKnora KB: {manifest.get('kb_name', '')} ({manifest.get('kb_id', '')})")
    print(f"Wiki mode: {manifest.get('wiki_mode', DEFAULT_WIKI_MODE)}")
    print(f"Embedding model: {manifest.get('embedding_model', '')}")
    if note:
        print(f"Note: {note}")
    print()
    if not results:
        print("No evidence found.")
        return
    for rank, item in enumerate(results, start=1):
        is_ctx = item.get("is_context")
        ctx_for = item.get("context_for_chunk")
        score = item.get("rerank_score", item.get("similarity"))
        score_name = "rerank" if "rerank_score" in item else "similarity"
        src_disp = _format_source_display(item)
        if is_ctx:
            print(f"## Evidence {rank} [context for chunk {ctx_for}]")
            print(f"- Source: {src_disp}")
            print(f"- Chunk: {item['chunk_no']}")
            print()
        else:
            print(f"## Evidence {rank}")
            print(f"- Source: {src_disp}")
            if item.get("page"):
                print(f"- Page: {item['page']}")
            print(f"- Chunk: {item['chunk_no']}")
            if item.get("wiki_evidence_boost"):
                print("- wiki_evidence_boost: true")
            if item.get("wiki_evidence_lexical_score"):
                print(f"- wiki_evidence_lexical_score: {item['wiki_evidence_lexical_score']}")
            print(f"- {score_name}: {score:.4f}" if isinstance(score, (int, float)) else f"- {score_name}: {score}")
            print()
        print(item["text"].strip())
        print()


def print_wiki_first_evidence(
    question: str,
    wiki_hits: list[dict],
    raw_manifest: dict,
    raw_hits: list[dict],
    expanded_query: str,
    note: str | None,
) -> None:
    print("# Wiki-Aware RAG Evidence")
    print()
    print(f"Question: {question}")
    if note:
        print(f"Note: {note}")
    print()
    print("# Wiki Hits")
    print()
    if not wiki_hits:
        print("No wiki hits found.")
        print()
    for rank, item in enumerate(wiki_hits, start=1):
        score = item.get("rerank_score", item.get("similarity"))
        print(f"## Wiki Hit {rank}")
        print(f"- Source: {item['source_path']}")
        print(f"- Chunk: {item['chunk_no']}")
        if isinstance(score, (int, float)):
            print(f"- similarity: {score:.4f}")
        print()
        print(item["text"].strip())
        print()
    print("# Expanded Query")
    print()
    print(expanded_query)
    print()
    print("# Raw Evidence")
    print()
    print_evidence(question, raw_manifest, raw_hits, None)


def raw_source_metrics(manifest: dict, source_path: str) -> tuple[int | None, int | None]:
    base_dir = manifest.get("source_dir") or manifest.get("md_dir")
    if not isinstance(base_dir, str) or not base_dir:
        return None, None
    source_file = Path(base_dir).expanduser() / source_path
    try:
        raw_bytes = source_file.stat().st_size
        if source_file.suffix.lower() in TEXT_SOURCE_EXTS:
            with source_file.open("r", encoding="utf-8", errors="replace") as handle:
                raw_lines = sum(1 for _ in handle)
        else:
            raw_lines = None
    except OSError:
        return None, None
    return raw_bytes, raw_lines


def size_gate(raw_bytes: int | None, raw_lines: int | None) -> str:
    if raw_bytes is None:
        return "unknown; inspect the source file before routing"
    if raw_bytes == 0:
        return "blocked; source file is empty or unreadable"
    if raw_lines is None:
        if raw_bytes >= 300 * 1024:
            return "large binary/PDF source; inspect material nature and context-loss risk before routing"
        return "inspect material nature and context-loss risk (binary/PDF source)"
    if raw_lines >= 500 or raw_bytes >= 100 * 1024:
        return "large; inspect material type and context-loss risk before routing"
    if raw_lines >= 200 or raw_bytes >= 40 * 1024:
        return "inspect material type and context-loss risk"
    return "short; direct-wiki only if narrow, self-contained and low-risk"


def matched_terms(question: str, text: str, limit: int = 8) -> list[str]:
    haystack = text.lower()
    terms: list[str] = []
    for tok in bm25_tokenize(question):
        cleaned = tok.strip().lower()
        if len(cleaned) < 2 or cleaned not in haystack or cleaned in terms:
            continue
        terms.append(cleaned)
        if len(terms) >= limit:
            break
    return terms


def print_source_discovery(
    question: str,
    raw_manifest: dict,
    raw_hits: list[dict],
    note: str | None,
    top_k: int,
    wiki_hits: list[dict] | None = None,
    expanded_query: str | None = None,
) -> None:
    print("# Source Discovery Shortlist")
    print()
    print(f"Question: {question}")
    if note:
        print(f"Note: {note}")
    if wiki_hits:
        print()
        print("## Wiki Recall Path")
        for item in wiki_hits:
            print(f"- {item.get('source_path', '?')} (chunk {item.get('chunk_no', '?')})")
    if expanded_query and expanded_query != question:
        print()
        print("## Expanded Query")
        print(expanded_query)

    grouped: dict[str, dict] = {}
    for item in raw_hits:
        if item.get("is_context"):
            continue
        sp = str(item.get("source_path", "")).strip()
        if not sp:
            continue
        score_name = "rerank_score" if "rerank_score" in item else "similarity"
        score = float(item.get(score_name) or 0.0)
        cand = grouped.get(sp)
        if cand is None:
            rb, rl = raw_source_metrics(raw_manifest, sp)
            grouped[sp] = {
                "source_path": sp,
                "matched_chunks": 1,
                "best_item": item,
                "score_name": score_name,
                "best_score": score,
                "raw_bytes": rb,
                "raw_lines": rl,
            }
        else:
            cand["matched_chunks"] += 1
            if score > cand["best_score"]:
                cand["best_item"] = item
                cand["score_name"] = score_name
                cand["best_score"] = score

    candidates = list(grouped.values())[:top_k]
    print()
    print("# Candidate Sources")
    if not candidates:
        print("No candidate sources found.")
        return

    for rank, cand in enumerate(candidates, start=1):
        rb, rl = cand["raw_bytes"], cand["raw_lines"]
        if rb is None:
            size_text = "unavailable"
        elif rl is None:
            size_text = f"{rb} bytes"
        else:
            size_text = f"{rl} lines, {rb} bytes"
        terms = matched_terms(question, str(cand["best_item"].get("text", "")))
        key_terms = "、".join(terms) or "no direct lexical overlap; retrieved semantically"
        excerpt = " ".join(str(cand["best_item"].get("text", "")).split())[:320]
        page_note = f" ({cand['best_item']['page']})" if cand["best_item"].get("page") else ""
        print()
        print(f"## Candidate Source {rank}")
        print(f"- Source: {cand['source_path']}{page_note}")
        print(f"- Matched chunks: {cand['matched_chunks']}")
        print(f"- Best {cand['score_name']}: {cand['best_score']:.4f}")
        print(f"- Key terms: {key_terms}")
        print(f"- Source size: {size_text}")
        print(f"- Size gate: {size_gate(rb, rl)}")
        print("- Next step: apply the social-science-km routing gate; document nature and context-loss risk override size")
        print("- Limits: this shortlist supports source selection, not final claims or citations")
        print(f"- Why relevant: {excerpt}")


def print_stats(manifest: dict, backend) -> None:
    kb_id = str(manifest.get("kb_id") or "")
    remote_docs = manifest.get("remote_docs") or {}
    file_hashes = manifest.get("file_hashes") or {}
    kb_info = backend.get_kb(kb_id) if kb_id else None
    server_docs = backend.list_docs(kb_id) if kb_id and kb_info else []

    issues: list[str] = []
    if not kb_info:
        issues.append(f"WeKnora KB {kb_id} not found on server")
    if len(remote_docs) != len(file_hashes):
        issues.append(f"remote_docs ({len(remote_docs)}) != file_hashes ({len(file_hashes)})")
    if kb_info and len(server_docs) < len(remote_docs):
        issues.append(f"server has {len(server_docs)} docs, manifest tracks {len(remote_docs)}")

    print("# Index Statistics")
    print()
    print(f"  Backend:         weknora (format v{manifest.get('format_version', 4)})")
    print(f"  Wiki mode:       {manifest.get('wiki_mode', DEFAULT_WIKI_MODE)}")
    print(f"  WeKnora KB:      {manifest.get('kb_name', '?')} ({kb_id})")
    print(f"  Files tracked:   {len(file_hashes)}")
    print(f"  Server docs:     {len(server_docs)}")
    print(f"  Metadata mode:   {manifest.get('metadata_mode', '?')}")
    print(f"  Embedding:       {manifest.get('embedding_model', '?')}")
    print(f"  Chunk size:      {manifest.get('chunk_size', '?')} chars (overlap {manifest.get('overlap', '?')})")
    print(f"  Synced at:       {manifest.get('created_at', '?')}")
    if manifest.get("wiki_mode") == "weknora_native" and kb_id and kb_info:
        wstats = backend.wiki_stats(kb_id)
        print(f"  Native Wiki:     {wstats.get('total_pages', 0)} pages (pending={wstats.get('pending_tasks', 0)})")
    print()
    print("## Health")
    if issues:
        print("  Status: WARN")
        for iss in issues:
            print(f"  - {iss}")
    else:
        print("  Status: OK")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Query WeKnora-backed RAG indexes and print evidence.")
    p.add_argument("--config", default=None, help="Optional JSON config file (weknora_config.json or rag_config.json)")
    p.add_argument("--project-root", default=None, help="Project root directory")
    p.add_argument("--wiki-mode", default=None, choices=sorted(VALID_WIKI_MODES), help="local_karpathy | weknora_native")
    p.add_argument("--index-dir", default=None, help="Manifest directory for single-KB query/stats")
    p.add_argument("--wiki-index-dir", default=None, help="Wiki manifest directory for local_karpathy --wiki-first")
    p.add_argument("--raw-index-dir", default=None, help="Raw manifest directory for --wiki-first")
    p.add_argument("--wiki-first", action="store_true", default=None, help="Retrieve wiki path first, then raw evidence")
    p.add_argument("--wiki-top-k", type=int, default=None, help="Wiki hits used for expansion")
    p.add_argument("--question", default=None, help="Question to retrieve evidence for")
    p.add_argument("--top-k", type=int, default=None, help="Evidence snippets to return")
    p.add_argument("--candidates", type=int, default=None, help="Candidate pool size before rerank")
    p.add_argument("--rerank", action="store_true", help="Enable WeKnora server-side rerank")
    p.add_argument("--rerank-model", default=None, help="Explicit WeKnora rerank model ID")
    p.add_argument("--timeout", type=int, default=None, help="Timeout in seconds")
    p.add_argument("--mock", action="store_true", help="Use offline mock WeKnora backend")
    p.add_argument("--expand-context", action="store_true", default=None, help="Include adjacent chunks from same doc")
    p.add_argument("--context-window", type=int, default=None, help="Adjacent chunks per side (default 1)")
    p.add_argument("--multi-query", action="store_true", default=None, help="Expand query into multiple formulations")
    p.add_argument("--no-multi-query", action="store_false", dest="multi_query", help="Disable multi-query")
    p.add_argument("--source-discovery", action="store_true", default=None, help="Aggregate hits by source file with size hints")
    p.add_argument("--stats", action="store_true", help="Print sync & WeKnora KB health statistics")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve() if args.project_root else Path.cwd().resolve()

    def _resolve_index_dir(value):
        if not value:
            return value
        p = Path(value).expanduser()
        return p if p.is_absolute() else (project_root / p).resolve()

    args.index_dir = _resolve_index_dir(args.index_dir)
    args.wiki_index_dir = _resolve_index_dir(args.wiki_index_dir)
    args.raw_index_dir = _resolve_index_dir(args.raw_index_dir)
    cfg_path = resolve_project_config_path(project_root, args.config)
    cfg = load_project_config(cfg_path)
    q_cfg = cfg["query"]
    weknora_cfg = cfg["weknora"]

    for key, default in QUERY_DEFAULTS.items():
        if getattr(args, key) is None:
            setattr(args, key, q_cfg.get(key, default))

    args.top_k = int(args.top_k)
    args.candidates = max(args.top_k, int(args.candidates))
    args.wiki_top_k = int(args.wiki_top_k)
    args.timeout = int(args.timeout)
    args.context_window = int(args.context_window)
    rerank_model_id = args.rerank_model or weknora_cfg.get("rerank_model_id")

    try:
        if args.stats:
            manifest = load_manifest(args.index_dir)
            backend = make_backend(weknora_cfg, project_root, mock=bool(args.mock or manifest.get("mock")), timeout=args.timeout)
            print_stats(manifest, backend)
            return

        if not args.question:
            raise SystemExit('Usage: query_kb.py --index-dir <dir> --question "..." [options]')

        if args.wiki_first:
            probe_dir = args.raw_index_dir or args.index_dir
            probe_manifest = load_manifest(probe_dir) if probe_dir else {}
            wiki_mode = args.wiki_mode or probe_manifest.get("wiki_mode") or cfg["wiki_mode"] or DEFAULT_WIKI_MODE
            use_mock = bool(args.mock or probe_manifest.get("mock"))
            backend = make_backend(weknora_cfg, project_root, mock=use_mock, timeout=args.timeout)

            if wiki_mode == "weknora_native":
                _, wiki_hits, raw_manifest, raw_hits, expanded_query, note = retrieve_wiki_first_weknora_native(
                    args, backend, rerank_model_id
                )
            else:
                _, wiki_hits, raw_manifest, raw_hits, expanded_query, note = retrieve_wiki_first_local_karpathy(
                    args, backend, rerank_model_id
                )

            if args.source_discovery:
                print_source_discovery(
                    args.question,
                    raw_manifest,
                    raw_hits,
                    note,
                    args.top_k,
                    wiki_hits=wiki_hits,
                    expanded_query=expanded_query,
                )
            else:
                print_wiki_first_evidence(args.question, wiki_hits, raw_manifest, raw_hits, expanded_query, note)
            return

        manifest = load_manifest(args.index_dir)
        use_mock = bool(args.mock or manifest.get("mock"))
        backend = make_backend(weknora_cfg, project_root, mock=use_mock, timeout=args.timeout)
        hits, note = retrieve_from_kb(
            backend=backend,
            manifest=manifest,
            query_text=args.question,
            top_k=args.candidates if args.source_discovery else args.top_k,
            candidates=args.candidates,
            rerank=bool(args.rerank),
            rerank_model_id=rerank_model_id,
            multi_query=bool(args.multi_query),
            expand_context=bool(args.expand_context),
            context_window=args.context_window,
        )
        if args.source_discovery:
            print_source_discovery(args.question, manifest, hits, note, args.top_k)
        else:
            print_evidence(args.question, manifest, hits, note)
    except WeKnoraError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(exc.exit_code) from exc


if __name__ == "__main__":
    main()
