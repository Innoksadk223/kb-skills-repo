#!/usr/bin/env python3
"""Shared helpers for the social-science-km RAG reference scripts.

``km_query.py`` (read-only query/routing) and ``check_rebuild_rag.py`` (index
maintenance) used to carry near-identical copies of these helpers. This module
is the single source of truth so the two CLIs cannot drift apart again.

Each script imports this module by resolving its *own* directory, so both work
when invoked as a script from any current working directory:

  python3 <skills-repo>/skills/social-science-km/references/km_query.py --project-root <project-root> "你的问题"
  python3 <skills-repo>/skills/social-science-km/references/check_rebuild_rag.py --project-root <project-root> --check

If you copy one of those helpers into a project root, you must copy
``km_rag_common.py`` alongside it as well, otherwise the helper cannot import
its shared logic.

A few helpers have deliberately different behaviour in the two CLIs. Those are
preserved through explicit keyword arguments instead of picking one side:

* :func:`describe_delta` -- ``action_hint`` toggles the maintenance wording used
  by ``check_rebuild_rag.py``.
* :func:`find_lint_script` -- ``include_script_relative`` toggles the
  skills-repo-relative candidate that only ``check_rebuild_rag.py`` searched.
* :func:`run_wiki_lint` -- ``return_summary`` selects whether the report is
  returned for ``km_query.py`` or printed by ``check_rebuild_rag.py``.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


WIKI_DIR_NAME = "wiki"
INDEX_DIR_NAME = "检索索引"
RAW_INDEX_NAME = "raw"
WIKI_INDEX_NAME = "wiki"
WIKI_INDEX_SOURCE_DIRS = ("claims", "concepts", "entities", "comparisons", "debates", "observations", "structures", "predicts", "synthesis", "queries")
RAW_ENRICHMENT_SOURCE_DIRS = ("claims", "concepts", "comparisons", "entities", "debates", "observations", "structures", "predicts")
SKIP_NAMES = {"_conversion_failures.md", "_conversion_manifest.md", "_主题索引.md"}


def path_matches_dir(rel_path: Path, dirs: set[str] | tuple[str, ...]) -> bool:
    rel = rel_path.as_posix()
    return any(rel == folder or rel.startswith(f"{folder}/") for folder in dirs)


def compute_hashes(
    md_dir: Path,
    include_dirs: tuple[str, ...] | set[str] | None = None,
    exclude_dirs: tuple[str, ...] | set[str] | None = None,
) -> dict[str, str]:
    """Return {relative_path: sha256_hex} for Markdown files under md_dir.

    Reads utf-8 with ``errors="replace"``, strips a leading BOM, and hashes the
    resulting text with sha256. ``include_dirs``/``exclude_dirs`` accept ``None``
    as well as a tuple/set of directory names.
    """
    include_dirs = include_dirs or ()
    exclude_dirs = exclude_dirs or ()
    hashes: dict[str, str] = {}
    if not md_dir.is_dir():
        return hashes
    for path in sorted(md_dir.rglob("*.md")):
        rel_path = path.relative_to(md_dir)
        if path.name.startswith("_") or path.name in SKIP_NAMES:
            continue
        if any(part.startswith(".") for part in rel_path.parts):
            continue
        if include_dirs and not path_matches_dir(rel_path, include_dirs):
            continue
        if exclude_dirs and path_matches_dir(rel_path, exclude_dirs):
            continue
        content = path.read_text(encoding="utf-8", errors="replace").lstrip("\ufeff")
        hashes[rel_path.as_posix()] = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return hashes


def project_build_settings(project_root: Path) -> dict[str, object]:
    config_path = project_root / "rag_config.json"
    if not config_path.is_file():
        return {}
    data = json.loads(config_path.read_text(encoding="utf-8"))
    build = data.get("build") if isinstance(data, dict) else None
    if not isinstance(build, dict):
        return {}
    expected: dict[str, object] = {}
    if "model" in build:
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
    """Summarize a hash delta between the current sources and a manifest.

    ``action_hint=False`` (default) produces the terse wording used by
    ``km_query.py`` in its stale-index warning. ``action_hint=True`` appends the
    maintenance instruction used by ``check_rebuild_rag.py`` in its update flow.
    """
    if action_hint:
        parts = []
        if new_or_changed:
            parts.append(f"{len(new_or_changed)} 个新增/改动，需要增量更新索引")
        if deleted:
            parts.append(f"{len(deleted)} 个删除，需要从索引移除对应条目")
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


def raw_expected_metadata_mode(project_root: Path) -> str:
    """Default build mode: plain before graph pages, enriched_raw after graph pages."""
    return "enriched_raw" if graph_hashes(project_root) else "plain"


def raw_allowed_metadata_modes(project_root: Path) -> set[str]:
    """Before graph pages exist, both plain and enriched_raw are valid."""
    return {"enriched_raw"} if graph_hashes(project_root) else {"plain", "enriched_raw"}


def find_lint_script(project_root: Path, *, include_script_relative: bool = False) -> Path | None:
    """Locate ``karpathy-wiki`` ``lint.py``.

    ``include_script_relative=True`` additionally searches the copy installed
    next to this skills repo (the behaviour of ``check_rebuild_rag.py``);
    ``False`` keeps the search rooted at the project/env/home candidates only
    (the behaviour of ``km_query.py``).
    """
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
    """Run ``karpathy-wiki`` ``lint.py`` if it can be found.

    ``return_summary=True`` reproduces ``km_query.py``: never prints, returns a
    short summary string for the caller to embed in the stale-index warning.

    ``return_summary=False`` reproduces ``check_rebuild_rag.py``: prints the
    report under a ``[LINT] `` prefix (truncated to 1200 chars) and returns
    ``None``.
    """
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
        if not findings:
            return "wiki lint: 未发现结构问题。"
        severe = [key for key in ["broken_links", "source_drift", "claim_structure", "frontmatter"] if key in findings]
        if severe:
            return "wiki lint: 发现需优先处理的问题: " + ", ".join(severe)
        return "wiki lint: 发现一般问题: " + ", ".join(sorted(findings))

    if lint_script is None:
        print("[LINT] 未找到 karpathy-wiki lint.py，跳过。")
        return None
    if not wiki_dir.is_dir():
        print(f"[LINT] wiki 目录不存在，跳过: {wiki_dir}")
        return None
    result = subprocess.run(
        [sys.executable, str(lint_script), str(wiki_dir)],
        cwd=str(project_root),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    summary = result.stdout.strip() or result.stderr.strip()
    if result.returncode != 0:
        print("[LINT] wiki lint 运行失败: " + summary)
    elif summary:
        print("[LINT] " + summary[:1200])
    return None
