#!/usr/bin/env python3
"""Check and incrementally sync social-science-km WeKnora RAG indexes.

Run with an explicit knowledge-base project root:
  python3 <skills-repo>/skills/social-science-km/scripts/check_rebuild_rag.py --project-root <project-root> --check
  python3 <skills-repo>/skills/social-science-km/scripts/check_rebuild_rag.py --project-root <project-root> [--source-dir <资料夹>]
  # Optional: --wiki-mode local_karpathy | weknora_native
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

PROJECT_ROOT = Path.cwd().resolve()


@dataclass
class IndexStatus:
    label: str
    stale: bool
    message: str
    source_dir: Path
    index_dir: Path
    metadata_mode: str
    allowed_metadata_modes: set[str]
    has_sources: bool
    direct_source: bool = False
    settings_rebuild: bool = False


def read_manifest(index_dir: Path) -> dict:
    manifest_path = index_dir / "manifest.json"
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def check_one(
    project_root: Path,
    label: str,
    source_dir: Path,
    index_dir: Path,
    metadata_mode: str,
    allowed_metadata_modes: set[str] | None = None,
    include_dirs: tuple[str, ...] = (),
    exclude_dirs: tuple[str, ...] = (),
    allowed_exts: set[str] | None = None,
    direct_source: bool = False,
    dependency_hashes: dict[str, str] | None = None,
    dependency_manifest_key: str | None = None,
    dependency_message: str | None = None,
    expected_settings: dict[str, object] | None = None,
) -> IndexStatus:
    current = compute_hashes(source_dir, include_dirs=include_dirs, exclude_dirs=exclude_dirs, allowed_exts=allowed_exts)
    manifest = read_manifest(index_dir)
    stored_mode = manifest.get("metadata_mode")
    if not direct_source and stored_mode == "plain" and "plain" in (allowed_metadata_modes or {metadata_mode}):
        dependency_hashes = None
        dependency_manifest_key = None
    has_sources = bool(current)
    allowed_metadata_modes = allowed_metadata_modes or {metadata_mode}

    if not current and not manifest:
        return IndexStatus(
            label, False, f"{label} 无可索引内容", source_dir, index_dir, metadata_mode, allowed_metadata_modes, has_sources, direct_source=direct_source
        )
    if not source_dir.is_dir():
        return IndexStatus(
            label, True, f"{label} 源目录不存在: {source_dir}", source_dir, index_dir, metadata_mode, allowed_metadata_modes, has_sources, direct_source=direct_source
        )
    if not manifest:
        return IndexStatus(
            label, True, f"{label} 索引不存在，需要先同步构建", source_dir, index_dir, metadata_mode, allowed_metadata_modes, has_sources, direct_source=direct_source
        )
    manifest_mode = manifest.get("metadata_mode")
    if manifest_mode not in allowed_metadata_modes:
        modes = "/".join(sorted(allowed_metadata_modes))
        return IndexStatus(
            label,
            True,
            f"{label} 索引 metadata_mode={manifest_mode}，需要按 {modes} 重建",
            source_dir,
            index_dir,
            metadata_mode,
            allowed_metadata_modes,
            has_sources,
            direct_source=direct_source,
            settings_rebuild=True,
        )
    metadata_mode = str(manifest_mode)
    settings_mismatch = [
        key for key, expected in (expected_settings or {}).items()
        if manifest.get(key) != expected
    ]
    if settings_mismatch:
        return IndexStatus(
            label,
            True,
            f"{label} 索引配置已变化，需要重建: {', '.join(settings_mismatch)}",
            source_dir,
            index_dir,
            metadata_mode,
            allowed_metadata_modes,
            has_sources,
            direct_source=direct_source,
            settings_rebuild=True,
        )
    stored = manifest.get("file_hashes")
    if not isinstance(stored, dict):
        return IndexStatus(
            label,
            True,
            f"{label} manifest 缺少 file_hashes，需要重建以支持增量检查",
            source_dir,
            index_dir,
            metadata_mode,
            allowed_metadata_modes,
            has_sources,
            direct_source=direct_source,
            settings_rebuild=True,
        )
    if dependency_hashes is not None and dependency_manifest_key:
        stored_dependencies = manifest.get(dependency_manifest_key)
        if not isinstance(stored_dependencies, dict):
            return IndexStatus(
                label,
                True,
                f"{label} manifest 缺少 {dependency_manifest_key}，需要重建以跟踪 Wiki 语义标签",
                source_dir,
                index_dir,
                metadata_mode,
                allowed_metadata_modes,
                has_sources,
                direct_source=direct_source,
                settings_rebuild=True,
            )
    else:
        stored_dependencies = None

    # Preserve any extra externally uploaded documents recorded in remote_docs (e.g. root-level PDFs in mixed legacy KBs)
    stored_remote = manifest.get("remote_docs") if isinstance(manifest.get("remote_docs"), dict) else {}
    new_or_changed = [rel for rel, digest in current.items() if rel not in stored or stored[rel] != digest]
    deleted = [
        rel
        for rel in stored
        if rel not in current
        and not (
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
            messages.append(describe_delta(label, new_or_changed, deleted, action_hint=True))
        if dependencies_changed:
            messages.append(dependency_message or f"{label} 的依赖内容有改动，需要增量同步到 WeKnora 索引")
        return IndexStatus(
            label,
            True,
            "；".join(messages),
            source_dir,
            index_dir,
            metadata_mode,
            allowed_metadata_modes,
            has_sources,
            direct_source=direct_source,
        )
    return IndexStatus(
        label, False, f"{label} 当前", source_dir, index_dir, metadata_mode, allowed_metadata_modes, has_sources, direct_source=direct_source
    )


def check_all(
    project_root: Path,
    wiki_mode: str | None = None,
    explicit_source_dir: str | None = None,
) -> list[IndexStatus]:
    wiki_dir = project_root / WIKI_DIR_NAME
    index_root = project_root / INDEX_DIR_NAME
    mode = project_wiki_mode(project_root, wiki_mode)
    sdir = project_source_dir(project_root, explicit_source_dir)
    is_direct = sdir is not None

    raw_source_dir = sdir if is_direct else (wiki_dir / "raw")
    raw_mode = raw_expected_metadata_mode(project_root, wiki_mode=mode, direct_source=is_direct)
    expected_settings = project_build_settings(project_root)
    if wiki_mode:
        expected_settings["wiki_mode"] = mode

    statuses = [
        check_one(
            project_root,
            "raw",
            raw_source_dir,
            index_root / RAW_INDEX_NAME,
            raw_mode,
            allowed_metadata_modes=raw_allowed_metadata_modes(project_root, wiki_mode=mode, direct_source=is_direct),
            allowed_exts=SUPPORTED_SOURCE_EXTS if is_direct else {".md"},
            direct_source=is_direct,
            dependency_hashes=raw_enrichment_hashes(project_root) if raw_mode == "enriched_raw" else None,
            dependency_manifest_key="semantic_source_hashes" if raw_mode == "enriched_raw" else None,
            dependency_message="raw 使用的 Wiki 语义标签有改动，需要增量同步到 WeKnora 索引",
            expected_settings=expected_settings,
        ),
    ]
    if mode != "weknora_native":
        statuses.append(
            check_one(
                project_root,
                "wiki",
                wiki_dir,
                index_root / WIKI_INDEX_NAME,
                "wiki",
                include_dirs=WIKI_INDEX_SOURCE_DIRS,
                exclude_dirs=("raw", "_archive"),
                allowed_exts={".md"},
                direct_source=False,
                expected_settings=expected_settings,
            )
        )
    return statuses


def find_sync_script(project_root: Path) -> Path:
    local_sync = SCRIPT_DIR / "sync_kb.py"
    if local_sync.is_file():
        return local_sync
    bases = [project_root, *project_root.parents]
    candidates: list[Path] = []
    for base in bases:
        candidates.append(base / "skills" / "social-science-km" / "scripts" / "sync_kb.py")
    env_dir = os.environ.get("KB_SKILLS_DIR")
    if env_dir:
        candidates.insert(0, Path(env_dir) / "social-science-km" / "scripts" / "sync_kb.py")
    for root in (".agents", ".claude", ".codex", ".hermes"):
        candidates.append(Path.home() / root / "skills" / "social-science-km" / "scripts" / "sync_kb.py")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise SystemExit("Cannot find social-science-km/scripts/sync_kb.py")


def build_command(
    status: IndexStatus,
    sync_script: Path,
    mock: bool,
    project_root: Path,
    wiki_mode: str,
) -> list[str]:
    cmd = [
        sys.executable,
        str(sync_script),
        "--project-root",
        str(project_root),
        "--wiki-mode",
        wiki_mode,
    ]
    if status.direct_source:
        cmd.extend(["--source-dir", str(status.source_dir)])
    else:
        cmd.extend(["--md-dir", str(status.source_dir)])
    cmd.extend([
        "--index-dir",
        str(status.index_dir),
        "--metadata-mode",
        status.metadata_mode,
        "--incremental",
    ])
    cfg_path = project_config_path(project_root)
    if cfg_path is not None:
        cmd.extend(["--config", str(cfg_path)])
    if status.label == "wiki":
        cmd.extend([
            "--include-dirs",
            ",".join(WIKI_INDEX_SOURCE_DIRS),
            "--exclude-dirs",
            "raw,_archive",
        ])
    if mock:
        cmd.append("--mock")
    return cmd


def apply_updates(
    project_root: Path,
    statuses: list[IndexStatus],
    mock: bool,
    no_lint: bool,
    wiki_mode: str,
) -> int:
    sync_script = find_sync_script(project_root)
    changed = 0
    for status in statuses:
        if not status.stale:
            continue
        if not status.has_sources and not status.index_dir.exists():
            print(f"[SKIP] {status.label}: 无可索引内容。")
            continue
        if status.label == "wiki" and not no_lint and wiki_mode == "local_karpathy":
            run_wiki_lint(project_root, return_summary=False, include_script_relative=True)
        print(f"[UPDATE] {status.message}")
        result = subprocess.run(
            build_command(status, sync_script, mock, project_root, wiki_mode=wiki_mode),
            cwd=str(project_root),
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.returncode != 0:
            if result.stderr.strip():
                print(result.stderr.strip(), file=sys.stderr)
            return result.returncode
        changed += 1
    if changed == 0:
        print(f"RAG 索引状态：当前（wiki_mode={wiki_mode}）")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check or sync social-science-km WeKnora RAG indexes.")
    parser.add_argument("--project-root", default=None, help="知识库项目根目录，默认是当前目录")
    parser.add_argument("--source-dir", default=None, help="新建知识库的原始资料文件夹（PDF/DOCX/MD 等直接入库，无需生成 wiki/raw）")
    parser.add_argument("--wiki-mode", default=None, choices=list(VALID_WIKI_MODES), help="local_karpathy（默认，本地社科 Wiki）| weknora_native（WeKnora 自动 Wiki）")
    parser.add_argument("--check", action="store_true", help="只检查索引是否过期，不执行同步")
    parser.add_argument("--raw-only", action="store_true", help="只检查/同步 raw 索引")
    parser.add_argument("--wiki-only", action="store_true", help="只检查/同步 wiki 索引")
    parser.add_argument("--no-lint", action="store_true", help="同步 wiki 索引前不运行 karpathy-wiki lint")
    parser.add_argument("--mock", action="store_true", help="使用本地离线 mock 后端，用于测试")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve() if args.project_root else Path.cwd().resolve()
    wmode = project_wiki_mode(project_root, args.wiki_mode)
    statuses = check_all(project_root, wiki_mode=args.wiki_mode, explicit_source_dir=args.source_dir)
    if args.raw_only:
        statuses = [status for status in statuses if status.label == "raw"]
    if args.wiki_only:
        statuses = [status for status in statuses if status.label == "wiki"]

    stale = [status for status in statuses if status.stale]
    if args.check:
        if not stale:
            print(f"RAG 索引状态：当前（wiki_mode={wmode}）")
            return
        for status in stale:
            print("[WARN] " + status.message)
        sys.exit(1)

    sys.exit(apply_updates(project_root, statuses, mock=args.mock, no_lint=args.no_lint, wiki_mode=wmode))


if __name__ == "__main__":
    main()
