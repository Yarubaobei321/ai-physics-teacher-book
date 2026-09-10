#!/usr/bin/env python3
"""检查 Markdown 中指向本机绝对路径的链接是否存在。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(<(/Users/[^>]+)>\)|\[[^\]]*\]\((/Users/[^)]+)\)")
LINE_SUFFIX = re.compile(r":\d+(?::\d+)?$")


def normalize(raw: str) -> Path:
    value = raw.strip()
    value = value.split("#", 1)[0]
    value = LINE_SUFFIX.sub("", value)
    return Path(value)


def inspect_file(markdown: Path) -> list[dict]:
    text = markdown.read_text(encoding="utf-8")
    results = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for match in MARKDOWN_LINK.finditer(line):
            raw = match.group(1) or match.group(2)
            path = normalize(raw)
            results.append(
                {
                    "source": str(markdown),
                    "line": line_no,
                    "target": str(path),
                    "exists": path.exists(),
                }
            )
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    markdown_files: list[Path] = []
    for path in args.paths:
        if path.is_dir():
            markdown_files.extend(sorted(path.rglob("*.md")))
        elif path.suffix.lower() == ".md":
            markdown_files.append(path)

    results = []
    for markdown in markdown_files:
        results.extend(inspect_file(markdown))

    missing = [item for item in results if not item["exists"]]
    payload = {
        "markdown_files": len(markdown_files),
        "local_links": len(results),
        "missing": missing,
        "ready": not missing,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
