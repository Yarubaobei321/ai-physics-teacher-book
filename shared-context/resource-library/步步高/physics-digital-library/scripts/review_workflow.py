#!/usr/bin/env python3
"""步步高资料库的单条人工复核入口。

自动生成的 ``review-queue.jsonl`` 只是一份待办，不得据此把记录视为已经人工
验收。本工具把真正的人工动作拆成两个小步骤：

1. ``admit-source`` 只把一份已结构化来源转入人工复核，不伪造人工结论；
2. ``checklist`` 为一份来源或一条题目生成可阅读的本地核对单；
3. ``submit`` 在明确给出 reviewer、decision、summary 后，才写入一条正式
   review JSON，并只更新这一个 document 或 question 的状态。

命令默认 dry-run；只有显式传入 ``--apply`` 才会写文件。它绝不读取后更改
``raw/``，也不会因为一条题目通过就把整份 Word 或整库提升为 reviewed/published。
"""

from __future__ import annotations

import argparse
import copy
import fcntl
import json
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from current_records import CurrentRecordsError, require_current_records  # noqa: E402
from library_common import (  # noqa: E402
    LIBRARY_ROOT,
    PipelineError,
    is_safe_relative_path,
    json_bytes,
    official_library_root,
    remove_generated_file,
    safe_library_root,
    safe_output_path,
    write_json,
    write_text,
)
from source_state import SOURCE_ID_RE, SourceStateError, update_source_state  # noqa: E402


