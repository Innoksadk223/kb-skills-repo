#!/usr/bin/env python3
"""End-to-end offline self-test for social-science-km WeKnora scripts.

Covers:
1. New workflow (NO local ``wiki/raw/``): direct PDF + DOCX/MD source folder upload
   → PDF page locator (`#p.12`) preservation → local ``karpathy-wiki`` card sync
   to ``<project>-wiki`` KB → two-hop ``km_query.py`` returning verbatim PDF chunk + page;
2. Optional ``weknora_native`` mode on direct PDF source folder (auto Web Wiki + two-hop);
3. Legacy compatibility workflow (existing ``wiki/raw/*.md`` + ``enriched_raw`` header stripping);
4. ``doctor.py --mock`` onboarding check.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SYNC_KB = SCRIPT_DIR / "sync_kb.py"
QUERY_KB = SCRIPT_DIR / "query_kb.py"
CHECK_REBUILD = SCRIPT_DIR / "check_rebuild_rag.py"
KM_QUERY = SCRIPT_DIR / "km_query.py"
DOCTOR = SCRIPT_DIR / "doctor.py"


def run_cmd(args: list[str], cwd: Path, expect_ok: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        [sys.executable, *args],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if expect_ok and proc.returncode != 0:
        raise SystemExit(
            f"Command failed ({proc.returncode}): {' '.join(args)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return proc


def assert_in(needle: str, haystack: str, label: str) -> None:
    if needle not in haystack:
        raise SystemExit(f"[{label}] Expected '{needle}' in output:\n{haystack}")


def assert_not_in(needle: str, haystack: str, label: str) -> None:
    if needle in haystack:
        raise SystemExit(f"[{label}] Unexpected '{needle}' in output:\n{haystack}")


def test_direct_pdf_local_karpathy(base_dir: Path) -> None:
    """New default workflow: sibling `<资料夹>/` with PDF, NO `wiki/raw/` generated."""
    src_dir = base_dir / "儒学文献"
    proj = base_dir / "儒学文献（知识库）"
    (src_dir / "02-学术研究").mkdir(parents=True)
    for sub in ("claims", "concepts", "debates"):
        (proj / "wiki" / sub).mkdir(parents=True)

    # Create synthetic multi-page PDF binary in read-only source folder
    pdf_bytes = (
        b"%PDF-1.7\n"
        + (
            "%%PAGE 1%%\n孝为仁礼之本论 导论\n\n"
            "%%PAGE 12%%\n孝是仁的情感发生根源，仁的博爱是孝之亲爱的有序推扩；礼的敬意源于孝亲敬祖意识。\n"
        ).encode("utf-8")
        + b"\n%%EOF\n"
    )
    (src_dir / "02-学术研究" / "孝为仁礼之本论_肖群忠.pdf").write_bytes(pdf_bytes)

    # Local karpathy-wiki cards cite the original PDF + page directly (no wiki/raw/*.md!)
    (proj / "wiki" / "concepts" / "孝与仁礼.md").write_text(
        "---\ntitle: 孝与仁礼\ntype: concept\nsources: [02-学术研究/孝为仁礼之本论_肖群忠.pdf]\n---\n\n"
        "# 孝与仁礼\n\n孝为仁与礼的内在心理根基（参见 `02-学术研究/孝为仁礼之本论_肖群忠.pdf#p.12`）。\n",
        encoding="utf-8",
    )
    (proj / "wiki" / "claims" / "孝是仁的情感发生根源.md").write_text(
        "---\ntitle: 孝是仁的情感发生根源\ntype: claim\nrelated_concepts: [孝与仁礼]\n"
        "contradicts: [孝与普遍仁爱冲突论]\nsources: [02-学术研究/孝为仁礼之本论_肖群忠.pdf#p.12]\n---\n\n"
        "## 命题\n孝是仁德博爱的情感发生根源与实践起点。\n\n"
        "## 关键证据\n来源：`02-学术研究/孝为仁礼之本论_肖群忠.pdf#p.12`\n",
        encoding="utf-8",
    )

    # Auto-detect sibling `儒学文献` and sync both <project>-raw and <project>-wiki
    r_sync = run_cmd([str(CHECK_REBUILD), "--project-root", str(proj), "--no-lint", "--mock"], cwd=proj)
    assert_in("[原文件直传]", r_sync.stdout, "direct source flag")

    if (proj / "wiki" / "raw").exists():
        raise SystemExit("New direct-source workflow MUST NOT create local wiki/raw/ directory!")
    if not (proj / "检索索引" / "_source_manifest.md").is_file():
        raise SystemExit("Expected 检索索引/_source_manifest.md to be generated")
    if not (proj / "检索索引" / "wiki" / "manifest.json").is_file():
        raise SystemExit("Expected 检索索引/wiki/manifest.json for <project>-wiki KB")

    # Freshness check must be clean
    r_chk = run_cmd([str(KM_QUERY), "--project-root", str(proj), "--check", "--no-lint", "--mock"], cwd=proj)
    assert_in("RAG 索引状态：当前（wiki_mode=local_karpathy）", r_chk.stdout, "fresh check")

    # Two-hop query: hits <project>-wiki claim card -> boosts cited PDF in <project>-raw -> outputs #p.12
    q_res = run_cmd(
        [str(KM_QUERY), "--project-root", str(proj), "--no-lint", "--rerank", "--mock", "为什么孝是仁与礼的根源？"],
        cwd=proj,
    )
    assert_in("[MODE] wiki-first (local_karpathy)", q_res.stdout, "mode banner")
    assert_in("# Wiki Hits", q_res.stdout, "wiki hits section")
    assert_in("02-学术研究/孝为仁礼之本论_肖群忠.pdf#p.12", q_res.stdout, "PDF page locator in evidence")
    assert_in("有序推扩", q_res.stdout, "verbatim PDF chunk text")


def test_direct_pdf_weknora_native(base_dir: Path) -> None:
    """Optional route: WeKnora built-in automated Wiki on direct PDF source folder."""
    src_dir = base_dir / "乡土资料"
    proj = base_dir / "乡土资料（知识库）"
    src_dir.mkdir(parents=True)
    proj.mkdir(parents=True)

    (proj / "weknora_config.json").write_text(
        json.dumps({"wiki_mode": "weknora_native", "source_dir": str(src_dir)}, ensure_ascii=False),
        encoding="utf-8",
    )
    pdf_bytes = (
        b"%PDF-1.7\n"
        + "%%PAGE 5%%\n# 乡土中国\n\n## 差序格局\n\n费孝通提出中国乡土社会结构如同水面波纹般的差序格局。\n".encode("utf-8")
        + b"\n%%EOF\n"
    )
    (src_dir / "乡土中国_费孝通.pdf").write_bytes(pdf_bytes)

    r_sync = run_cmd([str(CHECK_REBUILD), "--project-root", str(proj), "--mock"], cwd=proj)
    assert_in("已开启 WeKnora 自动生成 Wiki", r_sync.stdout, "native wiki enabled")
    if (proj / "检索索引" / "wiki" / "manifest.json").exists():
        raise SystemExit("weknora_native must not create local <project>-wiki manifest")

    q_nat = run_cmd([str(KM_QUERY), "--project-root", str(proj), "--mock", "什么是差序格局？"], cwd=proj)
    assert_in("[MODE] wiki-first (weknora_native)", q_nat.stdout, "native mode banner")
    assert_in("[weknora_wiki]", q_nat.stdout, "native wiki hit")
    assert_in("乡土中国_费孝通.pdf#p.5", q_nat.stdout, "native PDF page citation")
    assert_in("水面波纹", q_nat.stdout, "native raw quote")


def test_legacy_wiki_raw_compat(base_dir: Path) -> None:
    """Existing projects with `wiki/raw/*.md` continue working untouched."""
    proj = base_dir / "legacy-proj"
    raw = proj / "wiki" / "raw"
    claims = proj / "wiki" / "claims"
    raw.mkdir(parents=True)
    claims.mkdir(parents=True)

    (raw / "_conversion_manifest.md").write_text("operational file", encoding="utf-8")
    (raw / "analects.md").write_text("# 论语\n\n有子曰：孝弟也者，其为仁之本与！", encoding="utf-8")
    (claims / "孝为仁本.md").write_text(
        "---\ntitle: 孝为仁本\ntype: claim\nsources: [wiki/raw/analects.md]\n---\n\n"
        "## 命题\n孝悌为仁之本。\n\n证据位置：`wiki/raw/analects.md:L3`\n",
        encoding="utf-8",
    )

    run_cmd([str(CHECK_REBUILD), "--project-root", str(proj), "--no-lint", "--mock"], cwd=proj)
    raw_manifest = json.loads((proj / "检索索引" / "raw" / "manifest.json").read_text(encoding="utf-8"))
    if raw_manifest.get("metadata_mode") != "enriched_raw":
        raise SystemExit(f"Expected legacy project to use enriched_raw, got {raw_manifest.get('metadata_mode')}")

    q_leg = run_cmd([str(KM_QUERY), "--project-root", str(proj), "--no-lint", "--mock", "孝弟与仁之本的关系"], cwd=proj)
    assert_in("其为仁之本与", q_leg.stdout, "legacy raw text")
    assert_not_in("KM_ENRICHED_HEADER", q_leg.stdout, "enriched header stripped")


def test_doctor_mock(base_dir: Path) -> None:
    r_doc = run_cmd([str(DOCTOR), "--project-root", str(base_dir), "--mock"], cwd=base_dir)
    assert_in("[READY]", r_doc.stdout, "doctor banner")
    assert_in("[OK] parser", r_doc.stdout, "doctor parser check")


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="sskm-selftest-", dir=os.environ.get("PI_SCRATCH_DIR")))
    try:
        test_direct_pdf_local_karpathy(tmp)
        test_direct_pdf_weknora_native(tmp)
        test_legacy_wiki_raw_compat(tmp)
        test_doctor_mock(tmp)
        print("SELF_TEST_OK: social-science-km (direct PDF + local_karpathy + weknora_native + legacy raw + doctor)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
