# 配置指南

这份指南只讲安装技能之后还需要配置什么。技能安装完成不代表外部服务都可用：MinerU 负责解析复杂文档，SiliconFlow 负责 RAG 向量索引和可选 rerank。

## 最小可用配置

| 能力 | 是否必需 | 需要配置什么 | 不配置会怎样 |
|---|---:|---|---|
| 普通文档转 Markdown | 否 | `markitdown` Python 包，按需安装 | 只能处理已经是 Markdown/文本的资料 |
| MinerU Flash 解析 | 否 | MinerU MCP 或 CLI | 小 PDF/图片/Office 仍可走 flash 模式，但需要工具本身可用 |
| MinerU 高级解析 | 可选 | `MINERU_API_TOKEN`（MCP）或 `MINERU_TOKEN`（CLI） | 无法用更高额度、多格式输出和高级解析 |
| RAG 向量索引 | 是 | `SILICONFLOW_API_KEY` | 只能做 Markdown/wiki，不能建真实语义检索索引 |
| Rerank 精排 | 可选 | 同一个 `SILICONFLOW_API_KEY` | 查询仍可用，只是不做二次精排 |

## MinerU 配置

MinerU 有两条路：MCP 和 CLI。知识库工作流优先用 MCP；MCP 不可用时再用 CLI。

### 推荐：MinerU MCP

官方说明：

- MinerU ecosystem：https://mineru.net/ecosystem
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
- 填 token 后可用更高额度、更多输出格式和更完整的解析能力。
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

## SiliconFlow RAG 配置

`SiliconFlow-rag` 用 SiliconFlow embeddings 给 Markdown/wiki 建本地向量索引。索引文件仍保存在本地，发送给 SiliconFlow 的是用于生成向量的文本片段、查询文本，以及开启 rerank 时的候选片段。

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
mkdir -p ~/.hermes/private/SiliconFlow-rag
cat > ~/.hermes/private/SiliconFlow-rag/config.json <<'JSON'
{
  "SILICONFLOW_API_KEY": "your_key_here"
}
JSON
chmod 600 ~/.hermes/private/SiliconFlow-rag/config.json
```

兼容旧路径：

```text
~/.codex/SiliconFlow-rag/config.json
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
python skills/SiliconFlow-rag/scripts/build_index.py \
  --md-dir wiki/raw \
  --index-dir 检索索引/raw \
  --model BAAI/bge-m3
```

也可以在配置文件里写非密钥参数：

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

使用配置：

```bash
python skills/SiliconFlow-rag/scripts/build_index.py --config rag_config.json
python skills/SiliconFlow-rag/scripts/query_index.py --config rag_config.json --question "A 和 B 有什么区别？"
```

### 建两个索引

知识库推荐建两个索引：

```bash
python skills/SiliconFlow-rag/scripts/build_index.py \
  --md-dir wiki/raw \
  --index-dir 检索索引/raw \
  --metadata-mode enriched_raw \
  --incremental

python skills/SiliconFlow-rag/scripts/build_index.py \
  --md-dir wiki \
  --index-dir 检索索引/wiki \
  --metadata-mode wiki \
  --exclude-dirs raw \
  --incremental
```

查询时优先用 wiki，再回到 raw 原文证据：

```bash
python skills/SiliconFlow-rag/scripts/query_index.py \
  --wiki-first \
  --wiki-index-dir 检索索引/wiki \
  --raw-index-dir 检索索引/raw \
  --question "这个领域的主要争议是什么？"
```

需要更精确排序时：

```bash
python skills/SiliconFlow-rag/scripts/query_index.py \
  --wiki-first \
  --wiki-index-dir 检索索引/wiki \
  --raw-index-dir 检索索引/raw \
  --rerank \
  --question "A 和 B 有什么区别？"
```

## 给 AI 的教学口径

安装完成后，AI 不要把配置一次性全塞给用户。按这个顺序讲：

1. 先告诉用户：不配 API Key 也能整理 Markdown/wiki，但真实语义检索需要 SiliconFlow。
2. 处理 PDF、扫描件、表格、公式时，先问是否已经有 MinerU MCP；没有就给 MCP 的 `uvx` 配置。
3. 用户要建 RAG 索引时，再指导配置 `SILICONFLOW_API_KEY`。
4. 解释默认嵌入模型是 `BAAI/bge-m3`，适合中英文资料；换模型会导致已有索引需要重建。
5. 强调密钥只放环境变量或本地私有 config，不要写进仓库。

## 快速体检

```bash
mineru-open-api version
mineru-open-api auth --verify
python skills/SiliconFlow-rag/scripts/build_index.py --help
python skills/SiliconFlow-rag/scripts/query_index.py --help
```

如果只是测试脚本流程，不想调用 SiliconFlow：

```bash
python skills/SiliconFlow-rag/scripts/build_index.py --md-dir wiki/raw --index-dir 检索索引/raw --mock
python skills/SiliconFlow-rag/scripts/query_index.py --index-dir 检索索引/raw --question "测试" --mock
```
