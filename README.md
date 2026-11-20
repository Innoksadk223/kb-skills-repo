# kb-skills-repo · 社科知识管理（WeKnora 一体化解析与双模式 Wiki 技能集）

面向人文社科研究的 Agent 知识库与论文论证支持技能仓库。依托 **Tencent/WeKnora** 的服务端多格式解析（PDF 优先走 MinerU，内置引擎自动兜底）与混合检索（`pgvector` 向量 + `ParadeDB BM25` + `Rerank`），彻底免去本地安装格式转换插件与预先生成本地 `raw/*.md` 的繁琐步骤，同时支持**我们的社科精读卡片 Wiki** 与 **WeKnora 自带自动 Wiki** 两种路线按需切换。

---

## 一、技能边界：官方底座 vs 本仓库 4 个自研社科技能

本仓库遵循「官方已有的通用能力不重造、社科专属方法论自研内聚、每个技能既可单独用也可由 KM 编排」原则：

| 层级 | 技能名称 | 归属 | 核心职责 | 单独使用 vs KM 编排 |
|---|---|---|---|---|
| **官方通用底座**（按需选装） | `@lyingbug/weknora`（ClawHub 技能）或 `weknora-shared` + `weknora-rag-search`（官方 CLI 技能）或内置 MCP | **WeKnora 官方生态** | 日常通用的单库建库、传零散文件/网页、普通单库问答检索 | 日常对普通资料库做单步操作时直接调用 |
| **社科总协调与双库引擎** | [`social-science-km`](skills/social-science-km/SKILL.md) | **本仓库自研** | 社科全流程按需路由、源文件分流门禁、`<project>-raw` / `<project>-wiki` 增量同步、**Wiki→Raw 二跳检索**（`km_query.py`）、新手一键体检（`doctor.py`） | 既可一键编排建库/补库全链路，也可单独查索引、跑二跳检索或做环境体检 |
| **深读精析层** | [`deep-reading-to-wiki`](skills/deep-reading-to-wiki/SKILL.md) | **本仓库自研** | 对典籍、专著、论文集、学位论文做分窗精读，产出带 `#p.X` 页码锚点与 10 字段胶囊的 `reading_dossiers/*.md` | **可单独用**（给任意一篇 PDF/文档直接做深读报告），也可由 KM 在门禁后调度 |
| **社科图谱层** | [`karpathy-wiki`](skills/karpathy-wiki/SKILL.md) | **本仓库自研** | 编译与维护本地 Obsidian 图谱可读的 8 类社科卡片（`claims` / `concepts` / `debates` / `comparisons` / `entities` / `observations` / `structures` / `predicts`）+ `lint.py` 健康检查 | **可单独用**（单独维护本地研究图谱或跑结构体检），也可由 KM 批量调度并同步至 WeKnora |
| **论文大纲层** | [`wiki-paper-outline`](skills/wiki-paper-outline/SKILL.md) | **本仓库自研** | 基于正反方命题卡与原文证据，以导师质询方式分「骨架 → 追问 → 填充」三阶段产出 `outlines/*.md` | **可单独用**（对着已有社科 Wiki 讨论论文框架），也可作为 KM 下游出口 |

---

## 二、两种可选 Wiki 模式对比（`local_karpathy` vs `weknora_native`）

新建知识库**不再生成本地 `wiki/raw/*.md` 中间层**：原始 PDF / DOCX / EPUB / MD 留在只读 `<资料夹>/` 中直传 WeKnora `<project>-raw` 库，保留精确 PDF 页码（`p.X`）；已建好的旧知识库（含 `wiki/raw/`）保持原样 100% 兼容。

在项目根目录 `weknora_config.json` 中通过 `"wiki_mode"`（或命令行 `--wiki-mode`）任选其一：

| 对比维度 | 路线 A：`local_karpathy`（默认推荐 · 社科精读卡片库） | 路线 B：`weknora_native`（可选 · WeKnora 自带自动 Wiki） |
|---|---|---|
| **构建方式** | 多模态直读原 PDF → 深读档案 → 本地编译 8 类论证卡片（注明 `文件名.pdf#p.X`）→ 同步至 `<project>-wiki` | 原始文件传入 `<project>-raw` 并开启 `wiki_enabled=true`，由 WeKnora 后台大模型全自动抽取概念/人物/摘要页 |
| **在 WeKnora 网页端怎么看** | 打开 `http://localhost` 知识库列表，并列看到 **`<project>-raw`**（原文献）与 **`<project>-wiki`**（全部社科卡片与切块）；本地可用 Obsidian 看双链图谱 | 打开 `http://localhost` 进入 **`<project>-raw` →「Wiki / 图谱」页签**，直接浏览自动生成的条目树、聚类图谱与版本历史 |
| **WeKnora 模型要求** | 仅需 **Embedding**（必选）+ **Rerank**（推荐）；Agent 纯检索**无需在 WeKnora 配对话大模型** | 除 Embedding + Rerank 外，需在 WeKnora 多配一个**生成模型**供后台自动写 Wiki |
| **Agent 二跳检索** | 第一跳搜 `<project>-wiki`（命题正反方关系边）→ 第二跳搜 `<project>-raw` 抽带页码原文切块 | 第一跳调原生 `/wiki/search` → 第二跳搜 `<project>-raw` 抽带页码原文切块 |
| **适用场景** | **毕业论文/期刊论文写作、专著典籍精读、学派争鸣梳理、导师式大纲推演** | **日常文献速览、课题初期快速摸底、零手工维护成本** |

