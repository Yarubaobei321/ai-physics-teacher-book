#!/usr/bin/env python3
"""生成待人工复核的题目—答案块候选清单。

这不是自动配对器：每一条候选都必须先在受控模板中逐题登记，输出只供人工核对。
工具不会改写 question 的 answer、solution 或任何原始 Word；确认关联仍须走人工复核流程。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
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
    json_bytes,
    safe_library_root,
    safe_output_path,
    write_json,
)
from source_state import SourceStateError, read_source_manifest  # noqa: E402


TEMPLATE_RELATIVE_PATH = "sources/answer-association-candidates.required3.chapter09.charge.json"
TEMPLATE_SCHEMA_RELATIVE_PATH = "schemas/answer-association-template.schema.json"
SOURCE_ID_RE = re.compile(r"^src\.bbg\.[0-9a-f]{64}$")
QUESTION_ID_RE = re.compile(r"^q\.src\.bbg\.[0-9a-f]{64}\.[0-9]{3}$")
ANSWER_BLOCK_ID_RE = re.compile(r"^ab\.src\.bbg\.[0-9a-f]{64}\.[0-9]{3}$")
TEMPLATE_ID_RE = re.compile(r"^assocq-template\.bbg\.[a-z0-9][a-z0-9._-]*$")
LOCATOR_RE = re.compile(r"^Markdown 第 ([1-9][0-9]*)(?:-([1-9][0-9]*))? 行；(.+)$")
NUMBERED_LABEL_RE = re.compile(r"^第([1-9][0-9]*)题$")
ALLOWED_CANDIDATE_BASES = {
    "same_variant_group",
    "same_chapter",
    "same_label",
    "manual_source_audit",
}


class AnswerAssociationError(PipelineError):
    """候选模板或当前结构化记录不足以安全生成清单。"""


def _safe_regular_file(root: Path, relative_path: str, *, label: str) -> Path:
    if not is_safe_relative_path(relative_path):
        raise AnswerAssociationError(f"{label} 路径不安全：{relative_path!r}")
    target = root.joinpath(*PurePosixPath(relative_path).parts)
    current = root
    for component in target.relative_to(root).parts:
        current = current / component
        if current.is_symlink():
            raise AnswerAssociationError(f"{label} 不能是符号链接或位于符号链接目录：{relative_path}")
    if not target.is_file():
        raise AnswerAssociationError(f"缺少 {label}：{relative_path}")
    try:
        target.resolve(strict=True).relative_to(root)
    except (OSError, ValueError) as error:
        raise AnswerAssociationError(f"{label} 越出资料库根：{relative_path}") from error
    return target


def _read_json_object(root: Path, relative_path: str, *, label: str) -> dict[str, Any]:
    path = _safe_regular_file(root, relative_path, label=label)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AnswerAssociationError(f"{label} 不是可读取的 JSON 对象：{relative_path}") from error
    if not isinstance(value, dict):
        raise AnswerAssociationError(f"{label} 必须是 JSON 对象：{relative_path}")
    return value


def _require_string(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise AnswerAssociationError(f"{field} 必须是非空字符串")
    return value


def _read_template(root: Path, relative_path: str) -> dict[str, Any]:
    template = _read_json_object(root, relative_path, label="答案关联候选模板")
    if template.get("schema_version") != "1.0":
        raise AnswerAssociationError("答案关联候选模板 schema_version 必须为 1.0")
    if not isinstance(template.get("templates"), list) or not template["templates"]:
        raise AnswerAssociationError("答案关联候选模板必须包含非空 templates 数组")
    return template


def _source_index(root: Path) -> dict[str, dict[str, Any]]:
    try:
        sources = read_source_manifest(root)
    except SourceStateError as error:
        raise AnswerAssociationError(f"无法读取 sources.jsonl：{error}") from error
    return {str(source["id"]): dict(source) for source in sources}


def _source(root: Path, sources: dict[str, dict[str, Any]], source_id: object, *, field: str) -> dict[str, Any]:
    if not isinstance(source_id, str) or not SOURCE_ID_RE.fullmatch(source_id):
        raise AnswerAssociationError(f"{field} 必须是完整 source_id")
    source = sources.get(source_id)
    if source is None:
        raise AnswerAssociationError(f"{field} 未在 sources.jsonl 中登记：{source_id}")
    path = source.get("relative_path")
    if not isinstance(path, str) or not path.startswith("raw/") or not is_safe_relative_path(path):
        raise AnswerAssociationError(f"{field} 的 raw 相对路径无效：{source_id}")
    return source


def _question_record(root: Path, source: dict[str, Any], question_id: object) -> dict[str, Any]:
    source_id = str(source["id"])
    if not isinstance(question_id, str) or not QUESTION_ID_RE.fullmatch(question_id):
        raise AnswerAssociationError("target_question_id 必须是完整 question ID")
    if not question_id.startswith(f"q.{source_id}."):
        raise AnswerAssociationError(f"target_question_id 不属于 target_source_id：{question_id}")
    relative_path = f"questions/{question_id}.json"
    question = _read_json_object(root, relative_path, label="目标题目记录")
    if (
        question.get("id") != question_id
        or question.get("source_id") != source_id
        or question.get("relative_path") != relative_path
    ):
        raise AnswerAssociationError(f"目标题目记录与模板身份不一致：{question_id}")
    if not isinstance(question.get("label"), str) or not question["label"]:
        raise AnswerAssociationError(f"目标题目缺少 label：{question_id}")
    source_location = question.get("source_location")
    if (
        not isinstance(source_location, dict)
        or source_location.get("relative_path") != source.get("relative_path")
        or not isinstance(source_location.get("locator"), str)
        or not source_location["locator"]
    ):
        raise AnswerAssociationError(f"目标题目来源位置无效：{question_id}")
    return question


def _answer_markdown(root: Path, source: dict[str, Any]) -> tuple[str, list[str]]:
    source_id = str(source["id"])
    relative_path = f"records/documents/{document_id_for(source_id)}.md"
    path = _safe_regular_file(root, relative_path, label="答案来源 Markdown")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise AnswerAssociationError(f"无法读取答案来源 Markdown：{relative_path}") from error
    return relative_path, lines


def _parse_candidate(candidate: object, *, answer_source_id: str, context: str) -> dict[str, Any]:
    if not isinstance(candidate, dict):
        raise AnswerAssociationError(f"{context} 必须是对象")
    answer_block_id = candidate.get("answer_block_id")
    label = candidate.get("label")
    locator = candidate.get("locator")
    bases = candidate.get("candidate_basis")
    if not isinstance(answer_block_id, str) or not ANSWER_BLOCK_ID_RE.fullmatch(answer_block_id):
        raise AnswerAssociationError(f"{context}.answer_block_id 格式无效")
    if not answer_block_id.startswith(f"ab.{answer_source_id}."):
        raise AnswerAssociationError(f"{context}.answer_block_id 未绑定 answer_source_id")
    if not isinstance(label, str) or not label:
        raise AnswerAssociationError(f"{context}.label 必须是非空字符串")
    if not isinstance(locator, str) or not LOCATOR_RE.fullmatch(locator):
        raise AnswerAssociationError(f"{context}.locator 必须为 Markdown 行号定位")
    if (
        not isinstance(bases, list)
        or not bases
        or any(not isinstance(value, str) or value not in ALLOWED_CANDIDATE_BASES for value in bases)
        or len(set(bases)) != len(bases)
    ):
        raise AnswerAssociationError(f"{context}.candidate_basis 无效")
    return {
        "answer_block_id": answer_block_id,
        "label": label,
        "locator": locator,
        "candidate_basis": bases,
    }


def _candidate_line_matches(candidate: dict[str, Any], lines: list[str]) -> bool:
    matched = LOCATOR_RE.fullmatch(candidate["locator"])
    assert matched is not None
    first_line = int(matched.group(1))
    last_line = int(matched.group(2) or first_line)
    if first_line > last_line or last_line > len(lines):
        return False
    excerpt = "\n".join(lines[first_line - 1 : last_line])
    label = candidate["label"]
    numbered = NUMBERED_LABEL_RE.fullmatch(label)
    if numbered:
        question_number = numbered.group(1)
        return bool(re.search(rf"(?m)^\s*{re.escape(question_number)}[．.]", excerpt))
    return label in excerpt


def _candidate_output(
    candidate: dict[str, Any], *, answer_source: dict[str, Any], markdown_path: str
) -> dict[str, Any]:
    return {
        "answer_block_id": candidate["answer_block_id"],
        "candidate_basis": candidate["candidate_basis"],
        "label": candidate["label"],
        "markdown_path": markdown_path,
        "source_id": answer_source["id"],
        "source_location": {
            "relative_path": answer_source["relative_path"],
            "locator": candidate["locator"],
        },
        "status": "pending_manual_review",
    }


def _validate_template_header(template: dict[str, Any]) -> tuple[str, str, dict[str, str], list[dict[str, Any]]]:
    template_id = template.get("id")
    output_path = template.get("relative_output_path")
    status = template.get("status")
    variant_group = template.get("variant_group")
    scope = template.get("scope")
    source_pairs = template.get("source_pairs")
    if not isinstance(template_id, str) or not TEMPLATE_ID_RE.fullmatch(template_id):
        raise AnswerAssociationError("关联模板 id 格式无效")
    if (
        not isinstance(output_path, str)
        or not output_path.startswith("reports/associations/")
        or not is_safe_relative_path(output_path)
    ):
        raise AnswerAssociationError("关联模板 relative_output_path 必须位于 reports/associations/")
    if status != "pending_manual_review":
        raise AnswerAssociationError("关联模板 status 必须为 pending_manual_review")
    if not isinstance(variant_group, str) or not variant_group:
        raise AnswerAssociationError("关联模板 variant_group 必须为非空字符串")
    if not isinstance(scope, dict) or set(scope) != {"course", "chapter", "topic"}:
        raise AnswerAssociationError("关联模板 scope 必须含 course、chapter、topic")
    checked_scope = {field: _require_string(scope[field], field=f"scope.{field}") for field in scope}
    if not isinstance(source_pairs, list) or not source_pairs:
        raise AnswerAssociationError("关联模板 source_pairs 必须为非空数组")
    return template_id, output_path, checked_scope, source_pairs


def _build_template_queue(
    root: Path, template: dict[str, Any], sources: dict[str, dict[str, Any]]
) -> tuple[str, dict[str, Any]]:
    template_id, output_path, scope, source_pairs = _validate_template_header(template)
    associations: list[dict[str, Any]] = []
    unmatched_blocks: list[dict[str, Any]] = []
    seen_targets: set[str] = set()
    seen_answer_blocks: set[str] = set()

    for pair_index, pair in enumerate(source_pairs, start=1):
        if not isinstance(pair, dict):
            raise AnswerAssociationError(f"source_pairs[{pair_index - 1}] 必须是对象")
        target_role = pair.get("target_role")
        if target_role not in {"learning_note", "practice"}:
            raise AnswerAssociationError(f"source_pairs[{pair_index - 1}].target_role 无效")
        target_source = _source(
            root, sources, pair.get("target_source_id"), field=f"source_pairs[{pair_index - 1}].target_source_id"
        )
        answer_source = _source(
            root, sources, pair.get("answer_source_id"), field=f"source_pairs[{pair_index - 1}].answer_source_id"
        )
        targets = pair.get("targets")
        if not isinstance(targets, list) or not targets:
            raise AnswerAssociationError(f"source_pairs[{pair_index - 1}].targets 必须为非空数组")
        markdown_path, answer_lines = _answer_markdown(root, answer_source)

        for target_index, target in enumerate(targets, start=1):
            if not isinstance(target, dict):
                raise AnswerAssociationError(f"targets[{target_index - 1}] 必须是对象")
            question_id = target.get("target_question_id")
            if not isinstance(question_id, str) or question_id in seen_targets:
                raise AnswerAssociationError(f"target_question_id 重复或无效：{question_id!r}")
            seen_targets.add(question_id)
            question = _question_record(root, target_source, question_id)
            configured_candidates = target.get("answer_candidates")
            if not isinstance(configured_candidates, list) or not configured_candidates:
                raise AnswerAssociationError(f"{question_id} 缺少 answer_candidates")
            candidates: list[dict[str, Any]] = []
            for candidate_index, raw_candidate in enumerate(configured_candidates, start=1):
                candidate = _parse_candidate(
                    raw_candidate,
                    answer_source_id=str(answer_source["id"]),
                    context=f"{question_id}.answer_candidates[{candidate_index - 1}]",
                )
                if candidate["answer_block_id"] in seen_answer_blocks:
                    raise AnswerAssociationError(f"answer_block_id 不可重复使用：{candidate['answer_block_id']}")
                if not _candidate_line_matches(candidate, answer_lines):
                    raise AnswerAssociationError(f"答案候选定位与 Markdown 内容不符：{candidate['answer_block_id']}")
                if "same_label" in candidate["candidate_basis"] and question["label"] != candidate["label"]:
                    raise AnswerAssociationError(f"同标签候选的题目标签不一致：{question_id}")
                seen_answer_blocks.add(candidate["answer_block_id"])
                candidates.append(
                    _candidate_output(candidate, answer_source=answer_source, markdown_path=markdown_path)
                )
            associations.append(
                {
                    "id": f"assocq.bbg.{template_id.removeprefix('assocq-template.bbg.')}.{len(associations) + 1:03d}",
                    "relation_type": "question_to_answer_block_candidate",
                    "review": {
                        "confirmed_answer_block_id": None,
                        "decision": None,
                    },
                    "status": "pending_manual_review",
                    "target": {
                        "label": question["label"],
                        "question_id": question_id,
                        "relative_path": question["relative_path"],
                        "source_id": target_source["id"],
                        "source_location": question["source_location"],
                    },
                    "answer_candidates": candidates,
                    "issues": [
                        "候选位置未经人工核对；不得写回 question.answer 或 question.solution。"
                    ],
                }
            )

        configured_unmatched = pair.get("unmatched_answer_blocks", [])
        if not isinstance(configured_unmatched, list):
            raise AnswerAssociationError(f"source_pairs[{pair_index - 1}].unmatched_answer_blocks 必须为数组")
        for unmatched_index, raw_candidate in enumerate(configured_unmatched, start=1):
            candidate = _parse_candidate(
                raw_candidate,
                answer_source_id=str(answer_source["id"]),
                context=f"unmatched_answer_blocks[{unmatched_index - 1}]",
            )
            if candidate["answer_block_id"] in seen_answer_blocks:
                raise AnswerAssociationError(f"answer_block_id 不可同时作为候选和未匹配块：{candidate['answer_block_id']}")
            if not _candidate_line_matches(candidate, answer_lines):
                raise AnswerAssociationError(f"未匹配答案块定位与 Markdown 内容不符：{candidate['answer_block_id']}")
            seen_answer_blocks.add(candidate["answer_block_id"])
            unmatched_blocks.append(
                {
                    **_candidate_output(candidate, answer_source=answer_source, markdown_path=markdown_path),
                    "issue": "答案块存在，但对应练习题尚未形成可靠结构化题目记录。",
                }
            )

    report = {
        "id": template_id.removeprefix("assocq-template."),
        "relative_path": output_path,
        "template_schema_path": TEMPLATE_SCHEMA_RELATIVE_PATH,
        "status": "pending_manual_review",
        "variant_group": template["variant_group"],
        "scope": scope,
        "association_policy": {
            "auto_match": False,
            "write_back_to_question": False,
            "required_next_step": "逐题对照原始 Word 与答案来源后，由人工确认；未确认候选不得作为答案。",
        },
        "associations": associations,
        "unmatched_answer_blocks": unmatched_blocks,
        "summary": {
            "candidate_answer_blocks": sum(len(item["answer_candidates"]) for item in associations),
            "confirmed_question_level_associations": 0,
            "pending_target_questions": len(associations),
            "unmatched_answer_blocks": len(unmatched_blocks),
        },
        "issues": [
            "本报告是人工复核队列，不是已确认的题号级答案关联。",
            "所有候选均保持 pending_manual_review；禁止把候选内容自动写入题目记录。",
        ],
    }
    return output_path, report


def build_answer_association_queues(
    library_root: Path | str = LIBRARY_ROOT,
    *,
    template_relative_path: str = TEMPLATE_RELATIVE_PATH,
) -> dict[str, dict[str, Any]]:
    """读取人工登记模板并返回稳定的候选报告；不写入任何文件。"""
    root = safe_library_root(library_root)
    if not template_relative_path.startswith("sources/") or not is_safe_relative_path(template_relative_path):
        raise AnswerAssociationError("模板必须位于 sources/ 下的安全相对路径")
    template_file = _read_template(root, template_relative_path)
    sources = _source_index(root)
    reports: dict[str, dict[str, Any]] = {}
    for raw_template in template_file["templates"]:
        if not isinstance(raw_template, dict):
            raise AnswerAssociationError("templates 项必须是对象")
        output_path, report = _build_template_queue(root, raw_template, sources)
        if output_path in reports:
            raise AnswerAssociationError(f"输出路径重复：{output_path}")
        reports[output_path] = report
    return reports


def write_answer_association_queues(
    library_root: Path | str = LIBRARY_ROOT,
    *,
    template_relative_path: str = TEMPLATE_RELATIVE_PATH,
) -> list[Path]:
    """原子写入候选报告；不会写 raw/、questions/ 或 reviews/。"""
    root = safe_library_root(library_root)
    reports = build_answer_association_queues(root, template_relative_path=template_relative_path)
    return [write_json(root, relative_path, report) for relative_path, report in reports.items()]


def check_answer_association_queues(
    library_root: Path | str = LIBRARY_ROOT,
    *,
    template_relative_path: str = TEMPLATE_RELATIVE_PATH,
) -> list[str]:
    """校验报告是否可由模板无差异重建；返回差异信息。"""
    root = safe_library_root(library_root)
    reports = build_answer_association_queues(root, template_relative_path=template_relative_path)
    errors: list[str] = []
    for relative_path, report in reports.items():
        try:
            path = safe_output_path(root, relative_path, create_parent=False)
        except PipelineError as error:
            errors.append(str(error))
            continue
        expected = json_bytes(report)
        if not path.is_file() or path.is_symlink():
            errors.append(f"缺少候选报告：{relative_path}")
        elif path.read_bytes() != expected:
            errors.append(f"候选报告与模板重建结果不一致：{relative_path}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成步步高题目—答案块人工复核候选清单")
    parser.add_argument("--root", type=Path, default=LIBRARY_ROOT, help="资料库根目录")
    parser.add_argument(
        "--template",
        default=TEMPLATE_RELATIVE_PATH,
        help="sources/ 下的人工候选模板相对路径",
    )
    parser.add_argument("--check", action="store_true", help="只校验现有候选报告是否可重建，不写入")
    args = parser.parse_args(argv)
    try:
        if args.check:
            errors = check_answer_association_queues(args.root, template_relative_path=args.template)
            if errors:
                print(f"答案关联候选报告校验失败：{len(errors)} 项", file=sys.stderr)
                for error in errors:
                    print(f"- {error}", file=sys.stderr)
                return 1
            print("答案关联候选报告校验通过：全部候选仍待人工复核，未自动配对。")
            return 0
        paths = write_answer_association_queues(args.root, template_relative_path=args.template)
    except (AnswerAssociationError, PipelineError) as error:
        print(f"生成答案关联候选报告失败：{error}", file=sys.stderr)
        return 1
    for path in paths:
        print(path.relative_to(safe_library_root(args.root)).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
