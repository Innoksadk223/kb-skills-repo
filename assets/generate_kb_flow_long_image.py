#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "kb-skills-flow-long.png"

W = 1080
PAD_X = 76
TOP = 76
BOTTOM = 90
CARD_W = W - PAD_X * 2

FONT_CN = "/System/Library/Fonts/Hiragino Sans GB.ttc"
FONT_CN_BOLD = "/System/Library/Fonts/STHeiti Medium.ttc"
FONT_MONO = "/System/Library/Fonts/SFNSMono.ttf"


def font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    if mono:
        return ImageFont.truetype(FONT_MONO, size)
    return ImageFont.truetype(FONT_CN_BOLD if bold else FONT_CN, size)


F_TITLE = font(58, bold=True)
F_SUB = font(27)
F_EYEBROW = font(20, bold=True)
F_CARD_TITLE = font(34, bold=True)
F_BODY = font(23)
F_SMALL = font(20)
F_BADGE = font(19, bold=True)
F_MONO = font(20, mono=True)


def text_w(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> float:
    return draw.textlength(text, font=fnt)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue
        current = ""
        tokens = re.findall(r"[A-Za-z0-9_./:+-]+|[，。；：、？！“”（）]|[^\x00-\x7F]|\s+|.", paragraph)
        for token in tokens:
            if token.isspace():
                token = " "
            candidate = current + token
            if text_w(draw, candidate, fnt) <= max_w:
                current = candidate
            else:
                if current:
                    lines.append(current.rstrip())
                if text_w(draw, token, fnt) <= max_w:
                    current = token.lstrip()
                else:
                    current = ""
                    for ch in token:
                        candidate = current + ch
                        if text_w(draw, candidate, fnt) <= max_w:
                            current = candidate
                        else:
                            if current:
                                lines.append(current)
                            current = ch
        if current:
            lines.append(current.rstrip())
    return lines


def paragraph_height(draw: ImageDraw.ImageDraw, lines: list[str], fnt: ImageFont.FreeTypeFont, line_gap: int) -> int:
    if not lines:
        return 0
    bbox = draw.textbbox((0, 0), "知", font=fnt)
    line_h = bbox[3] - bbox[1]
    return len(lines) * line_h + max(0, len(lines) - 1) * line_gap


def rounded_rect_with_shadow(
    base: Image.Image,
    xy: tuple[int, int, int, int],
    radius: int,
    fill: str,
    outline: str | None = None,
    shadow: tuple[int, int, int, int] = (0, 0, 0, 70),
) -> None:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x1, y1, x2, y2 = xy
    d.rounded_rectangle((x1 + 8, y1 + 12, x2 + 8, y2 + 12), radius=radius, fill=shadow)
    layer = layer.filter(ImageFilter.GaussianBlur(18))
    base.alpha_composite(layer)
    d = ImageDraw.Draw(base)
    d.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=1 if outline else 0)


def draw_badge(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, fill: str, fg: str = "#ffffff") -> int:
    px = 16
    py = 8
    tw = int(text_w(draw, text, F_BADGE))
    h = 38
    draw.rounded_rectangle((x, y, x + tw + px * 2, y + h), radius=19, fill=fill)
    draw.text((x + px, y + py - 2), text, font=F_BADGE, fill=fg)
    return x + tw + px * 2 + 10


def draw_arrow(draw: ImageDraw.ImageDraw, cx: int, y: int, color: str) -> None:
    draw.line((cx, y, cx, y + 54), fill=color, width=5)
    draw.polygon([(cx - 14, y + 42), (cx + 14, y + 42), (cx, y + 62)], fill=color)


