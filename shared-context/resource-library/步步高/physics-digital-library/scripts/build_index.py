#!/usr/bin/env python3
"""建立步步高物理数字资料库的本地 SQLite 检索索引。

脚本只读取资料库中的结构化 JSON 记录，并把完整的新数据库先写到
``indexes/`` 中的临时文件；所有写入成功后才用原子替换更新
``indexes/bubugao.sqlite``。原始 Word、转换产物和其他资料库文件均不会修改。
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from current_records import (
    CurrentRecordsError,
    CurrentRecordResolution,
    manifest_snapshot_matches,
    require_current_records,
)


LIBRARY_ROOT = Path(__file__).resolve().parents[1]
DATABASE_RELATIVE_PATH = "indexes/bubugao.sqlite"
RECORD_DIRECTORIES = {
    "document": "records/documents",
    "question": "questions",
    "knowledge": "knowledge",
    "model": "models",
}


class IndexBuildError(RuntimeError):
    """资料库索引无法安全建立时抛出。"""


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def safe_library_root(library_root: Path = LIBRARY_ROOT) -> Path:
    """返回可安全使用的资料库根目录，拒绝符号链接和不存在的根。"""
    root = Path(library_root)
    if root.is_symlink():
        raise IndexBuildError("资料库根目录不能是符号链接")
    if not root.is_dir():
        raise IndexBuildError(f"资料库根目录不存在或不是目录：{root}")
    try:
        return root.resolve(strict=True)
    except OSError as error:
        raise IndexBuildError(f"无法解析资料库根目录：{error}") from error


def safe_output_path(
    library_root: Path, relative_path: str = DATABASE_RELATIVE_PATH
) -> Path:
    """返回唯一允许写入的数据库路径，并拒绝越界或符号链接输出。"""
    if relative_path != DATABASE_RELATIVE_PATH:
        raise IndexBuildError(f"不允许写入此输出路径：{relative_path!r}")
    relative = PurePosixPath(relative_path)
    if relative.is_absolute() or ".." in relative.parts or "\\" in relative_path:
        raise IndexBuildError(f"输出路径越出资料库：{relative_path!r}")

    root = safe_library_root(library_root)
    index_directory = root / "indexes"
    if index_directory.exists():
        if index_directory.is_symlink() or not index_directory.is_dir():
            raise IndexBuildError("索引输出目录必须是资料库内的普通目录")
    else:
        try:
            index_directory.mkdir()
        except OSError as error:
            raise IndexBuildError(f"无法创建索引输出目录：{error}") from error
    if index_directory.is_symlink() or not index_directory.is_dir():
        raise IndexBuildError("索引输出目录必须是资料库内的普通目录")

    try:
        resolved_directory = index_directory.resolve(strict=True)
    except OSError as error:
        raise IndexBuildError(f"无法解析索引输出目录：{error}") from error
    if not _is_within(resolved_directory, root):
        raise IndexBuildError("索引输出目录越出资料库")

    target = resolved_directory / "bubugao.sqlite"
    if target.is_symlink():
        raise IndexBuildError("索引输出文件不能是符号链接")
    if target.exists() and not target.is_file():
        raise IndexBuildError("索引输出路径必须是普通文件")
    try:
        resolved_target = target.resolve(strict=False)
    except OSError as error:
        raise IndexBuildError(f"无法解析索引输出文件：{error}") from error
    if not _is_within(resolved_target, root):
        raise IndexBuildError("索引输出文件越出资料库")
    return target


def _serialise_json(value: Any) -> str:
    """将任意已解析 JSON 字段稳定地保存为 JSON 文本。"""
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return json.dumps(str(value), ensure_ascii=False)


def _text(value: Any) -> str:
    """把可空、数组或对象字段转换为不抛异常的检索文本。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return " ".join(part for item in value if (part := _text(item)))
    if isinstance(value, dict):
        return " ".join(
            part
            for key, item in value.items()
            for part in (_text(key), _text(item))
            if part
        )
    return str(value).strip()


def _string_values(value: Any) -> list[str]:
    """将 string / array / null 字段规范为去重后的字符串列表。"""
    values: list[str] = []
    if isinstance(value, list):
        for item in value:
            values.extend(_string_values(item))
    elif value is not None and not isinstance(value, dict):
        text = _text(value)
        if text:
            values.append(text)
    return list(dict.fromkeys(values))


