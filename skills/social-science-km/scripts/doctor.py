#!/usr/bin/env python3
"""One-click environment & onboarding doctor for social-science-km + WeKnora.

Checks 5 layers without modifying user data:
1. WeKnora server health (`GET /health`) + Docker/OrbStack setup hints;
2. API credentials (`WEKNORA_API_KEY` / `~/.hermes/private/weknora-rag/config.json` / CLI);
3. Configured models (`Embedding` required, `Rerank` recommended, `KnowledgeQA` only for `weknora_native`);
4. Document parser engines (`mineru_cloud` / `mineru` priority + `builtin` fallback);
5. Skill installation symlinks (4 self-developed KM skills + optional official WeKnora skill).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from weknora_client import (  # noqa: E402
    DEFAULT_HOST,
    PRIVATE_CONFIG_PATH,
    WeKnoraError,
    load_project_config,
    make_backend,
    resolve_credentials,
    resolve_project_config_path,
)

REPO_SKILLS = (
    "social-science-km",
    "deep-reading-to-wiki",
    "karpathy-wiki",
    "wiki-paper-outline",
)
OFFICIAL_WEKNORA_SKILL_NAMES = (
    "weknora",
    "weknora-shared",
    "weknora-rag-search",
)


def _web_ui_url(api_host: str) -> str:
    if ":8080" in api_host:
        return api_host.replace(":8080", "")
    return api_host


def check_skill_symlinks() -> dict:
    trees = [
        Path.home() / ".agents" / "skills",
        Path.home() / ".claude" / "skills",
        Path.home() / ".codex" / "skills",
    ]
    existing_trees = [t for t in trees if t.is_dir()]
    installed: dict[str, list[str]] = {s: [] for s in REPO_SKILLS}
    dangling: list[str] = []
    official_found: list[str] = []

    for tree in existing_trees:
        for entry in sorted(tree.iterdir()):
            if entry.is_symlink() and not entry.exists():
                dangling.append(str(entry))
            if entry.name in REPO_SKILLS and entry.exists():
                installed[entry.name].append(str(tree))
            if entry.name in OFFICIAL_WEKNORA_SKILL_NAMES and entry.exists():
                official_found.append(f"{entry.name} ({tree})")

    cli_bin = shutil.which("weknora")
    return {
        "trees": [str(t) for t in existing_trees],
        "installed": installed,
        "missing": [s for s, locs in installed.items() if not locs],
        "dangling": dangling,
        "official_skills": official_found,
        "weknora_cli": cli_bin,
    }


def run_doctor(project_root: Path, config_arg: str | None = None, mock: bool = False) -> dict:
    cfg_path = resolve_project_config_path(project_root, config_arg)
    cfg = load_project_config(cfg_path)
    weknora_cfg = cfg["weknora"]
    creds = resolve_credentials(weknora_cfg)
    host = str(creds.get("host") or DEFAULT_HOST)
    ui_url = _web_ui_url(host)

    report: dict = {
        "ok": True,
        "host": host,
        "web_ui": ui_url,
        "wiki_mode": cfg["wiki_mode"],
        "checks": [],
        "next_steps": [],
    }

    # 1. Server health
    if mock:
        backend = make_backend(weknora_cfg, project_root, mock=True)
        health = backend.check_health()
        report["checks"].append({"id": "server", "status": "OK", "detail": f"Mock WeKnora active ({health.get('status')})"})
    else:
        try:
            req = urllib.request.Request(f"{host}/health", method="GET")
            with urllib.request.urlopen(req, timeout=6) as resp:
                h_data = json.loads(resp.read().decode("utf-8", errors="replace") or "{}")
            report["checks"].append({
                "id": "server",
                "status": "OK",
                "detail": f"WeKnora API 可达 ({host}/health -> {h_data.get('status', 'ok')})，网页工作台：{ui_url}",
            })
        except Exception as exc:
            report["ok"] = False
            report["checks"].append({
                "id": "server",
                "status": "FAIL",
                "detail": f"无法连接 WeKnora 服务 ({host}/health): {exc}",
            })
            report["next_steps"].append(
                "启动 WeKnora Docker 服务：`git clone https://github.com/Tencent/WeKnora && cd WeKnora && docker compose up -d`（若使用 OrbStack 需代理拉镜像：`orbctl config set network_proxy http://127.0.0.1:7890`）"
            )
            report["skills"] = check_skill_symlinks()
            return report

    # 2. Credentials
    if not mock and not creds.get("api_key") and not creds.get("token") and not creds.get("cli_bin"):
        report["ok"] = False
        report["checks"].append({
            "id": "auth",
            "status": "FAIL",
            "detail": f"未检测到 WeKnora API Key。请配置环境变量 WEKNORA_API_KEY 或写入 {PRIVATE_CONFIG_PATH}",
        })
        report["next_steps"].append(
            f"在浏览器打开 {ui_url} → 左下角「设置 → 发布集成 → API 集成」复制 `sk-...` 密钥，执行：\n"
            f"  mkdir -p '{PRIVATE_CONFIG_PATH.parent}' && printf '{{\"host\":\"{host}\",\"api_key\":\"sk-替换你的密钥\"}}\\n' > '{PRIVATE_CONFIG_PATH}' && chmod 600 '{PRIVATE_CONFIG_PATH}'"
        )
        report["skills"] = check_skill_symlinks()
        return report

    try:
        if not mock:
            backend = make_backend(weknora_cfg, project_root, mock=False)
        models = backend.list_models()
        kbs = backend.list_kbs()
        src_note = creds.get("cred_source") or "mock"
        report["checks"].append({
            "id": "auth",
            "status": "OK",
            "detail": f"API 认证通过（来源: {src_note}，当前空间已有 {len(kbs)} 个知识库）",
        })
    except WeKnoraError as exc:
        report["ok"] = False
        report["checks"].append({"id": "auth", "status": "FAIL", "detail": f"API 认证失败: {exc}"})
        report["next_steps"].append(f"请检查 {PRIVATE_CONFIG_PATH} 或环境变量 WEKNORA_API_KEY 是否与 {ui_url} 当前空间的 API Key 一致。")
        report["skills"] = check_skill_symlinks()
        return report

    # 3. Models
    by_type: dict[str, list[str]] = {}
    for m in models:
        t = str(m.get("type") or "unknown")
        by_type.setdefault(t, []).append(str(m.get("name") or m.get("id") or "?"))

    emb_models = by_type.get("Embedding") or []
    rerank_models = by_type.get("Rerank") or []
    qa_models = by_type.get("KnowledgeQA") or []

    if emb_models:
        rerank_txt = f"；Rerank: {', '.join(rerank_models)}" if rerank_models else "；Rerank: 未配（可选，建议补齐以开启 --rerank 精排）"
        qa_txt = (
            f"；生成模型: {', '.join(qa_models)}"
            if qa_models
            else "；生成模型: 未配（默认 local_karpathy 纯检索无需配置；若选 weknora_native 自动 Wiki 则需配置）"
        )
        report["checks"].append({
            "id": "models",
            "status": "OK" if (cfg["wiki_mode"] != "weknora_native" or qa_models) else "WARN",
            "detail": f"Embedding: {', '.join(emb_models)}{rerank_txt}{qa_txt}",
        })
        if cfg["wiki_mode"] == "weknora_native" and not qa_models:
            report["next_steps"].append(f"当前选择了 wiki_mode=weknora_native，请在 {ui_url}「设置 → 模型管理」添加至少一个对话/生成模型供自动 Wiki 使用。")
    else:
        report["ok"] = False
        report["checks"].append({"id": "models", "status": "FAIL", "detail": "未配置 Embedding 向量模型（建库与检索必需）"})
        report["next_steps"].append(f"打开 {ui_url} →「设置 → 模型管理」添加一个 Embedding 模型（如 Qwen3-Embedding-8B / BAAI/bge-m3）并设为默认。")

    # 4. Parser engines (MinerU priority + builtin fallback)
    try:
        engines = backend.list_parser_engines()
    except Exception:
        engines = []
    avail = {str(e.get("Name")): bool(e.get("Available")) for e in engines if isinstance(e, dict)}
    unavail_reason = {str(e.get("Name")): str(e.get("UnavailableReason") or "") for e in engines if isinstance(e, dict)}

    builtin_ok = avail.get("builtin", True)
    mineru_ok = avail.get("mineru_cloud", False) or avail.get("mineru", False)
    if mineru_ok:
        active_mineru = "mineru_cloud" if avail.get("mineru_cloud") else "mineru"
        p_detail = f"MinerU 高精度解析已就绪 ({active_mineru}) + 内置 docreader 兜底可用（无需本地安装任何转换技能）"
        p_status = "OK"
    elif builtin_ok:
        reason = unavail_reason.get("mineru_cloud") or "未填 MinerU API Key"
        p_detail = (
            f"内置 docreader 解析器已就绪（PDF/DOCX/EPUB/MD 直接可用）；"
            f"mineru_cloud 当前未启用（{reason}）。若有复杂古籍扫描件/公式表格，可在 {ui_url}「设置 → 解析引擎」填入 MinerU Key，配好后 PDF 自动优先走 MinerU。"
        )
        p_status = "OK"
    else:
        report["ok"] = False
        p_detail = "docreader 与 MinerU 均不可用，请检查 weknora-docreader 容器是否正常运行。"
        p_status = "FAIL"
    report["checks"].append({"id": "parser", "status": p_status, "detail": p_detail})

    # 5. Skills & symlinks
    sk = check_skill_symlinks()
    report["skills"] = sk
    repo_skills_dir = SCRIPT_DIR.parents[1]
    if sk["dangling"]:
        report["checks"].append({
            "id": "skills",
            "status": "WARN",
            "detail": f"发现悬空软链：{', '.join(sk['dangling'])}（建议清理）",
        })
    elif sk["missing"] and not mock:
        report["checks"].append({
            "id": "skills",
            "status": "WARN",
            "detail": f"未在全局技能目录检测到：{', '.join(sk['missing'])}",
        })
        report["next_steps"].append(
            f"软链安装本仓库 4 个社科技能：\n  for s in {' '.join(REPO_SKILLS)}; do ln -sfn '{repo_skills_dir}/'\"$s\" ~/.agents/skills/\"$s\"; done"
        )
    else:
        off_note = (
            f"；已检测到官方 WeKnora 工具：{', '.join(sk['official_skills']) or sk['weknora_cli']}"
            if (sk["official_skills"] or sk["weknora_cli"])
            else "；可选通用单库技能：ClawHub `@lyingbug/weknora` 或 WeKnora 内置 MCP"
        )
        report["checks"].append({
            "id": "skills",
            "status": "OK",
            "detail": f"本仓库 4 个自研社科技能就绪（{', '.join(REPO_SKILLS)}）{off_note}",
        })

    return report


def print_human(report: dict) -> None:
    banner = "READY" if report["ok"] else "ACTION REQUIRED"
    print(f"# Social-Science KM × WeKnora 环境体检 [{banner}]")
    print(f"- API 地址：{report['host']}  |  网页检查台：{report['web_ui']}  |  默认模式：{report['wiki_mode']}")
    print()
    icons = {"OK": "[OK]", "WARN": "[WARN]", "FAIL": "[FAIL]"}
    for item in report["checks"]:
        tag = icons.get(item["status"], f"[{item['status']}]")
        print(f"{tag} {item['id']:8s} {item['detail']}")
    if report["next_steps"]:
        print("\n## 下一步修复指引")
        for idx, step in enumerate(report["next_steps"], start=1):
            print(f"{idx}. {step}")


def main() -> None:
    p = argparse.ArgumentParser(description="Check WeKnora + social-science-km onboarding readiness.")
    p.add_argument("--project-root", default=None, help="Optional knowledge-base project root")
    p.add_argument("--config", default=None, help="Optional path to weknora_config.json")
    p.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p.add_argument("--mock", action="store_true", help="Run against offline mock backend")
    args = p.parse_args()

    proj = Path(args.project_root).expanduser().resolve() if args.project_root else Path.cwd().resolve()
    rep = run_doctor(proj, config_arg=args.config, mock=args.mock)
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print_human(rep)
    sys.exit(0 if rep["ok"] else 1)


if __name__ == "__main__":
    main()