def draw_card(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    y: int,
    step: str,
    title: str,
    body: str,
    outputs: list[str],
    accent: str,
    tags: list[str],
) -> int:
    x = PAD_X
    inner = 34
    max_text_w = CARD_W - inner * 2 - 92
    body_lines = wrap_text(draw, body, F_BODY, max_text_w)
    output_text = " / ".join(outputs)
    output_lines = wrap_text(draw, output_text, F_SMALL, max_text_w)
    h = 168 + paragraph_height(draw, body_lines, F_BODY, 10) + paragraph_height(draw, output_lines, F_SMALL, 8)
    h += 48 if tags else 0
    h = max(h, 318)

    rounded_rect_with_shadow(img, (x, y, x + CARD_W, y + h), 18, "#F8FAFC", "#D9E3EA")

    draw.rounded_rectangle((x, y, x + 18, y + h), radius=9, fill=accent)
    draw.ellipse((x + inner, y + 34, x + inner + 58, y + 92), fill=accent)
    sw = text_w(draw, step, F_EYEBROW)
    draw.text((x + inner + 29 - sw / 2, y + 49), step, font=F_EYEBROW, fill="#FFFFFF")

    tx = x + inner + 82
    draw.text((tx, y + 32), title, font=F_CARD_TITLE, fill="#10202A")
    draw.text((tx, y + 80), "技能流程节点", font=F_EYEBROW, fill=accent)

    cy = y + 122
    for line in body_lines:
        draw.text((tx, cy), line, font=F_BODY, fill="#273946")
        cy += 40

    cy += 14
    draw.text((tx, cy), "产出", font=F_EYEBROW, fill="#526676")
    cy += 34
    for line in output_lines:
        draw.text((tx, cy), line, font=F_SMALL, fill="#405464")
        cy += 34

    if tags:
        cy += 10
        bx = tx
        for tag in tags:
            fill = accent if bx == tx else "#E6EDF2"
            fg = "#FFFFFF" if bx == tx else "#405464"
            nx = draw_badge(draw, bx, cy, tag, fill, fg)
            if nx > x + CARD_W - inner:
                cy += 48
                bx = tx
                nx = draw_badge(draw, bx, cy, tag, fill, fg)
            bx = nx

    return y + h


def gradient_background(width: int, height: int) -> Image.Image:
    img = Image.new("RGBA", (width, height), "#0D1B22")
    px = img.load()
    top = (10, 28, 37)
    mid = (20, 55, 62)
    bot = (12, 24, 31)
    for yy in range(height):
        t = yy / max(1, height - 1)
        if t < 0.55:
            k = t / 0.55
            col = tuple(int(top[i] * (1 - k) + mid[i] * k) for i in range(3))
        else:
            k = (t - 0.55) / 0.45
            col = tuple(int(mid[i] * (1 - k) + bot[i] * k) for i in range(3))
        for xx in range(width):
            px[xx, yy] = (*col, 255)
    return img


def draw_header(img: Image.Image, draw: ImageDraw.ImageDraw) -> int:
    y = TOP
    draw.text((PAD_X, y), "个人知识库技能流程", font=F_TITLE, fill="#F8FBFC")
    y += 76
    lines = wrap_text(
        draw,
        "从原始资料到 Obsidian 图谱，再到基于证据的 RAG 问答：六个技能各守一段，AI 负责调度。",
        F_SUB,
        W - PAD_X * 2,
    )
    for line in lines:
        draw.text((PAD_X, y), line, font=F_SUB, fill="#BFD0D7")
        y += 42
    y += 26
    x = PAD_X
    for badge, color in [
        ("Markdown 原文", "#28A1A7"),
        ("深读档案", "#5C8CE6"),
        ("图谱 Wiki", "#61A36F"),
        ("SiliconFlow RAG", "#D77B4D"),
    ]:
        x = draw_badge(draw, x, y, badge, color)
    return y + 82


def draw_config_card(img: Image.Image, draw: ImageDraw.ImageDraw, y: int) -> int:
    x = PAD_X
    h = 330
    rounded_rect_with_shadow(img, (x, y, x + CARD_W, y + h), 18, "#102934", "#2B4B57", (0, 0, 0, 90))
    draw.text((x + 34, y + 32), "配置底座", font=F_CARD_TITLE, fill="#F8FBFC")
    draw.text((x + 34, y + 82), "这些不是技能本体，但决定流程能跑到什么程度。", font=F_BODY, fill="#BFD0D7")
    items = [
        ("MinerU MCP", "Flash 可免 key；高级解析配置 MINERU_API_TOKEN"),
        ("SiliconFlow", "RAG 需要 SILICONFLOW_API_KEY；默认嵌入模型 BAAI/bge-m3"),
        ("Obsidian", "打开知识库文件夹，Ctrl/Cmd + G 查看图谱"),
    ]
    cy = y + 138
    for title, desc in items:
        draw.rounded_rectangle((x + 34, cy, x + 206, cy + 46), radius=10, fill="#E8F3F4")
        draw.text((x + 52, cy + 10), title, font=F_BADGE, fill="#12313B")
        draw.text((x + 232, cy + 9), desc, font=F_SMALL, fill="#D7E3E8")
        cy += 58
    return y + h


