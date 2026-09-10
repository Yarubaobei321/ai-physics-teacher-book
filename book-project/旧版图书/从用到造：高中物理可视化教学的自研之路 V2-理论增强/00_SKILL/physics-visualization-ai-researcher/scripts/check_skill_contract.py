#!/usr/bin/env python3
"""检查 Skill 是否满足本项目的主题、模型、边界和输出契约。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REQUIRED = {
    "theme_visualization": r"高中物理可视化",
    "theme_ai": r"AI\s*协作自研|AI\s*自研",
    "theme_use_create": r"从用到造|用—改—造",
    "model_a": r"可追溯共同工作对象闭环",
    "model_b": r"四层正交架构",
    "model_c": r"最低足够的“用—改—造”责任梯度",
    "model_d": r"独立真值—可失败验真",
    "model_e": r"主张权限\s*×\s*本地可复核强度双轴",
    "model_f": r"门控式资源生命周期",
    "read_only": r"不覆盖原章|只读对象",
    "reference_boundary": r"不得复制.*案例|不得复制.*表格|不得.*模仿参考书",
    "evidence_labels": r"R：原始研究.*F：正式框架.*E：官方工程.*L：本地材料.*B：参考书导航.*S：本书综合",
    "claim_boundary": r"C0—C6.*E1—E3",
    "failure_route": r"只交付已核验部分|停止生成确定性引文",
}

FORBIDDEN = {
    "template_todo": r"\[TODO|TODO:",
    "learning_science_main": r"学习科学(?:是|作为|为)(?:本书|全书|默认)?主(?:线|轴)",
    "ai_release": r"AI拥有发布权|AI可以直接发布",
    "parallel_framework": r"作为主理论框架|第12章 B12:13—133 新总框架|本书原创的六角色—八道门模型",
}

CROSS_FILE_TARGETS = [
    Path("references/research/05-from-use-to-create.md"),
    Path("references/research/06-chapter-expansion-map.md"),
    Path("references/synthesis/theory-insertion-card-template.md"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_file", type=Path)
    args = parser.parse_args()
    text = args.skill_file.read_text(encoding="utf-8")
    lines = text.count("\n") + 1
    required = {
        name: bool(re.search(pattern, text, re.S)) for name, pattern in REQUIRED.items()
    }
    forbidden = {
        name: bool(re.search(pattern, text, re.S)) for name, pattern in FORBIDDEN.items()
    }
    skill_root = args.skill_file.parent
    cross_file_text = "\n".join(
        (skill_root / relative).read_text(encoding="utf-8")
        for relative in CROSS_FILE_TARGETS
        if (skill_root / relative).exists()
    )
    forbidden["parallel_framework_cross_files"] = bool(
        re.search(FORBIDDEN["parallel_framework"], cross_file_text, re.S)
    )
    issues = []
    if lines > 500:
        issues.append(f"SKILL.md 为 {lines} 行，超过500行")
    issues.extend(f"缺少契约：{name}" for name, passed in required.items() if not passed)
    issues.extend(f"发现禁止表述：{name}" for name, found in forbidden.items() if found)
    payload = {
        "lines": lines,
        "required": required,
        "forbidden": forbidden,
        "issues": issues,
        "ready": not issues,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
