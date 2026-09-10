#!/usr/bin/env python3
"""生成步步高资料库的分层人工复核队列。

队列是待办清单，不是 review 结论：所有条目的状态固定为
``pending_manual_review``，不会预填 reviewer、decision 或任何“已审通过”标记。
"""

from __future__ import annotations

import argparse
import hashlib
import math
import sys
from collections import defaultdict
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
from quality_common import PROFILE_ORDER, load_library_snapshot  # noqa: E402


QUEUE_JSONL_PATH = "reviews/review-queue.jsonl"
QUEUE_SUMMARY_PATH = "reports/review-queue-summary.json"
QUEUE_VERSION = "1.0"
MINIMUM_SAMPLE_RATE = 0.10


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    return [value for value in values if value and not (value in seen or seen.add(value))]


def _validate_sample_rate(sample_rate: float) -> float:
    if isinstance(sample_rate, bool) or not isinstance(sample_rate, (int, float)):
        raise ValueError("sample_rate 必须是 0.10 到 1.00 之间的数字")
    value = float(sample_rate)
    if not math.isfinite(value) or value < MINIMUM_SAMPLE_RATE or value > 1:
        raise ValueError("sample_rate 必须在 0.10 到 1.00 之间，保证每层至少抽检 10%")
    return value


def _required_count(total: int, sample_rate: float) -> int:
    return max(1, math.ceil(total * sample_rate)) if total else 0


def _stable_key(record: dict[str, Any], kind: str, profile: str) -> str:
    seed = f"bubugao-review-queue-v{QUEUE_VERSION}|{kind}|{profile}|{record['source_id']}|{record['id']}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _review_checklist(kind: str) -> list[str]:
    if kind == "document":
        return [
            "对照原始 Word 核对 Markdown 段落、表格、图片和公式是否完整。",
            "核对讲解、练习、答案解析等区块是否保留且没有跨课时或跨题串段。",
            "确认现有异常能否关闭；不能关闭时记录修复方案或转为 blocked。",
        ]
    if kind == "question":
        return [
            "对照来源位置核对题号、题干边界、题型和选项。",
            "核对答案、解析、公式和配图的完整性与对应关系。",
            "核对知识点、模型、技能、难度和复核状态；完成后另建正式 review 记录。",
        ]
    return [
        "确认原始 Word 是否可读取，并核对失败或异常的具体原因。",
        "执行人工补救后重新运行转换和结构化；无法修复时保留 blocked 原因。",
    ]


def _queue_item(
    record: dict[str, Any],
    *,
    kind: str,
    issues: list[str],
    selection_reasons: list[str],
) -> dict[str, Any]:
    """创建不包含人工审结字段的待办条目。"""
    return {
        "queue_id": f"queue.bbg.{kind}.{hashlib.sha256((kind + '|' + record['id']).encode('utf-8')).hexdigest()[:20]}",
        "status": "pending_manual_review",
        "target_type": kind,
        "target_id": record["id"],
        "target_relative_path": record["relative_path"],
        "source_id": record["source_id"],
        "source_relative_path": record["source_relative_path"],
        "profile": record["profile"],
        "selection_reasons": _unique_strings(selection_reasons),
        "issues": _unique_strings(issues),
        "review_checklist": _review_checklist(kind),
    }


