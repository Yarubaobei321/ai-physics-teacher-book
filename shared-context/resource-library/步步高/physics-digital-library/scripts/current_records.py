#!/usr/bin/env python3
"""解析“当前可用”的结构化记录，阻断过期或孤儿产物。

``sources/sources.jsonl`` 只确认一份原始 Word 的身份；转换和结构化阶段是否仍然
对应这份 Word，则由同一 ``source_id`` 的阶段报告确认。这个模块把两者收敛成唯一
的可索引清单：索引器不再扫描整个 ``questions/`` 等目录，而只能读取这里明确允许
的记录。

报告尚未产生时，来源仍可保留在来源索引中；但任何已落盘的结构化 JSON 都必须被
该来源当前的成功报告声明。失败报告可保留自己的 ``blocked`` document 作为可追溯
处理历史，但绝不会把它或旧题目送进检索索引。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from library_common import (  # noqa: E402
    LIBRARY_ROOT,
    PipelineError,
    document_id_for,
    is_safe_relative_path,
    safe_library_root,
    source_short_for,
)
from source_state import SourceStateError, read_source_manifest  # noqa: E402


INDEX_KINDS = ("document", "question", "knowledge", "model")
ALL_RECORD_KINDS = (*INDEX_KINDS, "review")
RECORD_DIRECTORIES = {
    "document": "records/documents",
    "question": "questions",
    "knowledge": "knowledge",
    "model": "models",
    "review": "reviews",
}
SOURCE_ID_RE = re.compile(r"^src\.bbg\.([0-9a-f]{64})$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REVIEW_ID_RE = re.compile(r"^review\.bbg\.[a-z0-9][a-z0-9._-]*$")
RELEASE_ID_RE = re.compile(r"^release\.bbg\.[a-z0-9][a-z0-9._-]*$")
ADMISSION_ID_RE = re.compile(r"^admission\.bbg\.[a-z0-9][a-z0-9._-]*$")
STRUCTURED_SOURCE_STATUSES = frozenset(
    {"ai_structured", "pending_manual_review", "reviewed", "published"}
)
REVIEW_DECISIONS = frozenset({"approved", "needs_changes", "rejected", "blocked"})
FINAL_REVIEW_STATUSES = frozenset({"reviewed", "published"})
REVIEW_STATUSES = frozenset(
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
REVIEW_RECORD_FIELDS = frozenset(
    {
        "id",
        "relative_path",
        "status",
        "target_id",
        "target_relative_path",
        "reviewer",
        "decision",
        "summary",
        "issues",
        "resolved_issues",
    }
)
RELEASE_AUDIT_FIELDS = frozenset(
    {
        "id",
        "relative_path",
        "created_at",
        "source_id",
        "source_sha256",
        "source_relative_path",
        "previous_status",
        "status",
        "reviewer",
        "decision",
        "summary",
        "manifest_sha256",
        "manifest_exceptions_before",
        "resolved_exceptions",
        "manifest_exceptions_after",
        "target_reviews",
    }
)
ADMISSION_AUDIT_FIELDS = frozenset(
    {
        "id",
        "relative_path",
        "created_at",
        "source_id",
        "source_sha256",
        "source_relative_path",
        "previous_status",
        "status",
        "operator",
        "summary",
        "manifest_sha256",
        "target_records",
    }
)
RELEASE_AUDIT_DIRECTORY = "reports/source-releases"
RELEASE_AUDIT_PREFIX = f"{RELEASE_AUDIT_DIRECTORY}/"
ADMISSION_AUDIT_DIRECTORY = "reports/review-admissions"
ADMISSION_AUDIT_PREFIX = f"{ADMISSION_AUDIT_DIRECTORY}/"


class CurrentRecordsError(RuntimeError):
    """当前记录无法作为受信任检索输入时抛出。"""


@dataclass
class CurrentRecordResolution:
    """解析结果。

    ``records`` 只含可安全索引的当前记录；``declared_records`` 还包含失败转换报告
    所声明的 document，供全量校验保留处理历史。``errors`` 非空时，索引器必须拒绝
    替换旧 SQLite 索引。
    """

    root: Path
    manifest_sha256: str | None = None
    sources: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    records: dict[str, list[tuple[str, dict[str, Any]]]] = field(
        default_factory=lambda: {kind: [] for kind in ALL_RECORD_KINDS}
    )
    declared_records: dict[str, list[tuple[str, dict[str, Any]]]] = field(
        default_factory=lambda: {kind: [] for kind in ALL_RECORD_KINDS}
    )
    release_audits: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    review_admissions: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _SourcePaths:
    source_id: str
    source_short: str
    document_id: str
    markdown: str
    document: str
    conversion_report: str
    structure_report: str


def _add_error(resolution: CurrentRecordResolution, message: str) -> None:
    if message not in resolution.errors:
        resolution.errors.append(message)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _source_paths(source_id: str) -> _SourcePaths:
    source_short = source_short_for(source_id)
    document_id = document_id_for(source_id)
    return _SourcePaths(
        source_id=source_id,
        source_short=source_short,
        document_id=document_id,
        markdown=f"records/documents/{document_id}.md",
        document=f"records/documents/{document_id}.json",
        conversion_report=f"reports/conversion/{source_short}.json",
        structure_report=f"reports/structure/{source_short}.json",
    )


def _safe_regular_file(
    resolution: CurrentRecordResolution,
    relative_path: str,
    *,
    label: str,
    required: bool,
) -> Path | None:
    """安全读取资料库内的普通文件，拒绝任一级软链接。"""
    root = resolution.root
    if not is_safe_relative_path(relative_path):
        _add_error(resolution, f"{label} 路径不安全：{relative_path!r}")
        return None
    target = root.joinpath(*PurePosixPath(relative_path).parts)
    current = root
    parts = target.relative_to(root).parts
    for index, component in enumerate(parts):
        current = current / component
        if current.is_symlink():
            _add_error(resolution, f"{label} 不能是符号链接或位于符号链接目录：{relative_path}")
            return None
        if index < len(parts) - 1:
            if not current.exists():
                if required:
                    _add_error(resolution, f"缺少 {label}：{relative_path}")
                return None
            if not current.is_dir():
                _add_error(resolution, f"{label} 父路径不是目录：{relative_path}")
                return None
    if not target.exists():
        if required:
            _add_error(resolution, f"缺少 {label}：{relative_path}")
        return None
    if not target.is_file():
        _add_error(resolution, f"{label} 必须是普通文件：{relative_path}")
        return None
    try:
        resolved = target.resolve(strict=True)
    except OSError as error:
        _add_error(resolution, f"无法解析 {label}：{relative_path}（{error}）")
        return None
    if not _is_within(resolved, root):
        _add_error(resolution, f"{label} 越出资料库根：{relative_path}")
        return None
    return target


def _read_json_file(
    resolution: CurrentRecordResolution,
    relative_path: str,
    *,
    label: str,
    required: bool,
) -> dict[str, Any] | None:
    path = _safe_regular_file(resolution, relative_path, label=label, required=required)
    if path is None:
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        _add_error(resolution, f"{label} 不是可读取的 JSON 对象：{relative_path}（{error}）")
        return None
    if not isinstance(value, dict):
        _add_error(resolution, f"{label} 必须是 JSON 对象：{relative_path}")
        return None
    return value


def _require_report_identity(
    resolution: CurrentRecordResolution,
    report: dict[str, Any],
    source: dict[str, Any],
    *,
    label: str,
) -> bool:
    valid = True
    expected = {
        "source_id": source["id"],
        "source_relative_path": source["relative_path"],
        "input_sha256": source["sha256"],
    }
    for field, value in expected.items():
        if report.get(field) != value:
            _add_error(resolution, f"{label} 的 {field} 与 sources.jsonl 不一致")
            valid = False
    return valid


def _require_report_paths(
    resolution: CurrentRecordResolution,
    report: dict[str, Any],
    expected: dict[str, str],
    *,
    label: str,
) -> bool:
    paths = report.get("paths")
    if not isinstance(paths, dict):
        _add_error(resolution, f"{label} 缺少对象 paths；旧报告不能作为当前索引依据")
        return False
    valid = True
    unexpected = sorted(set(paths) - set(expected))
    if unexpected:
        _add_error(resolution, f"{label} 的 paths 不允许额外字段：{', '.join(unexpected)}")
        valid = False
    for field, value in expected.items():
        if paths.get(field) != value:
            _add_error(resolution, f"{label} 的 paths.{field} 声明路径不一致")
            valid = False
    return valid


def _path_list(
    resolution: CurrentRecordResolution,
    report: dict[str, Any],
    field: str,
    *,
    prefix: str,
    label: str,
) -> tuple[list[str], bool]:
    value = report.get(field)
    if not isinstance(value, list):
        _add_error(resolution, f"{label} 缺少数组 {field}；旧报告不能作为当前索引依据")
        return [], False
    valid = True
    paths: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not is_safe_relative_path(item) or not item.startswith(prefix):
            _add_error(resolution, f"{label} 的 {field}[{index}] 路径不安全或目录不符")
            valid = False
            continue
        if item in seen:
            _add_error(resolution, f"{label} 的 {field} 有重复声明：{item}")
            valid = False
            continue
        seen.add(item)
        paths.append(item)
    return paths, valid


def _asset_paths(
    resolution: CurrentRecordResolution,
    report: dict[str, Any],
    source_id: str,
    *,
    label: str,
) -> tuple[list[str], bool]:
    paths, valid = _path_list(
        resolution, report, "asset_paths", prefix="assets/", label=label
    )
    approved_prefixes = (
        f"assets/original/{source_id}/",
        f"assets/derived/{source_id}/",
    )
    for path in paths:
        if not path.startswith(approved_prefixes):
            _add_error(resolution, f"{label} 的 asset_paths 不属于当前 source：{path}")
            valid = False
            continue
        if _safe_regular_file(resolution, path, label="声明的媒体资产", required=True) is None:
            valid = False
    return paths, valid


def _record_matches_file(
    resolution: CurrentRecordResolution,
    record: dict[str, Any],
    relative_path: str,
    *,
    kind: str,
) -> bool:
    if record.get("relative_path") != relative_path:
        _add_error(resolution, f"{kind} 记录声明路径不一致：{relative_path}")
        return False
    return True


def _validate_document(
    resolution: CurrentRecordResolution,
    source: dict[str, Any],
    paths: _SourcePaths,
    report_assets: list[str],
    *,
    conversion_success: bool,
) -> tuple[dict[str, Any] | None, bool]:
    document = _read_json_file(
        resolution,
        paths.document,
        label="document 记录",
        required=conversion_success,
    )
    if document is None:
        return None, not conversion_success
    valid = _record_matches_file(
        resolution, document, paths.document, kind="document"
    )
    expected = {
        "id": paths.document_id,
        "source_id": source["id"],
        "source_relative_path": source["relative_path"],
        "content_path": paths.markdown,
        "title": source["title"],
        "extraction_profile": source["profile"],
    }
    for field, expected_value in expected.items():
        if document.get(field) != expected_value:
            _add_error(resolution, f"document 记录的 {field} 与当前来源声明不一致：{paths.document}")
            valid = False
    asset_paths = document.get("asset_paths")
    if not isinstance(asset_paths, list) or asset_paths != report_assets:
        _add_error(resolution, f"document 记录的 asset_paths 与转换报告声明不一致：{paths.document}")
        valid = False
    if conversion_success and _safe_regular_file(
        resolution, paths.markdown, label="Markdown", required=True
    ) is None:
        valid = False
    return document, valid


def _validate_question(
    resolution: CurrentRecordResolution,
    record: dict[str, Any],
    relative_path: str,
    source: dict[str, Any],
    asset_paths: set[str],
) -> bool:
    valid = _record_matches_file(resolution, record, relative_path, kind="question")
    source_id = source["id"]
    question_id = record.get("id")
    if not isinstance(question_id, str) or not question_id.startswith(f"q.{source_id}."):
        _add_error(resolution, f"question 记录未绑定当前 source_id：{relative_path}")
        valid = False
    if record.get("source_id") != source_id:
        _add_error(resolution, f"question 记录的 source_id 与报告不一致：{relative_path}")
        valid = False
    source_location = record.get("source_location")
    if not isinstance(source_location, dict) or source_location.get("relative_path") != source["relative_path"]:
        _add_error(resolution, f"question 记录的 source_location.relative_path 与来源不一致：{relative_path}")
        valid = False
    figures = record.get("figures")
    if not isinstance(figures, list):
        _add_error(resolution, f"question 记录的 figures 必须是数组：{relative_path}")
        return False
    for index, figure in enumerate(figures):
        if not isinstance(figure, str) or figure not in asset_paths:
            _add_error(resolution, f"question 记录的 figures[{index}] 未在转换报告声明：{relative_path}")
            valid = False
            continue
        if _safe_regular_file(resolution, figure, label="题目图片", required=True) is None:
            valid = False
    return valid


def _validate_knowledge_or_model(
    resolution: CurrentRecordResolution,
    record: dict[str, Any],
    relative_path: str,
    source: dict[str, Any],
    *,
    kind: str,
) -> bool:
    valid = _record_matches_file(resolution, record, relative_path, kind=kind)
    source_ids = record.get("source_ids")
    if not isinstance(source_ids, list) or source["id"] not in source_ids:
        _add_error(resolution, f"{kind} 记录的 source_ids 未包含当前来源：{relative_path}")
        valid = False
    return valid


def _scan_json_files(
    resolution: CurrentRecordResolution,
    directory: str,
    *,
    label: str,
) -> list[str]:
    """在指定记录目录中递归列出普通 JSON，显式拒绝所有软链接。"""
    root = resolution.root
    if not is_safe_relative_path(directory):
        _add_error(resolution, f"{label} 目录路径不安全：{directory}")
        return []
    base = root.joinpath(*PurePosixPath(directory).parts)
    if base.is_symlink():
        _add_error(resolution, f"{label} 目录不能是符号链接：{directory}")
        return []
    if not base.exists():
        return []
    if not base.is_dir():
        _add_error(resolution, f"{label} 必须是目录：{directory}")
        return []
    paths: list[str] = []

    def onerror(error: OSError) -> None:
        _add_error(resolution, f"无法扫描 {label}：{error}")

    for raw_current, directories, filenames in os.walk(base, followlinks=False, onerror=onerror):
        current = Path(raw_current)
        for name in list(directories):
            candidate = current / name
            if candidate.is_symlink():
                _add_error(resolution, f"{label} 内不能有符号链接目录：{candidate.relative_to(root).as_posix()}")
                directories.remove(name)
        for name in filenames:
            candidate = current / name
            relative = candidate.relative_to(root).as_posix()
            if candidate.is_symlink():
                _add_error(resolution, f"{label} 内不能有符号链接文件：{relative}")
                continue
            if candidate.suffix.lower() != ".json":
                continue
            if not candidate.is_file():
                _add_error(resolution, f"{label} 中的记录必须是普通文件：{relative}")
                continue
            paths.append(relative)
    return sorted(paths)


def _check_report_directory(
    resolution: CurrentRecordResolution,
    directory: str,
    expected_paths: set[str],
    *,
    label: str,
) -> None:
    for relative_path in _scan_json_files(resolution, directory, label=label):
        if relative_path not in expected_paths:
            _add_error(resolution, f"孤儿 {label}：{relative_path}")


def _register_declared(
    resolution: CurrentRecordResolution,
    kind: str,
    relative_path: str,
    record: dict[str, Any],
    *,
    current: bool,
) -> None:
    declared = resolution.declared_records[kind]
    if any(path == relative_path for path, _ in declared):
        _add_error(resolution, f"{kind} 被多个来源报告重复声明：{relative_path}")
        return
    declared.append((relative_path, record))
    if current:
        resolution.records[kind].append((relative_path, record))


def _validate_structure_report(
    resolution: CurrentRecordResolution,
    report: dict[str, Any],
    source: dict[str, Any],
    paths: _SourcePaths,
    *,
    conversion_is_current: bool,
    conversion_assets: set[str],
) -> bool:
    label = f"结构化报告 {paths.structure_report}"
    identity_valid = _require_report_identity(resolution, report, source, label=label)
    paths_valid = _require_report_paths(
        resolution,
        report,
        {
            "markdown": paths.markdown,
            "document": paths.document,
            "structure_log": paths.structure_report,
        },
        label=label,
    )
    status = report.get("status")
    if status not in {"success", "failed"}:
        _add_error(resolution, f"{label} 的 status 必须是 success 或 failed")
        return False
    if not identity_valid or not paths_valid:
        return False
    question_paths, question_paths_valid = _path_list(
        resolution, report, "question_paths", prefix="questions/", label=label
    )
    knowledge_paths, knowledge_paths_valid = _path_list(
        resolution, report, "knowledge_paths", prefix="knowledge/", label=label
    )
    model_paths, model_paths_valid = _path_list(
        resolution, report, "model_paths", prefix="models/", label=label
    )
    counts = report.get("counts")
    if not isinstance(counts, dict):
        _add_error(resolution, f"{label} 缺少对象 counts；旧报告不能作为当前索引依据")
        return False
    for field, paths_for_field in (
        ("questions", question_paths),
        ("knowledge", knowledge_paths),
        ("models", model_paths),
    ):
        if counts.get(field) != len(paths_for_field):
            _add_error(resolution, f"{label} 的 counts.{field} 与声明路径数量不一致")
    if status == "failed":
        if question_paths or knowledge_paths or model_paths:
            _add_error(resolution, f"失败的 {label} 不能声明当前题目、知识点或模型记录")
        return False
    if not conversion_is_current:
        _add_error(resolution, f"{label} 对应的转换报告不是当前成功产物")
        return False
    markdown_path = _safe_regular_file(resolution, paths.markdown, label="Markdown", required=True)
    markdown_sha256 = report.get("markdown_sha256")
    if not isinstance(markdown_sha256, str) or not SHA256_RE.fullmatch(markdown_sha256):
        _add_error(resolution, f"{label} 缺少有效 markdown_sha256；旧报告不能作为当前索引依据")
        return False
    if markdown_path is None:
        return False
    try:
        actual_markdown_sha256 = hashlib.sha256(markdown_path.read_bytes()).hexdigest()
    except OSError as error:
        _add_error(resolution, f"无法计算 Markdown 哈希：{paths.markdown}（{error}）")
        return False
    if actual_markdown_sha256 != markdown_sha256:
        _add_error(resolution, f"{label} 的 markdown_sha256 已过期，不能索引旧结构化记录")
        return False
    if not (question_paths_valid and knowledge_paths_valid and model_paths_valid):
        return False

    local_records: list[tuple[str, str, dict[str, Any]]] = []
    for kind, declared_paths in (
        ("question", question_paths),
        ("knowledge", knowledge_paths),
        ("model", model_paths),
    ):
        for relative_path in declared_paths:
            record = _read_json_file(
                resolution,
                relative_path,
                label=f"{kind} 记录",
                required=True,
            )
            if record is None:
                continue
            if kind == "question":
                valid = _validate_question(
                    resolution, record, relative_path, source, conversion_assets
                )
            else:
                valid = _validate_knowledge_or_model(
                    resolution, record, relative_path, source, kind=kind
                )
            if valid:
                local_records.append((kind, relative_path, record))
    expected_count = len(question_paths) + len(knowledge_paths) + len(model_paths)
    if len(local_records) != expected_count:
        return False
    for kind, relative_path, record in local_records:
        _register_declared(resolution, kind, relative_path, record, current=True)
    return True


def _report_output_paths(report: dict[str, Any] | None, *, include_assets: bool = False) -> set[str]:
    """抽取阶段报告明确声明的受控输出路径。

    只把安全的字符串放入集合；报告本身的完整性会由调用处的身份/路径校验另行报错。
    """
    if not isinstance(report, dict):
        return set()
    result: set[str] = set()
    paths = report.get("paths")
    if isinstance(paths, dict):
        for value in paths.values():
            if isinstance(value, str) and is_safe_relative_path(value):
                result.add(value)
    for field in ("question_paths", "knowledge_paths", "model_paths"):
        values = report.get(field)
        if isinstance(values, list):
            result.update(
                value
                for value in values
                if isinstance(value, str) and is_safe_relative_path(value)
            )
    if include_assets:
        values = report.get("asset_paths")
        if isinstance(values, list):
            result.update(
                value
                for value in values
                if isinstance(value, str) and is_safe_relative_path(value)
            )
    return result


def _remove_source_from_current_records(
    resolution: CurrentRecordResolution, source_id: str
) -> None:
    """把不满足 manifest 状态的记录移出索引候选，但保留 declared 审计轨迹。"""
    for kind in INDEX_KINDS:
        filtered: list[tuple[str, dict[str, Any]]] = []
        for relative_path, record in resolution.records[kind]:
            if kind in {"document", "question"}:
                belongs_to_source = record.get("source_id") == source_id
            else:
                source_ids = record.get("source_ids")
                belongs_to_source = isinstance(source_ids, list) and source_id in source_ids
            if not belongs_to_source:
                filtered.append((relative_path, record))
        resolution.records[kind] = filtered


def _validate_manifest_stage(
    resolution: CurrentRecordResolution,
    source: dict[str, Any],
    conversion: dict[str, Any] | None,
    structure: dict[str, Any] | None,
    *,
    conversion_is_current: bool,
    structure_is_current: bool,
) -> bool:
    """确保清单状态和 output_paths 真正描述当前阶段产物。

    这一步不根据目录扫描补全任何路径：产物必须同时由对应阶段报告和 canonical
    manifest 明确声明，才能进入当前记录集合。
    """
    source_id = str(source["id"])
    status = source.get("status")
    output_paths = source.get("output_paths")
    if not isinstance(output_paths, dict):
        _add_error(resolution, f"来源 {source_id} 的 output_paths 必须是对象")
        return False
    actual_output_paths = {
        value for value in output_paths.values() if isinstance(value, str)
    }
    expected_output_paths = (
        _report_output_paths(conversion, include_assets=True)
        | _report_output_paths(structure, include_assets=False)
    )
    if actual_output_paths != expected_output_paths:
        missing = sorted(expected_output_paths - actual_output_paths)
        extra = sorted(actual_output_paths - expected_output_paths)
        detail: list[str] = []
        if missing:
            detail.append("缺少 " + ", ".join(missing[:3]))
        if extra:
            detail.append("多出 " + ", ".join(extra[:3]))
        _add_error(
            resolution,
            f"来源 {source_id} 的 output_paths 与阶段报告声明不一致"
            + ("：" + "；".join(detail) if detail else ""),
        )

    conversion_status = conversion.get("status") if isinstance(conversion, dict) else None
    structure_status = structure.get("status") if isinstance(structure, dict) else None
    stage_valid = True
    if status == "discovered":
        if conversion is not None or structure is not None:
            _add_error(resolution, f"来源 {source_id} 仍为 discovered，却已有阶段报告")
            stage_valid = False
        if actual_output_paths:
            _add_error(resolution, f"来源 {source_id} 为 discovered 时 output_paths 必须为空")
            stage_valid = False
    elif status == "raw_extracted":
        if conversion_status != "success" or not conversion_is_current:
            _add_error(resolution, f"来源 {source_id} 状态 raw_extracted 必须有当前成功转换报告")
            stage_valid = False
        if structure is not None:
            _add_error(resolution, f"来源 {source_id} 状态 raw_extracted 不应已有结构化报告")
            stage_valid = False
    elif status in STRUCTURED_SOURCE_STATUSES:
        if conversion_status != "success" or not conversion_is_current:
            _add_error(resolution, f"来源 {source_id} 状态 {status} 必须有当前成功转换报告")
            stage_valid = False
        if structure_status != "success" or not structure_is_current:
            _add_error(resolution, f"来源 {source_id} 状态 {status} 必须有当前成功结构化报告")
            stage_valid = False
    elif status == "blocked":
        # blocked 可能来自转换/结构化失败，也可能是人工阻断；无论哪种情况都不纳入
        # 检索索引。若已有阶段报告，output_paths 仍须准确反映它们，供问题定位。
        stage_valid = False
    else:
        _add_error(resolution, f"来源 {source_id} 的 status 非法：{status!r}")
        stage_valid = False
    if actual_output_paths != expected_output_paths:
        stage_valid = False
    return stage_valid


def _validate_cross_references(resolution: CurrentRecordResolution) -> None:
    knowledge_ids = {
        str(record.get("id"))
        for _, record in resolution.records["knowledge"]
        if isinstance(record.get("id"), str)
    }
    model_ids = {
        str(record.get("id"))
        for _, record in resolution.records["model"]
        if isinstance(record.get("id"), str)
    }
    for relative_path, question in resolution.records["question"]:
        for field, known in (("knowledge_ids", knowledge_ids), ("model_ids", model_ids)):
            value = question.get(field)
            if value is None and field == "model_ids":
                continue
            if not isinstance(value, list):
                _add_error(resolution, f"question 记录的 {field} 必须是数组或 null：{relative_path}")
                continue
            for item in value:
                if not isinstance(item, str) or item not in known:
                    _add_error(resolution, f"question 记录引用了未声明的 {field}：{relative_path}")
    for relative_path, model in resolution.records["model"]:
        value = model.get("knowledge_ids")
        if not isinstance(value, list):
            _add_error(resolution, f"model 记录的 knowledge_ids 必须是数组：{relative_path}")
            continue
        for item in value:
            if not isinstance(item, str) or item not in knowledge_ids:
                _add_error(resolution, f"model 记录引用了未声明的 knowledge_id：{relative_path}")


def _check_duplicate_ids(resolution: CurrentRecordResolution) -> None:
    seen: dict[str, str] = {}
    for location, source in resolution.sources:
        source_id = source.get("id")
        if isinstance(source_id, str):
            seen[source_id] = location
    for kind in ALL_RECORD_KINDS:
        for relative_path, record in resolution.declared_records[kind]:
            record_id = record.get("id")
            if not isinstance(record_id, str):
                continue
            previous = seen.get(record_id)
            if previous is not None:
                _add_error(resolution, f"重复 ID {record_id!r}：{relative_path} 与 {previous}")
            else:
                seen[record_id] = relative_path


def _check_orphan_records(
    resolution: CurrentRecordResolution,
) -> None:
    for kind in INDEX_KINDS:
        declared_paths = {
            relative_path for relative_path, _ in resolution.declared_records[kind]
        }
        for relative_path in _scan_json_files(
            resolution, RECORD_DIRECTORIES[kind], label=f"{kind} 记录目录"
        ):
            if relative_path not in declared_paths:
                _add_error(resolution, f"孤儿 {kind} 记录：{relative_path}")
    # review 目前由人工建立，不经过 structure report；仍然拒绝链接并让校验器读取它。
    for relative_path in _scan_json_files(
        resolution, RECORD_DIRECTORIES["review"], label="review 记录目录"
    ):
        record = _read_json_file(
            resolution, relative_path, label="review 记录", required=True
        )
        if record is not None:
            _register_declared(resolution, "review", relative_path, record, current=False)


def _validate_review_records(resolution: CurrentRecordResolution) -> None:
    """验证正式 review 与目标记录的关联及最终状态凭据。

    review 是人工建立的独立审计记录，因此旧的“未通过”结论可以在后续修复后保留。
    这里不要求每一条历史 review 都等于目标的当前状态；只要求每个当前
    reviewed/published document 或 question 至少有一条同状态的 approved review。
    这样手工直接改状态不会被索引器当作有效发布结果。
    """
    targets: dict[str, tuple[str, str, dict[str, Any]]] = {}
    for kind in ("document", "question"):
        for relative_path, record in resolution.declared_records[kind]:
            target_id = record.get("id")
            if isinstance(target_id, str) and target_id not in targets:
                targets[target_id] = (kind, relative_path, record)

    approved_statuses: set[tuple[str, str]] = set()
    approved_reviews: list[tuple[str, str, str]] = []
    # 一个目标可能先通过、后因新发现的问题回到待审。保留早先 approved
    # review 是审计要求；只要有一条合格的退回复核记录，就允许该历史状态。
    regressed_targets: set[str] = set()
    for relative_path, review in resolution.declared_records["review"]:
        unexpected = sorted(set(review) - REVIEW_RECORD_FIELDS)
        if unexpected:
            _add_error(resolution, f"review 不允许额外字段：{relative_path}（{', '.join(unexpected)}）")
            continue
        review_id = review.get("id")
        recorded_relative_path = review.get("relative_path")
        target_id = review.get("target_id")
        target_path = review.get("target_relative_path")
        decision = review.get("decision")
        status = review.get("status")
        issues = review.get("issues")
        resolved_issues = review.get("resolved_issues", [])
        reviewer = review.get("reviewer")
        summary = review.get("summary")
        if not isinstance(review_id, str) or not REVIEW_ID_RE.fullmatch(review_id):
            _add_error(resolution, f"review ID 格式无效：{relative_path}")
            continue
        if recorded_relative_path != relative_path:
            _add_error(resolution, f"review 的 relative_path 与文件位置不一致：{relative_path}")
            continue
        if not isinstance(reviewer, str) or not reviewer.strip():
            _add_error(resolution, f"review 的 reviewer 不能为空：{relative_path}")
            continue
        if not isinstance(summary, str) or not summary.strip():
            _add_error(resolution, f"review 的 summary 不能为空：{relative_path}")
            continue
        if not isinstance(target_id, str) or target_id not in targets:
            _add_error(resolution, f"review 目标不存在：{relative_path}")
            continue
        _, expected_path, _ = targets[target_id]
        if target_path != expected_path:
            _add_error(resolution, f"review 的 target_relative_path 与目标不一致：{relative_path}")
        if decision not in REVIEW_DECISIONS:
            _add_error(resolution, f"review 的 decision 非法：{relative_path}")
            continue
        if status not in REVIEW_STATUSES:
            _add_error(resolution, f"review 的 status 非法：{relative_path}")
            continue
        if not isinstance(issues, list) or any(not isinstance(issue, str) or not issue for issue in issues):
            _add_error(resolution, f"review 的 issues 必须是字符串数组：{relative_path}")
            continue
        if not isinstance(resolved_issues, list) or any(
            not isinstance(issue, str) or not issue for issue in resolved_issues
        ):
            _add_error(resolution, f"review 的 resolved_issues 必须是字符串数组：{relative_path}")
            continue
        if decision == "approved":
            if status not in FINAL_REVIEW_STATUSES:
                _add_error(resolution, f"approved review 必须为 reviewed 或 published：{relative_path}")
                continue
            if issues:
                _add_error(resolution, f"approved review 不能保留未解决 issues：{relative_path}")
                continue
            approved_statuses.add((target_id, str(status)))
            approved_reviews.append((target_id, str(status), relative_path))
        elif decision in {"needs_changes", "rejected"}:
            if resolved_issues:
                _add_error(resolution, f"needs_changes/rejected review 不能含 resolved_issues：{relative_path}")
            if status != "pending_manual_review" or not issues:
                _add_error(
                    resolution,
                    f"needs_changes/rejected review 必须为 pending_manual_review 且有 issues：{relative_path}",
                )
            else:
                regressed_targets.add(target_id)
        else:  # blocked
            if resolved_issues:
                _add_error(resolution, f"blocked review 不能含 resolved_issues：{relative_path}")
            if status != "blocked" or not issues:
                _add_error(resolution, f"blocked review 必须为 blocked 且有 issues：{relative_path}")

    for target_id, review_status, relative_path in approved_reviews:
        _, _, target_record = targets[target_id]
        current_target_status = target_record.get("status")
        allowed_target_statuses = (
            {"reviewed", "published", "blocked"}
            if review_status == "reviewed"
            else {"published", "blocked"}
        )
        if (
            current_target_status not in allowed_target_statuses
            and not (
                current_target_status == "pending_manual_review"
                and target_id in regressed_targets
            )
        ):
            _add_error(
                resolution,
                f"approved {review_status} review 与目标当前状态不一致：{relative_path}",
            )

    for target_id, (kind, relative_path, record) in targets.items():
        status = record.get("status")
        if kind == "question":
            review_status = record.get("review_status")
            if status in FINAL_REVIEW_STATUSES and review_status != status:
                _add_error(resolution, f"已审结 question 的 status/review_status 不一致：{relative_path}")
            if review_status in FINAL_REVIEW_STATUSES and status != review_status:
                _add_error(resolution, f"已审结 question 的 review_status/status 不一致：{relative_path}")
        if status in FINAL_REVIEW_STATUSES and (target_id, status) not in approved_statuses:
            _add_error(
                resolution,
                f"{status} 目标缺少同状态 approved review：{relative_path}",
            )


def _is_safe_admission_audit_path(value: object) -> bool:
    return (
        isinstance(value, str)
        and is_safe_relative_path(value)
        and value.startswith(ADMISSION_AUDIT_PREFIX)
        and value.endswith(".json")
    )


def _admission_audit_target_records(
    resolution: CurrentRecordResolution, source_id: str
) -> dict[str, tuple[str, str, dict[str, Any]]]:
    """返回来源当前 document/question，供转入待审审计交叉验证。"""
    result: dict[str, tuple[str, str, dict[str, Any]]] = {}
    for kind in ("document", "question"):
        for relative_path, record in resolution.records[kind]:
            if record.get("source_id") != source_id:
                continue
            target_id = record.get("id")
            if isinstance(target_id, str) and target_id not in result:
                result[target_id] = (kind, relative_path, record)
    return result


def _validate_review_admission_audit(
    resolution: CurrentRecordResolution,
    relative_path: str,
    audit: dict[str, Any],
    *,
    sources_by_id: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, Any]] | None:
    """验证转入待审审计，不把该动作误当作人工 review。"""
    label = f"转入待审审计 {relative_path}"
    unexpected = sorted(set(audit) - ADMISSION_AUDIT_FIELDS)
    missing = sorted(ADMISSION_AUDIT_FIELDS - set(audit))
    if unexpected or missing:
        details: list[str] = []
        if missing:
            details.append("缺少 " + ", ".join(missing))
        if unexpected:
            details.append("不允许额外字段 " + ", ".join(unexpected))
        _add_error(resolution, f"{label} 字段无效：" + "；".join(details))
        return None
    audit_id = audit.get("id")
    stored_path = audit.get("relative_path")
    if (
        not isinstance(audit_id, str)
        or not ADMISSION_ID_RE.fullmatch(audit_id)
        or stored_path != relative_path
        or not _is_safe_admission_audit_path(stored_path)
        or stored_path != f"{ADMISSION_AUDIT_PREFIX}{audit_id}.json"
    ):
        _add_error(resolution, f"{label} 的 ID 或 relative_path 无效")
        return None
    source_id = audit.get("source_id")
    source_sha256 = audit.get("source_sha256")
    source = sources_by_id.get(source_id) if isinstance(source_id, str) else None
    if (
        source is None
        or not isinstance(source_sha256, str)
        or not SHA256_RE.fullmatch(source_sha256)
        or source_id != f"src.bbg.{source_sha256}"
        or source.get("sha256") != source_sha256
        or audit.get("source_relative_path") != source.get("relative_path")
        or not isinstance(audit.get("source_relative_path"), str)
        or not is_safe_relative_path(audit.get("source_relative_path"))
        or not str(audit.get("source_relative_path")).startswith("raw/")
    ):
        _add_error(resolution, f"{label} 与当前来源身份或原始路径不一致")
        return None
    created_at = audit.get("created_at")
    if not isinstance(created_at, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", created_at):
        _add_error(resolution, f"{label} 的 created_at 必须是 UTC ISO 时间")
        return None
    if (
        audit.get("previous_status") != "ai_structured"
        or audit.get("status") != "pending_manual_review"
        or not isinstance(audit.get("operator"), str)
        or not audit["operator"].strip()
        or not isinstance(audit.get("summary"), str)
        or not audit["summary"].strip()
        or not isinstance(audit.get("manifest_sha256"), str)
        or not SHA256_RE.fullmatch(audit["manifest_sha256"])
    ):
        _add_error(resolution, f"{label} 的状态、操作人或 manifest 快照无效")
        return None
    targets = audit.get("target_records")
    if not isinstance(targets, list) or not targets:
        _add_error(resolution, f"{label} 必须保留 document 与当前 questions 的状态变更")
        return None
    # blocked 来源不属于当前可索引记录，旧 admission 审计仍应作为处理历史保留；
    # 只有仍在结构化状态链内的来源才需要与当前目标逐项绑定。
    bind_current_targets = source.get("status") in STRUCTURED_SOURCE_STATUSES
    current_targets = (
        _admission_audit_target_records(resolution, source_id) if bind_current_targets else {}
    )
    source_short = source_sha256[:16]
    seen_target_ids: set[str] = set()
    target_entries: dict[str, dict[str, Any]] = {}
    document_count = 0
    valid = True
    for sequence, entry in enumerate(targets, start=1):
        entry_label = f"{label} target_records[{sequence}]"
        if not isinstance(entry, dict) or set(entry) != {
            "target_id",
            "target_type",
            "target_relative_path",
            "previous_status",
            "status",
        }:
            _add_error(resolution, f"{entry_label} 字段无效")
            valid = False
            continue
        target_id = entry.get("target_id")
        target_type = entry.get("target_type")
        target_path = entry.get("target_relative_path")
        if not isinstance(target_id, str) or not target_id or target_id in seen_target_ids:
            _add_error(resolution, f"{entry_label} 的 target_id 无效或重复")
            valid = False
            continue
        seen_target_ids.add(target_id)
        if target_type == "document":
            expected_id = f"doc.bbg.{source_short}"
            expected_prefix = "records/documents/"
            document_count += 1
        elif target_type == "question":
            expected_id = None
            expected_prefix = "questions/"
        else:
            _add_error(resolution, f"{entry_label} 的 target_type 无效")
            valid = False
            continue
        if (
            (expected_id is not None and target_id != expected_id)
            or (target_type == "question" and not re.fullmatch(rf"q\.{re.escape(source_id)}\.\d{{3}}", target_id))
            or not isinstance(target_path, str)
            or not is_safe_relative_path(target_path)
            or not target_path.startswith(expected_prefix)
            or not target_path.endswith(".json")
            or entry.get("previous_status") != "ai_structured"
            or entry.get("status") != "pending_manual_review"
        ):
            _add_error(resolution, f"{entry_label} 的目标身份、路径或状态无效")
            valid = False
            continue
        if bind_current_targets:
            current_target = current_targets.get(target_id)
            if current_target is None or current_target[0] != target_type or current_target[1] != target_path:
                _add_error(resolution, f"{entry_label} 与当前来源目标路径或类型不一致")
                valid = False
                continue
            current_status = current_target[2].get("status")
            if source.get("status") != "ai_structured" and current_status == "ai_structured":
                _add_error(resolution, f"{entry_label} 已有转入待审审计但当前目标仍为 ai_structured")
                valid = False
            if target_type == "question" and current_status in {
                "pending_manual_review",
                "reviewed",
                "published",
                "blocked",
            } and current_target[2].get("review_status") != current_status:
                _add_error(resolution, f"{entry_label} 的当前 question status/review_status 不一致")
                valid = False
        target_entries[target_id] = dict(entry)
    if document_count != 1:
        _add_error(resolution, f"{label} 必须且只能包含一份 document 的状态变更")
        valid = False
    if bind_current_targets and set(target_entries) != set(current_targets):
        _add_error(resolution, f"{label} 未覆盖当前 document/全部 questions")
        valid = False
    if not valid:
        return None
    return source_id, {**audit, "_target_entries": target_entries}


def _validate_review_admission_audits(resolution: CurrentRecordResolution) -> None:
    """读取 admission 审计，并阻断无异常来源手工跳过待审入口。"""
    sources_by_id = {
        str(source.get("id")): source
        for _, source in resolution.sources
        if isinstance(source.get("id"), str)
    }
    valid_by_source: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for relative_path in _scan_json_files(
        resolution, ADMISSION_AUDIT_DIRECTORY, label="转入待审审计"
    ):
        audit = _read_json_file(
            resolution, relative_path, label="转入待审审计", required=True
        )
        if audit is None:
            continue
        parsed = _validate_review_admission_audit(
            resolution, relative_path, audit, sources_by_id=sources_by_id
        )
        if parsed is None:
            continue
        source_id, validated_audit = parsed
        resolution.review_admissions.append((relative_path, audit))
        valid_by_source.setdefault(source_id, []).append((relative_path, validated_audit))

    for source_id, source in sources_by_id.items():
        if source.get("status") != "pending_manual_review" or source.get("exceptions") != []:
            continue
        targets = _admission_audit_target_records(resolution, source_id)
        expected_target_ids = set(targets)
        matching_audits = [
            audit
            for _, audit in valid_by_source.get(source_id, [])
            if isinstance(audit.get("_target_entries"), dict)
            and set(audit["_target_entries"]) == expected_target_ids
        ]
        if not matching_audits:
            _add_error(
                resolution,
                f"待审且无 exceptions 的来源 {source_id} 缺少覆盖当前 document/全部 questions 的 ai_structured→pending_manual_review 转入待审审计",
            )


def _valid_nonempty_unique_strings(value: object) -> list[str] | None:
    """返回可用于正式审计的字符串数组；无效时返回 ``None``。"""
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        return None
    if len(value) != len(set(value)):
        return None
    return list(value)


def _is_safe_release_audit_path(value: object) -> bool:
    return (
        isinstance(value, str)
        and is_safe_relative_path(value)
        and value.startswith(RELEASE_AUDIT_PREFIX)
        and value.endswith(".json")
    )


def _is_safe_review_path(value: object) -> bool:
    return (
        isinstance(value, str)
        and is_safe_relative_path(value)
        and value.startswith("reviews/review.bbg.")
        and value.endswith(".json")
    )


def _release_audit_target_records(
    resolution: CurrentRecordResolution, source_id: str
) -> dict[str, tuple[str, str, dict[str, Any]]]:
    """当前来源的 document/question，供来源发布审计交叉验证。"""
    result: dict[str, tuple[str, str, dict[str, Any]]] = {}
    for kind in ("document", "question"):
        for relative_path, record in resolution.records[kind]:
            if record.get("source_id") != source_id:
                continue
            target_id = record.get("id")
            if isinstance(target_id, str) and target_id not in result:
                result[target_id] = (kind, relative_path, record)
    return result


def _validate_source_release_audit(
    resolution: CurrentRecordResolution,
    relative_path: str,
    audit: dict[str, Any],
    *,
    sources_by_id: dict[str, dict[str, Any]],
    reviews_by_path: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, Any]] | None:
    """验证一份来源发布审计的字段、来源绑定和 review 凭据。

    发布审计不是索引数据，因此不加入 ``records``；但它必须像 review 一样可追溯。
    这里故意不要求审计中的旧目标状态等于当前状态：目标在来源发布后可能继续从
    reviewed 进入 published，历史审计仍应保留。最终来源状态的一致性由调用方再查。
    """
    label = f"来源发布审计 {relative_path}"
    unexpected = sorted(set(audit) - RELEASE_AUDIT_FIELDS)
    missing = sorted(RELEASE_AUDIT_FIELDS - set(audit))
    if unexpected or missing:
        details: list[str] = []
        if missing:
            details.append("缺少 " + ", ".join(missing))
        if unexpected:
            details.append("不允许额外字段 " + ", ".join(unexpected))
        _add_error(resolution, f"{label} 字段无效：" + "；".join(details))
        return None
    audit_id = audit.get("id")
    stored_path = audit.get("relative_path")
    if (
        not isinstance(audit_id, str)
        or not RELEASE_ID_RE.fullmatch(audit_id)
        or stored_path != relative_path
        or not _is_safe_release_audit_path(stored_path)
        or stored_path != f"{RELEASE_AUDIT_PREFIX}{audit_id}.json"
    ):
        _add_error(resolution, f"{label} 的 ID 或 relative_path 无效")
        return None
    source_id = audit.get("source_id")
    source_sha256 = audit.get("source_sha256")
    source = sources_by_id.get(source_id) if isinstance(source_id, str) else None
    if (
        source is None
        or not isinstance(source_sha256, str)
        or not SHA256_RE.fullmatch(source_sha256)
        or source_id != f"src.bbg.{source_sha256}"
        or source.get("sha256") != source_sha256
        or audit.get("source_relative_path") != source.get("relative_path")
        or not isinstance(audit.get("source_relative_path"), str)
        or not is_safe_relative_path(audit.get("source_relative_path"))
        or not str(audit.get("source_relative_path")).startswith("raw/")
    ):
        _add_error(resolution, f"{label} 与当前来源身份或原始路径不一致")
        return None
    created_at = audit.get("created_at")
    if not isinstance(created_at, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", created_at):
        _add_error(resolution, f"{label} 的 created_at 必须是 UTC ISO 时间")
        return None
    if (
        audit.get("previous_status") not in {"pending_manual_review", "reviewed"}
        or audit.get("status") not in FINAL_REVIEW_STATUSES
        or audit.get("decision") != "approved"
        or not isinstance(audit.get("reviewer"), str)
        or not audit["reviewer"].strip()
        or not isinstance(audit.get("summary"), str)
        or not audit["summary"].strip()
        or not isinstance(audit.get("manifest_sha256"), str)
        or not SHA256_RE.fullmatch(audit["manifest_sha256"])
    ):
        _add_error(resolution, f"{label} 的状态、人工结论或 manifest 快照无效")
        return None
    expected_previous = "pending_manual_review" if audit["status"] == "reviewed" else "reviewed"
    if audit["previous_status"] != expected_previous:
        _add_error(resolution, f"{label} 的来源状态链不连续")
        return None
    exceptions_before = _valid_nonempty_unique_strings(audit.get("manifest_exceptions_before"))
    resolved_exceptions = _valid_nonempty_unique_strings(audit.get("resolved_exceptions"))
    exceptions_after = _valid_nonempty_unique_strings(audit.get("manifest_exceptions_after"))
    if (
        exceptions_before is None
        or resolved_exceptions is None
        or exceptions_after is None
        or exceptions_before != resolved_exceptions
        or exceptions_after != []
    ):
        _add_error(resolution, f"{label} 的 exception 处理审计不完整")
        return None

    targets = audit.get("target_reviews")
    if not isinstance(targets, list) or not targets:
        _add_error(resolution, f"{label} 必须保留 document 与 question 的人工复核凭据")
        return None
    source_targets = _release_audit_target_records(resolution, source_id)
    source_short = source_sha256[:16]
    seen_target_ids: set[str] = set()
    document_count = 0
    target_entries: dict[str, dict[str, Any]] = {}
    valid = True
    for sequence, entry in enumerate(targets, start=1):
        entry_label = f"{label} target_reviews[{sequence}]"
        if not isinstance(entry, dict) or set(entry) != {
            "target_id",
            "target_type",
            "target_relative_path",
            "target_status",
            "approved_review_paths",
        }:
            _add_error(resolution, f"{entry_label} 字段无效")
            valid = False
            continue
        target_id = entry.get("target_id")
        target_type = entry.get("target_type")
        target_path = entry.get("target_relative_path")
        target_status = entry.get("target_status")
        review_paths = _valid_nonempty_unique_strings(entry.get("approved_review_paths"))
        if not isinstance(target_id, str) or not target_id or target_id in seen_target_ids:
            _add_error(resolution, f"{entry_label} 的 target_id 无效或重复")
            valid = False
            continue
        seen_target_ids.add(target_id)
        if target_type == "document":
            expected_id = f"doc.bbg.{source_short}"
            expected_prefix = "records/documents/"
            document_count += 1
        elif target_type == "question":
            expected_id = None
            expected_prefix = "questions/"
        else:
            _add_error(resolution, f"{entry_label} 的 target_type 无效")
            valid = False
            continue
        if (
            (expected_id is not None and target_id != expected_id)
            or (target_type == "question" and not re.fullmatch(rf"q\.{re.escape(source_id)}\.\d{{3}}", target_id))
            or not isinstance(target_path, str)
            or not is_safe_relative_path(target_path)
            or not target_path.startswith(expected_prefix)
            or not target_path.endswith(".json")
            or target_status not in FINAL_REVIEW_STATUSES
            or review_paths is None
        ):
            _add_error(resolution, f"{entry_label} 的目标身份、路径、状态或 review 路径无效")
            valid = False
            continue
        if audit["status"] == "published" and target_status != "published":
            _add_error(resolution, f"{entry_label} 属于 published 来源审计但目标尚未 published")
            valid = False
        current_target = source_targets.get(target_id)
        if current_target is not None and (
            current_target[0] != target_type or current_target[1] != target_path
        ):
            _add_error(resolution, f"{entry_label} 与当前来源目标路径或类型不一致")
            valid = False
        for review_path in review_paths:
            if not _is_safe_review_path(review_path):
                _add_error(resolution, f"{entry_label} 的 approved review 路径不安全")
                valid = False
                continue
            review = reviews_by_path.get(review_path)
            if review is None or (
                review.get("target_id") != target_id
                or review.get("target_relative_path") != target_path
                or review.get("decision") != "approved"
                or review.get("status") != target_status
            ):
                _add_error(resolution, f"{entry_label} 的 approved review 凭据不存在或不匹配")
                valid = False
        target_entries[target_id] = dict(entry)
    if document_count != 1:
        _add_error(resolution, f"{label} 必须且只能包含一份 document 的复核凭据")
        valid = False
    if not valid:
        return None
    return source_id, {**audit, "_target_entries": target_entries}


def _validate_source_release_audits(resolution: CurrentRecordResolution) -> None:
    """读取来源发布审计，并阻止绕过发布门的最终来源状态。"""
    sources_by_id = {
        str(source.get("id")): source
        for _, source in resolution.sources
        if isinstance(source.get("id"), str)
    }
    reviews_by_path = {
        relative_path: review for relative_path, review in resolution.declared_records["review"]
    }
    valid_by_source: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for relative_path in _scan_json_files(
        resolution, RELEASE_AUDIT_DIRECTORY, label="来源发布审计"
    ):
        audit = _read_json_file(
            resolution, relative_path, label="来源发布审计", required=True
        )
        if audit is None:
            continue
        parsed = _validate_source_release_audit(
            resolution,
            relative_path,
            audit,
            sources_by_id=sources_by_id,
            reviews_by_path=reviews_by_path,
        )
        if parsed is None:
            continue
        source_id, validated_audit = parsed
        resolution.release_audits.append((relative_path, audit))
        valid_by_source.setdefault(source_id, []).append((relative_path, validated_audit))

    for source_id, source in sources_by_id.items():
        source_status = source.get("status")
        if source_status not in FINAL_REVIEW_STATUSES:
            continue
        exceptions = source.get("exceptions")
        if exceptions != []:
            _add_error(resolution, f"最终来源 {source_id} 仍保留未清空的 exceptions")
        targets = _release_audit_target_records(resolution, source_id)
        documents = [item for item in targets.values() if item[0] == "document"]
        if len(documents) != 1:
            _add_error(resolution, f"最终来源 {source_id} 必须恰有一份当前 document")
        for target_id, (target_type, relative_path, record) in targets.items():
            target_status = record.get("status")
            allowed_statuses = FINAL_REVIEW_STATUSES if source_status == "reviewed" else {"published"}
            if target_status not in allowed_statuses:
                _add_error(
                    resolution,
                    f"最终来源 {source_id} 的 {target_type} 尚未达到 {source_status} 发布要求：{relative_path}",
                )
            if target_type == "question" and record.get("review_status") != target_status:
                _add_error(resolution, f"最终来源 {source_id} 的 question 状态不一致：{relative_path}")

        expected_target_ids = set(targets)
        required_audit_status = str(source_status)
        matching_audits: list[tuple[str, dict[str, Any]]] = []
        for relative_path, audit in valid_by_source.get(source_id, []):
            if audit.get("status") != required_audit_status:
                continue
            audit_targets = audit.get("_target_entries")
            if not isinstance(audit_targets, dict) or set(audit_targets) != expected_target_ids:
                continue
            current_compatible = True
            for target_id, entry in audit_targets.items():
                _, _, current_record = targets[target_id]
                audit_target_status = entry.get("target_status")
                current_target_status = current_record.get("status")
                if required_audit_status == "published":
                    if audit_target_status != "published" or current_target_status != "published":
                        current_compatible = False
                elif audit_target_status == "published" and current_target_status != "published":
                    current_compatible = False
                elif audit_target_status == "reviewed" and current_target_status not in FINAL_REVIEW_STATUSES:
                    current_compatible = False
            if current_compatible:
                matching_audits.append((relative_path, audit))
        if not matching_audits:
            _add_error(
                resolution,
                f"最终来源 {source_id} 缺少覆盖当前 document/全部 questions 的 {required_audit_status} 来源发布审计",
            )
        if source_status == "published" and not any(
            audit.get("status") == "reviewed" for _, audit in valid_by_source.get(source_id, [])
        ):
            _add_error(resolution, f"已发布来源 {source_id} 缺少先前 reviewed 来源发布审计")


def _read_manifest_bytes(resolution: CurrentRecordResolution) -> bytes | None:
    path = _safe_regular_file(
        resolution,
        "sources/sources.jsonl",
        label="sources/sources.jsonl",
        required=True,
    )
    if path is None:
        return None
    try:
        return path.read_bytes()
    except OSError as error:
        _add_error(resolution, f"无法读取 sources/sources.jsonl：{error}")
        return None


def manifest_snapshot_matches(resolution: CurrentRecordResolution) -> bool:
    """确认 resolver 使用的 canonical manifest 在索引构建期间未被替换。"""
    if resolution.manifest_sha256 is None:
        return False
    current = _read_manifest_bytes(resolution)
    if current is None:
        return False
    return hashlib.sha256(current).hexdigest() == resolution.manifest_sha256


def resolve_current_records(library_root: Path | str = LIBRARY_ROOT) -> CurrentRecordResolution:
    """返回当前可索引记录和所有一致性错误。

    函数不会写文件。调用方可选择把 ``errors`` 变成验证失败或索引构建失败；无论
    如何，未明确列入 ``records`` 的文件绝不会成为检索结果。
    """
    try:
        root = safe_library_root(library_root)
    except PipelineError as error:
        raise CurrentRecordsError(str(error)) from error
    resolution = CurrentRecordResolution(root=root)
    before_manifest = _read_manifest_bytes(resolution)
    if before_manifest is None:
        return resolution
    try:
        sources = [dict(record) for record in read_source_manifest(root)]
    except (SourceStateError, OSError, ValueError) as error:
        _add_error(resolution, f"sources/sources.jsonl 不是可用的 canonical manifest：{error}")
        return resolution
    after_manifest = _read_manifest_bytes(resolution)
    if after_manifest is None:
        return resolution
    if after_manifest != before_manifest:
        _add_error(resolution, "sources/sources.jsonl 在当前记录解析期间发生变化")
        return resolution
    resolution.manifest_sha256 = hashlib.sha256(after_manifest).hexdigest()
    resolution.sources = [
        (f"sources/sources.jsonl:{index}", source)
        for index, source in enumerate(sources, start=1)
    ]

    expected_conversion_reports: set[str] = set()
    expected_structure_reports: set[str] = set()
    for source in sources:
        source_id = source.get("id")
        if not isinstance(source_id, str) or not SOURCE_ID_RE.fullmatch(source_id):
            _add_error(resolution, "canonical manifest 含无效 source_id")
            continue
        paths = _source_paths(source_id)
        expected_conversion_reports.add(paths.conversion_report)
        expected_structure_reports.add(paths.structure_report)
        conversion = _read_json_file(
            resolution,
            paths.conversion_report,
            label="转换报告",
            required=False,
        )
        conversion_is_current = False
        conversion_assets: set[str] = set()
        if conversion is not None:
            conversion_label = f"转换报告 {paths.conversion_report}"
            identity_valid = _require_report_identity(
                resolution, conversion, source, label=conversion_label
            )
            paths_valid = _require_report_paths(
                resolution,
                conversion,
                {
                    "markdown": paths.markdown,
                    "document": paths.document,
                    "conversion_log": paths.conversion_report,
                },
                label=conversion_label,
            )
            status = conversion.get("status")
            if status not in {"success", "failed"}:
                _add_error(resolution, f"{conversion_label} 的 status 必须是 success 或 failed")
            asset_paths, assets_valid = _asset_paths(
                resolution, conversion, source_id, label=conversion_label
            )
            if identity_valid and paths_valid and status in {"success", "failed"} and assets_valid:
                document, document_valid = _validate_document(
                    resolution,
                    source,
                    paths,
                    asset_paths,
                    conversion_success=status == "success",
                )
                if document is not None and document_valid:
                    _register_declared(
                        resolution,
                        "document",
                        paths.document,
                        document,
                        current=status == "success",
                    )
                conversion_is_current = status == "success" and document is not None and document_valid
                if conversion_is_current:
                    conversion_assets = set(asset_paths)

        structure = _read_json_file(
            resolution,
            paths.structure_report,
            label="结构化报告",
            required=False,
        )
        structure_is_current = False
        if structure is not None:
            structure_is_current = _validate_structure_report(
                resolution,
                structure,
                source,
                paths,
                conversion_is_current=conversion_is_current,
                conversion_assets=conversion_assets,
            )
        stage_is_current = _validate_manifest_stage(
            resolution,
            source,
            conversion,
            structure,
            conversion_is_current=conversion_is_current,
            structure_is_current=structure_is_current,
        )
        if not stage_is_current:
            _remove_source_from_current_records(resolution, source_id)

    _check_report_directory(
        resolution,
        "reports/conversion",
        expected_conversion_reports,
        label="转换报告",
    )
    _check_report_directory(
        resolution,
        "reports/structure",
        expected_structure_reports,
        label="结构化报告",
    )
    _check_orphan_records(resolution)
    _check_duplicate_ids(resolution)
    _validate_review_records(resolution)
    _validate_cross_references(resolution)
    _validate_review_admission_audits(resolution)
    _validate_source_release_audits(resolution)
    return resolution


def require_current_records(library_root: Path | str = LIBRARY_ROOT) -> CurrentRecordResolution:
    """取得无错误的当前记录；索引器使用它避免部分或过期索引。"""
    resolution = resolve_current_records(library_root)
    if resolution.errors:
        preview = "；".join(resolution.errors[:5])
        suffix = "；……" if len(resolution.errors) > 5 else ""
        raise CurrentRecordsError(f"当前记录一致性校验失败（{len(resolution.errors)} 项）：{preview}{suffix}")
    return resolution