def _integer(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _read_json_object(path: Path, location: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise IndexBuildError(f"无法读取 {location}：{error}") from error
    if not isinstance(value, dict):
        raise IndexBuildError(f"{location} 的记录必须是 JSON 对象")
    return value


def iter_source_records(root: Path) -> Iterable[tuple[str, dict[str, Any]]]:
    """逐行读取来源清单，保持其顺序并给出可定位的行号。"""
    path = root / "sources" / "sources.jsonl"
    if path.is_symlink():
        raise IndexBuildError("sources/sources.jsonl 不能是符号链接")
    if not path.is_file():
        raise IndexBuildError("缺少来源清单：sources/sources.jsonl")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise IndexBuildError(f"无法读取来源清单：{error}") from error
    for line_no, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        location = f"sources/sources.jsonl:{line_no}"
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise IndexBuildError(f"{location} 的 JSON 无法解析：{error.msg}") from error
        if not isinstance(record, dict):
            raise IndexBuildError(f"{location} 的记录必须是 JSON 对象")
        yield location, record


SCHEMA_SQL = """
CREATE TABLE sources (
    id TEXT PRIMARY KEY,
    relative_path TEXT,
    sha256 TEXT,
    profile TEXT,
    title TEXT,
    status TEXT,
    chapter TEXT,
    lesson_no INTEGER,
    metadata_json TEXT NOT NULL,
    search_text TEXT NOT NULL,
    raw_json TEXT NOT NULL
);
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    source_id TEXT,
    relative_path TEXT,
    source_relative_path TEXT,
    content_path TEXT,
    title TEXT,
    status TEXT,
    extraction_profile TEXT,
    issues_json TEXT NOT NULL,
    search_text TEXT NOT NULL,
    raw_json TEXT NOT NULL
);
CREATE TABLE questions (
    id TEXT PRIMARY KEY,
    source_id TEXT,
    relative_path TEXT,
    source_relative_path TEXT,
    source_locator TEXT,
    label TEXT,
    question_type TEXT,
    stem TEXT,
    status TEXT,
    review_status TEXT,
    knowledge_ids_json TEXT NOT NULL,
    model_ids_json TEXT NOT NULL,
    search_text TEXT NOT NULL,
    raw_json TEXT NOT NULL
);
CREATE TABLE knowledge (
    id TEXT PRIMARY KEY,
    relative_path TEXT,
    label TEXT,
    description TEXT,
    parent_id TEXT,
    status TEXT,
    aliases_json TEXT NOT NULL,
    source_ids_json TEXT NOT NULL,
    search_text TEXT NOT NULL,
    raw_json TEXT NOT NULL
);
CREATE TABLE models (
    id TEXT PRIMARY KEY,
    relative_path TEXT,
    label TEXT,
    description TEXT,
    status TEXT,
    knowledge_ids_json TEXT NOT NULL,
    source_ids_json TEXT NOT NULL,
    search_text TEXT NOT NULL,
    raw_json TEXT NOT NULL
);
CREATE TABLE question_knowledge (
    question_id TEXT NOT NULL,
    knowledge_id TEXT NOT NULL,
    PRIMARY KEY (question_id, knowledge_id)
);
CREATE TABLE question_model (
    question_id TEXT NOT NULL,
    model_id TEXT NOT NULL,
    PRIMARY KEY (question_id, model_id)
);
CREATE INDEX idx_sources_status_profile ON sources(status, profile);
CREATE INDEX idx_sources_lesson_chapter ON sources(lesson_no, chapter);
CREATE INDEX idx_documents_source_id ON documents(source_id);
CREATE INDEX idx_questions_source_type ON questions(source_id, question_type);
CREATE INDEX idx_question_knowledge_knowledge ON question_knowledge(knowledge_id, question_id);
CREATE INDEX idx_question_model_model ON question_model(model_id, question_id);
CREATE INDEX idx_knowledge_label ON knowledge(label);
CREATE INDEX idx_models_label ON models(label);
"""


def _record_id(record: dict[str, Any]) -> str | None:
    value = record.get("id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _insert_source(connection: sqlite3.Connection, record: dict[str, Any]) -> bool:
    record_id = _record_id(record)
    if record_id is None:
        return False
    metadata_value = record.get("metadata")
    metadata = metadata_value if isinstance(metadata_value, dict) else {}
    title = _text(record.get("title"))
    relative_path = _text(record.get("relative_path"))
    chapter = _text(metadata.get("chapter"))
    search_text = " ".join(
        part
        for part in (
            record_id,
            title,
            relative_path,
            _text(record.get("profile")),
            _text(record.get("status")),
            _text(metadata_value),
        )
        if part
    )
    connection.execute(
        """
        INSERT INTO sources (
            id, relative_path, sha256, profile, title, status, chapter, lesson_no,
            metadata_json, search_text, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record_id,
            relative_path,
            _text(record.get("sha256")),
            _text(record.get("profile")),
            title,
            _text(record.get("status")),
            chapter,
            _integer(metadata.get("lesson_no")),
            _serialise_json(metadata_value),
            search_text,
            _serialise_json(record),
        ),
    )
    return True


def _insert_document(connection: sqlite3.Connection, record: dict[str, Any]) -> bool:
    record_id = _record_id(record)
    if record_id is None:
        return False
    title = _text(record.get("title"))
    source_id = _text(record.get("source_id"))
    relative_path = _text(record.get("relative_path"))
    issues = record.get("issues")
    search_text = " ".join(
        part
        for part in (
            record_id,
            source_id,
            title,
            relative_path,
            _text(record.get("source_relative_path")),
            _text(record.get("content_path")),
            _text(record.get("extraction_profile")),
            _text(issues),
        )
        if part
    )
    connection.execute(
        """
        INSERT INTO documents (
            id, source_id, relative_path, source_relative_path, content_path, title,
            status, extraction_profile, issues_json, search_text, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record_id,
            source_id,
            relative_path,
            _text(record.get("source_relative_path")),
            _text(record.get("content_path")),
            title,
            _text(record.get("status")),
            _text(record.get("extraction_profile")),
            _serialise_json(issues),
            search_text,
            _serialise_json(record),
        ),
    )
    return True


def _insert_question(connection: sqlite3.Connection, record: dict[str, Any]) -> bool:
    record_id = _record_id(record)
    if record_id is None:
        return False
    source_location_value = record.get("source_location")
    source_location = source_location_value if isinstance(source_location_value, dict) else {}
    knowledge_ids = _string_values(record.get("knowledge_ids"))
    model_ids = _string_values(record.get("model_ids"))
    source_id = _text(record.get("source_id"))
    label = _text(record.get("label"))
    question_type = _text(record.get("question_type"))
    stem = _text(record.get("stem"))
    search_text = " ".join(
        part
        for part in (
            record_id,
            source_id,
            label,
            question_type,
            stem,
            _text(record.get("answer")),
            _text(record.get("solution")),
            _text(record.get("formula_latex")),
            _text(knowledge_ids),
            _text(model_ids),
            _text(record.get("skill_ids")),
            _text(record.get("issues")),
        )
        if part
    )
    connection.execute(
        """
        INSERT INTO questions (
            id, source_id, relative_path, source_relative_path, source_locator, label,
            question_type, stem, status, review_status, knowledge_ids_json, model_ids_json,
            search_text, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record_id,
            source_id,
            _text(record.get("relative_path")),
            _text(source_location.get("relative_path")),
            _text(source_location.get("locator")),
            label,
            question_type,
            stem,
            _text(record.get("status")),
            _text(record.get("review_status")),
            _serialise_json(knowledge_ids),
            _serialise_json(model_ids),
            search_text,
            _serialise_json(record),
        ),
    )
    connection.executemany(
        "INSERT INTO question_knowledge (question_id, knowledge_id) VALUES (?, ?)",
        [(record_id, knowledge_id) for knowledge_id in knowledge_ids],
    )
    connection.executemany(
        "INSERT INTO question_model (question_id, model_id) VALUES (?, ?)",
        [(record_id, model_id) for model_id in model_ids],
    )
    return True


def _insert_knowledge(connection: sqlite3.Connection, record: dict[str, Any]) -> bool:
    record_id = _record_id(record)
    if record_id is None:
        return False
    aliases = _string_values(record.get("aliases"))
    source_ids = _string_values(record.get("source_ids"))
    label = _text(record.get("label"))
    description = _text(record.get("description"))
    search_text = " ".join(
        part
        for part in (record_id, label, description, _text(aliases), _text(source_ids))
        if part
    )
    connection.execute(
        """
        INSERT INTO knowledge (
            id, relative_path, label, description, parent_id, status, aliases_json,
            source_ids_json, search_text, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record_id,
            _text(record.get("relative_path")),
            label,
            description,
            _text(record.get("parent_id")),
            _text(record.get("status")),
            _serialise_json(aliases),
            _serialise_json(source_ids),
            search_text,
            _serialise_json(record),
        ),
    )
    return True


def _insert_model(connection: sqlite3.Connection, record: dict[str, Any]) -> bool:
    record_id = _record_id(record)
    if record_id is None:
        return False
    knowledge_ids = _string_values(record.get("knowledge_ids"))
    source_ids = _string_values(record.get("source_ids"))
    label = _text(record.get("label"))
    description = _text(record.get("description"))
    search_text = " ".join(
        part
        for part in (record_id, label, description, _text(knowledge_ids), _text(source_ids))
        if part
    )
    connection.execute(
        """
        INSERT INTO models (
            id, relative_path, label, description, status, knowledge_ids_json,
            source_ids_json, search_text, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record_id,
            _text(record.get("relative_path")),
            label,
            description,
            _text(record.get("status")),
            _serialise_json(knowledge_ids),
            _serialise_json(source_ids),
            search_text,
            _serialise_json(record),
        ),
    )
    return True


INSERT_FUNCTIONS = {
    "source": _insert_source,
    "document": _insert_document,
    "question": _insert_question,
    "knowledge": _insert_knowledge,
    "model": _insert_model,
}


def _populate_database(
    connection: sqlite3.Connection, resolution: CurrentRecordResolution
) -> dict[str, int]:
    """只写入 current_records 已明确允许的结构化记录。

    这里刻意不遍历 questions/、knowledge/ 等目录；任何未被来源清单与当前阶段
    报告共同声明的 JSON 都没有机会进入 SQLite。
    """
    counts = {kind: 0 for kind in INSERT_FUNCTIONS}
    for _, record in resolution.sources:
        counts["source"] += int(_insert_source(connection, record))
    for kind in RECORD_DIRECTORIES:
        insert = INSERT_FUNCTIONS[kind]
        for _, record in resolution.records[kind]:
            counts[kind] += int(insert(connection, record))
    return counts


def _sync_directory(directory: Path) -> None:
    """尽力同步目录元数据；部分平台不支持时不影响已完成的替换。"""
    try:
        descriptor = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def build_index(library_root: Path = LIBRARY_ROOT) -> dict[str, int]:
    """重建索引并原子替换旧数据库，返回各类成功索引的记录数。"""
    root = safe_library_root(library_root)
    try:
        resolution = require_current_records(root)
    except CurrentRecordsError as error:
        raise IndexBuildError(str(error)) from error
    target = safe_output_path(root)
    descriptor: int | None = None
    temporary_path: Path | None = None
    connection: sqlite3.Connection | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".bubugao-", suffix=".sqlite", dir=target.parent
        )
        temporary_path = Path(temporary_name)
        os.close(descriptor)
        descriptor = None
        connection = sqlite3.connect(str(temporary_path))
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
        connection.executescript(SCHEMA_SQL)
        counts = _populate_database(connection, resolution)
        connection.commit()
        connection.close()
        connection = None
        with temporary_path.open("rb") as stream:
            os.fsync(stream.fileno())
        # sources/sources.jsonl 是索引的 canonical 输入。若它在读取、SQLite 写入和
        # 原子替换之间发生变化，宁可保留旧索引，也不能让新索引混入不一致快照。
        # 在替换前重新检查一次，避免把索引写到已被替换为链接的位置。
        target = safe_output_path(root)
        if not manifest_snapshot_matches(resolution):
            raise IndexBuildError("sources/sources.jsonl 在索引构建期间发生变化，已保留旧索引")
        os.replace(temporary_path, target)
        temporary_path = None
        _sync_directory(target.parent)
        return counts
    except sqlite3.Error as error:
        raise IndexBuildError(f"SQLite 索引构建失败：{error}") from error
    except OSError as error:
        raise IndexBuildError(f"索引文件写入失败：{error}") from error
    finally:
        if connection is not None:
            connection.close()
        if descriptor is not None:
            os.close(descriptor)
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="建立步步高物理数字资料库的本地 SQLite 索引")
    parser.add_argument("--root", type=Path, default=LIBRARY_ROOT, help="资料库根目录")
    args = parser.parse_args(argv)
    try:
        counts = build_index(args.root)
    except (IndexBuildError, ValueError) as error:
        print(f"索引构建失败：{error}", file=sys.stderr)
        return 1
    print(
        "已原子更新 indexes/bubugao.sqlite："
        f"来源 {counts['source']}，文档 {counts['document']}，题目 {counts['question']}，"
        f"知识点 {counts['knowledge']}，模型 {counts['model']}。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
