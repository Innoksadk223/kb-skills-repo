#!/usr/bin/env python3
"""Check and incrementally update social-science-km RAG indexes.

Copy this file to a knowledge-base project root, then run:
  python3 check_rebuild_rag.py --check
  python3 check_rebuild_rag.py

The script keeps raw/wiki index maintenance in one place so agents do not
improvise local rebuild commands.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
WIKI_DIR_NAME = "wiki"
INDEX_DIR_NAME = "检索索引"
RAW_INDEX_NAME = "raw"
WIKI_INDEX_NAME = "wiki"
WIKI_INDEX_SOURCE_DIRS = ("claims", "concepts", "entities", "comparisons", "debates", "synthesis", "queries")
RAW_ENRICHMENT_SOURCE_DIRS = ("claims", "concepts", "comparisons", "entities", "debates")
SKIP_NAMES = {"_conversion_failures.md", "_conversion_manifest.md", "_主题索引.md"}


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
    settings_rebuild: bool = False


def path_matches_dir(rel_path: Path, dirs: tuple[str, ...]) -> bool:
    rel = rel_path.as_posix()
    return any(rel == folder or rel.startswith(f"{folder}/") for folder in dirs)


def compute_hashes(
    md_dir: Path,
    include_dirs: tuple[str, ...] = (),
    exclude_dirs: tuple[str, ...] = (),
) -> dict[str, str]:
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


def read_manifest(index_dir: Path) -> dict:
    manifest_path = index_dir / "manifest.json"
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


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


def describe_delta(label: str, new_or_changed: list[str], deleted: list[str]) -> str:
    parts = []
    if new_or_changed:
        parts.append(f"{len(new_or_changed)} 个新增/改动，需要增量更新索引")
    if deleted:
        parts.append(f"{len(deleted)} 个删除，需要从索引移除对应条目")
    return f"{label} 有" + "；".join(parts)


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
    return "enriched_raw" if graph_hashes(project_root) else "plain"


def raw_allowed_metadata_modes(project_root: Path) -> set[str]:
    return {"enriched_raw"} if graph_hashes(project_root) else {"plain", "enriched_raw"}


def check_one(
    project_root: Path,
    label: str,
    source_dir: Path,
    index_dir: Path,
    metadata_mode: str,
    allowed_metadata_modes: set[str] | None = None,
    include_dirs: tuple[str, ...] = (),
    exclude_dirs: tuple[str, ...] = (),
    dependency_hashes: dict[str, str] | None = None,
    dependency_manifest_key: str | None = None,
    dependency_message: str | None = None,
    expected_settings: dict[str, object] | None = None,
) -> IndexStatus:
    current = compute_hashes(source_dir, include_dirs=include_dirs, exclude_dirs=exclude_dirs)
    manifest = read_manifest(index_dir)
    has_sources = bool(current)
    allowed_metadata_modes = allowed_metadata_modes or {metadata_mode}

    if not current and not manifest:
        return IndexStatus(label, False, f"{label} 无可索引内容", source_dir, index_dir, metadata_mode, allowed_metadata_modes, has_sources)
    if not source_dir.is_dir():
        return IndexStatus(label, True, f"{label} 源目录不存在: {source_dir}", source_dir, index_dir, metadata_mode, allowed_metadata_modes, has_sources)
    if not manifest:
        return IndexStatus(label, True, f"{label} 索引不存在，需要先构建", source_dir, index_dir, metadata_mode, allowed_metadata_modes, has_sources)
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
            settings_rebuild=True,
        )
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
                settings_rebuild=True,
            )
    else:
        stored_dependencies = None
    new_or_changed = [rel for rel, digest in current.items() if rel not in stored or stored[rel] != digest]
    deleted = [rel for rel in stored if rel not in current]
    dependencies_changed = stored_dependencies is not None and stored_dependencies != dependency_hashes
    if new_or_changed or deleted or dependencies_changed:
        messages = []
        if new_or_changed or deleted:
            messages.append(describe_delta(label, new_or_changed, deleted))
        if dependencies_changed:
            messages.append(dependency_message or f"{label} 的依赖内容有改动，需要增量更新索引")
        return IndexStatus(
            label,
            True,
            "；".join(messages),
            source_dir,
            index_dir,
            metadata_mode,
            allowed_metadata_modes,
            has_sources,
        )
    return IndexStatus(label, False, f"{label} 当前", source_dir, index_dir, metadata_mode, allowed_metadata_modes, has_sources)


def check_all(project_root: Path) -> list[IndexStatus]:
    wiki_dir = project_root / WIKI_DIR_NAME
    index_root = project_root / INDEX_DIR_NAME
    raw_mode = raw_expected_metadata_mode(project_root)
    expected_settings = project_build_settings(project_root)
    return [
        check_one(
            project_root,
            "raw",
            wiki_dir / "raw",
            index_root / RAW_INDEX_NAME,
            raw_mode,
            allowed_metadata_modes=raw_allowed_metadata_modes(project_root),
            dependency_hashes=raw_enrichment_hashes(project_root) if raw_mode == "enriched_raw" else None,
            dependency_manifest_key="semantic_source_hashes" if raw_mode == "enriched_raw" else None,
            dependency_message="raw 使用的 Wiki 语义标签有改动，需要增量更新索引",
            expected_settings=expected_settings,
        ),
        check_one(
            project_root,
            "wiki",
            wiki_dir,
            index_root / WIKI_INDEX_NAME,
            "wiki",
            include_dirs=WIKI_INDEX_SOURCE_DIRS,
            exclude_dirs=("raw", "_archive"),
            expected_settings=expected_settings,
        ),
    ]


def find_script(project_root: Path, *parts: str) -> Path:
    bases = [project_root, *project_root.parents]
    reference_skills_dir = Path(__file__).resolve().parents[2]
    candidates: list[Path] = [reference_skills_dir.joinpath(*parts[1:])]
    for base in bases:
        candidates.append(base.joinpath(*parts))
        candidates.append(base / "skills-hermes" / "research" / parts[-3] / parts[-2] / parts[-1] if len(parts) >= 3 else base.joinpath(*parts))
    candidates.extend([
        Path.home().joinpath(".agents", *parts),
        Path.home().joinpath(".codex", *parts),
        Path.home().joinpath(".hermes", *parts),
    ])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise SystemExit(f"Cannot find required script: {'/'.join(parts)}")


def find_build_script(project_root: Path) -> Path:
    return find_script(project_root, "skills", "SiliconFlow-rag", "scripts", "build_index.py")


def find_lint_script(project_root: Path) -> Path | None:
    try:
        return find_script(project_root, "skills", "karpathy-wiki", "scripts", "lint.py")
    except SystemExit:
        return None


def run_wiki_lint(project_root: Path) -> None:
    lint_script = find_lint_script(project_root)
    if lint_script is None:
        print("[LINT] 未找到 karpathy-wiki lint.py，跳过。")
        return
    wiki_dir = project_root / WIKI_DIR_NAME
    if not wiki_dir.is_dir():
        print(f"[LINT] wiki 目录不存在，跳过: {wiki_dir}")
        return
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


def build_command(status: IndexStatus, build_script: Path, mock: bool, project_root: Path) -> list[str]:
    cmd = [
        sys.executable,
        str(build_script),
        "--md-dir",
        str(status.source_dir),
        "--index-dir",
        str(status.index_dir),
        "--metadata-mode",
        status.metadata_mode,
        "--incremental",
    ]
    config_path = project_root / "rag_config.json"
    if config_path.is_file():
        cmd.extend(["--config", str(config_path)])
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


def apply_updates(project_root: Path, statuses: list[IndexStatus], mock: bool, no_lint: bool) -> int:
    build_script = find_build_script(project_root)
    changed = 0
    for status in statuses:
        if not status.stale:
            continue
        if not status.has_sources and not status.index_dir.exists():
            print(f"[SKIP] {status.label}: 无可索引内容。")
            continue
        if status.label == "wiki" and not no_lint:
            run_wiki_lint(project_root)
        print(f"[UPDATE] {status.message}")
        result = subprocess.run(
            build_command(status, build_script, mock, project_root),
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
        print("RAG 索引状态：当前")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check or update social-science-km RAG indexes.")
    parser.add_argument("--project-root", default=None, help="知识库项目根目录，默认是脚本所在目录")
    parser.add_argument("--check", action="store_true", help="只检查索引是否过期，不执行更新")
    parser.add_argument("--raw-only", action="store_true", help="只检查/更新 raw 索引")
    parser.add_argument("--wiki-only", action="store_true", help="只检查/更新 wiki 索引")
    parser.add_argument("--no-lint", action="store_true", help="更新 wiki 索引前不运行 karpathy-wiki lint")
    parser.add_argument("--mock", action="store_true", help="使用 SiliconFlow-rag 的本地 mock embedding，用于测试")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve() if args.project_root else PROJECT_ROOT
    statuses = check_all(project_root)
    if args.raw_only:
        statuses = [status for status in statuses if status.label == "raw"]
    if args.wiki_only:
        statuses = [status for status in statuses if status.label == "wiki"]

    stale = [status for status in statuses if status.stale]
    if args.check:
        if not stale:
            print("RAG 索引状态：当前")
            return
        for status in stale:
            print("[WARN] " + status.message)
        sys.exit(1)

    sys.exit(apply_updates(project_root, statuses, mock=args.mock, no_lint=args.no_lint))


if __name__ == "__main__":
    main()
