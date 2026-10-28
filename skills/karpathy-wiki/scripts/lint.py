#!/usr/bin/env python3
"""
karpathy-wiki lint script — scans a wiki directory and reports issues as JSON.
Usage: python3 lint.py <wiki_path>
       or set WIKI_PATH env var.
Output: JSON with findings grouped by category.
"""

import os, sys, re, json, hashlib, unicodedata
from collections import defaultdict
from datetime import datetime, timedelta

WIKI = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("WIKI_PATH", os.path.expanduser("~/wiki"))

RAW = os.path.join(WIKI, "raw")
ENTITIES = os.path.join(WIKI, "entities")
CONCEPTS = os.path.join(WIKI, "concepts")
COMPARISONS = os.path.join(WIKI, "comparisons")
DEBATES = os.path.join(WIKI, "debates")
OBSERVATIONS = os.path.join(WIKI, "observations")
STRUCTURES = os.path.join(WIKI, "structures")
PREDICTS = os.path.join(WIKI, "predicts")
CLAIMS = os.path.join(WIKI, "claims")
QUERIES = os.path.join(WIKI, "queries")
SYNTHESIS = os.path.join(WIKI, "synthesis")
ARCHIVE = os.path.join(WIKI, "_archive")
INDEX = os.path.join(WIKI, "index.md")
SCHEMA = os.path.join(WIKI, "SCHEMA.md")
LOG = os.path.join(WIKI, "log.md")

WIKI_DIRS = [ENTITIES, CONCEPTS, COMPARISONS, DEBATES, CLAIMS, OBSERVATIONS, STRUCTURES, PREDICTS, QUERIES, SYNTHESIS]

def _parse_scalar(val):
    val = val.strip().strip('"').strip("'")
    if val.startswith("[") and val.endswith("]"):
        return [v.strip().strip("'").strip('"') for v in val[1:-1].split(",") if v.strip()]
    return val

def read_frontmatter(filepath):
    """Extract YAML frontmatter as dict. Returns (dict, body_start_line).

    Supports one level of nesting (e.g. the `relationships:` block) and
    block lists (`- item` lines) under top-level or nested keys.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None, 0
    if not content.startswith("---"):
        return {}, 0
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, 0
    fm_text = parts[1]
    body = parts[2]
    body_start = content[:content.index(body)].count("\n") + 1
    fm = {}
    top_key = None   # last top-level key (for nesting / block lists)
    sub_key = None   # last second-level key inside a nested block
    fm_lines = [l for l in fm_text.split("\n") if l.strip()]
    # Tolerate uniformly indented frontmatter: nesting is judged by
    # indentation relative to the block's minimum indent.
    base_indent = min(len(l) - len(l.lstrip(" ")) for l in fm_lines) if fm_lines else 0
    for rawline in fm_lines:
        if rawline.strip().startswith("#"):
            continue
        indent = len(rawline) - len(rawline.lstrip(" ")) - base_indent
        line = rawline.strip()
        if line.startswith("- "):
            item = _parse_scalar(line[2:])
            if sub_key is not None and isinstance(fm.get(top_key), dict):
                bucket = fm[top_key].setdefault(sub_key, [])
                if isinstance(bucket, list):
                    bucket.append(item)
            elif top_key is not None:
                if not isinstance(fm.get(top_key), list):
                    fm[top_key] = []
                fm[top_key].append(item)
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        if indent == 0:
            fm[key] = _parse_scalar(val) if val.strip() else ""
            top_key, sub_key = key, None
        else:
            if not isinstance(fm.get(top_key), dict):
                if fm.get(top_key) in ("", [], None):
                    fm[top_key] = {}
                else:
                    continue  # deeper nesting unsupported
            fm[top_key][key] = _parse_scalar(val) if val.strip() else []
            sub_key = key
    return fm, body_start

def rel_get(fm, key):
    """Read a relation field from top level or the nested `relationships:` block."""
    val = fm.get(key)
    rel = fm.get("relationships")
    if val in (None, "", []) and isinstance(rel, dict):
        val = rel.get(key)
    return val

def scan_wiki_pages():
    """Return list of (relpath, abspath, filename_no_ext, frontmatter)."""
    pages = []
    for d in WIKI_DIRS:
        if not os.path.isdir(d):
            continue
        for fname in sorted(os.listdir(d)):
            if fname.endswith(".md"):
                abspath = os.path.join(d, fname)
                relpath = os.path.relpath(abspath, WIKI)
                name = fname[:-3]  # strip .md
                fm, _ = read_frontmatter(abspath)
                pages.append((relpath, abspath, name, fm))
    return pages

def extract_wikilinks(filepath):
    """Extract [[target]] and [[target|alias]] from file. Returns list of targets."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return []
    return re.findall(r"\[\[([^\]|#]+)(?:[|#][^\]]+)?\]\]", content)

