#!/usr/bin/env python3
"""验证《从用到造》正文、资产、台账、审阅页和PDF。"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "02_MANUSCRIPT"
SOURCE = ROOT / "01_SOURCE"
OUTPUT = ROOT / "output"
REVIEW = ROOT / "review"
REPORT = ROOT / "03_REVIEW" / "全书" / "最终验证记录.json"
PDF = OUTPUT / "从用到造：高中物理可视化教学的自研之路.pdf"
EXPECTED_IMAGE_REFERENCES = 150

IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
FIGURE_RE = re.compile(r"图(\d+)-(\d+)")
CAPTION_RE = re.compile(r"^\*\*图(\d+)-(\d+)[　 ]", re.MULTILINE)
CHAPTER_RE = re.compile(r"第(\d+)章")


class RefParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.refs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        for key in ("href", "src"):
            value = values.get(key)
            if value:
                self.refs.append(value)


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def chapter_files() -> list[Path]:
    files = []
    for path in MANUSCRIPT.glob("第*章*.md"):
        match = CHAPTER_RE.search(path.name)
        if match:
            files.append((int(match.group(1)), path))
    return [item[1] for item in sorted(files)]


def validate_markdown(result: dict) -> None:
    files = chapter_files()
    missing_images = []
    absolute_images = []
    caption_errors = []
    reference_errors = []
    image_count = 0

    for expected_chapter, path in enumerate(files, start=1):
        content = path.read_text(encoding="utf-8")
        images = IMAGE_RE.findall(content)
        image_count += len(images)
        for rel in images:
            if rel.startswith("/"):
                absolute_images.append({"file": str(path), "path": rel})
            if not (MANUSCRIPT / rel).is_file():
                missing_images.append({"file": str(path), "path": rel})

        captions = [
            int(number)
            for chapter, number in CAPTION_RE.findall(content)
            if int(chapter) == expected_chapter
        ]
        expected = list(range(1, len(images) + 1))
        if captions != expected:
            caption_errors.append(
                {"chapter": expected_chapter, "expected": expected, "actual": captions}
            )

        available = {(expected_chapter, number) for number in expected}
        for chapter, number in FIGURE_RE.findall(content):
            pair = (int(chapter), int(number))
            if pair[0] == expected_chapter and pair not in available:
                reference_errors.append(
                    {"file": str(path), "reference": f"图{pair[0]}-{pair[1]}"}
                )

    result["markdown"] = {
        "chapter_count": len(files),
        "image_references": image_count,
        "missing_images": missing_images,
        "absolute_images": absolute_images,
        "caption_errors": caption_errors,
        "reference_errors": reference_errors,
    }


def validate_svgs(result: dict) -> None:
    svgs = sorted((MANUSCRIPT / "assets").rglob("*.svg"))
    errors = []
    for path in svgs:
        try:
            ElementTree.parse(path)
        except Exception as error:
            errors.append({"file": str(path), "error": str(error)})
    result["svg"] = {"count": len(svgs), "parse_errors": errors}


def validate_formula_source(result: dict) -> None:
    """检查Pandoc数学定界符是否成对，避免公式在导出时被拆碎。"""
    files = chapter_files()
    totals = {
        "inline_open": 0,
        "inline_close": 0,
        "display_open": 0,
        "display_close": 0,
        "single_dollar_delimiters": 0,
        "double_dollar_delimiters": 0,
    }
    errors = []
    for path in files:
        content = path.read_text(encoding="utf-8")
        control_characters = [
            {"offset": match.start(), "codepoint": ord(match.group(0))}
            for match in re.finditer(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", content)
        ]
        counts = {
            "inline_open": content.count(r"\("),
            "inline_close": content.count(r"\)"),
            "display_open": content.count(r"\["),
            "display_close": content.count(r"\]"),
            "single_dollar_delimiters": len(
                re.findall(r"(?<![\\$])\$(?!\$)", content)
            ),
            "double_dollar_delimiters": content.count("$$"),
        }
        for key, value in counts.items():
            totals[key] += value
        if counts["inline_open"] != counts["inline_close"]:
            errors.append({"file": str(path), "type": "inline_delimiter", "counts": counts})
        if counts["display_open"] != counts["display_close"]:
            errors.append({"file": str(path), "type": "display_delimiter", "counts": counts})
        if counts["double_dollar_delimiters"] % 2:
            errors.append({"file": str(path), "type": "double_dollar", "counts": counts})
        if counts["single_dollar_delimiters"] % 2:
            errors.append({"file": str(path), "type": "single_dollar", "counts": counts})
        if any(counts[key] for key in ("inline_open", "inline_close", "display_open", "display_close")):
            errors.append({"file": str(path), "type": "unsupported_tex_delimiter", "counts": counts})
        if control_characters:
            errors.append(
                {"file": str(path), "type": "control_character", "items": control_characters}
            )
    result["formula_source"] = {"totals": totals, "errors": errors}


def validate_html(result: dict) -> None:
    files = sorted(REVIEW.rglob("*.html"))
    missing = []
    checked = 0
    for path in files:
        parser = RefParser()
        parser.feed(path.read_text(encoding="utf-8"))
        for raw in parser.refs:
            parts = urlsplit(raw)
            if parts.scheme in {"http", "https", "mailto", "data", "javascript"}:
                continue
            if not parts.path or parts.path.startswith("#"):
                continue
            target = (path.parent / unquote(parts.path)).resolve()
            checked += 1
            if not target.exists():
                missing.append({"html": str(path), "reference": raw, "target": str(target)})
    result["html"] = {
        "file_count": len(files),
        "local_references_checked": checked,
        "missing_local_references": missing,
    }


def validate_registry(result: dict) -> None:
    path = SOURCE / "资料转写台账.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    missing = []
    for row in rows:
        if row.get("status") == "已过期":
            continue
        for field in ("text_record", "image_index", "material_card"):
            value = (row.get(field) or "").strip()
            if value and not (ROOT / value).exists():
                missing.append(
                    {"resource_id": row.get("resource_id"), "field": field, "path": value}
                )
    statuses: dict[str, int] = {}
    for row in rows:
        status = row.get("status", "")
        statuses[status] = statuses.get(status, 0) + 1
    result["registry"] = {
        "record_count": len(rows),
        "statuses": statuses,
        "missing_outputs": missing,
    }


def validate_pdf(result: dict) -> None:
    info = run(["pdfinfo", str(PDF)])
    images = run(["pdfimages", "-list", str(PDF)])
    text_path = Path("/tmp/from-use-to-create-validation.txt")
    text_run = run(["pdftotext", str(PDF), str(text_path)])
    text = text_path.read_text(encoding="utf-8", errors="replace") if text_path.exists() else ""
    pages = re.search(r"^Pages:\s+(\d+)", info.stdout, re.MULTILINE)
    page_size = re.search(r"^Page size:\s+(.+)$", info.stdout, re.MULTILINE)
    image_rows = [
        line
        for line in images.stdout.splitlines()
        if re.match(r"^\s*\d+\s+\d+\s+image\s+", line)
    ]
    result["pdf"] = {
        "exists": PDF.is_file(),
        "pdfinfo_exit": info.returncode,
        "pages": int(pages.group(1)) if pages else None,
        "page_size": page_size.group(1) if page_size else None,
        "embedded_images": len(image_rows),
        "pdftotext_exit": text_run.returncode,
        "extracted_characters": len(text),
        "contains_first_chapter": "从知识传授到思维培养" in text,
        "contains_last_chapter": "教师自研工具的可持续之路" in text,
        "contains_chinese_toc": "目录" in text[:500],
    }


def collect_errors(result: dict) -> list[str]:
    errors = []
    md = result["markdown"]
    if md["chapter_count"] != 12:
        errors.append("章节数不是12")
    if md["image_references"] != EXPECTED_IMAGE_REFERENCES:
        errors.append(f"正文图片引用数不是{EXPECTED_IMAGE_REFERENCES}")
    for key in ("missing_images", "absolute_images", "caption_errors", "reference_errors"):
        if md[key]:
            errors.append(f"Markdown检查失败：{key}")
    if result["svg"]["parse_errors"]:
        errors.append("SVG解析失败")
    if result["formula_source"]["errors"]:
        errors.append("公式源定界符不成对")
    if result["html"]["missing_local_references"]:
        errors.append("HTML存在失效本地链接")
    if result["registry"]["record_count"] != 72:
        errors.append("资料台账记录数不是72")
    if result["registry"]["missing_outputs"]:
        errors.append("资料台账产物缺失")
    pdf = result["pdf"]
    if not pdf["exists"] or pdf["pdfinfo_exit"] != 0 or pdf["pdftotext_exit"] != 0:
        errors.append("PDF工具检查失败")
    if not pdf["pages"] or pdf["pages"] < 100:
        errors.append("PDF页数异常")
    if pdf["embedded_images"] != md["image_references"]:
        errors.append("PDF图片对象数与正文图片引用数不符")
    if not pdf["page_size"] or "A4" not in pdf["page_size"]:
        errors.append("PDF页面不是A4")
    if not all(
        [pdf["contains_first_chapter"], pdf["contains_last_chapter"], pdf["contains_chinese_toc"]]
    ):
        errors.append("PDF首尾章节或中文目录缺失")
    return errors


def main() -> int:
    result: dict = {"book": "从用到造：高中物理可视化教学的自研之路"}
    validate_markdown(result)
    validate_svgs(result)
    validate_formula_source(result)
    validate_html(result)
    validate_registry(result)
    validate_pdf(result)
    result["errors"] = collect_errors(result)
    result["status"] = "通过" if not result["errors"] else "失败"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if result["errors"]:
        print(json.dumps(result["errors"], ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    print(
        f"OK: 12章 / {result['markdown']['image_references']}图 / "
        f"{result['svg']['count']}个SVG / "
        f"{result['html']['file_count']}个HTML / "
        f"{result['registry']['record_count']}条资料记录 / "
        f"PDF {result['pdf']['pages']}页"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
