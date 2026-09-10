#!/usr/bin/env python3
"""把三条 Markdown 连续书稿导出为统一版式的 DOCX 审阅稿。"""

from __future__ import annotations

import html
import re
import sys
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
TABLE_HELPERS = Path(
    "/Users/yaril/.codex/plugins/cache/openai-primary-runtime/"
    "documents/26.826.12353/skills/documents/scripts"
)
sys.path.insert(0, str(TABLE_HELPERS))
from table_geometry import apply_table_geometry, column_widths_from_weights  # noqa: E402


ROUTES = {
    "Fable": {
        "subtitle": "从器械、数据与退回中长出教师判断",
        "images": {
            "第5章　六个小组、三种装置、一个网页": (
                "diagram/图1-三种机械能装置的证据路径@2x.png",
                "图1　三种机械能装置的证据路径",
            ),
            "第12章　做完之后，你能主张什么": (
                "diagram/图2-器械铸造链与退回点@2x.png",
                "图2　器械铸造链与退回点",
            ),
        },
    },
    "GLM": {
        "subtitle": "从任务书到第一个页面，再到验收、发布与接手",
        "images": {
            "第3章　页面会动，物理是否跟得上": (
                "diagram/图3-弹簧物块模型-物理时间与显示时间@2x.png",
                "图3　弹簧—物块模型的物理时间与显示时间",
            ),
            "第5章　第一个页面只做一件事": (
                "diagram/图4-v1-v2-从实时排序故障到保序规则@2x.png",
                "图4　v₁／v₂从实时排序故障到保序规则",
            ),
        },
    },
    "Grok": {
        "subtitle": "同一对象的几种说法，怎样接受独立证据",
        "images": {
            "同一件事的几种说法": (
                "diagram/图1-同一对象的几种说法如何互相限制@2x.png",
                "图1　同一对象的几种说法如何互相限制",
            ),
            "第11章　运行、物理、课堂和发布各自说明了什么": (
                "diagram/图2-运行物理教学发布四道门@2x.png",
                "图2　运行、物理、教学、发布四道门",
            ),
        },
    },
}

BODY_FONT = "Arial Unicode MS"
HEADING_FONT = "Arial Unicode MS"
MATH_FONT = "STIX Two Math"
CODE_FONT = "Menlo"
BLUE = RGBColor(46, 116, 181)
DARK_BLUE = RGBColor(31, 77, 120)
INK = RGBColor(33, 37, 41)
MUTED = RGBColor(92, 101, 112)


