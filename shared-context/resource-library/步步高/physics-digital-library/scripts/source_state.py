#!/usr/bin/env python3
"""来源清单处理状态的安全读写契约。

``sources/sources.jsonl`` 的静态来源身份由 ``build_manifest.py`` 从原始 Word
重新计算；本模块只维护可以随处理进度变化的四个字段：状态、输出路径、异常和
工具版本。所有输出路径均为相对正式资料库根的受控生成目录，清单写回采用临时
文件加原子替换，因而不会触碰 ``raw/`` 或原始 Word。
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path, PurePosixPath
from typing import Any


SOURCE_ID_RE = re.compile(r"^src\.bbg\.([0-9a-f]{64})$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
STATE_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SOURCE_STATUSES = (
    "discovered",
    "raw_extracted",
    "ai_structured",
    "pending_manual_review",
    "reviewed",
    "published",
    "blocked",
)
SOURCE_STATE_FIELDS = ("status", "output_paths", "exceptions", "tool_versions")
MANIFEST_RELATIVE_PATH = "sources/sources.jsonl"
OUTPUT_PREFIXES = (
    "records/documents/",
    "questions/",
    "knowledge/",
    "models/",
    "reviews/",
    "reports/",
    "assets/original/",
    "assets/derived/",
)
SOURCE_RECORD_FIELDS = frozenset(
    {
        "id",
        "relative_path",
        "sha256",
        "profile",
        "title",
        "status",
        "output_paths",
        "exceptions",
        "tool_versions",
        "metadata",
    }
)


class SourceStateError(RuntimeError):
    """来源清单状态无法安全读取、转换或写入时抛出。"""


def default_source_state() -> dict[str, object]:
    """返回每个新发现来源都必须拥有的初始处理状态。"""
    return {
        "status": "discovered",
        "output_paths": {},
        "exceptions": [],
        "tool_versions": {},
    }


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def is_safe_relative_path(value: object) -> bool:
    """判断值是否是没有 ``..``、绝对路径或 Windows 分隔符的 POSIX 相对路径。"""
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    if re.match(r"^[A-Za-z]:", value):
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and "." not in path.parts and ".." not in path.parts


def is_safe_output_path(value: object) -> bool:
    """判断来源状态所记录的路径是否位于允许的生成目录。"""
    return isinstance(value, str) and is_safe_relative_path(value) and value.startswith(OUTPUT_PREFIXES)


def _safe_library_root(library_root: Path | str) -> Path:
    root = Path(library_root)
    if root.is_symlink() or not root.is_dir():
        raise SourceStateError("资料库根必须是现有且非符号链接的目录")
    try:
        return root.resolve(strict=True)
    except OSError as error:
        raise SourceStateError(f"无法解析资料库根：{error}") from error


def safe_manifest_path(library_root: Path | str, *, require_exists: bool = True) -> Path:
    """安全取得唯一允许写入的 ``sources/sources.jsonl`` 路径。"""
    root = _safe_library_root(library_root)
    sources_directory = root / "sources"
    if sources_directory.is_symlink() or not sources_directory.is_dir():
        raise SourceStateError("sources 必须是现有且非符号链接的目录")
    target = sources_directory / "sources.jsonl"
    if target.is_symlink():
        raise SourceStateError("sources/sources.jsonl 不能是符号链接")
    if target.exists() and not target.is_file():
        raise SourceStateError("sources/sources.jsonl 必须是普通文件")
    if require_exists and not target.is_file():
        raise SourceStateError("缺少普通文件 sources/sources.jsonl")
    try:
        resolved_parent = sources_directory.resolve(strict=True)
        resolved_target = target.resolve(strict=False)
    except OSError as error:
        raise SourceStateError(f"无法解析 sources/sources.jsonl：{error}") from error
    if not _is_within(resolved_parent, root) or not _is_within(resolved_target, root):
        raise SourceStateError("sources/sources.jsonl 越出正式资料库根")
    return target


def _normalise_string_list(value: object, field: str) -> list[str]:
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        raise SourceStateError(f"{field} 必须是字符串数组")
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item:
            raise SourceStateError(f"{field} 只能包含非空字符串")
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def _normalise_string_mapping(value: object, field: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise SourceStateError(f"{field} 必须是对象")
    result: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not STATE_KEY_RE.fullmatch(key):
            raise SourceStateError(f"{field} 的键格式无效：{key!r}")
        if not isinstance(item, str) or not item:
            raise SourceStateError(f"{field}.{key} 必须是非空字符串")
        result[key] = item
    return {key: result[key] for key in sorted(result)}


def _normalise_output_paths(value: object) -> dict[str, str]:
    paths = _normalise_string_mapping(value, "output_paths")
    for key, path in paths.items():
        if not is_safe_output_path(path):
            raise SourceStateError(f"output_paths.{key} 必须是资料库内允许的相对生成路径")
    return paths


def normalise_source_state(state: Mapping[str, object]) -> dict[str, object]:
    """校验并规范化四个可变来源状态字段，方便获得稳定 JSONL 字节。"""
    missing = [field for field in SOURCE_STATE_FIELDS if field not in state]
    unexpected = sorted(set(state) - set(SOURCE_STATE_FIELDS))
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"缺少字段：{', '.join(missing)}")
        if unexpected:
            details.append(f"不允许字段：{', '.join(unexpected)}")
        raise SourceStateError("来源状态字段不完整：" + "；".join(details))
    status = state["status"]
    if not isinstance(status, str) or status not in SOURCE_STATUSES:
        raise SourceStateError(f"status 非法：{status!r}")
    return {
        "status": status,
        "output_paths": _normalise_output_paths(state["output_paths"]),
        "exceptions": _normalise_string_list(state["exceptions"], "exceptions"),
        "tool_versions": _normalise_string_mapping(state["tool_versions"], "tool_versions"),
    }


def source_state_from_record(record: Mapping[str, object]) -> dict[str, object]:
    """从完整来源记录中提取并校验可保留的处理状态。"""
    return normalise_source_state({field: record[field] for field in SOURCE_STATE_FIELDS})


def source_identity(record: Mapping[str, object]) -> tuple[str, str]:
    """返回经校验的 ``(source_id, sha256)``，防止把状态嫁接到不同内容。"""
    source_id = record.get("id")
    sha256 = record.get("sha256")
    if not isinstance(source_id, str) or not SOURCE_ID_RE.fullmatch(source_id):
        raise SourceStateError(f"来源 ID 格式无效：{source_id!r}")
    if not isinstance(sha256, str) or not SHA256_RE.fullmatch(sha256):
        raise SourceStateError(f"来源 sha256 格式无效：{sha256!r}")
    if source_id != f"src.bbg.{sha256}":
        raise SourceStateError("来源 ID 必须与完整 sha256 匹配")
    return source_id, sha256


def _canonical_source_record(record: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(record, Mapping):
        raise SourceStateError("来源记录必须是对象")
    missing = sorted(SOURCE_RECORD_FIELDS - set(record))
    unexpected = sorted(set(record) - SOURCE_RECORD_FIELDS)
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"缺少字段：{', '.join(missing)}")
        if unexpected:
            details.append(f"不允许字段：{', '.join(unexpected)}")
        raise SourceStateError("来源记录字段不符合契约：" + "；".join(details))
    source_id, sha256 = source_identity(record)
    relative_path = record["relative_path"]
    if not isinstance(relative_path, str) or not is_safe_relative_path(relative_path) or not relative_path.startswith("raw/"):
        raise SourceStateError("来源 relative_path 必须是 raw/ 下的安全相对路径")
    profile = record["profile"]
    if not isinstance(profile, str) or profile not in {"teacher", "gaokao", "textbook"}:
        raise SourceStateError(f"profile 非法：{profile!r}")
    title = record["title"]
    if not isinstance(title, str) or not title:
        raise SourceStateError("title 必须是非空字符串")
    if not isinstance(record["metadata"], Mapping):
        raise SourceStateError("metadata 必须是对象")
    state = source_state_from_record(record)
    return {
        "id": source_id,
        "relative_path": relative_path,
        "sha256": sha256,
        "profile": profile,
        "title": title,
        **state,
        "metadata": dict(record["metadata"]),
    }


def reconcile_source_states(
    fresh_records: Iterable[Mapping[str, object]], previous_records: Iterable[Mapping[str, object]]
) -> list[dict[str, object]]:
    """为新清单回填可安全继承的状态；内容身份变化一律回到初始状态。

    只有旧记录同时拥有相同的完整 source ID 和 SHA-256，且四个状态字段本身合法时
    才继承。旧清单重复身份或状态格式异常时，宁可放弃继承，也不会把不可靠状态
    写给新的来源。
    """
    previous_by_identity: dict[tuple[str, str], Mapping[str, object] | None] = {}
    for record in previous_records:
        try:
            identity = source_identity(record)
        except SourceStateError:
            continue
        if identity in previous_by_identity:
            previous_by_identity[identity] = None
        else:
            previous_by_identity[identity] = record

    reconciled: list[dict[str, object]] = []
    for fresh in fresh_records:
        identity = source_identity(fresh)
        previous = previous_by_identity.get(identity)
        state = default_source_state()
        if previous is not None:
            try:
                state = source_state_from_record(previous)
            except (KeyError, SourceStateError):
                state = default_source_state()
        reconciled.append({**dict(fresh), **state})
    return reconciled


def _manifest_bytes(records: Iterable[Mapping[str, object]]) -> tuple[bytes, list[dict[str, object]]]:
    canonical_records = [_canonical_source_record(record) for record in records]
    canonical_records.sort(key=lambda record: (str(record["relative_path"]), str(record["id"])))
    seen_ids: set[str] = set()
    for record in canonical_records:
        source_id = str(record["id"])
        if source_id in seen_ids:
            raise SourceStateError(f"sources/sources.jsonl 不允许重复 source ID：{source_id}")
        seen_ids.add(source_id)
    content = "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        for record in canonical_records
    )
    return content.encode("utf-8"), canonical_records


def write_source_manifest(library_root: Path | str, records: Iterable[Mapping[str, object]]) -> Path:
    """稳定、原子地写入唯一来源清单；调用方无法把输出导向资料库外。"""
    target = safe_manifest_path(library_root, require_exists=False)
    data, _ = _manifest_bytes(records)
    if target.exists() and target.read_bytes() == data:
        return target
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".source-state-", suffix=".jsonl", dir=target.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if target.is_symlink():
            raise SourceStateError("sources/sources.jsonl 不能是符号链接")
        os.replace(temporary_path, target)
    except BaseException:
        if temporary_path.exists():
            temporary_path.unlink()
        raise
    return target


def read_source_manifest(library_root: Path | str) -> list[dict[str, object]]:
    """读取并规范化完整来源清单，拒绝软链接、重复 ID 和无效状态。"""
    manifest = safe_manifest_path(library_root)
    records: list[dict[str, object]] = []
    try:
        lines = manifest.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise SourceStateError(f"无法读取 sources/sources.jsonl：{error}") from error
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise SourceStateError(f"sources/sources.jsonl 第 {line_number} 行不是 JSON：{error.msg}") from error
        if not isinstance(record, Mapping):
            raise SourceStateError(f"sources/sources.jsonl 第 {line_number} 行必须是对象")
        try:
            records.append(_canonical_source_record(record))
        except SourceStateError as error:
            raise SourceStateError(f"sources/sources.jsonl 第 {line_number} 行无效：{error}") from error
    _, canonical_records = _manifest_bytes(records)
    return canonical_records


def _validate_status_transition(current: str, requested: str) -> None:
    if current == requested:
        return
    if requested == "blocked":
        return
    if current == "blocked":
        # ``blocked`` 是一次明确的复核/处理阻断，不是可任意跳回中间或最终状态的
        # 旁路。流水线会先回到 raw_extracted，来源范围清理会回到 discovered；两者都
        # 会重新生成产物和人工复核凭据。这样旧的 release 审计不能被拿来恢复发布。
        if requested not in {"discovered", "raw_extracted"}:
            raise SourceStateError("blocked 来源只能回到 discovered 或 raw_extracted 后重新处理与复核")
        return
    if current == "published":
        raise SourceStateError("published 来源只能保持 published 或转入 blocked")
    current_index = SOURCE_STATUSES.index(current)
    requested_index = SOURCE_STATUSES.index(requested)
    if requested_index != current_index + 1:
        raise SourceStateError(f"不允许来源状态从 {current} 直接变为 {requested}")


def update_source_state(
    library_root: Path | str,
    source_id: str,
    *,
    status: str | None = None,
    output_paths: Mapping[str, str] | None = None,
    exceptions: Iterable[str] | None = None,
    tool_versions: Mapping[str, str] | None = None,
    expected_sha256: str | None = None,
    expected_status: str | None = None,
    expected_exceptions: Iterable[str] | None = None,
) -> dict[str, object]:
    """更新一份已登记来源的可变处理状态并原子写回清单。

    未提供的状态字段保持原值；传空对象或空数组可显式清空。可选
    ``expected_sha256`` 让流水线确认仍在更新同一份原始 Word，避免并发重建或人工
    替换来源后将旧结果误写回新来源。``expected_status`` 与
    ``expected_exceptions`` 可让来源级人工发布在清空 exception 前确认清单状态没有
    被另一项处理改动；未提供时保持兼容的“只校验 ID/哈希”行为。
    """
    if not isinstance(source_id, str) or not SOURCE_ID_RE.fullmatch(source_id):
        raise SourceStateError(f"来源 ID 格式无效：{source_id!r}")
    if expected_sha256 is not None and (
        not isinstance(expected_sha256, str) or not SHA256_RE.fullmatch(expected_sha256)
    ):
        raise SourceStateError("expected_sha256 必须是 64 位小写十六进制字符串")
    if expected_status is not None and (
        not isinstance(expected_status, str) or expected_status not in SOURCE_STATUSES
    ):
        raise SourceStateError("expected_status 必须是合法来源状态")
    expected_exception_values = (
        _normalise_string_list(expected_exceptions, "expected_exceptions")
        if expected_exceptions is not None
        else None
    )
    records = read_source_manifest(library_root)
    matched_indexes = [index for index, record in enumerate(records) if record["id"] == source_id]
    if len(matched_indexes) != 1:
        raise SourceStateError(f"sources/sources.jsonl 中未找到唯一来源：{source_id}")
    index = matched_indexes[0]
    current = records[index]
    if expected_sha256 is not None and current["sha256"] != expected_sha256:
        raise SourceStateError("来源 sha256 已变化，拒绝写入旧处理状态")
    current_state = source_state_from_record(current)
    if expected_status is not None and current_state["status"] != expected_status:
        raise SourceStateError("来源 status 已变化，拒绝写入旧处理状态")
    if expected_exception_values is not None and current_state["exceptions"] != expected_exception_values:
        raise SourceStateError("来源 exceptions 已变化，拒绝清空或覆盖未逐项处理的问题")
    next_state = dict(current_state)
    if status is not None:
        if not isinstance(status, str) or status not in SOURCE_STATUSES:
            raise SourceStateError(f"status 非法：{status!r}")
        _validate_status_transition(str(current_state["status"]), status)
        next_state["status"] = status
    if output_paths is not None:
        next_state["output_paths"] = _normalise_output_paths(output_paths)
    if exceptions is not None:
        next_state["exceptions"] = _normalise_string_list(exceptions, "exceptions")
    if tool_versions is not None:
        next_state["tool_versions"] = _normalise_string_mapping(tool_versions, "tool_versions")
    next_state = normalise_source_state(next_state)
    if next_state["status"] == "blocked" and not next_state["exceptions"]:
        raise SourceStateError("blocked 来源必须记录至少一项 exceptions")
    updated = {**current, **next_state}
    records[index] = updated
    write_source_manifest(library_root, records)
    return updated
