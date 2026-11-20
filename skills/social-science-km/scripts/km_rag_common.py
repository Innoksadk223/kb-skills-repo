#!/usr/bin/env python3
"""Shared helpers for social-science-km WeKnora RAG scripts.

Supports both:
- New projects: direct original source folder (``source_dir``, e.g. sibling
  ``<资料夹>/`` with PDF/DOCX/EPUB/MD/TXT) without generating local ``wiki/raw/*.md``.
- Legacy projects: existing ``wiki/raw/*.md`` directories.
And two selectable Wiki modes:
- ``local_karpathy`` (default): our social-science ``karpathy-wiki`` Markdown cards
  + Dual WeKnora KBs (``<project>-raw`` + ``<project>-wiki``).
- ``weknora_native`` (optional): WeKnora's built-in automated Web Wiki + Single KB.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from weknora_client import SUPPORTED_SOURCE_EXTS  # noqa: E402

WIKI_DIR_NAME = "wiki"
INDEX_DIR_NAME = "检索索引"
RAW_INDEX_NAME = "raw"
WIKI_INDEX_NAME = "wiki"
DEFAULT_WIKI_MODE = "local_karpathy"
VALID_WIKI_MODES = ("local_karpathy", "weknora_native")
WIKI_INDEX_SOURCE_DIRS = (
    "claims",
    "concepts",
    "entities",
    "comparisons",
    "debates",
    "observations",
    "structures",
    "predicts",
    "synthesis",
    "queries",
)
RAW_ENRICHMENT_SOURCE_DIRS = (
    "claims",
    "concepts",
    "comparisons",
    "entities",
    "debates",
    "observations",
    "structures",
    "predicts",
)
SKIP_NAMES = {
    "_conversion_failures.md",
    "_conversion_manifest.md",
    "_source_manifest.md",
    "_主题索引.md",
}


def path_matches_dir(rel_path: Path, dirs: set[str] | tuple[str, ...]) -> bool:
    rel = rel_path.as_posix()
    return any(rel == folder or rel.startswith(f"{folder}/") for folder in dirs)


def _hash_one_file(path: Path) -> str:
    if path.suffix.lower() in {".md", ".markdown", ".txt"}:
        content = path.read_text(encoding="utf-8", errors="replace").lstrip("\ufeff")
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def compute_hashes(
    root_dir: Path,
    include_dirs: tuple[str, ...] | set[str] | None = None,
    exclude_dirs: tuple[str, ...] | set[str] | None = None,
    allowed_exts: set[str] | None = None,
) -> dict[str, str]:
    include_dirs = include_dirs or ()
    exclude_dirs = exclude_dirs or ()
    exts = allowed_exts or {".md"}
    hashes: dict[str, str] = {}
    if not root_dir.is_dir():
        return hashes
    for path in sorted(root_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in exts:
            continue
        rel_path = path.relative_to(root_dir)
        if path.name.startswith("_") or path.name in SKIP_NAMES:
            continue
        if any(part.startswith(".") for part in rel_path.parts):
            continue
        if include_dirs and not path_matches_dir(rel_path, include_dirs):
            continue
        if exclude_dirs and path_matches_dir(rel_path, exclude_dirs):
            continue
        hashes[rel_path.as_posix()] = _hash_one_file(path)
    return hashes


def project_config_path(project_root: Path) -> Path | None:
    for name in ("weknora_config.json", "rag_config.json"):
        candidate = project_root / name
        if candidate.is_file():
            return candidate
    return None


def project_source_dir(project_root: Path, explicit_source_dir: str | None = None) -> Path | None:
    """Resolve direct source folder if configured/passed or recorded in raw manifest.

    Also auto-discovers a sibling ``<name>`` folder when ``project_root`` is named
    ``<name>（知识库）`` or ``<name>知识库`` AND ``wiki/raw`` does not exist yet.
    """
    if explicit_source_dir:
        p = Path(explicit_source_dir).expanduser()
        return p if p.is_absolute() else (project_root / p).resolve()

    cfg_path = project_config_path(project_root)
    if cfg_path:
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
        except Exception:
            data = {}
        if isinstance(data, dict):
            sdir = data.get("source_dir") or ((data.get("build") or {}).get("source_dir") if isinstance(data.get("build"), dict) else None)
            if sdir:
                p = Path(str(sdir)).expanduser()
                return p if p.is_absolute() else (project_root / p).resolve()

    raw_manifest_path = project_root / INDEX_DIR_NAME / RAW_INDEX_NAME / "manifest.json"
    if raw_manifest_path.is_file():
        try:
            m = json.loads(raw_manifest_path.read_text(encoding="utf-8"))
            if m.get("metadata_mode") == "direct_source" and m.get("source_dir"):
                return Path(str(m["source_dir"])).expanduser().resolve()
        except Exception:
            pass

    # If legacy wiki/raw exists with files, preserve legacy behavior
    legacy_raw = project_root / WIKI_DIR_NAME / "raw"
    if legacy_raw.is_dir() and any(legacy_raw.rglob("*.md")):
        return None

    # Sibling convention: `<name>（知识库）` -> `<name>`
    for suffix in ("（知识库）", "(知识库)", "知识库"):
        if project_root.name.endswith(suffix) and len(project_root.name) > len(suffix):
            stem = project_root.name[: -len(suffix)].rstrip(" -_")
            sibling = project_root.parent / stem
            if sibling.is_dir() and sibling.resolve() != project_root.resolve():
                return sibling.resolve()
    return None


def project_wiki_mode(project_root: Path, override: str | None = None) -> str:
    if override:
        if override not in VALID_WIKI_MODES:
            raise SystemExit(f"Invalid wiki_mode '{override}'; expected one of: {', '.join(VALID_WIKI_MODES)}")
        return override
    cfg_path = project_config_path(project_root)
    if cfg_path:
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
        except Exception:
            data = {}
        if isinstance(data, dict) and data.get("wiki_mode"):
            mode = str(data["wiki_mode"]).strip()
            if mode not in VALID_WIKI_MODES:
                raise SystemExit(f"Invalid wiki_mode '{mode}' in {cfg_path}")
            return mode
    raw_manifest_path = project_root / INDEX_DIR_NAME / RAW_INDEX_NAME / "manifest.json"
    if raw_manifest_path.is_file():
        try:
            m = json.loads(raw_manifest_path.read_text(encoding="utf-8"))
            if m.get("wiki_mode") in VALID_WIKI_MODES:
                return str(m["wiki_mode"])
        except Exception:
            pass
    return DEFAULT_WIKI_MODE


def project_build_settings(project_root: Path) -> dict[str, object]:
    cfg_path = project_config_path(project_root)
    if not cfg_path:
        return {}
    data = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        return {}
    expected: dict[str, object] = {}
    if "wiki_mode" in data:
        expected["wiki_mode"] = data["wiki_mode"]
    weknora = data.get("weknora")
    if isinstance(weknora, dict) and weknora.get("embedding_model_id"):
        expected["embedding_model"] = weknora["embedding_model_id"]
    build = data.get("build")
    if isinstance(build, dict):
        if "model" in build and "embedding_model" not in expected:
            expected["embedding_model"] = build["model"]
        for key in ("chunk_size", "overlap", "dimensions", "encoding_format"):
            if key in build:
                expected[key] = build[key]
    return expected


def describe_delta(
    label: str,
    new_or_changed: list[str],
    deleted: list[str],
    *,
    action_hint: bool = False,
) -> str:
    if action_hint:
        parts = []
        if new_or_changed:
            parts.append(f"{len(new_or_changed)} 个新增/改动，需要增量同步到 WeKnora 索引")
        if deleted:
            parts.append(f"{len(deleted)} 个删除，需要从 WeKnora 索引移除对应条目")
        return f"{label} 有" + "；".join(parts)
    parts = []
    if new_or_changed:
        parts.append(f"{len(new_or_changed)} 个新增/改动")
    if deleted:
        parts.append(f"{len(deleted)} 个删除")
    return f"{label} 有" + "、".join(parts)


def graph_hashes(project_root: Path) -> dict[str, str]:
    wiki_dir = project_root / WIKI_DIR_NAME
    return compute_hashes(
        wiki_dir,
        include_dirs=WIKI_INDEX_SOURCE_DIRS,
        exclude_dirs=("raw", "_archive"),
    )


def raw_enrichment_hashes(project_root: Path) -> dict[str, str]:
    wiki_dir = project_root / WIKI_DIR_NAME
    return compute_hashes(
        wiki_dir,
        include_dirs=RAW_ENRICHMENT_SOURCE_DIRS,
        exclude_dirs=("raw", "_archive"),
    )


def raw_expected_metadata_mode(project_root: Path, wiki_mode: str | None = None, direct_source: bool = False) -> str:
    if direct_source:
        return "direct_source"
    cfg_path = project_config_path(project_root)
    if cfg_path:
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
            explicit_mm = (data.get("build") or {}).get("metadata_mode") if isinstance(data.get("build"), dict) else None
            if explicit_mm in {"plain", "enriched_raw", "direct_source"}:
                return str(explicit_mm)
        except Exception:
            pass
    mode = wiki_mode or project_wiki_mode(project_root)
    if mode == "weknora_native":
        return "plain"
    return "enriched_raw" if graph_hashes(project_root) else "plain"


def raw_allowed_metadata_modes(project_root: Path, wiki_mode: str | None = None, direct_source: bool = False) -> set[str]:
    if direct_source:
        return {"direct_source"}
    cfg_path = project_config_path(project_root)
    if cfg_path:
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
            explicit_mm = (data.get("build") or {}).get("metadata_mode") if isinstance(data.get("build"), dict) else None
            if explicit_mm in {"plain", "enriched_raw", "direct_source"}:
                return {str(explicit_mm), "direct_source"}
        except Exception:
            pass
    mode = wiki_mode or project_wiki_mode(project_root)
    if mode == "weknora_native":
        return {"plain", "direct_source"}
    return {"enriched_raw", "direct_source"} if graph_hashes(project_root) else {"plain", "enriched_raw", "direct_source"}


def find_lint_script(project_root: Path, *, include_script_relative: bool = False) -> Path | None:
    bases = [project_root, *project_root.parents]
    candidates: list[Path] = []
    if include_script_relative:
        candidates.append(
            Path(__file__).resolve().parents[2] / "karpathy-wiki" / "scripts" / "lint.py"
        )
    for base in bases:
        candidates.extend([
            base / "skills" / "karpathy-wiki" / "scripts" / "lint.py",
            base / "skills-hermes" / "research" / "karpathy-wiki" / "scripts" / "lint.py",
        ])
    env_dir = os.environ.get("KB_SKILLS_DIR")
    if env_dir:
        candidates.insert(0, Path(env_dir) / "karpathy-wiki" / "scripts" / "lint.py")
    candidates.extend([
        Path.home() / ".claude" / "skills" / "karpathy-wiki" / "scripts" / "lint.py",
        Path.home() / ".agents" / "skills" / "karpathy-wiki" / "scripts" / "lint.py",
        Path.home() / ".codex" / "skills" / "karpathy-wiki" / "scripts" / "lint.py",
        Path.home() / ".hermes" / "skills" / "karpathy-wiki" / "scripts" / "lint.py",
        Path.home() / ".hermes" / "skills" / "research" / "karpathy-wiki" / "scripts" / "lint.py",
    ])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def run_wiki_lint(
    project_root: Path,
    *,
    return_summary: bool = False,
    include_script_relative: bool = False,
) -> str | None:
    lint_script = find_lint_script(project_root, include_script_relative=include_script_relative)
    wiki_dir = project_root / WIKI_DIR_NAME

    if return_summary:
        if lint_script is None:
            return "未找到 karpathy-wiki lint.py，已跳过 wiki lint。"
        if not wiki_dir.is_dir():
            return f"wiki 目录不存在，已跳过 wiki lint: {wiki_dir}"
        result = subprocess.run(
            [sys.executable, str(lint_script), str(wiki_dir)],
            cwd=str(project_root),
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        if result.returncode != 0:
            return "wiki lint 运行失败: " + (result.stderr.strip() or result.stdout.strip())
        try:
            report = json.loads(result.stdout)
        except json.JSONDecodeError:
            return "wiki lint 输出不是 JSON，已跳过摘要。"
        findings = report.get("findings") or {}
        counts = {k: len(v) for k, v in findings.items() if isinstance(v, list) and v}
        if not counts:
            return "wiki lint: 无结构性告警。"
        summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        return f"wiki lint: {summary}"

    if lint_script and wiki_dir.is_dir():
        subprocess.run(
            [sys.executable, str(lint_script), str(wiki_dir)],
            cwd=str(project_root),
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
    return None
