#!/usr/bin/env python3
"""查询步步高物理数字资料库的本地 SQLite 索引。"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Callable


LIBRARY_ROOT = Path(__file__).resolve().parents[1]
DATABASE_RELATIVE_PATH = "indexes/bubugao.sqlite"


class QueryError(RuntimeError):
    """索引不可安全查询或查询参数不正确时抛出。"""


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def database_path(library_root: Path = LIBRARY_ROOT) -> Path:
    """返回资料库内可安全读取的索引文件，拒绝链接和越界路径。"""
    root = Path(library_root)
    if root.is_symlink():
        raise QueryError("资料库根目录不能是符号链接")
    if not root.is_dir():
        raise QueryError(f"资料库根目录不存在或不是目录：{root}")
    try:
        resolved_root = root.resolve(strict=True)
    except OSError as error:
        raise QueryError(f"无法解析资料库根目录：{error}") from error

    directory = resolved_root / "indexes"
    path = directory / "bubugao.sqlite"
    if directory.is_symlink() or path.is_symlink():
        raise QueryError("索引目录和索引文件不能是符号链接")
    if not path.is_file():
        raise QueryError("索引不存在，请先运行 build_index.py")
    try:
        resolved_path = path.resolve(strict=True)
    except OSError as error:
        raise QueryError(f"无法解析索引文件：{error}") from error
    if not _is_within(resolved_path, resolved_root):
        raise QueryError("索引文件越出资料库")
    return resolved_path


def _like_pattern(value: str) -> str:
    """为 LIKE 查询转义通配符，关键词按字面量子串匹配。"""
    escaped = value.replace("!", "!!").replace("%", "!%").replace("_", "!_")
    return f"%{escaped}%"


def _add_keyword_clause(
    clauses: list[str], parameters: list[Any], expression: str, keyword: str | None
) -> None:
    if keyword and keyword.strip():
        clauses.append(f"LOWER({expression}) LIKE LOWER(?) ESCAPE '!'")
        parameters.append(_like_pattern(keyword.strip()))


def _rows_as_records(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in cursor.fetchall():
        try:
            value = json.loads(row["raw_json"])
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise QueryError(f"索引中的记录无法还原为 JSON：{error}") from error
        if isinstance(value, dict):
            records.append(value)
        else:
            raise QueryError("索引中的记录必须是 JSON 对象")
    return records


def query_sources(
    connection: sqlite3.Connection,
    *,
    status: str | None = None,
    profile: str | None = None,
    keyword: str | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    parameters: list[Any] = []
    if status:
        clauses.append("status = ?")
        parameters.append(status)
    if profile:
        clauses.append("profile = ?")
        parameters.append(profile)
    _add_keyword_clause(clauses, parameters, "search_text", keyword)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    return _rows_as_records(
        connection.execute(
            "SELECT raw_json FROM sources" + where + " ORDER BY title COLLATE NOCASE, id",
            parameters,
        )
    )


def query_lessons(
    connection: sqlite3.Connection,
    *,
    lesson_no: int | None = None,
    chapter: str | None = None,
    keyword: str | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    parameters: list[Any] = []
    if lesson_no is not None:
        clauses.append("s.lesson_no = ?")
        parameters.append(lesson_no)
    if chapter and chapter.strip():
        chapter_pattern = _like_pattern(chapter.strip())
        clauses.append(
            "(LOWER(s.chapter) LIKE LOWER(?) ESCAPE '!' "
            "OR LOWER(s.search_text) LIKE LOWER(?) ESCAPE '!' "
            "OR LOWER(COALESCE(d.search_text, '')) LIKE LOWER(?) ESCAPE '!')"
        )
        parameters.extend([chapter_pattern, chapter_pattern, chapter_pattern])
    if keyword and keyword.strip():
        keyword_pattern = _like_pattern(keyword.strip())
        clauses.append(
            "(LOWER(s.search_text) LIKE LOWER(?) ESCAPE '!' "
            "OR LOWER(COALESCE(d.search_text, '')) LIKE LOWER(?) ESCAPE '!')"
        )
        parameters.extend([keyword_pattern, keyword_pattern])
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    return _rows_as_records(
        connection.execute(
            "SELECT DISTINCT s.raw_json FROM sources AS s "
            "LEFT JOIN documents AS d ON d.source_id = s.id"
            + where
            + " ORDER BY s.chapter COLLATE NOCASE, s.lesson_no, s.title COLLATE NOCASE, s.id",
            parameters,
        )
    )


def query_questions(
    connection: sqlite3.Connection,
    *,
    knowledge_id: str | None = None,
    model_id: str | None = None,
    question_type: str | None = None,
    source_id: str | None = None,
    keyword: str | None = None,
) -> list[dict[str, Any]]:
    joins: list[str] = []
    clauses: list[str] = []
    parameters: list[Any] = []
    if knowledge_id:
        joins.append("JOIN question_knowledge AS qk ON qk.question_id = q.id")
        clauses.append("qk.knowledge_id = ?")
        parameters.append(knowledge_id)
    if model_id:
        joins.append("JOIN question_model AS qm ON qm.question_id = q.id")
        clauses.append("qm.model_id = ?")
        parameters.append(model_id)
    if question_type:
        clauses.append("q.question_type = ?")
        parameters.append(question_type)
    if source_id:
        clauses.append("q.source_id = ?")
        parameters.append(source_id)
    _add_keyword_clause(clauses, parameters, "q.search_text", keyword)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    join_sql = " " + " ".join(joins) if joins else ""
    return _rows_as_records(
        connection.execute(
            "SELECT DISTINCT q.raw_json FROM questions AS q"
            + join_sql
            + where
            + " ORDER BY q.label COLLATE NOCASE, q.id",
            parameters,
        )
    )


def query_knowledge(
    connection: sqlite3.Connection,
    *,
    keyword: str | None = None,
    question_id: str | None = None,
) -> list[dict[str, Any]]:
    joins: list[str] = []
    clauses: list[str] = []
    parameters: list[Any] = []
    if question_id:
        joins.append("JOIN question_knowledge AS qk ON qk.knowledge_id = k.id")
        clauses.append("qk.question_id = ?")
        parameters.append(question_id)
    _add_keyword_clause(clauses, parameters, "k.search_text", keyword)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    join_sql = " " + " ".join(joins) if joins else ""
    return _rows_as_records(
        connection.execute(
            "SELECT DISTINCT k.raw_json FROM knowledge AS k"
            + join_sql
            + where
            + " ORDER BY k.label COLLATE NOCASE, k.id",
            parameters,
        )
    )


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "、".join(_as_text(item) for item in value if _as_text(item))
    if isinstance(value, dict):
        return "；".join(f"{key}：{_as_text(item)}" for key, item in value.items())
    return str(value)


def _human_record(scenario: str, record: dict[str, Any]) -> str:
    record_id = _as_text(record.get("id")) or "（无 ID）"
    if scenario in {"source", "lesson"}:
        metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
        details = [
            _as_text(record.get("profile")),
            _as_text(record.get("status")),
            _as_text(metadata.get("chapter")),
            f"第{metadata['lesson_no']}课时" if metadata.get("lesson_no") is not None else "",
        ]
        return f"- {record_id}｜{_as_text(record.get('title'))}\n  " + "；".join(
            detail for detail in details if detail
        )
    if scenario == "question":
        return (
            f"- {record_id}｜{_as_text(record.get('label'))}\n"
            f"  {_as_text(record.get('question_type'))}；来源 {_as_text(record.get('source_id'))}\n"
            f"  {_as_text(record.get('stem'))}"
        )
    return (
        f"- {record_id}｜{_as_text(record.get('label'))}\n"
        f"  {_as_text(record.get('description'))}"
    )


def format_human(scenario: str, records: list[dict[str, Any]]) -> str:
    labels = {
        "source": "来源",
        "lesson": "课时",
        "question": "题目",
        "knowledge": "知识点",
    }
    heading = f"找到 {len(records)} 条{labels[scenario]}记录："
    return "\n".join([heading, *(_human_record(scenario, record) for record in records)])


def _add_global_options(parser: argparse.ArgumentParser, *, suppress_default: bool) -> None:
    default = argparse.SUPPRESS if suppress_default else False
    parser.add_argument("--json", dest="json_output", action="store_true", default=default, help="输出 JSON")
    root_default: Any = argparse.SUPPRESS if suppress_default else LIBRARY_ROOT
    parser.add_argument("--root", type=Path, default=root_default, help="资料库根目录")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="查询步步高物理数字资料库本地索引")
    _add_global_options(parser, suppress_default=False)
    subparsers = parser.add_subparsers(dest="scenario", required=True, title="查询场景")

    source = subparsers.add_parser("source", help="按状态、资料类型和关键词查询来源")
    _add_global_options(source, suppress_default=True)
    source.add_argument("--status", help="来源状态")
    source.add_argument("--profile", help="资料类型，如 teacher、gaokao、textbook")
    source.add_argument("--keyword", "-k", help="关键词（按字面量子串匹配）")

    lesson = subparsers.add_parser("lesson", help="按课时、章节和关键词查询课时来源")
    _add_global_options(lesson, suppress_default=True)
    lesson.add_argument("--lesson", "--lesson-no", dest="lesson_no", type=int, help="课时号")
    lesson.add_argument("--chapter", help="章节关键词")
    lesson.add_argument("--keyword", "-k", help="关键词（按字面量子串匹配）")

    question = subparsers.add_parser("question", help="按知识点、模型、题型、来源和关键词查询题目")
    _add_global_options(question, suppress_default=True)
    question.add_argument("--knowledge", "--knowledge-id", dest="knowledge_id", help="知识点 ID")
    question.add_argument("--model", "--model-id", dest="model_id", help="物理模型 ID")
    question.add_argument("--type", "--question-type", dest="question_type", help="题型")
    question.add_argument("--source", "--source-id", dest="source_id", help="来源 ID")
    question.add_argument("--keyword", "-k", help="关键词（按字面量子串匹配）")

    knowledge = subparsers.add_parser("knowledge", help="按关键词查询知识点，或由题目反查知识点")
    _add_global_options(knowledge, suppress_default=True)
    knowledge.add_argument("--keyword", "-k", help="关键词（按字面量子串匹配）")
    knowledge.add_argument("--question", "--question-id", dest="question_id", help="反查的题目 ID")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dispatch: dict[str, Callable[..., list[dict[str, Any]]]] = {
        "source": query_sources,
        "lesson": query_lessons,
        "question": query_questions,
        "knowledge": query_knowledge,
    }
    query_arguments = {
        "source": {
            "status": getattr(args, "status", None),
            "profile": getattr(args, "profile", None),
            "keyword": getattr(args, "keyword", None),
        },
        "lesson": {
            "lesson_no": getattr(args, "lesson_no", None),
            "chapter": getattr(args, "chapter", None),
            "keyword": getattr(args, "keyword", None),
        },
        "question": {
            "knowledge_id": getattr(args, "knowledge_id", None),
            "model_id": getattr(args, "model_id", None),
            "question_type": getattr(args, "question_type", None),
            "source_id": getattr(args, "source_id", None),
            "keyword": getattr(args, "keyword", None),
        },
        "knowledge": {
            "keyword": getattr(args, "keyword", None),
            "question_id": getattr(args, "question_id", None),
        },
    }
    try:
        path = database_path(args.root)
        connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only=ON")
            records = dispatch[args.scenario](connection, **query_arguments[args.scenario])
        finally:
            connection.close()
    except (QueryError, sqlite3.Error, OSError, ValueError) as error:
        print(f"查询失败：{error}", file=sys.stderr)
        return 1

    if args.json_output:
        payload: dict[str, Any] = {
            "scenario": args.scenario,
            "count": len(records),
            "results": records,
        }
        if not records:
            payload["message"] = "未找到符合条件的记录。"
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    elif records:
        print(format_human(args.scenario, records))

    if not records:
        print(f"未找到符合条件的{args.scenario}记录。", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