def scan_raw_files():
    """Return list of raw file paths with their frontmatter."""
    files = []
    if not os.path.isdir(RAW):
        return files
    for root, dirs, fnames in os.walk(RAW):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "assets"]
        for fname in fnames:
            if fname.endswith(".md"):
                abspath = os.path.join(root, fname)
                fm, body_start = read_frontmatter(abspath)
                files.append((os.path.relpath(abspath, WIKI), abspath, fm, body_start))
    return files

def read_index_entries():
    """Parse index.md and return set of page names listed."""
    if not os.path.exists(INDEX):
        return set()
    try:
        with open(INDEX, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return set()
    return set(re.findall(r"\[\[([^\]]+)\]\]", content))

# ── Checks ──

def check_orphans(pages):
    """① Find pages with zero inbound wikilinks."""
    all_links = defaultdict(set)
    for relpath, abspath, name, fm in pages:
        for target in extract_wikilinks(abspath):
            all_links[target].add(name)
    orphans = []
    for relpath, abspath, name, fm in pages:
        if name not in all_links:
            orphans.append(relpath)
    return orphans

def check_broken_links(pages):
    """② Find wikilinks pointing to non-existent pages."""
    page_set = {p[2] for p in pages}
    broken = defaultdict(set)
    for relpath, abspath, name, fm in pages:
        for target in extract_wikilinks(abspath):
            if target not in page_set:
                broken[target].add(name)
    return {k: list(v) for k, v in broken.items()}

def check_index_completeness(pages):
    """③ Pages not in index.md, and index entries with no page.

    Ordinary claims are intentionally discoverable through the graph and claims/
    folder; only core claims must appear in index.md.
    """
    indexed = read_index_entries()
    page_names = {p[2] for p in pages}
    required_names = set()
    link_discoverable = ("claims/", "observations/", "structures/", "predicts/")
    link_discoverable_types = {"claim", "observation", "structure", "prediction"}
    for relpath, abspath, name, fm in pages:
        exempt = relpath.startswith(link_discoverable) or (
            fm and fm.get("type") in link_discoverable_types
        )
        if exempt:
            if str((fm or {}).get("core", "")).lower() == "true":
                required_names.add(name)
            continue
        required_names.add(name)
    not_in_index = sorted(required_names - indexed)
    index_orphans = sorted(indexed - page_names)
    return not_in_index, index_orphans

def check_frontmatter(pages, taxonomy_tags):
    """④ Validate required fields and taxonomy tags.

    Claim-specific fields are validated by check_claim_structure(). Claim pages
    do not require tags because the claim template does not use them.
    """
    issues = []
    base_required = ["title", "created", "updated", "type", "sources"]
    for relpath, abspath, name, fm in pages:
        if fm is None:
            issues.append({"page": relpath, "issue": "unreadable file"})
            continue
        is_claim = relpath.startswith("claims/") or (fm and fm.get("type") == "claim")
        required = list(base_required)
        if not is_claim:
            required.append("tags")
        missing = [f for f in required if f not in fm]
        if missing:
            issues.append({"page": relpath, "issue": f"missing fields: {missing}"})
        # Tag-taxonomy violations are reported by check_tags() only.
    return issues

def check_stale_content(pages, raw_files):
    """⑤ Pages whose `updated` date is older than 90 days."""
    stale = []
    cutoff = datetime.now() - timedelta(days=90)
    for relpath, abspath, name, fm in pages:
        updated = fm.get("updated", "") if fm else ""
        try:
            dt = datetime.strptime(str(updated), "%Y-%m-%d")
        except Exception:
            continue
        if dt < cutoff:
            stale.append(relpath)
    return stale

def check_contradictions(pages):
    """⑥ Pages with contested markers or contested claim status."""
    issues = []
    for relpath, abspath, name, fm in pages:
        if not fm:
            continue
        if fm.get("contested") in [True, "true", "True"] or fm.get("status") == "contested":
            issues.append({"page": relpath, "issue": "marked contested"})
        contradictions = fm.get("contradictions", []) or rel_get(fm, "contradicts") or []
        if isinstance(contradictions, str):
            contradictions = [c.strip() for c in contradictions.strip("[]").split(",")]
        if contradictions and contradictions != [""]:
            issues.append({"page": relpath, "issue": f"contradicts: {contradictions}"})
    return issues

def check_quality_signals(pages):
    """⑦ Pages with confidence: low or single-source without confidence field."""
    issues = []
    for relpath, abspath, name, fm in pages:
        if not fm:
            continue
        conf = fm.get("confidence", "")
        if conf == "low":
            issues.append({"page": relpath, "issue": "confidence: low"})
        sources = fm.get("sources", [])
        if isinstance(sources, str):
            sources = [s.strip() for s in sources.strip("[]").split(",")]
        if len(sources) <= 1 and "confidence" not in fm:
            issues.append({"page": relpath, "issue": "single-source, no confidence field"})
    return issues

def check_source_drift(raw_files):
    """⑧ Recompute sha256 of raw files, flag mismatches."""
    drifts = []
    for relpath, abspath, fm, body_start in raw_files:
        if not fm or "sha256" not in fm:
            continue
        stored = fm["sha256"]
        try:
            with open(abspath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue
        if content.startswith("---"):
            parts = content.split("---", 2)
            body = parts[2].lstrip("\n") if len(parts) >= 3 else content
        else:
            body = content
        current = hashlib.sha256(body.encode()).hexdigest()
        if stored != current:
            drifts.append({"file": relpath, "stored": stored[:12], "current": current[:12]})
    return drifts

def check_page_size(pages):
    """⑨ Pages over 200 lines."""
    oversized = []
    for relpath, abspath, name, fm in pages:
        try:
            with open(abspath, "r", encoding="utf-8") as f:
                lines = len(f.readlines())
        except Exception:
            continue
        if lines > 200:
            oversized.append({"page": relpath, "lines": lines})
    return oversized

def check_tags(pages, taxonomy_tags):
    """⑩ Tags not in taxonomy."""
    issues = []
    for relpath, abspath, name, fm in pages:
        if not fm:
            continue
        tags = fm.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.strip("[]").split(",")]
        for t in tags:
            if t.strip() and taxonomy_tags and t.strip() not in taxonomy_tags:
                issues.append({"page": relpath, "tag": t.strip()})
    return issues

def check_log_rotation():
    """⑪ Check if log.md exceeds 500 entries."""
    if not os.path.exists(LOG):
        return False
    try:
        with open(LOG, "r", encoding="utf-8") as f:
            entries = [l for l in f if l.startswith("## [")]
    except Exception:
        return False
    return len(entries) > 500

def check_stub_upgrades(pages):
    """Stub upgrade candidates: stubs (confidence:low + 📝) linked by 2+ full pages."""
    # Find all wikilinks across all pages
    all_links = defaultdict(set)
    for relpath, abspath, name, fm in pages:
        is_full = fm and fm.get("confidence") not in ["low", ""] if fm else True
        for target in extract_wikilinks(abspath):
            all_links[target].add((name, is_full))
    upgrades = []
    for relpath, abspath, name, fm in pages:
        if not fm or fm.get("confidence") != "low":
            continue
        # Check if it's a stub
        try:
            with open(abspath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue
        if "📝" not in content:
            continue
        full_referrers = [n for n, is_full in all_links.get(name, set()) if is_full]
        if len(full_referrers) >= 2:
            upgrades.append({"page": relpath, "full_referrers": full_referrers})
    return upgrades

def check_stub_cleanup(pages):
    """Stub cleanup: stubs whose ALL referrers are archived."""
    archived_pages = set()
    if os.path.isdir(ARCHIVE):
        for root, _, fnames in os.walk(ARCHIVE):
            for fname in fnames:
                if fname.endswith(".md"):
                    archived_pages.add(fname[:-3])
    all_links = defaultdict(set)
    for relpath, abspath, name, fm in pages:
        for target in extract_wikilinks(abspath):
            all_links[target].add(name)
    orphan_stubs = []
    for relpath, abspath, name, fm in pages:
        if not fm or fm.get("confidence") != "low":
            continue
        try:
            with open(abspath, "r", encoding="utf-8") as f:
                if "📝" not in f.read():
                    continue
        except Exception:
            continue
        referrers = all_links.get(name, set())
        if referrers and referrers.issubset(archived_pages):
            orphan_stubs.append({"page": relpath, "referrers": list(referrers)})
    return orphan_stubs

def check_follows(pages):
    """`follows:` targets must exist; derive the reverse (followed_by) index.

    This is the lint-side derivation promised by SKILL.md — pages declare only
    the forward `follows:` edge; who-follows-me comes from this index.
    """
    page_set = {p[2] for p in pages}
    dangling = []
    followed_by = defaultdict(list)
    for relpath, abspath, name, fm in pages:
        if not fm:
            continue
        follows = rel_get(fm, "follows")
        if isinstance(follows, str):
            follows = [s.strip() for s in follows.strip("[]").split(",") if s.strip()]
        if not follows:
            continue
        for target in follows:
            if target not in page_set:
                dangling.append({
                    "page": relpath,
                    "issue": f"follows target '{target}' not found in wiki"
                })
            else:
                followed_by[target].append(name)
    return dangling, {k: sorted(v) for k, v in followed_by.items()}

def check_last_verified(pages):
    """Pages whose `last-verified` date is older than 12 months."""
    cutoff = datetime.now() - timedelta(days=365)
    out = []
    for relpath, abspath, name, fm in pages:
        lv = (fm or {}).get("last-verified", "")
        try:
            dt = datetime.strptime(str(lv), "%Y-%m-%d")
        except Exception:
            continue
        if dt < cutoff:
            out.append(relpath)
    return out

def check_supersedes_consistency(pages):
    """Check supersedes ↔ superseded-by bidirectional consistency."""
    name_to_fm = {p[2]: p[3] for p in pages if p[3]}
    issues = []
    for relpath, abspath, name, fm in pages:
        if not fm:
            continue
        supersedes = rel_get(fm, "supersedes") or []
        if isinstance(supersedes, str):
            supersedes = [s.strip() for s in supersedes.strip("[]").split(",") if s.strip()]
        if not supersedes:
            continue
        for target in supersedes:
            target_fm = name_to_fm.get(target)
            if not target_fm:
                issues.append({
                    "page": relpath,
                    "issue": f"supersedes target '{target}' not found in wiki"
                })
                continue
            superseded_by = rel_get(target_fm, "superseded-by") or []
            if isinstance(superseded_by, str):
                superseded_by = [s.strip() for s in superseded_by.strip("[]").split(",") if s.strip()]
            if name not in superseded_by:
                issues.append({
                    "page": relpath,
                    "issue": f"supersedes '{target}' but '{target}' missing superseded-by: [{name}]"
                })
    return issues

def load_taxonomy():
    """Load tags from SCHEMA.md taxonomy section."""
    if not os.path.exists(SCHEMA):
        return set()
    try:
        with open(SCHEMA, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return set()
    # Find taxonomy section — English template or Chinese project schema.
    tags = set()
    in_taxonomy = False
    for line in content.split("\n"):
        if line.startswith("## ") and ("Tag Taxonomy" in line or "标签体系" in line):
            in_taxonomy = True
            continue
        if in_taxonomy and line.startswith("## ") and "Tag Taxonomy" not in line and "标签体系" not in line:
            break
        if in_taxonomy:
            # Match `tag` patterns
            found = re.findall(r"`([^`]+)`", line)
            for t in found:
                full_tag = t.strip()
                if not full_tag or full_tag.startswith("e.g.") or full_tag.startswith("[Define"):
                    continue
                tags.add(full_tag)
                # Also accept the Chinese base form for bilingual taxonomy entries.
                base_tag = full_tag.split("（")[0].strip()
                if base_tag:
                    tags.add(base_tag)
    return tags

def check_claim_structure(pages):
    """Claim pages must expose argument structure in frontmatter and body wikilinks."""
    issues = []
    required = [
        "claim_type", "core", "status", "confidence", "supports", "opposes",
        "limits", "depends_on", "related_concepts", "related_entities",
        "related_comparisons", "sources"
    ]
    valid_types = {"main", "support", "objection", "limitation", "bridge"}
    valid_status = {"stub", "working", "supported", "contested"}
    for relpath, abspath, name, fm in pages:
        is_claim = relpath.startswith("claims/") or (fm and fm.get("type") == "claim")
        if not is_claim:
            continue
        if not fm:
            issues.append({"page": relpath, "issue": "claim missing frontmatter"})
            continue
        missing = [f for f in required if f not in fm]
        if missing:
            issues.append({"page": relpath, "issue": f"claim missing fields: {missing}"})
        if fm.get("claim_type") and fm.get("claim_type") not in valid_types:
            issues.append({"page": relpath, "issue": f"invalid claim_type: {fm.get('claim_type')}"})
        if fm.get("status") and fm.get("status") not in valid_status:
            issues.append({"page": relpath, "issue": f"invalid status: {fm.get('status')}"})
        try:
            with open(abspath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            issues.append({"page": relpath, "issue": "unreadable claim body"})
            continue
        if "## 命题" not in content:
            issues.append({"page": relpath, "issue": "missing ## 命题 section"})
        if "## 关系" not in content:
            issues.append({"page": relpath, "issue": "missing ## 关系 section"})
        if "[[raw/" in content or "[[../raw/" in content:
            issues.append({"page": relpath, "issue": "raw file wikilinked; use plain-text path instead"})
        core = str(fm.get("core", "")).lower() == "true"
        sources = fm.get("sources", [])
        if isinstance(sources, str):
            sources = [s.strip() for s in sources.strip("[]").split(",") if s.strip()]
        if core:
            for section in ["## 关键证据", "## 写作用途"]:
                if section not in content:
                    issues.append({"page": relpath, "issue": f"core claim missing {section}"})
            if not sources:
                issues.append({"page": relpath, "issue": "core claim has no sources"})
    return issues

LONG_SOURCE_LINES = 2000  # 与 SKILL.md「长文第二遍通读」、compile-dossier.md ①.5 同步
# 非词条页：入口页 / 过程归档，不要求「精读文本 + 原文」成对结构。
NON_NODE_DIRS = ("synthesis/", "queries/", "debates/")
RAW_ANCHOR = re.compile(r"raw/|:\s*\d+")

def _norm_source(value):
    """Normalize a `sources:` entry for path matching (NFC + strip wrappers)."""
    return unicodedata.normalize("NFC", str(value).strip().strip("[]'\"").strip())

def build_raw_index():
    """Return ({relpath: own line count}, {basename: [relpath, ...]}).

    Counting whole-file lines matches the `wc -lc` measurement the routing gate
    records in the manifest, so the two stay on the same ruler.
    """
    counts = {}
    basenames = defaultdict(list)
    if not os.path.isdir(RAW):
        return counts, basenames
    for root, dirs, fnames in os.walk(RAW):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "assets"]
        for fname in fnames:
            if not fname.endswith(".md"):
                continue
            abspath = os.path.join(root, fname)
            relpath = os.path.relpath(abspath, WIKI)
            try:
                with open(abspath, "r", encoding="utf-8") as f:
                    line_count = len(f.readlines())
            except Exception:
                continue
            counts[relpath] = line_count
            basenames[_norm_source(os.path.basename(relpath))].append(relpath)
    return counts, basenames

def resolve_raw_source(entry, counts, basenames):
    """Map a `sources:` entry onto a raw file, tolerating common path spellings."""
    if not entry:
        return None
    candidate = _norm_source(entry)
    for variant in (
        candidate,
        candidate.lstrip("./"),
        re.sub(r"^wiki/", "", candidate),
        re.sub(r"^.*[/\\]", "", candidate),
    ):
        if variant in counts:
            return variant
    # Unique basename match covers sources written with a different prefix.
    hits = basenames.get(re.sub(r"^.*[/\\]", "", candidate), [])
    return hits[0] if len(hits) == 1 else None

def _parse_page_sources(fm):
    sources = fm.get("sources", [])
    if isinstance(sources, str):
        sources = sources.strip("[]").split(",")
    return [s for s in sources if str(s).strip()]

def _section_positions(content):
    """First offset of each `## 精读文本` / `## 原文` heading."""
    positions = {}
    for match in re.finditer(r"^[ \t]*##[ \t]*(精读文本|原文)[ \t]*$", content, re.MULTILINE):
        positions.setdefault(match.group(1), match.start())
    return positions

def check_second_pass_structure(pages):
    """长文词条必须成对出现 `## 精读文本` 与 `## 原文`，顺序固定且原文可回查。

    A page is long-sourced when its resolvable raw sources are over
    LONG_SOURCE_LINES individually, or add up to more than that as an
    inseparable group. Entries that look like raw paths but resolve to no file
    are reported separately — otherwise a spelling mismatch would silently
    pass as compliance.
    """
    counts, basenames = build_raw_index()
    issues = []
    unresolved = []
    for relpath, abspath, name, fm in pages:
        if not fm or relpath.startswith(NON_NODE_DIRS):
            continue
        sources = _parse_page_sources(fm)
        if not sources:
            continue
        resolved = []
        unknown = []
        for source in sources:
            hit = resolve_raw_source(source, counts, basenames)
            if hit is not None:
                resolved.append((hit, counts[hit]))
            elif str(source).strip().strip("[]'\"").startswith("raw/"):
                unknown.append(str(source).strip())
        if unknown:
            unresolved.append({
                "page": relpath,
                "issue": (
                    "sources 指向的 raw 文件未能解析，长文结构检查无法执行："
                    + ", ".join(unknown)
                ),
            })
        if not resolved:
            continue
        total = sum(line_count for _, line_count in resolved)
        over_single = [p for p, line_count in resolved if line_count > LONG_SOURCE_LINES]
        is_group = len(resolved) > 1 and total > LONG_SOURCE_LINES
        if not over_single and not is_group:
            continue
        what = (
            f"{over_single[0]} 超过 {LONG_SOURCE_LINES} 行"
            if over_single
            else f"{len(resolved)} 个来源作为不可拆分组合计 {total} 行"
        )
        try:
            with open(abspath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue
        positions = _section_positions(content)
        if "精读文本" in positions and "原文" in positions:
            if positions["精读文本"] > positions["原文"]:
                issues.append({
                    "page": relpath,
                    "issue": "长文词条结构顺序错误：`## 精读文本` 必须先于 `## 原文`",
                })
            elif not RAW_ANCHOR.search(content[positions["原文"]:]):
                issues.append({
                    "page": relpath,
                    "issue": "`## 原文` 没有 raw 路径或行号锚点，无法回查逐字原文",
                })
            continue
        missing = [
            f"`## {section}`"
            for section in ("精读文本", "原文")
            if section not in positions
        ]
        issues.append({
            "page": relpath,
            "issue": (
                f"长文（{what}）词条缺 {' 与 '.join(missing)}——第二遍通读未落结构"
            ),
        })
    return issues, unresolved

# ── Main ──

def main():
    pages = scan_wiki_pages()
    raw_files = scan_raw_files()
    taxonomy = load_taxonomy()

    report = {
        "wiki_path": WIKI,
        "total_pages": len(pages),
        "total_raw_files": len(raw_files),
        "findings": {}
    }

    # ① Orphans
    orphans = check_orphans(pages)
    if orphans:
        report["findings"]["orphans"] = orphans

    # ② Broken wikilinks
    broken = check_broken_links(pages)
    if broken:
        report["findings"]["broken_links"] = broken

    # ③ Index completeness
    not_in_index, index_orphans = check_index_completeness(pages)
    if not_in_index or index_orphans:
        report["findings"]["index"] = {
            "pages_not_in_index": not_in_index,
            "index_entries_without_page": index_orphans
        }

    # ④ Frontmatter
    fm_issues = check_frontmatter(pages, taxonomy)
    if fm_issues:
        report["findings"]["frontmatter"] = fm_issues

    # ④b Claim structure
    claim_issues = check_claim_structure(pages)
    if claim_issues:
        report["findings"]["claim_structure"] = claim_issues

    # ④c 长文第二遍结构（精读文本 + 原文）
    second_pass_issues, unresolved_sources = check_second_pass_structure(pages)
    if second_pass_issues:
        report["findings"]["second_pass_structure"] = second_pass_issues
    if unresolved_sources:
        report["findings"]["second_pass_unresolved_sources"] = unresolved_sources
    # ⑤ Stale content
    stale = check_stale_content(pages, raw_files)
    if stale:
        report["findings"]["stale"] = stale

    # ⑥ Contradictions
    contradictions = check_contradictions(pages)
    if contradictions:
        report["findings"]["contradictions"] = contradictions

    # ⑦ Quality
    quality = check_quality_signals(pages)
    if quality:
        report["findings"]["quality"] = quality

    # ⑧ Source drift
    drift = check_source_drift(raw_files)
    if drift:
        report["findings"]["source_drift"] = drift

    # ⑨ Page size
    oversized = check_page_size(pages)
    if oversized:
        report["findings"]["oversized"] = oversized

    # ⑩ Tags
    tag_issues = check_tags(pages, taxonomy)
    if tag_issues:
        report["findings"]["tag_issues"] = tag_issues

    # ⑪ Log rotation
    if check_log_rotation():
        report["findings"]["log_rotation"] = "log.md exceeds 500 entries — rotate to log-YYYY.md"

    # Stub upgrade candidates
    upgrades = check_stub_upgrades(pages)
    if upgrades:
        report["findings"]["stub_upgrades"] = upgrades

    # Stub cleanup
    orphan_stubs = check_stub_cleanup(pages)
    if orphan_stubs:
        report["findings"]["stub_cleanup"] = orphan_stubs

    # Supersedes consistency
    supersedes_issues = check_supersedes_consistency(pages)
    if supersedes_issues:
        report["findings"]["supersedes_consistency"] = supersedes_issues

    # Follows: dangling targets + derived reverse index
    follows_issues, followed_by = check_follows(pages)
    if follows_issues:
        report["findings"]["follows"] = follows_issues
    if followed_by:
        report["followed_by"] = followed_by

    # last-verified staleness (>12 months)
    unverified = check_last_verified(pages)
    if unverified:
        report["findings"]["last_verified"] = unverified

    # Summary
    total_issues = sum(len(v) if isinstance(v, (list, dict)) else 1 for v in report["findings"].values())
    report["total_issues"] = total_issues

    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
