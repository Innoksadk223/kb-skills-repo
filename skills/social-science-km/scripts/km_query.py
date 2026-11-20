#!/usr/bin/env python3
"""
KM unified query interface (WeKnora RAG + Dual-Mode Wiki).

Run with an explicit knowledge-base project root:
  python3 <skills-repo>/skills/social-science-km/scripts/km_query.py --project-root <project-root> "你的问题"
  # Supports both --wiki-mode local_karpathy (default, thesis-grade local Wiki)
  # and --wiki-mode weknora_native (automated WeKnora Web Wiki).
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

from km_rag_common import (  # noqa: E402
    INDEX_DIR_NAME,
    RAW_INDEX_NAME,
    SUPPORTED_SOURCE_EXTS,
    VALID_WIKI_MODES,
    WIKI_DIR_NAME,
    WIKI_INDEX_NAME,
    WIKI_INDEX_SOURCE_DIRS,
    compute_hashes,
    describe_delta,
    project_build_settings,
    project_config_path,
    project_source_dir,
    project_wiki_mode,
    raw_allowed_metadata_modes,
    raw_enrichment_hashes,
    raw_expected_metadata_mode,
    run_wiki_lint,
)


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
    allowed_exts: set[str] | None = None,
    expected_metadata_mode: str | None = None,
    allowed_metadata_modes: set[str] | None = None,
    dependency_hashes: dict[str, str] | None = None,
    dependency_manifest_key: str | None = None,
    dependency_message: str | None = None,
    expected_settings: dict[str, object] | None = None,
) -> tuple[bool, str]:
    current = compute_hashes(source_dir, include_dirs=include_dirs, exclude_dirs=exclude_dirs, allowed_exts=allowed_exts)
    manifest = index_manifest(index_dir)
    if not current and not manifest:
        return False, ""
    if not source_dir.is_dir():
        return True, f"{label} 源目录不存在: {source_dir}"
    if not manifest:
        return True, f"{label} 索引不存在，需要先同步构建"
    manifest_mode = manifest.get("metadata_mode")
    if manifest_mode == "plain" and "plain" in (allowed_metadata_modes or set()):
        dependency_hashes = None
        dependency_manifest_key = None
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
    stored_remote = manifest.get("remote_docs") if isinstance(manifest.get("remote_docs"), dict) else {}
    new_or_changed, deleted = compare_hashes(current, stored)
    deleted = [
        rel
        for rel in deleted
        if not (
            rel in stored_remote
            and (
                str((stored_remote.get(rel) or {}).get("file_type") or "") == "pdf"
                or Path(rel).name.startswith("_")
            )
        )
    ]
    dependencies_changed = stored_dependencies is not None and stored_dependencies != dependency_hashes
    if new_or_changed or deleted or dependencies_changed:
        messages = []
        if new_or_changed or deleted:
            messages.append(describe_delta(label, new_or_changed, deleted, action_hint=False))
        if dependencies_changed:
            messages.append(dependency_message or f"{label} 的依赖内容有改动")
        return True, "；".join(messages)
    return False, ""


def check_staleness(
    project_root: Path,
    wiki_mode: str | None = None,
    explicit_source_dir: str | None = None,
) -> StalenessStatus:
    wiki_dir = project_path(project_root, WIKI_DIR_NAME)
    index_root = project_path(project_root, INDEX_DIR_NAME)
    mode = project_wiki_mode(project_root, wiki_mode)
    sdir = project_source_dir(project_root, explicit_source_dir)
    is_direct = sdir is not None

    raw_src = sdir if is_direct else (wiki_dir / "raw")
    raw_mode = raw_expected_metadata_mode(project_root, wiki_mode=mode, direct_source=is_direct)
    expected_settings = project_build_settings(project_root)
    raw_stale, raw_msg = check_one_index(
        source_dir=raw_src,
        index_dir=index_root / RAW_INDEX_NAME,
        label="raw",
        allowed_exts=SUPPORTED_SOURCE_EXTS if is_direct else {".md"},
        allowed_metadata_modes=raw_allowed_metadata_modes(project_root, wiki_mode=mode, direct_source=is_direct),
        dependency_hashes=raw_enrichment_hashes(project_root) if raw_mode == "enriched_raw" else None,
        dependency_manifest_key="semantic_source_hashes" if raw_mode == "enriched_raw" else None,
        dependency_message="raw 使用的 Wiki 语义标签有改动",
        expected_settings=expected_settings,
    )

    if mode == "weknora_native":
        wiki_stale, wiki_msg = False, ""
    else:
        wiki_stale, wiki_msg = check_one_index(
            source_dir=wiki_dir,
            index_dir=index_root / WIKI_INDEX_NAME,
            label="wiki",
            include_dirs=WIKI_INDEX_SOURCE_DIRS,
            exclude_dirs=("raw", "_archive"),
            allowed_exts={".md"},
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
    local_query = SCRIPT_DIR / "query_kb.py"
    if local_query.is_file():
        return local_query
    bases = [project_root, *project_root.parents]
    candidates: list[Path] = []
    for base in bases:
        candidates.append(base / "skills" / "social-science-km" / "scripts" / "query_kb.py")
    env_dir = os.environ.get("KB_SKILLS_DIR")
    if env_dir:
        candidates.insert(0, Path(env_dir) / "social-science-km" / "scripts" / "query_kb.py")
    for root in (".agents", ".claude", ".codex", ".hermes"):
        candidates.append(Path.home() / root / "skills" / "social-science-km" / "scripts" / "query_kb.py")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise SystemExit("Cannot find social-science-km/scripts/query_kb.py")


def raw_lookup_intent(question: str) -> bool:
    lowered = question.lower()
    raw_markers = ["原文", "出处", "哪一段", "引用", "页码", "source", "quote", "citation", "passage"]
    return any(marker in question or marker in lowered for marker in raw_markers)


def choose_mode(
    question: str,
    raw_only: bool,
    deep: bool,
    project_root: Path,
    wiki_mode: str | None = None,
) -> str:
    if raw_only:
        return "raw"
    wmode = project_wiki_mode(project_root, wiki_mode)
    if wmode == "weknora_native":
        raw_manifest = project_path(project_root, INDEX_DIR_NAME, RAW_INDEX_NAME, "manifest.json")
        if deep and raw_manifest.exists():
            return "wiki"
        if raw_lookup_intent(question):
            return "raw"
        return "wiki" if raw_manifest.exists() else "raw"

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
    wiki_mode: str | None = None,
    mock: bool = False,
) -> list[str]:
    index_root = project_path(project_root, INDEX_DIR_NAME)
    wmode = project_wiki_mode(project_root, wiki_mode)
    cmd = [sys.executable, str(query_script)]
    cfg_path = project_config_path(project_root)
    if cfg_path is not None:
        cmd.extend(["--config", str(cfg_path)])
    if wiki_mode:
        cmd.extend(["--wiki-mode", wmode])
    if mode == "wiki":
        cmd.append("--wiki-first")
        if wmode != "weknora_native":
            cmd.extend(["--wiki-index-dir", str(index_root / WIKI_INDEX_NAME)])
        cmd.extend(["--raw-index-dir", str(index_root / RAW_INDEX_NAME)])
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
    if mock:
        cmd.append("--mock")
    return cmd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query a social-science KM WeKnora RAG project.")
    parser.add_argument("question", nargs="?", help="用户问题；配合 --check 可省略")
    parser.add_argument("--project-root", default=None, help="知识库项目根目录，默认是当前目录")
    parser.add_argument("--source-dir", default=None, help="新建知识库的原始资料文件夹（检查新旧时使用）")
    parser.add_argument("--wiki-mode", default=None, choices=list(VALID_WIKI_MODES), help="local_karpathy（默认，本地社科 Wiki）| weknora_native（WeKnora 自动 Wiki）")
    parser.add_argument("--check", action="store_true", help="只检查 raw/wiki 索引是否过期，不执行查询")
    parser.add_argument("--skip-check", action="store_true", help="跳过索引新旧检查，直接查询当前索引")
    parser.add_argument("--raw-only", action="store_true", help="只查 raw evidence 索引，不使用 wiki-first")
    parser.add_argument("--no-context", action="store_true", help="不补相邻 chunk")
    parser.add_argument("--rerank", action="store_true", help="启用 WeKnora rerank 精排")
    parser.add_argument("--multi-query", action="store_true", help="启用多查询改写以提高召回")
    parser.add_argument("--deep", action="store_true", help="精读/写作档：wiki-first + multi-query + rerank + context")
    parser.add_argument("--source-discovery", action="store_true", help="输出候选来源清单、体量提示与深读分流线索")
    parser.add_argument("--candidates", type=int, default=None, help="rerank 前候选数；--deep 默认 20")
    parser.add_argument("--timeout", type=int, default=120, help="查询命令超时时间（秒）")
    parser.add_argument("--no-lint", action="store_true", help="不附带 wiki lint 状态摘要")
    parser.add_argument("--mock", action="store_true", help="使用本地离线 mock 后端")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve() if args.project_root else Path.cwd().resolve()
    wmode = project_wiki_mode(project_root, args.wiki_mode)

    if args.check:
        status = check_staleness(project_root, wiki_mode=args.wiki_mode, explicit_source_dir=args.source_dir)
        if not args.no_lint and wmode == "local_karpathy":
            lint_note = run_wiki_lint(project_root, return_summary=True, include_script_relative=True)
            if lint_note:
                print(f"[LINT] {lint_note}")
        if status.stale:
            print(f"[WARN] RAG 索引已过期：{status.message}")
            print("建议运行：python3 <skills-repo>/skills/social-science-km/scripts/check_rebuild_rag.py --project-root <知识库>")
            raise SystemExit(1)
        print(f"RAG 索引状态：当前（wiki_mode={wmode}）")
        return

    if not args.question:
        raise SystemExit(
            '用法: python3 km_query.py --project-root <知识库> "你的问题" [--wiki-mode local_karpathy|weknora_native] [--raw-only|--deep|--skip-check]'
        )

    mode = choose_mode(args.question, args.raw_only, args.deep, project_root, wiki_mode=args.wiki_mode)

    if not args.skip_check:
        status = check_staleness(project_root, wiki_mode=args.wiki_mode, explicit_source_dir=args.source_dir)
        blocking = status.raw_stale or (mode == "wiki" and status.wiki_stale)
        if blocking:
            print(f"[BLOCKED] 当前查询所需的 RAG 索引已过期：{status.message}")
            print("请先更新索引，或在确认允许使用旧索引时追加 --skip-check。")
            raise SystemExit(1)

    query_script = find_query_script(project_root)
    expand_context = not args.no_context
    rerank = bool(args.rerank or args.deep)
    multi_query = bool(args.multi_query or args.deep)
    candidates = args.candidates or (20 if args.deep else None)

    cmd = build_query_command(
        project_root=project_root,
        query_script=query_script,
        question=args.question,
        mode=mode,
        expand_context=expand_context,
        rerank=rerank,
        multi_query=multi_query,
        candidates=candidates,
        source_discovery=bool(args.source_discovery),
        wiki_mode=wmode,
        mock=bool(args.mock),
    )
    mode_label = f"wiki-first ({wmode})" if mode == "wiki" else "raw-only"
    print(f"[MODE] {mode_label}")
    if not args.no_lint and mode == "wiki" and wmode == "local_karpathy":
        lint_note = run_wiki_lint(project_root, return_summary=True, include_script_relative=True)
        if lint_note:
            print(f"[LINT] {lint_note}")

    result = subprocess.run(
        cmd,
        cwd=str(project_root),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=args.timeout,
    )
    if result.stdout:
        print(result.stdout.rstrip())
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr)
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
