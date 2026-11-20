#!/usr/bin/env python3
"""Sync original source documents or local Wiki cards into WeKnora knowledge bases.

Supports two selectable Wiki modes:
- ``local_karpathy`` (default): our social-science ``karpathy-wiki`` Markdown cards
  + Dual WeKnora KBs (``<project>-raw`` for original PDFs/docs, ``<project>-wiki``
  for typed claims/concepts/debates visible in WeKnora Web UI), server auto-wiki OFF.
- ``weknora_native`` (optional): WeKnora's built-in automated Web Wiki + Single
  WeKnora KB (``<project>-raw`` with ``indexing_strategy.wiki_enabled=true``).

New projects upload original files directly from ``--source-dir <资料夹>`` (PDF,
DOCX, EPUB, MD, TXT, images) without generating a local ``wiki/raw/*.md`` layer.
Existing projects with ``wiki/raw/*.md`` remain 100% compatible via ``--md-dir``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from weknora_client import (  # noqa: E402
    DEFAULT_WIKI_MODE,
    SUPPORTED_SOURCE_EXTS,
    TEXT_SOURCE_EXTS,
    VALID_WIKI_MODES,
    WeKnoraError,
    load_project_config,
    make_backend,
    resolve_project_config_path,
    wrap_enriched_header,
)

SKIP_NAMES = {
    "_conversion_failures.md",
    "_conversion_manifest.md",
    "_source_manifest.md",
    "_主题索引.md",
}
WIKI_SKIP_NAMES = {
    "index.md",
    "log.md",
    "SCHEMA.md",
}
RAW_SEMANTIC_SOURCE_DIRS = (
    "claims",
    "concepts",
    "comparisons",
    "entities",
    "debates",
    "observations",
    "structures",
    "predicts",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").lstrip("\ufeff")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".md", ".markdown", ".txt"}:
        return sha256_text(read_text(path))
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw_fm = text[4:end]
    body = text[end + 5 :]
    meta: dict = {}
    current_list_key: str | None = None
    for line in raw_fm.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current_list_key:
            meta.setdefault(current_list_key, []).append(stripped[2:].strip().strip("'\""))
            continue
        current_list_key = None
        if ":" in line and not line.startswith((" ", "\t")):
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            if not val:
                current_list_key = key
                meta[key] = []
            elif val.startswith("[") and val.endswith("]"):
                items = [x.strip().strip("'\"") for x in val[1:-1].split(",") if x.strip()]
                meta[key] = items
            else:
                meta[key] = val.strip("'\"")
    return meta, body


def as_list(val: object) -> list[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    s = str(val).strip()
    return [s] if s else []


def unique_limited(values: list[str], limit: int) -> list[str]:
    seen: list[str] = []
    for v in values:
        item = str(v).strip().strip("[]")
        if not item or item in seen:
            continue
        seen.append(item)
        if len(seen) >= limit:
            break
    return seen


def extract_section(body: str, heading: str) -> str:
    pattern = rf"^##+\s+{re.escape(heading)}\s*$\n(.*?)(?=^##+\s+|\Z)"
    m = re.search(pattern, body, flags=re.MULTILINE | re.DOTALL)
    if not m:
        return ""
    return " ".join(m.group(1).strip().splitlines())[:500]


def extract_wikilinks(body: str) -> list[str]:
    links = []
    for raw in re.findall(r"\[\[([^\]]+)\]\]", body):
        target = raw.split("|", 1)[0].split("#", 1)[0].strip()
        if target and target not in links:
            links.append(target)
    return links[:25]


def wiki_retrieval_document(rel_path: str, text: str) -> str:
    """Format a karpathy-wiki Markdown page so hybrid search captures typed edges & sources."""
    fm, body = parse_frontmatter(text)
    title = str(fm.get("title") or Path(rel_path).stem)
    page_type = str(fm.get("type") or Path(rel_path).parts[0].rstrip("s"))
    fields = [
        f"标题：{title}",
        f"路径：{rel_path}",
        f"类型：{page_type}",
    ]
    label_map = [
        ("supports", "支撑"),
        ("opposes", "反对"),
        ("contradicts", "反对"),
        ("limits", "限定"),
        ("depends_on", "依赖"),
        ("follows", "承接论证"),
        ("related_concepts", "相关概念"),
        ("related_entities", "相关人物"),
        ("related_comparisons", "相关辨析"),
        ("sources", "来源"),
    ]
    for key, label in label_map:
        val = fm.get(key)
        if val not in (None, "", []):
            items = [i.removeprefix("[[").removesuffix("]]").strip() for i in as_list(val)]
            if items:
                fields.append(f"{label}：{'、'.join(items)}")
    for rel_key, rel_label in (("supports", "支撑"), ("contradicts", "反对"), ("derives_from", "理论来源"), ("supersedes", "替代")):
        m = re.search(rf"^\s+{rel_key}:\s*\[([^\]]+)\]", text, flags=re.MULTILINE)
        if m:
            items = [x.strip().strip("'\"[]") for x in m.group(1).split(",") if x.strip()]
            if items:
                fields.append(f"{rel_label}：{'、'.join(items)}")

    prop = extract_section(body, "命题")
    if prop:
        fields.append(f"命题：{prop}")
    ev = extract_section(body, "关键证据") or extract_section(body, "原文")
    if ev:
        fields.append(f"关键证据：{ev}")
    links = extract_wikilinks(body)
    if links:
        fields.append(f"正文链接：{'、'.join(links)}")
    plain = body.replace("[[", "").replace("]]", "")
    fields.append("")
    fields.append(plain)
    return "\n".join(fields)


def extract_raw_evidence_paths(text: str) -> list[str]:
    fm, _ = parse_frontmatter(text)
    paths: list[str] = as_list(fm.get("sources"))
    patterns = [
        r"证据位置：`([^`]+)`",
        r"evidence:\s*`([^`]+)`",
        r"来源：`([^`]+)`",
        r"sources?:\s*\[([^\]]+)\]",
        r"`((?:wiki/)?raw/[^`]+?\.md)(?::[^`]*)?`",
        r"`([^`\n]+?\.(?:pdf|docx|epub|md|txt))(?:#[^`\n]*|:[^`\n]*)?`",
    ]
    for pat in patterns:
        for match in re.findall(pat, text, flags=re.IGNORECASE):
            for part in str(match).replace("，", ",").split(","):
                cleaned = part.strip().strip("'\"")
                if cleaned:
                    paths.append(cleaned)
    return unique_limited(paths, 200)


def normalize_source_evidence_path(path: str) -> str:
    cleaned = str(path).split("#", 1)[0].split(":", 1)[0].strip().removeprefix("./")
    return cleaned.removeprefix("wiki/raw/").removeprefix("raw/")


def collect_raw_semantic_hints(wiki_root: Path | None) -> dict[str, dict]:
    if not wiki_root or not wiki_root.is_dir():
        return {}
    hints: dict[str, dict] = {}
    for folder in RAW_SEMANTIC_SOURCE_DIRS:
        page_dir = wiki_root / folder
        if not page_dir.is_dir():
            continue
        for page in sorted(page_dir.rglob("*.md")):
            if page.name.startswith("_") or any(p.startswith(".") for p in page.relative_to(wiki_root).parts):
                continue
            text = read_text(page)
            fm, _ = parse_frontmatter(text)
            title = str(fm.get("title") or page.stem)
            page_type = str(fm.get("type") or folder.rstrip("s"))
            targets = [normalize_source_evidence_path(p) for p in extract_raw_evidence_paths(text)]
            targets = [t for t in targets if t]
            if not targets:
                continue
            concepts = as_list(fm.get("related_concepts")) + ([title] if folder == "concepts" else [])
            entities = as_list(fm.get("related_entities")) + ([title] if folder == "entities" else [])
            comparisons = as_list(fm.get("related_comparisons")) + ([title] if folder in ("comparisons", "debates") else [])
            claims = [title] if page_type == "claim" or folder == "claims" else []
            for target in targets:
                h = hints.setdefault(target, {})
                h["concepts"] = unique_limited(h.get("concepts", []) + concepts, 4)
                h["entities"] = unique_limited(h.get("entities", []) + entities, 3)
                h["claims"] = unique_limited(h.get("claims", []) + claims, 2)
                h["comparisons"] = unique_limited(h.get("comparisons", []) + comparisons, 1)
                h.setdefault("text_role", "原文依据")
    return hints


def compute_semantic_source_hashes(wiki_root: Path | None) -> dict[str, str]:
    if not wiki_root or not wiki_root.is_dir():
        return {}
    hashes: dict[str, str] = {}
    for folder in RAW_SEMANTIC_SOURCE_DIRS:
        page_dir = wiki_root / folder
        if not page_dir.is_dir():
            continue
        for page in sorted(page_dir.rglob("*.md")):
            rel = page.relative_to(wiki_root)
            if page.name.startswith("_") or any(p.startswith(".") for p in rel.parts):
                continue
            hashes[rel.as_posix()] = sha256_text(read_text(page))
    return hashes


def compute_semantic_hint_hashes(hints: dict[str, dict]) -> dict[str, str]:
    return {
        src: sha256_text(json.dumps(hint, ensure_ascii=False, sort_keys=True))
        for src, hint in sorted(hints.items())
    }


def format_enriched_raw(raw_text: str, hint: dict) -> str:
    if not hint:
        return raw_text
    lines = ["检索增强标签（仅用于召回，严禁作为原文引用）："]
    if hint.get("concepts"):
        lines.append("相关概念：" + "；".join(hint["concepts"]))
    if hint.get("claims"):
        lines.append("相关论证：" + "；".join(hint["claims"]))
    if hint.get("comparisons"):
        lines.append("相关辨析：" + "；".join(hint["comparisons"]))
    if hint.get("entities"):
        lines.append("相关实体：" + "；".join(hint["entities"]))
    if hint.get("text_role"):
        lines.append("文本作用：" + str(hint["text_role"]))
    return wrap_enriched_header(lines, raw_text)


def collect_source_files(
    root_dir: Path,
    allowed_exts: set[str],
    include_dirs: set[str] | None,
    exclude_dirs: set[str] | None,
) -> dict[str, Path]:
    files: dict[str, Path] = {}
    if not root_dir.is_dir():
        return files
    for path in sorted(root_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in allowed_exts:
            continue
        rel = path.relative_to(root_dir)
        if path.name.startswith("_") or path.name in SKIP_NAMES:
            continue
        if any(part.startswith(".") for part in rel.parts):
            continue
        rel_posix = rel.as_posix()
        if include_dirs and not any(rel_posix == d or rel_posix.startswith(f"{d}/") for d in include_dirs):
            continue
        if exclude_dirs and any(rel_posix == d or rel_posix.startswith(f"{d}/") for d in exclude_dirs):
            continue
        files[rel_posix] = path
    return files


def discover_default_model(models: list[dict], model_type: str, preferred: str | None) -> str | None:
    if preferred:
        for m in models:
            if m.get("id") == preferred or m.get("name") == preferred:
                return str(m["id"])
        return preferred
    typed = [m for m in models if str(m.get("type", "")).lower() == model_type.lower()]
    for m in typed:
        if m.get("is_default"):
            return str(m["id"])
    return str(typed[0]["id"]) if typed else None


def ensure_kb(
    backend,
    kb_name: str,
    existing_kb_id: str | None,
    wiki_mode: str,
    layer: str,
    weknora_cfg: dict,
    chunk_size: int,
    overlap: int,
) -> dict:
    models = backend.list_models()
    emb_id = discover_default_model(models, "Embedding", weknora_cfg.get("embedding_model_id"))
    sum_id = discover_default_model(models, "KnowledgeQA", weknora_cfg.get("summary_model_id"))
    if not emb_id:
        raise WeKnoraError(
            "No Embedding model configured in WeKnora server. Configure an Embedding model in WeKnora UI first (run doctor.py for guidance).",
            exit_code=1,
        )

    enable_native_wiki = (wiki_mode == "weknora_native" and layer == "raw")
    granularity = str(weknora_cfg.get("wiki_granularity") or "standard")
    desired_strategy = {
        "vector_enabled": True,
        "keyword_enabled": True,
        "wiki_enabled": bool(enable_native_wiki),
        "graph_enabled": False,
    }
    desired_wiki_cfg = {
        "auto_generate": bool(enable_native_wiki),
        "extraction_granularity": granularity,
    }
    if sum_id and enable_native_wiki:
        desired_wiki_cfg["synthesis_model_id"] = sum_id

    kb = backend.get_kb(existing_kb_id) if existing_kb_id else None
    if not kb:
        for candidate in backend.list_kbs():
            if candidate.get("name") == kb_name:
                kb = candidate
                break

    if not kb:
        payload: dict = {
            "name": kb_name,
            "description": f"Managed by social-science-km ({wiki_mode} / {layer})",
            "type": "document",
            "embedding_model_id": emb_id,
            "chunking_config": {"chunk_size": chunk_size, "chunk_overlap": overlap},
            "indexing_strategy": desired_strategy,
            "wiki_config": desired_wiki_cfg,
        }
        if sum_id:
            payload["summary_model_id"] = sum_id
        return backend.create_kb(payload)

    cur_strat = kb.get("indexing_strategy") or {}
    if bool(cur_strat.get("wiki_enabled")) != bool(enable_native_wiki):
        kb = backend.patch_kb(
            kb["id"],
            {"indexing_strategy": desired_strategy, "wiki_config": desired_wiki_cfg},
        )
    return kb


def write_source_manifest(
    project_root: Path,
    source_dir: Path,
    files: dict[str, Path],
    remote_docs: dict[str, dict],
) -> Path:
    """Write/update `<知识库>/检索索引/_source_manifest.md` for direct source-folder projects."""
    ledger_path = project_root / "检索索引" / "_source_manifest.md"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 源文献入库清单 (_source_manifest)",
        "",
        f"- 原始资料目录：`{source_dir}`",
        f"- 同步时间：{datetime.now(timezone.utc).isoformat()}",
        f"- 文件总数：{len(files)}",
        "",
        "| 相对路径 | 格式 | 字节数 | WeKnora 文档 ID | 状态 |",
        "|---|---|---:|---|---|",
    ]
    for rel_posix, fpath in sorted(files.items()):
        ext = fpath.suffix.lower().lstrip(".") or "file"
        size_b = fpath.stat().st_size
        doc_id = (remote_docs.get(rel_posix) or {}).get("knowledge_id", "-")
        lines.append(f"| `{rel_posix}` | `{ext}` | {size_b} | `{doc_id}` | completed |")
    lines.append("")
    ledger_path.write_text("\n".join(lines), encoding="utf-8")
    return ledger_path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sync original source documents or local Wiki cards into WeKnora.")
    p.add_argument("--config", default=None, help="Path to weknora_config.json or rag_config.json")
    p.add_argument("--project-root", default=None, help="Knowledge-base project root (defaults to cwd)")
    p.add_argument("--wiki-mode", default=None, choices=sorted(VALID_WIKI_MODES), help="local_karpathy | weknora_native")
    p.add_argument(
        "--source-dir",
        default=None,
        help="Original read-only source folder (PDF/DOCX/EPUB/MD/TXT) — uploads directly to <project>-raw without creating local wiki/raw/*.md",
    )
    p.add_argument("--md-dir", default=None, help="Markdown directory (wiki for card sync, or legacy wiki/raw)")
    p.add_argument("--index-dir", default=None, help="Local manifest directory (e.g. 检索索引/raw or 检索索引/wiki)")
    p.add_argument("--include-dirs", default=None, help="Comma-separated subdirectories to include")
    p.add_argument("--exclude-dirs", default=None, help="Comma-separated subdirectories to exclude")
    p.add_argument("--metadata-mode", default=None, choices=["plain", "enriched_raw", "wiki", "direct_source"], help="Sync formatting mode")
    p.add_argument("--chunk-size", type=int, default=None, help="Chunk size in characters")
    p.add_argument("--overlap", type=int, default=None, help="Chunk overlap in characters")
    p.add_argument("--timeout", type=int, default=None, help="Timeout in seconds")
    p.add_argument("--incremental", action="store_true", help="Upload only new/changed files and delete removed files")
    p.add_argument("--mock", action="store_true", help="Use offline mock WeKnora backend for testing")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve() if args.project_root else Path.cwd().resolve()
    cfg_path = resolve_project_config_path(project_root, args.config)
    cfg = load_project_config(cfg_path)

    wiki_mode = args.wiki_mode or cfg["wiki_mode"] or DEFAULT_WIKI_MODE
    weknora_cfg = cfg["weknora"]
    build_cfg = cfg["build"]

    metadata_mode = args.metadata_mode or build_cfg.get("metadata_mode")
    is_wiki_layer = metadata_mode == "wiki"

    if wiki_mode == "weknora_native" and is_wiki_layer:
        print("[SKIP] wiki_mode=weknora_native uses WeKnora's built-in automated Wiki; local wiki card sync is not needed.")
        return

    # Determine whether this is a direct source-folder sync (new no-raw workflow) or Markdown sync
    explicit_source_dir = args.source_dir or (None if is_wiki_layer or args.md_dir else cfg.get("source_dir"))
    direct_source = bool(explicit_source_dir or metadata_mode == "direct_source")

    if direct_source:
        raw_src = explicit_source_dir or args.md_dir or cfg.get("source_dir")
        if not raw_src:
            raise SystemExit("--metadata-mode direct_source requires --source-dir (or source_dir in weknora_config.json)")
        target_dir = Path(raw_src).expanduser()
        if not target_dir.is_absolute():
            target_dir = (project_root / target_dir).resolve()
        metadata_mode = "direct_source"
        allowed_exts = SUPPORTED_SOURCE_EXTS
    else:
        target_dir = Path(args.md_dir or build_cfg.get("md_dir") or ("wiki" if is_wiki_layer else "wiki/raw")).expanduser()
        if not target_dir.is_absolute():
            target_dir = (project_root / target_dir).resolve()
        if not metadata_mode:
            metadata_mode = "plain"
        if wiki_mode == "weknora_native" and metadata_mode == "enriched_raw":
            metadata_mode = "plain"
        allowed_exts = {".md"}

    default_idx = "检索索引/wiki" if is_wiki_layer else "检索索引/raw"
    index_dir = Path(args.index_dir or (default_idx if is_wiki_layer else (build_cfg.get("index_dir") or default_idx))).expanduser()
    if not index_dir.is_absolute():
        index_dir = (project_root / index_dir).resolve()

    chunk_size = int(args.chunk_size or build_cfg.get("chunk_size") or 1000)
    overlap = int(args.overlap or build_cfg.get("overlap") or 200)
    timeout = int(args.timeout or build_cfg.get("timeout") or 120)

    def split_csv(val: object) -> set[str] | None:
        if not val:
            return None
        if isinstance(val, list):
            return {str(x).strip() for x in val if str(x).strip()}
        return {x.strip() for x in str(val).split(",") if x.strip()}

    include_dirs = split_csv(args.include_dirs or (None if is_wiki_layer else build_cfg.get("include_dirs")))
    exclude_dirs = split_csv(args.exclude_dirs or (None if is_wiki_layer else build_cfg.get("exclude_dirs")))

    if not target_dir.is_dir():
        raise SystemExit(f"Source directory does not exist: {target_dir}")

    layer = "wiki" if is_wiki_layer else "raw"
    kb_prefix = str(weknora_cfg.get("kb_prefix") or project_root.name).strip()
    kb_name = f"{kb_prefix}-{layer}"

    manifest_path = index_dir / "manifest.json"
    old_manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}

    settings_changed = bool(
        old_manifest
        and (
            old_manifest.get("backend") != "weknora"
            or old_manifest.get("wiki_mode") != wiki_mode
            or old_manifest.get("metadata_mode") != metadata_mode
            or old_manifest.get("chunk_size") != chunk_size
            or old_manifest.get("overlap") != overlap
            or bool(old_manifest.get("mock")) != bool(args.mock)
        )
    )
    incremental = bool(args.incremental and old_manifest and not settings_changed)

    files = collect_source_files(target_dir, allowed_exts, include_dirs, exclude_dirs)
    if metadata_mode == "wiki":
        files = {k: v for k, v in files.items() if k not in WIKI_SKIP_NAMES and Path(k).name not in WIKI_SKIP_NAMES}
    wiki_root = project_root / "wiki" if (project_root / "wiki").is_dir() else (target_dir.parent if target_dir.name == "raw" else None)
    hints = collect_raw_semantic_hints(wiki_root) if metadata_mode == "enriched_raw" else {}
    sem_src_hashes = compute_semantic_source_hashes(wiki_root) if metadata_mode == "enriched_raw" else {}
    sem_hint_hashes = compute_semantic_hint_hashes(hints) if metadata_mode == "enriched_raw" else {}

    try:
        backend = make_backend(weknora_cfg, project_root, mock=args.mock, timeout=timeout)
        kb = ensure_kb(
            backend=backend,
            kb_name=kb_name,
            existing_kb_id=old_manifest.get("kb_id") if not settings_changed else None,
            wiki_mode=wiki_mode,
            layer=layer,
            weknora_cfg=weknora_cfg,
            chunk_size=chunk_size,
            overlap=overlap,
        )
        kb_id = str(kb["id"])

        old_remote_docs: dict[str, dict] = old_manifest.get("remote_docs") or {}
        preserved_external: dict[str, dict] = {}
        preserved_hashes: dict[str, str] = {}
        old_hashes: dict[str, str] = old_manifest.get("file_hashes") or {}
        if not direct_source and layer == "raw":
            for rel_k, info in old_remote_docs.items():
                if rel_k not in files and (
                    str((info or {}).get("file_type") or "") == "pdf"
                    or Path(rel_k).name.startswith("_")
                ):
                    preserved_external[rel_k] = info
                    if rel_k in old_hashes:
                        preserved_hashes[rel_k] = old_hashes[rel_k]

        if not incremental and old_remote_docs:
            for rel_k, info in old_remote_docs.items():
                if rel_k in preserved_external:
                    continue
                if info.get("knowledge_id"):
                    backend.delete_doc(str(info["knowledge_id"]))
            old_remote_docs = dict(preserved_external)

        # Build server-side existing doc map for smart reuse (e.g. docs already uploaded via UI/CLI)
        existing_server_by_hash: dict[str, dict] = {}
        existing_server_by_name: dict[str, dict] = {}
        for sdoc in backend.list_docs(kb_id):
            if sdoc.get("parse_status") == "completed" and sdoc.get("id"):
                if sdoc.get("file_hash"):
                    existing_server_by_hash[str(sdoc["file_hash"])] = sdoc
                for k in (sdoc.get("title"), sdoc.get("file_name")):
                    if k:
                        existing_server_by_name[str(k)] = sdoc
                        existing_server_by_name[Path(str(k)).name] = sdoc

        file_hashes: dict[str, str] = {}
        new_remote_docs: dict[str, dict] = {}
        uploaded_ids: list[str] = []
        uploaded_count = 0
        reused_count = 0
        deleted_count = 0

        for rel_posix, info in old_remote_docs.items():
            if rel_posix not in files and rel_posix not in preserved_external:
                if info.get("knowledge_id"):
                    backend.delete_doc(str(info["knowledge_id"]))
                    deleted_count += 1

        for rel_posix, fpath in files.items():
            content_hash = sha256_file(fpath)
            file_hashes[rel_posix] = content_hash
            prev = old_remote_docs.get(rel_posix)

            if direct_source:
                if incremental and prev and prev.get("sha256") == content_hash and prev.get("knowledge_id"):
                    new_remote_docs[rel_posix] = prev
                    reused_count += 1
                    continue

                # Reuse an identical completed document already on the WeKnora KB instead of re-parsing
                matched_server = existing_server_by_hash.get(content_hash) or existing_server_by_name.get(fpath.name)
                if matched_server and not prev:
                    doc_id = str(matched_server["id"])
                    new_remote_docs[rel_posix] = {
                        "knowledge_id": doc_id,
                        "sha256": content_hash,
                        "upload_sha256": content_hash,
                        "file_type": fpath.suffix.lower().lstrip("."),
                    }
                    reused_count += 1
                    continue

                if prev and prev.get("knowledge_id"):
                    backend.delete_doc(str(prev["knowledge_id"]))

                if fpath.suffix.lower() in TEXT_SOURCE_EXTS:
                    txt = read_text(fpath)
                    doc = backend.upload_file(kb_id=kb_id, content=txt, rel_file_name=rel_posix, chunk_size=chunk_size, overlap=overlap)
                else:
                    doc = backend.upload_file_path(kb_id=kb_id, file_path=fpath, rel_file_name=rel_posix, chunk_size=chunk_size, overlap=overlap)
                doc_id = str(doc["id"])
                uploaded_ids.append(doc_id)
                uploaded_count += 1
                new_remote_docs[rel_posix] = {
                    "knowledge_id": doc_id,
                    "sha256": content_hash,
                    "upload_sha256": content_hash,
                    "file_type": fpath.suffix.lower().lstrip("."),
                }
                continue

            raw_content = read_text(fpath)
            if metadata_mode == "wiki":
                upload_text = wiki_retrieval_document(rel_posix, raw_content)
            elif metadata_mode == "enriched_raw":
                upload_text = format_enriched_raw(raw_content, hints.get(rel_posix, {}))
            else:
                upload_text = raw_content

            upload_hash = sha256_text(upload_text)
            if (
                incremental
                and prev
                and prev.get("sha256") == content_hash
                and prev.get("upload_sha256") == upload_hash
                and prev.get("knowledge_id")
            ):
                new_remote_docs[rel_posix] = prev
                reused_count += 1
                continue

            matched_md_server = (
                existing_server_by_name.get(rel_posix)
                or existing_server_by_name.get(fpath.name)
            )
            if matched_md_server and not prev and metadata_mode == "plain":
                doc_id = str(matched_md_server["id"])
                new_remote_docs[rel_posix] = {
                    "knowledge_id": doc_id,
                    "sha256": content_hash,
                    "upload_sha256": upload_hash,
                    "semantic_hint_hash": sem_hint_hashes.get(rel_posix, ""),
                }
                reused_count += 1
                continue

            if prev and prev.get("knowledge_id"):
                backend.delete_doc(str(prev["knowledge_id"]))

            doc = backend.upload_file(
                kb_id=kb_id,
                content=upload_text,
                rel_file_name=rel_posix,
                chunk_size=chunk_size,
                overlap=overlap,
            )
            doc_id = str(doc["id"])
            uploaded_ids.append(doc_id)
            uploaded_count += 1
            new_remote_docs[rel_posix] = {
                "knowledge_id": doc_id,
                "sha256": content_hash,
                "upload_sha256": upload_hash,
                "semantic_hint_hash": sem_hint_hashes.get(rel_posix, ""),
            }

        file_hashes.update(preserved_hashes)
        new_remote_docs.update(preserved_external)
        wait_res = backend.wait_docs(uploaded_ids, timeout_sec=max(timeout, 600)) if uploaded_ids else {"completed": [], "failed": [], "timeout": []}
        if wait_res.get("failed") or wait_res.get("timeout"):
            raise WeKnoraError(
                f"Document parsing incomplete in WeKnora KB {kb_name}: failed={wait_res.get('failed')}, timeout={wait_res.get('timeout')}",
                exit_code=1,
            )

        index_dir.mkdir(parents=True, exist_ok=True)
        manifest: dict = {
            "backend": "weknora",
            "format_version": 4,
            "wiki_mode": wiki_mode,
            "kb_id": kb_id,
            "kb_name": kb_name,
            "embedding_model": kb.get("embedding_model_id") or build_cfg.get("model") or "weknora-default",
            "source_dir": str(target_dir) if direct_source else None,
            "md_dir": str(target_dir),
            "index_dir": str(index_dir),
            "metadata_mode": metadata_mode,
            "include_dirs": sorted(include_dirs) if include_dirs else None,
            "exclude_dirs": sorted(exclude_dirs) if exclude_dirs else None,
            "chunk_size": chunk_size,
            "overlap": overlap,
            "dimensions": build_cfg.get("dimensions"),
            "encoding_format": build_cfg.get("encoding_format"),
            "mock": bool(args.mock),
            "file_count": len(file_hashes),
            "file_hashes": file_hashes,
            "remote_docs": new_remote_docs,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if metadata_mode == "enriched_raw":
            manifest["semantic_source_hashes"] = sem_src_hashes
            manifest["semantic_hint_hashes"] = sem_hint_hashes

        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        if direct_source:
            write_source_manifest(project_root, target_dir, files, new_remote_docs)

        action_word = "增量同步" if incremental else "全量同步"
        native_note = "（已开启 WeKnora 自动生成 Wiki）" if (wiki_mode == "weknora_native" and layer == "raw") else ""
        src_note = " [原文件直传]" if direct_source else ""
        print(
            f"[OK] WeKnora {action_word}完成 [{kb_name} / {kb_id}]{native_note}{src_note}: "
            f"总文件 {len(file_hashes)}，上传 {uploaded_count}，复用 {reused_count}，移除 {deleted_count}。"
        )
    except WeKnoraError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(exc.exit_code) from exc


if __name__ == "__main__":
    main()
