#!/usr/bin/env python3
"""检查女娲 Phase 1 六维调研是否具备进入综合阶段的最小条件。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


EXPECTED = {
    "01-theory-landscape.md": ("theory-landscape", 4_000),
    "02-learning-mechanisms.md": ("learning-mechanisms", 4_000),
    "03-translation-dna.md": ("translation-dna", 4_000),
    "04-design-methods.md": ("design-methods", 4_000),
    "05-evidence-boundaries.md": ("evidence-boundaries", 4_000),
    "06-chapter-map-antipatterns.md": ("chapter-map-antipatterns", 4_000),
}

CHECKS = {
    "source_anchor": re.compile(
        r"(?:LIT-\d{4}|https?://|DOI|\.md(?::\d+|#|\)|`|\s)|PDF\s*p\.?\s*\d+)",
        re.IGNORECASE,
    ),
    "evidence_layer": re.compile(
        r"(?:原始文献|源理论|二手|实证|理论推演|推断|已核验|待核验|证据层级)"
    ),
    "boundary": re.compile(
        r"(?:边界|局限|失效|不适用|不能|不得|替代解释|只能支持)"
    ),
    "action_or_observable": re.compile(
        r"(?:教师动作|学生动作|设计变量|可观察|产物|证据|修订|操作|任务)"
    ),
}


def inspect_file(path: Path, minimum_chars: int) -> dict:
    if not path.exists():
        return {
            "file": path.name,
            "exists": False,
            "chars": 0,
            "minimum_chars": minimum_chars,
            "checks": {name: False for name in CHECKS},
            "ready": False,
            "issues": ["文件缺失"],
        }

    text = path.read_text(encoding="utf-8")
    checks = {name: bool(pattern.search(text)) for name, pattern in CHECKS.items()}
    issues = []
    if len(text) < minimum_chars:
        issues.append(f"字符数 {len(text)} 低于最小值 {minimum_chars}")
    for name, passed in checks.items():
        if not passed:
            issues.append(f"未找到必要要素：{name}")

    return {
        "file": path.name,
        "exists": True,
        "chars": len(text),
        "minimum_chars": minimum_chars,
        "checks": checks,
        "ready": not issues,
        "issues": issues,
    }


def render_markdown(results: list[dict], ready: bool) -> str:
    lines = [
        "# 女娲 Phase 1 调研覆盖检查",
        "",
        f"**结论：{'PASS，可进入综合' if ready else 'FAIL，尚不可进入综合'}**",
        "",
        "| 文件 | 字符数 | 来源锚点 | 证据分层 | 边界 | 动作/观察 | 结果 |",
        "|---|---:|---|---|---|---|---|",
    ]
    labels = {
        "source_anchor": "来源锚点",
        "evidence_layer": "证据分层",
        "boundary": "边界",
        "action_or_observable": "动作/观察",
    }
    for item in results:
        checks = item["checks"]
        lines.append(
            f"| {item['file']} | {item['chars']} | "
            f"{'PASS' if checks['source_anchor'] else 'FAIL'} | "
            f"{'PASS' if checks['evidence_layer'] else 'FAIL'} | "
            f"{'PASS' if checks['boundary'] else 'FAIL'} | "
            f"{'PASS' if checks['action_or_observable'] else 'FAIL'} | "
            f"{'PASS' if item['ready'] else 'FAIL'} |"
        )

    failures = [item for item in results if not item["ready"]]
    if failures:
        lines += ["", "## 待补项"]
        for item in failures:
            lines.append(f"\n### {item['file']}")
            for issue in item["issues"]:
                lines.append(f"- {issue}")
            missing = [labels[name] for name, passed in item["checks"].items() if not passed]
            if missing:
                lines.append(f"- 必要要素缺失：{' / '.join(missing)}")
    lines += [
        "",
        "## 检查边界",
        "",
        "本检查只验证结构完整性，不替代对来源真实性、理论理解和综合质量的人工审查。",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("research_dir", type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--md-output", type=Path)
    args = parser.parse_args()

    results = [
        inspect_file(args.research_dir / filename, minimum_chars)
        for filename, (_, minimum_chars) in EXPECTED.items()
    ]
    ready = all(item["ready"] for item in results)
    payload = {"ready_for_synthesis": ready, "results": results}

    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    if args.md_output:
        args.md_output.parent.mkdir(parents=True, exist_ok=True)
        args.md_output.write_text(render_markdown(results, ready), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