def set_run_font(run, name: str, size: float | None = None, *, bold=None, italic=None, color=None):
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.rFonts
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
        rfonts.set(qn(f"w:{attr}"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = color


def set_style_font(style, name: str, size: float, color=INK, bold=None):
    style.font.name = name
    style.font.size = Pt(size)
    style.font.color.rgb = color
    if bold is not None:
        style.font.bold = bold
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.rFonts
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
        rfonts.set(qn(f"w:{attr}"), name)


def shade_paragraph(paragraph, fill: str, border_left: str | None = None):
    ppr = paragraph._p.get_or_add_pPr()
    shd = ppr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        ppr.append(shd)
    shd.set(qn("w:fill"), fill)
    if border_left:
        pbdr = ppr.find(qn("w:pBdr"))
        if pbdr is None:
            pbdr = OxmlElement("w:pBdr")
            ppr.append(pbdr)
        left = OxmlElement("w:left")
        left.set(qn("w:val"), "single")
        left.set(qn("w:sz"), "20")
        left.set(qn("w:space"), "8")
        left.set(qn("w:color"), border_left)
        pbdr.append(left)


def configure_styles(doc: Document):
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)
    section.different_first_page_header_footer = True

    normal = doc.styles["Normal"]
    set_style_font(normal, BODY_FONT, 11)
    pf = normal.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.space_before = Pt(0)
    pf.space_after = Pt(8)
    pf.line_spacing = 1.333
    pf.first_line_indent = Pt(22)
    pf.widow_control = True

    heading_tokens = {
        "Heading 1": (HEADING_FONT, 16, BLUE, 18, 10),
        "Heading 2": (HEADING_FONT, 14, BLUE, 14, 7),
        "Heading 3": (HEADING_FONT, 12, DARK_BLUE, 10, 5),
        "Heading 4": (HEADING_FONT, 11, DARK_BLUE, 8, 4),
    }
    for name, (font, size, color, before, after) in heading_tokens.items():
        style = doc.styles[name]
        set_style_font(style, font, size, color, bold=True)
        fmt = style.paragraph_format
        fmt.space_before = Pt(before)
        fmt.space_after = Pt(after)
        fmt.line_spacing = 1.15
        fmt.keep_with_next = True
        fmt.keep_together = True

    for list_name in ("List Bullet", "List Number"):
        style = doc.styles[list_name]
        set_style_font(style, BODY_FONT, 11)
        fmt = style.paragraph_format
        fmt.left_indent = Inches(0.5)
        fmt.first_line_indent = Inches(-0.25)
        fmt.space_after = Pt(4)
        fmt.line_spacing = 1.208
        fmt.widow_control = True

    if "Formula" not in doc.styles:
        style = doc.styles.add_style("Formula", WD_STYLE_TYPE.PARAGRAPH)
    else:
        style = doc.styles["Formula"]
    set_style_font(style, MATH_FONT, 10.5)
    fmt = style.paragraph_format
    fmt.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fmt.space_before = Pt(6)
    fmt.space_after = Pt(8)
    fmt.line_spacing = 1.1
    fmt.keep_together = True

    if "Code Block" not in doc.styles:
        style = doc.styles.add_style("Code Block", WD_STYLE_TYPE.PARAGRAPH)
    else:
        style = doc.styles["Code Block"]
    set_style_font(style, CODE_FONT, 9)
    fmt = style.paragraph_format
    fmt.left_indent = Inches(0.18)
    fmt.right_indent = Inches(0.18)
    fmt.space_before = Pt(4)
    fmt.space_after = Pt(8)
    fmt.line_spacing = 1.1
    fmt.first_line_indent = Pt(0)

    quote = doc.styles["Quote"]
    set_style_font(quote, BODY_FONT, 10.5, MUTED)
    fmt = quote.paragraph_format
    fmt.left_indent = Inches(0.28)
    fmt.right_indent = Inches(0.15)
    fmt.first_line_indent = Pt(0)
    fmt.space_before = Pt(5)
    fmt.space_after = Pt(8)
    fmt.line_spacing = 1.25


INLINE_PATTERN = re.compile(
    r"(\*\*.+?\*\*|\x60.+?\x60|\\\(.+?\\\)|\$.+?\$|\*[^*]+\*)"
)


def normalize_plain_text(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1（\2）", text)
    return text


def latex_readable(expr: str) -> str:
    """把常见书稿 LaTeX 转成不依赖公式引擎的可读文本。"""
    value = expr.strip()
    replacements = {
        "\\Delta": "Δ",
        "\\Phi": "Φ",
        "\\pi": "π",
        "\\mu": "μ",
        "\\omega": "ω",
        "\\approx": "≈",
        "\\sim": "∼",
        "\\pm": "±",
        "\\ge": "≥",
        "\\le": "≤",
        "\\times": "×",
        "\\cdot": "·",
        "\\cos": "cos",
        "\\sin": "sin",
        "\\max": "max",
        "\\left": "",
        "\\right": "",
        "\\qquad": "   ",
        "\\quad": "  ",
        "\\,": " ",
        "\\ ": " ",
    }
    # \\le 是 \\left 的前缀；先处理长命令，避免把 \\left 误转为“≤ft”。
    for old, new in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        value = value.replace(old, new)
    for _ in range(8):
        before = value
        value = re.sub(r"\\(?:t?frac)\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)", value)
        value = re.sub(r"\\(?:t?frac)([0-9])([0-9])", r"\1/\2", value)
        value = re.sub(r"\\sqrt\{([^{}]+)\}", r"√(\1)", value)
        value = re.sub(r"\\sqrt\s*([A-Za-z0-9]+)", r"√\1", value)
        value = re.sub(r"\\(?:mathrm|text|mathcal)\{([^{}]*)\}", r"\1", value)
        value = re.sub(r"\\(?:mathrm|text|mathcal)\s*([A-Za-z]+)", r"\1", value)
        if value == before:
            break
    value = value.replace("\\rm", "")
    superscripts = {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹"}
    subscripts = {"0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉"}
    value = re.sub(r"\^([0-9])", lambda m: superscripts[m.group(1)], value)
    value = re.sub(r"_([0-9])", lambda m: subscripts[m.group(1)], value)
    value = re.sub(r"\^\{([^{}]+)\}", r"^(\1)", value)
    value = re.sub(r"_\{([^{}]+)\}", r"_(\1)", value)
    value = value.replace("{", "").replace("}", "")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def add_inline(paragraph, text: str, *, default_size: float = 11, default_font: str = BODY_FONT):
    text = normalize_plain_text(text)
    pos = 0
    for match in INLINE_PATTERN.finditer(text):
        if match.start() > pos:
            run = paragraph.add_run(text[pos : match.start()])
            set_run_font(run, default_font, default_size, color=INK)
        token = match.group(0)
        if token.startswith("**"):
            run = paragraph.add_run(token[2:-2])
            set_run_font(run, default_font, default_size, bold=True, color=INK)
        elif token.startswith(chr(96)):
            run = paragraph.add_run(token[1:-1])
            set_run_font(run, CODE_FONT, default_size - 1, color=DARK_BLUE)
            shd = OxmlElement("w:shd")
            shd.set(qn("w:fill"), "EEF2F6")
            run._element.get_or_add_rPr().append(shd)
        elif token.startswith("\\("):
            run = paragraph.add_run(latex_readable(token[2:-2]))
            set_run_font(run, MATH_FONT, default_size, italic=True, color=INK)
        elif token.startswith("$"):
            run = paragraph.add_run(latex_readable(token[1:-1]))
            set_run_font(run, MATH_FONT, default_size, italic=True, color=INK)
        else:
            run = paragraph.add_run(token[1:-1])
            set_run_font(run, default_font, default_size, italic=True, color=INK)
        pos = match.end()
    if pos < len(text):
        run = paragraph.add_run(text[pos:])
        set_run_font(run, default_font, default_size, color=INK)


def add_page_field(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run()
    set_run_font(run, HEADING_FONT, 9, color=MUTED)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    run._r.append(fld)


def add_header_footer(doc: Document, route: str):
    section = doc.sections[0]
    header = section.header
    p = header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_after = Pt(0)
    run = p.add_run(f"{route}版｜连续正文审阅稿")
    set_run_font(run, HEADING_FONT, 8.5, color=MUTED)
    footer = section.footer
    p = footer.paragraphs[0]
    add_page_field(p)


def add_cover(doc: Document, route: str, subtitle: str):
    for _ in range(4):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(9)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(12)
    run = p.add_run("AI时代物理教师实践与技术手册")
    set_run_font(run, HEADING_FONT, 28, bold=True, color=DARK_BLUE)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    run = p.add_run(f"{route}版 · 连续正文审阅稿")
    set_run_font(run, HEADING_FONT, 17, bold=True, color=BLUE)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(40)
    run = p.add_run(subtitle)
    set_run_font(run, BODY_FONT, 12, color=MUTED)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(7)
    run = p.add_run("2026年8月31日｜供作者组连续阅读与批注")
    set_run_font(run, HEADING_FONT, 10, color=MUTED)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(0)
    run = p.add_run("事实边界、署名与图件授权以随稿审阅说明为准")
    set_run_font(run, BODY_FONT, 9.5, italic=True, color=MUTED)
    doc.add_page_break()


def split_table_row(line: str) -> list[str]:
    core = line.strip().strip("|")
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", core)]


def is_table_delimiter(line: str) -> bool:
    if not line.lstrip().startswith("|"):
        return False
    cells = split_table_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)


def text_weight(value: str) -> int:
    clean = re.sub(r"[*$\x60\\]", "", value)
    return max(6, sum(2 if ord(ch) > 127 else 1 for ch in clean))


def shade_cell(cell, fill: str):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = tcpr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tcpr.append(shd)
    shd.set(qn("w:fill"), fill)


def repeat_table_header(row):
    trpr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    trpr.append(tbl_header)


def add_markdown_table(doc: Document, rows: list[list[str]]):
    cols = max(len(row) for row in rows)
    normalized = [row + [""] * (cols - len(row)) for row in rows]
    table = doc.add_table(rows=len(normalized), cols=cols)
    table.style = "Table Grid"

    weights = []
    for idx in range(cols):
        peak = max(text_weight(row[idx]) for row in normalized)
        # 给含较长拉丁词的窄列留出最小宽度，避免 Agent 等词被按字母拆行。
        has_long_latin_word = any(
            re.search(r"[A-Za-z]{5,}", row[idx]) for row in normalized
        )
        minimum = 15 if has_long_latin_word else 10
        weights.append(min(max(peak, minimum), 46))
    widths = column_widths_from_weights(weights, 9360)

    for r_idx, row in enumerate(normalized):
        for c_idx, value in enumerate(row):
            cell = table.cell(r_idx, c_idx)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.alignment = (
                WD_ALIGN_PARAGRAPH.CENTER if text_weight(value) <= 16 else WD_ALIGN_PARAGRAPH.LEFT
            )
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.first_line_indent = Pt(0)
            add_inline(p, value, default_size=9, default_font=BODY_FONT)
            if r_idx == 0:
                shade_cell(cell, "E8EEF5")
                for run in p.runs:
                    run.bold = True
    repeat_table_header(table.rows[0])
    apply_table_geometry(
        table,
        widths,
        table_width_dxa=9360,
        indent_dxa=120,
        cell_margins_dxa={"top": 90, "bottom": 90, "start": 120, "end": 120},
    )
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)


def add_figure(doc: Document, image_path: Path, caption: str):
    if not image_path.exists():
        raise FileNotFoundError(image_path)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    run = p.add_run()
    shape = run.add_picture(str(image_path), width=Inches(6.25))
    shape._inline.docPr.set("descr", caption)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(10)
    p.paragraph_format.keep_with_next = False
    run = p.add_run(caption)
    set_run_font(run, BODY_FONT, 9.5, color=MUTED)


def add_heading(doc: Document, level: int, title: str, *, first_h1: bool):
    style_name = f"Heading {min(level, 4)}"
    p = doc.add_paragraph(style=style_name)
    p.paragraph_format.first_line_indent = Pt(0)
    if level == 1 and not first_h1:
        p.paragraph_format.page_break_before = True
    add_inline(
        p,
        title,
        default_size={1: 16, 2: 14, 3: 12, 4: 11}.get(level, 11),
        default_font=HEADING_FONT,
    )
    for run in p.runs:
        run.bold = True
        run.font.color.rgb = BLUE if level <= 2 else DARK_BLUE
    return p


def new_decimal_numbering(doc: Document) -> int:
    """新建一个从 1 开始的真实 Word 编号实例。"""
    numbering = doc.part.numbering_part.element
    abstract_ids = [
        int(node.get(qn("w:abstractNumId")))
        for node in numbering.findall(qn("w:abstractNum"))
    ]
    num_ids = [
        int(node.get(qn("w:numId")))
        for node in numbering.findall(qn("w:num"))
    ]
    abstract_id = max(abstract_ids, default=-1) + 1
    num_id = max(num_ids, default=0) + 1

    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), str(abstract_id))
    multi = OxmlElement("w:multiLevelType")
    multi.set(qn("w:val"), "singleLevel")
    abstract.append(multi)

    level = OxmlElement("w:lvl")
    level.set(qn("w:ilvl"), "0")
    start = OxmlElement("w:start")
    start.set(qn("w:val"), "1")
    level.append(start)
    num_fmt = OxmlElement("w:numFmt")
    num_fmt.set(qn("w:val"), "decimal")
    level.append(num_fmt)
    level_text = OxmlElement("w:lvlText")
    level_text.set(qn("w:val"), "%1.")
    level.append(level_text)
    level_jc = OxmlElement("w:lvlJc")
    level_jc.set(qn("w:val"), "left")
    level.append(level_jc)

    ppr = OxmlElement("w:pPr")
    tabs = OxmlElement("w:tabs")
    tab = OxmlElement("w:tab")
    tab.set(qn("w:val"), "num")
    tab.set(qn("w:pos"), "720")
    tabs.append(tab)
    ppr.append(tabs)
    indent = OxmlElement("w:ind")
    indent.set(qn("w:left"), "720")
    indent.set(qn("w:hanging"), "360")
    ppr.append(indent)
    level.append(ppr)
    abstract.append(level)

    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(num_id))
    abstract_ref = OxmlElement("w:abstractNumId")
    abstract_ref.set(qn("w:val"), str(abstract_id))
    num.append(abstract_ref)
    numbering.append(abstract)
    numbering.append(num)
    return num_id


