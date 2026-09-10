#!/usr/bin/env python3
"""生成步步高正式资料库的可重建处理质量报告。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from library_common import (  # noqa: E402
    LIBRARY_ROOT,
    PipelineError,
    json_bytes,
    official_library_root,
    safe_library_root,
    write_json,
    write_text,
)
from quality_common import (  # noqa: E402
    PROFILE_ORDER,
    load_library_snapshot,
    source_processing_summary,
)


REPORT_JSON_PATH = "reports/quality-report.json"
REPORT_MARKDOWN_PATH = "reports/quality-report.md"
REPORT_VERSION = "1.2"


def build_quality_report(library_root: Path | str = LIBRARY_ROOT) -> dict[str, Any]:
    """从清单、记录和阶段日志生成统计对象，不写入资料库。"""
    snapshot = load_library_snapshot(library_root)
    source_summary = source_processing_summary(snapshot)
    phase_reports = {
        phase: dict(sorted(counts.items()))
        for phase, counts in snapshot["phase_status_counts"].items()
    }
    totals = source_summary["total"]
    return {
        "report_version": REPORT_VERSION,
        "scope": "physics-digital-library",
        "manifest": {
            "path": "sources/sources.jsonl",
            "sha256": snapshot["manifest_sha256"],
            "source_count": source_summary["total"]["expected"],
        },
        "overview": {
            "readable_sources": totals["successful"],
            "conversion_or_structure_failed_or_blocked": totals["failed"],
            "automatic_review_marked_sources": totals["automatic_review_marked"],
            "conservative_unsplit_blocks": totals["conservative_unsplit_blocks"],
            "conservative_unsplit_sources": totals["conservative_unsplit_sources"],
            "pending_manual_review_sources": totals["pending_manual_review"],
        },
        "source_processing": source_summary,
        "source_manifest_status": snapshot["source_manifest_status"],
        "records": snapshot["record_counts"],
        "question_review_signals": snapshot["record_counts"]["questions"].get(
            "review_signals", {}
        ),
        "phase_reports": phase_reports,
        "quality_rules": {
            "successful": "已有可读 Markdown/document 记录且没有失败或 blocked 标记；不代表人工复核或发布。",
            "failed": "存在转换/结构化失败阶段日志，或来源/document 已标记 blocked。",
            "automatic_review_marked": "来源存在至少一个自动核对标记；可与 successful、failed、pending_manual_review 重叠，不等于转换失败。",
            "conservative_unsplit_blocks": "证据不足时未猜测生成题目记录的编号条目数；原文仍保留在对应 Markdown，计数单位是区块，不是来源文档。",
            "pending_manual_review": "来源、document 或 question 已进入待人工复核流程；不代表已有 reviewer、reviewed 或 published。",
            "question_direct_reminder": "题目自身的答案、解析、公式、选项等 issue，或未从来源继承的单题 pending 状态；会强制进入题目复核队列。",
            "question_inherited_source_reminder": "只反映来源/document 的转换或结构化待审状态；来源 document 会优先复核，题目本身不因这一提示被逐题强制入队。",
            "unprocessed": "尚无可用 document 记录，且未发现失败阶段日志。",
            "source_state_mismatch": "来源清单状态与已读取的产物或阶段日志不一致；已计入自动核对标记，必须同步后再发布。",
        },
        "warnings": snapshot["warnings"],
    }


def _source_processing_rows(report: dict[str, Any]) -> list[str]:
    summary = report["source_processing"]
    rows = [
        "| 资料类型 | 应处理 | 已生成可读文档 | 转换/结构化失败或阻断 | 未处理 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    labels = {"teacher": "教师用书", "gaokao": "高考题", "textbook": "必修/选修资料"}
    for profile in PROFILE_ORDER:
        values = summary["by_profile"][profile]
        rows.append(
            "| {label} | {expected} | {successful} | {failed} | {unprocessed} |".format(
                label=labels[profile],
                expected=values["expected"],
                successful=values["successful"],
                failed=values["failed"],
                unprocessed=values["unprocessed"],
            )
        )
    total = summary["total"]
    rows.append(
        "| 合计 | {expected} | {successful} | {failed} | {unprocessed} |".format(
            expected=total["expected"],
            successful=total["successful"],
            failed=total["failed"],
            unprocessed=total["unprocessed"],
        )
    )
    return rows


def _automatic_review_rows(report: dict[str, Any]) -> list[str]:
    summary = report["source_processing"]
    rows = [
        "| 资料类型 | 需人工核对（自动标记，来源数） | 已进入待人工复核流程（来源数） | 保守未拆题来源数 | 保守未拆题区块数 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    labels = {"teacher": "教师用书", "gaokao": "高考题", "textbook": "必修/选修资料"}
    for profile in PROFILE_ORDER:
        values = summary["by_profile"][profile]
        rows.append(
            "| {label} | {marked} | {pending} | {unsplit_sources} | {unsplit_blocks} |".format(
                label=labels[profile],
                marked=values["automatic_review_marked"],
                pending=values["pending_manual_review"],
                unsplit_sources=values["conservative_unsplit_sources"],
                unsplit_blocks=values["conservative_unsplit_blocks"],
            )
        )
    total = summary["total"]
    rows.append(
        "| 合计 | {marked} | {pending} | {unsplit_sources} | {unsplit_blocks} |".format(
            marked=total["automatic_review_marked"],
            pending=total["pending_manual_review"],
            unsplit_sources=total["conservative_unsplit_sources"],
            unsplit_blocks=total["conservative_unsplit_blocks"],
        )
    )
    return rows


def _record_rows(report: dict[str, Any]) -> list[str]:
    rows = [
        "| 记录类型 | 已读取 | 待人工复核状态（含继承） | 直接提醒 | 仅继承来源级提醒 | 状态分布 |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    documents = report["records"]["documents"]
    document_pending = sum(
        item["pending_manual_review"] for item in documents["by_profile"].values()
    )
    document_issues = sum(item["with_issues"] for item in documents["by_profile"].values())
    document_statuses = "；".join(
        f"{key} {value}" for key, value in documents["by_status"].items()
    ) or "无"
    rows.append(
        f"| 文档 | {documents['total']} | {document_pending} | {document_issues} | — | {document_statuses} |"
    )

    questions = report["records"]["questions"]
    question_pending = sum(
        item["pending_manual_review"] for item in questions["by_profile"].values()
    )
    question_signals = report["question_review_signals"]
    question_statuses = "；".join(
        f"{key} {value}" for key, value in questions["by_status"].items()
    ) or "无"
    rows.append(
        "| 题目 | {total} | {pending} | {direct} | {inherited} | {statuses} |".format(
            total=questions["total"],
            pending=question_pending,
            direct=question_signals.get("direct_review_required", 0),
            inherited=question_signals.get("only_inherited_source_review_signal", 0),
            statuses=question_statuses,
        )
    )
    return rows


def _question_signal_rows(report: dict[str, Any]) -> list[str]:
    questions = report["records"]["questions"]
    rows = [
        "| 资料类型 | 题目数 | 有直接提醒（强制逐题复核） | 仅继承来源级提醒（不当作题目异常） |",
        "| --- | ---: | ---: | ---: |",
    ]
    labels = {"teacher": "教师用书", "gaokao": "高考题", "textbook": "必修/选修资料"}
    for profile in PROFILE_ORDER:
        values = questions["by_profile"][profile]
        rows.append(
            "| {label} | {total} | {direct} | {inherited} |".format(
                label=labels[profile],
                total=values["total"],
                direct=values.get("direct_review_required", 0),
                inherited=values.get("only_inherited_source_review_signal", 0),
            )
        )
    total = questions["review_signals"]
    rows.append(
        "| 合计 | {count} | {direct} | {inherited} |".format(
            count=questions["total"],
            direct=total.get("direct_review_required", 0),
            inherited=total.get("only_inherited_source_review_signal", 0),
        )
    )
    return rows


def _manifest_status_rows(report: dict[str, Any]) -> list[str]:
    rows = ["| 资料类型 | 清单状态分布 |", "| --- | --- |"]
    labels = {"teacher": "教师用书", "gaokao": "高考题", "textbook": "必修/选修资料"}
    statuses = report["source_manifest_status"]["by_profile"]
    for profile in PROFILE_ORDER:
        values = "；".join(f"{key} {count}" for key, count in statuses[profile].items()) or "无"
        rows.append(f"| {labels[profile]} | {values} |")
    return rows


def _review_rows(report: dict[str, Any]) -> list[str]:
    values = report["records"]["reviews"]
    statuses = "；".join(f"{key} {value}" for key, value in values["by_status"].items()) or "无"
    decisions = "；".join(f"{key} {value}" for key, value in values["by_decision"].items()) or "无"
    targets = "；".join(f"{key} {value}" for key, value in values["by_target_type"].items()) or "无"
    return [
        "| 已读取正式复核记录 | 已审结（reviewed/published） | 状态分布 | 决定分布 | 目标类型 |",
        "| ---: | ---: | --- | --- | --- |",
        f"| {values['total']} | {values['finalized']} | {statuses} | {decisions} | {targets} |",
    ]


def render_quality_report(report: dict[str, Any]) -> str:
    """把统计对象渲染为可直接阅读的 Markdown，不写入绝对路径或审核结论。"""
    warning_lines = report["warnings"]
    overview = report["overview"]
    lines = [
        "# 步步高物理数字资料库处理质量报告",
        "",
        "本报告由 `sources/sources.jsonl`、document/question 记录及转换、结构化阶段日志重建；只描述自动处理状态，不能替代人工复核或发布验收。",
        "",
        "## 先看结论",
        "",
        f"- 已生成可读文档：{overview['readable_sources']} 份；转换/结构化失败或阻断：{overview['conversion_or_structure_failed_or_blocked']} 份。",
        f"- 需人工核对（自动标记）：{overview['automatic_review_marked_sources']} 份来源。这是图、公式、表格、答案或题目边界的自动提醒，**不等于转换失败**。",
        f"- 保守未拆题：{overview['conservative_unsplit_blocks']} 个编号区块，分布在 {overview['conservative_unsplit_sources']} 份来源中。它们因证据不足没有被猜成题目记录，但原文仍保留在对应 Markdown，**不等于丢失**。",
        f"- 已进入待人工复核流程：{overview['pending_manual_review_sources']} 份来源；这只是工作流状态，不表示已经有人复核完成。",
        "",
        "## 来源处理统计",
        "",
        *_source_processing_rows(report),
        "",
        "`已生成可读文档` 仅表示已得到 Markdown/document 记录且没有失败或阻断状态；它不表示内容已经人工确认、`reviewed` 或 `published`。",
        "",
        "## 自动核对情况",
        "",
        *_automatic_review_rows(report),
        "",
        "自动标记和待人工复核可与“已生成可读文档”重叠。保守未拆题的计数单位是编号区块，因此会大于来源数；它只说明系统拒绝猜测题目边界，不能用于推断原文缺失。",
        "",
        "## 文档与题目记录",
        "",
        *_record_rows(report),
        "",
        "## 题目提醒如何进入人工复核",
        "",
        *_question_signal_rows(report),
        "",
        "“直接提醒”是题目自身检测到的答案、解析、公式、选项或题目边界问题，或未从来源继承的单题待审状态；这些题会强制进入复核队列。",
        "",
        "“仅继承来源级提醒”表示题目没有自身问题，只是随来源/document 的转换或结构化待审状态一起标记。它**不等于这道题有异常**：对应 document 会优先复核，题目只参加各资料类型至少 10% 的稳定抽样。题目若同时有直接提醒，仍按直接提醒强制复核，不会被降级为抽样。",
        "",
        "## 来源清单状态",
        "",
        *_manifest_status_rows(report),
        "",
        "来源清单的状态由处理流水线维护；报告同时用实际 document/question 记录与阶段日志交叉检查。若清单状态与产物不一致，会显示为自动核对标记，不能仅凭清单状态宣布完成。",
        "",
        "清单状态与产物/阶段日志不一致（已计入自动核对标记）：" + "；".join(
            f"{label} {report['source_processing']['by_profile'][profile]['source_state_mismatch']}"
            for profile, label in (("teacher", "教师用书"), ("gaokao", "高考题"), ("textbook", "必修/选修资料"))
        ) + f"；合计 {report['source_processing']['total']['source_state_mismatch']}。",
        "",
        "## 正式人工复核记录",
        "",
        *_review_rows(report),
        "",
        "这里仅统计符合 `review.schema.json` 语义、可关联到 document/question 的正式 review JSON；`reviews/review-queue.jsonl` 是自动待办，不计入人工复核或已审结数量。",
        "",
        "## 阶段日志",
        "",
        "| 阶段 | 状态分布 |",
        "| --- | --- |",
    ]
    for phase, statuses in report["phase_reports"].items():
        value = "；".join(f"{key} {count}" for key, count in statuses.items()) or "尚无日志"
        lines.append(f"| {phase} | {value} |")
    lines.extend(
        [
            "",
            "## 人工复核入口",
            "",
            "运行 `python3 项目资源库/步步高/physics-digital-library/scripts/generate_review_queue.py` 可按教师用书、高考题、必修/选修资料分层抽取已生成 document 与 question 的至少 10% 复核样本。所有 document 的来源级问题优先入队；题目只在有自身直接提醒时强制入队，纯继承来源级提示的题目按抽样入队。队列记录统一为 `pending_manual_review`，其中不包含人工 reviewer、decision 或已审结论。",
            "",
            "实际逐题核对时，先运行 `review_workflow.py checklist` 生成只读核对单；确认后用 `review_workflow.py submit` 预览，再显式加 `--apply` 写入一条正式 review JSON。单题通过不会自动提升整份来源或全库状态。",
            "",
            "## 数据完整性提示",
            "",
            f"- 权威清单：`{report['manifest']['path']}`（SHA-256：`{report['manifest']['sha256']}`）。",
            "- 本报告只读取资料库内固定位置的清单、记录和阶段日志，不跟随 JSON 输入目录或文件的符号链接；路径、JSON 或来源关联异常会列入下方警告，且不会静默进入统计或复核队列。",
            "- 原始资料及转换内容仅限个人本地教学、备课、研究和受控 AI 辅助使用，不得公开发布、分发、商业出售或上传至未获授权的平台。",
        ]
    )
    if warning_lines:
        lines.extend(["", "## 读取警告", ""])
        for warning in warning_lines[:100]:
            lines.append(f"- {warning}")
        if len(warning_lines) > 100:
            lines.append(f"- 其余 {len(warning_lines) - 100} 条警告已省略；请检查输入记录。")
    return "\n".join(lines) + "\n"


def write_quality_report(library_root: Path | str = LIBRARY_ROOT) -> dict[str, Any]:
    """安全写入 JSON 和 Markdown 质量报告，返回写入路径和统计对象。"""
    root = safe_library_root(library_root)
    report = build_quality_report(root)
    write_json(root, REPORT_JSON_PATH, report)
    write_text(root, REPORT_MARKDOWN_PATH, render_quality_report(report))
    return {
        "report": report,
        "paths": {"json": REPORT_JSON_PATH, "markdown": REPORT_MARKDOWN_PATH},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成步步高正式资料库的处理质量报告")
    parser.add_argument("--json", action="store_true", help="将报告对象输出到标准输出")
    args = parser.parse_args(argv)
    try:
        result = write_quality_report(official_library_root())
    except (OSError, PipelineError, ValueError) as error:
        print(f"质量报告生成失败：{error}", file=sys.stderr)
        return 1
    if args.json:
        print(json_bytes(result["report"]).decode("utf-8"), end="")
    else:
        print("已写入 {markdown} 与 {json}".format(**result["paths"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
