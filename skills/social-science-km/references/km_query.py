#!/usr/bin/env python3
"""
KM unified query interface.

Run the maintained helper with an explicit knowledge-base project root:
  python3 <skills-repo>/skills/social-science-km/references/km_query.py --project-root <project-root> "你的问题"
  # Add --raw-only for raw evidence, or --deep when evidence quality needs escalation.
Existing copies in project roots remain supported.

Layout: the RAG layout constants and the helpers shared with
``check_rebuild_rag.py`` (hashing, staleness inputs, lint) now live in
``km_rag_common.py`` next to this file, imported via this script's own
directory so the CLI still works from any current working directory.

If you copy this helper into a project root, you must copy
``km_rag_common.py`` alongside it as well.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# The full shared surface is re-exported so existing references such as
# ``km_query.compute_hashes`` / ``km_query.graph_hashes`` keep resolving.
try:
    from km_rag_common import (
        INDEX_DIR_NAME,
        RAW_ENRICHMENT_SOURCE_DIRS,
        RAW_INDEX_NAME,
        SKIP_NAMES,
        WIKI_DIR_NAME,
        WIKI_INDEX_NAME,
        WIKI_INDEX_SOURCE_DIRS,
        compute_hashes,
        describe_delta,
        find_lint_script,
        graph_hashes,
        path_matches_dir,
        project_build_settings,
        raw_allowed_metadata_modes,
        raw_enrichment_hashes,
        raw_expected_metadata_mode,
        run_wiki_lint,
    )
except ImportError as exc:  # pragma: no cover - guidance when a copy is incomplete
    raise SystemExit(
        "km_query.py 需要同目录的 km_rag_common.py（把 helper 复制到项目根目录时请一并复制）。原始错误: "
        f"{exc}"
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parent


@dataclass
class StalenessStatus:
    stale: bool
    message: str
    raw_stale: bool = False
    wiki_stale: bool = False


def project_path(project_root: Path, *parts: str) -> Path:
    return project_root.joinpath(*parts)


def index_manifest(index_dir: Path) -> dict:
    manifest_path = index_dir / "manifest.json"
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def compare_hashes(current: dict[str, str], stored: dict[str, str]) -> tuple[list[str], list[str]]:
    new_or_changed = [
        rel for rel, digest in current.items()
        if rel not in stored or stored[rel] != digest
    ]
    deleted = [rel for rel in stored if rel not in current]
    return new_or_changed, deleted


def check_one_index(
    source_dir: Path,
    index_dir: Path,
    label: str,
    include_dirs: tuple[str, ...] | None = None,
    exclude_dirs: tuple[str, ...] | None = None,
    expected_metadata_mode: str | None = None,
    allowed_metadata_modes: set[str] | None = None,
    dependency_hashes: dict[str, str] | None = None,
    dependency_manifest_key: str | None = None,
    dependency_message: str | None = None,
    expected_settings: dict[str, object] | None = None,
) -> tuple[bool, str]:
    current = compute_hashes(source_dir, include_dirs=include_dirs, exclude_dirs=exclude_dirs)
    manifest = index_manifest(index_dir)
    if not current and not manifest:
        return False, ""
    if not source_dir.is_dir():
        return True, f"{label} 源目录不存在: {source_dir}"
    if not manifest:
        return True, f"{label} 索引不存在，需要先构建"
    manifest_mode = manifest.get("metadata_mode")
    if allowed_metadata_modes and manifest_mode not in allowed_metadata_modes:
        modes = "/".join(sorted(allowed_metadata_modes))
        return True, f"{label} 索引 metadata_mode={manifest_mode}，需要按 {modes} 重建"
    if expected_metadata_mode and manifest_mode != expected_metadata_mode:
        return True, f"{label} 索引 metadata_mode={manifest.get('metadata_mode')}，需要按 {expected_metadata_mode} 重建"
    settings_mismatch = [
        key for key, expected in (expected_settings or {}).items()
        if manifest.get(key) != expected
    ]
    if settings_mismatch:
        return True, f"{label} 索引配置已变化，需要重建: {', '.join(settings_mismatch)}"
    stored = manifest.get("file_hashes")
    if not isinstance(stored, dict):
        return True, f"{label} manifest 缺少 file_hashes，需要重建以支持增量检查"
    if dependency_hashes is not None and dependency_manifest_key:
        stored_dependencies = manifest.get(dependency_manifest_key)
        if not isinstance(stored_dependencies, dict):
            return True, f"{label} manifest 缺少 {dependency_manifest_key}，需要重建以跟踪 Wiki 语义标签"
    else:
        stored_dependencies = None
    new_or_changed, deleted = compare_hashes(current, stored)
    dependencies_changed = stored_dependencies is not None and stored_dependencies != dependency_hashes
    if new_or_changed or deleted or dependencies_changed:
        messages = []
        if new_or_changed or deleted:
            messages.append(describe_delta(label, new_or_changed, deleted, action_hint=False))
        if dependencies_changed:
            messages.append(dependency_message or f"{label} 的依赖内容有改动")
        return True, "；".join(messages)
    return False, ""


def check_staleness(project_root: Path) -> StalenessStatus:
    wiki_dir = project_path(project_root, WIKI_DIR_NAME)
    index_root = project_path(project_root, INDEX_DIR_NAME)

    raw_mode = raw_expected_metadata_mode(project_root)
    expected_settings = project_build_settings(project_root)
    raw_stale, raw_msg = check_one_index(
        source_dir=wiki_dir / "raw",
        index_dir=index_root / RAW_INDEX_NAME,
        label="raw",
        allowed_metadata_modes=raw_allowed_metadata_modes(project_root),
        dependency_hashes=raw_enrichment_hashes(project_root) if raw_mode == "enriched_raw" else None,
        dependency_manifest_key="semantic_source_hashes" if raw_mode == "enriched_raw" else None,
        dependency_message="raw 使用的 Wiki 语义标签有改动",
        expected_settings=expected_settings,
    )
    wiki_stale, wiki_msg = check_one_index(
        source_dir=wiki_dir,
        index_dir=index_root / WIKI_INDEX_NAME,
        label="wiki",
        include_dirs=WIKI_INDEX_SOURCE_DIRS,
        exclude_dirs=("raw", "_archive"),
        expected_metadata_mode="wiki",
        expected_settings=expected_settings,
    )

    messages = [msg for msg in [raw_msg, wiki_msg] if msg]
    return StalenessStatus(
        stale=bool(raw_stale or wiki_stale),
        message="；".join(messages),
        raw_stale=raw_stale,
        wiki_stale=wiki_stale,
    )


def find_query_script(project_root: Path) -> Path:
    bases = [project_root, *project_root.parents]
    reference_skills_dir = Path(__file__).resolve().parents[2]
    candidates: list[Path] = [reference_skills_dir / "SiliconFlow-rag" / "scripts" / "query_index.py"]
    for base in bases:
        candidates.extend([
            base / "skills" / "SiliconFlow-rag" / "scripts" / "query_index.py",
            base / "skills-hermes" / "research" / "SiliconFlow-rag" / "scripts" / "query_index.py",
        ])
    env_dir = os.environ.get("KB_SKILLS_DIR")
    if env_dir:
        candidates.insert(0, Path(env_dir) / "SiliconFlow-rag" / "scripts" / "query_index.py")
    candidates.extend([
        Path.home() / ".claude" / "skills" / "SiliconFlow-rag" / "scripts" / "query_index.py",
        Path.home() / ".agents" / "skills" / "SiliconFlow-rag" / "scripts" / "query_index.py",
        Path.home() / ".codex" / "skills" / "SiliconFlow-rag" / "scripts" / "query_index.py",
        Path.home() / ".hermes" / "skills" / "SiliconFlow-rag" / "scripts" / "query_index.py",
        Path.home() / ".hermes" / "skills" / "research" / "SiliconFlow-rag" / "scripts" / "query_index.py",
    ])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise SystemExit("Cannot find SiliconFlow-rag query_index.py; install the skill or set KB_SKILLS_DIR=<skills 根目录>.")


def raw_lookup_intent(question: str) -> bool:
    lowered = question.lower()
    # "证据" was removed on purpose: conceptual questions like "有什么证据支持孝是仁之本？"
    # need wiki argument structure, so that marker must not force raw-only routing.
    # Do not re-add it; keep only genuine source-lookup markers here.
    raw_markers = ["原文", "出处", "哪一段", "引用", "页码", "source", "quote", "citation", "passage"]
    return any(marker in question or marker in lowered for marker in raw_markers)


def choose_mode(question: str, raw_only: bool, deep: bool, project_root: Path) -> str:
    if raw_only:
        return "raw"
    wiki_manifest = project_path(project_root, INDEX_DIR_NAME, WIKI_INDEX_NAME, "manifest.json")
    if deep and wiki_manifest.exists():
        return "wiki"
    if raw_lookup_intent(question):
        return "raw"
    if wiki_manifest.exists():
        return "wiki"
    return "raw"


def build_query_command(
    project_root: Path,
    query_script: Path,
    question: str,
    mode: str,
    expand_context: bool,
    rerank: bool,
    multi_query: bool,
    candidates: int | None,
    source_discovery: bool = False,
) -> list[str]:
    index_root = project_path(project_root, INDEX_DIR_NAME)
    cmd = [sys.executable, str(query_script)]
    config_path = project_path(project_root, "rag_config.json")
    if config_path.is_file():
        cmd.extend(["--config", str(config_path)])
    if mode == "wiki":
        cmd.extend([
            "--wiki-first",
            "--wiki-index-dir", str(index_root / WIKI_INDEX_NAME),
            "--raw-index-dir", str(index_root / RAW_INDEX_NAME),
        ])
    else:
        cmd.extend(["--index-dir", str(index_root / RAW_INDEX_NAME)])
    cmd.extend(["--question", question])
    if expand_context:
        cmd.append("--expand-context")
    if rerank:
        cmd.append("--rerank")
    if multi_query:
        cmd.append("--multi-query")
    if source_discovery:
        cmd.append("--source-discovery")
    if candidates:
        cmd.extend(["--candidates", str(candidates)])
    return cmd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query a social-science KM RAG project.")
    parser.add_argument("question", nargs="?", help="用户问题；配合 --check 可省略")
    parser.add_argument("--project-root", default=None, help="知识库项目根目录，默认是 km_query.py 所在目录")
    parser.add_argument("--check", action="store_true", help="只检查 raw/wiki 索引是否过期，不执行查询")
    parser.add_argument("--skip-check", action="store_true", help="跳过索引新旧检查，直接查询当前索引")
    parser.add_argument("--raw-only", action="store_true", help="只查 raw evidence 索引，不使用 wiki-first")
    parser.add_argument("--no-context", action="store_true", help="不补相邻 chunk")
    parser.add_argument("--rerank", action="store_true", help="启用 rerank 精排")
    parser.add_argument("--multi-query", action="store_true", help="启用多查询改写以提高召回")
    parser.add_argument("--deep", action="store_true", help="精读/写作档：wiki-first + multi-query + rerank + context")
    parser.add_argument("--source-discovery", action="store_true", help="输出候选 Raw 来源清单、体量提示与深读分流线索")
    parser.add_argument("--candidates", type=int, default=None, help="rerank 前候选数；--deep 默认 20，普通默认由 query_index.py 决定")
    parser.add_argument("--timeout", type=int, default=120, help="查询命令超时时间（秒）")
    parser.add_argument("--no-lint", action="store_true", help="索引过期时不运行 wiki lint 摘要")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve() if args.project_root else PROJECT_ROOT

    if not args.question and not args.check:
        raise SystemExit("用法: python3 km_query.py \"你的问题\" [--raw-only|--deep|--skip-check]")

    mode = None if args.check else choose_mode(
        args.question, raw_only=args.raw_only, deep=args.deep, project_root=project_root,
    )
    if args.check or not args.skip_check:
        status = check_staleness(project_root)
        blocking = status.raw_stale if mode == "raw" else status.stale
        if status.stale and not blocking:
            print(f"[NOTE] wiki 索引过期（{status.message}）；raw-only 查询不受影响，继续。")
        if blocking:
            print(f"[WARN] RAG 索引过期：{status.message}")
            if status.wiki_stale and not args.no_lint:
                print("[LINT] " + run_wiki_lint(project_root, return_summary=True, include_script_relative=False))
            print("[HINT] 先运行增量更新脚本补入索引；确认要临时查询旧索引时再加 --skip-check。")
            sys.exit(1)

    if args.check:
        print("RAG 索引状态：当前")
        return

    assert args.question is not None and mode is not None
    query_script = find_query_script(project_root)
    cmd = build_query_command(
        project_root=project_root,
        query_script=query_script,
        question=args.question,
        mode=mode,
        expand_context=not args.no_context,
        rerank=args.rerank or args.deep,
        multi_query=args.multi_query or args.deep,
        candidates=args.candidates or (20 if args.deep else None),
        source_discovery=args.source_discovery,
    )
    mode_label = "wiki-first" if mode == "wiki" else "raw-only"
    if args.source_discovery:
        mode_label += " + source-discovery"
    print(f"[MODE] {mode_label}")
    result = subprocess.run(
        cmd,
        cwd=str(project_root),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=args.timeout,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