def draw_footer(img: Image.Image, draw: ImageDraw.ImageDraw, y: int) -> int:
    x = PAD_X
    h = 318
    rounded_rect_with_shadow(img, (x, y, x + CARD_W, y + h), 18, "#F8FAFC", "#D9E3EA")
    draw.text((x + 34, y + 32), "用户只需要这样说", font=F_CARD_TITLE, fill="#10202A")
    examples = [
        "帮我把这个论文文件夹建个知识库",
        "把这几篇新论文加进去，旧资料不要重跑",
        "A 和 B 有什么区别？请引用原文证据",
        "教我在 Obsidian 打开这个知识库",
    ]
    cy = y + 94
    for ex in examples:
        draw.text((x + 42, cy), "“" + ex + "”", font=F_BODY, fill="#273946")
        cy += 40
    draw.rounded_rectangle((x + 34, y + h - 72, x + CARD_W - 34, y + h - 30), radius=10, fill="#E8F1F3")
    draw.text((x + 52, y + h - 62), "AI 负责选择技能、补齐配置、执行流程和给出可追溯证据。", font=F_SMALL, fill="#526676")
    return y + h


def main() -> None:
    steps = [
        {
            "step": "01",
            "title": "资料进入知识库",
            "body": "用户给出 PDF、Word、网页、图片、长书或论文文件夹。AI 先判断文件类型、规模、是否需要 OCR、是否要增量加入已有知识库。",
            "outputs": ["待处理资料清单", "知识库项目目录"],
            "accent": "#28A1A7",
            "tags": ["入口", "文件夹", "增量"],
        },
        {
            "step": "02",
            "title": "MinerU / MarkItDown 文档解析",
            "body": "PDF、扫描件、表格和公式优先交给 MinerU；干净的非 PDF 文档用 MarkItDown 轻量转换。失败、空输出或乱码时记录并兜底。",
            "outputs": ["wiki/raw/*.md", "_conversion_failures.md"],
            "accent": "#D77B4D",
            "tags": ["OCR", "Markdown", "表格公式"],
        },
        {
            "step": "03",
            "title": "deep-reading-to-wiki 深读档案",
            "body": "长书、理论文献、核心章节先被读成 reading_dossiers，保留论证脉络、关键概念和可引用证据，避免浅层总结直接入图谱。",
            "outputs": ["reading_dossiers/*.md", "证据密集摘要"],
            "accent": "#5C8CE6",
            "tags": ["深读", "理论", "证据"],
        },
        {
            "step": "04",
            "title": "karpathy-wiki 图谱编译",
            "body": "把 raw 原文和深读档案编译为图谱可读页面：论证命题、概念、实体、对比和阶段性综述，供 Obsidian 直接浏览。",
            "outputs": ["claims/", "concepts/", "entities/", "comparisons/", "synthesis/"],
            "accent": "#61A36F",
            "tags": ["Obsidian", "Wiki", "Graph"],
        },
        {
            "step": "05",
            "title": "SiliconFlow-rag 双索引检索",
            "body": "建立 raw 原文索引和 wiki 结构索引。默认用 SiliconFlow 的 BAAI/bge-m3 嵌入模型，查询时先定位图谱，再回到原文证据。",
            "outputs": ["检索索引/raw", "检索索引/wiki", "可选 rerank"],
            "accent": "#B56FE8",
            "tags": ["BAAI/bge-m3", "wiki-first", "RAG"],
        },
        {
            "step": "06",
            "title": "social-science-km 总调度",
            "body": "作为一站式入口，负责建库、补库、体检、问答和综述。用户只说目标，AI 调用前面技能完成整条流程。",
            "outputs": ["可追溯问答", "增量补库", "文献综述"],
            "accent": "#E0A93E",
            "tags": ["总入口", "问答", "综述"],
        },
    ]

    scratch = Image.new("RGBA", (W, 5000), (0, 0, 0, 0))
    draw = ImageDraw.Draw(scratch)
    y = draw_header(scratch, draw)
    for idx, item in enumerate(steps):
        y = draw_card(scratch, draw, y, **item)
        if idx != len(steps) - 1:
            draw_arrow(draw, W // 2, y + 16, "#7FBCC1")
            y += 96
        else:
            y += 48
    y = draw_config_card(scratch, draw, y)
    y += 52
    y = draw_footer(scratch, draw, y)
    y += BOTTOM

    img = gradient_background(W, y)
    img.alpha_composite(scratch.crop((0, 0, W, y)))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(OUT, quality=96)
    print(OUT)
    print(f"{W}x{y}")


if __name__ == "__main__":
    main()