def apply_numbering(paragraph, num_id: int):
    ppr = paragraph._p.get_or_add_pPr()
    numpr = ppr.find(qn("w:numPr"))
    if numpr is None:
        numpr = OxmlElement("w:numPr")
        ppr.insert(0, numpr)
    ilvl = OxmlElement("w:ilvl")
    ilvl.set(qn("w:val"), "0")
    numpr.append(ilvl)
    num_id_node = OxmlElement("w:numId")
    num_id_node.set(qn("w:val"), str(num_id))
    numpr.append(num_id_node)


def render_markdown(doc: Document, route_dir: Path, md_path: Path, image_map):
    lines = md_path.read_text(encoding="utf-8").splitlines()
    i = 0
    in_code = False
    code_lines: list[str] = []
    first_h1 = True
    current_numbering_id: int | None = None

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith(chr(96) * 3):
            if not in_code:
                in_code = True
                code_lines = []
            else:
                p = doc.add_paragraph(style="Code Block")
                p.paragraph_format.first_line_indent = Pt(0)
                shade_paragraph(p, "F2F4F7")
                run = p.add_run("\n".join(code_lines))
                set_run_font(run, CODE_FONT, 9, color=INK)
                in_code = False
            i += 1
            continue
        if in_code:
            code_lines.append(line)
            i += 1
            continue

        if stripped in ("\\[", "$$"):
            end_marker = "\\]" if stripped == "\\[" else "$$"
            formula_lines = []
            i += 1
            while i < len(lines) and lines[i].strip() != end_marker:
                formula_lines.append(lines[i].strip())
                i += 1
            p = doc.add_paragraph(style="Formula")
            p.paragraph_format.first_line_indent = Pt(0)
            run = p.add_run(latex_readable(" ".join(formula_lines)))
            set_run_font(run, MATH_FONT, 10.5, italic=True, color=INK)
            i += 1
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2).strip()
            add_heading(doc, level, title, first_h1=first_h1)
            if level == 1:
                first_h1 = False
            if title in image_map:
                rel, caption = image_map[title]
                add_figure(doc, route_dir / rel, caption)
            i += 1
            continue

        if (
            stripped.startswith("|")
            and i + 1 < len(lines)
            and is_table_delimiter(lines[i + 1])
        ):
            rows = [split_table_row(line)]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(split_table_row(lines[i]))
                i += 1
            add_markdown_table(doc, rows)
            continue

        if not stripped:
            i += 1
            continue

        if stripped == "---":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(3)
            i += 1
            continue

        if re.match(r"^\s*[-*+]\s+", line):
            content = re.sub(r"^\s*[-*+]\s+", "", line)
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.first_line_indent = Inches(-0.25)
            add_inline(p, content)
            i += 1
            continue

        numbered = re.match(r"^\s*(\d+)[.)]\s+(.+)$", line)
        if numbered:
            source_number = int(numbered.group(1))
            content = numbered.group(2)
            if source_number == 1 or current_numbering_id is None:
                current_numbering_id = new_decimal_numbering(doc)
            p = doc.add_paragraph(style="List Number")
            p.paragraph_format.first_line_indent = Inches(-0.25)
            apply_numbering(p, current_numbering_id)
            add_inline(p, content)
            i += 1
            continue

        if stripped.startswith(">"):
            content = re.sub(r"^>\s?", "", stripped)
            p = doc.add_paragraph(style="Quote")
            p.paragraph_format.first_line_indent = Pt(0)
            shade_paragraph(p, "F4F6F9", border_left="2E74B5")
            add_inline(p, content, default_size=10.5)
            i += 1
            continue

        p = doc.add_paragraph()
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        add_inline(p, stripped)
        i += 1


