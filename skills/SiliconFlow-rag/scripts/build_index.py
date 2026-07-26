#!/usr/bin/env python3
"""Build a local RAG index from Markdown files using SiliconFlow embeddings."""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.client
import json
import math
import os
import re
import stat
import struct
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_URL = "https://api.siliconflow.cn/v1/embeddings"
DEFAULT_MODEL = "BAAI/bge-m3"
HERMES_CONFIG_PATH = Path.home() / ".hermes" / "private" / "SiliconFlow-rag" / "config.json"
LEGACY_CONFIG_PATH = Path.home() / ".codex" / "SiliconFlow-rag" / "config.json"
DEFAULT_CONFIG_PATH = HERMES_CONFIG_PATH
BUILD_DEFAULTS = {
    "md_dir": "raw",
    "index_dir": "检索索引",
    "model": DEFAULT_MODEL,
    "api_key_env": "SILICONFLOW_API_KEY",
    "api_key_file": None,
    "chunk_size": 1200,
    "overlap": 200,
    "batch_size": 16,
    "timeout": 60,
    "sleep": 0.0,
    "include_dirs": None,
    "exclude_dirs": None,
    "metadata_mode": "plain",
    "dimensions": None,
    "encoding_format": "float",
}
CONFIG_SECTIONS = {"build", "query"}
QUERY_CONFIG_FIELDS = {"top_k", "candidates", "embedding_model", "rerank_model"}
BUILD_INT_FIELDS = {"chunk_size", "overlap", "batch_size", "timeout"}
BUILD_FLOAT_FIELDS = {"sleep"}
SKIP_NAMES = {
    "_conversion_failures.md",
    "_conversion_manifest.md",
    "_主题索引.md",
}
RAW_SEMANTIC_SOURCE_DIRS = ("claims", "concepts", "comparisons", "entities", "debates", "observations", "structures", "predicts")


class TransientAPIError(RuntimeError):
    """Retryable transport, rate-limit, or server-side embedding failure."""


def normalize_config(data: dict, fields: set[str], label: str) -> dict:
    config = {}
    unknown = []
    for key, value in data.items():
        normalized = str(key).replace("-", "_")
        if normalized in fields:
            config[normalized] = value
        else:
            unknown.append(str(key))
    if unknown:
        raise SystemExit(f"Unknown {label} config keys: {', '.join(sorted(unknown))}")
    return config


def top_level_config(data: dict, fields: set[str], label: str) -> dict:
    allowed = fields | CONFIG_SECTIONS | QUERY_CONFIG_FIELDS
    unknown = [str(key) for key in data if str(key).replace("-", "_") not in allowed]
    if unknown:
        raise SystemExit(f"Unknown {label} config keys: {', '.join(sorted(unknown))}")
    return normalize_config({
        key: value
        for key, value in data.items()
        if str(key).replace("-", "_") in fields
    }, fields, label)


def coerce_int(value: object, key: str) -> int:
    if isinstance(value, bool):
        raise SystemExit(f"{key} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"{key} must be an integer") from exc


def coerce_float(value: object, key: str) -> float:
    if isinstance(value, bool):
        raise SystemExit(f"{key} must be a number")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"{key} must be a number") from exc


