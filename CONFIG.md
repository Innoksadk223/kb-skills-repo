# 配置指南

这份指南只讲安装技能之后还需要配置什么。  
`setup.sh` 只安装本仓库 5 个知识库技能；第三方可选推荐 `academic-search` 以及 `mineru-document-extractor`、`markitdown` 与 **MinerU MCP** 请按需从各自上游安装（见 README「上游与外围能力」）。

技能装好后，外部服务仍需单独配置：MinerU 负责解析复杂文档，SiliconFlow 负责 RAG 向量索引和可选 rerank。

## 最小可用配置

| 能力 | 是否必需 | 需要配置什么 | 不配置会怎样 |
|---|---:|---|---|
| 普通文档转 Markdown | 否 | 上游安装 Microsoft `markitdown` Python 包 | 只能处理已经是 Markdown/文本的资料 |
| MinerU Flash 解析 | 否 | 上游安装 MinerU MCP 或 CLI | 小 PDF/图片/Office 仍可走 flash 模式，但需要工具本身可用 |
| MinerU 高级解析 | 可选 | `MINERU_API_TOKEN`（MCP）或 `MINERU_TOKEN`（CLI） | 无法用更高额度、多格式输出和高级解析 |
| RAG 向量索引 | 是 | `SILICONFLOW_API_KEY` | 只能做 Markdown/wiki，不能建真实语义检索索引 |
| Rerank 精排 | 可选 | 同一个 `SILICONFLOW_API_KEY` | 查询仍可用，只是不做二次精排 |

## 上游组件安装入口

| 组件 | 上游地址 |
|---|---|
| academic-search | https://github.com/ustc-ai4science/academic-search |
| mineru-document-extractor skill | https://github.com/opendatalab/MinerU-Ecosystem/blob/main/skills/SKILL.md |
| **MinerU MCP** | https://github.com/opendatalab/MinerU-Ecosystem/tree/main/mcp |
| MinerU 生态总入口 | https://mineru.net/ecosystem |
| markitdown | https://github.com/microsoft/markitdown |

## MinerU 配置

MinerU 有两条路：MCP 和 CLI。知识库工作流优先用 MCP；MCP 不可用时再用 CLI。  
**本仓库不内置 MinerU skill 副本**——请从上游安装 skill，并按下方配置 MCP。

### 推荐：MinerU MCP

官方说明：

- MinerU ecosystem：https://mineru.net/ecosystem
- MinerU MCP 目录：https://github.com/opendatalab/MinerU-Ecosystem/tree/main/mcp
- MinerU MCP README：https://github.com/opendatalab/MinerU-Ecosystem/blob/main/mcp/README.md

安装 `uv` 后，MCP 客户端可以用 `uvx` 直接启动最新版：

```json
{
  "mcpServers": {
    "mineru": {
      "command": "uvx",
      "args": ["mineru-open-mcp"],
      "env": {
        "MINERU_API_TOKEN": "your_token_here",
        "OUTPUT_DIR": "~/mineru-downloads"
      }
    }
  }
}
```

说明：

- `MINERU_API_TOKEN` 可不填；不填时走 Flash mode，免费、免注册，但额度和输出能力较低。
- 填 token 后可用更高额度、更多输出格式和更完整的解析能力。Token：https://mineru.net/apiManage/token
- `OUTPUT_DIR` 是批量解析或内容过长时保存结果的目录。
- 有些 MCP 客户端会把拖入的文件放进临时沙盒；让用户尽量给出文件的完整路径。

### Streamable HTTP 模式

适合需要手动启动 MCP 服务、再让客户端连接的场景：

```bash
MINERU_API_TOKEN=your_token_here mineru-open-mcp --transport streamable-http --port 8001
```

客户端配置：

```json
{
  "mcpServers": {
    "mineru": {
      "type": "streamableHttp",
      "url": "http://127.0.0.1:8001/mcp"
    }
  }
}
```

### 备用：MinerU CLI

安装：

```bash
npm install -g mineru-open-api
mineru-open-api version
```

或 macOS/Linux 使用 Go：

```bash
go install github.com/opendatalab/MinerU-Ecosystem/cli/mineru-open-api@latest
```

认证：

```bash
mineru-open-api auth
export MINERU_TOKEN="your_token_here"
```

CLI token 读取顺序：`--token` 参数 > `MINERU_TOKEN` 环境变量 > `~/.mineru/config.yaml`。

常用命令：

