#!/usr/bin/env python3
"""检查女娲六维调研是否围绕可视化、AI 自研与教师创造完成。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


EXPECTED = {
    "01-visualization-theory-landscape.md": 4_000,
    "02-physics-visualization-taxonomy.md": 4_000,
    "03-ai-assisted-creation.md": 4_000,
    "04-verification-governance.md": 4_000,
    "05-from-use-to-create.md": 4_000,
    "06-chapter-expansion-map.md": 6_000,
}

CHECKS = {
    "source_anchor": re.compile(
        r"(?:https?://|DOI|\.md(?::\d+|#|\)|`|\s)|PDF\s*p\.?\s*\d+)",
        re.IGNORECASE,
    ),
    "theme_focus": re.compile(
        r"(?:科学可视化|信息可视化|数据可视化|交互可视化|物理可视化|"
        r"生成式\s*AI|智能体|AI\s*协作|教师自研|从用到造|物理计算)"
    ),
    "physics_or_technical_chain": re.compile(
        r"(?:实物|现象|传感器|测量|数据|模型|仿真|表征|交互|代码|网页|ESP32|Blockly)"
    ),
    "evidence_layer": re.compile(
        r"(?:原始文献|官方|实证|项目证据|理论推演|推断|已核验|待核验|证据等级|来源等级)"
    ),
    "boundary": re.compile(
        r"(?:边界|局限|失效|不适用|不能|不得|禁止外推|只能支持|风险|误用)"
    ),
    "action_or_observable": re.compile(
        r"(?:教师动作|设计动作|技术链|可观察|产物|验收|验证|修订|操作|任务|插入位置)"
    ),
}

DRIFT_PATTERN = re.compile(
    r"(?:以学习科学为主轴|学习科学是主线|从学习科学出发|通用学习科学综述)"
)


def inspect_file(path: Path, minimum_chars: int) -> dict:
    if not path.exists():
        return {
            "file": path.name,
            "exists": False,
            "chars": 0,
            "minimum_chars": minimum_chars,
            "checks": {name: False for name in CHECKS},
            "theme_drift": False,
            "ready": False,
            "issues": ["文件缺失"],
        }

    text = path.read_text(encoding="utf-8")
    checks = {name: bool(pattern.search(text)) for name, pattern in CHECKS.items()}
    theme_drift = bool(DRIFT_PATTERN.search(text))
    issues = []
    if len(text) < minimum_chars:
        issues.append(f"字符数 {len(text)} 低于最小值 {minimum_chars}")
    for name, passed in checks.items():
        if not passed:
            issues.append(f"未找到必要要素：{name}")
    if theme_drift:
        issues.append("出现把通用学习科学设为主轴的主题漂移表述")

    return {
        "file": path.name,
        "exists": True,
        "chars": len(text),
        "minimum_chars": minimum_chars,
        "checks": checks,
        "theme_drift": theme_drift,
        "ready": not issues,
        "issues": issues,
    }


def render_markdown(results: list[dict], ready: bool) -> str:
    lines = [
        "# 女娲 Phase 1 可视化与 AI 调研覆盖检查",
        "",
        f"**结论：{'PASS，可进入综合' if ready else 'FAIL，尚不可进入综合'}**",
        "",
        "| 文件 | 字符数 | 来源 | 主题 | 物理/技术链 | 证据 | 边界 | 动作 | 漂移 | 结果 |",
        "|---|---:|---|---|---|---|---|---|---|---|",
    ]
    for item in results:
        c = item["checks"]
        lines.append(
            f"| {item['file']} | {item['chars']} | "
            f"{'PASS' if c['source_anchor'] else 'FAIL'} | "
            f"{'PASS' if c['theme_focus'] else 'FAIL'} | "
            f"{'PASS' if c['physics_or_technical_chain'] else 'FAIL'} | "
            f"{'PASS' if c['evidence_layer'] else 'FAIL'} | "
            f"{'PASS' if c['boundary'] else 'FAIL'} | "
            f"{'PASS' if c['action_or_observable'] else 'FAIL'} | "
            f"{'FAIL' if item['theme_drift'] else 'PASS'} | "
            f"{'PASS' if item['ready'] else 'FAIL'} |"
        )

    failures = [item for item in results if not item["ready"]]
    if failures:
        lines += ["", "## 待补项"]
        for item in failures:
            lines.append(f"\n### {item['file']}")
            for issue in item["issues"]:
                lines.append(f"- {issue}")

    lines += [
        "",
        "## 检查边界",
        "",
        "本检查验证文件、主题和必要研究要素是否齐全；来源真实性、理论理解与综合质量仍须人工审阅。",
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
        for filename, minimum_chars in EXPECTED.items()
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
