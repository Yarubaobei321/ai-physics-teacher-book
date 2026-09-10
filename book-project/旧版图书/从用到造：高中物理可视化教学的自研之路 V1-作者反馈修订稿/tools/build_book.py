#!/usr/bin/env python3
"""重建《从用到造》合订稿、全书统计、正文图像索引和PDF。

逐章 Markdown 是唯一正文源。合订稿、索引和 PDF 均为可重复生成的产物，
避免逐章文件与全书文件分别修改后产生版本漂移。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "02_MANUSCRIPT"
ASSETS = MANUSCRIPT / "assets"
OUTPUT = ROOT / "output"
SOURCE = ROOT / "01_SOURCE"
BOOK_MD = MANUSCRIPT / "全书合订稿.md"
AUTHOR_REVIEW_MD = ROOT / "《从用到造》V1作者反馈修订稿-作者审阅.md"
STATS_JSON = OUTPUT / "全书统计.json"
FIGURE_CSV = SOURCE / "全书正文图像索引.csv"
PDF_PATH = OUTPUT / "从用到造：高中物理可视化教学的自研之路.pdf"
PDF_INPUT = OUTPUT / "全书排版输入.md"

TITLE = "从用到造：高中物理可视化教学的自研之路"
SUBTITLE = "教师自研工具与科学思维培养实践"
AUTHORS = "丁龙　黄灿斌　王硕　严力耕"

CHAPTERS = [
    "第1章 从知识传授到思维培养：当学生需要现场建模.md",
    "第2章 可视化与科学思维：从看见到建模、推理与论证.md",
    "第3章 创新实验与自制教具：让不可见变为可见.md",
    "第4章 计算机仿真与可视化：让模型可以操控、比较与检验.md",
    "第5章 图形化编程：让代码驱动真实世界.md",
    "第6章 数字化教学平台：让分散资源成为共同入口.md",
    "第7章 概念课：让定义背后的关系逐步显现.md",
    "第8章 规律课：让证据在预测与修正之间流动.md",
    "第9章 习题课：把复杂情境展开成可检查的推理.md",
    "第10章 为教学问题自制和改造教具.md",
    "第11章 科学思维培养的效果评价：证据能把结论带到哪里.md",
    "第12章 教师自研工具的可持续之路：把一次创造变成长期能力.md",
]

PARTS = {
    1: "第一篇　为什么：问题与方向",
    3: "第二篇　怎么造：教师自研可视化工具",
    7: "第三篇　怎么用：课堂教学实践",
    11: "第四篇　那又怎样：评价与持续发展",
}

IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
CAPTION_RE = re.compile(r"^\*\*图(\d+)-(\d+)[　 ](.+?)\*\*(.*)$")
H1_RE = re.compile(r"^# (.+)$", re.MULTILINE)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_dimensions(path: Path) -> tuple[int | None, int | None]:
    if path.suffix.lower() == ".svg":
        text = path.read_text(encoding="utf-8")
        viewbox = re.search(r'viewBox="[^\"]*?([\d.]+)\s+([\d.]+)"', text)
        if viewbox:
            return round(float(viewbox.group(1))), round(float(viewbox.group(2)))
        width = re.search(r'width="([\d.]+)', text)
        height = re.search(r'height="([\d.]+)', text)
        if width and height:
            return round(float(width.group(1))), round(float(height.group(1)))
        return None, None
    try:
        from PIL import Image

        with Image.open(path) as image:
            return image.width, image.height
    except Exception:
        sips = shutil.which("sips")
        if not sips:
            return None, None
        result = subprocess.run(
            [sips, "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        width = re.search(r"pixelWidth: (\d+)", result.stdout)
        height = re.search(r"pixelHeight: (\d+)", result.stdout)
        return (int(width.group(1)), int(height.group(1))) if width and height else (None, None)


def load_chapters() -> list[dict]:
    chapters: list[dict] = []
    missing = []
    for number, filename in enumerate(CHAPTERS, start=1):
        path = MANUSCRIPT / filename
        if not path.is_file():
            missing.append(str(path))
            continue
        content = path.read_text(encoding="utf-8").strip()
        h1 = H1_RE.search(content)
        if not h1:
            raise ValueError(f"缺少章标题：{path}")
        chapters.append(
            {
                "number": number,
                "filename": filename,
                "path": path,
                "title": h1.group(1),
                "content": content,
            }
        )
    if missing:
        raise FileNotFoundError("\n".join(missing))
    return chapters


def build_markdown(chapters: list[dict]) -> None:
    lines = [
        f"# {TITLE}",
        "",
        f"## {SUBTITLE}",
        "",
        f"**作者：** {AUTHORS}",
        "",
        "<!-- 本文件由十二章正文自动合并。逐章Markdown是正文源文件。 -->",
        "",
        "## 目录",
        "",
    ]
    for chapter in chapters:
        lines.append(f"- {chapter['title']}")
    lines.extend(["", "---", ""])

    for chapter in chapters:
        number = chapter["number"]
        if number in PARTS:
            lines.extend([f"# {PARTS[number]}", ""])
        lines.extend([chapter["content"], ""])

    book_text = "\n".join(lines).rstrip() + "\n"
    BOOK_MD.write_text(book_text, encoding="utf-8")

    review_header = """# 作者审阅说明