def _select_stratum(
    records: list[dict[str, Any]],
    *,
    kind: str,
    profile: str,
    sample_rate: float,
    source_issues: dict[str, list[str]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """先纳入直接问题，再按稳定哈希补足每一资料类型的最低抽检比例。

    document 的待审状态本身就是来源级问题，应优先复核；question 则只在题目
    自身有直接 issue 或单题待审状态时强制入队。来源文档传播给所有题目的
    通用提示和 pending 状态只保留为追溯上下文，不会把整份试卷的每一道题都
    伪装成题目异常。
    """
    required = _required_count(len(records), sample_rate)
    selected_by_id: dict[str, dict[str, Any]] = {}
    for record in records:
        if kind == "document":
            issues = list(record["issues"])
            issues.extend(source_issues.get(record["source_id"], []))
            pending = bool(record.get("is_pending_manual_review"))
            issue_reason = "已发现文档或来源级问题，必须人工复核"
            pending_reason = "文档已标记 pending_manual_review，必须人工复核"
        else:
            issues = list(record.get("direct_issues", record["issues"]))
            pending = bool(record.get("direct_pending_manual_review"))
            issue_reason = "题目存在直接提醒，必须人工复核"
            pending_reason = "题目已单独标记 pending_manual_review，必须人工复核"
        if issues or pending:
            reasons: list[str] = []
            if issues:
                reasons.append(issue_reason)
            if pending:
                reasons.append(pending_reason)
            selected_by_id[record["id"]] = {
                "record": record,
                "issues": _unique_strings(issues),
                "selection_reasons": reasons,
            }
    forced_selected = len(selected_by_id)
    candidates = [record for record in records if record["id"] not in selected_by_id]
    candidates.sort(key=lambda record: (_stable_key(record, kind, profile), record["id"]))
    # 对“其他题”（没有直接提醒的题目）另行抽取至少 10%，不能让大量直接问题
    # 抵扣掉这一层抽样。document 仍沿用“直接问题先入队，再补足总体最低比例”。
    sample_required = (
        _required_count(len(candidates), sample_rate)
        if kind == "question"
        else max(0, required - forced_selected)
    )
    sampled_selected = 0
    for record in candidates:
        if sampled_selected >= sample_required:
            break
        selected_by_id[record["id"]] = {
            "record": record,
            # 抽样题不把来源级继承提示展示成题目自身问题；需要核对来源时应打开
            # 对应 document 队列项。
            "issues": list(record.get("direct_issues", record["issues"]))
            if kind == "question"
            else list(record["issues"]),
            "selection_reasons": _unique_strings(
                [
                    "仅继承来源级提醒；本题不作为直接异常，按分层稳定抽检"
                    if kind == "question"
                    and record.get("only_inherited_source_review_signal")
                    else "",
                    f"{profile} 分层稳定抽检（至少 {sample_rate:.0%}）",
                ]
            ),
        }
        sampled_selected += 1
    selected = [selected_by_id[key] for key in sorted(selected_by_id)]
    return selected, {
        "eligible": len(records),
        "minimum_required": required,
        "minimum_sample_required": sample_required,
        "forced_by_direct_signal_or_document_state": forced_selected,
        "selected_by_sample": sampled_selected,
        "only_inherited_source_review_signal": sum(
            bool(record.get("only_inherited_source_review_signal")) for record in records
        )
        if kind == "question"
        else 0,
        "selected": len(selected),
        "coverage_percent": round((len(selected) / len(records) * 100) if records else 0, 2),
    }


def build_review_queue(
    library_root: Path | str = LIBRARY_ROOT, *, sample_rate: float = MINIMUM_SAMPLE_RATE
) -> dict[str, Any]:
    """构建队列对象而不写入文件，适合测试或人工预览。"""
    rate = _validate_sample_rate(sample_rate)
    snapshot = load_library_snapshot(library_root)
    # source_summaries 已只汇总来源/document 问题与题目直接问题。来源待审提示
    # 仅附给 document 队列，确保来源文档优先复核，但绝不再传播到所有题目项。
    source_issues: dict[str, list[str]] = {}
    for source_id, source_summary in snapshot["source_summaries"].items():
        issues = list(source_summary["issues"])
        if source_summary["pending_manual_review"]:
            issues.append("来源清单或关联记录已标记 pending_manual_review，文档需优先复核")
        source_issues[source_id] = _unique_strings(issues)
    queue_items: list[dict[str, Any]] = []
    by_profile: dict[str, Any] = {}
    for profile in PROFILE_ORDER:
        profile_summary: dict[str, Any] = {}
        for plural_kind, kind in (("documents", "document"), ("questions", "question")):
            records = [record for record in snapshot[plural_kind] if record["profile"] == profile]
            selected, summary = _select_stratum(
                records,
                kind=kind,
                profile=profile,
                sample_rate=rate,
                source_issues=source_issues,
            )
            profile_summary[plural_kind] = summary
            for value in selected:
                queue_items.append(
                    _queue_item(
                        value["record"],
                        kind=kind,
                        issues=value["issues"],
                        selection_reasons=value["selection_reasons"],
                    )
                )

        source_exceptions = [
            summary
            for summary in snapshot["source_summaries"].values()
            if summary["profile"] == profile
            and (
                summary["processing_state"] == "failed"
                or (summary["has_exception"] and summary["document_count"] == 0)
            )
        ]
        profile_summary["source_exceptions"] = {
            "eligible": len(source_exceptions),
            "minimum_required": len(source_exceptions),
            "selected": len(source_exceptions),
            "coverage_percent": 100 if source_exceptions else 0,
        }
        for source in sorted(source_exceptions, key=lambda value: value["source_id"]):
            reason = (
                "阶段失败异常，必须人工处理"
                if source["processing_state"] == "failed"
                else "缺少可复核文档的来源异常，必须人工处理"
            )
            queue_items.append(
                _queue_item(
                    {
                        "id": source["source_id"],
                        "source_id": source["source_id"],
                        "profile": source["profile"],
                        "relative_path": source["source_relative_path"],
                        "source_relative_path": source["source_relative_path"],
                    },
                    kind="source_exception",
                    issues=source["issues"] or ["来源处理失败，需人工补救"],
                    selection_reasons=[reason],
                )
            )
        by_profile[profile] = profile_summary

    queue_items.sort(key=lambda item: (PROFILE_ORDER.index(item["profile"]), item["target_type"], item["target_id"]))
    totals_by_type = defaultdict(int)
    for item in queue_items:
        totals_by_type[item["target_type"]] += 1
    summary = {
        "queue_version": QUEUE_VERSION,
        "status": "pending_manual_review",
        "sample_rate": rate,
        "manifest_sha256": snapshot["manifest_sha256"],
        "queue_path": QUEUE_JSONL_PATH,
        "counts": {
            "total": len(queue_items),
            "by_target_type": dict(sorted(totals_by_type.items())),
            "by_profile": by_profile,
        },
        "warnings": snapshot["warnings"],
        "notice": (
            "队列仅表示待人工复核；未生成 reviewer、decision 或任何已审结论。"
            "题目队列仅强制纳入题目自身直接提醒；仅继承来源级提醒的题目按分层抽样。"
        ),
    }
    return {"items": queue_items, "summary": summary}


def write_review_queue(
    library_root: Path | str = LIBRARY_ROOT, *, sample_rate: float = MINIMUM_SAMPLE_RATE
) -> dict[str, Any]:
    """安全写入 JSONL 队列及摘要，原子替换上一次同名自动队列。"""
    root = safe_library_root(library_root)
    result = build_review_queue(root, sample_rate=sample_rate)
    contents = "".join(json_bytes(item, indent=None).decode("utf-8") for item in result["items"])
    write_text(root, QUEUE_JSONL_PATH, contents)
    write_json(root, QUEUE_SUMMARY_PATH, result["summary"])
    return {
        **result,
        "paths": {"queue": QUEUE_JSONL_PATH, "summary": QUEUE_SUMMARY_PATH},
    }


def _sample_rate_argument(value: str) -> float:
    try:
        return _validate_sample_rate(float(value))
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成步步高资料库的分层人工复核待办队列")
    parser.add_argument(
        "--sample-rate",
        type=_sample_rate_argument,
        default=MINIMUM_SAMPLE_RATE,
        help="每个资料类型内 document/question 的最低抽检比例，默认 0.10",
    )
    parser.add_argument("--json", action="store_true", help="将队列摘要输出到标准输出")
    args = parser.parse_args(argv)
    try:
        result = write_review_queue(official_library_root(), sample_rate=args.sample_rate)
    except (OSError, PipelineError, ValueError) as error:
        print(f"复核队列生成失败：{error}", file=sys.stderr)
        return 1
    if args.json:
        print(json_bytes(result["summary"]).decode("utf-8"), end="")
    else:
        print("已写入 {queue} 与 {summary}".format(**result["paths"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