---

## 三、三步快速安装与一键验通（供任何人开箱使用）

### 第 1 步：启动 WeKnora 服务并配置模型

1. 按 [Tencent/WeKnora 官方文档](https://github.com/Tencent/WeKnora) 使用 Docker Compose（macOS 推荐 OrbStack）启动标准版服务（默认前端 `http://localhost`，后端 API `http://localhost:8080`）。
2. 打开 `http://localhost` 进入「设置」：
   - **模型管理**：配置一个 **Embedding 模型**（必选）与 **Rerank 模型**（强烈推荐）；若需使用 `weknora_native` 自动 Wiki 或网页聊天，再配一个对话生成模型。
   - **解析引擎（可选增强）**：若处理复杂排版/古籍扫描 PDF，填入 **MinerU Cloud API Key**（或自建 MinerU 地址），WeKnora 解析 PDF 时会自动优先走 MinerU，未配置则自动使用内置 `docreader` 解析引擎。
   - **获取 API Key**：在「设置 → API Key」复制密钥，写入私有配置（切勿提交进代码库）：

```bash
mkdir -p ~/.hermes/private/weknora-rag
cat > ~/.hermes/private/weknora-rag/config.json << 'EOF'
{
  "host": "http://localhost:8080",
  "api_key": "sk-替换为你的WeKnora密钥"
}
EOF
chmod 600 ~/.hermes/private/weknora-rag/config.json
```

### 第 2 步：安装技能到你的 Agent

将本仓库 `skills/` 下的 4 个社科技能软链到你的 Agent 技能目录（以 `~/.agents/skills` 为例；Claude Code 可链至 `~/.claude/skills`，Codex 可链至 `~/.codex/skills`）：

```bash
git clone <本仓库地址> ~/kb-skills-repo
mkdir -p ~/.agents/skills

for s in social-science-km deep-reading-to-wiki karpathy-wiki wiki-paper-outline; do
  ln -sfn ~/kb-skills-repo/skills/$s ~/.agents/skills/$s
done
```

> *可选*：若日常还想用自然语言直接管理零散普通知识库，可额外安装 WeKnora 官方通用技能（ClawHub `@lyingbug/weknora` 或官方 CLI 的 `weknora-shared` / `weknora-rag-search`）。

### 第 3 步：运行 `doctor.py` 一键体检

纯 Python 3 标准库脚本，无需额外 `pip install` 任何依赖：

```bash
python3 ~/.agents/skills/social-science-km/scripts/doctor.py
```

看到 `总结: 5/5 项就绪` 即表示服务、凭证、Embedding/Rerank、解析引擎与 4 个技能软链全部就绪！若缺某一项，`doctor.py` 会直接给出可复制的修复指引。

---

## 四、常用工作流速查

### 1. 在 Agent 对话中直接提问或建库（最常用）
直接对 Agent 说：
- *「帮我把 `~/文献/孝道研究` 建一个社科知识库（默认用我们的本地 Wiki / 或用 WeKnora 自带 Wiki）」*
- *「基于 `~/文献/孝道研究（知识库）` 查一下：孝为什么能作为仁之本？学界有哪些批评？」*
- *「单独用 `deep-reading-to-wiki` 帮我精读这篇 PDF：`~/文献/孝道研究/肖群忠.pdf`」*
- *「基于现有知识库帮我构思一篇关于儒家亲亲伦理边界的论文大纲」*

### 2. 命令行直接调用脚本（可供任意 Agent 或终端复用）

```bash
# 同步原始文献夹 -> WeKnora <project>-raw（不生成本地 wiki/raw/*.md）
python3 ~/.agents/skills/social-science-km/scripts/sync_kb.py \
  --project-root "~/文献/孝道研究（知识库）" \
  --source-dir "~/文献/孝道研究" \
  --wiki-mode local_karpathy --incremental

# 增量检查并同步 <project>-raw 与 <project>-wiki 双库
python3 ~/.agents/skills/social-science-km/scripts/check_rebuild_rag.py \
  --project-root "~/文献/孝道研究（知识库）"

# Wiki -> Raw 二跳检索（返回带原文件名 + PDF 页码 p.X 的原文证据）
python3 ~/.agents/skills/social-science-km/scripts/km_query.py \
  --project-root "~/文献/孝道研究（知识库）" "仁与礼的关系" --rerank
```

### 3. 运行离线回归自测

```bash
python3 skills/social-science-km/scripts/self_test.py
python3 skills/deep-reading-to-wiki/scripts/validate_dossier_self_test.py
python3 skills/karpathy-wiki/scripts/lint_self_test.py
```
