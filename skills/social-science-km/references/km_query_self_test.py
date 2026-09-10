#!/usr/bin/env python3
"""Self-test for the social-science-km km_query.py reference script."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parent
KM_QUERY = SCRIPT_DIR / "km_query.py"
CHECK_REBUILD = SCRIPT_DIR / "check_rebuild_rag.py"


def load_module():
    spec = importlib.util.spec_from_file_location("km_query_ref", KM_QUERY)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load {KM_QUERY}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_manifest(
    index_dir: Path,
    file_hashes: dict[str, str],
    metadata_mode: str,
    semantic_source_hashes: dict[str, str] | None = None,
) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    (index_dir / "manifest.json").write_text(
        json.dumps({
            "file_hashes": file_hashes,
            "format_version": 2,
            "metadata_mode": metadata_mode,
            "semantic_source_hashes": semantic_source_hashes or {},
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (index_dir / "chunks.jsonl").write_text("", encoding="utf-8")
    (index_dir / "embeddings.jsonl").write_text("", encoding="utf-8")


def run_py(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, encoding="utf-8", errors="replace")


def check_query_cli(km, project_root: Path, args: list[str], expected_code: int, mode: str | None) -> None:
    """Exercise routing and real freshness checks without launching query/API work."""
    argv = [str(KM_QUERY), "--project-root", str(project_root), "--no-lint", *args]
    output = io.StringIO()
    with patch.object(sys, "argv", argv), redirect_stdout(output), \
            patch.object(km, "find_query_script", return_value=project_root / "query_index.py"), \
            patch.object(km.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "mock evidence", "")) as run, \
            patch.object(km, "check_staleness", wraps=km.check_staleness) as freshness:
        code = 0
        try:
            km.main()
        except SystemExit as exc:
            code = exc.code
        if code != expected_code:
            raise SystemExit(f"CLI {args}: expected exit {expected_code}, got {code}: {output.getvalue()}")
        if "--skip-check" in args and "--check" not in args:
            freshness.assert_not_called()
        else:
            freshness.assert_called_once_with(project_root)
        if mode is None:
            run.assert_not_called()
        else:
            run.assert_called_once()
            command = run.call_args.args[0]
            if ("--wiki-first" in command) != (mode == "wiki"):
                raise SystemExit(f"CLI {args}: wrong query mode: {command}")
            if mode == "raw" and "--index-dir" not in command:
                raise SystemExit(f"CLI {args}: missing raw index: {command}")
            if run.call_args.kwargs["cwd"] != str(project_root):
                raise SystemExit("Query must run in the project root")
            if "--deep" in args:
                for flag in ("--multi-query", "--rerank", "--expand-context"):
                    if flag not in command:
                        raise SystemExit(f"Deep query missing {flag}")


def main() -> None:
    km = load_module()
    temp_dir = Path(tempfile.mkdtemp(prefix="km-query-test-", dir=os.environ.get("PI_SCRATCH_DIR")))
    try:
        wiki = temp_dir / "wiki"
        raw = wiki / "raw"
        claims = wiki / "claims"
        concepts = wiki / "concepts"
        debates = wiki / "debates"
        raw.mkdir(parents=True)
        claims.mkdir(parents=True)
        concepts.mkdir(parents=True)
        debates.mkdir(parents=True)

        (raw / "care.md").write_text("# Care\n\nraw evidence", encoding="utf-8")
        (temp_dir / "rag_config.json").write_text('{"query": {"top_k": 4}}', encoding="utf-8")

        raw_hashes = km.compute_hashes(raw)
        write_manifest(temp_dir / "检索索引" / "raw", raw_hashes, "plain")

        status = km.check_staleness(temp_dir)
        if status.stale:
            raise SystemExit(f"Expected plain raw to be accepted before graph pages exist, got: {status.message}")

        write_manifest(
            temp_dir / "检索索引" / "raw",
            raw_hashes,
            "enriched_raw",
            semantic_source_hashes=km.raw_enrichment_hashes(temp_dir),
        )
        status = km.check_staleness(temp_dir)
        if status.stale:
            raise SystemExit(f"Expected enriched_raw to be accepted before graph pages exist, got: {status.message}")

        (claims / "claim.md").write_text("---\ntype: claim\n---\n# Claim", encoding="utf-8")
        (concepts / "concept.md").write_text("---\ntype: concept\n---\n# Concept", encoding="utf-8")
        (debates / "debate.md").write_text("---\ntype: debate\n---\n# Debate", encoding="utf-8")

        write_manifest(temp_dir / "检索索引" / "raw", raw_hashes, "plain")
        status = km.check_staleness(temp_dir)
        if not status.stale or "metadata_mode=plain" not in status.message or "enriched_raw" not in status.message:
            raise SystemExit(f"Expected plain raw to become stale after graph pages exist, got: {status}")

        write_manifest(
            temp_dir / "检索索引" / "raw",
            raw_hashes,
            "enriched_raw",
            semantic_source_hashes=km.raw_enrichment_hashes(temp_dir),
        )
        wiki_hashes = km.compute_hashes(wiki, include_dirs=km.WIKI_INDEX_SOURCE_DIRS, exclude_dirs={"raw", "_archive"})
        if "debates/debate.md" not in wiki_hashes:
            raise SystemExit("Expected debates/ pages to be included in wiki index hashes")
        write_manifest(temp_dir / "检索索引" / "wiki", wiki_hashes, "wiki")

        status = km.check_staleness(temp_dir)
        if status.stale:
            raise SystemExit(f"Expected fresh indexes, got stale: {status.message}")

        source_question = "这段话的原文出处在哪里？"
        concept_question = "孝与仁的关系是什么？"
        # "证据" is no longer a raw-lookup marker, so a question that only says
        # "证据" must fall through to wiki-first when a wiki manifest exists.
        evidence_question = "有什么证据支持孝是仁之本？"
        check_query_cli(km, temp_dir, [source_question], 0, "raw")
        check_query_cli(km, temp_dir, [concept_question], 0, "wiki")
        check_query_cli(km, temp_dir, [evidence_question], 0, "wiki")
        check_query_cli(km, temp_dir, [source_question, "--deep"], 0, "wiki")
        check_query_cli(km, temp_dir, ["--check"], 0, None)

        # synthesis is indexed by wiki but does not enrich raw embeddings.
        synthesis = wiki / "synthesis"
        synthesis.mkdir()
        unrelated_page = synthesis / "overview.md"
        unrelated_page.write_text("# Overview", encoding="utf-8")
        status = km.check_staleness(temp_dir)
        if status.raw_stale or not status.wiki_stale:
            raise SystemExit(f"Expected only unrelated wiki staleness, got: {status}")
        check_query_cli(km, temp_dir, [source_question], 0, "raw")
        check_query_cli(km, temp_dir, [source_question, "--raw-only"], 0, "raw")
        check_query_cli(km, temp_dir, [concept_question], 1, None)
        check_query_cli(km, temp_dir, [source_question, "--deep"], 1, None)
        check_query_cli(km, temp_dir, ["--check"], 1, None)
        check_query_cli(km, temp_dir, ["--check", "--raw-only"], 1, None)
        check_query_cli(km, temp_dir, ["--check", "--skip-check"], 1, None)
        check_query_cli(km, temp_dir, [concept_question, "--skip-check"], 0, "wiki")
        unrelated_page.unlink()

        (temp_dir / "rag_config.json").write_text(
            '{"build": {"dimensions": 512}, "query": {"top_k": 4}}',
            encoding="utf-8",
        )
        status = km.check_staleness(temp_dir)
        if not status.raw_stale or not status.wiki_stale or "dimensions" not in status.message:
            raise SystemExit(f"Expected config dimension change to stale both indexes, got: {status}")
        check_query_cli(km, temp_dir, [source_question], 1, None)
        (temp_dir / "rag_config.json").write_text('{"query": {"top_k": 4}}', encoding="utf-8")

        (claims / "claim.md").write_text("---\ntype: claim\n---\n# Changed Claim", encoding="utf-8")
        status = km.check_staleness(temp_dir)
        if not status.raw_stale or "Wiki 语义标签" not in status.message:
            raise SystemExit(f"Expected wiki label changes to stale the enriched raw index, got: {status}")
        check_query_cli(km, temp_dir, [source_question], 1, None)
        check_query_cli(km, temp_dir, [source_question, "--skip-check"], 0, "raw")
        (claims / "claim.md").write_text("---\ntype: claim\n---\n# Claim", encoding="utf-8")

        (raw / "new.md").write_text("# New\n\nnew raw evidence", encoding="utf-8")
        status = km.check_staleness(temp_dir)
        if not status.stale or "raw" not in status.message or "新增/改动" not in status.message:
            raise SystemExit(f"Expected raw new/changed stale message, got: {status}")

        check_query_cli(km, temp_dir, [source_question], 1, None)
        check_query_cli(km, temp_dir, [concept_question], 1, None)
        check_query_cli(km, temp_dir, [source_question, "--deep"], 1, None)
        check_query_cli(km, temp_dir, ["--check"], 1, None)
        check_query_cli(km, temp_dir, [source_question, "--skip-check"], 0, "raw")

        raw_mode = km.choose_mode("这段话的原文出处在哪里？", raw_only=False, deep=False, project_root=temp_dir)
        if raw_mode != "raw":
            raise SystemExit(f"Expected raw mode for source lookup, got: {raw_mode}")

        wiki_mode = km.choose_mode("孝与仁的关系是什么？", raw_only=False, deep=False, project_root=temp_dir)
        if wiki_mode != "wiki":
            raise SystemExit(f"Expected wiki mode for conceptual query, got: {wiki_mode}")

        # CHANGE 2 routing assertions: "证据" no longer forces raw-only, while a
        # genuine source-lookup question still routes raw.
        evidence_mode = km.choose_mode(evidence_question, raw_only=False, deep=False, project_root=temp_dir)
        if evidence_mode != "wiki":
            raise SystemExit(f"Expected wiki mode for evidence question, got: {evidence_mode}")

        source_lookup_mode = km.choose_mode(source_question, raw_only=False, deep=False, project_root=temp_dir)
        if source_lookup_mode != "raw":
            raise SystemExit(f"Expected raw mode for genuine source lookup, got: {source_lookup_mode}")

        cmd = km.build_query_command(
            project_root=temp_dir,
            query_script=Path("/tmp/query_index.py"),
            question="孝与仁的关系是什么？",
            mode="wiki",
            expand_context=True,
            rerank=False,
            multi_query=False,
            candidates=None,
            source_discovery=True,
        )
        joined = " ".join(cmd)
        for marker in ["--config", "rag_config.json", "--wiki-first", "--wiki-index-dir", "检索索引/wiki", "--raw-index-dir", "检索索引/raw", "--expand-context", "--source-discovery"]:
            if marker not in joined:
                raise SystemExit(f"Wiki command missing {marker}: {joined}")

        result = run_py([sys.executable, str(KM_QUERY), "--help"], SCRIPT_DIR)
        if result.returncode != 0 or "--deep" not in result.stdout or "--raw-only" not in result.stdout or "--source-discovery" not in result.stdout:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            raise SystemExit("CLI help test failed")

        check_project = Path(tempfile.mkdtemp(prefix="km-check-test-", dir=temp_dir))
        try:
            check_raw = check_project / "wiki" / "raw"
            check_raw.mkdir(parents=True)
            (check_raw / "source.md").write_text("# Source\n\nraw text", encoding="utf-8")
            result = run_py([sys.executable, str(CHECK_REBUILD), "--project-root", str(check_project), "--mock", "--no-lint"], SCRIPT_DIR)
            if result.returncode != 0:
                print(result.stdout)
                print(result.stderr, file=sys.stderr)
                raise SystemExit("check_rebuild_rag raw build failed")
            raw_manifest = json.loads((check_project / "检索索引" / "raw" / "manifest.json").read_text(encoding="utf-8"))
            if raw_manifest.get("metadata_mode") != "plain":
                raise SystemExit(f"Expected initial raw manifest metadata_mode plain, got: {raw_manifest.get('metadata_mode')}")

            check_claims = check_project / "wiki" / "claims"
            check_claims.mkdir(parents=True)
            (check_claims / "claim.md").write_text("---\ntype: claim\n---\n# Claim", encoding="utf-8")
            result = run_py([sys.executable, str(CHECK_REBUILD), "--project-root", str(check_project), "--mock", "--no-lint"], SCRIPT_DIR)
            if result.returncode != 0:
                print(result.stdout)
                print(result.stderr, file=sys.stderr)
                raise SystemExit("check_rebuild_rag graph-stage update failed")
            raw_manifest = json.loads((check_project / "检索索引" / "raw" / "manifest.json").read_text(encoding="utf-8"))
            wiki_manifest = json.loads((check_project / "检索索引" / "wiki" / "manifest.json").read_text(encoding="utf-8"))
            if raw_manifest.get("metadata_mode") != "enriched_raw":
                raise SystemExit(f"Expected graph-stage raw metadata_mode enriched_raw, got: {raw_manifest.get('metadata_mode')}")
            if not isinstance(raw_manifest.get("semantic_source_hashes"), dict):
                raise SystemExit("Expected graph-stage raw manifest to track semantic_source_hashes")
            if wiki_manifest.get("metadata_mode") != "wiki":
                raise SystemExit(f"Expected wiki metadata_mode wiki, got: {wiki_manifest.get('metadata_mode')}")

            (check_claims / "claim.md").write_text("---\ntype: claim\n---\n# Changed Claim", encoding="utf-8")
            result = run_py([
                sys.executable,
                str(CHECK_REBUILD),
                "--project-root",
                str(check_project),
                "--check",
            ], SCRIPT_DIR)
            if result.returncode == 0 or "raw 使用的 Wiki 语义标签有改动" not in result.stdout:
                print(result.stdout)
                print(result.stderr, file=sys.stderr)
                raise SystemExit("Expected check_rebuild_rag to detect stale enriched-raw semantic labels")
        finally:
            shutil.rmtree(check_project, ignore_errors=True)

        print("km_query self-test passed")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
