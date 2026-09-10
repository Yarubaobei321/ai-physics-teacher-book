#!/usr/bin/env python3
"""只读验收步步高 V1 的三个固定代表样本。

这个脚本是“正式产物”的回归门：它不会转换 Word、不会改写 JSON，也不会改变
任何复核状态。它只读取 sources、document 和 question 记录，确认已修复的关键
题目边界、题型、答案/解析计数及题图关联没有在后续批量重跑中退化。

用法（在工作区根目录）：

    python3 项目资源库/步步高/physics-digital-library/scripts/verify_regression_samples.py

任一约束不满足时进程返回非零，便于作为人工复核前和全库重跑后的验收门。
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


LIBRARY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID_RE = re.compile(r"^src\.bbg\.[0-9a-f]{64}$")
QUESTION_ID_RE = re.compile(r"^q\.src\.bbg\.[0-9a-f]{64}\.[0-9]{3}$")
IMAGE_REFERENCE_RE = re.compile(
    r"""
    <img\b[^>]*?\bsrc\s*=\s*(?:
        \"([^\"]+)\" | '([^']+)' | ([^\s>]+)
    )[^>]*>
    |
    !\[[^\]]*\]\(\s*(?:<([^>]+)>|([^\s)]+))(?:\s+[^)]*)?\)
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)
SCORE_LINE_RE = re.compile(r"\d+\s*\*?\s*[~～]\s*\*?\s*\d+\s*题\s*每小题\s*\d+\s*分")


@dataclass(frozen=True)
class SampleSpec:
    """一份固定代表样本的不可变身份和可验收计数。"""

    key: str
    source_id: str
    profile: str
    title: str
    question_count: int
    answer_count: int
    solution_count: int


TEACHER = SampleSpec(
    key="teacher_lesson_11",
    source_id="src.bbg.ca3a2b6b07c70b7c15d07b6d11d1810a4a6e1d0013cd3423dc065baa5c6443a9",
    profile="teacher",
    title="2026 大一轮教师用书：第三章第 11 课时",
    question_count=23,
    answer_count=23,
    solution_count=20,
)
GAOKAO = SampleSpec(
    key="gaokao_2024_new_curriculum",
    source_id="src.bbg.7e1ab406df4003cc74134b35a35be396f6baf6f1fc531061c8b4f01cb0759637",
    profile="gaokao",
    title="2024 年高考新课标卷物理真题",
    question_count=13,
    answer_count=13,
    solution_count=13,
)
TEXTBOOK = SampleSpec(
    key="required3_charge_instruction",
    source_id="src.bbg.2117ba6fd04cad6e62f860d75d4ff75f428376fb2fc39bde38e946804f47ea97",
    profile="textbook",
    title="必修 3 配套讲解：第九章第 1 节电荷",
    question_count=21,
    answer_count=21,
    solution_count=19,
)
SAMPLES = (TEACHER, GAOKAO, TEXTBOOK)


class RegressionVerificationError(RuntimeError):
    """代表样本的已知验收规则未满足。"""

    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = list(errors)
        super().__init__("\n".join(self.errors))


def _source_short(source_id: str) -> str:
    if not SOURCE_ID_RE.fullmatch(source_id):
        raise ValueError(f"非法 source_id：{source_id!r}")
    return source_id.rsplit(".", 1)[-1][:16]


def _relative_document_path(source_id: str) -> str:
    return f"records/documents/doc.bbg.{_source_short(source_id)}.json"


def _safe_read_json(root: Path, relative_path: str, errors: list[str], *, label: str) -> dict[str, Any] | None:
    candidate = root.joinpath(*PurePosixPath(relative_path).parts)
    try:
        candidate.relative_to(root)
    except ValueError:
        errors.append(f"{label} 路径越出资料库：{relative_path}")
        return None
    if not candidate.is_file():
        errors.append(f"缺少{label}：{relative_path}")
        return None
    try:
        value = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        errors.append(f"无法读取{label}：{relative_path}（{error}）")
        return None
    if not isinstance(value, dict):
        errors.append(f"{label} 必须是 JSON 对象：{relative_path}")
        return None
    return value