def load_build_config(config_file: str | None) -> dict:
    if not config_file:
        return {}

    config_path = Path(config_file).expanduser()
    if not config_path.exists():
        raise SystemExit(f"RAG config file not found: {config_path}")
    try:
        data = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise SystemExit(f"Could not read RAG config: {config_path}. Reason: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"RAG config must be a JSON object: {config_path}")

    fields = set(BUILD_DEFAULTS)
    config = top_level_config(data, fields, "top-level build")
    section = data.get("build")
    if section is not None:
        if not isinstance(section, dict):
            raise SystemExit("RAG config key 'build' must be an object")
        config.update(normalize_config(section, fields, "build"))
    return config


def apply_build_config(args: argparse.Namespace) -> argparse.Namespace:
    config = load_build_config(args.config)
    for key, default in BUILD_DEFAULTS.items():
        if getattr(args, key) is None:
            setattr(args, key, config.get(key, default))

    for key in BUILD_INT_FIELDS:
        setattr(args, key, coerce_int(getattr(args, key), key))
    for key in BUILD_FLOAT_FIELDS:
        setattr(args, key, coerce_float(getattr(args, key), key))

    if args.chunk_size <= 0:
        raise SystemExit("chunk_size must be greater than 0")
    if args.overlap < 0:
        raise SystemExit("overlap must be 0 or greater")
    if args.overlap >= args.chunk_size:
        raise SystemExit("overlap must be smaller than chunk_size")
    if args.batch_size <= 0:
        raise SystemExit("batch_size must be greater than 0")
    if args.timeout <= 0:
        raise SystemExit("timeout must be greater than 0")
    if args.sleep < 0:
        raise SystemExit("sleep must be 0 or greater")
    if args.dimensions is not None:
        args.dimensions = coerce_int(args.dimensions, "dimensions")
        if args.dimensions <= 0:
            raise SystemExit("dimensions must be greater than 0")
    if args.encoding_format not in {"float", "base64"}:
        raise SystemExit("encoding_format must be 'float' or 'base64'")
    args.include_dirs = parse_csv(args.include_dirs)
    args.exclude_dirs = parse_csv(args.exclude_dirs)
    if args.metadata_mode not in {"plain", "wiki", "enriched_raw"}:
        raise SystemExit("metadata_mode must be 'plain', 'wiki', or 'enriched_raw'")
    return args


def parse_csv(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = str(value).split(",")
    return [str(item).strip().strip("/") for item in items if str(item).strip()]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").lstrip("\ufeff")


def stable_id(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def path_matches_dir(rel_path: Path, dirs: list[str]) -> bool:
    rel = rel_path.as_posix()
    return any(rel == folder or rel.startswith(f"{folder}/") for folder in dirs)


def list_markdown_files(md_dir: Path, include_dirs: list[str] | None = None, exclude_dirs: list[str] | None = None) -> list[Path]:
    include_dirs = include_dirs or []
    exclude_dirs = exclude_dirs or []
    files = []
    for path in md_dir.rglob("*.md"):
        rel_path = path.relative_to(md_dir)
        if path.name.startswith("_") or path.name in SKIP_NAMES:
            continue
        if any(part.startswith(".") for part in rel_path.parts):
            continue
        if include_dirs and not path_matches_dir(rel_path, include_dirs):
            continue
        if exclude_dirs and path_matches_dir(rel_path, exclude_dirs):
            continue
        files.append(path)
    return sorted(files)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    block = text[4:end]
    body = text[end + 5:]
    data: dict[str, object] = {}
    list_key: str | None = None
    for line in block.splitlines():
        stripped = line.strip()
        if list_key and stripped.startswith("- "):
            value = stripped[2:].strip().strip('"').strip("'")
            if value:
                current = data.setdefault(list_key, [])
                if isinstance(current, list):
                    current.append(value)
            continue
        if ":" not in line or line.startswith(" "):
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        list_key = None
        if not value:
            data[key] = []
            list_key = key
            continue
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            data[key] = [item.strip().strip('"').strip("'") for item in inner.split(",") if item.strip()] if inner else []
        elif value.lower() in {"true", "false"}:
            data[key] = value.lower() == "true"
        else:
            data[key] = value.strip('"').strip("'")
    return data, body


def extract_wikilinks(text: str) -> list[str]:
    links: list[str] = []
    for part in text.split("[[")[1:]:
        target = part.split("]]", 1)[0].split("|", 1)[0].strip()
        if target and target not in links:
            links.append(target)
    return links


def extract_section(body: str, heading: str) -> str:
    marker = f"## {heading}"
    start = body.find(marker)
    if start == -1:
        return ""
    section = body[start + len(marker):]
    next_heading = section.find("\n## ")
    if next_heading != -1:
        section = section[:next_heading]
    return section.strip()


def as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if value in (None, ""):
        return []
    return [str(value)]


def wiki_retrieval_text(text: str, rel_path: str) -> str:
    frontmatter, body = parse_frontmatter(text)
    page_type = str(frontmatter.get("type") or Path(rel_path).parent.name or "wiki")
    title = str(frontmatter.get("title") or Path(rel_path).stem)
    fields = [
        f"页面类型：{page_type}",
        f"标题：{title}",
        f"路径：{rel_path}",
    ]
    for key, label in [
        ("claim_type", "claim_type"),
        ("core", "核心论证"),
        ("status", "状态"),
        ("confidence", "置信度"),
        ("supports", "支撑"),
        ("opposes", "反对"),
        ("limits", "限定"),
        ("depends_on", "依赖"),
        ("related_concepts", "相关概念"),
        ("related_entities", "相关人物"),
        ("related_comparisons", "相关辨析"),
        ("sources", "来源"),
    ]:
        value = frontmatter.get(key)
        if value not in (None, "", []):
            items = as_list(value)
            items = [item.removeprefix("[[") .removesuffix("]]").strip() for item in items]
            fields.append(f"{label}：{'、'.join(items) if items else value}")
    proposition = extract_section(body, "命题")
    if proposition:
        fields.append(f"命题：{proposition}")
    evidence = extract_section(body, "关键证据")
    if evidence:
        fields.append(f"关键证据：{evidence}")
    links = extract_wikilinks(body)
    if links:
        fields.append(f"正文链接：{'、'.join(links)}")
    plain = body.replace("[[", "").replace("]]", "")
    fields.append(plain[:1600])
    return "\n".join(fields)



def unique_limited(values: list[str], limit: int) -> list[str]:
    seen: list[str] = []
    for value in values:
        item = str(value).strip().strip("[]")
        if not item or item in seen:
            continue
        seen.append(item)
        if len(seen) >= limit:
            break
    return seen


def extract_raw_evidence_paths(text: str) -> list[str]:
    frontmatter, _ = parse_frontmatter(text)
    paths: list[str] = as_list(frontmatter.get("sources"))
    patterns = [
        r"证据位置：`([^`]+)`",
        r"evidence:\s*`([^`]+)`",
        r"sources?:\s*\[([^\]]+)\]",
        r"`((?:wiki/)?raw/[^`]+?\.md)(?::[^`]*)?`",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, text, flags=re.IGNORECASE):
            for part in str(match).replace("，", ",").split(","):
                cleaned = part.strip().strip("'\"")
                if cleaned:
                    paths.append(cleaned)
    return unique_limited(paths, 200)


def normalize_raw_evidence_path(path: str) -> str:
    cleaned = str(path).split(":", 1)[0].strip().removeprefix("./")
    return cleaned.removeprefix("wiki/raw/").removeprefix("raw/")


def merge_hint(target: dict, key: str, values: list[str], limit: int) -> None:
    existing = target.setdefault(key, [])
    target[key] = unique_limited(existing + values, limit)


def collect_raw_semantic_hints(md_dir: Path) -> dict[str, dict]:
    """Collect minimal wiki labels that explicitly point back to raw files.

    The labels are a retrieval bridge only. They are stored separately from raw_text
    and must not be cited as source evidence.
    """
    if md_dir.name != "raw":
        print(
            "[warn] enriched_raw expects --md-dir to be a directory named 'raw' "
            f"with wiki page folders as siblings; got '{md_dir.name}'. "
            "No semantic labels will be added (plain-equivalent index).",
            file=sys.stderr,
        )
        return {}
    wiki_root = md_dir.parent
    if not wiki_root.is_dir():
        return {}

    hints: dict[str, dict] = {}
    for folder in RAW_SEMANTIC_SOURCE_DIRS:
        page_dir = wiki_root / folder
        if not page_dir.is_dir():
            continue
        for page in sorted(page_dir.rglob("*.md")):
            text = read_text(page)
            frontmatter, body = parse_frontmatter(text)
            title = str(frontmatter.get("title") or page.stem)
            page_type = str(frontmatter.get("type") or folder.rstrip("s"))
            targets = [normalize_raw_evidence_path(path) for path in extract_raw_evidence_paths(text)]
            targets = [target for target in targets if target]
            if not targets:
                continue

            concepts = as_list(frontmatter.get("related_concepts"))
            entities = as_list(frontmatter.get("related_entities"))
            comparisons = as_list(frontmatter.get("related_comparisons"))
            claim_titles = [title] if page_type == "claim" or folder == "claims" else []
            comparison_titles = [title] if page_type == "comparison" or folder == "comparisons" else []
            comparison_titles += comparisons

            for target in targets:
                hint = hints.setdefault(target, {})
                merge_hint(hint, "concepts", concepts, 4)
                merge_hint(hint, "entities", entities, 3)
                merge_hint(hint, "claims", claim_titles, 2)
                merge_hint(hint, "comparisons", comparison_titles, 1)
                hint.setdefault("text_role", "原文依据")
    return hints


def semantic_hint_hashes(hints: dict[str, dict]) -> dict[str, str]:
    return {
        source: hashlib.sha256(
            json.dumps(hint, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        for source, hint in sorted(hints.items())
    }


def semantic_source_hashes(md_dir: Path) -> dict[str, str]:
    """Hash wiki pages that can contribute labels to an enriched raw index."""
    if md_dir.name != "raw":
        return {}
    wiki_root = md_dir.parent
    hashes: dict[str, str] = {}
    for folder in RAW_SEMANTIC_SOURCE_DIRS:
        page_dir = wiki_root / folder
        if not page_dir.is_dir():
            continue
        for page in sorted(page_dir.rglob("*.md")):
            rel_path = page.relative_to(wiki_root)
            if page.name.startswith("_") or any(part.startswith(".") for part in rel_path.parts):
                continue
            content = read_text(page)
            hashes[rel_path.as_posix()] = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return hashes


def enriched_raw_embedding_text(raw_text: str, hint: dict) -> str:
    lines = ["检索增强标签（仅用于召回，不作为原文证据）："]
    if hint.get("concepts"):
        lines.append("相关概念：" + "；".join(unique_limited(hint["concepts"], 4)))
    if hint.get("claims"):
        lines.append("相关论证：" + "；".join(unique_limited(hint["claims"], 2)))
    if hint.get("comparisons"):
        lines.append("相关辨析：" + "；".join(unique_limited(hint["comparisons"], 1)))
    if hint.get("entities"):
        lines.append("相关实体：" + "；".join(unique_limited(hint["entities"], 3)))
    if hint.get("source_type"):
        lines.append("来源类型：" + str(hint["source_type"]))
    if hint.get("text_role"):
        lines.append("文本作用：" + str(hint["text_role"]))
    lines.append("原文：")
    lines.append(raw_text)
    return "\n".join(lines)

def chunk_text(text: str, chunk_size: int, overlap: int) -> list[tuple[int, int, str]]:
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks = []
    start = 0
    length = len(normalized)
    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            newline = normalized.rfind("\n\n", start, end)
            if newline > start + chunk_size // 2:
                end = newline
        snippet = normalized[start:end].strip()
        if snippet:
            chunks.append((start, end, snippet))
        if end >= length:
            break
        start = max(start + 1, end - overlap)
    return chunks


def mock_embedding(text: str, dimensions: int = 64) -> list[float]:
    vector = [0.0] * dimensions
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:2], "big") % dimensions
        sign = 1.0 if digest[2] % 2 == 0 else -1.0
        vector[idx] += sign
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def decode_embedding(value: object) -> list[float]:
    if isinstance(value, list):
        return [float(item) for item in value]
    if isinstance(value, str):
        raw = base64.b64decode(value)
        if len(raw) % 4:
            raise RuntimeError("Base64 embedding byte length is not divisible by 4")
        return list(struct.unpack(f"<{len(raw) // 4}f", raw))
    raise RuntimeError(f"Unexpected embedding value type: {type(value).__name__}")


def siliconflow_embeddings(
    texts: list[str],
    model: str,
    api_key: str,
    timeout: int,
    dimensions: int | None = None,
    encoding_format: str = "float",
) -> list[list[float]]:
    payload_data = {
        "model": model,
        "input": texts,
        "encoding_format": encoding_format,
        "truncate": "right",
    }
    if dimensions is not None:
        payload_data["dimensions"] = dimensions
    payload = json.dumps(payload_data, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code == 429 or exc.code >= 500:
            raise TransientAPIError(f"SiliconFlow embedding request failed: HTTP {exc.code} {detail}") from exc
        raise RuntimeError(f"SiliconFlow embedding request failed: HTTP {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise TransientAPIError(f"SiliconFlow embedding request failed: {exc.reason}") from exc
    except (http.client.RemoteDisconnected, http.client.IncompleteRead, TimeoutError, ConnectionError) as exc:
        raise TransientAPIError(f"SiliconFlow embedding connection failed: {exc}") from exc

    data = body.get("data")
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected embedding response: {body}")
    ordered = sorted(data, key=lambda item: item.get("index", 0))
    return [decode_embedding(item["embedding"]) for item in ordered]


def warn_if_private_config_too_open(config_path: Path) -> None:
    """Warn on POSIX systems if a private key file is group/world-readable."""
    if os.name != "posix":
        return
    try:
        mode = config_path.stat().st_mode
    except OSError:
        return
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        print(
            f"Warning: API key config is readable by group/others: {config_path}. "
            "Consider chmod 600.",
            file=sys.stderr,
        )


def candidate_api_key_paths(api_key_file: str | None) -> list[Path]:
    if api_key_file:
        return [Path(api_key_file).expanduser()]
    return [HERMES_CONFIG_PATH, LEGACY_CONFIG_PATH]


def load_api_key(api_key_env: str, api_key_file: str | None) -> str:
    env_value = os.environ.get(api_key_env)
    if env_value:
        return env_value

    config_path = None
    for path in candidate_api_key_paths(api_key_file):
        if path.exists():
            config_path = path
            break
    if config_path is None:
        return ""
    warn_if_private_config_too_open(config_path)
    try:
        data = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise SystemExit(f"Could not read API key config: {config_path}. Reason: {exc}") from exc

    if isinstance(data, dict):
        for key in (api_key_env, "siliconflow_api_key", "api_key"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    raise SystemExit(f"API key config found but no usable key was present: {config_path}")


def checkpoint_metadata(args: argparse.Namespace) -> dict:
    return {
        "format_version": 1,
        "model": args.model,
        "mock": bool(args.mock),
        "dimensions": args.dimensions,
        "encoding_format": args.encoding_format,
    }


def load_embedding_checkpoint(path: Path, args: argparse.Namespace) -> dict[str, list[float]]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            rows = [json.loads(line) for line in handle if line.strip()]
    except (OSError, json.JSONDecodeError):
        path.unlink(missing_ok=True)
        return {}
    if not rows or rows[0].get("_meta") != checkpoint_metadata(args):
        path.unlink(missing_ok=True)
        return {}
    return {
        str(row["id"]): row["embedding"]
        for row in rows[1:]
        if isinstance(row, dict) and row.get("id") and isinstance(row.get("embedding"), list)
    }


def append_embedding_checkpoint(path: Path, rows: list[dict], args: argparse.Namespace) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            json.dumps({"_meta": checkpoint_metadata(args)}, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def embed_batches(chunks: list[dict], args: argparse.Namespace, checkpoint_path: Path) -> list[list[float]]:
    cached = load_embedding_checkpoint(checkpoint_path, args)
    pending = [chunk for chunk in chunks if chunk["id"] not in cached]
    if cached:
        print(f"Resuming embeddings: {len(cached)} cached, {len(pending)} remaining.", flush=True)

    if args.mock:
        for chunk in pending:
            cached[chunk["id"]] = mock_embedding(chunk.get("embedding_text") or chunk["text"])
        return [cached[chunk["id"]] for chunk in chunks]

    api_key = load_api_key(args.api_key_env, args.api_key_file)
    if not api_key:
        raise SystemExit(
            f"Missing {args.api_key_env}. Set it in the environment or save a local private config at "
            f"{HERMES_CONFIG_PATH} (preferred) or {LEGACY_CONFIG_PATH} (legacy), or use --mock for tests."
        )

    total = len(pending)
    total_batches = max(1, math.ceil(total / args.batch_size))
    progress_every = max(1, total_batches // 20)
    for start in range(0, total, args.batch_size):
        batch_chunks = pending[start:start + args.batch_size]
        batch = [chunk.get("embedding_text") or chunk["text"] for chunk in batch_chunks]
        batch_vectors: list[list[float]] = []
        for attempt in range(1, 4):
            try:
                batch_vectors = siliconflow_embeddings(
                    batch,
                    args.model,
                    api_key,
                    args.timeout,
                    dimensions=args.dimensions,
                    encoding_format=args.encoding_format,
                )
                break
            except TransientAPIError as exc:
                if attempt == 3:
                    raise RuntimeError(f"Embedding batch failed after {attempt} attempts: {exc}") from exc
                delay = 2 ** (attempt - 1)
                print(
                    f"Transient embedding failure for batch {start // args.batch_size + 1}; "
                    f"retrying in {delay}s ({attempt}/3): {exc}",
                    file=sys.stderr,
                )
                time.sleep(delay)
        checkpoint_rows = [
            {"id": chunk["id"], "embedding": vector}
            for chunk, vector in zip(batch_chunks, batch_vectors)
        ]
        append_embedding_checkpoint(checkpoint_path, checkpoint_rows, args)
        for row in checkpoint_rows:
            cached[row["id"]] = row["embedding"]
        batch_no = start // args.batch_size + 1
        if batch_no == 1 or batch_no == total_batches or batch_no % progress_every == 0:
            print(
                f"Embedding progress: {min(start + len(batch_chunks), total)}/{total} "
                f"({batch_no}/{total_batches} batches).",
                flush=True,
            )
        if args.sleep and start + args.batch_size < total:
            time.sleep(args.sleep)
    return [cached[chunk["id"]] for chunk in chunks]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def compute_file_hashes(md_dir: Path, files: list[Path]) -> dict[str, str]:
    """Return {source_path: sha256_hex} for each file."""
    hashes: dict[str, str] = {}
    for fp in files:
        rel = fp.relative_to(md_dir).as_posix()
        hashes[rel] = hashlib.sha256(read_text(fp).encode("utf-8")).hexdigest()
    return hashes


def manifest_settings(args: argparse.Namespace, md_dir: Path, index_dir: Path) -> dict:
    return {
        "md_dir": str(md_dir),
        "index_dir": str(index_dir),
        "embedding_model": args.model,
        "mock": bool(args.mock),
        "chunk_size": args.chunk_size,
        "overlap": args.overlap,
        "format_version": 3,
        "include_dirs": args.include_dirs,
        "exclude_dirs": args.exclude_dirs,
        "metadata_mode": args.metadata_mode,
        "dimensions": args.dimensions,
        "encoding_format": args.encoding_format,
    }


def changed_index_settings(old_manifest: dict, current: dict) -> list[str]:
    return [key for key, value in current.items() if old_manifest.get(key) != value]


def build_index(args: argparse.Namespace) -> None:
    md_dir = Path(args.md_dir).resolve()
    index_dir = Path(args.index_dir).resolve()
    if not md_dir.is_dir():
        raise SystemExit(f"Markdown directory not found: {md_dir}")

    files = list_markdown_files(md_dir, args.include_dirs, args.exclude_dirs)
    current_hashes = compute_file_hashes(md_dir, files)
    current_settings = manifest_settings(args, md_dir, index_dir)
    raw_semantic_hints = collect_raw_semantic_hints(md_dir) if args.metadata_mode == "enriched_raw" else {}
    raw_semantic_hints = {
        source: hint for source, hint in raw_semantic_hints.items()
        if source in current_hashes
    }
    current_hint_hashes = semantic_hint_hashes(raw_semantic_hints)
    current_semantic_source_hashes = semantic_source_hashes(md_dir) if args.metadata_mode == "enriched_raw" else {}

    # --- Incremental: diff against previous index ---
    old_chunks: list[dict] = []
    old_embeddings: list[dict] = []
    process_files = files  # default: process all
    skip_embed = False

    if args.incremental:
        manifest_path = index_dir / "manifest.json"
        chunks_path = index_dir / "chunks.jsonl"
        embeddings_path = index_dir / "embeddings.jsonl"
        if manifest_path.exists() and chunks_path.exists() and embeddings_path.exists():
            old_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            changed_settings = changed_index_settings(old_manifest, current_settings)
            if changed_settings:
                print("Incremental settings changed; falling back to full build: " + ", ".join(changed_settings))
            elif args.metadata_mode == "enriched_raw" and (
                not isinstance(old_manifest.get("semantic_hint_hashes"), dict)
                or not isinstance(old_manifest.get("semantic_source_hashes"), dict)
            ):
                print("Incremental semantic dependency metadata missing; falling back to full build.")
            else:
                old_hashes = old_manifest.get("file_hashes", {})
                new_or_changed = [
                    rel for rel, h in current_hashes.items()
                    if rel not in old_hashes or old_hashes[rel] != h
                ]
                deleted = [rel for rel in old_hashes if rel not in current_hashes]

                semantic_dependencies_changed = False
                if args.metadata_mode == "enriched_raw":
                    old_hint_hashes = old_manifest.get("semantic_hint_hashes", {})
                    changed_hints = {
                        rel for rel in set(old_hint_hashes) | set(current_hint_hashes)
                        if old_hint_hashes.get(rel) != current_hint_hashes.get(rel)
                    }
                    new_or_changed = sorted(set(new_or_changed) | (changed_hints & set(current_hashes)))
                    semantic_dependencies_changed = (
                        old_manifest.get("semantic_source_hashes", {}) != current_semantic_source_hashes
                    )

                if not new_or_changed and not deleted and not semantic_dependencies_changed:
                    print(f"Index is up to date ({len(files)} files, no changes).")
                    return

                # Load existing chunks and embeddings
                old_chunks = read_jsonl(chunks_path)
                old_embeddings = read_jsonl(embeddings_path)

                # Remove chunks from deleted or changed sources
                remove_sources = set(deleted + new_or_changed)
                old_chunks = [c for c in old_chunks if c["source_path"] not in remove_sources]
                kept_ids = {c["id"] for c in old_chunks}
                old_embeddings = [e for e in old_embeddings if e["id"] in kept_ids]

                # Only process new/changed files
                process_files = [fp for fp in files if fp.relative_to(md_dir).as_posix() in new_or_changed]
                if not process_files:
                    skip_embed = True
                    if deleted:
                        print(f"Removed {len(deleted)} stale file(s), no new content to embed.")
                    else:
                        print("Semantic dependencies changed; refreshed manifest without re-embedding raw chunks.")
                else:
                    print(f"Incremental: {len(new_or_changed)} file(s) content/semantic labels new or changed, "
                          f"{len(deleted)} removed, "
                          f"{len(files) - len(new_or_changed)} unchanged.")
        else:
            print("No existing index found; falling back to full build.")

    # --- Chunk new/changed files ---
    chunks: list[dict] = list(old_chunks)
    for file_path in process_files:
        rel_path = file_path.relative_to(md_dir).as_posix()
        source_text = read_text(file_path)
        if args.metadata_mode == "wiki":
            source_text = wiki_retrieval_text(source_text, rel_path)
        for chunk_no, (start, end, snippet) in enumerate(chunk_text(source_text, args.chunk_size, args.overlap), start=1):
            hint = raw_semantic_hints.get(rel_path, {}) if args.metadata_mode == "enriched_raw" else {}
            embedding_text = enriched_raw_embedding_text(snippet, hint) if hint else snippet
            chunk_id = stable_id(f"{rel_path}\n{chunk_no}\n{snippet}\n{json.dumps(hint, ensure_ascii=False, sort_keys=True)}")
            row = {
                "id": chunk_id,
                "source_path": rel_path,
                "chunk_no": chunk_no,
                "char_start": start,
                "char_end": end,
                "text": snippet,
            }
            if hint:
                row["embedding_text"] = embedding_text
                row["semantic_metadata"] = hint
            chunks.append(row)

    if not chunks:
        raise SystemExit(f"No Markdown content found under {md_dir}")

    # --- Embed ---
    checkpoint_path = index_dir / ".embedding_checkpoint.jsonl"
    if skip_embed:
        vectors = [e["embedding"] for e in old_embeddings]
        if len(vectors) != len(chunks):
            raise RuntimeError("Embedding count does not match chunk count")
    else:
        new_chunks = chunks[len(old_chunks):]
        if new_chunks:
            new_vectors = embed_batches(new_chunks, args, checkpoint_path)
        else:
            new_vectors = []
        vectors = [e["embedding"] for e in old_embeddings] + new_vectors
        if len(vectors) != len(chunks):
            raise RuntimeError("Embedding count does not match chunk count")

    # --- Write index ---
    index_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(index_dir / "chunks.jsonl", chunks)
    write_jsonl(index_dir / "embeddings.jsonl", [
        {"id": chunk["id"], "embedding": vector}
        for chunk, vector in zip(chunks, vectors)
    ])
    manifest = dict(current_settings)
    manifest.update({
        "created_at": datetime.now(timezone.utc).isoformat(),
        "api_key_env": args.api_key_env,
        "file_count": len(files),
        "chunk_count": len(chunks),
        "file_hashes": current_hashes,
        "semantic_hint_hashes": current_hint_hashes,
        "semantic_source_hashes": current_semantic_source_hashes,
    })
    (index_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    checkpoint_path.unlink(missing_ok=True)

    new_count = len(chunks) - len(old_chunks)
    kept_count = len(old_chunks)
    if args.incremental and kept_count:
        print(f"Index updated: {kept_count} chunks kept, {new_count} new, "
              f"total {len(chunks)} chunks from {len(files)} files into {index_dir}")
    else:
        print(f"Indexed {len(chunks)} chunks from {len(files)} files into {index_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a local RAG index from Markdown files.")
    parser.add_argument("--config", default=None, help="Optional JSON config file for build parameters")
    parser.add_argument("--md-dir", default=None, help="Markdown source directory")
    parser.add_argument("--index-dir", default=None, help="Index output directory")
    parser.add_argument("--model", default=None, help="SiliconFlow embedding model")
    parser.add_argument("--api-key-env", default=None, help="Environment variable containing the API key")
    parser.add_argument("--api-key-file", default=None, help=f"Local private API key config file; default: {DEFAULT_CONFIG_PATH}")
    parser.add_argument("--chunk-size", type=int, default=None, help="Chunk size in characters")
    parser.add_argument("--overlap", type=int, default=None, help="Chunk overlap in characters")
    parser.add_argument("--batch-size", type=int, default=None, help="Embedding request batch size")
    parser.add_argument("--timeout", type=int, default=None, help="HTTP timeout in seconds")
    parser.add_argument("--sleep", type=float, default=None, help="Sleep between embedding batches")
    parser.add_argument("--mock", action="store_true", help="Use deterministic local mock embeddings for tests")
    parser.add_argument("--incremental", action="store_true", help="Only re-index new or changed files (use file content hash)")
    parser.add_argument("--include-dirs", default=None, help="Comma-separated directories under md-dir to include")
    parser.add_argument("--exclude-dirs", default=None, help="Comma-separated directories under md-dir to exclude")
    parser.add_argument("--metadata-mode", default=None, choices=["plain", "wiki", "enriched_raw"], help="Metadata strategy: plain raw chunks, wiki retrieval text, or minimal wiki-label enriched raw chunks")
    parser.add_argument("--dimensions", type=int, default=None, help="Optional output embedding dimensions for models that support Matryoshka dimensions")
    parser.add_argument("--encoding-format", default=None, choices=["float", "base64"], help="Embedding response encoding; base64 reduces response size")
    return apply_build_config(parser.parse_args())


if __name__ == "__main__":
    build_index(parse_args())
