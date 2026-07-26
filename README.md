# Inno Knowledge Base Skills

把论文、PDF、网页和长文资料整理成**可搜索、可追问、可在 Obsidian 看图谱**的个人知识库技能包。

这个仓库只维护知识库链路的核心技能，支持 **Claude Code**、**Codex**、**Hermes**。  
文档解析与学术搜索等能力从**上游仓库安装**，不随本仓库复制。

> 小白上手看 [START.md](START.md) —— 不用懂技术，会说目标就行。详细图谱和问答说明看 [KB-GUIDE.md](KB-GUIDE.md)。MinerU / SiliconFlow 配置看 [CONFIG.md](CONFIG.md)。

## AI 使用流程

收到安装请求后，AI 应按以下步骤：

1. **先说明目标** —— 这是知识库技能包，适合把资料整理成长期可用的 Markdown/wiki/Obsidian/RAG 知识库
2. **再确认目标 agent** —— 问用户要装到 Claude Code、Codex、Hermes，还是全部
3. **再安装本仓库技能** —— `bash setup.sh`
4. **再安装上游依赖** —— 按下方「上游技能安装」装 `academic-search`、`mineru-document-extractor`、`markitdown`，并配置 **MinerU MCP**
5. **最后教** —— 安装/更新完成后，不要只说「装好了」，也不要先问要不要介绍；直接读 [START.md](START.md)，给用户一段 3 分钟上手教程

安装后教程示例：

> 「知识库技能包已经装好。我先用 3 分钟带你上手：你不用记技能名，直接说结果就行。比如：
>   "帮我把这个论文文件夹建个知识库" -> 自动走文档解析、深读、wiki 编译和索引
>   "把这几篇新论文加进去" -> 增量补库
>   "A 和 B 有什么区别，引用原文证据" -> 先查 wiki，再回到原文证据
>   "打开 Obsidian 看知识图谱" -> 教你打开 vault 和图谱视图。
>  你想先了解哪块：建库、加资料、Obsidian 看图、提问检索，还是 SiliconFlow API Key？」

## 技能列表

### 本仓库安装（`setup.sh`）

| 技能 | 负责什么 |
|---|---|
| `deep-reading-to-wiki` | 长书、章节、理论文献先生成深读档案，避免浅总结直接入库 |
| `karpathy-wiki` | 把原文和深读档案编译成 claims / concepts / entities / comparisons 图谱 wiki |
| `SiliconFlow-rag` | 建 raw 原文索引 + wiki 结构索引，支持 wiki-first 检索 |
| `social-science-km` | 总调度入口：从资料转换、深读、wiki 到 RAG 索引的一体化流程 |
| `wiki-paper-outline` | 基于已有 wiki 与检索索引，经导师式讨论生成有证据出处的社科论文大纲 |

### 上游安装（不随本仓库复制）

| 技能 / 工具 | 负责什么 | 上游 |
|---|---|---|
| `academic-search` | 搜索相关领域论文、筛选候选文献、判断开放获取 PDF | https://github.com/ustc-ai4science/academic-search |
| `mineru-document-extractor` | PDF、扫描件、表格、公式、多格式文档高保真解析 | https://github.com/opendatalab/MinerU-Ecosystem |
| MinerU MCP | 推荐的文档解析 MCP 服务（知识库工作流优先） | https://github.com/opendatalab/MinerU-Ecosystem/tree/main/mcp |
| `markitdown` | Word、PPT、Excel、HTML、图片等文件轻量转 Markdown | https://github.com/microsoft/markitdown |

## 典型工作流

用户只要说：

> 「帮我把这个文件夹里的论文建个知识库」

AI 应该按场景调度：

1. `academic-search`（上游）—— 可选；本地资料不够时，先找相关领域论文并筛出可合法获取的全文
2. `mineru-document-extractor` / MinerU MCP / `markitdown`（上游）—— 先把文件转成 Markdown 原文
3. `deep-reading-to-wiki` —— 对长文、理论文献、补库候选源做深读档案
4. `karpathy-wiki` —— 编译 Obsidian 可读的图谱 wiki
5. `SiliconFlow-rag` —— 建立可查询索引
6. `social-science-km` —— 负责统筹流程、补库和问答入口

已有知识库后，用户也可以说：

> 「基于这个知识库，和我讨论并规划一篇关于 X 的论文大纲」

此时由 `wiki-paper-outline` 先检索 wiki 和原文索引、提出骨架与质询；用户确认方向后再填充完整大纲，并写入知识库的 `outlines/` 目录。

## 安装

### 1. 安装本仓库技能

```bash
git clone https://github.com/Innoksadk223/kb-skills-repo.git ~/kb-skills
cd ~/kb-skills
bash setup.sh
```

常用命令：

