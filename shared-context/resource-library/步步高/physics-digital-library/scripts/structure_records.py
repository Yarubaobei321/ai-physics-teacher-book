#!/usr/bin/env python3
"""从正式资料库 Markdown 保守生成题目和知识记录。

结构化只读取 ``records/documents/*.md`` 和对应 document JSON。题目只有在题号和内容
边界明确时才生成；无法可靠界定的内容会保留在原 Markdown，并登记在 document 和报告的
问题列表中，不会被悄悄丢弃或伪装为已人工审核。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from library_common import (  # noqa: E402
    LIBRARY_ROOT,
    PROFILES,
    SOURCE_ID_RE,
    PipelineError,
    document_id_for,
    document_topic_id_for,
    heading_knowledge_id_for,
    is_safe_relative_path,
    json_bytes,
    official_library_root,
    question_id_for,
    read_json,
    safe_library_root,
    safe_output_path,
    remove_generated_file,
    source_short_for,
    write_json,
)


EXPLICIT_QUESTION_START_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?第\s*(?P<number>\d{1,3})\s*题\s*(?P<body>.+)$"
)
NUMBERED_ITEM_START_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?P<number>\d{1,3})(?:\s*\*\.\*|\s*[\.．、])\s*(?P<body>.+)$"
)
EXAMPLE_START_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:【\s*)?(?P<label>例题|典例|例|针对训练)\s*(?P<number>\d{1,3})?\s*(?:】)?\s*[:：.]?\s*(?P<body>.*)$"
)
# ``anydoc`` 会把部分 Word 选项包成 Markdown 引用块。选项标签和内容有时还会被
# 分成多行（例如 ``> A．`` 后接一个数学代码块），因此这里允许选项标签行暂时没有
# 文字；具体内容由 ``_option_entries`` 收集后再决定是否保留。
OPTION_RE = re.compile(r"^\s*(?P<label>[A-D])\s*[\.．、:：]\s*(?P<body>.*)$")
INLINE_OPTION_LABEL_RE = re.compile(r"(?<![A-Za-z])(?P<label>[A-D])\s*[\.．、:：]\s*")
MARKDOWN_BLOCK_QUOTE_RE = re.compile(r"^\s*>\s?(?P<body>.*)$")
ANSWER_RE = re.compile(r"^\s*(?:【\s*)?(?:答案|参考答案)(?:\s*】)?\s*[:：]?\s*(?P<body>.*)$")
SOLUTION_RE = re.compile(r"^\s*(?:【\s*)?(?:解析|答案解析|详解|解答|解析与答案)(?:\s*】)?\s*[:：]?\s*(?P<body>.*)$")
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(?P<label>.+?)\s*#*\s*$")
AMBIGUOUS_BOUNDARY_RE = re.compile(r"^\s*(?:第\s*\d{1,3}\s*题|\d{1,3}\s*[)）])")
EXAM_SECTION_HEADING_RE = re.compile(
    r"^\s*(?:[一二三四五六七八九十]+|\d+)\s*[、.．]\s*"
    r"(?P<section>单选题|多选题|不定项选择题|选择题|实验题|填空题|解答题|论述题)\s*$"
)
CONTENT_HEADING_RE = re.compile(r"^\s*(?:#{1,6}\s+|[一二三四五六七八九十]+、|考点[一二三四五六七八九十\d]+)")
PRACTICE_SCORE_HEADING_RE = re.compile(
    r"^\s*(?:\(?\s*\d+\s*分\s*\)?|\d+\s*(?:[~～\-]\s*\d+)?\s*题.*?分)"
)
PLAIN_CONTENT_LABEL_RE = re.compile(
    r"^\s*[\u4e00-\u9fffA-Za-z0-9（）()、，,]{2,30}"
    r"(?:的方法|的关系|的规律|的原理|的应用|的比较|的理解|的判断|的意义|的特点|的概念|的性质)\s*$"
)
TRUE_FALSE_JUDGEMENT_RE = re.compile(r"(?:[（(]\s*[√×]\s*[）)])\s*$")
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\((?:<(?P<angle>[^>]+)>|(?P<plain>[^\s)]+))[^)]*\)")
HTML_SOURCE_RE = re.compile(r"\bsrc\s*=\s*[\"'](?P<target>[^\"']+)[\"']", re.IGNORECASE)
LEADING_MARKDOWN_IMAGE_RE = re.compile(
    r"^\s*!\[[^\]]*\]\((?:<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)\s*"
)
LEADING_HTML_IMAGE_RE = re.compile(r"^\s*<img\b[^>]*>\s*", re.IGNORECASE)
QUESTION_PROMPT_RE = re.compile(
    r"(?:[（(][^）)]{0,120}[）)]|选择|下列|判断|求(?:出|解|)|计算|填空|作图|简答|实验|指出|写出|为什么|如何|是否|正确|错误|哪些|哪项)"
)
CHOICE_PROMPT_RE = re.compile(r"(?:[（(]\s*(?:多选)?\s*[）)]|下列.+?(?:正确|错误|说法|选项)|选择|以下.+?说法|哪(?:项|个))")
UNNUMBERED_PROMPT_RE = re.compile(r"^(?:思考[：:　\s]*)?(?P<body>.+?(?:[？?]|请(?:分析|说明|描述|判断|作答|作图|写出).*))$")
INLINE_MATH_RE = re.compile(r"(?<!\\)\$(?!\$)([^\n$]+?)(?<!\\)\$(?!\$)")
DISPLAY_MATH_RE = re.compile(r"\$\$(.+?)\$\$|\\\[(.+?)\\\]", re.DOTALL)
UNRESOLVED_IMAGE_DOCUMENT_ISSUE = "文档含提取图片，但 Markdown 未保留可靠图像位置锚点；图像位置未可靠关联"
UNRESOLVED_IMAGE_QUESTION_ISSUE = "图像位置未可靠关联，未将文档全部资产附加到本题"

VARIANT_ASSOCIATION_CONFIG_RELATIVE = "sources/variant-associations.json"
ASSOCIATION_ID_RE = re.compile(r"^assoc\.bbg\.[a-z0-9][a-z0-9._-]*$")


def _normalise_text(lines: list[str]) -> str:
    return "\n".join(line.strip() for line in lines if line.strip()).strip()


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    return [value for value in values if value and not (value in seen or seen.add(value))]


def _extract_formulas(markdown: str) -> list[str]:
    formulas: list[str] = []
    for match in DISPLAY_MATH_RE.finditer(markdown):
        value = next((part for part in match.groups() if part is not None), "").strip()
        if value and value not in formulas:
            formulas.append(value)
    for match in INLINE_MATH_RE.finditer(markdown):
        value = match.group(1).strip()
        if value and value not in formulas:
            formulas.append(value)
    return formulas


def _asset_paths_in_text(text: str, markdown_relative_path: str | None) -> list[str]:
    if not markdown_relative_path or not is_safe_relative_path(markdown_relative_path):
        return []
    parent = PurePosixPath(markdown_relative_path).parent.as_posix()
    values: list[str] = []
    for match in list(MARKDOWN_IMAGE_RE.finditer(text)) + list(HTML_SOURCE_RE.finditer(text)):
        target = (match.groupdict().get("angle") or match.groupdict().get("plain") or match.groupdict().get("target") or "")
        target = target.split("#", 1)[0].split("?", 1)[0].replace("\\", "/")
        candidate = posixpath.normpath(posixpath.join(parent, target))
        if is_safe_relative_path(candidate) and candidate.startswith("assets/"):
            values.append(candidate)
    return _unique_strings(values)


def _strip_leading_decorative_images(line: str) -> str:
    """只移除行首装饰图片，避免把题干中的图片或文字一起清掉。"""
    result = line
    while True:
        match = LEADING_MARKDOWN_IMAGE_RE.match(result) or LEADING_HTML_IMAGE_RE.match(result)
        if match is None:
            return result.strip()
        result = result[match.end() :]


def _is_teacher_or_textbook_question_boundary(line: str) -> bool:
    """判断讲义/教材中的下一个内容块是否必须终止前一题。

    题目后的普通标题、考点标题和课时练习分值说明都不属于上一题的解析。只用于
    ``teacher`` 与 ``textbook``，并保守地限定为显式 Markdown 标题、中文章节标题、
    考点标题或分值小节，避免截断题干中的普通叙述。
    """
    cleaned = _strip_leading_decorative_images(line)
    # Pandoc 会把 ``8~11`` 这类题号范围中的波浪线转为 ``8*~*11``。分节判断只看
    # 结构，不应被强调标记干扰。
    score_label = cleaned.replace("*~*", "~").replace("*.*", ".")
    return bool(
        CONTENT_HEADING_RE.match(cleaned)
        or PRACTICE_SCORE_HEADING_RE.match(score_label)
        or PLAIN_CONTENT_LABEL_RE.match(cleaned)
    )


def _is_decorative_image_only(line: str) -> bool:
    """判断行内是否仅有分节装饰图。

    分节标题前常带一个无文字的图标；当后续标题截断上一题时，该图标也不能成为
    上一题的配图。真正的题图通常还会与题干、选项或答案共同处于题块内部。
    """
    return bool(line.strip()) and not _strip_leading_decorative_images(line)


def _is_true_false_judgement_item(boundary: dict[str, str]) -> bool:
    """判断编号条目是否为讲义中的正误判断，而不是独立待解题。

    教师用书常把多条“(√)/(×)”知识判断紧接在一道无编号应用题前。它们没有单独
    答案块，不能占用无编号题目的开始位置，也不能吞入该题的题干。
    """
    return boundary.get("kind") == "numbered" and bool(TRUE_FALSE_JUDGEMENT_RE.search(boundary.get("body", "")))


def _boundary_from_line(line: str, profile: str) -> dict[str, str] | None:
    cleaned = _strip_leading_decorative_images(line)
    explicit = EXPLICIT_QUESTION_START_RE.match(cleaned)
    if explicit:
        return {
            "kind": "explicit",
            "label": f"第{explicit.group('number')}题",
            "body": explicit.group("body").strip(),
        }
    numbered = NUMBERED_ITEM_START_RE.match(cleaned)
    if numbered:
        return {
            "kind": "numbered",
            "label": f"第{numbered.group('number')}题",
            "body": numbered.group("body").strip(),
        }
    if profile in {"teacher", "textbook"}:
        example = EXAMPLE_START_RE.match(cleaned)
        if example:
            number = example.group("number")
            label = f"{example.group('label')}{number or ''}"
            body = _strip_leading_decorative_images(example.group("body"))
            if body:
                return {"kind": "example", "label": label, "body": body}
    return None


def _numbered_segment_has_question_evidence(
    lines: list[str], start: int, end: int, boundary: dict[str, str]
) -> bool:
    """教师/教材中的 ``1.`` 既可能是知识条目也可能是题号，故要求强证据。

    单独的编号、定义、知识梳理不会通过。存在完整 A-D 选项且有题干提示，或同时有
    题干提示与答案/解析标记的段落，才作为可结构化的题目。
    """
    segment = [boundary["body"], *(_strip_leading_decorative_images(line) for line in lines[start + 1 : end])]
    content = _normalise_text(segment)
    option_labels = [label for label, _, _ in _option_entries(segment)]
    has_full_options = option_labels == ["A", "B", "C", "D"]
    has_answer_or_solution = any(ANSWER_RE.match(line) or SOLUTION_RE.match(line) for line in segment)
    # 题干提示必须就在编号起始行中。否则“4. 对比理解”后面恰好出现一段无编号
    # 问答时，不能把知识条目误判为该问题的题号。
    has_prompt = bool(QUESTION_PROMPT_RE.search(boundary["body"]))
    return (has_full_options and (has_prompt or has_answer_or_solution)) or (has_prompt and has_answer_or_solution)


def _has_answer_before_next_boundary(lines: list[str], start: int, next_boundary: int) -> bool:
    for line in lines[start + 1 : next_boundary]:
        cleaned = _strip_leading_decorative_images(line)
        if ANSWER_RE.match(cleaned):
            return True
    return False


def _end_after_answer_block(lines: list[str], start: int, next_boundary: int) -> int | None:
    """返回无编号问答中紧随答案标记的连续答案块末行（exclusive）。"""
    answer_start: int | None = None
    for index in range(start + 1, next_boundary):
        cleaned = _strip_leading_decorative_images(lines[index])
        if ANSWER_RE.match(cleaned):
            answer_start = index
            break
    if answer_start is None:
        return None
    end = answer_start + 1
    while end < next_boundary and lines[end].strip():
        end += 1
    return end


def _unnumbered_question_boundary(
    lines: list[str], index: int, next_boundary: int
) -> dict[str, str] | None:
    """识别紧跟答案的无编号问答/“思考”块，避免其串入前一例题。"""
    cleaned = _strip_leading_decorative_images(lines[index])
    if not cleaned or not _has_answer_before_next_boundary(lines, index, next_boundary):
        return None
    # 普通教材正文也可能有“问题？答案”式讲解。只接受显式“思考”块，或真正以问号/
    # “请…”结束的独立问题；其余保留为无法可靠分段的原文和报告异常。
    is_thought = cleaned.startswith("思考")
    prompt = UNNUMBERED_PROMPT_RE.match(cleaned)
    # 教师用书中的无编号问答有时以“请分析……”开头、以句号结束。只要答案块已在
    # 紧随范围内，仍是足够强的题目证据；不能因此把前一条正误判断并入该题。
    has_explicit_request = "?" in cleaned or "？" in cleaned or "请" in cleaned
    if (prompt is None and not has_explicit_request) or (not is_thought and not has_explicit_request):
        return None
    answer_end = _end_after_answer_block(lines, index, next_boundary)
    if answer_end is None:
        return None
    body = cleaned
    if is_thought:
        body = re.sub(r"^思考[：:\u3000\s]*", "", body).strip()
    return {
        "kind": "unnumbered",
        "label": "思考" if is_thought else "无编号问答",
        # ``请分析`` 可能出现在很长的陈述句中，不能只保留正则命中的前半段。
        "body": body,
        "end": str(answer_end),
    }


def _normalise_option_body(lines: list[str]) -> str:
    """保留选项正文，并把单行数学围栏还原为便于阅读的行内公式。"""
    body = _normalise_text(lines)
    math_fence = re.fullmatch(r"```\s*math\s*\n(?P<formula>[^\n]+)\n```", body)
    if math_fence is not None:
        formula = math_fence.group("formula").strip()
        if formula:
            return f"${formula}$"
    return body


def _option_entries(lines: list[str]) -> list[tuple[str, str, set[int]]]:
    """读取独占行、压缩行和 Markdown 引用块中的 A–D 选项。

    Word 转 Markdown 后，表格式选项常被输出为如下引用块：

    ``> A．``
    ``> ``` math```
    ``> F_{M} < F_{N}``

    引用块内的公式行属于 A 选项，不应残留在题干。返回值的第三项是本选项占用的
    所有原始行号，供调用方完整地从题干移除。
    """
    entries: list[tuple[str, str, set[int]]] = []
    index = 0
    while index < len(lines):
        line = _strip_leading_decorative_images(lines[index])
        quote_match = MARKDOWN_BLOCK_QUOTE_RE.match(line)
        if quote_match is not None:
            quote_body = quote_match.group("body")
            matches = list(INLINE_OPTION_LABEL_RE.finditer(quote_body))
            if not matches or matches[0].start() != 0:
                index += 1
                continue

            # 同一引用行的压缩选项（``> A．甲 B．乙 ...``）沿用普通行的分割规则。
            if len(matches) > 1:
                for position, match in enumerate(matches):
                    body_end = matches[position + 1].start() if position + 1 < len(matches) else len(quote_body)
                    body = quote_body[match.end() : body_end].strip()
                    if body:
                        entries.append((match.group("label"), body, {index}))
                index += 1
                continue

            match = matches[0]
            option_lines = [quote_body[match.end() :].strip()]
            option_indices = {index}
            index += 1
            # 一条引用选项可以跨多行，尤其常见于被 anydoc 还原成数学代码块的选项。
            # 只吞入仍在同一引用块且未开启下一选项的行，普通正文和实验步骤不会被扩大。
            while index < len(lines):
                continuation = _strip_leading_decorative_images(lines[index])
                continuation_match = MARKDOWN_BLOCK_QUOTE_RE.match(continuation)
                if continuation_match is None:
                    break
                continuation_body = continuation_match.group("body")
                next_labels = list(INLINE_OPTION_LABEL_RE.finditer(continuation_body))
                if next_labels and next_labels[0].start() == 0:
                    break
                option_lines.append(continuation_body)
                option_indices.add(index)
                index += 1
            body = _normalise_option_body(option_lines)
            if body:
                entries.append((match.group("label"), body, option_indices))
            continue

        matches = list(INLINE_OPTION_LABEL_RE.finditer(line))
        if not matches or matches[0].start() != 0:
            index += 1
            continue
        for position, match in enumerate(matches):
            body_end = matches[position + 1].start() if position + 1 < len(matches) else len(line)
            body = line[match.end() : body_end].strip()
            if body:
                entries.append((match.group("label"), body, {index}))
        index += 1
    return entries


def _extract_question_segment(
    lines: list[str],
    start: int,
    end: int,
    boundary: dict[str, str],
    markdown_relative_path: str | None,
    profile: str,
) -> dict[str, object] | None:
    """抽取由清晰题号界定的一段内容；None 表示题干边界仍不可靠。"""
    body_lines = [boundary["body"]]
    content_end = end
    for index in range(start + 1, end):
        line = lines[index]
        # 同一份试卷的下一分节标题位于两个题号之间时，不能成为前一题的题干、答案或
        # 解析的一部分。例如 2024 新课标卷第 23 题后紧跟“四、解答题”。教师/教材
        # 的考点与课时练习小节同样必须终止前一题，不能被吸入解析。
        if profile == "gaokao" and EXAM_SECTION_HEADING_RE.match(_strip_leading_decorative_images(line)):
            # ``end_line`` 是最后一行内容的 1-based 行号；标题恰在下一行时其 0-based
            # 索引正好就是上一行的 1-based 行号。
            content_end = index
            break
        if profile in {"teacher", "textbook"} and _is_teacher_or_textbook_question_boundary(line):
            # 纯装饰图紧贴后续内容标题时属于新内容块，而不是上一题的图。标题本身不会
            # 被加入 body_lines，此处再回退掉已读取的装饰图，避免重复配图或错误关联。
            while len(body_lines) > 1 and _is_decorative_image_only(body_lines[-1]):
                body_lines.pop()
            content_end = index
            break
        body_lines.append(line)
    before_answer: list[str] = []
    answer_lines: list[str] = []
    solution_lines: list[str] = []
    current = before_answer
    for line in body_lines:
        marker_line = _strip_leading_decorative_images(line)
        answer_match = ANSWER_RE.match(marker_line)
        solution_match = SOLUTION_RE.match(marker_line)
        if solution_match:
            current = solution_lines
            value = solution_match.group("body").strip()
            if value:
                current.append(value)
            continue
        if answer_match:
            current = answer_lines
            value = answer_match.group("body").strip()
            if value:
                current.append(value)
            continue
        current.append(line)

    answer = _normalise_text(answer_lines) or None
    solution = _normalise_text(solution_lines) or None
    numbered_options = _option_entries(before_answer)
    option_labels = [label for label, _, _ in numbered_options]
    # 四个连续 A-D 加清楚的选择题题干，才满足保守的选择题边界。实验 A/B/C、
    # 实验步骤，即使凑巧含有字母，也不会进入 options。
    exam_section = boundary.get("exam_section")
    is_experiment_section = exam_section == "实验题"
    is_choice_section = exam_section in {"单选题", "多选题", "不定项选择题", "选择题"}
    answer_is_choice_label = bool(
        answer
        and re.fullmatch(r"[A-D](?:[、,，;；\s]?[A-D])*", answer.replace(" ", ""))
    )
    has_choice_prompt = bool(CHOICE_PROMPT_RE.search(_normalise_text(before_answer)))
    is_choice = (
        not is_experiment_section
        and option_labels == ["A", "B", "C", "D"]
        and has_choice_prompt
    ) or (
        # 教师用书/教材中少数选择题把完整选项嵌入题图。答案为 A-D 之一（或组合）且题干
        # 明确要求选择时，题型可可靠保留为选择题；文本选项仍保持为空，绝不凭空补写。
        profile in {"teacher", "textbook"}
        and not is_experiment_section
        and not option_labels
        and has_choice_prompt
        and answer_is_choice_label
    )
    if is_choice:
        option_indices = {
            index
            for _, _, option_line_indices in numbered_options
            for index in option_line_indices
        }
        stem_lines = [line for index, line in enumerate(before_answer) if index not in option_indices]
        options = [f"{label}. {body}" for label, body, _ in numbered_options]
        question_type = "选择题"
    else:
        stem_lines = before_answer
        options = []
        if is_experiment_section or "实验" in _normalise_text(before_answer):
            question_type = "实验题"
        elif is_choice_section:
            # 选项完全嵌在图中的高考题（如 2024 新课标卷第 14 题）不能虚构文本选项，
            # 但其所属分节仍足以可靠判定题型。
            question_type = "选择题"
        else:
            question_type = "非选择题"

    stem = _normalise_text(stem_lines)
    if not stem or len(stem.replace(" ", "")) < 2:
        return None
    full_text = "\n".join(body_lines)
    issues: list[str] = []
    if answer is None:
        issues.append("未识别到答案，需人工复核")
    if solution is None:
        issues.append("未识别到解析，需人工复核")
    if option_labels == ["A", "B", "C", "D"] and not is_choice:
        issues.append("检测到 A-D 标签但题干未明确为选择题，未拆分选项")
    if is_choice and not options:
        issues.append("选择题选项未在可解析文本中还原，需人工核对题图或原 Word")
    formulas = _extract_formulas(full_text)
    if formulas:
        issues.append("题目段落含公式，需人工核对公式转换")
    return {
        "label": boundary["label"],
        "locator": f"Markdown 第 {start + 1}-{content_end} 行；{boundary['label']}",
        "start_line": start + 1,
        "end_line": content_end,
        "question_type": question_type,
        "stem": stem,
        "options": options,
        "answer": answer,
        "solution": solution,
        "figures": _asset_paths_in_text(full_text, markdown_relative_path),
        "formula_latex": formulas,
        "issues": issues,
    }


def parse_markdown_questions(
    markdown: str, profile: str, *, markdown_relative_path: str | None = None
) -> dict[str, object]:
    """按 teacher / gaokao / textbook 的保守边界解析 Markdown。

    ``questions`` 中只有明确题号或教师/教材例题标记的记录。其余疑似题号会写入
    ``unresolved_segments``，让调用方加入 document issues 和结构化报告。
    """
    if profile not in PROFILES:
        raise ValueError(f"不支持的结构化 profile：{profile!r}")
    lines = markdown.splitlines()
    starts: list[tuple[int, dict[str, str]]] = []
    current_exam_section: str | None = None
    for index, line in enumerate(lines):
        section_heading = (
            EXAM_SECTION_HEADING_RE.match(_strip_leading_decorative_images(line))
            if profile == "gaokao"
            else None
        )
        if section_heading is not None:
            current_exam_section = section_heading.group("section")
        boundary = _boundary_from_line(line, profile)
        if boundary:
            if current_exam_section is not None:
                boundary["exam_section"] = current_exam_section
            starts.append((index, boundary))

    # 教师用书的“思考”或无编号问答常位于例题之后。教材的同类文本更常是讲解，
    # 因此只在 teacher profile 补充，避免把教材正文误提为题目。
    if profile == "teacher":
        initial_start_indexes = {index for index, _ in starts}
        for index in range(len(lines)):
            if index in initial_start_indexes:
                continue
            next_boundary = next(
                (candidate_index for candidate_index, _ in starts if candidate_index > index), len(lines)
            )
            boundary = _unnumbered_question_boundary(lines, index, next_boundary)
            if boundary is not None:
                starts.append((index, boundary))
        starts.sort(key=lambda item: item[0])

    questions: list[dict[str, object]] = []
    unresolved: list[str] = []
    known_starts = {index for index, _ in starts}
    for index, line in enumerate(lines):
        if index not in known_starts and AMBIGUOUS_BOUNDARY_RE.match(line):
            unresolved.append(f"Markdown 第 {index + 1} 行疑似题号边界不可靠，未生成题目记录")
    for position, (start, boundary) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        if boundary.get("end") is not None:
            end = min(end, int(boundary["end"]))
        if profile in {"teacher", "textbook"} and _is_true_false_judgement_item(boundary):
            unresolved.append(f"Markdown 第 {start + 1}-{end} 行正误判断条目未作为独立题目生成")
            continue
        if boundary["kind"] == "numbered" and profile in {"teacher", "textbook"}:
            if not _numbered_segment_has_question_evidence(lines, start, end, boundary):
                unresolved.append(
                    f"Markdown 第 {start + 1}-{end} 行编号条目缺少题干、答案或完整选项等强证据，未生成题目记录"
                )
                continue
        question = _extract_question_segment(lines, start, end, boundary, markdown_relative_path, profile)
        if question is None:
            unresolved.append(f"Markdown 第 {start + 1}-{end} 行题目内容不足或边界不可靠，未生成题目记录")
        else:
            questions.append(question)
    return {
        "questions": questions,
        "issues": _unique_strings(unresolved),
        "unresolved_segments": _unique_strings(unresolved),
    }


def _structure_paths(source_id: str) -> tuple[str, str, str, str]:
    document_id = document_id_for(source_id)
    source_short = source_short_for(source_id)
    return (
        document_id,
        f"records/documents/{document_id}.md",
        f"records/documents/{document_id}.json",
        f"reports/structure/{source_short}.json",
    )


def _markdown_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def structure_is_current(library_root: Path | str, source: dict[str, Any]) -> bool:
    """输入 Word/Markdown hash 与成功报告一致时，允许安全跳过结构化。"""
    try:
        root = safe_library_root(library_root)
        source_id = str(source["id"])
        _, markdown_relative, _, report_relative = _structure_paths(source_id)
        markdown_path = safe_output_path(root, markdown_relative, create_parent=False)
        report = read_json(safe_output_path(root, report_relative, create_parent=False))
        topic_path = safe_output_path(root, f"knowledge/{document_topic_id_for(source_id)}.json", create_parent=False)
    except (KeyError, OSError, PipelineError, ValueError):
        return False
    if not (
        markdown_path.is_file()
        and topic_path.is_file()
        and report
        and report.get("status") == "success"
        and report.get("source_id") == source_id
        and report.get("input_sha256") == source.get("sha256")
        and report.get("markdown_sha256") == _markdown_sha256(markdown_path)
    ):
        return False
    question_paths = report.get("question_paths")
    knowledge_paths = report.get("knowledge_paths")
    if not isinstance(question_paths, list) or not isinstance(knowledge_paths, list):
        return False
    try:
        for relative_path in question_paths:
            if not isinstance(relative_path, str) or not relative_path.startswith("questions/"):
                return False
            question = read_json(safe_output_path(root, relative_path, create_parent=False))
            if not question or question.get("source_id") != source_id:
                return False
        for relative_path in knowledge_paths:
            if not isinstance(relative_path, str) or not relative_path.startswith("knowledge/"):
                return False
            knowledge = read_json(safe_output_path(root, relative_path, create_parent=False))
            if not knowledge or source_id not in knowledge.get("source_ids", []):
                return False
    except (OSError, PipelineError):
        return False
    return True


def _validate_source_for_structure(source: dict[str, Any]) -> None:
    required = {"id", "relative_path", "sha256", "profile", "title"}
    missing = sorted(required - source.keys())
    if missing:
        raise PipelineError(f"来源清单缺少字段：{', '.join(missing)}")
    if not isinstance(source["id"], str) or not SOURCE_ID_RE.fullmatch(source["id"]):
        raise PipelineError("来源 ID 格式无效")
    if not isinstance(source["relative_path"], str) or not source["relative_path"].startswith("raw/"):
        raise PipelineError("来源相对路径必须位于 raw/")
    if source["profile"] not in PROFILES:
        raise PipelineError("来源 profile 无效")
    if not isinstance(source["title"], str) or not source["title"].strip():
        raise PipelineError("来源 title 不能为空")


def _topic_record(source: dict[str, Any]) -> dict[str, Any]:
    source_id = source["id"]
    topic_id = document_topic_id_for(source_id)
    return {
        "id": topic_id,
        "relative_path": f"knowledge/{topic_id}.json",
        "status": "ai_structured",
        "label": f"文档主题：{source['title']}",
        "description": "用于关联本来源已结构化题目的受控文档主题，不替代人工确认的学科知识点。",
        "parent_id": None,
        "aliases": [],
        "source_ids": [source_id],
    }


def _heading_candidates(source: dict[str, Any], markdown: str) -> list[tuple[int, dict[str, Any]]]:
    """返回候选标题知识点及其 Markdown 行号，不推断学科层级。"""
    candidates: list[tuple[int, dict[str, Any]]] = []
    labels_seen: set[str] = set()
    for line_number, line in enumerate(markdown.splitlines(), start=1):
        match = HEADING_RE.match(line)
        if not match:
            continue
        label = re.sub(r"\s+", " ", match.group("label").strip())
        if not label or label in labels_seen:
            continue
        labels_seen.add(label)
        knowledge_id = heading_knowledge_id_for(source["id"], len(candidates) + 1)
        candidates.append(
            (
                line_number,
                {
                    "id": knowledge_id,
                    "relative_path": f"knowledge/{knowledge_id}.json",
                    "status": "pending_manual_review",
                    "label": label,
                    "description": "由 Markdown 标题原样提取的候选知识点；其学科归属和层级需人工确认。",
                    "parent_id": document_topic_id_for(source["id"]),
                    "aliases": [],
                    "source_ids": [source["id"]],
                },
            )
        )
    return candidates


def _nearest_heading_knowledge_id(
    heading_candidates: list[tuple[int, dict[str, Any]]], question_start_line: object, fallback_id: str
) -> str:
    """仅使用题目前最近的 Markdown 标题；没有明确标题时回退到文档主题。"""
    if not isinstance(question_start_line, int):
        return fallback_id
    nearest: dict[str, Any] | None = None
    for heading_line, record in heading_candidates:
        if heading_line > question_start_line:
            break
        nearest = record
    return str(nearest["id"]) if nearest is not None else fallback_id


def _question_record(
    source: dict[str, Any],
    parsed: dict[str, object],
    sequence: int,
    *,
    source_needs_review: bool,
    knowledge_ids: list[str],
    unresolved_figure_positions: bool,
) -> dict[str, Any]:
    source_id = source["id"]
    question_id = question_id_for(source_id, sequence)
    issues = list(parsed["issues"])
    if source_needs_review:
        issues.append("来源文档存在待人工复核的转换或结构化问题")
    if unresolved_figure_positions:
        # ``figures`` 只保留 Markdown 中可验证的就地链接，绝不把整份文档资产挂到每题。
        issues.append(UNRESOLVED_IMAGE_QUESTION_ISSUE)
    issues = _unique_strings(issues)
    status = "pending_manual_review" if issues else "ai_structured"
    options = parsed["options"]
    confidence = 0.88 if parsed["question_type"] == "选择题" and parsed["answer"] else 0.62
    if status == "pending_manual_review":
        confidence = min(confidence, 0.58)
    return {
        "id": question_id,
        "relative_path": f"questions/{question_id}.json",
        "status": status,
        "source_id": source_id,
        "source_location": {"relative_path": source["relative_path"], "locator": parsed["locator"]},
        "label": parsed["label"],
        "question_type": parsed["question_type"],
        "stem": parsed["stem"],
        "options": options,
        "answer": parsed["answer"],
        "solution": parsed["solution"],
        "figures": parsed["figures"],
        "formula_latex": parsed["formula_latex"],
        "knowledge_ids": knowledge_ids or [document_topic_id_for(source_id)],
        "model_ids": None,
        "skill_ids": None,
        "difficulty": None,
        "extraction_confidence": confidence,
        "review_status": status,
        "issues": issues,
    }


def _updated_document(document: dict[str, Any], issues: list[str], *, needs_review: bool) -> dict[str, Any]:
    """仅更新 document schema 允许的 status/issues，保留转换阶段的其他信息。"""
    allowed = {
        "id",
        "source_id",
        "relative_path",
        "source_relative_path",
        "content_path",
        "title",
        "status",
        "extraction_profile",
        "asset_paths",
        "issues",
    }
    result = {key: value for key, value in document.items() if key in allowed}
    result["issues"] = _unique_strings(list(result.get("issues", [])) + issues)
    if result.get("status") != "blocked":
        result["status"] = "pending_manual_review" if needs_review or result["issues"] else "ai_structured"
    return result


def _write_structure_report(library_root: Path, relative_path: str, report: dict[str, Any]) -> None:
    write_json(library_root, relative_path, report)


def _previous_successful_structure_report(root: Path, report_relative: str, source_id: str) -> dict[str, Any] | None:
    """只读取当前来源自己留下的成功报告，绝不据不明 JSON 删除文件。"""
    try:
        report = read_json(safe_output_path(root, report_relative, create_parent=False))
    except (OSError, PipelineError):
        return None
    if not report or report.get("status") != "success" or report.get("source_id") != source_id:
        return None
    return report


def _remove_owned_generated_record(root: Path, relative_path: str, source_id: str, *, kind: str) -> bool:
    """安全清理本 source 已不再生成的题目/标题候选记录。"""
    expected_prefix = "questions/" if kind == "question" else "knowledge/"
    if not isinstance(relative_path, str) or not relative_path.startswith(expected_prefix):
        return False
    try:
        path = safe_output_path(root, relative_path, create_parent=False)
    except PipelineError:
        return False
    if not path.is_file() or path.is_symlink():
        return False
    record = read_json(path)
    if not record:
        return False
    if kind == "question":
        owned = record.get("source_id") == source_id
    else:
        topic_id = document_topic_id_for(source_id)
        owned = (
            isinstance(record.get("id"), str)
            and str(record["id"]).startswith(f"{topic_id}.h")
            and record.get("source_ids") == [source_id]
        )
    if not owned:
        return False
    return remove_generated_file(root, relative_path)


def _reconcile_source_structure_outputs(
    root: Path,
    previous_report: dict[str, Any] | None,
    *,
    source_id: str,
    current_question_paths: list[str],
    current_knowledge_paths: list[str],
) -> list[str]:
    """移除上次报告中、本次已不再生成且能证明归属当前 source 的记录。"""
    if previous_report is None:
        return []
    stale_questions = set(previous_report.get("question_paths", [])) - set(current_question_paths)
    stale_knowledge = set(previous_report.get("knowledge_paths", [])) - set(current_knowledge_paths)
    removed: list[str] = []
    for relative_path in sorted(stale_questions):
        if _remove_owned_generated_record(root, relative_path, source_id, kind="question"):
            removed.append(relative_path)
    for relative_path in sorted(stale_knowledge):
        if _remove_owned_generated_record(root, relative_path, source_id, kind="knowledge"):
            removed.append(relative_path)
    return removed


def build_association_reports(
    library_root: Path | str, sources: list[dict[str, Any]]
) -> list[str]:
    """按受控声明式配置写资料包的篇章级关联报告。

    配置中的每个来源都用 ``source_id + raw 相对路径`` 双重验证。关系只表达资料
    包级别的讲解、练习与独立答案关系，不会捏造题号级答案匹配。
    """
    root = safe_library_root(library_root)
    config_path = root / VARIANT_ASSOCIATION_CONFIG_RELATIVE
    if not config_path.is_file() or config_path.is_symlink():
        return []
    try:
        resolved_config = config_path.resolve(strict=True)
        resolved_config.relative_to(root)
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise PipelineError(f"资料包关联配置无效：{error}") from error
    if not isinstance(config, dict) or not isinstance(config.get("associations"), list):
        raise PipelineError("资料包关联配置必须包含 associations 数组")
    by_id = {str(source.get("id")): source for source in sources if isinstance(source, dict)}
    written_paths: list[str] = []
    for association in config["associations"]:
        if not isinstance(association, dict):
            raise PipelineError("资料包关联配置项必须是对象")
        association_id = association.get("id")
        variant_group = association.get("variant_group")
        scope = association.get("scope")
        configured_members = association.get("members")
        configured_relationships = association.get("relationships")
        if (
            not isinstance(association_id, str)
            or not ASSOCIATION_ID_RE.fullmatch(association_id)
            or not isinstance(variant_group, str)
            or not variant_group
            or not isinstance(scope, dict)
            or not isinstance(configured_members, list)
            or not isinstance(configured_relationships, list)
        ):
            raise PipelineError("资料包关联配置字段不完整或格式无效")
        members: list[dict[str, str]] = []
        role_to_source_id: dict[str, str] = {}
        for member in configured_members:
            if not isinstance(member, dict):
                raise PipelineError("资料包成员必须是对象")
            source_id = member.get("source_id")
            relative_path = member.get("relative_path")
            role = member.get("role")
            label = member.get("label")
            if (
                not isinstance(source_id, str)
                or not SOURCE_ID_RE.fullmatch(source_id)
                or not isinstance(relative_path, str)
                or not relative_path.startswith("raw/")
                or not is_safe_relative_path(relative_path)
                or not isinstance(role, str)
                or not re.fullmatch(r"[a-z][a-z0-9_]*", role)
                or not isinstance(label, str)
                or not label
                or role in role_to_source_id
            ):
                raise PipelineError("资料包成员字段无效或 role 重复")
            source = by_id.get(source_id)
            if source is None or source.get("relative_path") != relative_path:
                raise PipelineError(f"资料包成员未在当前 sources.jsonl 中按原路径登记：{source_id}")
            role_to_source_id[role] = source_id
            members.append(
                {"source_id": source_id, "relative_path": relative_path, "role": role, "label": label}
            )
        relationships: list[dict[str, object]] = []
        for relation in configured_relationships:
            if not isinstance(relation, dict):
                raise PipelineError("资料包关系必须是对象")
            from_role = relation.get("from_role")
            to_role = relation.get("to_role")
            relation_type = relation.get("type")
            relation_scope = relation.get("scope")
            question_level_match = relation.get("question_level_match", False)
            if (
                not isinstance(from_role, str)
                or not isinstance(to_role, str)
                or from_role not in role_to_source_id
                or to_role not in role_to_source_id
                or not isinstance(relation_type, str)
                or not re.fullmatch(r"[a-z][a-z0-9_]*", relation_type)
                or not isinstance(relation_scope, str)
                or relation_scope not in {"chapter_level", "collection_level"}
                or question_level_match is not False
            ):
                raise PipelineError("资料包关系字段无效；不允许自动建立题号级答案匹配")
            relationships.append(
                {
                    "from_source_id": role_to_source_id[from_role],
                    "to_source_id": role_to_source_id[to_role],
                    "type": relation_type,
                    "scope": relation_scope,
                    "question_level_match": False,
                    "review_status": "pending_manual_review",
                }
            )
        relative_path = f"reports/associations/{association_id}.json"
        report = {
            "id": association_id,
            "relative_path": relative_path,
            "status": "pending_manual_review",
            "variant_group": variant_group,
            "scope": scope,
            "members": members,
            "relationships": relationships,
            "issues": [
                "独立答案文档尚未建立题号级匹配；仅建立篇章/资料包级关系，需人工复核。"
            ],
        }
        write_json(root, relative_path, report)
        written_paths.append(relative_path)
    return written_paths


def structure_source(library_root: Path | str, source: dict[str, Any], *, force: bool = False) -> dict[str, Any]:
    """把已转换文档保守地写成题目/知识记录；模型记录默认留空。"""
    root = safe_library_root(library_root)
    try:
        _validate_source_for_structure(source)
        source_id = source["id"]
        document_id, markdown_relative, document_relative, report_relative = _structure_paths(source_id)
    except (PipelineError, KeyError, ValueError) as error:
        return {"success": False, "skipped": False, "issues": [str(error)], "error": str(error)}
    if not force and structure_is_current(root, source):
        return {
            "success": True,
            "skipped": True,
            "source_id": source_id,
            "document_id": document_id,
            "issues": [],
        }
    try:
        previous_report = _previous_successful_structure_report(root, report_relative, source_id)
        markdown_path = safe_output_path(root, markdown_relative, create_parent=False)
        document_path = safe_output_path(root, document_relative, create_parent=False)
        document = read_json(document_path)
        if not markdown_path.is_file() or not document:
            raise PipelineError("缺少成功转换后的 Markdown 或 document JSON；不能执行 structure-only")
        if document.get("source_id") != source_id or document.get("status") == "blocked":
            raise PipelineError("document 记录不对应当前来源，或转换已被阻断")
        markdown = markdown_path.read_text(encoding="utf-8")
        parsed = parse_markdown_questions(markdown, source["profile"], markdown_relative_path=markdown_relative)
        document_issues = list(parsed["issues"])
        source_needs_review = document.get("status") == "pending_manual_review" or bool(document.get("issues"))
        unresolved_figure_positions = bool(document.get("asset_paths")) and any(
            UNRESOLVED_IMAGE_DOCUMENT_ISSUE in str(issue)
            or "Markdown 未保留可靠图像位置锚点" in str(issue)
            or "题目图像未可靠关联" in str(issue)
            for issue in document.get("issues", [])
        )
        topic = _topic_record(source)
        heading_candidates = _heading_candidates(source, markdown)
        heading_records = [record for _, record in heading_candidates]
        questions = [
            _question_record(
                source,
                item,
                index,
                source_needs_review=source_needs_review,
                knowledge_ids=[
                    _nearest_heading_knowledge_id(
                        heading_candidates, item.get("start_line"), topic["id"]
                    )
                ],
                unresolved_figure_positions=unresolved_figure_positions,
            )
            for index, item in enumerate(parsed["questions"], start=1)
        ]
        question_issues = [issue for question in questions for issue in question["issues"]]
        needs_review = source_needs_review or bool(document_issues) or any(
            question["status"] == "pending_manual_review" for question in questions
        )
        write_json(root, topic["relative_path"], topic)
        for record in heading_records:
            write_json(root, record["relative_path"], record)
        for question in questions:
            write_json(root, question["relative_path"], question)
        removed_paths = _reconcile_source_structure_outputs(
            root,
            previous_report,
            source_id=source_id,
            current_question_paths=[question["relative_path"] for question in questions],
            current_knowledge_paths=[topic["relative_path"], *[record["relative_path"] for record in heading_records]],
        )
        updated_document = _updated_document(
            document, _unique_strings(document_issues + question_issues), needs_review=needs_review
        )
        write_json(root, document_relative, updated_document)
        knowledge_paths = [topic["relative_path"], *[record["relative_path"] for record in heading_records]]
        report = {
            "source_id": source_id,
            "source_relative_path": source["relative_path"],
            "input_sha256": source["sha256"],
            "markdown_sha256": _markdown_sha256(markdown_path),
            "status": "success",
            "paths": {
                "markdown": markdown_relative,
                "document": document_relative,
                "structure_log": report_relative,
            },
            "knowledge_paths": knowledge_paths,
            "question_paths": [question["relative_path"] for question in questions],
            "model_paths": [],
            "counts": {"questions": len(questions), "knowledge": len(knowledge_paths), "models": 0},
            "removed_paths": removed_paths,
            "issues": _unique_strings(document_issues + question_issues),
        }
        _write_structure_report(root, report_relative, report)
        return {
            "success": True,
            "skipped": False,
            "source_id": source_id,
            "document_id": document_id,
            "question_paths": report["question_paths"],
            "knowledge_paths": knowledge_paths,
            "removed_paths": removed_paths,
            "issues": report["issues"],
        }
    except (OSError, PipelineError, UnicodeError, ValueError) as error:
        message = str(error)
        report = {
            "source_id": source_id,
            "source_relative_path": source["relative_path"],
            "input_sha256": source["sha256"],
            "status": "failed",
            "paths": {
                "markdown": markdown_relative,
                "document": document_relative,
                "structure_log": report_relative,
            },
            "knowledge_paths": [],
            "question_paths": [],
            "model_paths": [],
            "counts": {"questions": 0, "knowledge": 0, "models": 0},
            "issues": [message],
        }
        _write_structure_report(root, report_relative, report)
        return {
            "success": False,
            "skipped": False,
            "source_id": source_id,
            "document_id": document_id,
            "issues": [message],
            "error": message,
        }


def _read_manifest(root: Path) -> list[dict[str, Any]]:
    manifest = root / "sources" / "sources.jsonl"
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise PipelineError(f"sources.jsonl 第 {line_number} 行无效：{error.msg}") from error
        if not isinstance(value, dict):
            raise PipelineError(f"sources.jsonl 第 {line_number} 行必须是对象")
        records.append(value)
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="结构化一个已转换的步步高来源文档")
    parser.add_argument("--source-id", required=True, help="要结构化的 src.bbg.* 来源 ID")
    parser.add_argument("--force", action="store_true", help="即使输入未变化也重新结构化")
    args = parser.parse_args(argv)
    try:
        root = official_library_root()
        source = next(record for record in _read_manifest(root) if record.get("id") == args.source_id)
    except (StopIteration, OSError, PipelineError) as error:
        print(f"结构化准备失败：{error}", file=sys.stderr)
        return 1
    result = structure_source(root, source, force=args.force)
    print(json_bytes(result).decode("utf-8"), end="")
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
