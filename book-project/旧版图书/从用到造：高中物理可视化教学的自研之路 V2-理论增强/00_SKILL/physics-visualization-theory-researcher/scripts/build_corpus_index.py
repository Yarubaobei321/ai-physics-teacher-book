#!/usr/bin/env python3
"""从本地物理教育文献卡片生成理论蒸馏候选索引。"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover - 给调用者明确环境提示
    raise SystemExit("需要 PyYAML；本工作区可用 /opt/anaconda3/bin/python3 运行。") from exc


ROLE_KEYWORDS = {
    "表征、认知与科学思维": ["可视化", "表征", "认知", "概念", "建模", "科学思维", "思维进阶"],
    "实验、测量与证据": ["实验", "探究", "测量", "误差", "传感", "DIS", "证据", "数据"],
    "仿真、交互与物理计算": ["仿真", "交互", "H5", "HTML5", "Arduino", "ESP32", "开源硬件", "图形化编程", "编程"],
    "AI与教师设计": ["人工智能", "生成式", "ChatGPT", "DeepSeek", "教师", "教案", "资源开发"],
    "评价与人机协作": ["评价", "评估", "量规", "效度", "协作", "合作", "提示", "prompt"],
    "项目学习与教师发展": ["项目式", "项目学习", "STEAM", "课程开发", "教师发展", "专业成长", "共同体"],
}

TOPIC_DEFAULT_ROLES = {
    "01_课程标准与核心素养": ["表征、认知与科学思维"],
    "02_科学思维与可视化": ["表征、认知与科学思维"],
    "03_实验测量与误差": ["实验、测量与证据"],
    "04_数字化实验与开源硬件": ["实验、测量与证据", "仿真、交互与物理计算"],
    "05_AI与物理教学": ["AI与教师设计"],
    "06_H5与交互资源": ["仿真、交互与物理计算"],
    "07_学习评价与人机协作": ["评价与人机协作"],
    "08_教师发展与项目学习": ["项目学习与教师发展"],
}


def parse_frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    _, raw, body = text.split("---", 2)
    return yaml.safe_load(raw) or {}, body


def is_preferred(meta: dict) -> bool:
    return bool(meta.get("favorite")) or (
        meta.get("source_priority") in {"A", "B"}
        and meta.get("evidence_grade") in {"A", "B"}
        and meta.get("relevance") == "高"
    )


def score(meta: dict) -> int:
    total = 0
    total += {"A": 4, "B": 3, "C": 1, "D": 0}.get(meta.get("source_priority"), 0)
    total += {"A": 4, "B": 3, "C": 1, "D": 0}.get(meta.get("evidence_grade"), 0)
    total += 2 if meta.get("relevance") == "高" else 0
    total += 2 if meta.get("citation_ready") else 0
    total += 2 if meta.get("review_status") == "已精读" else 0
    total += 3 if meta.get("favorite") else 0
    return total


def assign_roles(meta: dict) -> list[str]:
    roles = list(TOPIC_DEFAULT_ROLES.get(meta.get("primary_topic"), []))
    haystack = " ".join(
        str(value)
        for value in (
            meta.get("title", ""),
            meta.get("topics", ""),
            meta.get("research_methods", ""),
        )
    ).lower()
    for role, keywords in ROLE_KEYWORDS.items():
        if role not in roles and any(keyword.lower() in haystack for keyword in keywords):
            roles.append(role)
    return roles or ["待人工归类"]


def build_record(card: Path, root: Path) -> dict:
    meta, body = parse_frontmatter(card)
    return {
        "literature_id": meta.get("literature_id"),
        "title": meta.get("title"),
        "year": meta.get("year"),
        "source": meta.get("source"),
        "primary_topic": meta.get("primary_topic"),
        "source_priority": meta.get("source_priority"),
        "evidence_grade": meta.get("evidence_grade"),
        "relevance": meta.get("relevance"),
        "metadata_status": meta.get("metadata_status"),
        "citation_ready": bool(meta.get("citation_ready")),
        "review_status": meta.get("review_status"),
        "preferred": is_preferred(meta),
        "selection_score": score(meta),
        "roles": assign_roles(meta),
        "citation": meta.get("citation_gbt7714"),
        "card_path": str(card),
        "fulltext_md_path": str(root / meta["fulltext_md_path"]) if meta.get("fulltext_md_path") else None,
        "pdf_path": str(root / meta["pdf_path"]) if meta.get("pdf_path") else None,
    }


def render_markdown(records: list[dict], library_root: Path) -> str:
    preferred = [record for record in records if record["preferred"]]
    role_counts = Counter(role for record in records for role in record["roles"])
    lines = [
        "# 理论蒸馏语料索引",
        "",
        f"- 文献库：`{library_root}`",
        f"- 正式文献单元：{len(records)}",
        f"- 按现有口径优先使用：{len(preferred)}",
        "- 本文件只保存元数据和本地路径，不复制受版权保护的全文。",
        "",
        "## 角色覆盖",
        "",
        "| 理论角色 | 命中文献数 |",
        "|---|---:|",
    ]
    lines.extend(f"| {role} | {count} |" for role, count in sorted(role_counts.items()))
    lines.extend(["", "## 优先使用文献", "", "| ID | 题名 | 来源/证据 | 理论角色 | 卡片 |", "|---|---|---|---|---|"])
    for record in sorted(preferred, key=lambda item: (-item["selection_score"], item["literature_id"] or "")):
        roles = "；".join(record["roles"])
        lines.append(
            f"| {record['literature_id']} | {record['title']} | {record['source_priority']}/{record['evidence_grade']} | "
            f"{roles} | `{record['card_path']}` |"
        )
    lines.extend(["", "## 分角色全文候选", ""])
    for role in ROLE_KEYWORDS:
        candidates = sorted(
            (record for record in records if role in record["roles"] and record["citation_ready"]),
            key=lambda item: (-item["selection_score"], item["literature_id"] or ""),
        )[:8]
        lines.extend([f"### {role}", ""])
        lines.extend(
            f"- {record['literature_id']}｜{record['title']}｜来源/证据 {record['source_priority']}/{record['evidence_grade']}｜`{record['card_path']}`"
            for record in candidates
        )
        lines.append("")
    lines.extend([
        "",
        "## 使用边界",
        "",
        "- `preferred` 只表示优先进入全文核验队列，不表示结论强度足以支持因果主张。",
        "- 理论源头、课程标准和关键反方材料可由人工提升，即使未命中优先口径。",
        "- 正式写作前必须按卡片锚点回查全文或 PDF。",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("library_root", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path, required=True)
    parser.add_argument("--markdown", dest="markdown_path", type=Path, required=True)
    args = parser.parse_args()

    cards = sorted(args.library_root.rglob("*_文献卡片.md"))
    records = [build_record(card, args.library_root) for card in cards]
    args.json_path.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_path.parent.mkdir(parents=True, exist_ok=True)
    args.json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown_path.write_text(render_markdown(records, args.library_root), encoding="utf-8")
    print(json.dumps({"cards": len(records), "preferred": sum(item["preferred"] for item in records)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
