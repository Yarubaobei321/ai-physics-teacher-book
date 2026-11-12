#!/usr/bin/env python3
"""将全书 27 篇现役 Markdown 按自然阅读单元拆分，供逐段审阅与人工级精修润色使用。"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path("/Users/yaril/个人文档/3 写作/图书出版/00_这本书的全部进展")
OUT_DIR = Path(__file__).resolve().parent
UNITS_DIR = OUT_DIR / "units"

sys.path.insert(0, str(ROOT / "编务/新增两章与重新编号-20261018"))
from 构建阅读版 import get_files  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def split_raw_blocks(text: str) -> list[str]:
    blocks, cur, fence, details = [], [], False, 0
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("```"):
            fence = not fence
        if not fence:
            if s.startswith("<details"):
                details += 1
            if not s and details == 0:
                if cur:
                    blocks.append("\n".join(cur))
                    cur = []
                continue
        cur.append(line)
        if not fence and details > 0 and s.startswith("</details>"):
            details -= 1
            if details == 0:
                blocks.append("\n".join(cur))
                cur = []
    if cur:
        blocks.append("\n".join(cur))
    return [b for b in blocks if b.strip() != "---"]


def group_editorial_units(raw_blocks: list[str], doc_id: str) -> list[str]:
    out = []
    i = 0
    n = len(raw_blocks)
    while i < n:
        b = raw_blocks[i]
        s = b.strip()
        # 附录 A 的每个 ### 提示词条目合并为一个完整审阅单元
        if doc_id == "appendix-a" and s.startswith("### "):
            combined = [b]
            i += 1
            while i < n and not raw_blocks[i].strip().startswith(("# ", "## ", "### ")):
                combined.append(raw_blocks[i])
                i += 1
            out.append("\n\n".join(combined))
            continue
        # 单行标题作为小节锚点单元
        if "\n" not in s and s.startswith("#"):
            out.append(b)
            i += 1
            continue
        # 提示词标签 + 引用块合并为一个完整提示词单元
        if s in ("**提示词（为本书整理）**", "**提示词**") and i + 1 < n and raw_blocks[i + 1].lstrip().startswith(">"):
            out.append(b + "\n\n" + raw_blocks[i + 1])
            i += 2
            continue
        # 以冒号结尾的引导段 + 紧随的列表/公式/代码块（不含大型独立表格，表格单独成块更清晰）
        if (s.endswith("：") or s.endswith(":")) and not s.startswith(("![", "|", "```", ">")) and i + 1 < n:
            nxt = raw_blocks[i + 1].lstrip()
            if nxt.startswith(("- ", "* ", "1. ", "2. ", "$$", ">")):
                combined = b + "\n\n" + raw_blocks[i + 1]
                i += 2
                if nxt.startswith("$$") and i < n and raw_blocks[i].lstrip().startswith(("其中", "式中", "这里")):
                    combined += "\n\n" + raw_blocks[i]
                    i += 1
                out.append(combined)
                continue
        # 段落后紧跟行间公式 $$
        if i + 1 < n and raw_blocks[i + 1].lstrip().startswith("$$") and not s.startswith(("![", "|", "```")):
            combined = b + "\n\n" + raw_blocks[i + 1]
            i += 2
            if i < n and raw_blocks[i].lstrip().startswith(("其中", "式中", "这里")):
                combined += "\n\n" + raw_blocks[i]
                i += 1
            out.append(combined)
            continue
        out.append(b)
        i += 1
    return out


def classify_unit(md: str) -> str:
    s = md.strip()
    if "\n" not in s and s.startswith("#"):
        return "heading"
    if s.startswith("![") and "\n" not in s:
        return "figure"
    if s.startswith("|") and "\n|" in s:
        return "table"
    if s.startswith("```") and s.endswith("```"):
        return "code"
    if "**提示词" in s and "\n>" in s:
        return "prompt"
    if s.startswith("> **本章在框架中的位置**"):
        return "framework"
    return "paragraph"


def main() -> None:
    UNITS_DIR.mkdir(parents=True, exist_ok=True)
    files, _ = get_files(ROOT, None)
    manifest = []
    for doc_id, path in files:
        text = path.read_text(encoding="utf-8")
        raw = split_raw_blocks(text)
        units_md = group_editorial_units(raw, doc_id)
        doc_title = ""
        cur_h2 = ""
        cur_h3 = ""
        units = []
        for idx, u_md in enumerate(units_md):
            s = u_md.strip()
            kind = classify_unit(u_md)
            if kind == "heading":
                if s.startswith("# "):
                    doc_title = s[2:].strip()
                elif s.startswith("## "):
                    cur_h2 = s[3:].strip()
                    cur_h3 = ""
                elif s.startswith("### "):
                    cur_h3 = s[4:].strip()
            sec_label = " / ".join(x for x in (cur_h2, cur_h3) if x) or doc_title
            units.append({
                "unit_id": f"{doc_id}-u{idx:03d}",
                "index": idx,
                "kind": kind,
                "section": sec_label,
                "orig_md": u_md,
            })
        rel_path = str(path.relative_to(ROOT))
        doc_info = {
            "doc_id": doc_id,
            "title": doc_title,
            "rel_path": rel_path,
            "sha256": sha256(path),
            "unit_count": len(units),
            "content_unit_count": sum(1 for u in units if u["kind"] != "heading"),
        }
        manifest.append(doc_info)
        (UNITS_DIR / f"{doc_id}.json").write_text(
            json.dumps({"doc": doc_info, "units": units}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Prepared {len(manifest)} docs, total units: {sum(x['unit_count'] for x in manifest)}")


if __name__ == "__main__":
    main()
