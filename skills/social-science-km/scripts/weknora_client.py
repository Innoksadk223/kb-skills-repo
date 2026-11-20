#!/usr/bin/env python3
"""Shared WeKnora CLI / REST client, config loader, and offline mock backend.

Uses the Python 3 standard library only.
- Prefers the official ``weknora`` CLI when installed for auth discovery and wait.
- Uses stdlib ``urllib`` multipart / JSON against ``/api/v1`` for direct binary
  uploads (PDF/DOCX/EPUB/images) and structured hybrid retrieval.
- Supports ``--mock`` with a deterministic local JSON state store so self-tests
  verify both ``local_karpathy`` and ``weknora_native`` workflows offline,
  including direct PDF/source uploads without a local ``wiki/raw/`` Markdown layer.
"""

from __future__ import annotations

import hashlib
import json
import math
import mimetypes
import os
import re
import shutil
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

VALID_WIKI_MODES = {"local_karpathy", "weknora_native"}
DEFAULT_WIKI_MODE = "local_karpathy"
DEFAULT_HOST = "http://localhost:8080"

PRIVATE_CONFIG_PATH = Path.home() / ".hermes" / "private" / "weknora-rag" / "config.json"
KM_PRIVATE_CONFIG_PATH = Path.home() / ".hermes" / "private" / "social-science-km" / "config.json"
LEGACY_PRIVATE_CONFIG_PATH = Path.home() / ".codex" / "weknora-rag" / "config.json"

ENRICHED_HEADER_START = "<!-- KM_ENRICHED_HEADER_START -->"
ENRICHED_HEADER_END = "<!-- KM_ENRICHED_HEADER_END -->"
ENRICHED_HEADER_RE = re.compile(
    re.escape(ENRICHED_HEADER_START) + r".*?" + re.escape(ENRICHED_HEADER_END) + r"\s*",
    flags=re.DOTALL,
)

SUPPORTED_SOURCE_EXTS = {
    ".pdf",
    ".md",
    ".markdown",
    ".txt",
    ".docx",
    ".doc",
    ".pptx",
    ".ppt",
    ".xlsx",
    ".xls",
    ".csv",
    ".epub",
    ".html",
    ".htm",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}
TEXT_SOURCE_EXTS = {".md", ".markdown", ".txt", ".csv", ".html", ".htm"}

TOP_SECTIONS = {"wiki_mode", "source_dir", "weknora", "build", "query"}
WEKNORA_SECTION_KEYS = {
    "host",
    "profile",
    "kb_prefix",
    "embedding_model_id",
    "summary_model_id",
    "rerank_model_id",
    "wiki_granularity",
    "api_key_env",
    "api_key_file",
}
BUILD_SECTION_KEYS = {
    "source_dir",
    "md_dir",
    "index_dir",
    "model",
    "chunk_size",
    "overlap",
    "batch_size",
    "timeout",
    "sleep",
    "include_dirs",
    "exclude_dirs",
    "metadata_mode",
    "dimensions",
    "encoding_format",
}
QUERY_SECTION_KEYS = {
    "index_dir",
    "top_k",
    "candidates",
    "wiki_top_k",
    "embedding_model",
    "rerank_model",
    "timeout",
    "expand_context",
    "context_window",
    "wiki_index_dir",
    "raw_index_dir",
    "wiki_first",
    "multi_query",
    "source_discovery",
    "dimensions",
}


