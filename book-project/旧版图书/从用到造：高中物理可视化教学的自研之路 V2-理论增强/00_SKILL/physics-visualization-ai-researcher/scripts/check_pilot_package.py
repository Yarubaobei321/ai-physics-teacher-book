#!/usr/bin/env python3
"""检查章节试点包的文件、字段、篇幅和高风险措辞。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


EXPECTED = {
    "章节诊断.md",
    "理论插入卡.md",
    "引用核验表.md",
    "重复与边界检查.md",
    "作者裁决卡.md",
    "示范扩写稿.md",
}

PACKAGE_TERMS = ["插入", "边界", "作者", "V1"]
HIGH_RISK = re.compile(r"(?:显著|普遍|必然)(?:提升|提高|促进|形成)|AI(?:自动|独立)保证正确")
NEGATION = re.compile(r"(?:不|未|无证据|禁止|避免|不可|不得|不能|不支持|不等于|不声称)")
BOUNDARY_CONTEXT = re.compile(
    r"(?:不能支持|不可支持|禁止措辞|禁用|越界|边界|不写|不得写|"
    r"\|\s*(?:渐隐|动画|资源|作品|提交|访问|AI).*?(?:必然|普遍|显著))"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pilot_dir", type=Path)
    parser.add_argument("--min-demo-chinese", type=int, default=3500)
    args = parser.parse_args()
    issues = []
    files = {p.name for p in args.pilot_dir.glob("*.md")}
    missing = sorted(EXPECTED - files)
    if missing:
        issues.append(f"缺少文件：{', '.join(missing)}")
    combined = ""
    demo_chinese = 0
    for name in EXPECTED & files:
        text = (args.pilot_dir / name).read_text(encoding="utf-8")
        combined += text + "\n"
        if name == "示范扩写稿.md":
            demo_chinese = len(re.findall(r"[\u3400-\u9fff]", text))
    for term in PACKAGE_TERMS:
        if term not in combined:
            issues.append(f"试点包缺少必要要素：{term}")
    if demo_chinese < args.min_demo_chinese:
        issues.append(f"示范扩写稿中文字符 {demo_chinese} 低于 {args.min_demo_chinese}")
    risky_lines = [
        line.strip()
        for line in combined.splitlines()
        if HIGH_RISK.search(line)
        and not NEGATION.search(line)
        and not BOUNDARY_CONTEXT.search(line)
    ]
    if risky_lines:
        issues.append("发现无条件高风险效果措辞")
    payload = {
        "directory": str(args.pilot_dir),
        "files": sorted(files),
        "missing": missing,
        "demo_chinese": demo_chinese,
        "high_risk_claim": bool(risky_lines),
        "high_risk_lines": risky_lines,
        "issues": issues,
        "ready": not issues,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
