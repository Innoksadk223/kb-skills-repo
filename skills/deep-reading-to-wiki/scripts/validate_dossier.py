#!/usr/bin/env python3
"""Validate a deep-reading dossier before handing it to karpathy-wiki.

Stdlib only. Checks the hard structural contract from
references/dossier-template.md so a dossier cannot be handed off shallow:
frontmatter fields, the 5 fixed blocks, each high-value (HV) candidate's raw
anchor + context capsule, and the anti-slack self-check.

Usage:
    python validate_dossier.py <dossier.md>      # exit 0 = pass, 1 = fail
    python validate_dossier.py --self-test       # run bundled fixtures
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED_FRONTMATTER = [
    "title", "type", "source_raw", "trigger",
    "status", "target", "created", "updated", "compiled_to",
]
ALLOWED_STATUS = {"draft", "compiled", "archived"}

# (canonical name, keyword that must appear in the "## N. ..." heading)
REQUIRED_BLOCKS = [
    ("阅读地图", "阅读地图"),
    ("候选节点池", "候选节点池"),
    ("高价值点深挖", "高价值"),
    ("wiki 交接清单", "交接"),
    ("反偷懒自检", "自检"),
]


def _split_frontmatter(text: str) -> tuple[str | None, str]:
    """Return (frontmatter_block, body). frontmatter is None if absent."""
    if not text.lstrip().startswith("---"):
        return None, text
    # find the opening --- then the next --- on its own line
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.strip() == "---")
    for end in range(start + 1, len(lines)):
        if lines[end].strip() == "---":
            fm = "\n".join(lines[start + 1:end])
            body = "\n".join(lines[end + 1:])
            return fm, body
    return None, text


def _sections(body: str) -> dict[str, str]:
    """Split body on `## ` headings → {heading_text: section_body}."""
    parts: dict[str, str] = {}
    current = None
    buf: list[str] = []
    for line in body.splitlines():
        if re.match(r"^##\s+", line):
            if current is not None:
                parts[current] = "\n".join(buf)
            current = line.lstrip("# ").strip()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        parts[current] = "\n".join(buf)
    return parts


def validate_dossier(text: str) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Empty errors = pass."""
    errors: list[str] = []
    warnings: list[str] = []

    fm, body = _split_frontmatter(text)
    if fm is None:
        errors.append("缺少 frontmatter（开头的 --- 块）")
    else:
        for key in REQUIRED_FRONTMATTER:
            if not re.search(rf"^{re.escape(key)}\s*:", fm, re.MULTILINE):
                errors.append(f"frontmatter 缺字段: {key}")
        m = re.search(r"^status\s*:\s*(\S+)", fm, re.MULTILINE)
        if m and m.group(1) not in ALLOWED_STATUS:
            errors.append(
                f"status 非法: {m.group(1)}（应为 {sorted(ALLOWED_STATUS)}）"
            )

    sections = _sections(body)
    heading_blob = "\n".join(sections.keys())
    for canonical, keyword in REQUIRED_BLOCKS:
        if keyword not in heading_blob:
            errors.append(f"缺少必备区块: {canonical}")

    # High-value deep dives: find the "高价值" section, require >=1 HV block,
    # each with a context capsule + raw anchor.
    hv_section = next(
        (v for k, v in sections.items() if "高价值" in k), None
    )
    if hv_section is not None:
        hv_blocks = re.split(r"^###\s+HV-", hv_section, flags=re.MULTILINE)[1:]
        if not hv_blocks:
            errors.append("高价值点深挖区块下没有 ### HV- 候选")
        for i, blk in enumerate(hv_blocks, 1):
            if "上下文胶囊" not in blk:
                errors.append(f"HV-{i} 缺少上下文胶囊")
            if "wiki/raw/" not in blk:
                errors.append(f"HV-{i} 缺少 raw 锚点（wiki/raw/...）")
        if 0 < len(hv_blocks) < 3:
            warnings.append(
                f"高价值候选只有 {len(hv_blocks)} 个（Gate 2 建议 >=3，"
                "除非来源短或弱相关——请在档案中说明）"
            )

    # Self-check must contain at least one checkbox.
    self_check = next((v for k, v in sections.items() if "自检" in k), None)
    if self_check is not None and not re.search(r"-\s*\[[ xX]\]", self_check):
        errors.append("反偷懒自检区块没有勾选项（- [ ]）")

    # Soft richness signals from Gate 2.
    warnings += _richness_warnings(sections)
    return errors, warnings


def _count_table_rows(section: str) -> int:
    """Count markdown table data rows (skip header + separator)."""
    rows = [l for l in section.splitlines() if l.strip().startswith("|")]
    data = [l for l in rows if not re.match(r"^\s*\|[\s:|-]+\|\s*$", l)]
    # first remaining row is the header
    return max(0, len(data) - 1)


def _richness_warnings(sections: dict[str, str]) -> list[str]:
    pool = next((v for k, v in sections.items() if "候选节点池" in k), None)
    if pool is None:
        return []
    out: list[str] = []
    concepts = re.search(r"候选 Concepts(.*?)(?:###|$)", pool, re.S)
    claims = re.search(r"候选 Claims(.*?)(?:###|$)", pool, re.S)
    if concepts and _count_table_rows(concepts.group(1)) < 5:
        out.append("候选 Concepts < 5（Gate 2 建议，除非来源窄）")
    if claims and _count_table_rows(claims.group(1)) < 8:
        out.append("候选 Claims < 8（Gate 2 建议，除非来源短或多为描述性）")
    return out


def _report(path: str, errors: list[str], warnings: list[str]) -> int:
    label = path
    if errors:
        print(f"FAIL {label}")
        for e in errors:
            print(f"  ✗ {e}")
    else:
        print(f"PASS {label}")
    for w in warnings:
        print(f"  ! {w}")
    return 1 if errors else 0


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    arg = argv[0]
    if arg == "--self-test":
        import validate_dossier_self_test as t
        return t.run()
    text = Path(arg).read_text(encoding="utf-8")
    errors, warnings = validate_dossier(text)
    return _report(arg, errors, warnings)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