本文件是项目根目录下的完整Markdown审阅稿，由十二章正文自动合并生成；逐章正文仍以`02_MANUSCRIPT/第1章…md`至`第12章…md`为唯一正文源。

- 已落实既有作者审阅：第1、2、3、4章。
- 已落实本轮作者口述反馈：第5、6、8、9、10章。
- 第7、11、12章本轮没有新增作者口述修改，保留V1内容；全书数学定界符已经统一。
- 题源、版权、课堂记录或原始数据不足处保留`【待作者补充】`或`【待作者/出版社补充】`，没有推测补写。
- 本稿不覆盖原V1，也不包含“V2-理论增强”的第7、12章试点。

---

"""
    review_text = review_header + book_text.replace("](assets/", "](02_MANUSCRIPT/assets/")
    AUTHOR_REVIEW_MD.write_text(review_text, encoding="utf-8")


def build_indexes(chapters: list[dict]) -> dict:
    figure_rows = []
    stats = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "book": TITLE,
        "chapters": [],
        "summary": {},
        "validation": {},
    }
    all_images: list[Path] = []
    missing_images = []
    caption_problems = []

    for chapter in chapters:
        content = chapter["content"]
        image_matches = list(IMAGE_RE.finditer(content))
        captions = []
        for line in content.splitlines():
            match = CAPTION_RE.match(line)
            if match:
                captions.append(
                    {
                        "chapter": int(match.group(1)),
                        "number": int(match.group(2)),
                        "title": match.group(3).strip().rstrip("。"),
                        "note": match.group(4).strip(),
                    }
                )
        caption_map = {(item["chapter"], item["number"]): item for item in captions}
        expected = list(range(1, len(image_matches) + 1))
        actual = [item["number"] for item in captions if item["chapter"] == chapter["number"]]
        if actual != expected:
            caption_problems.append(
                {"chapter": chapter["number"], "expected": expected, "actual": actual}
            )

        for index, match in enumerate(image_matches, start=1):
            alt, rel = match.group(1), match.group(2).strip()
            asset = MANUSCRIPT / rel
            if not asset.is_file():
                missing_images.append(str(asset))
                width = height = None
                file_size = None
                checksum = None
            else:
                all_images.append(asset)
                width, height = image_dimensions(asset)
                file_size = asset.stat().st_size
                checksum = sha256(asset)
            caption = caption_map.get((chapter["number"], index), {})
            figure_rows.append(
                {
                    "图号": f"图{chapter['number']}-{index}",
                    "章节": f"第{chapter['number']}章",
                    "图题": caption.get("title") or alt,
                    "正文相对路径": rel,
                    "文件格式": asset.suffix.lower().lstrip("."),
                    "像素宽": width or "",
                    "像素高": height or "",
                    "文件字节": file_size or "",
                    "SHA256": checksum or "",
                    "状态": "可用" if asset.is_file() else "缺失",
                }
            )

        stats["chapters"].append(
            {
                "chapter": chapter["number"],
                "title": chapter["title"],
                "characters": len(content),
                "figures": len(image_matches),
                "h2": len(re.findall(r"^## ", content, re.MULTILINE)),
                "h3": len(re.findall(r"^### ", content, re.MULTILINE)),
                "file": chapter["filename"],
                "sha256": sha256(chapter["path"]),
            }
        )

    with FIGURE_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(figure_rows[0].keys()))
        writer.writeheader()
        writer.writerows(figure_rows)

    stats["summary"] = {
        "chapter_count": len(chapters),
        "characters": sum(item["characters"] for item in stats["chapters"]),
        "figure_references": len(figure_rows),
        "unique_figure_files": len(set(all_images)),
        "h2": sum(item["h2"] for item in stats["chapters"]),
        "h3": sum(item["h3"] for item in stats["chapters"]),
    }
    stats["validation"] = {
        "missing_images": missing_images,
        "caption_sequence_problems": caption_problems,
        "absolute_image_references": [
            row["正文相对路径"]
            for row in figure_rows
            if row["正文相对路径"].startswith("/")
        ],
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    STATS_JSON.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return stats


def make_pdf_input(chapters: list[dict]) -> Path:
    """生成带书目信息和篇章页的排版输入，不作为正文源文件。"""
    lines = [
        "---",
        f'title: "{TITLE}"',
        f'subtitle: "{SUBTITLE}"',
        "author:",
        '  - "丁龙"',
        '  - "黄灿斌"',
        '  - "王硕"',
        '  - "严力耕"',
        'date: ""',
        "---",
        "",
    ]
    for chapter in chapters:
        number = chapter["number"]
        if number in PARTS:
            lines.extend([f"# {PARTS[number]}", ""])
        lines.extend([chapter["content"], ""])
    PDF_INPUT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return PDF_INPUT


def export_pdf(chapters: list[dict]) -> None:
    pandoc = shutil.which("pandoc") or "/opt/homebrew/bin/pandoc"
    typst = shutil.which("typst") or "/opt/homebrew/bin/typst"
    if not Path(pandoc).is_file() or not Path(typst).is_file():
        raise FileNotFoundError("需要pandoc与typst才能导出PDF")
    pdf_input = make_pdf_input(chapters)
    command = [
        pandoc,
        str(pdf_input),
        "--from=gfm+tex_math_dollars+raw_attribute",
        f"--pdf-engine={typst}",
        "--pdf-engine-opt=--root=/",
        "--lua-filter=" + str(ROOT / "tools" / "pagebreak-before-h1.lua"),
        "-V",
        "mainfont=Songti SC",
        "-V",
        "mathfont=STIX Two Math",
        "-V",
        "papersize=a4",
        "-V",
        "fontsize=10.5pt",
        "-V",
        "linestretch=1.35",
        "-V",
        "page-numbering=1",
        "--resource-path=" + str(MANUSCRIPT),
        "-o",
        str(PDF_PATH),
    ]
    subprocess.run(command, cwd=MANUSCRIPT, check=True)


def validate(stats: dict, require_pdf: bool) -> list[str]:
    errors = []
    if stats["summary"]["chapter_count"] != 12:
        errors.append("章节数不是12")
    if stats["validation"]["missing_images"]:
        errors.append("存在缺失正文图片")
    if stats["validation"]["caption_sequence_problems"]:
        errors.append("存在图号不连续或图注格式问题")
    if stats["validation"]["absolute_image_references"]:
        errors.append("正文仍含绝对图片路径")
    if require_pdf and not PDF_PATH.is_file():
        errors.append("PDF未生成")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="重建全书合订稿、索引与PDF")
    parser.add_argument("--no-pdf", action="store_true", help="只建合订稿和索引")
    parser.add_argument("--check", action="store_true", help="只检查，不重建")
    args = parser.parse_args()

    chapters = load_chapters()
    if args.check:
        stats = build_indexes(chapters)
        errors = validate(stats, require_pdf=False)
    else:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        build_markdown(chapters)
        stats = build_indexes(chapters)
        errors = validate(stats, require_pdf=False)
        if not errors and not args.no_pdf:
            export_pdf(chapters)
        errors.extend(validate(stats, require_pdf=not args.no_pdf))

    if errors:
        for error in sorted(set(errors)):
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        f"OK: {stats['summary']['chapter_count']}章，"
        f"{stats['summary']['characters']}字符，"
        f"{stats['summary']['figure_references']}幅正文图"
    )
    if not args.no_pdf and not args.check:
        print(f"PDF: {PDF_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