```bash
mineru-open-api flash-extract paper.pdf -o ./out/
mineru-open-api extract paper.pdf -o ./out/ -f md,json --model pipeline
mineru-open-api extract paper.pdf -o ./out/ -f md --model vlm
```

模型选择：

- `pipeline`：更稳，适合要求不幻觉的解析。
- `vlm`：版式理解更强，适合复杂排版，但极少数情况下可能生成幻觉文本。
- `html` / MinerU-HTML：适合需要 HTML 结构的场景。

### MinerU skill 安装（上游）

```bash
git clone --depth 1 https://github.com/opendatalab/MinerU-Ecosystem.git /tmp/MinerU-Ecosystem
mkdir -p ~/.claude/skills/mineru-document-extractor
cp /tmp/MinerU-Ecosystem/skills/SKILL.md ~/.claude/skills/mineru-document-extractor/SKILL.md
# Codex: ~/.codex/skills/mineru-document-extractor
# Hermes: ~/.hermes/skills/productivity/mineru-document-extractor
```

## markitdown 配置

```bash
python -m pip install 'markitdown[all]'
python -m markitdown --version
```

上游：https://github.com/microsoft/markitdown

## academic-search 配置（第三方可选推荐）

仅在本地论文资料不足、需要搜索和筛选候选文献时配置；已有完整资料集可跳过。

```bash
git clone https://github.com/ustc-ai4science/academic-search.git ~/.claude/skills/academic-search
bash ~/.claude/skills/academic-search/scripts/check-deps.sh
```

上游：https://github.com/ustc-ai4science/academic-search  
建议申请 Semantic Scholar API Key 以提高配额：https://www.semanticscholar.org/product/api#api-key-form

## SiliconFlow RAG 配置

`siliconflow-rag` 用 SiliconFlow embeddings 给 Markdown/wiki 建本地向量索引。技能标识为小写 `siliconflow-rag`，仓库磁盘目录为 `skills/SiliconFlow-rag/`。索引文件仍保存在本地，发送给 SiliconFlow 的是用于生成向量的文本片段、查询文本，以及开启 rerank 时的候选片段。

下列 Python 示例中的 `<skills-repo>` 请替换为技能仓库的绝对路径，`<知识库项目>` 替换为知识库根目录。先 `cd "<知识库项目>"`，使 `wiki/`、`检索索引/` 和 `rag_config.json` 均相对该项目解析；脚本从技能仓库直接调用。

官方说明：

- Embeddings API：https://docs.siliconflow.cn/en/api-reference/embeddings/create-embeddings
- Rerank API：https://docs.siliconflow.cn/en/api-reference/rerank/create-rerank
- API Key：https://cloud.siliconflow.cn/account/ak

### API Key

推荐用环境变量，最简单也最通用：

```bash
export SILICONFLOW_API_KEY="your_key_here"
```

如果要保存到本地私有文件，当前脚本优先读取：

```bash
mkdir -p ~/.hermes/private/siliconflow-rag
cat > ~/.hermes/private/siliconflow-rag/config.json <<'JSON'
{
  "SILICONFLOW_API_KEY": "your_key_here"
}
JSON
chmod 600 ~/.hermes/private/siliconflow-rag/config.json
```

兼容旧路径（同样小写，不需要迁移已有配置）：

```text
~/.codex/siliconflow-rag/config.json
```

不要把真实 key 写进仓库、`rag_config.json`、README、日志或索引 manifest。

### 默认模型

本仓库脚本默认：

| 用途 | 默认值 | 说明 |
|---|---|---|
| 嵌入模型 | `BAAI/bge-m3` | 官方 embeddings API 支持；输入上限 8192 tokens，适合中英混合语料 |
| 可选 rerank | `Qwen/Qwen3-Reranker-8B` | 查询时加 `--rerank` 才会调用 |

可替换模型示例：

```bash
cd "<知识库项目>"
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/build_index.py" \
  --md-dir wiki/raw \
  --index-dir 检索索引/raw \
  --model BAAI/bge-m3
```

也可以在项目根目录的 `rag_config.json` 里写非密钥参数：

```json
{
  "build": {
    "model": "BAAI/bge-m3",
    "chunk_size": 1200,
    "overlap": 200,
    "batch_size": 16,
    "timeout": 60,
    "sleep": 0
  },
  "query": {
    "embedding_model": "BAAI/bge-m3",
    "rerank_model": "Qwen/Qwen3-Reranker-8B",
    "top_k": 6,
    "candidates": 12,
    "wiki_top_k": 5
  }
}
```

