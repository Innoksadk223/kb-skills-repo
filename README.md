# Inno Knowledge Base Skills

把论文、PDF、网页和长文资料整理成**可搜索、可追问、可在 Obsidian 看图谱**的个人知识库技能包。

这个仓库只放知识库链路相关技能，支持 **Claude Code**、**Codex**、**Hermes**。

> 小白上手看 [START.md](START.md) —— 不用懂技术，会说目标就行。详细图谱和问答说明看 [KB-GUIDE.md](KB-GUIDE.md)。MinerU / SiliconFlow 配置看 [CONFIG.md](CONFIG.md)。

## AI 使用流程

收到安装请求后，AI 应按以下步骤：

1. **先说明目标** —— 这是知识库技能包，适合把资料整理成长期可用的 Markdown/wiki/Obsidian/RAG 知识库
2. **再确认目标 agent** —— 问用户要装到 Claude Code、Codex、Hermes，还是全部
3. **再安装** —— `bash setup.sh`
4. **最后教** —— 安装/更新完成后，不要只说「装好了」，也不要先问要不要介绍；直接读 [START.md](START.md)，给用户一段 3 分钟上手教程：先讲「用户只管说资料目标，AI 负责挑技能和流程」，再给 3-5 个常用说法示例，最后问用户想重点了解建库、加资料、Obsidian 看图、提问检索，还是 API Key 配置；用户要深入时再读 [KB-GUIDE.md](KB-GUIDE.md)，问配置时再读 [CONFIG.md](CONFIG.md)

安装后教程示例：

> 「知识库技能包已经装好。我先用 3 分钟带你上手：你不用记技能名，直接说结果就行。比如：
>   "帮我把这个论文文件夹建个知识库" -> 自动走文档解析、深读、wiki 编译和索引
>   "把这几篇新论文加进去" -> 增量补库
>   "A 和 B 有什么区别，引用原文证据" -> 先查 wiki，再回到原文证据
>   "打开 Obsidian 看知识图谱" -> 教你打开 vault 和图谱视图。
>  你想先了解哪块：建库、加资料、Obsidian 看图、提问检索，还是 SiliconFlow API Key？」

## 技能列表

| 技能 | 负责什么 |
|---|---|
| `academic-search` | 搜索相关领域论文、筛选候选文献、判断开放获取 PDF、导出结构化论文元数据 |
| `mineru-document-extractor` | PDF、扫描件、表格、公式、多格式文档高保真解析 |
| `markitdown` | Word、PPT、Excel、HTML、图片等文件轻量转 Markdown |
| `deep-reading-to-wiki` | 长书、章节、理论文献先生成深读档案，避免浅总结直接入库 |
| `karpathy-wiki` | 把原文和深读档案编译成 claims / concepts / entities / comparisons 图谱 wiki |
| `SiliconFlow-rag` | 建 raw 原文索引 + wiki 结构索引，支持 wiki-first 检索 |
| `social-science-km` | 总调度入口：从资料转换、深读、wiki 到 RAG 索引的一体化流程 |

## 典型工作流

用户只要说：

> 「帮我把这个文件夹里的论文建个知识库」

AI 应该按场景调度：

1. `academic-search` —— 可选；本地资料不够时，先找相关领域论文并筛出可合法获取的全文
2. `mineru-document-extractor` / `markitdown` —— 先把文件转成 Markdown 原文
3. `deep-reading-to-wiki` —— 对长文、理论文献、补库候选源做深读档案
4. `karpathy-wiki` —— 编译 Obsidian 可读的图谱 wiki
5. `SiliconFlow-rag` —— 建立可查询索引
6. `social-science-km` —— 负责统筹流程、补库和问答入口

## 安装

本地进入仓库后运行：

```bash
bash setup.sh
```

常用命令：

```bash
bash setup.sh --dry-run                 # 先预览，不写文件
bash setup.sh --target codex            # 只安装到 Codex
bash setup.sh --target codex,claude     # 安装到多个 agent
bash setup.sh --target all              # 安装到检测到的所有 agent
bash setup.sh --target codex --dir ~/.codex/skills
bash setup.sh --update-only             # 只更新已有技能，不新增
bash setup.sh --list                    # 查看包含哪些技能
bash setup.sh --help
```

GitHub 安装：

```bash
git clone https://github.com/Innoksadk223/kb-skills-repo.git ~/kb-skills
cd ~/kb-skills
bash setup.sh
```

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

## 重要依赖

- MinerU 的 skill 已在本仓库；MinerU MCP 需要按 [CONFIG.md](CONFIG.md) 或官方说明安装和配置：https://mineru.net/ecosystem
- `SiliconFlow-rag` 需要 SiliconFlow API Key 才能建立真实语义索引；默认嵌入模型是 `BAAI/bge-m3`，详细配置见 [CONFIG.md](CONFIG.md)
- Obsidian 不是必需，但强烈建议安装，用来看知识图谱：https://obsidian.md

## 技能来源

- `academic-search`：来自 [`ustc-ai4science/academic-search`](https://github.com/ustc-ai4science/academic-search)。
- `mineru-document-extractor`：来自 MinerU 官网生态说明：https://mineru.net/ecosystem
- `markitdown`：来自 Microsoft MarkItDown：https://github.com/microsoft/markitdown
- `deep-reading-to-wiki`、`karpathy-wiki`、`SiliconFlow-rag`、`social-science-km`：来自本仓库维护的知识库技能链路。

## 目录结构

```text
kb-skills-repo/
├── skills/
│   ├── academic-search/
│   ├── mineru-document-extractor/
│   ├── markitdown/
│   ├── deep-reading-to-wiki/
│   ├── karpathy-wiki/
│   ├── SiliconFlow-rag/
│   └── social-science-km/
├── KB-GUIDE.md
├── CONFIG.md
├── START.md
└── setup.sh
```