def enable_update_fields(doc: Document):
    settings = doc.settings.element
    update = settings.find(qn("w:updateFields"))
    if update is None:
        update = OxmlElement("w:updateFields")
        settings.append(update)
    update.set(qn("w:val"), "true")


def assert_no_courier(path: Path):
    hits = []
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if not name.endswith(".xml"):
                continue
            payload = zf.read(name).lower()
            if b"courier" in payload:
                hits.append(name)
    if hits:
        raise RuntimeError(f"Courier font residue in {path.name}: {hits}")


def scrub_courier(path: Path):
    """移除默认模板中未使用样式和字体表残留的 Courier 字样。"""
    replacement = path.with_suffix(".rewrite.docx")
    with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(
        replacement, "w", compression=zipfile.ZIP_DEFLATED
    ) as target:
        for item in source.infolist():
            payload = source.read(item.filename)
            if item.filename.endswith(".xml"):
                payload = payload.replace(b"Courier New", b"Menlo")
                payload = payload.replace(b"Courier", b"Menlo")
                payload = payload.replace(b"courier new", b"Menlo")
                payload = payload.replace(b"courier", b"Menlo")
            target.writestr(item, payload)
    replacement.replace(path)


def build_route(route: str, config: dict):
    route_dir = ROOT / route
    source = route_dir / "正文-第一批.md"
    output = Path(__file__).resolve().parent / f"{route}-连续正文审阅版.docx"
    doc = Document()
    configure_styles(doc)
    add_header_footer(doc, route)
    add_cover(doc, route, config["subtitle"])
    doc.core_properties.title = f"{route}版连续正文审阅稿"
    doc.core_properties.subject = "AI时代物理教师实践与技术手册三路线正文检验"
    doc.core_properties.author = "项目作者组"
    doc.core_properties.keywords = "高中物理, AI, 教师实践, 审阅稿"
    render_markdown(doc, route_dir, source, config["images"])
    enable_update_fields(doc)
    doc.save(output)
    scrub_courier(output)
    assert_no_courier(output)
    print(output)


def main():
    for route, config in ROUTES.items():
        build_route(route, config)


if __name__ == "__main__":
    main()
