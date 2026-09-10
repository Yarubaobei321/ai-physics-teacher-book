#!/usr/bin/env python3
"""用 Python 标准库检查步步高物理数字资料库的基础数据治理规则。"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from current_records import CurrentRecordsError, resolve_current_records


LIBRARY_ROOT = Path(__file__).resolve().parents[1]
STATUSES = {
    "discovered",
    "raw_extracted",
    "ai_structured",
    "pending_manual_review",
    "reviewed",
    "published",
    "blocked",
}
SOURCE_ID_RE = re.compile(r"^src\.bbg\.([0-9a-f]{64})$")
QUESTION_ID_RE = re.compile(r"^q\.src\.bbg\.[0-9a-f]{64}\.[0-9]{3}$")
SKILL_ID_RE = re.compile(r"^skill\.bbg\.[a-z0-9][a-z0-9._-]*$")
ID_PATTERNS = {
    "source": SOURCE_ID_RE,
    "document": re.compile(r"^doc\.bbg\.[a-z0-9][a-z0-9._-]*$"),
    "question": QUESTION_ID_RE,
    "knowledge": re.compile(r"^kn\.bbg\.[a-z0-9][a-z0-9._-]*$"),
    "model": re.compile(r"^model\.bbg\.[a-z0-9][a-z0-9._-]*$"),
    "review": re.compile(r"^review\.bbg\.[a-z0-9][a-z0-9._-]*$"),
}
REQUIRED_FIELDS = {
    "source": {"id", "relative_path", "sha256", "profile", "title", "status", "metadata"},
    "document": {"id", "source_id", "relative_path", "source_relative_path", "content_path", "title", "status", "extraction_profile", "asset_paths"},
    "question": {"id", "relative_path", "status", "source_id", "source_location", "label", "question_type", "stem", "options", "answer", "solution", "figures", "formula_latex", "knowledge_ids", "model_ids", "skill_ids", "difficulty", "extraction_confidence", "review_status", "issues"},
    "knowledge": {"id", "relative_path", "status", "label", "description", "parent_id", "aliases", "source_ids"},
    "model": {"id", "relative_path", "status", "label", "description", "knowledge_ids", "source_ids"},
    "review": {"id", "relative_path", "status", "target_id", "target_relative_path", "reviewer", "decision", "summary", "issues"},
}
RECORD_DIRECTORIES = {
    "document": "records/documents",
    "question": "questions",
    "knowledge": "knowledge",
    "model": "models",
    "review": "reviews",
}


def load_builder():
    path = LIBRARY_ROOT / "scripts" / "build_manifest.py"
    spec = importlib.util.spec_from_file_location("build_manifest_for_validation", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载构建器：{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def is_relative_library_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    if re.match(r"^[A-Za-z]:", value):
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and "." not in path.parts


def read_jsonl(path: Path, errors: list[str]) -> list[tuple[int, dict[str, Any]]]:
    records: list[tuple[int, dict[str, Any]]] = []
    if not path.exists():
        errors.append(f"缺少清单：{path.as_posix()}")
        return records
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            errors.append(f"{path.as_posix()}:{line_no}: JSONL 不允许空行")
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            errors.append(f"{path.as_posix()}:{line_no}: JSON 无法解析：{error.msg}")
            continue
        if not isinstance(value, dict):
            errors.append(f"{path.as_posix()}:{line_no}: 记录必须是对象")
            continue
        records.append((line_no, value))
    return records


def infer_kind(path: Path, root: Path) -> str | None:
    relative = path.relative_to(root).as_posix()
    if relative == "sources/sources.jsonl":
        return "source"
    for kind, directory in RECORD_DIRECTORIES.items():
        if relative.startswith(directory + "/"):
            return kind
    return None


def iter_json_records(root: Path, errors: list[str]) -> Iterable[tuple[str, str, dict[str, Any]]]:
    """兼容早期最小夹具的全目录读取器。

    正式 canonical manifest 使用 ``resolve_current_records``，不会调用本函数；保留
    它只为还没有来源状态字段的历史最小校验夹具，避免把兼容模式误当作索引输入。
    """
    manifest = root / "sources" / "sources.jsonl"
    for line_no, record in read_jsonl(manifest, errors):
        yield "source", f"sources/sources.jsonl:{line_no}", record
    for directory in RECORD_DIRECTORIES.values():
        base = root / directory
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.json"), key=lambda item: item.as_posix()):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as error:
                errors.append(f"{path.relative_to(root).as_posix()}: JSON 无法解析：{error.msg}")
                continue
            if not isinstance(record, dict):
                errors.append(f"{path.relative_to(root).as_posix()}: 记录必须是对象")
                continue
            kind = infer_kind(path, root)
            if kind:
                yield kind, path.relative_to(root).as_posix(), record


def _uses_canonical_current_record_contract(
    manifest_records: list[tuple[int, dict[str, Any]]]
) -> bool:
    """判断是否启用当前报告约束。

    早期的最小 schema 测试没有来源状态字段，仍走只做字段校验的兼容分支；一旦
    清单中出现任一状态字段，就必须使用 canonical manifest + 阶段报告，不能回退。
    """
    state_fields = {"output_paths", "exceptions", "tool_versions"}
    return any(bool(state_fields & set(record)) for _, record in manifest_records)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_string(
    location: str, field: str, value: Any, errors: list[str], *, non_empty: bool = False
) -> bool:
    if not isinstance(value, str) or (non_empty and not value):
        expected = "非空字符串" if non_empty else "字符串"
        errors.append(f"{location}: {field} 必须是{expected}")
        return False
    return True


def _validate_status(location: str, field: str, value: Any, errors: list[str]) -> bool:
    if not isinstance(value, str) or value not in STATUSES:
        errors.append(f"{location}: {field} 非法：{value!r}")
        return False
    return True


def _validate_relative_path(location: str, field: str, value: Any, errors: list[str]) -> bool:
    if not is_relative_library_path(value):
        errors.append(f"{location}: {field} 必须是无 .. 的相对路径：{value!r}")
        return False
    return True


def _validate_identifier(
    location: str, field: str, value: Any, pattern: re.Pattern[str], errors: list[str]
) -> bool:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        errors.append(f"{location}: {field} 格式无效：{value!r}")
        return False
    return True


def _validate_array(
    location: str, field: str, value: Any, errors: list[str], *, nullable: bool = False
) -> list[Any] | None:
    if nullable and value is None:
        return None
    if not isinstance(value, list):
        suffix = "或 null" if nullable else ""
        errors.append(f"{location}: {field} 必须是数组{suffix}")
        return None
    return value


def _validate_identifier_array(
    location: str,
    field: str,
    value: Any,
    pattern: re.Pattern[str],
    errors: list[str],
    *,
    nullable: bool = False,
) -> None:
    items = _validate_array(location, field, value, errors, nullable=nullable)
    if items is None:
        return
    for index, item in enumerate(items):
        if not isinstance(item, str) or not pattern.fullmatch(item):
            errors.append(f"{location}: {field}[{index}] 格式无效：{item!r}")


def _validate_string_array(location: str, field: str, value: Any, errors: list[str]) -> None:
    items = _validate_array(location, field, value, errors)
    if items is None:
        return
    for index, item in enumerate(items):
        if not isinstance(item, str):
            errors.append(f"{location}: {field}[{index}] 必须是字符串")


def _validate_path_array(location: str, field: str, value: Any, errors: list[str]) -> None:
    items = _validate_array(location, field, value, errors)
    if items is None:
        return
    for index, item in enumerate(items):
        _validate_relative_path(location, f"{field}[{index}]", item, errors)


def _validate_source_metadata(location: str, value: Any, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{location}: metadata 必须是对象")
        return
    required = {
        "raw_collection",
        "series_year",
        "exam_year",
        "course",
        "chapter",
        "chapter_origin",
        "lesson_no",
        "version_hint",
        "source_bundle",
    }
    missing = sorted(required - value.keys())
    if missing:
        errors.append(f"{location}: metadata 缺少必填字段：{', '.join(missing)}")
        return
    for field in ("raw_collection", "course", "chapter", "version_hint", "source_bundle"):
        item = value[field]
        if item is not None and not isinstance(item, str):
            errors.append(f"{location}: metadata.{field} 必须是字符串或 null")
    for field in ("series_year", "exam_year"):
        item = value[field]
        if item is not None and not _is_integer(item):
            errors.append(f"{location}: metadata.{field} 必须是整数或 null")
    lesson_no = value["lesson_no"]
    if lesson_no is not None and (not _is_integer(lesson_no) or lesson_no < 1):
        errors.append(f"{location}: metadata.lesson_no 必须是正整数或 null")
    if value["chapter_origin"] not in {"directory", "filename", None}:
        errors.append(f"{location}: metadata.chapter_origin 非法：{value['chapter_origin']!r}")


def _validate_source_record(location: str, record: dict[str, Any], errors: list[str]) -> None:
    value_id = record["id"]
    source_id_valid = _validate_identifier(location, "source ID", value_id, SOURCE_ID_RE, errors)
    sha256 = record["sha256"]
    sha256_valid = _validate_string(location, "sha256", sha256, errors) and bool(
        re.fullmatch(r"[0-9a-f]{64}", sha256)
    )
    if not sha256_valid:
        errors.append(f"{location}: sha256 格式无效")
    elif source_id_valid and value_id != f"src.bbg.{sha256}":
        errors.append(f"{location}: source ID 必须与 sha256 完整匹配")
    relative_path = record["relative_path"]
    if not isinstance(relative_path, str) or not relative_path.startswith("raw/"):
        errors.append(f"{location}: source relative_path 必须以 raw/ 开头")
    profile = record["profile"]
    if not isinstance(profile, str) or profile not in {"teacher", "gaokao", "textbook"}:
        errors.append(f"{location}: profile 非法：{profile!r}")
    _validate_string(location, "title", record["title"], errors, non_empty=True)
    _validate_source_metadata(location, record["metadata"], errors)


def _validate_document_record(location: str, record: dict[str, Any], errors: list[str]) -> None:
    _validate_identifier(location, "source_id", record["source_id"], SOURCE_ID_RE, errors)
    _validate_relative_path(location, "source_relative_path", record["source_relative_path"], errors)
    _validate_relative_path(location, "content_path", record["content_path"], errors)
    if not isinstance(record["source_relative_path"], str) or not record["source_relative_path"].startswith("raw/"):
        errors.append(f"{location}: source_relative_path 必须以 raw/ 开头")
    _validate_string(location, "title", record["title"], errors, non_empty=True)
    profile = record["extraction_profile"]
    if not isinstance(profile, str) or profile not in {"teacher", "gaokao", "textbook"}:
        errors.append(f"{location}: extraction_profile 非法：{profile!r}")
    _validate_path_array(location, "asset_paths", record["asset_paths"], errors)
    if "issues" in record:
        _validate_string_array(location, "issues", record["issues"], errors)


def _validate_question_record(location: str, record: dict[str, Any], errors: list[str]) -> None:
    source_id = record["source_id"]
    source_id_valid = _validate_identifier(location, "source_id", source_id, SOURCE_ID_RE, errors)
    question_id = record["id"]
    if (
        source_id_valid
        and isinstance(question_id, str)
        and QUESTION_ID_RE.fullmatch(question_id)
        and not question_id.startswith(f"q.{source_id}.")
    ):
        errors.append(f"{location}: question ID 必须以 q.<source_id>.NNN 关联其 source_id")
    source_location = record["source_location"]
    if not isinstance(source_location, dict):
        errors.append(f"{location}: source_location 必须包含 relative_path 和 locator")
    else:
        required = {"relative_path", "locator"}
        missing = sorted(required - source_location.keys())
        unexpected = sorted(source_location.keys() - required)
        if missing:
            errors.append(f"{location}: source_location 缺少字段：{', '.join(missing)}")
        if unexpected:
            errors.append(f"{location}: source_location 不允许额外字段：{', '.join(unexpected)}")
        if not missing:
            source_path = source_location["relative_path"]
            _validate_relative_path(location, "source_location.relative_path", source_path, errors)
            if not isinstance(source_path, str) or not source_path.startswith("raw/"):
                errors.append(f"{location}: source_location.relative_path 必须是 raw/ 相对路径")
            _validate_string(location, "source_location.locator", source_location["locator"], errors, non_empty=True)
    for field in ("label", "question_type", "stem"):
        _validate_string(location, field, record[field], errors, non_empty=True)
    options = _validate_array(location, "options", record["options"], errors)
    if options is not None:
        for index, option in enumerate(options):
            if not isinstance(option, (str, dict)):
                errors.append(f"{location}: options[{index}] 必须是字符串或对象")
    for field in ("answer", "solution"):
        if record[field] is not None and not isinstance(record[field], (str, dict, list)):
            errors.append(f"{location}: {field} 必须是字符串、对象、数组或 null")
    _validate_path_array(location, "figures", record["figures"], errors)
    _validate_string_array(location, "formula_latex", record["formula_latex"], errors)
    _validate_identifier_array(location, "knowledge_ids", record["knowledge_ids"], ID_PATTERNS["knowledge"], errors)
    _validate_identifier_array(
        location, "model_ids", record["model_ids"], ID_PATTERNS["model"], errors, nullable=True
    )
    _validate_identifier_array(
        location, "skill_ids", record["skill_ids"], SKILL_ID_RE, errors, nullable=True
    )
    difficulty = record["difficulty"]
    if difficulty is not None and not isinstance(difficulty, str) and not _is_number(difficulty):
        errors.append(f"{location}: difficulty 必须是数值、字符串或 null")
    confidence = record["extraction_confidence"]
    if confidence is not None and (
        not _is_number(confidence) or not math.isfinite(confidence) or confidence < 0 or confidence > 1
    ):
        errors.append(f"{location}: extraction_confidence 必须是 0 到 1 的数值或 null")
    _validate_status(location, "review_status", record["review_status"], errors)
    _validate_string_array(location, "issues", record["issues"], errors)
    if record["status"] == "published" or record["review_status"] == "published":
        knowledge_ids = record["knowledge_ids"]
        if not isinstance(knowledge_ids, list) or not knowledge_ids:
            errors.append(f"{location}: 已发布 question 必须至少关联一个 knowledge_id")


def _validate_knowledge_record(location: str, record: dict[str, Any], errors: list[str]) -> None:
    for field in ("label", "description"):
        _validate_string(location, field, record[field], errors, non_empty=True)
    parent_id = record["parent_id"]
    if parent_id is not None:
        _validate_identifier(location, "parent_id", parent_id, ID_PATTERNS["knowledge"], errors)
    _validate_string_array(location, "aliases", record["aliases"], errors)
    _validate_identifier_array(location, "source_ids", record["source_ids"], SOURCE_ID_RE, errors)


def _validate_model_record(location: str, record: dict[str, Any], errors: list[str]) -> None:
    for field in ("label", "description"):
        _validate_string(location, field, record[field], errors, non_empty=True)
    _validate_identifier_array(location, "knowledge_ids", record["knowledge_ids"], ID_PATTERNS["knowledge"], errors)
    _validate_identifier_array(location, "source_ids", record["source_ids"], SOURCE_ID_RE, errors)


def _validate_review_record(location: str, record: dict[str, Any], errors: list[str]) -> None:
    allowed = REQUIRED_FIELDS["review"] | {"resolved_issues"}
    unexpected = sorted(set(record) - allowed)
    if unexpected:
        errors.append(f"{location}: review 不允许额外字段：{', '.join(unexpected)}")
    _validate_string(location, "target_id", record["target_id"], errors, non_empty=True)
    _validate_relative_path(location, "target_relative_path", record["target_relative_path"], errors)
    for field in ("reviewer", "summary"):
        _validate_string(location, field, record[field], errors, non_empty=True)
    decision = record["decision"]
    if not isinstance(decision, str) or decision not in {"approved", "needs_changes", "rejected", "blocked"}:
        errors.append(f"{location}: decision 非法：{decision!r}")
    _validate_string_array(location, "issues", record["issues"], errors)
    if "resolved_issues" in record:
        _validate_string_array(location, "resolved_issues", record["resolved_issues"], errors)


def validate_record(kind: str, location: str, record: dict[str, Any], errors: list[str]) -> None:
    missing = sorted(REQUIRED_FIELDS[kind] - record.keys())
    if missing:
        errors.append(f"{location}: 缺少必填字段：{', '.join(missing)}")
        return
    value_id = record["id"]
    _validate_identifier(location, f"{kind} ID", value_id, ID_PATTERNS[kind], errors)
    _validate_status(location, "status", record["status"], errors)
    _validate_relative_path(location, "relative_path", record["relative_path"], errors)
    if kind == "source":
        _validate_source_record(location, record, errors)
    elif kind == "document":
        _validate_document_record(location, record, errors)
    elif kind == "question":
        _validate_question_record(location, record, errors)
    elif kind == "knowledge":
        _validate_knowledge_record(location, record, errors)
    elif kind == "model":
        _validate_model_record(location, record, errors)
    elif kind == "review":
        _validate_review_record(location, record, errors)


def validate_library(root: Path = LIBRARY_ROOT, expected_profile_counts: dict[str, int] | None = None) -> list[str]:
    """返回所有校验错误；空列表表示通过。"""
    root = Path(root).resolve()
    errors: list[str] = []
    seen_ids: dict[str, str] = {}
    source_counts = {"teacher": 0, "gaokao": 0, "textbook": 0}
    manifest_records = read_jsonl(root / "sources" / "sources.jsonl", errors)
    records: list[tuple[str, str, dict[str, Any]]] = [
        ("source", f"sources/sources.jsonl:{line_no}", record)
        for line_no, record in manifest_records
    ]
    if _uses_canonical_current_record_contract(manifest_records):
        try:
            resolution = resolve_current_records(root)
        except CurrentRecordsError as error:
            errors.append(f"当前记录解析失败：{error}")
        else:
            errors.extend(resolution.errors)
            for kind in RECORD_DIRECTORIES:
                records.extend(
                    (kind, location, record)
                    for location, record in resolution.declared_records[kind]
                )
    else:
        # 最小兼容夹具：来源没有状态字段时，仅验证 JSON Schema 语义，不用于索引。
        records.extend(
            (kind, location, record)
            for kind, location, record in iter_json_records(root, errors)
            if kind != "source"
        )
    for kind, location, record in records:
        validate_record(kind, location, record, errors)
        value_id = record.get("id")
        if isinstance(value_id, str):
            previous = seen_ids.get(value_id)
            if previous:
                errors.append(f"{location}: 重复 ID {value_id!r}，首次出现在 {previous}")
            else:
                seen_ids[value_id] = location
        profile = record.get("profile")
        if kind == "source" and isinstance(profile, str) and profile in source_counts:
            source_counts[profile] += 1
    if expected_profile_counts is not None:
        for profile, expected in expected_profile_counts.items():
            actual = source_counts.get(profile, 0)
            if actual != expected:
                errors.append(f"分类总数不符：{profile} 应为 {expected}，实际为 {actual}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="校验步步高物理数字资料库基础记录")
    parser.add_argument("--root", type=Path, default=LIBRARY_ROOT, help="资料库根目录")
    parser.add_argument("--no-count-check", action="store_true", help="跳过全库 101/72/443 分类总数检查")
    args = parser.parse_args(argv)
    expected = None if args.no_count_check else {"teacher": 101, "gaokao": 72, "textbook": 443}
    errors = validate_library(args.root, expected_profile_counts=expected)
    if errors:
        print(f"校验失败：{len(errors)} 项", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("校验通过：manifest、路径、ID、状态、分类总数和题目知识点关联均符合基础规则。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
