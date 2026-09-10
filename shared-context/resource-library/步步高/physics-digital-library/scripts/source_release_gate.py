#!/usr/bin/env python3
"""步步高资料库的单来源人工发布门。

``review_workflow.py`` 只复核一份 document 或一条 question，刻意不会因为局部
通过而提升来源状态。本脚本补上来源级的最后一道门：在同一份 Word 的当前
document 和全部当前 questions 均已有真实的 approved 人工复核后，才允许把
``sources/sources.jsonl`` 中这一份来源从 ``pending_manual_review`` 依次提升为
``reviewed``、``published``。

默认永远是预览。传入 ``--apply`` 后，脚本只处理一个 ``source_id``，并把每一项
已显式处理的 manifest exception、目标复核凭据和人工结论写入
``reports/source-releases/``。原始 ``raw/`` 与原始 Word 从不在可写范围内。
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

import review_workflow  # noqa: E402
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
)
from source_state import (  # noqa: E402
    SOURCE_ID_RE,
    SourceStateError,
    read_source_manifest,
    update_source_state,
)


RELEASE_ID_RE = re.compile(r"^release\.bbg\.[a-z0-9][a-z0-9._-]*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RELEASE_PATH_PREFIX = "reports/source-releases/"
LOCK_PATH = f"{RELEASE_PATH_PREFIX}.source-release-gate.lock"
TRANSACTION_PATH = f"{RELEASE_PATH_PREFIX}.source-release-gate.pending"
RELEASE_STATUSES = ("reviewed", "published")
RELEASE_RECORD_FIELDS = frozenset(
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
TRANSACTION_FIELDS = frozenset(
    {
        "source_id",
        "source_sha256",
        "previous_status",
        "next_status",
        "exceptions_before",
        "resolved_exceptions",
        "audit_relative_path",
        "audit",
    }
)


class SourceReleaseGateError(RuntimeError):
    """来源不满足人工发布条件或安全写入边界时抛出。"""


@contextmanager
def _release_lock(root: Path):
    """串行化来源发布，防止两个发布动作覆盖同一份清单状态。"""
    target = safe_output_path(root, LOCK_PATH)
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(target, flags, 0o600)
    except OSError as error:
        raise SourceReleaseGateError(f"无法取得来源发布锁：{error}") from error
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _normalise_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SourceReleaseGateError(f"{field} 必须是非空文本")
    return value.strip()


def _normalise_items(values: Iterable[object] | None, field: str) -> list[str]:
    if values is None:
        return []
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise SourceReleaseGateError(f"{field} 只能包含非空文本")
        item = value.strip()
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def _is_safe_release_path(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith(RELEASE_PATH_PREFIX) or not value.endswith(".json"):
        return False
    if "\\" in value or value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        return False
    path = PurePosixPath(value)
    return "." not in path.parts and ".." not in path.parts


def _is_safe_release_internal_path(value: object) -> bool:
    """允许读取发布门自己的审计、锁和短事务标记。"""
    if not isinstance(value, str) or not value.startswith(RELEASE_PATH_PREFIX):
        return False
    if "\\" in value or value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        return False
    path = PurePosixPath(value)
    if "." in path.parts or ".." in path.parts:
        return False
    return value.endswith((".json", ".pending", ".lock"))


def _release_path(release_id: str) -> str:
    if not RELEASE_ID_RE.fullmatch(release_id):
        raise SourceReleaseGateError("release_id 必须符合 release.bbg.<小写标识> 格式")
    return f"{RELEASE_PATH_PREFIX}{release_id}.json"


def _safe_existing_path(root: Path, relative_path: str) -> Path | None:
    """只读检查一个候选审计路径，不因预览而创建目录。"""
    if not _is_safe_release_path(relative_path):
        raise SourceReleaseGateError("来源发布审计路径不安全")
    target = root.joinpath(*PurePosixPath(relative_path).parts)
    current = root
    for component in target.relative_to(root).parts[:-1]:
        current = current / component
        if not current.exists():
            return None
        if current.is_symlink() or not current.is_dir():
            raise SourceReleaseGateError("来源发布审计目录不是安全普通目录")
    if target.is_symlink():
        raise SourceReleaseGateError("来源发布审计文件不能是符号链接")
    return target if target.exists() else None


def _unique_release_id(root: Path, source_id: str, status: str, requested_id: str | None) -> tuple[str, str]:
    if requested_id is not None:
        release_id = _normalise_text(requested_id, "release_id")
        relative_path = _release_path(release_id)
        if _safe_existing_path(root, relative_path) is not None:
            raise SourceReleaseGateError("release_id 已存在；来源发布审计不可覆盖")
        return release_id, relative_path

    source_short = source_id.rsplit(".", 1)[-1][:16]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dt%H%M%Sz").lower()
    base = f"release.bbg.{source_short}.{status}.{timestamp}"
    for sequence in range(1, 10_000):
        release_id = base if sequence == 1 else f"{base}-{sequence:03d}"
        relative_path = _release_path(release_id)
        if _safe_existing_path(root, relative_path) is None:
            return release_id, relative_path
    raise SourceReleaseGateError("无法生成唯一的来源发布审计 ID")


def _optional_bytes(root: Path, relative_path: str) -> bytes | None:
    if not _is_safe_release_internal_path(relative_path):
        raise SourceReleaseGateError("来源发布内部文件路径不安全")
    target = root.joinpath(*PurePosixPath(relative_path).parts)
    current = root
    for component in target.relative_to(root).parts[:-1]:
        current = current / component
        if not current.exists():
            return None
        if current.is_symlink() or not current.is_dir():
            raise SourceReleaseGateError(f"来源发布目录必须是普通目录：{relative_path}")
    if not target.exists():
        return None
    if target.is_symlink() or not target.is_file():
        raise SourceReleaseGateError(f"来源发布文件必须是普通文件：{relative_path}")
    try:
        return target.read_bytes()
    except OSError as error:
        raise SourceReleaseGateError(f"无法读取来源发布文件：{relative_path}（{error}）") from error


def _write_json_exclusive(root: Path, relative_path: str, value: dict[str, Any]) -> None:
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
        raise SourceReleaseGateError("来源发布审计文件已存在，拒绝覆盖") from error
    except OSError as error:
        raise SourceReleaseGateError(f"无法写入来源发布审计：{error}") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _remove_if_present(root: Path, relative_path: str) -> None:
    try:
        remove_generated_file(root, relative_path)
    except PipelineError as error:
        raise SourceReleaseGateError(f"无法清理来源发布临时文件：{error}") from error


def _source_by_id(root: Path, source_id: str) -> dict[str, Any]:
    try:
        sources = read_source_manifest(root)
    except SourceStateError as error:
        raise SourceReleaseGateError(f"无法读取来源清单：{error}") from error
    matches = [source for source in sources if source.get("id") == source_id]
    if len(matches) != 1:
        raise SourceReleaseGateError("来源清单中未找到唯一 source_id")
    return dict(matches[0])


def _target_reviews(resolution: Any, source_id: str, release_status: str) -> list[dict[str, Any]]:
    """验证单来源的所有当前目标均有与当前状态一致的 approved review。"""
    documents = [
        (relative_path, record)
        for relative_path, record in resolution.records["document"]
        if record.get("source_id") == source_id
    ]
    questions = [
        (relative_path, record)
        for relative_path, record in resolution.records["question"]
        if record.get("source_id") == source_id
    ]
    if len(documents) != 1:
        raise SourceReleaseGateError("该来源必须恰有一份当前 document；缺失、重复或过期记录均不能发布")

    approved: dict[tuple[str, str], list[str]] = {}
    for review_path, review in resolution.declared_records["review"]:
        if review.get("decision") != "approved":
            continue
        target_id = review.get("target_id")
        review_status = review.get("status")
        if isinstance(target_id, str) and isinstance(review_status, str):
            approved.setdefault((target_id, review_status), []).append(review_path)

    evidence: list[dict[str, Any]] = []
    for target_type, records in (("document", documents), ("question", questions)):
        for relative_path, record in records:
            target_id = record.get("id")
            target_status = record.get("status")
            if not isinstance(target_id, str) or target_status not in {"reviewed", "published"}:
                raise SourceReleaseGateError(
                    f"{target_type} 尚未完成当前人工复核：{relative_path}"
                )
            if release_status == "published" and target_status != "published":
                raise SourceReleaseGateError(
                    f"来源发布前所有 {target_type} 必须已发布：{relative_path}"
                )
            if target_type == "question" and record.get("review_status") != target_status:
                raise SourceReleaseGateError(
                    f"question 的 status/review_status 不一致：{relative_path}"
                )
            matching_paths = sorted(approved.get((target_id, target_status), []))
            if not matching_paths:
                raise SourceReleaseGateError(
                    f"{target_type} 缺少与当前状态一致的 approved 人工 review：{relative_path}"
                )
            evidence.append(
                {
                    "target_id": target_id,
                    "target_type": target_type,
                    "target_relative_path": relative_path,
                    "target_status": target_status,
                    "approved_review_paths": matching_paths,
                }
            )
    return sorted(evidence, key=lambda item: (item["target_type"], item["target_relative_path"]))


def _validate_source_status(source: dict[str, Any], requested_status: str) -> None:
    current_status = source.get("status")
    if current_status == "ai_structured":
        raise SourceReleaseGateError("来源仍为 ai_structured，必须先进入 pending_manual_review 并完成真实人工复核")
    if current_status == "blocked":
        raise SourceReleaseGateError("来源已 blocked，必须先修复并重新处理，不能直接发布")
    expected_previous = "pending_manual_review" if requested_status == "reviewed" else "reviewed"
    if current_status != expected_previous:
        raise SourceReleaseGateError(
            f"来源状态必须从 {expected_previous} 单步变为 {requested_status}，当前为 {current_status!r}"
        )


def _validate_exception_resolutions(source: dict[str, Any], resolved_exceptions: list[str]) -> list[str]:
    exceptions = source.get("exceptions")
    if not isinstance(exceptions, list) or any(not isinstance(item, str) or not item for item in exceptions):
        raise SourceReleaseGateError("来源清单 exceptions 不是有效字符串数组")
    before = list(exceptions)
    missing = [item for item in before if item not in resolved_exceptions]
    extra = [item for item in resolved_exceptions if item not in before]
    if missing or extra:
        details: list[str] = []
        if missing:
            details.append("未逐项处理：" + "；".join(missing))
        if extra:
            details.append("清单中不存在：" + "；".join(extra))
        raise SourceReleaseGateError(
            "来源存在 exceptions 时，必须通过 --resolve-exception 逐项精确声明处理结果："
            + "；".join(details)
        )
    return before


def _validate_audit_record(audit: object) -> dict[str, Any]:
    if not isinstance(audit, dict):
        raise SourceReleaseGateError("来源发布审计必须是对象")
    missing = sorted(RELEASE_RECORD_FIELDS - set(audit))
    unexpected = sorted(set(audit) - RELEASE_RECORD_FIELDS)
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append("缺少字段：" + ", ".join(missing))
        if unexpected:
            details.append("不允许字段：" + ", ".join(unexpected))
        raise SourceReleaseGateError("来源发布审计字段无效：" + "；".join(details))
    record = dict(audit)
    release_id = record.get("id")
    relative_path = record.get("relative_path")
    if (
        not isinstance(release_id, str)
        or not RELEASE_ID_RE.fullmatch(release_id)
        or not isinstance(relative_path, str)
        or relative_path != _release_path(release_id)
        or not _is_safe_release_path(relative_path)
    ):
        raise SourceReleaseGateError("来源发布审计 ID 或路径无效")
    if not isinstance(record.get("source_id"), str) or not SOURCE_ID_RE.fullmatch(record["source_id"]):
        raise SourceReleaseGateError("来源发布审计 source_id 无效")
    if not isinstance(record.get("source_sha256"), str) or not SHA256_RE.fullmatch(record["source_sha256"]):
        raise SourceReleaseGateError("来源发布审计 source_sha256 无效")
    if record["source_id"] != f"src.bbg.{record['source_sha256']}":
        raise SourceReleaseGateError("来源发布审计 source_id 必须与 sha256 匹配")
    if (
        not isinstance(record.get("source_relative_path"), str)
        or not is_safe_relative_path(record["source_relative_path"])
        or not record["source_relative_path"].startswith("raw/")
    ):
        raise SourceReleaseGateError("来源发布审计 source_relative_path 无效")
    if record.get("previous_status") not in {"pending_manual_review", "reviewed"}:
        raise SourceReleaseGateError("来源发布审计 previous_status 无效")
    if record.get("status") not in RELEASE_STATUSES:
        raise SourceReleaseGateError("来源发布审计 status 无效")
    expected_previous = "pending_manual_review" if record["status"] == "reviewed" else "reviewed"
    if record["previous_status"] != expected_previous:
        raise SourceReleaseGateError("来源发布审计状态链不连续")
    if record.get("decision") != "approved":
        raise SourceReleaseGateError("来源发布审计 decision 必须为 approved")
    _normalise_text(record.get("reviewer"), "来源发布审计 reviewer")
    _normalise_text(record.get("summary"), "来源发布审计 summary")
    created_at = record.get("created_at")
    if not isinstance(created_at, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", created_at):
        raise SourceReleaseGateError("来源发布审计 created_at 必须是 UTC ISO 时间")
    if not isinstance(record.get("manifest_sha256"), str) or not SHA256_RE.fullmatch(record["manifest_sha256"]):
        raise SourceReleaseGateError("来源发布审计 manifest_sha256 无效")
    for field in (
        "manifest_exceptions_before",
        "resolved_exceptions",
        "manifest_exceptions_after",
    ):
        values = record.get(field)
        if not isinstance(values, list) or any(not isinstance(item, str) or not item for item in values):
            raise SourceReleaseGateError(f"来源发布审计 {field} 必须是非空字符串数组")
        if len(values) != len(set(values)):
            raise SourceReleaseGateError(f"来源发布审计 {field} 不允许重复")
    if record["manifest_exceptions_before"] != record["resolved_exceptions"]:
        raise SourceReleaseGateError("来源发布审计必须逐项记录所有原有 exceptions 的处理")
    if record["manifest_exceptions_after"] != []:
        raise SourceReleaseGateError("来源发布审计完成后 exceptions 必须为空")
    targets = record.get("target_reviews")
    if not isinstance(targets, list) or not targets:
        raise SourceReleaseGateError("来源发布审计必须保留至少一份 document 的人工复核凭据")
    seen_targets: set[str] = set()
    document_count = 0
    source_short = record["source_sha256"][:16]
    source_id = record["source_id"]
    for target in targets:
        if not isinstance(target, dict) or set(target) != {
            "target_id",
            "target_type",
            "target_relative_path",
            "target_status",
            "approved_review_paths",
        }:
            raise SourceReleaseGateError("来源发布审计 target_reviews 条目无效")
        target_id = target.get("target_id")
        target_type = target.get("target_type")
        target_path = target.get("target_relative_path")
        target_status = target.get("target_status")
        review_paths = target.get("approved_review_paths")
        if not isinstance(target_id, str) or not target_id or target_id in seen_targets:
            raise SourceReleaseGateError("来源发布审计 target_reviews 的 target_id 无效或重复")
        seen_targets.add(target_id)
        if target_type not in {"document", "question"}:
            raise SourceReleaseGateError("来源发布审计 target_reviews 的 target_type 无效")
        expected_prefix = "records/documents/" if target_type == "document" else "questions/"
        expected_id = f"doc.bbg.{source_short}" if target_type == "document" else None
        if (
            (expected_id is not None and target_id != expected_id)
            or (
                target_type == "question"
                and not re.fullmatch(rf"q\.{re.escape(source_id)}\.\d{{3}}", target_id)
            )
            or not isinstance(target_path, str)
            or not is_safe_relative_path(target_path)
            or not target_path.startswith(expected_prefix)
            or not target_path.endswith(".json")
        ):
            raise SourceReleaseGateError("来源发布审计 target_reviews 的目标路径无效")
        if target_status not in {"reviewed", "published"}:
            raise SourceReleaseGateError("来源发布审计 target_reviews 的目标状态无效")
        if record["status"] == "published" and target_status != "published":
            raise SourceReleaseGateError("published 来源审计不能包含未 published 的目标")
        if not isinstance(review_paths, list) or not review_paths or any(
            not isinstance(item, str)
            or not is_safe_relative_path(item)
            or not item.startswith("reviews/review.bbg.")
            or not item.endswith(".json")
            for item in review_paths
        ):
            raise SourceReleaseGateError("来源发布审计必须保留 approved review 路径")
        if len(review_paths) != len(set(review_paths)):
            raise SourceReleaseGateError("来源发布审计 approved review 路径不允许重复")
        if target_type == "document":
            document_count += 1
    if document_count != 1:
        raise SourceReleaseGateError("来源发布审计必须且只能含一份 document 凭据")
    return record


def _prepare_release(
    root: Path,
    *,
    source_id: str,
    reviewer: str,
    result_status: str,
    summary: str,
    resolved_exceptions: list[str],
    release_id: str | None,
) -> dict[str, Any]:
    if not isinstance(source_id, str) or not SOURCE_ID_RE.fullmatch(source_id):
        raise SourceReleaseGateError("source_id 必须是完整 src.bbg.<sha256> ID")
    if result_status not in RELEASE_STATUSES:
        raise SourceReleaseGateError("来源发布 status 只能是 reviewed 或 published")
    try:
        resolution = require_current_records(root)
    except CurrentRecordsError as error:
        raise SourceReleaseGateError(
            f"资料库当前记录未通过一致性校验（包括孤儿数据、缺失或过期记录），拒绝来源发布：{error}"
        ) from error
    source_matches = [source for _, source in resolution.sources if source.get("id") == source_id]
    if len(source_matches) != 1:
        raise SourceReleaseGateError("当前来源清单中未找到唯一 source_id")
    source = dict(source_matches[0])
    _validate_source_status(source, result_status)
    exceptions_before = _validate_exception_resolutions(source, resolved_exceptions)
    # ``--resolve-exception`` 是逐项确认，不要求使用者按清单顺序输入；审计统一按
    # manifest 原顺序保存，既便于比对，也避免同一组确认因参数顺序不同而失败。
    resolved_exceptions = list(exceptions_before)
    target_evidence = _target_reviews(resolution, source_id, result_status)
    resolved_id, relative_path = _unique_release_id(root, source_id, result_status, release_id)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    audit = _validate_audit_record(
        {
            "id": resolved_id,
            "relative_path": relative_path,
            "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_id": source_id,
            "source_sha256": source["sha256"],
            "source_relative_path": source["relative_path"],
            "previous_status": source["status"],
            "status": result_status,
            "reviewer": reviewer,
            "decision": "approved",
            "summary": summary,
            "manifest_sha256": resolution.manifest_sha256,
            "manifest_exceptions_before": exceptions_before,
            "resolved_exceptions": resolved_exceptions,
            "manifest_exceptions_after": [],
            "target_reviews": target_evidence,
        }
    )
    return {
        "root": root,
        "source": source,
        "audit": audit,
        "target_count": len(target_evidence),
    }


def _validate_pending_transaction(root: Path, value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != TRANSACTION_FIELDS:
        raise SourceReleaseGateError("来源发布事务标记字段无效；请人工检查后再提交")
    source_id = value.get("source_id")
    source_sha256 = value.get("source_sha256")
    previous_status = value.get("previous_status")
    next_status = value.get("next_status")
    exceptions_before = value.get("exceptions_before")
    resolved_exceptions = value.get("resolved_exceptions")
    audit_path = value.get("audit_relative_path")
    audit = _validate_audit_record(value.get("audit"))
    if (
        not isinstance(source_id, str)
        or not SOURCE_ID_RE.fullmatch(source_id)
        or not isinstance(source_sha256, str)
        or not SHA256_RE.fullmatch(source_sha256)
        or source_id != f"src.bbg.{source_sha256}"
        or previous_status not in {"pending_manual_review", "reviewed"}
        or next_status not in RELEASE_STATUSES
        or not isinstance(exceptions_before, list)
        or not isinstance(resolved_exceptions, list)
        or not isinstance(audit_path, str)
        or not _is_safe_release_path(audit_path)
    ):
        raise SourceReleaseGateError("来源发布事务标记内容无效；请人工检查后再提交")
    if audit_path != audit["relative_path"] or source_id != audit["source_id"] or source_sha256 != audit["source_sha256"]:
        raise SourceReleaseGateError("来源发布事务与审计记录未正确绑定；请人工检查后再提交")
    if previous_status != audit["previous_status"] or next_status != audit["status"]:
        raise SourceReleaseGateError("来源发布事务状态链与审计记录不一致；请人工检查后再提交")
    if exceptions_before != audit["manifest_exceptions_before"] or resolved_exceptions != audit["resolved_exceptions"]:
        raise SourceReleaseGateError("来源发布事务 exceptions 与审计记录不一致；请人工检查后再提交")
    return dict(value)


def _recover_pending_transaction(root: Path) -> None:
    """恢复一次中断的来源发布，避免出现已改状态却没有审计的情况。"""
    raw = _optional_bytes(root, TRANSACTION_PATH)
    if raw is None:
        return
    try:
        transaction = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise SourceReleaseGateError("发现无法解析的来源发布事务标记；请人工检查后再提交") from error
    transaction = _validate_pending_transaction(root, transaction)
    audit = transaction["audit"]
    audit_path = transaction["audit_relative_path"]
    source = _source_by_id(root, transaction["source_id"])
    if source.get("sha256") != transaction["source_sha256"]:
        raise SourceReleaseGateError("来源 sha256 已变化，不能恢复旧的来源发布事务")
    before_matches = (
        source.get("status") == transaction["previous_status"]
        and source.get("exceptions") == transaction["exceptions_before"]
    )
    after_matches = source.get("status") == transaction["next_status"] and source.get("exceptions") == []
    audit_bytes = _optional_bytes(root, audit_path)
    expected_audit_bytes = json_bytes(audit)
    if after_matches:
        if audit_bytes is None:
            _write_json_exclusive(root, audit_path, audit)
        elif audit_bytes != expected_audit_bytes:
            raise SourceReleaseGateError("来源已提升但同名审计记录内容不一致；请人工检查")
        _remove_if_present(root, TRANSACTION_PATH)
        return
    if before_matches:
        if audit_bytes is not None:
            if audit_bytes != expected_audit_bytes:
                raise SourceReleaseGateError("未完成来源发布的同名审计记录内容不一致；请人工检查")
            _remove_if_present(root, audit_path)
        _remove_if_present(root, TRANSACTION_PATH)
        return
    raise SourceReleaseGateError("来源发布事务与当前来源状态不一致；请先人工检查，拒绝覆盖")


def release_source(
    library_root: Path | str = LIBRARY_ROOT,
    *,
    source_id: str,
    reviewer: str,
    result_status: str,
    summary: str,
    resolved_exceptions: Iterable[object] | None = None,
    release_id: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    """预览或执行一份来源的 ``reviewed`` / ``published`` 状态提升。

    只接受一个 source ID。预览既不生成审计，也不清空 exceptions，更不会改动
    ``sources.jsonl``。真正写入时，先写可恢复的事务标记和独占审计文件，再调用
    ``source_state.update_source_state`` 做单步原子状态转换。
    """
    reviewer_value = _normalise_text(reviewer, "reviewer")
    summary_value = _normalise_text(summary, "summary")
    resolved_values = _normalise_items(resolved_exceptions, "resolve-exception")
    root = safe_library_root(library_root)

    if not apply:
        if _optional_bytes(root, TRANSACTION_PATH) is not None:
            raise SourceReleaseGateError("存在未恢复的来源发布事务；请显式使用 --apply 触发安全恢复")
        prepared = _prepare_release(
            root,
            source_id=source_id,
            reviewer=reviewer_value,
            result_status=result_status,
            summary=summary_value,
            resolved_exceptions=resolved_values,
            release_id=release_id,
        )
        return {
            "applied": False,
            "source": {
                "id": source_id,
                "previous_status": prepared["source"]["status"],
                "next_status": result_status,
                "status_changed": False,
            },
            "audit": prepared["audit"],
            "target_count": prepared["target_count"],
            "notice": "预览模式：未写入来源发布审计，未清空 exceptions，也未改变 sources/sources.jsonl。传入 --apply 才会执行。",
        }

    try:
        with _release_lock(root):
            # 复核提交使用同一把锁；先取得自己的锁再取得复核锁，避免来源提升与单条
            # review 的状态变更交错。
            with review_workflow._review_lock(root):
                review_workflow._recover_pending_admission_transaction(root)
                _recover_pending_transaction(root)
                prepared = _prepare_release(
                    root,
                    source_id=source_id,
                    reviewer=reviewer_value,
                    result_status=result_status,
                    summary=summary_value,
                    resolved_exceptions=resolved_values,
                    release_id=release_id,
                )
                source = prepared["source"]
                audit = prepared["audit"]
                transaction = {
                    "source_id": source_id,
                    "source_sha256": source["sha256"],
                    "previous_status": source["status"],
                    "next_status": result_status,
                    "exceptions_before": list(source["exceptions"]),
                    "resolved_exceptions": list(audit["resolved_exceptions"]),
                    "audit_relative_path": audit["relative_path"],
                    "audit": audit,
                }
                write_json(root, TRANSACTION_PATH, transaction)
                try:
                    _write_json_exclusive(root, audit["relative_path"], audit)
                    update_source_state(
                        root,
                        source_id,
                        status=result_status,
                        exceptions=[],
                        expected_sha256=source["sha256"],
                        expected_status=source["status"],
                        expected_exceptions=list(source["exceptions"]),
                    )
                    _recover_pending_transaction(root)
                except (OSError, PipelineError, SourceStateError, SourceReleaseGateError) as error:
                    # 若状态尚未写入，恢复逻辑会删掉预写的审计；若状态已写入，则会补齐
                    # 审计。恢复本身无法判断时保留事务供人工检查，绝不静默覆盖。
                    try:
                        _recover_pending_transaction(root)
                    except SourceReleaseGateError:
                        pass
                    raise SourceReleaseGateError(f"来源发布失败；未完成事务已保留或恢复：{error}") from error
    except review_workflow.ReviewWorkflowError as error:
        raise SourceReleaseGateError(f"无法取得人工复核事务锁：{error}") from error

    return {
        "applied": True,
        "source": {
            "id": source_id,
            "previous_status": source["status"],
            "next_status": result_status,
            "status_changed": True,
        },
        "audit": audit,
        "target_count": prepared["target_count"],
        "notice": "已仅提升这一份来源；审计已保留，原始 Word 未被读取后写入。",
    }


def _arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-id", required=True, help="唯一待发布来源的完整 source ID")
    parser.add_argument("--reviewer", required=True, help="实际完成来源级复核的人员标识")
    parser.add_argument("--status", dest="result_status", required=True, choices=RELEASE_STATUSES, help="本次单步提升到的来源状态")
    parser.add_argument("--summary", required=True, help="实际核对范围和来源级结论")
    parser.add_argument(
        "--resolve-exception",
        action="append",
        default=[],
        help="逐项处理 sources.jsonl 中现有 exception；文字必须与清单完全一致，可重复",
    )
    parser.add_argument("--release-id", help="可选的唯一 release.bbg.* 审计 ID；默认自动生成")
    parser.add_argument("--apply", action="store_true", help="真正写入审计并单步更新这一份来源状态")
    parser.add_argument("--json", action="store_true", help="输出机器可读结果")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="发布一份已完成真实人工复核的步步高来源")
    _arguments(parser)
    args = parser.parse_args(argv)
    try:
        result = release_source(
            official_library_root(),
            source_id=args.source_id,
            reviewer=args.reviewer,
            result_status=args.result_status,
            summary=args.summary,
            resolved_exceptions=args.resolve_exception,
            release_id=args.release_id,
            apply=args.apply,
        )
        if args.json:
            print(json_bytes(result).decode("utf-8"), end="")
        elif result["applied"]:
            print(
                f"已将 {result['source']['id']} 从 {result['source']['previous_status']} 提升为 "
                f"{result['source']['next_status']}；审计：{result['audit']['relative_path']}。"
            )
        else:
            print(
                f"预览通过：将把 {result['source']['id']} 从 {result['source']['previous_status']} 提升为 "
                f"{result['source']['next_status']}；未写入任何文件。确认无误后加 --apply。"
            )
        return 0
    except (OSError, PipelineError, SourceStateError, SourceReleaseGateError, ValueError) as error:
        print(f"来源发布操作失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
