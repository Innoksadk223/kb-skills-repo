#!/usr/bin/env python3
"""Self-test for karpathy-wiki lint behavior.

The fixture is intentionally tiny and uses only the Python standard library.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
LINT = ROOT / "scripts" / "lint.py"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def run_lint(wiki: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(LINT), str(wiki)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return json.loads(result.stdout)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="karpathy-wiki-lint-test-") as td:
        wiki = Path(td) / "wiki"
        for dirname in [
            "claims",
            "concepts",
            "entities",
            "comparisons",
            "queries",
            "synthesis",
            "raw/01-访谈材料",
        ]:
            (wiki / dirname).mkdir(parents=True, exist_ok=True)

        write(
            wiki / "SCHEMA.md",
            """
            # Schema

            ## Tag Taxonomy
            - `社会资本（Social Capital）`
            - `方法论`
            """,
        )
        write(
            wiki / "index.md",
            """
            # Index

            ## 论证节点 / Claims
            - [[核心命题]]

            ## 概念
            - [[社会资本（Social Capital）]]

            ## 综述入口
            - [[研究路线图]]
            """,
        )
        write(wiki / "log.md", "# Log")
        write(
            wiki / "raw/01-访谈材料/访谈A.md",
            """
            ---
            ingested: 2026-06-12
            sha256: intentionally-wrong
            ---

            访谈材料正文。
            """,
        )
        write(
            wiki / "concepts/社会资本（Social Capital）.md",
            """
            ---
            title: 社会资本（Social Capital）
            created: 2026-06-12
            updated: 2026-06-12
            type: concept
            tags: [社会资本（Social Capital）]
            sources: [raw/01-访谈材料/访谈A.md]
            confidence: medium
            ---

            # 社会资本（Social Capital）

            关联 [[核心命题]] 与 [[研究路线图]]。
            """,
        )
        write(
            wiki / "claims/核心命题.md",
            """
            ---
            title: 核心命题
            type: claim
            claim_type: main
            core: true
            status: supported
            confidence: medium
            supports: []
            opposes: []
            limits: []
            depends_on: []
            related_concepts: [社会资本（Social Capital）]
            related_entities: []
            related_comparisons: []
            sources: [社会资本（Social Capital）]
            created: 2026-06-12
            updated: 2026-06-12
            ---

            # 核心命题

            ## 命题
            社会资本影响行动者的资源可得性。

            ## 关系
            - 支撑：无
            - 反对：无
            - 限定：[[争议命题]]
            - 依赖：[[社会资本（Social Capital）]]

            ## 关键证据
            - [[社会资本（Social Capital）]]：访谈材料显示资源网络差异。
              - 证据位置：`raw/01-访谈材料/访谈A.md:1`

            ## 写作用途
            可用于文献综述。
            """,
        )
        write(
            wiki / "claims/普通命题.md",
            """
            ---
            title: 普通命题
            type: claim
            claim_type: support
            core: false
            status: working
            confidence: medium
            supports: [核心命题]
            opposes: []
            limits: []
            depends_on: []
            related_concepts: [社会资本（Social Capital）]
            related_entities: []
            related_comparisons: []
            sources: [社会资本（Social Capital）]
            created: 2026-06-12
            updated: 2026-06-12
            ---

            # 普通命题

            ## 命题
            普通命题不需要出现在 index。

            ## 关系
            - 支撑：[[核心命题]]
            - 反对：无
            - 限定：无
            - 依赖：[[社会资本（Social Capital）]]
            """,
        )
        write(
            wiki / "claims/争议命题.md",
            """
            ---
            title: 争议命题
            type: claim
            claim_type: objection
            core: false
            status: contested
            confidence: medium
            supports: []
            opposes: [核心命题]
            limits: [核心命题]
            depends_on: []
            related_concepts: [社会资本（Social Capital）]
            related_entities: []
            related_comparisons: []
            sources: [社会资本（Social Capital）]
            created: 2026-06-12
            updated: 2026-06-12
            ---

            # 争议命题

            ## 命题
            社会资本也可能再生产不平等。

            ## 关系
            - 支撑：无
            - 反对：[[核心命题]]
            - 限定：[[核心命题]]
            - 依赖：[[社会资本（Social Capital）]]
            """,
        )
        write(
            wiki / "synthesis/研究路线图.md",
            """
            ---
            title: 研究路线图
            created: 2026-06-12
            updated: 2026-06-12
            type: synthesis
            tags: [方法论]
            sources: [核心命题]
            confidence: medium
            ---

            # 研究路线图

            入口页，连接 [[核心命题]] 与 [[社会资本（Social Capital）]]。
            """,
        )

        write(
            wiki / "claims/序列命题.md",
            """
            ---
            title: 序列命题
            type: claim
            claim_type: support
            core: false
            status: working
            confidence: medium
            supports: [核心命题]
            opposes: []
            limits: []
            depends_on: []
            related_concepts: []
            related_entities: []
            related_comparisons: []
            sources: [raw/01-访谈材料/访谈A.md]
            created: 2026-06-12
            updated: 2026-06-12
            relationships:
              contradicts: [核心命题]
            follows:
              - 核心命题
              - 不存在的页面
            ---

            # 序列命题

            ## 命题
            x

            ## 关系
            - 依赖：[[核心命题]]
            """,
        )

        write(
            wiki / "raw/01-访谈材料/长文材料.md",
            "长文正文。\n" + "补充行。\n" * 2100,
        )
        # 长文来源：缺「精读文本 + 原文」成对结构，必须报出
        write(
            wiki / "claims/长文命题缺结构.md",
            """
            ---
            title: 长文命题缺结构
            type: claim
            claim_type: support
            core: false
            status: working
            confidence: medium
            supports: []
            opposes: []
            limits: []
            depends_on: []
            related_concepts: []
            related_entities: []
            related_comparisons: []
            sources: [raw/01-访谈材料/长文材料.md]
            created: 2026-06-12
            updated: 2026-06-12
            ---

            # 长文命题缺结构

            ## 命题
            这是长文的词条，但漏了第二遍结构。

            ## 关系
            - 依赖：[[核心命题]]
            """,
        )
        # 长文来源：结构顺序颠倒，也必须报出
        write(
            wiki / "claims/长文命题顺序错.md",
            """
            ---
            title: 长文命题顺序错
            type: claim
            claim_type: support
            core: false
            status: working
            confidence: medium
            supports: []
            opposes: []
            limits: []
            depends_on: []
            related_concepts: []
            related_entities: []
            related_comparisons: []
            sources: [raw/01-访谈材料/长文材料.md]
            created: 2026-06-12
            updated: 2026-06-12
            ---

            # 长文命题顺序错

            ## 命题
            这是长文的词条，结构顺序颠倒了。

            ## 关系
            - 依赖：[[核心命题]]

            ## 原文
            > 逐字摘录
            `raw/01-访谈材料/长文材料.md:1`

            ## 精读文本
            第一遍精读的记录。
            """,
        )
        # 长文来源：成对且顺序正确，不应报出
        write(
            wiki / "claims/长文命题合规.md",
            """
            ---
            title: 长文命题合规
            type: claim
            claim_type: support
            core: false
            status: working
            confidence: medium
            supports: []
            opposes: []
            limits: []
            depends_on: []
            related_concepts: []
            related_entities: []
            related_comparisons: []
            sources: [raw/01-访谈材料/长文材料.md]
            created: 2026-06-12
            updated: 2026-06-12
            ---

            # 长文命题合规

            ## 命题
            这是长文的词条，第二遍结构完整。

            ## 关系
            - 依赖：[[核心命题]]

            ## 精读文本
            第一遍精读的记录。

            ## 原文
            > 逐字摘录
            `raw/01-访谈材料/长文材料.md:1`
            """,
        )

        # 合并组：单篇都不超 2000 行，合计超过 → 视为长文，需成对结构
        for index in (1, 2):
            write(
                wiki / f"raw/01-访谈材料/组材料{index}.md",
                "组内正文。\n" + "补充行。\n" * 1100,
            )
        write(
            wiki / "claims/合并组命题.md",
            """
            ---
            title: 合并组命题
            type: claim
            claim_type: support
            core: false
            status: working
            confidence: medium
            supports: []
            opposes: []
            limits: []
            depends_on: []
            related_concepts: []
            related_entities: []
            related_comparisons: []
            sources: [raw/01-访谈材料/组材料1.md, raw/01-访谈材料/组材料2.md]
            created: 2026-06-12
            updated: 2026-06-12
            ---

            # 合并组命题

            ## 命题
            合并组来源，合计超过阈值。

            ## 关系
            - 依赖：[[核心命题]]
            """,
        )
        # 路径写法带 wiki/ 前缀：解析成功，成对结构合规 → 不报
        write(
            wiki / "claims/前缀路径命题.md",
            """
            ---
            title: 前缀路径命题
            type: claim
            claim_type: support
            core: false
            status: working
            confidence: medium
            supports: []
            opposes: []
            limits: []
            depends_on: []
            related_concepts: []
            related_entities: []
            related_comparisons: []
            sources: [wiki/raw/01-访谈材料/长文材料.md]
            created: 2026-06-12
            updated: 2026-06-12
            ---

            # 前缀路径命题

            ## 命题
            sources 带 wiki/ 前缀，仍应解析到长文。

            ## 关系
            - 依赖：[[核心命题]]

            ## 精读文本
            第一遍精读的记录。

            ## 原文
            > 逐字摘录
            `raw/01-访谈材料/长文材料.md:1`
            """,
        )
        # raw 路径拼错：解析不到，报未解析提示
        write(
            wiki / "claims/路径拼错命题.md",
            """
            ---
            title: 路径拼错命题
            type: claim
            claim_type: support
            core: false
            status: working
            confidence: medium
            supports: []
            opposes: []
            limits: []
            depends_on: []
            related_concepts: []
            related_entities: []
            related_comparisons: []
            sources: [raw/01-访谈材料/不存在的材料.md]
            created: 2026-06-12
            updated: 2026-06-12
            ---

            # 路径拼错命题

            ## 命题
            sources 路径拼接错误。

            ## 关系
            - 依赖：[[核心命题]]
            """,
        )
        # synthesis 入口页引用长文：非词条页，不要求成对结构
        write(
            wiki / "synthesis/长文路线.md",
            """
            ---
            title: 长文路线
            created: 2026-06-12
            updated: 2026-06-12
            type: synthesis
            tags: [方法论]
            sources: [raw/01-访谈材料/长文材料.md]
            confidence: medium
            ---

            # 长文路线

            入口页，连接 [[核心命题]] 与 [[社会资本（Social Capital）]]。
            """,
        )

        report = run_lint(wiki)
        findings = report.get("findings", {})

        assert report["total_raw_files"] == 4, report
        assert "研究路线图" not in findings.get("index", {}).get("index_entries_without_page", []), report
        assert "普通命题" not in findings.get("index", {}).get("pages_not_in_index", []), report
        assert not findings.get("tag_issues"), report
        assert not any(
            issue.get("issue", "").startswith("tag ")
            for issue in findings.get("frontmatter", [])
        ), report
        assert any(
            item.get("page") == "claims/争议命题.md"
            for item in findings.get("contradictions", [])
        ), report
        assert any(
            item.get("file") == "raw/01-访谈材料/访谈A.md"
            for item in findings.get("source_drift", [])
        ), report
        # follows: dangling target detected + reverse index derived
        assert any(
            "不存在的页面" in item.get("issue", "")
            for item in findings.get("follows", [])
        ), report
        assert "序列命题" in report.get("followed_by", {}).get("核心命题", []), report
        # nested relationships.contradicts reaches the contradictions report
        assert any(
            item.get("page") == "claims/序列命题.md"
            for item in findings.get("contradictions", [])
        ), report
        # 长文第二遍结构：缺结构与顺序颠倒各报一条，合规页不报
        second_pass = findings.get("second_pass_structure", [])
        flagged = {item.get("page") for item in second_pass}
        assert "claims/长文命题缺结构.md" in flagged, report
        assert any(
            item.get("page") == "claims/长文命题缺结构.md"
            and "第二遍通读未落结构" in item.get("issue", "")
            for item in second_pass
        ), report
        assert any(
            item.get("page") == "claims/长文命题顺序错.md"
            and "顺序错误" in item.get("issue", "")
            for item in second_pass
        ), report
        assert "claims/长文命题合规.md" not in flagged, report
        # 短文来源不触发长文结构检查
        assert "claims/核心命题.md" not in flagged, report
        # 合并组（单篇各 1101 行，合计超阈值）：按长文检查
        assert "claims/合并组命题.md" in flagged, report
        assert any(
            item.get("page") == "claims/合并组命题.md"
            and "不可拆分组合计" in item.get("issue", "")
            for item in second_pass
        ), report
        # sources 带 wiki/ 前缀仍能解析；该页结构合规，不应报
        assert "claims/前缀路径命题.md" not in flagged, report
        # synthesis 入口页引用长文：非词条页豁免
        assert "synthesis/长文路线.md" not in flagged, report
        # raw 路径拼错：单独报未解析，便于发现漏判
        unresolved = findings.get("second_pass_unresolved_sources", [])
        assert any(
            item.get("page") == "claims/路径拼错命题.md"
            for item in unresolved
        ), report

    print("karpathy-wiki lint self-test passed")


if __name__ == "__main__":
    main()