```bash
bash setup.sh --dry-run                 # 先预览，不写文件
bash setup.sh --target codex            # 只安装到 Codex
bash setup.sh --target codex,claude     # 安装到多个 agent
bash setup.sh --target all              # 安装到检测到的所有 agent
bash setup.sh --update-only             # 只更新已有技能，不新增
bash setup.sh --list                    # 查看本仓库技能 + 上游地址
bash setup.sh --help
```

### 2. 上游技能安装（新用户必做）

`setup.sh` 结束后也会打印同样的提示。

#### academic-search

```bash
# Claude Code
git clone https://github.com/ustc-ai4science/academic-search.git ~/.claude/skills/academic-search
bash ~/.claude/skills/academic-search/scripts/check-deps.sh

# Codex
git clone https://github.com/ustc-ai4science/academic-search.git ~/.codex/skills/academic-search

# Hermes
git clone https://github.com/ustc-ai4science/academic-search.git ~/.hermes/skills/research/academic-search
```

上游仓库：https://github.com/ustc-ai4science/academic-search

#### mineru-document-extractor + MinerU MCP

技能与 MCP 都来自 MinerU 官方生态：

- 生态总入口：https://mineru.net/ecosystem
- 技能源码：https://github.com/opendatalab/MinerU-Ecosystem/blob/main/skills/SKILL.md
- **MCP 安装说明（推荐）**：https://github.com/opendatalab/MinerU-Ecosystem/tree/main/mcp  
  README：https://github.com/opendatalab/MinerU-Ecosystem/blob/main/mcp/README.md

安装 skill（Claude 示例）：

```bash
git clone --depth 1 https://github.com/opendatalab/MinerU-Ecosystem.git /tmp/MinerU-Ecosystem
mkdir -p ~/.claude/skills/mineru-document-extractor
cp /tmp/MinerU-Ecosystem/skills/SKILL.md ~/.claude/skills/mineru-document-extractor/SKILL.md
```

安装 / 配置 MinerU MCP（stdio + `uvx`，无需单独 pip install）：

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

- 不填 `MINERU_API_TOKEN` 时走 Flash 免费模式  
- Token：https://mineru.net/apiManage/token  
- 可选 CLI：`npm install -g mineru-open-api`  
- 完整配置见 [CONFIG.md](CONFIG.md)

#### markitdown

```bash
python -m pip install 'markitdown[all]'
python -m markitdown --version
```

上游：https://github.com/microsoft/markitdown  
（官方以 CLI/Python 包为主；agent 需要 skill 目录时，可按官方 CLI 写薄封装，不要依赖本仓库内置副本。）

## 更新

当用户要求更新本技能库时，AI 应先找安装路径：

```bash
cat ~/.codex/skills/.kb-skills-repo-path
cat ~/.claude/skills/.kb-skills-repo-path
cat ~/.hermes/skills/.kb-skills-repo-path
```

然后执行：

```bash
cd <上面读到的仓库路径>
git pull
bash setup.sh --update-only
```

上游技能请分别在其上游仓库 `git pull` 或按上游文档升级；MinerU MCP 用 `uvx` 时会自动取最新版。

## 重要依赖

- **MinerU skill + MCP 均需从上游安装**；本仓库不再内置 `mineru-document-extractor` 副本  
  - MCP：https://github.com/opendatalab/MinerU-Ecosystem/tree/main/mcp  
  - 生态：https://mineru.net/ecosystem
- `SiliconFlow-rag` 需要 SiliconFlow API Key 才能建立真实语义索引；默认嵌入模型是 `BAAI/bge-m3`，详细配置见 [CONFIG.md](CONFIG.md)
- Obsidian 不是必需，但强烈建议安装，用来看知识图谱：https://obsidian.md

## 技能来源

| 能力 | 来源 | 是否随 setup 安装 |
|---|---|---|
| `deep-reading-to-wiki` / `karpathy-wiki` / `SiliconFlow-rag` / `social-science-km` / `wiki-paper-outline` | 本仓库 | 是 |
| `academic-search` | https://github.com/ustc-ai4science/academic-search | 否，上游安装 |
| `mineru-document-extractor` | https://github.com/opendatalab/MinerU-Ecosystem | 否，上游安装 |
| MinerU MCP | https://github.com/opendatalab/MinerU-Ecosystem/tree/main/mcp | 否，上游配置 |
| `markitdown` | https://github.com/microsoft/markitdown | 否，上游安装 |

## 目录结构

```text
kb-skills-repo/
├── skills/
│   ├── deep-reading-to-wiki/
│   ├── karpathy-wiki/
│   ├── SiliconFlow-rag/
│   ├── social-science-km/
│   └── wiki-paper-outline/
├── KB-GUIDE.md
├── CONFIG.md
├── START.md
└── setup.sh
```