def _read_sources(root: Path, errors: list[str]) -> dict[str, dict[str, Any]]:
    manifest = root / "sources" / "sources.jsonl"
    if not manifest.is_file():
        errors.append("缺少来源清单：sources/sources.jsonl")
        return {}
    sources: dict[str, dict[str, Any]] = {}
    try:
        lines = manifest.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        errors.append(f"无法读取来源清单：{error}")
        return sources
    for line_number, line in enumerate(lines, start=1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            errors.append(f"sources/sources.jsonl 第 {line_number} 行无法解析：{error.msg}")
            continue
        if not isinstance(value, dict) or not isinstance(value.get("id"), str):
            errors.append(f"sources/sources.jsonl 第 {line_number} 行不是带 id 的对象")
            continue
        source_id = value["id"]
        if source_id in sources:
            errors.append(f"sources/sources.jsonl 存在重复 source_id：{source_id}")
            continue
        sources[source_id] = value
    return sources


def _has_content(value: Any) -> bool:
    """答案/解析字段在 schema 允许的三种容器中是否确有内容。"""
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(_has_content(item) for item in value)
    if isinstance(value, dict):
        return any(_has_content(item) for item in value.values())
    return False


def _text_fragments(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _text_fragments(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _text_fragments(item)


def _question_text(question: dict[str, Any]) -> str:
    return "\n".join(
        fragment
        for field in ("label", "stem", "options", "answer", "solution")
        for fragment in _text_fragments(question.get(field))
    )


def _normalise_asset_reference(value: str) -> str | None:
    """把 document Markdown 中的图片 URL 还原为资料库 assets 相对路径。"""
    reference = value.strip().replace("\\", "/")
    if not reference or "://" in reference or reference.startswith(("data:", "#")):
        return None
    normalized = posixpath.normpath(
        posixpath.join("records/documents", reference.split("#", 1)[0].split("?", 1)[0])
    )
    if normalized.startswith("../") or normalized == ".." or not normalized.startswith("assets/"):
        return None
    return normalized


def _image_references(question: dict[str, Any]) -> tuple[set[str], list[str]]:
    assets: set[str] = set()
    unsafe: list[str] = []
    for match in IMAGE_REFERENCE_RE.finditer(_question_text(question)):
        raw_reference = next((value for value in match.groups() if value is not None), "")
        normalized = _normalise_asset_reference(raw_reference)
        if normalized is None:
            unsafe.append(raw_reference)
        else:
            assets.add(normalized)
    return assets, unsafe


def _questions_for_source(root: Path, source_id: str, errors: list[str]) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    directory = root / "questions"
    if not directory.is_dir():
        errors.append("缺少题目目录：questions/")
        return questions
    for path in sorted(directory.glob(f"q.{source_id}.*.json"), key=lambda item: item.name):
        relative_path = path.relative_to(root).as_posix()
        question = _safe_read_json(root, relative_path, errors, label="题目记录")
        if question is None:
            continue
        question_id = question.get("id")
        if not isinstance(question_id, str) or not QUESTION_ID_RE.fullmatch(question_id):
            errors.append(f"题目记录 id 格式无效：{relative_path}")
            continue
        if question_id != path.stem or question.get("source_id") != source_id:
            errors.append(f"题目记录身份与文件名或来源不一致：{relative_path}")
            continue
        questions.append(question)
    return questions


def _find_question(questions: list[dict[str, Any]], label: str) -> dict[str, Any] | None:
    matches = [question for question in questions if question.get("label") == label]
    return matches[0] if len(matches) == 1 else None


def _check_source_identity(
    spec: SampleSpec,
    source: dict[str, Any] | None,
    errors: list[str],
) -> None:
    if source is None:
        errors.append(f"{spec.title}：来源清单缺少固定 source_id")
        return
    if source.get("profile") != spec.profile:
        errors.append(f"{spec.title}：profile 应为 {spec.profile!r}，实际为 {source.get('profile')!r}")


def _check_document_identity_and_pending(
    root: Path,
    spec: SampleSpec,
    errors: list[str],
) -> dict[str, Any] | None:
    document = _safe_read_json(
        root,
        _relative_document_path(spec.source_id),
        errors,
        label=f"{spec.title} document",
    )
    if document is None:
        return None
    if document.get("source_id") != spec.source_id:
        errors.append(f"{spec.title}：document source_id 不匹配")
    return document


def _check_counts(spec: SampleSpec, questions: list[dict[str, Any]], errors: list[str]) -> None:
    if len(questions) != spec.question_count:
        errors.append(f"{spec.title}：题目数应为 {spec.question_count}，实际为 {len(questions)}")
    answer_count = sum(_has_content(question.get("answer")) for question in questions)
    solution_count = sum(_has_content(question.get("solution")) for question in questions)
    if answer_count != spec.answer_count:
        errors.append(f"{spec.title}：有答案的题目数应为 {spec.answer_count}，实际为 {answer_count}")
    if solution_count != spec.solution_count:
        errors.append(f"{spec.title}：有解析的题目数应为 {spec.solution_count}，实际为 {solution_count}")


def _check_question_image_associations(
    root: Path,
    spec: SampleSpec,
    questions: list[dict[str, Any]],
    errors: list[str],
) -> int:
    referenced_count = 0
    for question in questions:
        referenced, unsafe = _image_references(question)
        question_id = question.get("id", "<未知题目>")
        if unsafe:
            errors.append(f"{spec.title}：{question_id} 有无法追溯的题图引用：{', '.join(unsafe)}")
        figures = question.get("figures")
        if not isinstance(figures, list) or any(not isinstance(item, str) for item in figures):
            errors.append(f"{spec.title}：{question_id} 的 figures 不是字符串数组")
            continue
        figure_set = set(figures)
        missing = sorted(referenced - figure_set)
        if missing:
            errors.append(
                f"{spec.title}：{question_id} 的题图线索未关联 figures：{', '.join(missing)}"
            )
        for asset in sorted(figure_set):
            candidate = root.joinpath(*PurePosixPath(asset).parts)
            if not asset.startswith("assets/") or not candidate.is_file():
                errors.append(f"{spec.title}：{question_id} 关联的题图不存在：{asset}")
        referenced_count += len(referenced)
    return referenced_count


def _check_teacher(root: Path, source: dict[str, Any] | None, errors: list[str]) -> dict[str, Any]:
    _check_source_identity(TEACHER, source, errors)
    _check_document_identity_and_pending(root, TEACHER, errors)
    questions = _questions_for_source(root, TEACHER.source_id, errors)
    _check_counts(TEACHER, questions, errors)
    types = Counter(question.get("question_type") for question in questions)
    if types["选择题"] != 19 or sum(types.values()) - types["选择题"] != 4:
        errors.append(
            f"{TEACHER.title}：题型应为 19 道选择题和 4 道非选择题，实际为 {dict(types)}"
        )
    rain_questions = [question for question in questions if "雨滴下落" in str(question.get("stem", ""))]
    if len(rain_questions) != 1:
        errors.append(f"{TEACHER.title}：应恰有 1 道雨滴题，实际为 {len(rain_questions)}")
    elif not str(rain_questions[0].get("stem", "")).lstrip().startswith("某同学为研究雨滴下落的规律"):
        errors.append(f"{TEACHER.title}：雨滴题题干起始不正确，疑似仍吞入前一段内容")
    leakage_terms = ("考点二　牛顿第二定律", "判断超重和失重的方法", "课时精练")
    for question in questions:
        text = _question_text(question)
        for term in leakage_terms:
            if term in text:
                errors.append(f"{TEACHER.title}：{question.get('id')} 泄漏了后续标题「{term}」")
        if SCORE_LINE_RE.search(text):
            errors.append(f"{TEACHER.title}：{question.get('id')} 泄漏了后续分值行")
    image_reference_count = _check_question_image_associations(root, TEACHER, questions, errors)
    return {
        "question_count": len(questions),
        "question_types": dict(sorted(types.items())),
        "image_reference_count": image_reference_count,
    }


def _check_gaokao(root: Path, source: dict[str, Any] | None, errors: list[str]) -> dict[str, Any]:
    _check_source_identity(GAOKAO, source, errors)
    document = _check_document_identity_and_pending(root, GAOKAO, errors)
    questions = _questions_for_source(root, GAOKAO.source_id, errors)
    _check_counts(GAOKAO, questions, errors)
    question_14 = _find_question(questions, "第14题")
    if question_14 is None:
        errors.append(f"{GAOKAO.title}：缺少或重复第 14 题")
    elif question_14.get("question_type") != "选择题":
        errors.append(f"{GAOKAO.title}：第 14 题应为选择题，实际为 {question_14.get('question_type')!r}")
    question_23 = _find_question(questions, "第23题")
    if question_23 is None:
        errors.append(f"{GAOKAO.title}：缺少或重复第 23 题")
    else:
        if question_23.get("question_type") != "实验题":
            errors.append(f"{GAOKAO.title}：第 23 题应为实验题，实际为 {question_23.get('question_type')!r}")
        if "四、解答题" in _question_text(question_23):
            errors.append(f"{GAOKAO.title}：第 23 题仍吞入「四、解答题」")
        if any(str(option).lstrip().startswith(("A.", "A．", "A、")) for option in question_23.get("options", [])):
            errors.append(f"{GAOKAO.title}：第 23 题的实验步骤仍被误识别为选择题选项")
    if source is not None and source.get("status") != "pending_manual_review":
        errors.append(f"{GAOKAO.title}：来源图/公式异常应仍待人工复核，实际来源状态为 {source.get('status')!r}")
    if document is not None:
        if document.get("status") != "pending_manual_review":
            errors.append(f"{GAOKAO.title}：document 图/公式异常应仍待人工复核，实际为 {document.get('status')!r}")
        issues = document.get("issues") if isinstance(document.get("issues"), list) else []
        issue_lines = [str(issue) for issue in issues]
        if not any("图" in issue and "人工" in issue for issue in issue_lines):
            errors.append(f"{GAOKAO.title}：document 未保留待人工核对的题图异常")
        if not any("公式" in issue and "人工" in issue for issue in issue_lines):
            errors.append(f"{GAOKAO.title}：document 未保留待人工核对的公式异常")
    for question in (question_14, question_23):
        if question is not None and question.get("status") != "pending_manual_review":
            errors.append(f"{GAOKAO.title}：{question.get('id')} 应仍待人工复核")
    image_reference_count = _check_question_image_associations(root, GAOKAO, questions, errors)
    return {
        "question_count": len(questions),
        "image_reference_count": image_reference_count,
        "q14_type": question_14.get("question_type") if question_14 else None,
        "q23_type": question_23.get("question_type") if question_23 else None,
    }


def _check_textbook(root: Path, source: dict[str, Any] | None, errors: list[str]) -> dict[str, Any]:
    _check_source_identity(TEXTBOOK, source, errors)
    _check_document_identity_and_pending(root, TEXTBOOK, errors)
    questions = _questions_for_source(root, TEXTBOOK.source_id, errors)
    _check_counts(TEXTBOOK, questions, errors)
    leakage_terms = ("考点一　电荷量与元电荷", "考点二　三种起电方式")
    for question in questions:
        text = _question_text(question)
        for term in leakage_terms:
            if term in text:
                errors.append(f"{TEXTBOOK.title}：{question.get('id')} 泄漏了后续标题「{term}」")
        if SCORE_LINE_RE.search(text):
            errors.append(f"{TEXTBOOK.title}：{question.get('id')} 泄漏了后续分值行")
    image_reference_count = _check_question_image_associations(root, TEXTBOOK, questions, errors)
    return {
        "question_count": len(questions),
        "image_reference_count": image_reference_count,
    }


def verify_regression_samples(root: Path | str = LIBRARY_ROOT) -> dict[str, Any]:
    """执行正式样本的只读验收；失败时抛出带全部问题的异常。"""
    library_root = Path(root)
    errors: list[str] = []
    if not library_root.is_dir():
        raise RegressionVerificationError([f"资料库根不存在或不是目录：{library_root}"])
    try:
        library_root = library_root.resolve(strict=True)
    except OSError as error:
        raise RegressionVerificationError([f"无法解析资料库根：{library_root}（{error}）"]) from error
    sources = _read_sources(library_root, errors)
    summary = {
        "root": library_root.as_posix(),
        "samples": {
            TEACHER.key: _check_teacher(library_root, sources.get(TEACHER.source_id), errors),
            GAOKAO.key: _check_gaokao(library_root, sources.get(GAOKAO.source_id), errors),
            TEXTBOOK.key: _check_textbook(library_root, sources.get(TEXTBOOK.source_id), errors),
        },
    }
    if errors:
        raise RegressionVerificationError(errors)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="只读验收步步高 V1 三个固定代表样本")
    parser.add_argument(
        "--root",
        type=Path,
        default=LIBRARY_ROOT,
        help="正式资料库根目录；默认使用本脚本所在的 physics-digital-library",
    )
    parser.add_argument("--json", action="store_true", help="以 JSON 输出通过摘要")
    return parser


def main(arguments: list[str] | None = None) -> int:
    args = _parser().parse_args(arguments)
    try:
        summary = verify_regression_samples(args.root)
    except RegressionVerificationError as error:
        print("代表样本回归验收未通过：", file=sys.stderr)
        for message in error.errors:
            print(f"- {message}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print("代表样本回归验收通过：教师用书、2024 新课标卷、必修 3 电荷讲解均符合固定约束。")
        for key, details in summary["samples"].items():
            print(f"- {key}: {json.dumps(details, ensure_ascii=False, sort_keys=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
