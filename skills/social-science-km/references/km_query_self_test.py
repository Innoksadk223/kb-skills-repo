#!/usr/bin/env python3
"""Self-test for social-science-km km_query.py and check_rebuild_rag.py (both Wiki modes)."""

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
SCRIPTS_DIR = SCRIPT_DIR.parents[0] / "scripts"
KM_QUERY = SCRIPTS_DIR / "km_query.py"
CHECK_REBUILD = SCRIPTS_DIR / "check_rebuild_rag.py"


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
    wiki_mode: str = "local_karpathy",
) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    (index_dir / "manifest.json").write_text(
        json.dumps(
            {
                "backend": "weknora",
                "format_version": 3,
                "wiki_mode": wiki_mode,
                "kb_id": f"kb_{index_dir.name}",
                "kb_name": f"test-{index_dir.name}",
                "file_hashes": file_hashes,
                "remote_docs": {k: {"knowledge_id": f"doc_{i}", "sha256": v, "upload_sha256": v} for i, (k, v) in enumerate(file_hashes.items())},
                "metadata_mode": metadata_mode,
                "semantic_source_hashes": semantic_source_hashes or {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def run_py(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, encoding="utf-8", errors="replace")


def check_query_cli(km, project_root: Path, args: list[str], expected_code: int, mode: str | None) -> None:
    argv = [str(KM_QUERY), "--project-root", str(project_root), "--no-lint", *args]
    output = io.StringIO()
    with patch.object(sys, "argv", argv), redirect_stdout(output), \
            patch.object(km, "find_query_script", return_value=project_root / "query_kb.py"), \
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
            freshness.assert_called_once()
        if mode is None:
            run.assert_not_called()
        else:
            run.assert_called_once()
            command = run.call_args.args[0]
            if ("--wiki-first" in command) != (mode == "wiki"):
                raise SystemExit(f"CLI {args}: wrong query mode: {command}")
            if mode == "raw" and "--index-dir" not in command:
                raise SystemExit(f"CLI {args}: missing raw index: {command}")
            if Path(run.call_args.kwargs["cwd"]).resolve() != project_root.resolve():
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
        (temp_dir / "weknora_config.json").write_text(
            '{"wiki_mode": "local_karpathy", "query": {"top_k": 4}}',
            encoding="utf-8",
        )

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
        check_query_cli(km, temp_dir, [concept_question, "--skip-check"], 0, "wiki")
        unrelated_page.unlink()

        (temp_dir / "weknora_config.json").write_text(
            '{"wiki_mode": "local_karpathy", "build": {"chunk_size": 512}, "query": {"top_k": 4}}',
            encoding="utf-8",
        )
        status = km.check_staleness(temp_dir)
        if not status.raw_stale or not status.wiki_stale or "chunk_size" not in status.message:
            raise SystemExit(f"Expected config chunk_size change to stale both indexes, got: {status}")
        check_query_cli(km, temp_dir, [source_question], 1, None)
        (temp_dir / "weknora_config.json").write_text(
            '{"wiki_mode": "local_karpathy", "query": {"top_k": 4}}',
            encoding="utf-8",
        )

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

        cmd = km.build_query_command(
            project_root=temp_dir,
            query_script=Path("/tmp/query_kb.py"),
            question="孝与仁的关系是什么？",
            mode="wiki",
            expand_context=True,
            rerank=False,
            multi_query=False,
            candidates=None,
            source_discovery=True,
        )
        joined = " ".join(cmd)
        for marker in [
            "--config",
            "weknora_config.json",
            "--wiki-first",
            "--wiki-index-dir",
            "检索索引/wiki",
            "--raw-index-dir",
            "检索索引/raw",
            "--expand-context",
            "--source-discovery",
        ]:
            if marker not in joined:
                raise SystemExit(f"Wiki command missing {marker}: {joined}")

        # End-to-end check_rebuild_rag + km_query test in local_karpathy mode
        check_project = Path(tempfile.mkdtemp(prefix="km-check-karpathy-", dir=temp_dir))
        try:
            check_raw = check_project / "wiki" / "raw"
            check_raw.mkdir(parents=True)
            (check_raw / "source.md").write_text("# 孝与仁\n\n有子曰：孝弟也者，其为仁之本与！", encoding="utf-8")
            result = run_py([sys.executable, str(CHECK_REBUILD), "--project-root", str(check_project), "--mock", "--no-lint"], SCRIPT_DIR)
            if result.returncode != 0:
                raise SystemExit(f"check_rebuild_rag raw sync failed:\n{result.stdout}\n{result.stderr}")
            raw_manifest = json.loads((check_project / "检索索引" / "raw" / "manifest.json").read_text(encoding="utf-8"))
            if raw_manifest.get("metadata_mode") != "plain" or raw_manifest.get("backend") != "weknora":
                raise SystemExit(f"Expected initial weknora plain manifest, got: {raw_manifest}")

            check_claims = check_project / "wiki" / "claims"
            check_claims.mkdir(parents=True)
            (check_claims / "claim.md").write_text("---\ntitle: 孝为仁本\ntype: claim\nsources: [raw/source.md]\n---\n## 命题\n孝悌是仁之本。", encoding="utf-8")
            result = run_py([sys.executable, str(CHECK_REBUILD), "--project-root", str(check_project), "--mock", "--no-lint"], SCRIPT_DIR)
            if result.returncode != 0:
                raise SystemExit(f"check_rebuild_rag graph-stage sync failed:\n{result.stdout}\n{result.stderr}")
            raw_manifest = json.loads((check_project / "检索索引" / "raw" / "manifest.json").read_text(encoding="utf-8"))
            wiki_manifest = json.loads((check_project / "检索索引" / "wiki" / "manifest.json").read_text(encoding="utf-8"))
            if raw_manifest.get("metadata_mode") != "enriched_raw" or wiki_manifest.get("metadata_mode") != "wiki":
                raise SystemExit("Expected enriched_raw + wiki manifests in local_karpathy mode")

            q_res = run_py([sys.executable, str(KM_QUERY), "--project-root", str(check_project), "--mock", "孝与仁的关系是什么？"], SCRIPT_DIR)
            if q_res.returncode != 0 or "[MODE] wiki-first (local_karpathy)" not in q_res.stdout or "其为仁之本与" not in q_res.stdout:
                raise SystemExit(f"Live mock query failed in local_karpathy mode:\n{q_res.stdout}\n{q_res.stderr}")
        finally:
            shutil.rmtree(check_project, ignore_errors=True)

        # End-to-end check_rebuild_rag + km_query test in weknora_native mode
        native_project = Path(tempfile.mkdtemp(prefix="km-check-native-", dir=temp_dir))
        try:
            native_raw = native_project / "wiki" / "raw"
            native_raw.mkdir(parents=True)
            (native_project / "weknora_config.json").write_text('{"wiki_mode": "weknora_native"}', encoding="utf-8")
            (native_raw / "feixiaotong.md").write_text("# 乡土中国\n\n## 差序格局\n\n乡土社会的人际格局如同水面波纹。", encoding="utf-8")

            res_nat = run_py([sys.executable, str(CHECK_REBUILD), "--project-root", str(native_project), "--mock"], SCRIPT_DIR)
            if res_nat.returncode != 0:
                raise SystemExit(f"weknora_native sync failed:\n{res_nat.stdout}\n{res_nat.stderr}")
            if (native_project / "检索索引" / "wiki" / "manifest.json").exists():
                raise SystemExit("weknora_native mode must NOT create local wiki manifest")

            q_nat = run_py([sys.executable, str(KM_QUERY), "--project-root", str(native_project), "--mock", "什么是差序格局？"], SCRIPT_DIR)
            if q_nat.returncode != 0 or "[MODE] wiki-first (weknora_native)" not in q_nat.stdout or "水面波纹" not in q_nat.stdout:
                raise SystemExit(f"weknora_native query failed:\n{q_nat.stdout}\n{q_nat.stderr}")
        finally:
            shutil.rmtree(native_project, ignore_errors=True)

        print("km_query self-test passed (local_karpathy + weknora_native)")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