使用配置时仍明确指定数据与索引目录：

```bash
cd "<知识库项目>"
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/build_index.py" \
  --config rag_config.json --md-dir wiki/raw --index-dir 检索索引/raw
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/query_index.py" \
  --config rag_config.json --index-dir 检索索引/raw --question "A 和 B 有什么区别？"
```

### 建两个索引

完整建库或索引更新任务中，知识库推荐建两个索引：

```bash
cd "<知识库项目>"
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/build_index.py" \
  --md-dir wiki/raw \
  --index-dir 检索索引/raw \
  --metadata-mode enriched_raw \
  --incremental

python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/build_index.py" \
  --md-dir wiki \
  --index-dir 检索索引/wiki \
  --metadata-mode wiki \
  --include-dirs claims,concepts,entities,comparisons,debates,observations,structures,predicts,synthesis,queries \
  --exclude-dirs raw,_archive \
  --incremental
```

Wiki 索引覆盖 `wiki/` 下的图谱页面，包括按证据需要创建的 `observations/`、`structures/`、`predicts/`；项目根目录的论文大纲 `outlines/` 不在该索引范围内。

查询时可先用 wiki，再回到 raw 原文证据：

```bash
cd "<知识库项目>"
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/query_index.py" \
  --wiki-first \
  --wiki-index-dir 检索索引/wiki \
  --raw-index-dir 检索索引/raw \
  --question "这个领域的主要争议是什么？"
```

默认使用基础检索；召回不足时再考虑 `--multi-query`，需要更精确排序时使用 `--rerank`，并遵守当前任务的外部服务授权范围：

```bash
cd "<知识库项目>"
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/query_index.py" \
  --wiki-first \
  --wiki-index-dir 检索索引/wiki \
  --raw-index-dir 检索索引/raw \
  --rerank \
  --question "A 和 B 有什么区别？"
```

### 通过总入口检查与查询

`social-science-km` 的 helper 可直接从技能仓库调用并指定项目，无需复制到知识库。已有项目副本仍兼容，不自动覆盖或删除。

```bash
cd "<知识库项目>"
python3 "<skills-repo>/skills/social-science-km/references/km_query.py" \
  --project-root "<知识库项目>" --check
python3 "<skills-repo>/skills/social-science-km/references/km_query.py" \
  --project-root "<知识库项目>" "这个领域的主要争议是什么？"
```

`--check` 检查 raw / wiki 双索引后结束，不更新索引。实际查询先选择 raw / wiki 模式，再检查必要索引；直接查 raw 不受无关 Wiki 索引过期阻塞，但仍检查 raw 自身及其 enriched_raw 依赖。仅查询不触发摄入；仅 Wiki 结构体检交给 `karpathy-wiki`，报告后结束。获准沿用旧索引查询或写大纲时，应显式加 `--skip-check` 并说明证据可能滞后。

## 给 AI 的教学口径

安装完成后，AI 不要把配置一次性全塞给用户。按这个顺序讲：

1. 先告诉用户：`setup.sh` 只装本仓库 5 个技能；academic-search 是其他项目维护的可选论文搜集入口，MinerU / markitdown 按文档类型从上游安装。
2. 先告诉用户：不配 API Key 也能整理 Markdown/wiki，但真实语义检索需要 SiliconFlow。
3. 处理 PDF、扫描件、表格、公式时，先问是否已有 MinerU skill + MCP；没有就给上游 skill 安装命令和 MCP 的 `uvx` 配置（见上文）。
4. 用户要建 RAG 索引时，再指导配置 `SILICONFLOW_API_KEY`。
5. 解释默认嵌入模型是 `BAAI/bge-m3`，适合中英文资料；换模型会导致已有索引需要重建。
6. 强调密钥只放环境变量或本地私有 config，不要写进仓库。

## 快速体检

```bash
cd "<知识库项目>"
mineru-open-api version
mineru-open-api auth --verify
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/build_index.py" --help
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/query_index.py" --help
```

如果只是测试脚本流程，不想调用 SiliconFlow：

```bash
cd "<知识库项目>"
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/build_index.py" --md-dir wiki/raw --index-dir 检索索引/raw --mock
python3 "<skills-repo>/skills/SiliconFlow-rag/scripts/query_index.py" --index-dir 检索索引/raw --question "测试" --mock
```