class WeKnoraError(RuntimeError):
    """Typed operational error from WeKnora CLI or HTTP API."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def strip_enriched_header(text: str) -> str:
    """Remove KM_ENRICHED_HEADER_START...END blocks so quotes stay verbatim."""
    return ENRICHED_HEADER_RE.sub("", text or "").lstrip("\r\n")


def wrap_enriched_header(header_lines: list[str], raw_text: str) -> str:
    block = "\n".join([ENRICHED_HEADER_START, *header_lines, ENRICHED_HEADER_END])
    return f"{block}\n\n{raw_text}"


def extract_page_label(row: dict) -> str | None:
    """Extract PDF/document page range (e.g. 'p.12' or 'p.12-13') from WeKnora source_locators."""
    locators = row.get("source_locators")
    if not isinstance(locators, list) or not locators:
        md = row.get("metadata")
        if isinstance(md, dict):
            locators = md.get("source_locators")
    if not isinstance(locators, list) or not locators:
        return None
    pages: list[int] = []
    for loc in locators:
        if not isinstance(loc, dict):
            continue
        p = loc.get("page")
        if isinstance(p, int) and p > 0 and p not in pages:
            pages.append(p)
    if not pages:
        return None
    pages.sort()
    if len(pages) == 1:
        return f"p.{pages[0]}"
    return f"p.{pages[0]}-{pages[-1]}"


def warn_if_private_config_too_open(config_path: Path) -> None:
    if os.name == "nt" or not config_path.exists():
        return
    try:
        mode = config_path.stat().st_mode
    except OSError:
        return
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        print(
            f"[warn] Private config {config_path} has group/other permissions; run: chmod 600 '{config_path}'",
            file=sys.stderr,
        )


def resolve_project_config_path(project_root: Path, explicit_config: str | None = None) -> Path | None:
    if explicit_config:
        path = Path(explicit_config).expanduser()
        if not path.exists():
            raise SystemExit(f"Config file not found: {path}")
        return path
    for name in ("weknora_config.json", "rag_config.json"):
        candidate = project_root / name
        if candidate.is_file():
            return candidate
    return None


def _normalize_dict_keys(data: dict, allowed: set[str], label: str) -> dict:
    out: dict = {}
    unknown: list[str] = []
    for k, v in data.items():
        nk = str(k).replace("-", "_")
        if nk in allowed:
            out[nk] = v
        else:
            unknown.append(str(k))
    if unknown:
        raise SystemExit(f"Unknown {label} config keys: {', '.join(sorted(unknown))}")
    return out


def load_project_config(config_file: str | Path | None) -> dict:
    """Load and validate weknora_config.json or legacy rag_config.json."""
    if not config_file:
        return {"wiki_mode": DEFAULT_WIKI_MODE, "source_dir": None, "weknora": {}, "build": {}, "query": {}}
    path = Path(config_file).expanduser()
    if not path.exists():
        raise SystemExit(f"RAG config file not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise SystemExit(f"Could not read config {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise SystemExit(f"Config must be a JSON object: {path}")

    allowed_top = TOP_SECTIONS | WEKNORA_SECTION_KEYS | BUILD_SECTION_KEYS | QUERY_SECTION_KEYS
    _normalize_dict_keys(raw, allowed_top, "top-level")

    wiki_mode = str(raw.get("wiki_mode") or DEFAULT_WIKI_MODE).strip()
    if wiki_mode not in VALID_WIKI_MODES:
        raise SystemExit(
            f"Invalid wiki_mode '{wiki_mode}' in {path}; expected one of: {', '.join(sorted(VALID_WIKI_MODES))}"
        )

    weknora_cfg: dict = {}
    build_cfg: dict = {}
    query_cfg: dict = {}
    top_source_dir = raw.get("source_dir")

    for k, v in raw.items():
        nk = str(k).replace("-", "_")
        if nk in TOP_SECTIONS:
            continue
        if nk in WEKNORA_SECTION_KEYS:
            weknora_cfg[nk] = v
        if nk in BUILD_SECTION_KEYS:
            build_cfg[nk] = v
        if nk in QUERY_SECTION_KEYS:
            query_cfg[nk] = v

    for sec_name, target, allowed in (
        ("weknora", weknora_cfg, WEKNORA_SECTION_KEYS),
        ("build", build_cfg, BUILD_SECTION_KEYS),
        ("query", query_cfg, QUERY_SECTION_KEYS),
    ):
        sec = raw.get(sec_name)
        if sec is not None:
            if not isinstance(sec, dict):
                raise SystemExit(f"Config key '{sec_name}' must be an object")
            target.update(_normalize_dict_keys(sec, allowed, sec_name))

    resolved_source_dir = top_source_dir or build_cfg.get("source_dir")
    return {
        "wiki_mode": wiki_mode,
        "source_dir": str(resolved_source_dir) if resolved_source_dir else None,
        "weknora": weknora_cfg,
        "build": build_cfg,
        "query": query_cfg,
    }


def resolve_credentials(weknora_cfg: dict) -> dict[str, str | None]:
    """Resolve host, api_key, bearer token, and CLI profile without storing secrets in project files."""
    host = os.environ.get("WEKNORA_HOST") or os.environ.get("WEKNORA_BASE_URL") or weknora_cfg.get("host")
    api_key_env = str(weknora_cfg.get("api_key_env") or "WEKNORA_API_KEY")
    api_key = os.environ.get(api_key_env) or os.environ.get("WEKNORA_API_KEY")
    token = os.environ.get("WEKNORA_TOKEN")
    profile = os.environ.get("WEKNORA_PROFILE") or weknora_cfg.get("profile")
    cred_source: str | None = "env" if (api_key or token) else None

    key_files: list[Path] = []
    if weknora_cfg.get("api_key_file"):
        key_files.append(Path(str(weknora_cfg["api_key_file"])).expanduser())
    key_files.extend([KM_PRIVATE_CONFIG_PATH, PRIVATE_CONFIG_PATH, LEGACY_PRIVATE_CONFIG_PATH])

    for kf in key_files:
        if not kf.is_file():
            continue
        warn_if_private_config_too_open(kf)
        try:
            priv = json.loads(kf.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(priv, dict):
            host = host or priv.get("WEKNORA_HOST") or priv.get("host")
            found_key = priv.get(api_key_env) or priv.get("WEKNORA_API_KEY") or priv.get("api_key")
            found_tok = priv.get("WEKNORA_TOKEN") or priv.get("token")
            if not api_key and found_key:
                api_key = found_key
                cred_source = str(kf)
            if not token and found_tok:
                token = found_tok
                cred_source = cred_source or str(kf)
            profile = profile or priv.get("WEKNORA_PROFILE") or priv.get("profile")
        if api_key or token:
            break

    cli_bin = shutil.which("weknora")
    if cli_bin and not api_key and not token:
        cmd = [cli_bin]
        if profile:
            cmd.extend(["--profile", str(profile)])
        cmd.extend(["auth", "token", "--format", "json"])
        proc = subprocess.run(cmd, text=True, capture_output=True, encoding="utf-8", errors="replace")
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                env_obj = json.loads(proc.stdout)
                data = env_obj.get("data") if isinstance(env_obj.get("data"), dict) else env_obj
                tok = data.get("token")
                mode = data.get("mode")
                if tok:
                    cred_source = "weknora_cli"
                    if mode == "api_key" or str(tok).startswith("sk-"):
                        api_key = str(tok)
                    else:
                        token = str(tok)
            except Exception:
                pass

    resolved_host = str(host or DEFAULT_HOST).rstrip("/")
    if resolved_host.endswith("/api/v1"):
        resolved_host = resolved_host[: -len("/api/v1")]

    return {
        "host": resolved_host,
        "api_key": str(api_key) if api_key else None,
        "token": str(token) if token else None,
        "profile": str(profile) if profile else None,
        "cli_bin": cli_bin,
        "cred_source": cred_source,
    }


# ---------------------------------------------------------------------------
# Lightweight tokenizer / vector helpers (used by offline mock & query utils)
# ---------------------------------------------------------------------------

def bm25_tokenize(text: str) -> list[str]:
    cleaned = re.sub(r"[^\w\u4e00-\u9fa5]", " ", (text or "").lower())
    tokens = [w for w in cleaned.split() if w]
    out: list[str] = []
    for t in tokens:
        if re.search(r"[\u4e00-\u9fa5]", t) and len(t) > 1:
            for i in range(len(t) - 1):
                out.append(t[i : i + 2])
        out.append(t)
    return out


def mock_vector(text: str, dim: int = 96) -> list[float]:
    vec = [0.0] * dim
    for tok in bm25_tokenize(text):
        digest = hashlib.sha256(tok.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:2], "big") % dim
        sign = 1.0 if digest[2] % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def cosine_sim(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


def split_chunks(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    norm = (text or "").replace("\r\n", "\n").strip()
    if not norm:
        return []
    overlap = max(0, min(overlap, chunk_size - 1))
    chunks: list[str] = []
    start = 0
    length = len(norm)
    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            nl = norm.rfind("\n\n", start, end)
            if nl > start + chunk_size // 2:
                end = nl
        piece = norm[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        start = max(start + 1, end - overlap)
    return chunks


def _extract_mock_text_from_bytes(data: bytes, file_name: str) -> tuple[str, list[tuple[int, str]]]:
    """Extract readable text from mock binary/PDF files for offline self-testing.

    Supports synthetic PDFs with ``%%PAGE N%%`` markers or UTF-8 text streams.
    Returns (full_text, [(page_num, page_text), ...]).
    """
    decoded = data.decode("utf-8", errors="ignore")
    # Strip PDF binary header lines if present while preserving embedded UTF-8 text
    lines = [
        ln for ln in decoded.splitlines()
        if not ln.startswith(("%PDF-", "%%EOF", "endobj", "stream", "endstream", "xref", "trailer"))
        and not re.match(r"^\d+\s+\d+\s+obj$", ln.strip())
    ]
    cleaned = "\n".join(lines).strip()
    if not cleaned:
        cleaned = f"# {Path(file_name).stem}\n\nMock parsed document content for {file_name}."

    page_splits = re.split(r"%%PAGE\s+(\d+)%%", cleaned)
    if len(page_splits) > 1:
        pages: list[tuple[int, str]] = []
        for idx in range(1, len(page_splits), 2):
            pno = int(page_splits[idx])
            ptxt = page_splits[idx + 1].strip()
            if ptxt:
                pages.append((pno, ptxt))
        full = "\n\n".join(ptxt for _, ptxt in pages)
        return full, pages
    return cleaned, [(1, cleaned)]


# ---------------------------------------------------------------------------
# Stateful Mock Backend (simulates WeKnora Server for --mock / self_test.py)
# ---------------------------------------------------------------------------

class MockWeKnoraBackend:
    """Simulates WeKnora KBs, binary/text documents, PDF page locators, RRF search, and native Wiki."""

    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        if self.state_file.exists():
            self.state = json.loads(self.state_file.read_text(encoding="utf-8"))
        else:
            self.state = {
                "models": [
                    {"id": "emb-mock-qwen3", "name": "Qwen/Qwen3-Embedding-8B", "type": "Embedding", "is_default": True},
                    {"id": "qa-mock-llm", "name": "Mock-QA-LLM", "type": "KnowledgeQA", "is_default": True},
                    {"id": "rr-mock-rerank", "name": "Qwen/Qwen3-Reranker-8B", "type": "Rerank", "is_default": True},
                ],
                "parser_engines": [
                    {"Name": "builtin", "Description": "内置文档解析器 (docreader)", "Available": True, "FileTypes": ["pdf", "docx", "epub", "md", "txt"]},
                    {"Name": "mineru_cloud", "Description": "MinerU 云服务高精度解析", "Available": True, "FileTypes": ["pdf", "png", "jpg"]},
                ],
                "kbs": {},
                "docs": {},
                "chunks": {},
                "wiki_pages": {},
            }
            self._save()

    def _save(self) -> None:
        self.state_file.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")

    def check_health(self) -> dict:
        return {"status": "ok", "mock": True}

    def list_parser_engines(self) -> list[dict]:
        return list(self.state.get("parser_engines") or [])

    def list_models(self) -> list[dict]:
        return list(self.state["models"])

    def list_kbs(self) -> list[dict]:
        return list(self.state["kbs"].values())

    def get_kb(self, kb_id: str) -> dict | None:
        return self.state["kbs"].get(kb_id)

    def create_kb(self, payload: dict) -> dict:
        kb_id = f"kb_{uuid.uuid4().hex[:10]}"
        kb = {
            "id": kb_id,
            "name": payload["name"],
            "description": payload.get("description", ""),
            "type": payload.get("type", "document"),
            "embedding_model_id": payload.get("embedding_model_id") or "emb-mock-qwen3",
            "summary_model_id": payload.get("summary_model_id") or "qa-mock-llm",
            "chunking_config": payload.get("chunking_config") or {"chunk_size": 1000, "chunk_overlap": 200},
            "indexing_strategy": payload.get("indexing_strategy")
            or {"vector_enabled": True, "keyword_enabled": True, "wiki_enabled": False, "graph_enabled": False},
            "wiki_config": payload.get("wiki_config") or {"auto_generate": False, "extraction_granularity": "standard"},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.state["kbs"][kb_id] = kb
        self._save()
        return kb

    def patch_kb(self, kb_id: str, payload: dict) -> dict:
        kb = self.state["kbs"].get(kb_id)
        if not kb:
            raise WeKnoraError(f"KB not found: {kb_id}", exit_code=4)
        for k, v in payload.items():
            if isinstance(v, dict) and isinstance(kb.get(k), dict):
                kb[k].update(v)
            else:
                kb[k] = v
        self._save()
        return kb

    def upload_file(
        self,
        kb_id: str,
        content: str | bytes,
        rel_file_name: str,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> dict:
        kb = self.state["kbs"].get(kb_id)
        if not kb:
            raise WeKnoraError(f"KB not found: {kb_id}", exit_code=4)
        doc_id = f"doc_{uuid.uuid4().hex[:10]}"
        parts = rel_file_name.replace("\\", "/").split("/")
        folder_path = "/".join(parts[:-1])
        base_name = parts[-1]
        ext = Path(base_name).suffix.lower()
        c_cfg = kb.get("chunking_config") or {}
        cs = int(c_cfg.get("chunk_size") or chunk_size or 1000)
        ov = int(c_cfg.get("chunk_overlap") or overlap or 200)

        raw_bytes = content.encode("utf-8") if isinstance(content, str) else content
        file_hash = hashlib.sha256(raw_bytes).hexdigest()

        if isinstance(content, bytes) and ext not in TEXT_SOURCE_EXTS:
            parsed_text, page_blocks = _extract_mock_text_from_bytes(content, base_name)
        else:
            parsed_text = content if isinstance(content, str) else content.decode("utf-8", errors="replace")
            page_blocks = []

        doc = {
            "id": doc_id,
            "kb_id": kb_id,
            "title": rel_file_name,
            "file_name": base_name,
            "file_type": ext.lstrip(".") or "md",
            "file_size": len(raw_bytes),
            "file_hash": file_hash,
            "folder_path": folder_path,
            "rel_path": rel_file_name,
            "parse_status": "completed",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.state["docs"][doc_id] = doc

        chunk_ids: list[str] = []
        idx = 0
        if page_blocks and ext == ".pdf":
            for pno, ptxt in page_blocks:
                for ch_text in split_chunks(ptxt, cs, ov):
                    cid = f"chk_{doc_id}_{idx}"
                    self.state["chunks"][cid] = {
                        "id": cid,
                        "kb_id": kb_id,
                        "knowledge_id": doc_id,
                        "knowledge_title": rel_file_name,
                        "chunk_index": idx,
                        "content": ch_text,
                        "chunk_type": "text",
                        "source_locators": [{"type": "pdf", "mapping": "exact", "page": pno}],
                        "vector": mock_vector(ch_text),
                    }
                    chunk_ids.append(cid)
                    idx += 1
        else:
            for ch_text in split_chunks(parsed_text, cs, ov):
                cid = f"chk_{doc_id}_{idx}"
                self.state["chunks"][cid] = {
                    "id": cid,
                    "kb_id": kb_id,
                    "knowledge_id": doc_id,
                    "knowledge_title": rel_file_name,
                    "chunk_index": idx,
                    "content": ch_text,
                    "chunk_type": "text",
                    "vector": mock_vector(ch_text),
                }
                chunk_ids.append(cid)
                idx += 1

        idx_strat = kb.get("indexing_strategy") or {}
        w_cfg = kb.get("wiki_config") or {}
        if idx_strat.get("wiki_enabled") and w_cfg.get("auto_generate", True):
            self._auto_ingest_native_wiki(kb_id, doc_id, rel_file_name, parsed_text, chunk_ids)

        self._save()
        return doc

    def upload_file_path(
        self,
        kb_id: str,
        file_path: Path,
        rel_file_name: str,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> dict:
        return self.upload_file(kb_id, file_path.read_bytes(), rel_file_name, chunk_size=chunk_size, overlap=overlap)

    def _auto_ingest_native_wiki(self, kb_id: str, doc_id: str, title: str, content: str, chunk_ids: list[str]) -> None:
        pages = self.state["wiki_pages"].setdefault(kb_id, {})
        clean = strip_enriched_header(content)
        headings = re.findall(r"^#{1,3}\s+(.+)$", clean, flags=re.MULTILINE)
        first_para = next((p.strip() for p in clean.split("\n\n") if p.strip() and not p.strip().startswith("#")), clean[:160])
        sum_slug = f"summary/{doc_id}"
        pages[sum_slug] = {
            "id": f"wp_{uuid.uuid4().hex[:8]}",
            "knowledge_base_id": kb_id,
            "slug": sum_slug,
            "title": f"{Path(title).stem} 摘要",
            "page_type": "summary",
            "status": "published",
            "summary": first_para[:120],
            "content": f"# {Path(title).stem}\n\n{first_para}\n",
            "source_refs": [f"{doc_id}|{title}"],
            "chunk_refs": chunk_ids[:3],
            "out_links": [],
            "in_links": [],
            "version": 1,
        }
        for h in headings[:6]:
            term = re.sub(r"[#*`\[\]]", "", h).strip()
            if not term or len(term) > 40:
                continue
            slug_key = re.sub(r"[^a-z0-9\u4e00-\u9fa5]+", "-", term.lower()).strip("-")
            slug = f"concept/{slug_key}"
            existing = pages.get(slug)
            if existing:
                if f"{doc_id}|{title}" not in existing["source_refs"]:
                    existing["source_refs"].append(f"{doc_id}|{title}")
                existing["content"] += f"\n\n补充（来自 {title}）：{first_para[:160]}"
                existing["version"] += 1
            else:
                pages[slug] = {
                    "id": f"wp_{uuid.uuid4().hex[:8]}",
                    "knowledge_base_id": kb_id,
                    "slug": slug,
                    "title": term,
                    "page_type": "concept",
                    "status": "published",
                    "summary": f"{term}：{first_para[:80]}",
                    "content": f"# {term}\n\n标题：{term}\n相关概念：{term}\n来源：{title}\n\n{clean[:400]}",
                    "source_refs": [f"{doc_id}|{title}"],
                    "chunk_refs": chunk_ids[:2],
                    "out_links": [sum_slug],
                    "in_links": [],
                    "version": 1,
                }
            if slug not in pages[sum_slug]["out_links"]:
                pages[sum_slug]["out_links"].append(slug)

    def delete_doc(self, doc_id: str) -> None:
        doc = self.state["docs"].pop(doc_id, None)
        if not doc:
            return
        to_del = [cid for cid, c in self.state["chunks"].items() if c["knowledge_id"] == doc_id]
        for cid in to_del:
            self.state["chunks"].pop(cid, None)
        kb_pages = self.state["wiki_pages"].get(doc["kb_id"], {})
        kb_pages.pop(f"summary/{doc_id}", None)
        self._save()

    def list_docs(self, kb_id: str) -> list[dict]:
        return [d for d in self.state["docs"].values() if d["kb_id"] == kb_id]

    def wait_docs(self, doc_ids: list[str], timeout_sec: int = 180) -> dict:
        completed = [d for d in doc_ids if d in self.state["docs"]]
        failed = [d for d in doc_ids if d not in self.state["docs"]]
        return {"completed": completed, "failed": failed, "timeout": []}

    def list_chunks_for_doc(self, doc_id: str) -> list[dict]:
        rows = [c for c in self.state["chunks"].values() if c["knowledge_id"] == doc_id]
        rows.sort(key=lambda r: r["chunk_index"])
        return [{k: v for k, v in r.items() if k != "vector"} for r in rows]

    def hybrid_search(
        self,
        kb_id: str,
        query_text: str,
        match_count: int = 12,
        rerank: bool = False,
        rerank_model_id: str | None = None,
    ) -> tuple[list[dict], dict]:
        pool = [c for c in self.state["chunks"].values() if c["kb_id"] == kb_id]
        if not pool:
            return [], {"applied": False, "outcome": "no_candidates"}

        q_vec = mock_vector(query_text)
        q_tokens = bm25_tokenize(query_text)
        doc_tokens_list = [bm25_tokenize(c["content"]) for c in pool]
        avgdl = (sum(len(dt) for dt in doc_tokens_list) / len(doc_tokens_list)) or 1.0

        df: Counter[str] = Counter()
        for dt in doc_tokens_list:
            for tok in set(dt):
                df[tok] += 1
        n_docs = len(pool)
        idf = {tok: math.log(1 + (n_docs - freq + 0.5) / (freq + 0.5)) for tok, freq in df.items()}

        vec_scored: list[tuple[float, str]] = []
        kw_scored: list[tuple[float, str]] = []

        for c, dt in zip(pool, doc_tokens_list):
            v_score = cosine_sim(q_vec, c["vector"])
            vec_scored.append((v_score, c["id"]))

            tf = Counter(dt)
            b_score = 0.0
            for tok in q_tokens:
                if tok in tf:
                    f = tf[tok]
                    b_score += idf.get(tok, 0.0) * (f * 2.5) / (f + 1.5 * (0.25 + 0.75 * len(dt) / avgdl))
            if b_score > 0:
                kw_scored.append((b_score, c["id"]))

        vec_scored.sort(reverse=True)
        kw_scored.sort(reverse=True)
        vec_rank = {cid: r for r, (_, cid) in enumerate(vec_scored, start=1)}
        kw_rank = {cid: r for r, (_, cid) in enumerate(kw_scored, start=1)}
        vec_map = {cid: s for s, cid in vec_scored}

        chunk_map = {c["id"]: c for c in pool}
        fused: list[dict] = []
        for cid, c in chunk_map.items():
            vr = vec_rank.get(cid)
            kr = kw_rank.get(cid)
            rrf = (0.7 / (60 + vr) if vr else 0.0) + (0.3 / (60 + kr) if kr else 0.0)
            norm_score = rrf / (1.0 / 61.0)
            item = {
                "id": cid,
                "knowledge_id": c["knowledge_id"],
                "knowledge_title": c["knowledge_title"],
                "chunk_index": c["chunk_index"],
                "content": c["content"],
                "score": round(max(norm_score, vec_map.get(cid, 0.0) * 0.5), 4),
                "match_type": "hybrid" if kr else "vector",
                "chunk_type": "text",
                "source_locators": c.get("source_locators") or [],
            }
            if rerank:
                overlap_cnt = len(set(q_tokens) & set(bm25_tokenize(c["content"])))
                model_score = min(1.0, 0.25 + 0.12 * overlap_cnt + 0.4 * max(0.0, vec_map.get(cid, 0.0)))
                item["rerank_score"] = round(0.6 * model_score + 0.4 * item["score"], 4)
            fused.append(item)

        sort_key = "rerank_score" if rerank else "score"
        fused.sort(key=lambda x: x.get(sort_key, 0.0), reverse=True)
        meta = {"applied": bool(rerank), "outcome": "ok" if fused else "no_candidates"}
        return fused[:match_count], meta

    def wiki_search(self, kb_id: str, query: str, limit: int = 8) -> list[dict]:
        pages = list(self.state["wiki_pages"].get(kb_id, {}).values())
        if not pages:
            return []
        q_tokens = set(bm25_tokenize(query))
        scored: list[tuple[int, dict]] = []
        for p in pages:
            hay = f"{p['title']} {p.get('summary', '')} {p.get('content', '')}"
            overlap = len(q_tokens & set(bm25_tokenize(hay)))
            if overlap > 0 or query.lower() in hay.lower():
                scored.append((overlap + (3 if query in p["title"] else 0), p))
        if not scored:
            scored = [(1, p) for p in pages[:limit]]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:limit]]

    def wiki_stats(self, kb_id: str) -> dict:
        pages = list(self.state["wiki_pages"].get(kb_id, {}).values())
        by_type: Counter[str] = Counter(p["page_type"] for p in pages)
        return {
            "total_pages": len(pages),
            "pages_by_type": dict(by_type),
            "pending_tasks": 0,
            "is_active": False,
        }


# ---------------------------------------------------------------------------
# Live WeKnora Client (CLI + REST API v1)
# ---------------------------------------------------------------------------

class LiveWeKnoraClient:
    """Drives a real WeKnora server via `/api/v1` HTTP endpoints (and optional `weknora` CLI)."""

    def __init__(self, creds: dict[str, str | None], timeout: int = 90) -> None:
        self.host = str(creds["host"]).rstrip("/")
        self.api_key = creds.get("api_key")
        self.token = creds.get("token")
        self.profile = creds.get("profile")
        self.cli_bin = creds.get("cli_bin")
        self.timeout = timeout

        if not self.api_key and not self.token and not self.cli_bin:
            raise WeKnoraError(
                "Missing WeKnora credentials. Set WEKNORA_HOST + WEKNORA_API_KEY (or WEKNORA_TOKEN), "
                f"save them in {PRIVATE_CONFIG_PATH} (chmod 600), or run `doctor.py` for setup instructions.",
                exit_code=3,
            )

    def _auth_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        elif self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _cli_env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["WEKNORA_HOST"] = self.host
        if self.api_key:
            env["WEKNORA_API_KEY"] = self.api_key
        elif self.token:
            env["WEKNORA_TOKEN"] = self.token
        return env

    def _run_cli_json(self, args: list[str], stdin_text: str | None = None) -> dict:
        if not self.cli_bin:
            raise WeKnoraError("weknora CLI binary not installed on PATH", exit_code=1)
        cmd = [self.cli_bin]
        if self.profile:
            cmd.extend(["--profile", self.profile])
        cmd.extend(args)
        if "--format" not in args:
            cmd.extend(["--format", "json"])
        proc = subprocess.run(
            cmd,
            input=stdin_text,
            text=True,
            capture_output=True,
            env=self._cli_env(),
            timeout=self.timeout,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode == 10:
            raise WeKnoraError(
                f"WeKnora exit-10 confirmation required; halting for user approval: {proc.stderr.strip()}",
                exit_code=10,
            )
        if proc.returncode != 0:
            raise WeKnoraError(
                f"weknora {' '.join(args[:3])} failed (exit {proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}",
                exit_code=proc.returncode,
            )
        return json.loads(proc.stdout) if proc.stdout.strip() else {"ok": True}

    def _http_json(self, method: str, api_path: str, body: dict | None = None) -> dict:
        if not self.api_key and not self.token and self.cli_bin:
            stdin_payload = json.dumps(body, ensure_ascii=False) if body is not None else None
            cli_args = ["api", "-X", method, api_path]
            if stdin_payload is not None:
                cli_args.extend(["--input", "-"])
            env_resp = self._run_cli_json(cli_args, stdin_text=stdin_payload)
            return env_resp.get("data") if isinstance(env_resp.get("data"), dict) and "success" in env_resp.get("data", {}) else env_resp

        url = f"{self.host}{api_path}"
        headers = self._auth_headers()
        raw_body: bytes | None = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            raw_body = json.dumps(body, ensure_ascii=False).encode("utf-8")

        req = urllib.request.Request(url, data=raw_body, headers=headers, method=method)
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    text = resp.read().decode("utf-8", errors="replace")
                    return json.loads(text) if text.strip() else {"success": True}
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                if exc.code in (429, 502, 503, 504) and attempt < 2:
                    time.sleep(1.5 * (2**attempt))
                    continue
                code = 3 if exc.code in (401, 403) else (4 if exc.code == 404 else 1)
                raise WeKnoraError(f"WeKnora HTTP {exc.code} {method} {api_path}: {detail}", exit_code=code) from exc
            except urllib.error.URLError as exc:
                if attempt < 2:
                    time.sleep(1.5 * (2**attempt))
                    continue
                raise WeKnoraError(f"WeKnora connection error ({self.host}): {exc.reason}", exit_code=7) from exc
        raise WeKnoraError(f"WeKnora request retries exhausted: {method} {api_path}", exit_code=7)

    @staticmethod
    def _unwrap_list(resp: dict | list) -> list[dict]:
        if isinstance(resp, list):
            return resp
        data = resp.get("data")
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            return data["data"]
        return []

    @staticmethod
    def _unwrap_obj(resp: dict) -> dict:
        data = resp.get("data")
        if isinstance(data, dict):
            if "data" in data and isinstance(data["data"], dict) and "id" in data["data"]:
                return data["data"]
            return data
        return resp

    def check_health(self) -> dict:
        url = f"{self.host}/health"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=min(self.timeout, 10)) as resp:
                text = resp.read().decode("utf-8", errors="replace")
                return json.loads(text) if text.strip() else {"status": "ok"}
        except Exception as exc:
            raise WeKnoraError(f"Health check failed ({url}): {exc}", exit_code=7) from exc

    def list_parser_engines(self) -> list[dict]:
        return self._unwrap_list(self._http_json("GET", "/api/v1/system/parser-engines"))

    def list_models(self) -> list[dict]:
        return self._unwrap_list(self._http_json("GET", "/api/v1/models"))

    def list_kbs(self) -> list[dict]:
        return self._unwrap_list(self._http_json("GET", "/api/v1/knowledge-bases?page=1&page_size=100"))

    def get_kb(self, kb_id: str) -> dict | None:
        try:
            return self._unwrap_obj(self._http_json("GET", f"/api/v1/knowledge-bases/{kb_id}"))
        except WeKnoraError as exc:
            if exc.exit_code == 4:
                return None
            raise

    def create_kb(self, payload: dict) -> dict:
        return self._unwrap_obj(self._http_json("POST", "/api/v1/knowledge-bases", payload))

    def patch_kb(self, kb_id: str, payload: dict) -> dict:
        return self._unwrap_obj(self._http_json("PATCH", f"/api/v1/knowledge-bases/{kb_id}", payload))

    def _multipart_upload(
        self,
        kb_id: str,
        file_bytes: bytes,
        rel_file_name: str,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> dict:
        boundary = f"----WeKnoraBoundary{uuid.uuid4().hex}"
        process_cfg = json.dumps(
            {
                "summary_enabled": False,
                "chunking_config": {"chunk_size": chunk_size, "chunk_overlap": overlap},
            },
            ensure_ascii=False,
        )
        parts: list[bytes] = []

        def add_field(name: str, val: str) -> None:
            parts.append(f"--{boundary}\r\n".encode("utf-8"))
            parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
            parts.append(val.encode("utf-8") + b"\r\n")

        add_field("fileName", rel_file_name)
        add_field("enable_multimodel", "false")
        add_field("process_config", process_cfg)

        mime = mimetypes.guess_type(rel_file_name)[0] or "application/octet-stream"
        parts.append(f"--{boundary}\r\n".encode("utf-8"))
        parts.append(
            f'Content-Disposition: form-data; name="file"; filename="{Path(rel_file_name).name}"\r\n'
            f"Content-Type: {mime}\r\n\r\n".encode("utf-8")
        )
        parts.append(file_bytes + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode("utf-8"))
        body = b"".join(parts)

        url = f"{self.host}/api/v1/knowledge-bases/{kb_id}/knowledge/file"
        headers = self._auth_headers()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return self._unwrap_obj(json.loads(resp.read().decode("utf-8", errors="replace")))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code == 409:
                try:
                    parsed = json.loads(detail)
                    if isinstance(parsed.get("data"), dict) and parsed["data"].get("id"):
                        return parsed["data"]
                except Exception:
                    pass
            raise WeKnoraError(f"Upload failed ({rel_file_name}): HTTP {exc.code} {detail}", exit_code=1) from exc

    def upload_file(
        self,
        kb_id: str,
        content: str | bytes,
        rel_file_name: str,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> dict:
        raw_bytes = content.encode("utf-8") if isinstance(content, str) else content
        return self._multipart_upload(kb_id, raw_bytes, rel_file_name, chunk_size=chunk_size, overlap=overlap)

    def upload_file_path(
        self,
        kb_id: str,
        file_path: Path,
        rel_file_name: str,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> dict:
        return self._multipart_upload(kb_id, file_path.read_bytes(), rel_file_name, chunk_size=chunk_size, overlap=overlap)

    def delete_doc(self, doc_id: str) -> None:
        try:
            self._http_json("DELETE", f"/api/v1/knowledge/{doc_id}")
        except WeKnoraError as exc:
            if exc.exit_code != 4:
                raise

    def list_docs(self, kb_id: str) -> list[dict]:
        out: list[dict] = []
        page = 1
        while True:
            resp = self._http_json("GET", f"/api/v1/knowledge-bases/{kb_id}/knowledge?page={page}&page_size=100")
            items = self._unwrap_list(resp)
            out.extend(items)
            total = int(resp.get("total") or len(out))
            if not items or len(out) >= total:
                break
            page += 1
        return out

    def wait_docs(self, doc_ids: list[str], timeout_sec: int = 240) -> dict:
        if not doc_ids:
            return {"completed": [], "failed": [], "timeout": []}
        if self.cli_bin:
            completed: list[str] = []
            failed: list[str] = []
            timed_out: list[str] = []
            for idx in range(0, len(doc_ids), 10):
                batch = doc_ids[idx : idx + 10]
                cmd = [self.cli_bin]
                if self.profile:
                    cmd.extend(["--profile", self.profile])
                cmd.extend(["doc", "wait", *batch, "--timeout", f"{timeout_sec}s", "--format", "json"])
                proc = subprocess.run(cmd, text=True, capture_output=True, env=self._cli_env(), encoding="utf-8", errors="replace")
                if proc.stdout.strip():
                    try:
                        data = json.loads(proc.stdout).get("data") or {}
                        completed.extend(data.get("completed") or [])
                        failed.extend(data.get("failed") or [])
                        timed_out.extend(data.get("timeout") or [])
                        continue
                    except Exception:
                        pass
                if proc.returncode == 0:
                    completed.extend(batch)
                elif proc.returncode == 124:
                    timed_out.extend(batch)
                else:
                    failed.extend(batch)
            return {"completed": completed, "failed": failed, "timeout": timed_out}

        deadline = time.time() + timeout_sec
        pending = set(doc_ids)
        completed = []
        failed = []
        while pending and time.time() < deadline:
            q = "&".join(f"ids={urllib.parse.quote(i)}" for i in sorted(pending)[:40])
            resp = self._http_json("GET", f"/api/v1/knowledge/batch?{q}")
            for row in self._unwrap_list(resp):
                did = str(row.get("id") or "")
                st = str(row.get("parse_status") or "")
                if st == "completed":
                    pending.discard(did)
                    completed.append(did)
                elif st == "failed":
                    pending.discard(did)
                    failed.append(did)
            if pending:
                time.sleep(1.5)
        return {"completed": completed, "failed": failed, "timeout": sorted(pending)}

    def list_chunks_for_doc(self, doc_id: str) -> list[dict]:
        out: list[dict] = []
        page = 1
        while True:
            resp = self._http_json("GET", f"/api/v1/chunks/{doc_id}?page={page}&page_size=100")
            items = self._unwrap_list(resp)
            out.extend(items)
            total = int(resp.get("total") or len(out))
            if not items or len(out) >= total:
                break
            page += 1
        out.sort(key=lambda r: int(r.get("chunk_index") or 0))
        return out

    def hybrid_search(
        self,
        kb_id: str,
        query_text: str,
        match_count: int = 12,
        rerank: bool = False,
        rerank_model_id: str | None = None,
    ) -> tuple[list[dict], dict]:
        payload: dict = {
            "query_text": query_text,
            "match_count": match_count,
            "skip_context_enrichment": True,
        }
        if rerank:
            rr_obj: dict = {"enabled": True, "top_k": match_count}
            if rerank_model_id:
                rr_obj["model_id"] = rerank_model_id
            payload["rerank"] = rr_obj
        resp = self._http_json("POST", f"/api/v1/knowledge-bases/{kb_id}/hybrid-search", payload)
        items = self._unwrap_list(resp)
        meta = (resp.get("meta") or {}).get("rerank") or {}
        for row in items:
            md = row.get("metadata") or {}
            if rerank and "model_score" in md and "rerank_score" not in row:
                row["rerank_score"] = row.get("score")
        return items, meta

    def wiki_search(self, kb_id: str, query: str, limit: int = 8) -> list[dict]:
        q_enc = urllib.parse.quote(query)
        resp = self._http_json("GET", f"/api/v1/knowledgebase/{kb_id}/wiki/search?q={q_enc}&limit={limit}")
        pages = resp.get("pages") if isinstance(resp, dict) else None
        if isinstance(pages, list):
            return pages
        return self._unwrap_list(resp)

    def wiki_stats(self, kb_id: str) -> dict:
        return self._unwrap_obj(self._http_json("GET", f"/api/v1/knowledgebase/{kb_id}/wiki/stats"))


def make_backend(weknora_cfg: dict, project_root: Path, mock: bool = False, timeout: int = 90):
    if mock:
        mock_state = Path(os.environ.get("WEKNORA_MOCK_STATE") or (project_root / "检索索引" / "_mock_weknora_server.json"))
        return MockWeKnoraBackend(mock_state)
    creds = resolve_credentials(weknora_cfg)
    return LiveWeKnoraClient(creds, timeout=timeout)
