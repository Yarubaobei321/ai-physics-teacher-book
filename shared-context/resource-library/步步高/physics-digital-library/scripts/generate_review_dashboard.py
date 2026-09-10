#!/usr/bin/env python3
"""生成可直接点击使用的步步高人工复核入口。

这个入口只读取已生成的来源、文档和题目记录。它把每一份待核资料的原始
Word、转换后的 Markdown、document JSON 和逐题 JSON 放在同一页，方便非技术
使用者直接对照。生成或打开该页面不会改变任何复核状态。
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from library_common import (  # noqa: E402
    LIBRARY_ROOT,
    PipelineError,
    SOURCE_ID_RE,
    document_id_for,
    is_safe_relative_path,
    official_library_root,
    safe_library_root,
    safe_source_path,
    source_short_for,
    write_text,
)


DASHBOARD_PATH = "reviews/人工复核入口.md"
DASHBOARD_VERSION = "1.1"
QUESTION_CARDS_DIRECTORY = "reviews/question-cards"
LINE_LOCATOR_RE = re.compile(r"Markdown\s*第\s*(\d+)\s*(?:[-—–至]\s*\d+)?\s*行")
HTML_IMAGE_SOURCE_RE = re.compile(
    r'(?P<prefix><img\b[^>]*?\bsrc=["\'])(?P<path>[^"\']+)(?P<suffix>["\'])',
    re.IGNORECASE,
)
MARKDOWN_IMAGE_SOURCE_RE = re.compile(r"(?P<prefix>!\[[^\]]*\]\()(?P<path>[^\s)]+)(?P<suffix>\))")

# 这四份资料不是“已经通过”的样本，而是最适合先做人工核对的固定入口：
# 用户指出的公式呈现问题、三个 V1 回归样本各一份。
DEFAULT_FOCUS_SOURCES: tuple[dict[str, str], ...] = (
    {
        "source_id": "src.bbg.9b172047ac423c7d50253c647b58c8de6db75163b93d426b1a6f5fd93f78ac69",
        "reason": "用户指出的公式行内呈现问题；先核对第 2 题及同卷题目。",
    },
    {
        "source_id": "src.bbg.ca3a2b6b07c70b7c15d07b6d11d1810a4a6e1d0013cd3423dc065baa5c6443a9",
        "reason": "教师用书固定回归样本：确认 23 题边界没有吞入后续课时内容。",
    },
    {
        "source_id": "src.bbg.7e1ab406df4003cc74134b35a35be396f6baf6f1fc531061c8b4f01cb0759637",
        "reason": "高考卷固定回归样本：确认第 23 题仍是实验题，A/B/C 为实验步骤。",
    },
    {
        "source_id": "src.bbg.2117ba6fd04cad6e62f860d75d4ff75f428376fb2fc39bde38e946804f47ea97",
        "reason": "必修 3 电荷固定回归样本：核对讲解、练习、独立答案与 21 道题的关联。",
    },
)


class ReviewDashboardError(RuntimeError):
    """人工复核入口无法安全构建时抛出。"""


def _read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _inside_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _safe_library_file(root: Path, relative_path: object) -> Path | None:
    """只返回资料库内的普通文件，拒绝越界路径和输出链接。"""
    if not is_safe_relative_path(relative_path):
        return None
    candidate = root.joinpath(*PurePosixPath(str(relative_path)).parts)
    if candidate.is_symlink() or not candidate.is_file():
        return None
    try:
        resolved = candidate.resolve(strict=True)
    except OSError:
        return None
    return resolved if _inside_root(resolved, root) else None


def _load_sources(root: Path) -> dict[str, dict[str, Any]]:
    manifest = _safe_library_file(root, "sources/sources.jsonl")
    if manifest is None:
        raise ReviewDashboardError("缺少或无法安全读取 sources/sources.jsonl")
    sources: dict[str, dict[str, Any]] = {}
    try:
        lines = manifest.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise ReviewDashboardError(f"无法读取来源清单：{error}") from error
    for line_number, line in enumerate(lines, start=1):
        try:
            source = json.loads(line)
        except json.JSONDecodeError as error:
            raise ReviewDashboardError(
                f"sources/sources.jsonl 第 {line_number} 行无法解析：{error.msg}"
            ) from error
        source_id = source.get("id") if isinstance(source, dict) else None
        if (
            not isinstance(source_id, str)
            or not SOURCE_ID_RE.fullmatch(source_id)
            or source_id in sources
        ):
            raise ReviewDashboardError(f"sources/sources.jsonl 第 {line_number} 行来源 ID 无效或重复")
        sources[source_id] = source
    return sources


def _document_path_for(source_id: str) -> str:
    return f"records/documents/{document_id_for(source_id)}.json"


def _load_document(root: Path, source_id: str) -> tuple[Path | None, dict[str, Any] | None]:
    relative_path = _document_path_for(source_id)
    path = _safe_library_file(root, relative_path)
    record = _read_json_object(path) if path is not None else None
    if record is None or record.get("source_id") != source_id or record.get("relative_path") != relative_path:
        return None, None
    return path, record


def _load_questions(root: Path, source_id: str) -> list[tuple[Path, dict[str, Any]]]:
    directory = root / "questions"
    if directory.is_symlink() or not directory.is_dir():
        return []
    questions: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(directory.glob(f"q.{source_id}.*.json"), key=lambda item: item.name):
        if path.is_symlink() or not path.is_file():
            continue
        relative_path = path.relative_to(root).as_posix()
        safe_path = _safe_library_file(root, relative_path)
        if safe_path is None:
            continue
        record = _read_json_object(safe_path)
        if record is None:
            continue
        if (
            record.get("source_id") != source_id
            or record.get("relative_path") != relative_path
            or record.get("id") != path.stem
        ):
            continue
        questions.append((safe_path, record))
    return questions


def _line_from_locator(value: object) -> int | None:
    if not isinstance(value, str):
        return None
    matched = LINE_LOCATOR_RE.search(value)
    return int(matched.group(1)) if matched else None


def _question_card_relative_path(source_id: str, question_id: object) -> str | None:
    """返回题目对照卡的固定安全路径。

    题目 ID 来自 JSON，不能直接作为文件路径使用；这里只接受资料库规定的
    ``q.<完整 source_id>.<序号>`` 形式，再取纯数字序号作为文件名。
    """
    if not isinstance(question_id, str):
        return None
    matched = re.fullmatch(rf"q\.{re.escape(source_id)}\.(\d{{3,}})", question_id)
    if matched is None:
        return None
    return f"{QUESTION_CARDS_DIRECTORY}/{source_short_for(source_id)}/{matched.group(1)}.md"


def _output_path(root: Path, relative_path: str) -> Path:
    """由本模块生成的受控相对路径转换为绝对路径，供页面跳转使用。"""
    return root.joinpath(*PurePosixPath(relative_path).parts)


def _unique_strings(values: Iterable[object]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def _list_strings(values: object) -> list[str]:
    """只接收 JSON 数组，避免错误数据被按单个字符拆开。"""
    return _unique_strings(values) if isinstance(values, list) else []


def _review_issues(values: object) -> list[str]:
    """保留用户可行动的问题，去掉仅重复说明待审状态的汇总提示。"""
    if not isinstance(values, list):
        return []
    ignored = {
        "来源文档存在待人工复核的转换或结构化问题",
        "来源清单或关联记录已标记 pending_manual_review，需人工复核",
    }
    return [issue for issue in _unique_strings(values) if issue not in ignored]


def _question_summary(record: dict[str, Any]) -> str:
    issue_count = len(_review_issues(record.get("issues")))
    pieces = [
        str(record.get("question_type") or "题型待核对"),
        "答案已提取" if str(record.get("answer") or "").strip() else "答案待核对",
        "解析已提取" if str(record.get("solution") or "").strip() else "解析待核对",
    ]
    if issue_count:
        pieces.append(f"{issue_count} 项自动提醒")
    return "；".join(pieces)


def _focus_requests(
    sources: dict[str, dict[str, Any]], source_ids: Iterable[str] | None
) -> list[dict[str, str]]:
    if source_ids:
        requested: list[dict[str, str]] = []
        seen: set[str] = set()
        for source_id in source_ids:
            if source_id in seen:
                continue
            seen.add(source_id)
            requested.append({"source_id": source_id, "reason": "按指定来源生成。"})
        return requested

    focus = [item for item in DEFAULT_FOCUS_SOURCES if item["source_id"] in sources]
    if focus:
        return list(focus)

    # 临时资料库或未来没有固定样本时仍应能生成一个可打开的入口。
    fallback: list[dict[str, str]] = []
    for source in sorted(
        sources.values(), key=lambda item: (str(item.get("profile")), str(item.get("title")), str(item.get("id")))
    )[:4]:
        source_id = source.get("id")
        if isinstance(source_id, str):
            fallback.append({"source_id": source_id, "reason": "自动选取的可复核来源。"})
    return fallback


def build_review_dashboard(
    library_root: Path | str = LIBRARY_ROOT, *, source_ids: Iterable[str] | None = None
) -> dict[str, Any]:
    """构造人工复核入口的数据，不写入文件。"""
    root = safe_library_root(library_root)
    sources = _load_sources(root)
    selected: list[dict[str, Any]] = []
    warnings: list[str] = []

    for request in _focus_requests(sources, source_ids):
        source_id = request["source_id"]
        source = sources.get(source_id)
        if source is None:
            warnings.append(f"指定来源不在清单中：{source_id}")
            continue
        relative_source_path = source.get("relative_path")
        try:
            source_path = safe_source_path(root, str(relative_source_path))
        except (PipelineError, OSError, ValueError) as error:
            warnings.append(f"{source_id} 的原始 Word 无法安全定位：{error}")
            source_path = None

        document_path, document = _load_document(root, source_id)
        content_path = None
        content_line_count = None
        if document is None:
            warnings.append(f"{source_id} 缺少可用的 document 记录")
        else:
            content_path = _safe_library_file(root, document.get("content_path"))
            if content_path is None:
                warnings.append(f"{source_id} 的转换后 Markdown 不可用")
            else:
                try:
                    content_line_count = len(content_path.read_text(encoding="utf-8").splitlines())
                except (OSError, UnicodeDecodeError):
                    warnings.append(f"{source_id} 的转换后 Markdown 无法读取")
                    content_path = None

        question_rows: list[dict[str, Any]] = []
        for question_path, question in _load_questions(root, source_id):
            location = question.get("source_location")
            locator = location.get("locator") if isinstance(location, dict) else None
            card_relative_path = _question_card_relative_path(source_id, question.get("id"))
            card_path = _output_path(root, card_relative_path) if card_relative_path else None
            if card_relative_path is None:
                warnings.append(f"{source_id} 的题目记录 ID 不符合题目卡命名规则：{question.get('id')!r}")

            figures: list[Path] = []
            invalid_figures: list[str] = []
            for figure in _list_strings(question.get("figures")):
                figure_path = _safe_library_file(root, figure)
                if figure_path is None:
                    invalid_figures.append(figure)
                else:
                    figures.append(figure_path)
            question_rows.append(
                {
                    "id": question["id"],
                    "label": str(question.get("label") or question["id"]),
                    "path": question_path,
                    "card_relative_path": card_relative_path,
                    "card_path": card_path,
                    "locator": str(locator or "未提供行号"),
                    "line": _line_from_locator(locator),
                    "summary": _question_summary(question),
                    "issues": _review_issues(question.get("issues")),
                    "record": question,
                    "figures": figures,
                    "invalid_figures": invalid_figures,
                }
            )

        structure_log = _safe_library_file(
            root, f"reports/structure/{source_short_for(source_id)}.json"
        )
        selected.append(
            {
                "source": source,
                "library_root": root,
                "reason": request["reason"],
                "source_path": source_path,
                "document_path": document_path,
                "document": document,
                "content_path": content_path,
                "content_relative_path": document.get("content_path") if document else None,
                "content_line_count": content_line_count,
                "structure_log": structure_log,
                "document_issues": _review_issues(document.get("issues")) if document else [],
                "question_rows": question_rows,
            }
        )

    return {
        "dashboard_version": DASHBOARD_VERSION,
        "scope": "read-only-human-review-entry",
        "sources": selected,
        "warnings": warnings,
    }


def _markdown_link(label: str, path: Path | None, *, line: int | None = None) -> str:
    if path is None:
        return "（文件缺失）"
    target = str(path)
    if line is not None:
        target = f"{target}:{line}"
    # 绝对路径使页面无论从 Finder、编辑器还是 Codex 中打开都可以直接跳转；
    # 尖括号处理中文路径中的空格和括号。
    return f"[{label}](<{target}>)"


def _markdown_code(value: object) -> str:
    return "`" + str(value).replace("`", "\\`") + "`"


def _display(value: object) -> str:
    if value is None:
        return "（未提供）"
    text = str(value).strip()
    return text if text else "（未提供）"


def _escape_table(value: object) -> str:
    return _display(value).replace("|", "\\|").replace("\n", " ").strip()


def _issue_lines(issues: list[str], *, limit: int = 8) -> list[str]:
    if not issues:
        return ["- 当前没有单独列出的自动提醒；仍需人工对照原 Word。"]
    lines = [f"- {issue}" for issue in issues[:limit]]
    if len(issues) > limit:
        lines.append(f"- 其余 {len(issues) - limit} 项已折叠；请先处理以上项目。")
    return lines


def _content_or_placeholder(value: object, placeholder: str = "（未提取到）") -> str:
    if value is None:
        return placeholder
    text = str(value).strip()
    return text if text else placeholder


def _inline_formula(value: str) -> str:
    """把公式字段作为行内数学显示；原始题干/解析文本保持不改。"""
    escaped = value.replace("$", "\\$")
    return f"${escaped}$"


def _embedded_asset_path(item: dict[str, Any], reference: str) -> Path | None:
    """将正文中的相对图片引用安全地改成资料库内的绝对路径。"""
    if re.match(r"^(?:[a-z]+:|/)", reference, re.IGNORECASE):
        return None
    content_relative_path = item.get("content_relative_path")
    root = item.get("library_root")
    if not isinstance(content_relative_path, str) or not isinstance(root, Path):
        return None
    candidate = PurePosixPath(
        posixpath.normpath(str(PurePosixPath(content_relative_path).parent / reference))
    ).as_posix()
    return _safe_library_file(root, candidate)


def _card_content(value: object, item: dict[str, Any], placeholder: str = "（未提取到）") -> str:
    """保留提取文本，同时让其中的本地图片在题目卡的位置仍可打开。"""
    text = _content_or_placeholder(value, placeholder)
    if text == placeholder:
        return text

    def replace_html(match: re.Match[str]) -> str:
        asset_path = _embedded_asset_path(item, match.group("path"))
        if asset_path is None:
            return match.group(0)
        return f"{match.group('prefix')}{asset_path}{match.group('suffix')}"

    def replace_markdown(match: re.Match[str]) -> str:
        asset_path = _embedded_asset_path(item, match.group("path"))
        if asset_path is None:
            return match.group(0)
        return f"{match.group('prefix')}{asset_path}{match.group('suffix')}"

    text = HTML_IMAGE_SOURCE_RE.sub(replace_html, text)
    return MARKDOWN_IMAGE_SOURCE_RE.sub(replace_markdown, text)


def render_question_card(item: dict[str, Any], question: dict[str, Any]) -> str:
    """将一道已提取题目呈现成供人工直接阅读的只读对照卡。"""
    source = item["source"]
    record = question["record"]
    title = str(source.get("title") or source.get("id"))
    label = str(question["label"])
    options = _list_strings(record.get("options"))
    formulas = _list_strings(record.get("formula_latex"))
    question_issues = question["issues"]
    document_issues = item["document_issues"]

    lines = [
        f"# {title} · {label}",
        "",
        "这是一张只读题目对照卡。请以原始 Word 为准，核对本页提取内容和转换后正文是否属于同一道题。",
        "",
        "## 快速跳转",
        "",
        f"- {_markdown_link('打开原始 Word（只读）', item['source_path'])}",
        f"- {_markdown_link(question['locator'], item['content_path'], line=question['line'])}",
        f"- {_markdown_link('打开完整转换后正文', item['content_path'])}",
        f"- {_markdown_link('打开原始 JSON 记录（可选）', question['path'])}",
        "",
        "## 自动识别信息",
        "",
        f"- 题型：{_display(record.get('question_type'))}",
        f"- 提取置信度：{_display(record.get('extraction_confidence'))}",
        f"- 题目 ID：{_markdown_code(question['id'])}",
        f"- 来源 ID：{_markdown_code(source.get('id', '（缺失）'))}",
        "",
        "## 题干",
        "",
        _card_content(record.get("stem"), item),
        "",
        "## 选项",
        "",
    ]
    if options:
        lines.extend(f"- {option}" for option in options)
    else:
        lines.append("- （本题未提取为选择题选项，或选项需对照题图/原 Word。）")

    lines.extend(
        [
            "",
            "## 答案",
            "",
            _content_or_placeholder(record.get("answer"), "（未提取到答案，需人工核对。）"),
            "",
            "## 解析",
            "",
            _card_content(record.get("solution"), item, "（未提取到解析，需人工核对。）"),
            "",
            "## 公式",
            "",
        ]
    )
    if formulas:
        lines.extend(f"- {_inline_formula(formula)}" for formula in formulas)
    else:
        lines.append("- （未单独提取公式。）")

    lines.extend(["", "## 配图", ""])
    if question["figures"]:
        for number, figure_path in enumerate(question["figures"], start=1):
            lines.extend(
                [
                    f"### 配图 {number}",
                    "",
                    f"- {_markdown_link('打开原图', figure_path)}",
                    f"![配图 {number}]({figure_path})",
                    "",
                ]
            )
    else:
        lines.append("- （本题没有已关联的配图。）")
    if question["invalid_figures"]:
        lines.extend(
            [
                "",
                "以下配图路径无法安全打开，需以原始 Word 核对：",
            ]
        )
        lines.extend(f"- {_markdown_code(path)}" for path in question["invalid_figures"])

    lines.extend(["", "## 自动提醒", ""])
    if question_issues:
        lines.extend(f"- 本题：{issue}" for issue in question_issues)
    else:
        lines.append("- 本题没有单独列出的自动提醒；仍需和原始 Word 对照。")
    if document_issues:
        lines.extend(f"- 同一份资料：{issue}" for issue in document_issues)

    lines.extend(
        [
            "",
            "## 来源定位",
            "",
            f"- 原始来源登记路径：{_markdown_code(record.get('source_location', {}).get('relative_path', '（未提供）') if isinstance(record.get('source_location'), dict) else '（未提供）')}",
            f"- 转换后正文定位：{_display(question['locator'])}",
            "",
            "核对后，如有问题，请记录“资料名 + 题号 + 正文行号 + 问题现象”。",
        ]
    )
    return "\n".join(lines) + "\n"


def render_review_dashboard(dashboard: dict[str, Any]) -> str:
    """把复核入口渲染为可在本地直接打开的 Markdown。"""
    lines = [
        "# 步步高人工复核入口",
        "",
        "这是一张只读对照页：点开同一份资料的 **原始 Word**、**转换后正文** 和 **可读题目卡**，核对内容是否一致。题目卡直接展示题干、选项、答案、解析、公式和配图；JSON 只保留给需要查看原始记录时使用。打开或阅读本页不会改变任何资料的复核状态。",
        "",
        "## 你现在要核对什么",
        "",
        "1. **正文呈现**：段落是否串段；公式是否应该行内却被拆成大块；图片、表格是否与原 Word 对应。",
        "2. **每道题**：题干、选项、答案、解析、公式和配图是否来自同一题，题号和边界是否正确。",
        "3. **没有自动拆成题的编号区块**：若页面列出具体行号，打开转换后正文到该行，判断它是否本应是一道题。",
        "",
        "不需要一次审完全部资料。先完成下面的四份代表资料；发现问题时，直接把“资料名 + 题号/行号 + 问题”告诉我即可。",
        "",
        "## 复核优先入口",
    ]

    for number, item in enumerate(dashboard["sources"], start=1):
        source = item["source"]
        metadata = source.get("metadata") if isinstance(source.get("metadata"), dict) else {}
        document = item["document"]
        title = str(source.get("title") or source.get("id"))
        lines.extend(
            [
                "",
                f"### {number}. {title}",
                "",
                f"- 为什么先看：{item['reason']}",
                f"- 来源 ID：{_markdown_code(source.get('id', '（缺失）'))}",
                f"- 资料类型：{_escape_table(source.get('profile', '（缺失）'))}；章节：{_escape_table(metadata.get('chapter'))}；课时：{_escape_table(metadata.get('lesson_no'))}",
                f"- {_markdown_link('打开原始 Word（只读）', item['source_path'])}",
                f"- {_markdown_link('打开转换后正文', item['content_path'])}",
                f"- {_markdown_link('打开文档状态卡', item['document_path'])}",
                f"- {_markdown_link('打开自动结构化检查记录', item['structure_log'])}",
            ]
        )
        if item["content_line_count"] is not None:
            lines.append(f"- 转换后正文行数：{item['content_line_count']} 行；已识别题目：{len(item['question_rows'])} 道。")
        elif document is None:
            lines.append("- ⚠️ 缺少文档状态卡，先不要做通过结论。")
        lines.extend(["", "#### 这一份资料的自动提醒", ""])
        lines.extend(_issue_lines(item["document_issues"]))

        lines.extend(
            [
                "",
                "#### 逐题跳转",
                "",
                "| 题目 | 转换后正文定位 | 可读题目卡 | JSON 记录（可选） | 本题自动提醒 |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        if not item["question_rows"]:
            lines.append("| （未识别题目） | 请打开转换后正文 | （无） | （无） | 需要人工判断是否应拆题 |")
        else:
            for question in item["question_rows"]:
                source_link = _markdown_link(
                    question["locator"], item["content_path"], line=question["line"]
                )
                question_link = _markdown_link("打开题目卡", question["card_path"])
                json_link = _markdown_link("JSON 记录", question["path"])
                issue_text = "；".join(question["issues"][:2]) or question["summary"]
                if len(question["issues"]) > 2:
                    issue_text += f"；另有 {len(question['issues']) - 2} 项"
                lines.append(
                    "| {label} | {source_link} | {question_link} | {json_link} | {issue_text} |".format(
                        label=_escape_table(question["label"]),
                        source_link=source_link,
                        question_link=question_link,
                        json_link=json_link,
                        issue_text=_escape_table(issue_text),
                    )
                )

    warnings = dashboard.get("warnings")
    if isinstance(warnings, list) and warnings:
        lines.extend(["", "## 需要先修复的入口问题", ""])
        lines.extend(f"- ⚠️ {warning}" for warning in warnings)

    lines.extend(
        [
            "",
            "## 追溯规则",
            "",
            "每一张题目卡都有固定题目 ID、来源 ID、来源 Word 路径和正文行号；因此任何一道已识别题目都能反查到它来自哪一份 Word。卡内已列出提取的公式和配图；如需查看机器原始记录，再打开表中的 JSON 链接。",
            "",
            "## 状态说明",
            "",
            "本页出现的“自动提醒”是待核对项，不是“转换失败”的同义词；只有把原始 Word 和转换结果逐项对照后，才能决定是否通过。",
        ]
    )
    return "\n".join(lines) + "\n"


def write_review_dashboard(
    library_root: Path | str = LIBRARY_ROOT, *, source_ids: Iterable[str] | None = None
) -> dict[str, Any]:
    """安全写入用户可直接打开的复核入口。"""
    root = safe_library_root(library_root)
    dashboard = build_review_dashboard(root, source_ids=source_ids)
    question_card_count = 0
    for item in dashboard["sources"]:
        for question in item["question_rows"]:
            card_relative_path = question["card_relative_path"]
            if card_relative_path is None:
                continue
            write_text(root, card_relative_path, render_question_card(item, question))
            question_card_count += 1
    write_text(root, DASHBOARD_PATH, render_review_dashboard(dashboard))
    return {
        "path": DASHBOARD_PATH,
        "source_count": len(dashboard["sources"]),
        "question_card_count": question_card_count,
        "warnings": dashboard["warnings"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成可直接点击的步步高人工复核入口")
    parser.add_argument(
        "--source-id",
        action="append",
        help="可重复指定；只为这些来源生成入口。省略时生成固定代表样本入口。",
    )
    args = parser.parse_args(argv)
    try:
        result = write_review_dashboard(official_library_root(), source_ids=args.source_id)
    except (OSError, PipelineError, ReviewDashboardError, ValueError) as error:
        print(f"人工复核入口生成失败：{error}", file=sys.stderr)
        return 1
    print(
        f"已写入 {result['path']}（{result['source_count']} 份来源，"
        f"{result['question_card_count']} 张可读题目卡）"
    )
    for warning in result["warnings"]:
        print(f"警告：{warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
