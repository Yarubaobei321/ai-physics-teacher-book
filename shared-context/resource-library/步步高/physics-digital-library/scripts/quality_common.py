#!/usr/bin/env python3
"""质量报告与人工复核队列共用的安全读取层。

本模块只读取正式资料库中固定位置的 JSON/JSONL 记录，并只返回已通过最小
路径与来源关联检查的候选项。它不修改来源清单、原始 Word、转换结果或题目
记录；调用方只能通过 ``library_common.write_*`` 写入 reports/ 或 reviews/。
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from library_common import (  # noqa: E402
    LIBRARY_ROOT,
    PROFILES,
    PipelineError,
    SOURCE_ID_RE,
    is_safe_relative_path,
    safe_library_root,
)


PROFILE_ORDER = ("teacher", "gaokao", "textbook")
RECORD_DIRECTORIES = {
    "document": "records/documents",
    "question": "questions",
}
REVIEW_DIRECTORY = "reviews"
PHASE_REPORT_DIRECTORIES = {
    "conversion": "reports/conversion",
    "structure": "reports/structure",
}
FAILED_PHASE_STATUSES = frozenset({"failed", "partial_failure", "blocked"})
CONSERVATIVE_UNSPLIT_ISSUE_MARKER = "编号条目缺少题干、答案或完整选项等强证据，未生成题目记录"
# 这些措辞不是某一道题自身识别出的内容错误，而是转换/结构化流水线把来源
# 文档的待审状态传播给题目时留下的通用提示。它们必须保留在原始题目记录中，
# 以便完整追溯；但在复核统计和题目队列里不能把它们误当成每一道题都异常。
INHERITED_SOURCE_REVIEW_ISSUE_MARKERS = (
    "来源文档存在待人工复核的转换或结构化问题",
    "来源清单或关联记录已标记 pending_manual_review",
    "来源文档已标记 pending_manual_review",
    "来源已标记 pending_manual_review",
)
SOURCE_STATUSES = frozenset(
    {
        "discovered",
        "raw_extracted",
        "ai_structured",
        "pending_manual_review",
        "reviewed",
        "published",
        "blocked",
    }
)


class QualityDataError(PipelineError):
    """质量统计读取到不能安全使用的核心输入时抛出。"""


def _normalise_strings(value: object) -> list[str]:
    """保留非空字符串，去重但不把任意对象串化进报告。"""
    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    result: list[str] = []
    for item in value:
        if isinstance(item, str):
            text = item.strip()
            if text and text not in seen:
                seen.add(text)
                result.append(text)
    return result


def _is_inherited_source_review_issue(issue: str) -> bool:
    """判断题目 issue 是否只是来源级待审状态的继承提示。

    这里故意只识别固定、可解释的通用措辞，不会把“答案缺失”“公式需核对”等
    题目自身信号过滤掉。未来若流水线新增同类措辞，应把完整稳定短语加入常量，
    而不是用宽泛的“来源”关键词猜测。
    """
    return any(marker in issue for marker in INHERITED_SOURCE_REVIEW_ISSUE_MARKERS)


def _split_direct_and_inherited_issues(issues: list[str]) -> tuple[list[str], list[str]]:
    """把记录中的 issue 分为直接问题和仅继承的来源级提示。"""
    direct: list[str] = []
    inherited: list[str] = []
    for issue in issues:
        if _is_inherited_source_review_issue(issue):
            inherited.append(issue)
        else:
            direct.append(issue)
    return direct, inherited


def _record_is_pending_manual_review(record: dict[str, Any]) -> bool:
    return (
        record.get("status") == "pending_manual_review"
        or record.get("review_status") == "pending_manual_review"
    )


def _safe_directory(root: Path, relative_path: str, warnings: list[str]) -> Path | None:
    """返回一个未经过符号链接的固定输入目录，缺失目录视为空集合。"""
    if not is_safe_relative_path(relative_path):
        raise QualityDataError(f"内部输入目录不是安全相对路径：{relative_path}")
    current = root
    for component in Path(relative_path).parts:
        current = current / component
        if current.exists() and current.is_symlink():
            warnings.append(f"跳过符号链接输入目录：{relative_path}")
            return None
    if not current.exists():
        return None
    if not current.is_dir():
        warnings.append(f"跳过非目录输入位置：{relative_path}")
        return None
    return current


def _iter_safe_json_files(root: Path, relative_directory: str, warnings: list[str]) -> Iterable[tuple[str, Path]]:
    """在固定目录内递归读取普通 .json 文件，绝不跟随符号链接。"""
    directory = _safe_directory(root, relative_directory, warnings)
    if directory is None:
        return
    for current_directory, dirnames, filenames in os.walk(directory, followlinks=False):
        current = Path(current_directory)
        if current.is_symlink():
            dirnames[:] = []
            continue
        safe_dirnames: list[str] = []
        for name in sorted(dirnames):
            candidate = current / name
            if candidate.is_symlink():
                try:
                    shown = candidate.relative_to(root).as_posix()
                except ValueError:
                    shown = relative_directory
                warnings.append(f"跳过符号链接输入目录：{shown}")
            else:
                safe_dirnames.append(name)
        dirnames[:] = safe_dirnames
        for name in sorted(filenames):
            if not name.endswith(".json"):
                continue
            candidate = current / name
            if candidate.is_symlink() or not candidate.is_file():
                try:
                    shown = candidate.relative_to(root).as_posix()
                except ValueError:
                    shown = relative_directory
                warnings.append(f"跳过符号链接或非普通 JSON：{shown}")
                continue
            try:
                relative = candidate.relative_to(root).as_posix()
            except ValueError:
                warnings.append(f"跳过越界 JSON：{candidate.name}")
                continue
            if not is_safe_relative_path(relative):
                warnings.append(f"跳过不安全 JSON 路径：{relative}")
                continue
            yield relative, candidate


def _read_json(path: Path, relative_path: str, warnings: list[str]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        warnings.append(f"跳过无法解析的 JSON：{relative_path}（{error}）")
        return None
    if not isinstance(value, dict):
        warnings.append(f"跳过非对象 JSON：{relative_path}")
        return None
    return value


def _load_manifest(root: Path, warnings: list[str]) -> tuple[dict[str, dict[str, Any]], str]:
    """读取唯一权威来源清单，并返回按 source_id 索引的安全来源。"""
    sources_directory = root / "sources"
    if sources_directory.is_symlink() or not sources_directory.is_dir():
        raise QualityDataError("sources 必须是现有且非符号链接的目录")
    manifest = sources_directory / "sources.jsonl"
    if manifest.is_symlink() or not manifest.is_file():
        raise QualityDataError("缺少普通文件 sources/sources.jsonl")
    try:
        contents = manifest.read_bytes()
        lines = contents.decode("utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise QualityDataError(f"无法读取 sources/sources.jsonl：{error}") from error

    sources: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            warnings.append(f"sources/sources.jsonl:{line_number}：跳过空行")
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as error:
            warnings.append(f"sources/sources.jsonl:{line_number}：跳过无效 JSON（{error.msg}）")
            continue
        if not isinstance(raw, dict):
            warnings.append(f"sources/sources.jsonl:{line_number}：跳过非对象记录")
            continue
        source_id = raw.get("id")
        profile = raw.get("profile")
        source_relative_path = raw.get("relative_path")
        if not isinstance(source_id, str) or not SOURCE_ID_RE.fullmatch(source_id):
            warnings.append(f"sources/sources.jsonl:{line_number}：跳过格式无效的 source_id")
            continue
        if profile not in PROFILES:
            warnings.append(f"sources/sources.jsonl:{line_number}：跳过未知 profile：{profile!r}")
            continue
        if not isinstance(source_relative_path, str) or not is_safe_relative_path(source_relative_path) or not source_relative_path.startswith("raw/"):
            warnings.append(f"sources/sources.jsonl:{line_number}：跳过不安全来源路径")
            continue
        if source_id in sources:
            warnings.append(f"sources/sources.jsonl:{line_number}：跳过重复 source_id：{source_id}")
            continue
        metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
        manifest_status = raw.get("status")
        if manifest_status not in SOURCE_STATUSES:
            warnings.append(f"sources/sources.jsonl:{line_number}：来源状态无效，按 discovered 统计")
            manifest_status = "discovered"
        output_paths = raw.get("output_paths")
        if output_paths is not None and not isinstance(output_paths, dict):
            warnings.append(f"sources/sources.jsonl:{line_number}：output_paths 不是对象，已忽略")
        sources[source_id] = {
            "id": source_id,
            "profile": profile,
            "relative_path": source_relative_path,
            "title": raw.get("title") if isinstance(raw.get("title"), str) else source_id,
            "status": manifest_status,
            "exceptions": _normalise_strings(raw.get("exceptions")),
            "metadata": metadata,
        }
    return sources, hashlib.sha256(contents).hexdigest()


def _load_linked_records(
    root: Path,
    kind: str,
    sources: dict[str, dict[str, Any]],
    warnings: list[str],
) -> list[dict[str, Any]]:
    """读取 document/question 记录，并验证其文件位置、来源和 profile 关联。"""
    directory = RECORD_DIRECTORIES[kind]
    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for actual_relative_path, path in _iter_safe_json_files(root, directory, warnings):
        raw = _read_json(path, actual_relative_path, warnings)
        if raw is None:
            continue
        record_id = raw.get("id")
        source_id = raw.get("source_id")
        recorded_relative_path = raw.get("relative_path")
        if not isinstance(record_id, str) or not record_id:
            warnings.append(f"跳过缺少 ID 的 {kind}：{actual_relative_path}")
            continue
        if record_id in seen_ids:
            warnings.append(f"跳过重复 ID 的 {kind}：{record_id}")
            continue
        if source_id not in sources:
            warnings.append(f"跳过未在 manifest 中登记来源的 {kind}：{actual_relative_path}")
            continue
        if recorded_relative_path != actual_relative_path or not is_safe_relative_path(recorded_relative_path):
            warnings.append(f"跳过记录路径不一致或不安全的 {kind}：{actual_relative_path}")
            continue
        if kind == "document" and not actual_relative_path.startswith("records/documents/"):
            warnings.append(f"跳过目录不匹配的 document：{actual_relative_path}")
            continue
        if kind == "question" and not actual_relative_path.startswith("questions/"):
            warnings.append(f"跳过目录不匹配的 question：{actual_relative_path}")
            continue
        record_issues = _normalise_strings(raw.get("issues"))
        direct_issues, inherited_source_review_issues = _split_direct_and_inherited_issues(
            record_issues
        )
        status = raw.get("status") if isinstance(raw.get("status"), str) else "unknown"
        review_status = (
            raw.get("review_status") if isinstance(raw.get("review_status"), str) else None
        )
        seen_ids.add(record_id)
        records.append(
            {
                "id": record_id,
                "source_id": source_id,
                "profile": sources[source_id]["profile"],
                "relative_path": actual_relative_path,
                "status": status,
                "review_status": review_status,
                "issues": record_issues,
                "direct_issues": direct_issues,
                "inherited_source_review_issues": inherited_source_review_issues,
                "is_pending_manual_review": _record_is_pending_manual_review(
                    {"status": status, "review_status": review_status}
                ),
                "source_relative_path": sources[source_id]["relative_path"],
                "source_title": sources[source_id]["title"],
            }
        )
    return sorted(records, key=lambda value: (value["profile"], value["id"]))


def _load_phase_reports(
    root: Path,
    sources: dict[str, dict[str, Any]],
    warnings: list[str],
) -> tuple[dict[str, dict[str, list[str]]], dict[str, Counter[str]]]:
    """汇集每个来源的转换/结构化日志状态和异常，但不信任其路径字段。"""
    source_phases: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    phase_status_counts: dict[str, Counter[str]] = {
        phase: Counter() for phase in PHASE_REPORT_DIRECTORIES
    }
    for phase, directory in PHASE_REPORT_DIRECTORIES.items():
        for relative_path, path in _iter_safe_json_files(root, directory, warnings):
            raw = _read_json(path, relative_path, warnings)
            if raw is None:
                continue
            source_id = raw.get("source_id")
            status = raw.get("status")
            if source_id not in sources:
                warnings.append(f"跳过未在 manifest 中登记的 {phase} 日志：{relative_path}")
                continue
            if not isinstance(status, str) or not status:
                warnings.append(f"{phase} 日志缺少状态：{relative_path}")
                status = "unknown"
            phase_status_counts[phase][status] += 1
            source_phases[source_id][f"{phase}_status"].append(status)
            source_phases[source_id]["issues"].extend(_normalise_strings(raw.get("issues")))
    return source_phases, phase_status_counts


def _load_pipeline_fallback_issues(
    root: Path,
    sources: dict[str, dict[str, Any]],
    source_phases: dict[str, dict[str, list[str]]],
    warnings: list[str],
) -> None:
    """读取最近一次批处理结果，仅为缺少阶段日志的来源补充异常线索。

    ``pipeline-last-run.json`` 会被下一次运行覆盖，不能覆盖每来源阶段日志的结论；
    所以这里绝不把它当作唯一成功证据。
    """
    reports_directory = _safe_directory(root, "reports", warnings)
    if reports_directory is None:
        return
    relative_path = "reports/pipeline-last-run.json"
    path = reports_directory / "pipeline-last-run.json"
    if not path.exists():
        return
    if path.is_symlink() or not path.is_file():
        warnings.append("跳过符号链接或非普通 JSON：reports/pipeline-last-run.json")
        return
    raw = _read_json(path, relative_path, warnings)
    if raw is None:
        return
    results = raw.get("results")
    if not isinstance(results, list):
        return
    for result in results:
        if not isinstance(result, dict):
            continue
        source_id = result.get("source_id")
        if source_id not in sources:
            continue
        phase_info = source_phases[source_id]
        if phase_info.get("conversion_status") or phase_info.get("structure_status"):
            continue
        if result.get("success") is False:
            phase_info["pipeline_status"].append("failed")
            phase_info["issues"].extend(_normalise_strings(result.get("issues")))


def _status_counter(
    records: list[dict[str, Any]], profiles: Iterable[str], *, kind: str
) -> dict[str, Any]:
    """统计记录状态，并为题目单独保留直接/继承提醒的归属。

    ``pending_manual_review`` 是流水线状态，可能由来源文档传播而来。因此题目
    的“直接提醒”只统计题目自身 issues 或未继承来源状态的单题待审；不能用
    原始 ``issues`` 数量替代它。
    """
    result: dict[str, Any] = {
        "total": len(records),
        "by_status": dict(sorted(Counter(record["status"] for record in records).items())),
        "by_profile": {},
    }
    for profile in profiles:
        current = [record for record in records if record["profile"] == profile]
        values: dict[str, Any] = {
            "total": len(current),
            "by_status": dict(sorted(Counter(record["status"] for record in current).items())),
            "pending_manual_review": sum(
                bool(record.get("is_pending_manual_review")) for record in current
            ),
            "with_issues": sum(1 for record in current if record["issues"]),
        }
        if kind == "question":
            values.update(
                {
                    "with_direct_issues": sum(
                        bool(record.get("direct_issues")) for record in current
                    ),
                    "with_inherited_source_review_issues": sum(
                        bool(record.get("inherited_source_review_issues")) for record in current
                    ),
                    "direct_pending_manual_review": sum(
                        bool(record.get("direct_pending_manual_review")) for record in current
                    ),
                    "inherited_source_review_status": sum(
                        bool(record.get("inherited_source_review_status")) for record in current
                    ),
                    "direct_review_required": sum(
                        bool(record.get("has_direct_review_signal")) for record in current
                    ),
                    "only_inherited_source_review_signal": sum(
                        bool(record.get("only_inherited_source_review_signal"))
                        for record in current
                    ),
                }
            )
        result["by_profile"][profile] = values
    if kind == "question":
        result["review_signals"] = {
            "with_direct_issues": sum(bool(record.get("direct_issues")) for record in records),
            "with_inherited_source_review_issues": sum(
                bool(record.get("inherited_source_review_issues")) for record in records
            ),
            "direct_pending_manual_review": sum(
                bool(record.get("direct_pending_manual_review")) for record in records
            ),
            "inherited_source_review_status": sum(
                bool(record.get("inherited_source_review_status")) for record in records
            ),
            "direct_review_required": sum(
                bool(record.get("has_direct_review_signal")) for record in records
            ),
            "only_inherited_source_review_signal": sum(
                bool(record.get("only_inherited_source_review_signal")) for record in records
            ),
        }
    return result


def _source_manifest_status_counter(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """独立保留来源清单的声明状态，便于发现清单与产物不一致。"""
    result: dict[str, Any] = {
        "total": dict(sorted(Counter(source["status"] for source in sources.values()).items())),
        "by_profile": {},
    }
    for profile in PROFILE_ORDER:
        result["by_profile"][profile] = dict(
            sorted(
                Counter(
                    source["status"]
                    for source in sources.values()
                    if source["profile"] == profile
                ).items()
            )
        )
    return result


def _load_review_records(
    root: Path,
    target_records: dict[str, dict[str, Any]],
    warnings: list[str],
) -> list[dict[str, Any]]:
    """读取正式 review JSON，显式排除 ``review-queue.jsonl`` 自动待办。

    只接受能关联到已读取 document/question 的正式复核记录；无法关联的 JSON
    不能凭自身的 ``reviewed`` 状态为资料库制造人工验收结论。
    """
    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for actual_relative_path, path in _iter_safe_json_files(root, REVIEW_DIRECTORY, warnings):
        raw = _read_json(path, actual_relative_path, warnings)
        if raw is None:
            continue
        review_id = raw.get("id")
        recorded_relative_path = raw.get("relative_path")
        target_id = raw.get("target_id")
        target_relative_path = raw.get("target_relative_path")
        decision = raw.get("decision")
        reviewer = raw.get("reviewer")
        status = raw.get("status")
        if not isinstance(review_id, str) or not review_id:
            warnings.append(f"跳过缺少 ID 的 review：{actual_relative_path}")
            continue
        if review_id in seen_ids:
            warnings.append(f"跳过重复 ID 的 review：{review_id}")
            continue
        if recorded_relative_path != actual_relative_path or not is_safe_relative_path(recorded_relative_path):
            warnings.append(f"跳过记录路径不一致或不安全的 review：{actual_relative_path}")
            continue
        if not isinstance(target_id, str) or target_id not in target_records:
            warnings.append(f"跳过目标不存在的 review：{actual_relative_path}")
            continue
        target = target_records[target_id]
        if target_relative_path != target["relative_path"]:
            warnings.append(f"跳过目标路径不一致的 review：{actual_relative_path}")
            continue
        if not isinstance(status, str) or status not in SOURCE_STATUSES:
            warnings.append(f"跳过状态无效的 review：{actual_relative_path}")
            continue
        if not isinstance(decision, str) or decision not in {"approved", "needs_changes", "rejected", "blocked"}:
            warnings.append(f"跳过 decision 无效的 review：{actual_relative_path}")
            continue
        if not isinstance(reviewer, str) or not reviewer.strip():
            warnings.append(f"跳过 reviewer 缺失的 review：{actual_relative_path}")
            continue
        seen_ids.add(review_id)
        records.append(
            {
                "id": review_id,
                "relative_path": actual_relative_path,
                "status": status,
                "decision": decision,
                "target_id": target_id,
                "target_type": "document" if target["relative_path"].startswith("records/documents/") else "question",
                "profile": target["profile"],
            }
        )
    return sorted(records, key=lambda value: value["id"])


def _review_counter(records: list[dict[str, Any]]) -> dict[str, Any]:
    """只统计正式人工 review JSON，队列和 pending 记录不算人工复核完成。"""
    reviewed_statuses = {"reviewed", "published"}
    return {
        "total": len(records),
        "finalized": sum(record["status"] in reviewed_statuses for record in records),
        "by_status": dict(sorted(Counter(record["status"] for record in records).items())),
        "by_decision": dict(sorted(Counter(record["decision"] for record in records).items())),
        "by_target_type": dict(sorted(Counter(record["target_type"] for record in records).items())),
        "by_profile": {
            profile: {
                "total": sum(record["profile"] == profile for record in records),
                "finalized": sum(
                    record["profile"] == profile and record["status"] in reviewed_statuses
                    for record in records
                ),
            }
            for profile in PROFILE_ORDER
        },
    }


def _has_failed_phase(phase_data: dict[str, list[str]]) -> bool:
    for key, statuses in phase_data.items():
        if not key.endswith("_status"):
            continue
        if any(status in FAILED_PHASE_STATUSES for status in statuses):
            return True
    return False


def _conservative_unsplit_block_count(issues: Iterable[str]) -> int:
    """统计因证据不足而保留在 Markdown 中的编号条目。

    这类条目没有被静默删除：结构化器仅拒绝把它们猜成题目记录。这里按结构化
    日志中的每条定位信息计数，故它是“区块数”，不是来源文档数。
    """
    return sum(CONSERVATIVE_UNSPLIT_ISSUE_MARKER in issue for issue in issues)


def load_library_snapshot(library_root: Path | str = LIBRARY_ROOT) -> dict[str, Any]:
    """读取生成质量报告和队列所需的最小安全快照。

    结果只包含用于聚合和排队的字段，路径全部是资料库内的相对路径。不能安全
    关联的记录被跳过，并写入 ``warnings``，让报告明确呈现问题而不是静默纳入。
    """
    root = safe_library_root(library_root)
    warnings: list[str] = []
    sources, manifest_sha256 = _load_manifest(root, warnings)
    documents = _load_linked_records(root, "document", sources, warnings)
    questions = _load_linked_records(root, "question", sources, warnings)
    target_records = {record["id"]: record for record in [*documents, *questions]}
    reviews = _load_review_records(root, target_records, warnings)
    source_phases, phase_status_counts = _load_phase_reports(root, sources, warnings)
    _load_pipeline_fallback_issues(root, sources, source_phases, warnings)

    documents_by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    questions_by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for document in documents:
        documents_by_source[document["source_id"]].append(document)
    for question in questions:
        questions_by_source[question["source_id"]].append(question)

    # 题目的 pending 状态可能由来源/文档整体进入待审而传播。只有来源或关联
    # document 已经待审时才归类为“继承状态”；否则仍按题目自身待审处理。题目
    # 自身的直接 issues 始终优先，绝不会因状态继承而从强制复核中消失。
    for source_id, linked_questions in questions_by_source.items():
        source = sources[source_id]
        source_or_document_pending = source["status"] == "pending_manual_review" or any(
            bool(document.get("is_pending_manual_review"))
            for document in documents_by_source.get(source_id, [])
        )
        for question in linked_questions:
            inherited_status = bool(question.get("is_pending_manual_review")) and source_or_document_pending
            direct_pending = bool(question.get("is_pending_manual_review")) and not inherited_status
            has_direct_review_signal = bool(question.get("direct_issues")) or direct_pending
            has_inherited_source_signal = bool(
                question.get("inherited_source_review_issues")
            ) or inherited_status
            question["inherited_source_review_status"] = inherited_status
            question["direct_pending_manual_review"] = direct_pending
            question["has_direct_review_signal"] = has_direct_review_signal
            question["only_inherited_source_review_signal"] = (
                has_inherited_source_signal and not has_direct_review_signal
            )

    source_summaries: dict[str, dict[str, Any]] = {}
    for source_id, source in sources.items():
        linked_documents = documents_by_source.get(source_id, [])
        linked_questions = questions_by_source.get(source_id, [])
        phase_data = source_phases.get(source_id, {})
        issues = list(source["exceptions"])
        issues.extend(phase_data.get("issues", []))
        for document in linked_documents:
            issues.extend(document["issues"])
        for question in linked_questions:
            # 避免一个传播到所有题目的来源级提示重新被汇总为来源的“新异常”。
            # 题目本身的缺答案、公式、选项等直接信号仍会提升该来源的核对优先级。
            issues.extend(question["direct_issues"])
        has_phase_success = any(
            status == "success"
            for key, statuses in phase_data.items()
            if key.endswith("_status")
            for status in statuses
        )
        source_state_mismatch = (
            (source["status"] == "discovered" and (bool(linked_documents) or has_phase_success))
            or (
                source["status"] not in {"discovered", "blocked"}
                and not linked_documents
            )
        )
        if source_state_mismatch:
            issues.append("来源清单状态与已读取产物或阶段日志不一致，需同步处理状态")
        unique_issues = _normalise_strings(issues)
        conservative_unsplit_blocks = _conservative_unsplit_block_count(
            phase_data.get("issues", [])
        )
        has_failure = source["status"] == "blocked" or _has_failed_phase(phase_data) or any(
            document["status"] == "blocked" for document in linked_documents
        )
        has_document = bool(linked_documents)
        pending = source["status"] == "pending_manual_review" or any(
            document["status"] == "pending_manual_review" for document in linked_documents
        ) or any(
            question["status"] == "pending_manual_review"
            or question.get("review_status") == "pending_manual_review"
            for question in linked_questions
        )
        if has_failure:
            processing_state = "failed"
        elif has_document:
            processing_state = "successful"
        else:
            processing_state = "unprocessed"
        source_summaries[source_id] = {
            "source_id": source_id,
            "profile": source["profile"],
            "source_relative_path": source["relative_path"],
            "manifest_status": source["status"],
            "source_state_mismatch": source_state_mismatch,
            "processing_state": processing_state,
            "has_automatic_review_marker": bool(unique_issues),
            "conservative_unsplit_blocks": conservative_unsplit_blocks,
            # 兼容复核队列的既有判断；报告不再把这类综合状态称为“异常”。
            "has_exception": bool(unique_issues) or has_failure,
            "pending_manual_review": pending,
            "issues": unique_issues,
            "document_count": len(linked_documents),
            "question_count": len(linked_questions),
        }

    return {
        "root": root,
        "manifest_sha256": manifest_sha256,
        "sources": sources,
        "documents": documents,
        "questions": questions,
        "reviews": reviews,
        "source_summaries": source_summaries,
        "source_phases": source_phases,
        "phase_status_counts": phase_status_counts,
        "source_manifest_status": _source_manifest_status_counter(sources),
        "warnings": _normalise_strings(warnings),
        "record_counts": {
            "documents": _status_counter(documents, PROFILE_ORDER, kind="document"),
            "questions": _status_counter(questions, PROFILE_ORDER, kind="question"),
            "reviews": _review_counter(reviews),
        },
    }


def source_processing_summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    """按资料类型汇总处理进度与自动核对标记。

    ``automatic_review_marked`` 是来源数，和“成功”可重叠；
    ``conservative_unsplit_blocks`` 是未猜测建题的编号区块数，和来源数无关。
    """
    summaries = snapshot["source_summaries"]
    result: dict[str, Any] = {"total": {}, "by_profile": {}}
    for profile in PROFILE_ORDER:
        current = [
            summary
            for summary in summaries.values()
            if summary["profile"] == profile
        ]
        result["by_profile"][profile] = {
            "expected": len(current),
            "successful": sum(summary["processing_state"] == "successful" for summary in current),
            "failed": sum(summary["processing_state"] == "failed" for summary in current),
            "unprocessed": sum(summary["processing_state"] == "unprocessed" for summary in current),
            "automatic_review_marked": sum(
                bool(summary["has_automatic_review_marker"]) for summary in current
            ),
            "conservative_unsplit_blocks": sum(
                int(summary["conservative_unsplit_blocks"]) for summary in current
            ),
            "conservative_unsplit_sources": sum(
                int(summary["conservative_unsplit_blocks"]) > 0 for summary in current
            ),
            "pending_manual_review": sum(bool(summary["pending_manual_review"]) for summary in current),
            "source_state_mismatch": sum(bool(summary["source_state_mismatch"]) for summary in current),
        }
    # ``total`` 使用不嵌套 profile 的形式，方便命令和报告直接读取。
    result["total"] = {
        "expected": len(summaries),
        "successful": sum(summary["processing_state"] == "successful" for summary in summaries.values()),
        "failed": sum(summary["processing_state"] == "failed" for summary in summaries.values()),
        "unprocessed": sum(summary["processing_state"] == "unprocessed" for summary in summaries.values()),
        "automatic_review_marked": sum(
            bool(summary["has_automatic_review_marker"]) for summary in summaries.values()
        ),
        "conservative_unsplit_blocks": sum(
            int(summary["conservative_unsplit_blocks"]) for summary in summaries.values()
        ),
        "conservative_unsplit_sources": sum(
            int(summary["conservative_unsplit_blocks"]) > 0 for summary in summaries.values()
        ),
        "pending_manual_review": sum(bool(summary["pending_manual_review"]) for summary in summaries.values()),
        "source_state_mismatch": sum(
            bool(summary["source_state_mismatch"]) for summary in summaries.values()
        ),
    }
    return result