REVIEW_ID_RE = re.compile(r"^review\.bbg\.[a-z0-9][a-z0-9._-]*$")
REVIEW_PATH_PREFIX = "reviews/"
WORKLIST_PATH_PREFIX = "reviews/worklists/"
LOCK_PATH = "reviews/.review-workflow.lock"
TRANSACTION_PATH = "reviews/.review-workflow.pending"
ADMISSION_ID_RE = re.compile(r"^admission\.bbg\.[a-z0-9][a-z0-9._-]*$")
ADMISSION_PATH_PREFIX = "reports/review-admissions/"
ADMISSION_TRANSACTION_PATH = f"{ADMISSION_PATH_PREFIX}.review-admission.pending"
TARGET_KINDS = ("document", "question")
APPROVED_STATUSES = ("reviewed", "published")
DECISIONS = ("approved", "needs_changes", "rejected", "blocked")
RESULT_STATUSES = ("pending_manual_review", "reviewed", "published", "blocked")
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
ADMISSION_RECORD_FIELDS = frozenset(
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
ADMISSION_TRANSACTION_FIELDS = frozenset(
    {
        "source_id",
        "source_sha256",
        "previous_status",
        "next_status",
        "targets",
        "audit_relative_path",
        "audit",
    }
)
ADMISSION_TRANSACTION_TARGET_FIELDS = frozenset(
    {"target_relative_path", "original_target", "updated_target"}
)


class ReviewWorkflowError(RuntimeError):
    """人工复核的目标、状态或输出位置不满足安全契约。"""


@contextmanager
def _review_lock(root: Path):
    """串行化本工具的提交，避免两位复核者覆盖彼此的结论。"""
    target = safe_output_path(root, LOCK_PATH)
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(target, flags, 0o600)
    except OSError as error:
        raise ReviewWorkflowError(f"无法取得人工复核锁：{error}") from error
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _optional_bytes(root: Path, relative_path: str) -> bytes | None:
    target = safe_output_path(root, relative_path, create_parent=False)
    if not target.exists():
        return None
    if target.is_symlink() or not target.is_file():
        raise ReviewWorkflowError(f"事务文件必须是普通文件：{relative_path}")
    try:
        return target.read_bytes()
    except OSError as error:
        raise ReviewWorkflowError(f"无法读取事务文件：{relative_path}（{error}）") from error


def _remove_if_present(root: Path, relative_path: str) -> None:
    try:
        remove_generated_file(root, relative_path)
    except (OSError, PipelineError) as error:
        raise ReviewWorkflowError(f"无法清理事务文件：{relative_path}（{error}）") from error


def _write_json_exclusive(root: Path, relative_path: str, value: dict[str, Any]) -> None:
    """以“仅不存在时创建”方式发布 review，拒绝同名覆盖。"""
    target = safe_output_path(root, relative_path)
    data = json_bytes(value)
    descriptor, raw_temporary = tempfile.mkstemp(prefix=".review-", dir=target.parent)
    temporary = Path(raw_temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if target.is_symlink():
            raise ReviewWorkflowError("review 输出不能是符号链接")
        try:
            os.link(temporary, target)
        except FileExistsError as error:
            raise ReviewWorkflowError("review_id 已存在；正式复核记录不可覆盖") from error
    except OSError as error:
        raise ReviewWorkflowError(f"无法写入正式 review：{error}") from error
    finally:
        if temporary.exists():
            temporary.unlink()


def _json_matches(raw: bytes | None, expected: dict[str, Any]) -> bool:
    if raw is None:
        return False
    try:
        return json.loads(raw.decode("utf-8")) == expected
    except (UnicodeDecodeError, ValueError):
        return False


def _is_safe_admission_path(value: object) -> bool:
    return (
        isinstance(value, str)
        and is_safe_relative_path(value)
        and value.startswith(ADMISSION_PATH_PREFIX)
        and value.endswith(".json")
    )


def _is_safe_admission_internal_path(value: object) -> bool:
    return (
        isinstance(value, str)
        and is_safe_relative_path(value)
        and value.startswith(ADMISSION_PATH_PREFIX)
        and value.endswith((".json", ".pending"))
    )


def _optional_admission_bytes(root: Path, relative_path: str) -> bytes | None:
    """只读 admission 审计/短事务；预览不创建缺失目录。"""
    if not _is_safe_admission_internal_path(relative_path):
        raise ReviewWorkflowError("转入待审内部文件路径不安全")
    target = root.joinpath(*Path(relative_path).parts)
    current = root
    for component in target.relative_to(root).parts[:-1]:
        current = current / component
        if not current.exists():
            return None
        if current.is_symlink() or not current.is_dir():
            raise ReviewWorkflowError(f"转入待审目录必须是普通目录：{relative_path}")
    if not target.exists():
        return None
    if target.is_symlink() or not target.is_file():
        raise ReviewWorkflowError(f"转入待审文件必须是普通文件：{relative_path}")
    try:
        return target.read_bytes()
    except OSError as error:
        raise ReviewWorkflowError(f"无法读取转入待审文件：{relative_path}（{error}）") from error


def _safe_existing_admission_path(root: Path, relative_path: str) -> Path | None:
    """检查一个候选审计路径，不为默认预览创建目录。"""
    if not _is_safe_admission_path(relative_path):
        raise ReviewWorkflowError("转入待审审计路径不安全")
    target = root.joinpath(*Path(relative_path).parts)
    current = root
    for component in target.relative_to(root).parts[:-1]:
        current = current / component
        if not current.exists():
            return None
        if current.is_symlink() or not current.is_dir():
            raise ReviewWorkflowError("转入待审审计目录不是安全普通目录")
    if target.is_symlink():
        raise ReviewWorkflowError("转入待审审计文件不能是符号链接")
    return target if target.exists() else None


def _write_admission_exclusive(root: Path, relative_path: str, value: dict[str, Any]) -> None:
    """只允许首次写入 admission 审计，避免覆写既有状态链凭据。"""
    target = safe_output_path(root, relative_path)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int | None = None
    try:
        descriptor = os.open(target, flags, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            stream.write(json_bytes(value))
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as error:
        raise ReviewWorkflowError("admission_id 已存在；转入待审审计不可覆盖") from error
    except OSError as error:
        raise ReviewWorkflowError(f"无法写入转入待审审计：{error}") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _validate_pending_transaction(
    root: Path,
    *,
    target_path: object,
    review_path: object,
    original: object,
    updated: object,
    review: object,
) -> tuple[str, str, dict[str, Any], dict[str, Any], dict[str, Any]]:
    """只接受本工具能自行重建的事务内容，拒绝损坏或手工伪造的标记。"""
    if (
        not isinstance(target_path, str)
        or not target_path.startswith(("records/documents/", "questions/"))
        or not target_path.endswith(".json")
        or not is_safe_relative_path(target_path)
        or not isinstance(review_path, str)
        or not review_path.startswith(REVIEW_PATH_PREFIX)
        or not review_path.endswith(".json")
        or not is_safe_relative_path(review_path)
        or not isinstance(original, dict)
        or not isinstance(updated, dict)
        or not isinstance(review, dict)
    ):
        raise ReviewWorkflowError("人工复核事务标记包含不安全路径或内容；请人工检查后再提交")

    # 先由受控路径检查拒绝软链接、越界和不存在的父目录，再校验各 JSON 的互相绑定。
    try:
        safe_output_path(root, target_path, create_parent=False)
        safe_output_path(root, review_path, create_parent=False)
    except PipelineError as error:
        raise ReviewWorkflowError(f"人工复核事务路径不安全：{error}") from error

    original_id = original.get("id")
    updated_id = updated.get("id")
    if (
        not isinstance(original_id, str)
        or original_id != updated_id
        or original.get("relative_path") != target_path
        or updated.get("relative_path") != target_path
    ):
        raise ReviewWorkflowError("人工复核事务的目标 ID 或记录路径不一致；请人工检查后再提交")

    unexpected_review_fields = sorted(set(review) - REVIEW_RECORD_FIELDS)
    review_id = review.get("id")
    if (
        unexpected_review_fields
        or not isinstance(review_id, str)
        or not REVIEW_ID_RE.fullmatch(review_id)
        or review.get("relative_path") != review_path
        or review_path != _review_path(review_id)
        or review.get("target_id") != original_id
        or review.get("target_relative_path") != target_path
    ):
        raise ReviewWorkflowError("人工复核事务的 review 与目标未正确绑定；请人工检查后再提交")

    target_kind = "question" if target_path.startswith("questions/") else "document"
    try:
        reviewer = _normalise_text(review.get("reviewer"), "事务 reviewer")
        summary = _normalise_text(review.get("summary"), "事务 summary")
        issues = _normalise_issues(review.get("issues"))
        resolved_issues = _normalise_issues(review.get("resolved_issues"))
        if review.get("issues") != issues or review.get("resolved_issues", []) != resolved_issues:
            raise ReviewWorkflowError("人工复核事务的 issues 必须是去重后的非空文本数组")
        decision = review.get("decision")
        result_status = review.get("status")
        _validate_outcome(
            {"kind": target_kind, "record": original},
            decision=decision,
            result_status=result_status,
            issues=issues,
            resolved_issues=resolved_issues,
        )
        expected_updated = _updated_target_record(
            {"kind": target_kind, "record": original},
            result_status=result_status,
            new_issues=issues,
        )
    except ReviewWorkflowError as error:
        raise ReviewWorkflowError(f"人工复核事务不符合状态链：{error}") from error
    if updated != expected_updated or reviewer != review.get("reviewer") or summary != review.get("summary"):
        raise ReviewWorkflowError("人工复核事务的目标改动与 review 内容不一致；请人工检查后再提交")
    return target_path, review_path, original, updated, review


def _recover_pending_transaction(root: Path) -> None:
    """恢复被中断的单条提交，或确认它已完整提交后清理事务标记。"""
    raw = _optional_bytes(root, TRANSACTION_PATH)
    if raw is None:
        return
    try:
        transaction = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise ReviewWorkflowError("发现无法解析的人工复核事务标记；请人工检查后再提交") from error
    if not isinstance(transaction, dict):
        raise ReviewWorkflowError("人工复核事务标记格式无效；请人工检查后再提交")
    required = {"target_relative_path", "original_target", "updated_target", "review_relative_path", "review"}
    if set(transaction) != required:
        raise ReviewWorkflowError("人工复核事务标记字段无效；请人工检查后再提交")
    target_path = transaction["target_relative_path"]
    review_path = transaction["review_relative_path"]
    original = transaction["original_target"]
    updated = transaction["updated_target"]
    review = transaction["review"]
    target_path, review_path, original, updated, review = _validate_pending_transaction(
        root,
        target_path=target_path,
        review_path=review_path,
        original=original,
        updated=updated,
        review=review,
    )
    target_bytes = _optional_bytes(root, target_path)
    review_bytes = _optional_bytes(root, review_path)
    target_is_original = _json_matches(target_bytes, original)
    target_is_updated = _json_matches(target_bytes, updated)
    review_is_expected = _json_matches(review_bytes, review)
    if target_is_updated and review_is_expected:
        _remove_if_present(root, TRANSACTION_PATH)
        return
    if target_is_original and review_bytes is None:
        _remove_if_present(root, TRANSACTION_PATH)
        return
    if target_is_original and review_is_expected:
        _remove_if_present(root, review_path)
        _remove_if_present(root, TRANSACTION_PATH)
        return
    if target_is_updated and review_bytes is None:
        write_json(root, target_path, original)
        _remove_if_present(root, TRANSACTION_PATH)
        return
    raise ReviewWorkflowError("发现无法安全恢复的人工复核事务；请先运行校验并人工处理")


def _normalise_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewWorkflowError(f"{field} 必须是非空文本")
    return value.strip()


def _normalise_issues(values: Iterable[object] | None) -> list[str]:
    if values is None:
        return []
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ReviewWorkflowError("issues 只能包含非空文本")
        item = value.strip()
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def _record_issues(record: dict[str, Any]) -> list[str]:
    value = record.get("issues", [])
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ReviewWorkflowError("目标记录的 issues 不是有效字符串数组；请先修复记录")
    return _normalise_issues(value)


def _resolution_targets(library_root: Path | str) -> tuple[Path, dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """返回仅由当前成功报告声明的 document/question 目标。

    ``require_current_records`` 会拒绝孤儿记录、过期报告和路径越界。因而这个工具
    不会依靠用户传入的路径直接打开 JSON，也不会把 review 写到资料库外。
    """
    root = safe_library_root(library_root)
    try:
        resolution = require_current_records(root)
    except CurrentRecordsError as error:
        raise ReviewWorkflowError(f"资料库当前记录未通过一致性校验：{error}") from error
    targets: dict[str, dict[str, Any]] = {}
    for kind in TARGET_KINDS:
        for relative_path, record in resolution.records[kind]:
            record_id = record.get("id")
            if not isinstance(record_id, str) or record_id in targets:
                raise ReviewWorkflowError("当前记录含重复或无效 target ID，拒绝提交复核")
            targets[record_id] = {"kind": kind, "relative_path": relative_path, "record": record}
    sources: dict[str, dict[str, Any]] = {}
    for _, source in resolution.sources:
        source_id = source.get("id")
        if isinstance(source_id, str):
            sources[source_id] = source
    return root, targets, sources


def _target_context(
    library_root: Path | str, target_id: str
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    target_value = _normalise_text(target_id, "target_id")
    root, targets, sources = _resolution_targets(library_root)
    target = targets.get(target_value)
    if target is None:
        raise ReviewWorkflowError("target_id 不在当前可复核的 document/question 记录中")
    record = target["record"]
    source_id = record.get("source_id")
    if not isinstance(source_id, str) or source_id not in sources:
        raise ReviewWorkflowError("目标记录没有可追溯的当前来源")
    return root, target, sources[source_id]


def _display_value(value: object) -> str:
    if value is None:
        return "（未提供）"
    if isinstance(value, list):
        return "；".join(_display_value(item) for item in value) or "（无）"
    if isinstance(value, dict):
        return "；".join(f"{key}: {_display_value(item)}" for key, item in value.items()) or "（无）"
    return str(value).strip() or "（空）"


def _markdown_code(value: object) -> str:
    return "`" + str(value).replace("`", "\\`") + "`"


def _question_lines(record: dict[str, Any]) -> list[str]:
    location = record.get("source_location") if isinstance(record.get("source_location"), dict) else {}
    lines = [
        f"- 来源位置：{_markdown_code(location.get('relative_path', '（缺失）'))}；{_display_value(location.get('locator'))}",
        f"- 题型：{_display_value(record.get('question_type'))}",
        f"- 题干：{_display_value(record.get('stem'))}",
        f"- 选项：{_display_value(record.get('options'))}",
        f"- 答案：{_display_value(record.get('answer'))}",
        f"- 解析：{_display_value(record.get('solution'))}",
        f"- 公式：{_display_value(record.get('formula_latex'))}",
        f"- 配图：{_display_value(record.get('figures'))}",
        f"- 知识点：{_display_value(record.get('knowledge_ids'))}",
        f"- 模型：{_display_value(record.get('model_ids'))}",
        f"- 技能：{_display_value(record.get('skill_ids'))}",
        f"- 难度：{_display_value(record.get('difficulty'))}；提取置信度：{_display_value(record.get('extraction_confidence'))}",
    ]
    return lines


def build_checklist(
    library_root: Path | str = LIBRARY_ROOT,
    *,
    source_id: str | None = None,
    target_id: str | None = None,
) -> dict[str, Any]:
    """生成一份只读的人工核对单数据，不写入任何文件。"""
    if bool(source_id) == bool(target_id):
        raise ReviewWorkflowError("必须且只能提供 source_id 或 target_id 之一")
    root, targets, sources = _resolution_targets(library_root)
    markdown_by_source = {
        str(target["record"].get("source_id")): str(target["record"].get("content_path"))
        for target in targets.values()
        if target["kind"] == "document"
        and isinstance(target["record"].get("source_id"), str)
        and isinstance(target["record"].get("content_path"), str)
    }
    selected: list[dict[str, Any]]
    if source_id:
        source_key = _normalise_text(source_id, "source_id")
        source = sources.get(source_key)
        if source is None:
            raise ReviewWorkflowError("source_id 不在当前来源清单中")
        selected = [
            {"id": record_id, **target}
            for record_id, target in targets.items()
            if target["record"].get("source_id") == source_key
        ]
        if not selected:
            raise ReviewWorkflowError("该来源没有当前可复核的 document/question 记录")
    else:
        target_key = _normalise_text(target_id, "target_id")
        target = targets.get(target_key)
        if target is None:
            raise ReviewWorkflowError("target_id 不在当前可复核的 document/question 记录中")
        raw_source_id = target["record"].get("source_id")
        if not isinstance(raw_source_id, str) or raw_source_id not in sources:
            raise ReviewWorkflowError("目标记录没有可追溯的当前来源")
        source = sources[raw_source_id]
        selected = [{"id": target_key, **target}]

    ordered = sorted(
        selected,
        key=lambda item: (0 if item["kind"] == "document" else 1, str(item["id"])),
    )
    entries: list[dict[str, Any]] = []
    for item in ordered:
        record = dict(item["record"])
        entries.append(
            {
                "target_id": item["id"],
                "target_type": item["kind"],
                "target_relative_path": item["relative_path"],
                "status": record.get("status"),
                "review_status": record.get("review_status"),
                "issues": _record_issues(record),
                "document_content_path": markdown_by_source.get(str(record.get("source_id"))),
                "record": record,
            }
        )
    return {
        "scope": "single-source" if source_id else "single-target",
        "source": dict(source),
        "entries": entries,
        "notice": "此清单仅供人工核对；生成或阅读它不会改变任何记录状态。",
        "root": root,
    }


def render_checklist(checklist: dict[str, Any]) -> str:
    """将核对单数据转为可直接打开的本地 Markdown。"""
    source = checklist["source"]
    metadata = source.get("metadata") if isinstance(source.get("metadata"), dict) else {}
    lines = [
        "# 步步高人工复核清单",
        "",
        "这是一份待核对清单，不代表任何题目、文档或来源已经通过人工复核。完成核对后，必须用 `review_workflow.py submit --apply` 写入正式记录。",
        "",
        "## 来源",
        "",
        f"- 来源 ID：{_markdown_code(source.get('id', '（缺失）'))}",
        f"- 原始 Word（只读）：{_markdown_code(source.get('relative_path', '（缺失）'))}",
        f"- 标题：{_display_value(source.get('title'))}",
        f"- 分类：{_display_value(source.get('profile'))}",
        f"- 来源状态：{_display_value(source.get('status'))}",
        f"- 章节：{_display_value(metadata.get('chapter'))}；课时：{_display_value(metadata.get('lesson_no'))}",
        "",
        "## 核对要求",
        "",
        "1. 打开原始 Word 与相应 Markdown，核对题干、题号、选项、答案、解析、公式和配图。",
        "2. 确认知识点、模型、技能和难度是否合适；有问题时保留具体问题，不得直接通过。",
        "3. 通过后先提交 `reviewed`；需要进入检索稳定版本时，再对同一条记录单独提交 `published`。",
        "4. 单题通过不会提升整份 Word 或其他题目；来源清单状态仍须逐项完成复核后另行处理。",
    ]
    for sequence, entry in enumerate(checklist["entries"], start=1):
        record = entry["record"]
        lines.extend(
            [
                "",
                f"## {sequence}. {entry['target_type']}：{_display_value(record.get('label', record.get('title', entry['target_id'])))}",
                "",
                f"- 目标 ID：{_markdown_code(entry['target_id'])}",
                f"- 记录：{_markdown_code(entry['target_relative_path'])}",
                f"- 当前状态：{_display_value(entry['status'])}",
            ]
        )
        if entry["target_type"] == "document":
            lines.extend(
                [
                    f"- Markdown：{_markdown_code(record.get('content_path', '（缺失）'))}",
                    f"- 图片资产：{_display_value(record.get('asset_paths'))}",
                    "- 请核对：段落、表格、图片、公式、讲解/练习/答案区块，以及是否跨课时或跨题串段。",
                ]
            )
        else:
            if entry.get("document_content_path"):
                lines.append(f"- 对照 Markdown：{_markdown_code(entry['document_content_path'])}")
            lines.extend(_question_lines(record))
        if entry["issues"]:
            lines.append(f"- 当前待处理问题：{_display_value(entry['issues'])}")
        else:
            lines.append("- 当前待处理问题：无（仍必须人工核对后才能通过）。")
    return "\n".join(lines) + "\n"


def _validate_worklist_path(relative_path: str) -> str:
    if (
        not is_safe_relative_path(relative_path)
        or not relative_path.startswith(WORKLIST_PATH_PREFIX)
        or not relative_path.endswith(".md")
    ):
        raise ReviewWorkflowError("核对单只能写入 reviews/worklists/ 下的 .md 相对路径")
    return relative_path


def write_checklist(
    library_root: Path | str = LIBRARY_ROOT,
    *,
    output_relative_path: str,
    source_id: str | None = None,
    target_id: str | None = None,
) -> dict[str, Any]:
    """写入一份可读核对单；该操作不会写 review JSON 或更新数据状态。"""
    checklist = build_checklist(library_root, source_id=source_id, target_id=target_id)
    root = checklist["root"]
    output = _validate_worklist_path(output_relative_path)
    target = safe_output_path(root, output)
    if target.exists():
        raise ReviewWorkflowError("核对单已存在；请使用新的文件名，避免覆盖既有人工记录")
    write_text(root, output, render_checklist(checklist))
    return {
        "path": output,
        "source_id": checklist["source"]["id"],
        "target_count": len(checklist["entries"]),
        "notice": checklist["notice"],
    }


def _review_id_for(target_id: str, *, now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    source_match = re.search(r"src\.bbg\.([0-9a-f]{16})[0-9a-f]{48}", target_id)
    source_short = source_match.group(1) if source_match else "target"
    suffix = target_id.rsplit(".", 1)[-1].lower()
    timestamp = current.strftime("%Y%m%dt%H%M%Sz").lower()
    return f"review.bbg.{source_short}.{suffix}.{timestamp}"


def _review_path(review_id: str) -> str:
    if not REVIEW_ID_RE.fullmatch(review_id):
        raise ReviewWorkflowError("review_id 必须符合 review.bbg.<小写标识> 格式")
    return f"{REVIEW_PATH_PREFIX}{review_id}.json"


def _unique_review_id(
    root: Path, target_id: str, requested_id: str | None, *, create_parent: bool
) -> tuple[str, str]:
    if requested_id is not None:
        review_id = _normalise_text(requested_id, "review_id")
        relative_path = _review_path(review_id)
        if safe_output_path(root, relative_path, create_parent=create_parent).exists():
            raise ReviewWorkflowError("review_id 已存在；正式复核记录不可覆盖")
        return review_id, relative_path
    base = _review_id_for(target_id)
    for sequence in range(1, 10_000):
        review_id = base if sequence == 1 else f"{base}-{sequence:03d}"
        relative_path = _review_path(review_id)
        if not safe_output_path(root, relative_path, create_parent=create_parent).exists():
            return review_id, relative_path
    raise ReviewWorkflowError("无法生成唯一 review_id")


def _admission_path(admission_id: str) -> str:
    if not ADMISSION_ID_RE.fullmatch(admission_id):
        raise ReviewWorkflowError("admission_id 必须符合 admission.bbg.<小写标识> 格式")
    return f"{ADMISSION_PATH_PREFIX}{admission_id}.json"


def _unique_admission_id(
    root: Path, source_id: str, requested_id: str | None
) -> tuple[str, str]:
    if requested_id is not None:
        admission_id = _normalise_text(requested_id, "admission_id")
        relative_path = _admission_path(admission_id)
        if _safe_existing_admission_path(root, relative_path) is not None:
            raise ReviewWorkflowError("admission_id 已存在；转入待审审计不可覆盖")
        return admission_id, relative_path
    source_short = source_id.rsplit(".", 1)[-1][:16]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dt%H%M%Sz").lower()
    base = f"admission.bbg.{source_short}.pending-manual-review.{timestamp}"
    for sequence in range(1, 10_000):
        admission_id = base if sequence == 1 else f"{base}-{sequence:03d}"
        relative_path = _admission_path(admission_id)
        if _safe_existing_admission_path(root, relative_path) is None:
            return admission_id, relative_path
    raise ReviewWorkflowError("无法生成唯一 admission_id")


def _admitted_target_record(target: dict[str, Any]) -> dict[str, Any]:
    """只更新状态；转入待审不是人工 review，不能清空或添加 issues。"""
    record = copy.deepcopy(target["record"])
    record["status"] = "pending_manual_review"
    if target["kind"] == "question":
        record["review_status"] = "pending_manual_review"
    return record


def _admission_targets(
    root: Path, source_id: str
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    """取得一份可安全转入待审的来源及其全部当前 document/question。"""
    if not isinstance(source_id, str) or not SOURCE_ID_RE.fullmatch(source_id):
        raise ReviewWorkflowError("source_id 必须是完整 src.bbg.<sha256> ID")
    try:
        resolution = require_current_records(root)
    except CurrentRecordsError as error:
        raise ReviewWorkflowError(f"资料库当前记录未通过一致性校验：{error}") from error
    source_matches = [source for _, source in resolution.sources if source.get("id") == source_id]
    if len(source_matches) != 1:
        raise ReviewWorkflowError("来源清单中未找到唯一 source_id")
    source = dict(source_matches[0])
    if source.get("status") != "ai_structured":
        raise ReviewWorkflowError(
            "来源必须仍为 ai_structured 才能转入 pending_manual_review；不能借此绕过或回退状态链"
        )
    if source.get("exceptions") != []:
        raise ReviewWorkflowError("含 exceptions 的来源应由流水线保留待审原因，不能使用无异常转入入口")

    selected: list[dict[str, Any]] = []
    for kind in TARGET_KINDS:
        for relative_path, record in resolution.records[kind]:
            if record.get("source_id") != source_id:
                continue
            selected.append({"kind": kind, "relative_path": relative_path, "record": record})
    documents = [target for target in selected if target["kind"] == "document"]
    if len(documents) != 1:
        raise ReviewWorkflowError("该来源必须恰有一份当前 document，才能转入人工复核")
    for target in selected:
        record = target["record"]
        if record.get("status") != "ai_structured":
            raise ReviewWorkflowError("所有当前 document/question 都必须仍为 ai_structured，拒绝覆盖已改变目标")
        if _record_issues(record):
            raise ReviewWorkflowError("目标仍有 issues，应保留异常并走常规待审流程，不能静默转入")
        if target["kind"] == "question" and record.get("review_status") != "ai_structured":
            raise ReviewWorkflowError("question 的 status/review_status 不一致，拒绝转入待审")
    if resolution.manifest_sha256 is None:
        raise ReviewWorkflowError("缺少当前 sources/sources.jsonl 哈希，拒绝建立转入待审审计")
    ordered = sorted(
        selected,
        key=lambda target: (0 if target["kind"] == "document" else 1, target["relative_path"]),
    )
    return source, ordered, resolution.manifest_sha256


def _validate_admission_audit(audit: object) -> dict[str, Any]:
    """验证 admission 审计自身的固定字段和来源/目标绑定。"""
    if not isinstance(audit, dict):
        raise ReviewWorkflowError("转入待审审计必须是对象")
    missing = sorted(ADMISSION_RECORD_FIELDS - set(audit))
    unexpected = sorted(set(audit) - ADMISSION_RECORD_FIELDS)
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append("缺少字段：" + ", ".join(missing))
        if unexpected:
            details.append("不允许字段：" + ", ".join(unexpected))
        raise ReviewWorkflowError("转入待审审计字段无效：" + "；".join(details))
    record = dict(audit)
    admission_id = record.get("id")
    relative_path = record.get("relative_path")
    if (
        not isinstance(admission_id, str)
        or not ADMISSION_ID_RE.fullmatch(admission_id)
        or not isinstance(relative_path, str)
        or relative_path != _admission_path(admission_id)
        or not _is_safe_admission_path(relative_path)
    ):
        raise ReviewWorkflowError("转入待审审计 ID 或路径无效")
    source_id = record.get("source_id")
    source_sha256 = record.get("source_sha256")
    if (
        not isinstance(source_id, str)
        or not SOURCE_ID_RE.fullmatch(source_id)
        or not isinstance(source_sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", source_sha256)
        or source_id != f"src.bbg.{source_sha256}"
        or not isinstance(record.get("source_relative_path"), str)
        or not is_safe_relative_path(record["source_relative_path"])
        or not record["source_relative_path"].startswith("raw/")
    ):
        raise ReviewWorkflowError("转入待审审计的来源身份或原始路径无效")
    created_at = record.get("created_at")
    if not isinstance(created_at, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", created_at):
        raise ReviewWorkflowError("转入待审审计 created_at 必须是 UTC ISO 时间")
    if record.get("previous_status") != "ai_structured" or record.get("status") != "pending_manual_review":
        raise ReviewWorkflowError("转入待审审计必须记录 ai_structured → pending_manual_review")
    _normalise_text(record.get("operator"), "转入待审审计 operator")
    _normalise_text(record.get("summary"), "转入待审审计 summary")
    if not isinstance(record.get("manifest_sha256"), str) or not re.fullmatch(
        r"[0-9a-f]{64}", record["manifest_sha256"]
    ):
        raise ReviewWorkflowError("转入待审审计 manifest_sha256 无效")
    targets = record.get("target_records")
    if not isinstance(targets, list) or not targets:
        raise ReviewWorkflowError("转入待审审计必须保留 document 与当前 questions 的状态变更")
    seen_ids: set[str] = set()
    document_count = 0
    for target in targets:
        if not isinstance(target, dict) or set(target) != {
            "target_id",
            "target_type",
            "target_relative_path",
            "previous_status",
            "status",
        }:
            raise ReviewWorkflowError("转入待审审计 target_records 条目无效")
        target_id = target.get("target_id")
        target_type = target.get("target_type")
        target_path = target.get("target_relative_path")
        if not isinstance(target_id, str) or not target_id or target_id in seen_ids:
            raise ReviewWorkflowError("转入待审审计 target_records 的 target_id 无效或重复")
        seen_ids.add(target_id)
        if target_type == "document":
            expected_id = f"doc.bbg.{source_sha256[:16]}"
            expected_prefix = "records/documents/"
            document_count += 1
        elif target_type == "question":
            expected_id = None
            expected_prefix = "questions/"
        else:
            raise ReviewWorkflowError("转入待审审计 target_records 的 target_type 无效")
        if (
            (expected_id is not None and target_id != expected_id)
            or (target_type == "question" and not re.fullmatch(rf"q\.{re.escape(source_id)}\.\d{{3}}", target_id))
            or not isinstance(target_path, str)
            or not is_safe_relative_path(target_path)
            or not target_path.startswith(expected_prefix)
            or not target_path.endswith(".json")
            or target.get("previous_status") != "ai_structured"
            or target.get("status") != "pending_manual_review"
        ):
            raise ReviewWorkflowError("转入待审审计 target_records 的身份、路径或状态无效")
    if document_count != 1:
        raise ReviewWorkflowError("转入待审审计必须且只能包含一份 document")
    return record


def _validate_admission_transaction(root: Path, transaction: object) -> dict[str, Any]:
    if not isinstance(transaction, dict) or set(transaction) != ADMISSION_TRANSACTION_FIELDS:
        raise ReviewWorkflowError("转入待审事务标记字段无效；请人工检查后再提交")
    source_id = transaction.get("source_id")
    source_sha256 = transaction.get("source_sha256")
    previous_status = transaction.get("previous_status")
    next_status = transaction.get("next_status")
    audit_path = transaction.get("audit_relative_path")
    audit = _validate_admission_audit(transaction.get("audit"))
    targets = transaction.get("targets")
    if (
        not isinstance(source_id, str)
        or not SOURCE_ID_RE.fullmatch(source_id)
        or not isinstance(source_sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", source_sha256)
        or source_id != f"src.bbg.{source_sha256}"
        or previous_status != "ai_structured"
        or next_status != "pending_manual_review"
        or not isinstance(audit_path, str)
        or not _is_safe_admission_path(audit_path)
        or not isinstance(targets, list)
        or not targets
    ):
        raise ReviewWorkflowError("转入待审事务标记内容无效；请人工检查后再提交")
    if (
        audit_path != audit["relative_path"]
        or source_id != audit["source_id"]
        or source_sha256 != audit["source_sha256"]
        or previous_status != audit["previous_status"]
        or next_status != audit["status"]
    ):
        raise ReviewWorkflowError("转入待审事务与审计记录未正确绑定；请人工检查后再提交")
    audit_targets = {entry["target_id"]: entry for entry in audit["target_records"]}
    if len(audit_targets) != len(targets):
        raise ReviewWorkflowError("转入待审事务与审计目标数量不一致；请人工检查后再提交")
    seen_paths: set[str] = set()
    for target in targets:
        if not isinstance(target, dict) or set(target) != ADMISSION_TRANSACTION_TARGET_FIELDS:
            raise ReviewWorkflowError("转入待审事务目标字段无效；请人工检查后再提交")
        relative_path = target.get("target_relative_path")
        original = target.get("original_target")
        updated = target.get("updated_target")
        if (
            not isinstance(relative_path, str)
            or not is_safe_relative_path(relative_path)
            or not relative_path.startswith(("records/documents/", "questions/"))
            or not relative_path.endswith(".json")
            or relative_path in seen_paths
            or not isinstance(original, dict)
            or not isinstance(updated, dict)
            or original.get("relative_path") != relative_path
            or updated.get("relative_path") != relative_path
            or original.get("id") != updated.get("id")
            or original.get("id") not in audit_targets
        ):
            raise ReviewWorkflowError("转入待审事务目标绑定无效；请人工检查后再提交")
        seen_paths.add(relative_path)
        target_id = original["id"]
        audit_target = audit_targets[target_id]
        kind = "question" if relative_path.startswith("questions/") else "document"
        expected_target = {
            "kind": kind,
            "relative_path": relative_path,
            "record": original,
        }
        if (
            audit_target["target_type"] != kind
            or audit_target["target_relative_path"] != relative_path
            or updated != _admitted_target_record(expected_target)
        ):
            raise ReviewWorkflowError("转入待审事务目标状态与审计不一致；请人工检查后再提交")
        try:
            safe_output_path(root, relative_path, create_parent=False)
        except PipelineError as error:
            raise ReviewWorkflowError(f"转入待审事务目标路径不安全：{error}") from error
    if set(audit_targets) != {target["original_target"]["id"] for target in targets}:
        raise ReviewWorkflowError("转入待审事务未覆盖审计中的全部目标；请人工检查后再提交")
    return dict(transaction)


def _admission_source_by_id(root: Path, source_id: str) -> dict[str, Any]:
    try:
        from source_state import read_source_manifest

        sources = read_source_manifest(root)
    except SourceStateError as error:
        raise ReviewWorkflowError(f"无法读取来源清单：{error}") from error
    matches = [source for source in sources if source.get("id") == source_id]
    if len(matches) != 1:
        raise ReviewWorkflowError("来源清单中未找到唯一 source_id")
    return dict(matches[0])


def _recover_pending_admission_transaction(root: Path) -> None:
    """恢复中断的转入待审动作，避免来源/目标/审计只写入一部分。"""
    raw = _optional_admission_bytes(root, ADMISSION_TRANSACTION_PATH)
    if raw is None:
        return
    try:
        transaction = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise ReviewWorkflowError("发现无法解析的转入待审事务标记；请人工检查后再提交") from error
    transaction = _validate_admission_transaction(root, transaction)
    source = _admission_source_by_id(root, transaction["source_id"])
    if source.get("sha256") != transaction["source_sha256"]:
        raise ReviewWorkflowError("来源 sha256 已变化，不能恢复旧的转入待审事务")
    audit = transaction["audit"]
    audit_bytes = _optional_admission_bytes(root, transaction["audit_relative_path"])
    expected_audit_bytes = json_bytes(audit)
    target_states: list[str] = []
    for target in transaction["targets"]:
        target_bytes = _optional_bytes(root, target["target_relative_path"])
        if _json_matches(target_bytes, target["updated_target"]):
            target_states.append("updated")
        elif _json_matches(target_bytes, target["original_target"]):
            target_states.append("original")
        else:
            raise ReviewWorkflowError("转入待审事务目标已被其他操作改动；请人工检查，拒绝覆盖")
    source_is_after = source.get("status") == transaction["next_status"] and source.get("exceptions") == []
    source_is_before = source.get("status") == transaction["previous_status"] and source.get("exceptions") == []
    if source_is_after:
        if audit_bytes is None:
            _write_admission_exclusive(root, transaction["audit_relative_path"], audit)
        elif audit_bytes != expected_audit_bytes:
            raise ReviewWorkflowError("来源已转入待审但同名审计内容不一致；请人工检查")
        if any(state != "updated" for state in target_states):
            raise ReviewWorkflowError("来源已转入待审但目标状态不完整；请人工检查，拒绝回退来源")
        _remove_if_present(root, ADMISSION_TRANSACTION_PATH)
        return
    if source_is_before:
        if audit_bytes is not None and audit_bytes != expected_audit_bytes:
            raise ReviewWorkflowError("未完成转入待审的同名审计内容不一致；请人工检查")
        for target, state in zip(transaction["targets"], target_states):
            if state == "updated":
                write_json(root, target["target_relative_path"], target["original_target"])
        if audit_bytes is not None:
            _remove_if_present(root, transaction["audit_relative_path"])
        _remove_if_present(root, ADMISSION_TRANSACTION_PATH)
        return
    raise ReviewWorkflowError("转入待审事务与当前来源状态不一致；请先人工检查，拒绝覆盖")


def admit_source_for_review(
    library_root: Path | str = LIBRARY_ROOT,
    *,
    source_id: str,
    operator: str,
    summary: str,
    admission_id: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    """将一份无异常的 ``ai_structured`` 来源整体转入待人工复核。

    这不是人工 review：不会创建 ``reviews/review.bbg.*``，不会写 reviewer/decision，
    也不会把任何目标提升为 reviewed。默认仅预览；``--apply`` 才会同时推进当前
    document、全部当前 questions 和来源清单的一步状态，并保存独立审计。
    """
    operator_value = _normalise_text(operator, "operator")
    summary_value = _normalise_text(summary, "summary")
    root = safe_library_root(library_root)

    def prepare() -> dict[str, Any]:
        source, targets, manifest_sha256 = _admission_targets(root, source_id)
        resolved_id, relative_path = _unique_admission_id(root, source_id, admission_id)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        audit = _validate_admission_audit(
            {
                "id": resolved_id,
                "relative_path": relative_path,
                "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "source_id": source_id,
                "source_sha256": source["sha256"],
                "source_relative_path": source["relative_path"],
                "previous_status": "ai_structured",
                "status": "pending_manual_review",
                "operator": operator_value,
                "summary": summary_value,
                "manifest_sha256": manifest_sha256,
                "target_records": [
                    {
                        "target_id": target["record"]["id"],
                        "target_type": target["kind"],
                        "target_relative_path": target["relative_path"],
                        "previous_status": "ai_structured",
                        "status": "pending_manual_review",
                    }
                    for target in targets
                ],
            }
        )
        return {"source": source, "targets": targets, "audit": audit}

    if not apply:
        if _optional_admission_bytes(root, ADMISSION_TRANSACTION_PATH) is not None:
            raise ReviewWorkflowError("存在未恢复的转入待审事务；请显式使用 --apply 触发安全恢复")
        prepared = prepare()
        return {
            "applied": False,
            "source": {
                "id": source_id,
                "previous_status": prepared["source"]["status"],
                "next_status": "pending_manual_review",
                "status_changed": False,
            },
            "audit": prepared["audit"],
            "target_count": len(prepared["targets"]),
            "notice": "预览模式：未写入审计、未改 document/question，也未改变 sources/sources.jsonl。传入 --apply 才会执行。",
        }

    with _review_lock(root):
        _recover_pending_admission_transaction(root)
        _recover_pending_transaction(root)
        prepared = prepare()
        source = prepared["source"]
        targets = prepared["targets"]
        audit = prepared["audit"]
        transaction = {
            "source_id": source_id,
            "source_sha256": source["sha256"],
            "previous_status": source["status"],
            "next_status": "pending_manual_review",
            "targets": [
                {
                    "target_relative_path": target["relative_path"],
                    "original_target": copy.deepcopy(target["record"]),
                    "updated_target": _admitted_target_record(target),
                }
                for target in targets
            ],
            "audit_relative_path": audit["relative_path"],
            "audit": audit,
        }
        if _optional_admission_bytes(root, ADMISSION_TRANSACTION_PATH) is not None:
            raise ReviewWorkflowError("已有未恢复的转入待审事务，拒绝覆盖")
        try:
            write_json(root, ADMISSION_TRANSACTION_PATH, transaction)
            _write_admission_exclusive(root, audit["relative_path"], audit)
            for target in transaction["targets"]:
                write_json(root, target["target_relative_path"], target["updated_target"])
            update_source_state(
                root,
                source_id,
                status="pending_manual_review",
                expected_sha256=source["sha256"],
                expected_status="ai_structured",
                expected_exceptions=[],
            )
            _recover_pending_admission_transaction(root)
        except (OSError, PipelineError, SourceStateError, ReviewWorkflowError) as error:
            try:
                _recover_pending_admission_transaction(root)
            except ReviewWorkflowError:
                pass
            raise ReviewWorkflowError(f"转入人工复核失败；未完成事务已保留或恢复：{error}") from error
    return {
        "applied": True,
        "source": {
            "id": source_id,
            "previous_status": source["status"],
            "next_status": "pending_manual_review",
            "status_changed": True,
        },
        "audit": audit,
        "target_count": len(targets),
        "notice": "已只将这一份来源转入待人工复核；未创建人工 review，原始 Word 未被写入。",
    }


def _validate_outcome(
    target: dict[str, Any],
    *,
    decision: str,
    result_status: str,
    issues: list[str],
    resolved_issues: list[str],
) -> None:
    if decision not in DECISIONS:
        raise ReviewWorkflowError(f"decision 非法：{decision!r}")
    if result_status not in RESULT_STATUSES:
        raise ReviewWorkflowError(f"status 非法：{result_status!r}")
    record = target["record"]
    current_status = record.get("status")
    if current_status not in {"pending_manual_review", "reviewed", "published", "blocked"}:
        raise ReviewWorkflowError("目标必须先进入 pending_manual_review，不能跳过状态链")
    current_issues = _record_issues(record)
    if target["kind"] == "question" and record.get("review_status") != current_status:
        raise ReviewWorkflowError("question 的 status 与 review_status 不一致；请先修复记录")

    if decision == "approved":
        if result_status not in APPROVED_STATUSES:
            raise ReviewWorkflowError("approved 只能提交为 reviewed 或 published")
        if issues:
            raise ReviewWorkflowError("approved 不得附带未解决 issues；请改为 needs_changes 或 blocked")
        missing_resolutions = [issue for issue in current_issues if issue not in resolved_issues]
        extra_resolutions = [issue for issue in resolved_issues if issue not in current_issues]
        if missing_resolutions or extra_resolutions:
            details: list[str] = []
            if missing_resolutions:
                details.append("未逐项确认：" + "；".join(missing_resolutions))
            if extra_resolutions:
                details.append("不存在于当前目标：" + "；".join(extra_resolutions))
            raise ReviewWorkflowError(
                "目标仍有未解决 issues；实际核对确认后，须用 --resolve-issue 逐项声明："
                + "；".join(details)
            )
        if current_status == "blocked":
            raise ReviewWorkflowError("blocked 目标必须先完成修复和重新结构化")
        if result_status == "reviewed" and current_status == "published":
            raise ReviewWorkflowError("published 目标不能退回 reviewed；如发现问题请提交 blocked")
        if result_status == "published":
            if current_status != "reviewed":
                raise ReviewWorkflowError("published 前必须已有一次单独的 reviewed 人工复核")
            if target["kind"] == "question":
                knowledge_ids = record.get("knowledge_ids")
                if not isinstance(knowledge_ids, list) or not knowledge_ids:
                    raise ReviewWorkflowError("已发布 question 必须至少关联一个 knowledge_id")
    elif decision in {"needs_changes", "rejected"}:
        if current_status == "blocked":
            raise ReviewWorkflowError("blocked 目标必须先完成修复和重新结构化，不能直接恢复待审")
        if resolved_issues:
            raise ReviewWorkflowError("needs_changes/rejected 不得声明 resolved_issues")
        if result_status != "pending_manual_review":
            raise ReviewWorkflowError("needs_changes/rejected 必须保持 pending_manual_review")
        if not issues:
            raise ReviewWorkflowError("needs_changes/rejected 必须至少记录一项具体 issues")
        if current_status == "published":
            raise ReviewWorkflowError("已发布目标不能直接退回待审；如发现严重问题请提交 blocked")
    else:  # blocked
        if resolved_issues:
            raise ReviewWorkflowError("blocked 不得声明 resolved_issues")
        if result_status != "blocked":
            raise ReviewWorkflowError("blocked 决定必须写为 blocked 状态")
        if not issues:
            raise ReviewWorkflowError("blocked 必须至少记录一项具体 issues")


def _updated_target_record(
    target: dict[str, Any], *, result_status: str, new_issues: list[str]
) -> dict[str, Any]:
    record = copy.deepcopy(target["record"])
    if result_status in {"pending_manual_review", "blocked"}:
        record["issues"] = _normalise_issues([*_record_issues(record), *new_issues])
    elif result_status in APPROVED_STATUSES:
        # _validate_outcome 已确保 resolved_issues 与既有 issues 一一对应；批准后不再
        # 留下“未解决”标记，具体已解决项写入正式 review JSON 留痕。
        record["issues"] = []
    record["status"] = result_status
    if target["kind"] == "question":
        record["review_status"] = result_status
    return record


def submit_review(
    library_root: Path | str = LIBRARY_ROOT,
    *,
    target_id: str,
    reviewer: str,
    decision: str,
    result_status: str,
    summary: str,
    issues: Iterable[object] | None = None,
    resolved_issues: Iterable[object] | None = None,
    review_id: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    """预览或提交一条单目标人工复核。

    ``apply=False`` 是默认的无写入预览。真正提交持有资料库内互斥锁，并留下可恢复
    的短事务标记：review 与目标记录要么一起生效，要么下次提交前被安全恢复。来源
    清单状态永远不在这里自动提升，避免单题通过被误记成整份 Word 已发布。
    """
    reviewer_value = _normalise_text(reviewer, "reviewer")
    summary_value = _normalise_text(summary, "summary")
    issue_values = _normalise_issues(issues)
    resolved_issue_values = _normalise_issues(resolved_issues)

    def prepare(root: Path, *, create_parent: bool) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        _, target, source = _target_context(root, target_id)
        _validate_outcome(
            target,
            decision=decision,
            result_status=result_status,
            issues=issue_values,
            resolved_issues=resolved_issue_values,
        )
        generated_review_id, review_relative_path = _unique_review_id(
            root, target_id, review_id, create_parent=create_parent
        )
        target_record = _updated_target_record(
            target,
            result_status=result_status,
            new_issues=issue_values,
        )
        review_record: dict[str, Any] = {
            "id": generated_review_id,
            "relative_path": review_relative_path,
            "status": result_status,
            "target_id": target_id,
            "target_relative_path": target["relative_path"],
            "reviewer": reviewer_value,
            "decision": decision,
            "summary": summary_value,
            "issues": issue_values,
        }
        if resolved_issue_values:
            review_record["resolved_issues"] = resolved_issue_values
        result = {
            "applied": bool(apply),
            "review": review_record,
            "target": {
                "id": target_id,
                "type": target["kind"],
                "relative_path": target["relative_path"],
                "previous_status": target["record"].get("status"),
                "next_status": result_status,
            },
            "source": {
                "id": source["id"],
                "status": source.get("status"),
                "status_changed": False,
            },
            "notice": (
                "仅提交一个 target；来源清单状态未自动提升。请在所有相关文档和题目均完成"
                "真实人工复核后，再单独处理来源级发布。"
            ),
        }
        return result, target, target_record

    root = safe_library_root(library_root)
    if not apply:
        result, _, _ = prepare(root, create_parent=False)
        result["notice"] = "预览模式：未写入 review JSON，也未改变目标状态。传入 --apply 才会执行。"
        return result

    with _review_lock(root):
        _recover_pending_admission_transaction(root)
        _recover_pending_transaction(root)
        result, target, target_record = prepare(root, create_parent=True)
        transaction = {
            "target_relative_path": target["relative_path"],
            "original_target": copy.deepcopy(target["record"]),
            "updated_target": target_record,
            "review_relative_path": result["review"]["relative_path"],
            "review": result["review"],
        }
        if _optional_bytes(root, TRANSACTION_PATH) is not None:
            raise ReviewWorkflowError("已有未恢复的人工复核事务，拒绝覆盖")
        try:
            write_json(root, TRANSACTION_PATH, transaction)
            _write_json_exclusive(root, result["review"]["relative_path"], result["review"])
            write_json(root, target["relative_path"], target_record)
            _recover_pending_transaction(root)
        except ReviewWorkflowError:
            raise
        except (OSError, PipelineError) as error:
            raise ReviewWorkflowError(f"提交人工复核失败；下次提交前会尝试恢复事务：{error}") from error
        return result


def _checklist_arguments(parser: argparse.ArgumentParser) -> None:
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--source-id", help="为该来源的 document/question 生成核对单")
    selector.add_argument("--target-id", help="仅为一条 document 或 question 生成核对单")
    parser.add_argument(
        "--output",
        help="可选：写入 reviews/worklists/ 下的 .md 相对路径；不提供时输出到终端",
    )
    parser.add_argument("--json", action="store_true", help="输出机器可读的核对单数据")


def _submit_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--target-id", required=True, help="待复核的 document 或 question ID")
    parser.add_argument("--reviewer", required=True, help="实际完成核对的人员标识")
    parser.add_argument("--decision", required=True, choices=DECISIONS, help="人工结论")
    parser.add_argument(
        "--status",
        dest="result_status",
        required=True,
        choices=RESULT_STATUSES,
        help="本次结论后的目标状态",
    )
    parser.add_argument("--summary", required=True, help="实际核对的范围和结论")
    parser.add_argument("--issue", action="append", default=[], help="未通过/阻断时的具体问题；可重复")
    parser.add_argument(
        "--resolve-issue",
        action="append",
        default=[],
        help="approved 时逐项确认已解决的既有 issue；文字必须与当前记录完全一致，可重复",
    )
    parser.add_argument("--review-id", help="可选的唯一 review.bbg.* ID；默认自动生成")
    parser.add_argument("--apply", action="store_true", help="真正写入 review JSON 并更新这一个目标")
    parser.add_argument("--json", action="store_true", help="输出机器可读结果")


def _admit_source_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-id", required=True, help="唯一待转入人工复核的完整 source ID")
    parser.add_argument("--operator", required=True, help="执行转入动作的本地操作人标识；不是 reviewer")
    parser.add_argument("--summary", required=True, help="本次转入待审的范围和原因")
    parser.add_argument("--admission-id", help="可选的唯一 admission.bbg.* 审计 ID；默认自动生成")
    parser.add_argument("--apply", action="store_true", help="真正写入审计并单步更新这一份来源及当前目标")
    parser.add_argument("--json", action="store_true", help="输出机器可读结果")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成并提交步步高单条人工复核记录")
    subparsers = parser.add_subparsers(dest="command", required=True)
    checklist_parser = subparsers.add_parser("checklist", help="生成只读人工核对单")
    _checklist_arguments(checklist_parser)
    admission_parser = subparsers.add_parser(
        "admit-source", help="预览或将一份 ai_structured 来源转入待人工复核"
    )
    _admit_source_arguments(admission_parser)
    submit_parser = subparsers.add_parser("submit", help="预览或提交一条正式人工复核")
    _submit_arguments(submit_parser)
    args = parser.parse_args(argv)
    try:
        root = official_library_root()
        if args.command == "checklist":
            checklist = build_checklist(root, source_id=args.source_id, target_id=args.target_id)
            if args.output:
                result = write_checklist(
                    root,
                    output_relative_path=args.output,
                    source_id=args.source_id,
                    target_id=args.target_id,
                )
                if args.json:
                    print(json_bytes(result).decode("utf-8"), end="")
                else:
                    print(f"已写入只读核对单：{result['path']}（{result['target_count']} 条目标）")
            elif args.json:
                output = dict(checklist)
                output.pop("root", None)
                print(json_bytes(output).decode("utf-8"), end="")
            else:
                print(render_checklist(checklist), end="")
            return 0
        if args.command == "admit-source":
            result = admit_source_for_review(
                root,
                source_id=args.source_id,
                operator=args.operator,
                summary=args.summary,
                admission_id=args.admission_id,
                apply=args.apply,
            )
            if args.json:
                print(json_bytes(result).decode("utf-8"), end="")
            elif result["applied"]:
                print(
                    f"已将 {result['source']['id']} 转入 pending_manual_review；"
                    f"审计：{result['audit']['relative_path']}。未创建人工 review。"
                )
            else:
                print(
                    f"预览通过：将把 {result['source']['id']} 及 {result['target_count']} 条当前目标转入 "
                    "pending_manual_review；未写入任何文件。确认无误后加 --apply。"
                )
            return 0
        result = submit_review(
            root,
            target_id=args.target_id,
            reviewer=args.reviewer,
            decision=args.decision,
            result_status=args.result_status,
            summary=args.summary,
            issues=args.issue,
            resolved_issues=args.resolve_issue,
            review_id=args.review_id,
            apply=args.apply,
        )
        if args.json:
            print(json_bytes(result).decode("utf-8"), end="")
        elif result["applied"]:
            print(
                f"已提交 {result['target']['id']} 的 {result['target']['next_status']} 人工复核；"
                f"正式记录：{result['review']['relative_path']}。"
            )
        else:
            print(
                f"预览通过：将把 {result['target']['id']} 设为 {result['target']['next_status']}；"
                "未写入任何文件。确认无误后加 --apply。"
            )
        return 0
    except (OSError, PipelineError, ReviewWorkflowError, ValueError) as error:
        print(f"人工复核操作失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
