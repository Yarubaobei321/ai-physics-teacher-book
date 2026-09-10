#!/usr/bin/env python3
"""将已登记的 Word 来源安全转换为正式资料库 Markdown。

输入只来自 ``sources/sources.jsonl`` 登记的 ``raw/`` 路径。输出只写入正式资料库
的 documents、assets 与 reports；不会移动、复制回写或覆盖任何原始 Word 文件。
"""

from __future__ import annotations

import argparse
import os
import posixpath
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from library_common import (  # noqa: E402
    LIBRARY_ROOT,
    PROFILES,
    PipelineError,
    document_id_for,
    is_safe_relative_path,
    json_bytes,
    markdown_relative_path,
    official_library_root,
    read_json,
    safe_library_root,
    safe_output_path,
    safe_source_path,
    sanitise_log_text,
    sha256_file,
    source_short_for,
    write_bytes,
    write_json,
    write_text,
)


WORKTREE_ROOT = LIBRARY_ROOT.parents[2]
ANYDOC_BINARY = WORKTREE_ROOT / "node_modules" / ".bin" / "anydoc"
PANDOC_BINARY = Path("/opt/homebrew/bin/pandoc")
SIPS_BINARY = Path("/usr/bin/sips")
MARKDOWN_IMAGE_RE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\((?:<(?P<angle>[^>]+)>|(?P<plain>[^\s)]+))(?P<title>\s+[^)]*)?\)"
)
HTML_SOURCE_RE = re.compile(r"(?P<prefix>\bsrc\s*=\s*[\"'])(?P<target>[^\"']+)(?P<suffix>[\"'])", re.IGNORECASE)
MARKDOWN_TABLE_RE = re.compile(r"(?m)^\s*\|.+\|\s*$")
INLINE_MATH_RE = re.compile(r"(?<!\\)\$(?!\$)([^\n$]+?)(?<!\\)\$(?!\$)")
DISPLAY_MATH_RE = re.compile(r"\$\$(.+?)\$\$|\\\[(.+?)\\\]", re.DOTALL)
MATH_FENCE_OPEN_RE = re.compile(r"^ {0,3}```[ \t]*math[ \t]*$")
MATH_FENCE_CLOSE_RE = re.compile(r"^ {0,3}```[ \t]*$")
INLINE_MATH_CONTEXT_RE = re.compile(
    r"^(?:#{1,6}\s|[-*+]\s|\d+[.)]\s|[A-Da-d][．.、]\s*|>|<|!\[|<img\b|```|\$\$|\||【)"
)
NON_INLINE_MATH_OPERATOR_RE = re.compile(
    r"(?:[=<>+*/|]|(?<![A-Za-z])-|[,;，；]|\\\\|"
    r"\\(?:frac|dfrac|tfrac|sqrt|sum|prod|int|lim|left|right|begin|end|"
    r"over|choose|to|rightarrow|mapsto|le|ge|neq|approx|sim|times|cdot|div|pm|mp|quad|qquad))"
)
INLINE_MATH_ALLOWED_RE = re.compile(r"^[A-Za-z0-9_{}^\\()\[\]\s'.\u0370-\u03ff\u4e00-\u9fff]+$")
ANYDOC_IMAGE_PLACEHOLDER_RE = re.compile(r"(?m)^@@@[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\s*$", re.IGNORECASE)
FORMULA_LABEL_RE = re.compile(r"(?:公式|表达式|方程|解得|由.*(?:定律|关系))\s*[:：]\s*(?:\n|$|[。．])")
UNRESOLVED_ASSET_ANCHOR_ISSUE = "文档含提取图片，但 Markdown 未保留可靠图像位置锚点；图像位置未可靠关联"
ANYDOC_PLACEHOLDER_ISSUE_FRAGMENT = "Anydoc 图像占位符"
FORMULA_LOSS_ISSUE_FRAGMENT = "公式是否丢失"

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


def _run_command(command: list[str], *, command_runner: CommandRunner | None) -> subprocess.CompletedProcess[str]:
    if command_runner is not None:
        result = command_runner(command, cwd=str(LIBRARY_ROOT))
        if not isinstance(result, subprocess.CompletedProcess):
            raise PipelineError("测试或调用方提供的 command_runner 必须返回 subprocess.CompletedProcess")
        return result
    return subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def _tool_version(
    command: list[str], *, command_runner: CommandRunner | None, library_root: Path, source_path: Path
) -> str:
    try:
        result = _run_command([*command, "--version"], command_runner=command_runner)
    except (OSError, PipelineError) as error:
        return f"unavailable: {sanitise_log_text(error, library_root, source_path)}"
    output = (result.stdout or result.stderr or "").strip().splitlines()
    if result.returncode == 0 and output:
        return sanitise_log_text(output[0], library_root, source_path)
    return f"unavailable (exit {result.returncode})"


def _safe_media_name(member_name: str, used_names: set[str]) -> str | None:
    member = PurePosixPath(member_name)
    if len(member.parts) != 3 or member.parts[:2] != ("word", "media") or ".." in member.parts:
        return None
    name = member.name
    if not name or name in {".", ".."} or "\\" in name:
        return None
    if name not in used_names:
        used_names.add(name)
        return name
    stem = PurePosixPath(name).stem
    suffix = PurePosixPath(name).suffix
    number = 2
    while f"{stem}-{number}{suffix}" in used_names:
        number += 1
    unique_name = f"{stem}-{number}{suffix}"
    used_names.add(unique_name)
    return unique_name


def _extract_docx_media(
    library_root: Path,
    source_id: str,
    source_path: Path,
    *,
    command_runner: CommandRunner | None,
) -> tuple[list[str], dict[str, str], list[str], list[dict[str, object]]]:
    """从 OOXML 包复制媒体到正式 assets，并将 TIFF 派生为 PNG。"""
    asset_paths: list[str] = []
    media_mapping: dict[str, str] = {}
    issues: list[str] = []
    attempts: list[dict[str, object]] = []
    used_names: set[str] = set()
    try:
        archive = zipfile.ZipFile(source_path)
    except (OSError, zipfile.BadZipFile) as error:
        return asset_paths, media_mapping, [f"无法读取 docx 内嵌媒体：{error}"], attempts
    with archive:
        for info in archive.infolist():
            asset_name = _safe_media_name(info.filename, used_names)
            if asset_name is None:
                continue
            original_relative = f"assets/original/{source_id}/{asset_name}"
            try:
                write_bytes(library_root, original_relative, archive.read(info))
            except (KeyError, OSError, PipelineError) as error:
                issues.append(f"提取媒体 {asset_name} 失败：{sanitise_log_text(error, library_root, source_path)}")
                continue
            asset_paths.append(original_relative)
            media_mapping[asset_name] = original_relative
            media_mapping[f"media/{asset_name}"] = original_relative
            media_mapping[f"word/media/{asset_name}"] = original_relative
            media_mapping[f"images/{asset_name}"] = original_relative
            suffix = PurePosixPath(asset_name).suffix.lower()
            if suffix not in {".tif", ".tiff"}:
                continue
            derived_name = f"{PurePosixPath(asset_name).stem}.png"
            derived_relative = f"assets/derived/{source_id}/{derived_name}"
            try:
                derived_path = safe_output_path(library_root, derived_relative)
                original_path = safe_output_path(library_root, original_relative, create_parent=False)
                result = _run_command(
                    [str(SIPS_BINARY), "-s", "format", "png", str(original_path), "--out", str(derived_path)],
                    command_runner=command_runner,
                )
                attempts.append(
                    {
                        "tool": "sips",
                        "returncode": result.returncode,
                        "stdout": sanitise_log_text(result.stdout, library_root, source_path),
                        "stderr": sanitise_log_text(result.stderr, library_root, source_path),
                    }
                )
                if result.returncode != 0 or not derived_path.is_file():
                    issues.append(f"TIFF 媒体 {asset_name} 未能生成 PNG 派生文件，需人工复核")
                    continue
                asset_paths.append(derived_relative)
                for key in (asset_name, f"media/{asset_name}", f"word/media/{asset_name}", f"images/{asset_name}"):
                    media_mapping[key] = derived_relative
            except (OSError, PipelineError) as error:
                issues.append(f"TIFF 媒体 {asset_name} 生成 PNG 失败：{sanitise_log_text(error, library_root, source_path)}")
    return asset_paths, media_mapping, issues, attempts


def _normalise_media_key(value: str) -> str:
    value = value.strip().replace("\\", "/")
    value = value.split("#", 1)[0].split("?", 1)[0]
    while value.startswith("./"):
        value = value[2:]
    return value


def _media_reference_candidates(value: str) -> list[str]:
    """给出转换器输出媒体链接可能对应的 OOXML 媒体键。

    Pandoc 可能写绝对临时路径、``media/image1.png`` 或仅文件名。映射表本身仍只
    来自该 Word 的 ``word/media/``，因此这里仅做键归一化，不接受任意外部路径。
    """
    key = _normalise_media_key(value)
    name = PurePosixPath(key).name
    candidates = [key]
    if name and name not in candidates:
        candidates.append(name)
    for prefix in ("media/", "word/media/", "images/"):
        candidate = f"{prefix}{name}" if name else ""
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _rewrite_asset_links(markdown: str, markdown_relative: str, mapping: dict[str, str]) -> str:
    """把转换器的临时媒体链接统一改写为相对于 records/documents 的正式资产链接。"""
    def resolved(target: str) -> str | None:
        asset_relative = next((mapping[key] for key in _media_reference_candidates(target) if key in mapping), None)
        if asset_relative is None:
            return None
        return markdown_relative_path(markdown_relative, asset_relative)

    def replace_markdown(match: re.Match[str]) -> str:
        target = match.group("angle") or match.group("plain") or ""
        replacement = resolved(target)
        if replacement is None:
            return match.group(0)
        return f"![{match.group('alt')}]({replacement}{match.group('title') or ''})"

    def replace_html(match: re.Match[str]) -> str:
        replacement = resolved(match.group("target"))
        if replacement is None:
            return match.group(0)
        return f"{match.group('prefix')}{replacement}{match.group('suffix')}"

    return HTML_SOURCE_RE.sub(replace_html, MARKDOWN_IMAGE_RE.sub(replace_markdown, markdown))


def _referenced_asset_paths(markdown: str, markdown_relative: str) -> list[str]:
    """返回 Markdown 内可安全解析到正式 assets 的就地图片链接。"""
    if not is_safe_relative_path(markdown_relative):
        return []
    parent = PurePosixPath(markdown_relative).parent.as_posix()
    referenced: list[str] = []
    for match in list(MARKDOWN_IMAGE_RE.finditer(markdown)) + list(HTML_SOURCE_RE.finditer(markdown)):
        target = match.groupdict().get("angle") or match.groupdict().get("plain") or match.groupdict().get("target") or ""
        target = _normalise_media_key(target)
        candidate = posixpath.normpath(posixpath.join(parent, target))
        if is_safe_relative_path(candidate) and candidate.startswith("assets/") and candidate not in referenced:
            referenced.append(candidate)
    return referenced


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


def _is_plain_inline_math_context(line: str) -> bool:
    """判断相邻行是否可与短公式组成同一自然语言句子。

    Pandoc 偶尔会将 Word 中的独立公式 run 输出为三行 ````` math```` 围栏，哪怕
    它在原文只是“分别为 F_M 和 F_N”中的一个符号。这里只接受普通文本行；标题、
    选项、引用、图像、表格等结构性行均不参与合并，避免破坏题目结构。
    """
    stripped = line.strip()
    return bool(stripped) and not INLINE_MATH_CONTEXT_RE.match(stripped)


def _is_simple_inline_math(formula: str) -> bool:
    """只将单个符号或带上下标的短表达式视为可内联。

    等式、不等式、运算、分式、求和、积分以及任何多行公式都保留为展示公式。
    这是一条宁可少合并、也不把真正推导式压进句内的保守规则。
    """
    candidate = formula.strip()
    return bool(
        candidate
        and len(candidate) <= 80
        and INLINE_MATH_ALLOWED_RE.fullmatch(candidate)
        and not NON_INLINE_MATH_OPERATOR_RE.search(candidate)
    )


def _normalise_inline_math_blocks(markdown: str) -> str:
    """将句子中被 Pandoc 错拆的短 ``math`` 围栏还原为行内公式。

    仅处理无空行分隔、前后均为普通文本、且内容是单行简单符号的三行围栏。真正的
    独立公式或多行公式会原样保留为 ``math`` 围栏。
    """
    if "```" not in markdown:
        return markdown
    line_ending = "\r\n" if "\r\n" in markdown else "\n"
    has_final_newline = markdown.endswith(("\n", "\r"))
    lines = markdown.splitlines()
    normalised: list[str] = []
    index = 0
    while index < len(lines):
        if (
            index + 3 < len(lines)
            and normalised
            and MATH_FENCE_OPEN_RE.fullmatch(lines[index])
            and MATH_FENCE_CLOSE_RE.fullmatch(lines[index + 2])
        ):
            formula = lines[index + 1].strip()
            previous = normalised[-1]
            following = lines[index + 3]
            if (
                _is_simple_inline_math(formula)
                and _is_plain_inline_math_context(previous)
                and _is_plain_inline_math_context(following)
            ):
                left = previous.rstrip()
                right = following.lstrip()
                # 中文原句通常不留空格；英文单词与公式相邻时补一个空格，避免把
                # ``is$F$and`` 显示成连写。
                before = " " if left and left[-1].isascii() and left[-1].isalnum() else ""
                after = " " if right and right[0].isascii() and right[0].isalnum() else ""
                normalised[-1] = f"{left}{before}${formula}${after}{right}"
                index += 4
                continue
        normalised.append(lines[index])
        index += 1
    result = line_ending.join(normalised)
    return result + (line_ending if has_final_newline else "")


def _docx_media_count(source_path: Path) -> int:
    """只读统计 Word 内嵌媒体数，用于决定是否需要质量回退。"""
    try:
        with zipfile.ZipFile(source_path) as archive:
            return sum(1 for info in archive.infolist() if _safe_media_name(info.filename, set()) is not None)
    except (OSError, zipfile.BadZipFile):
        return 0


def _markdown_media_reference_count(markdown: str) -> int:
    """统计 Markdown 中的图像锚点数（同一图重复出现也按位置计数）。"""
    return len(MARKDOWN_IMAGE_RE.findall(markdown)) + len(HTML_SOURCE_RE.findall(markdown))


def _markdown_has_media_reference(markdown: str) -> bool:
    return _markdown_media_reference_count(markdown) > 0


def _needs_quality_fallback(markdown: str, *, source_media_count: int, formula_object_count: int) -> bool:
    """判断 Anydoc 成功后是否仍应尝试 Pandoc 进行质量对比。

    成功退出码不等于资料可追溯：有媒体却没有任何 Markdown 图像锚点、出现 Anydoc
    占位符，或原 Word 有公式对象但没有可识别公式时，都需要取得 Pandoc 候选进行
    比较。若 Pandoc 没有带来更多可验证信息，后续选择器仍保留 Anydoc 结果。
    """
    return (
        # 一个图片锚点不足以证明整份文档的媒体位置可追溯。Word 中的同一媒体可能被
        # 重复使用，因而这里的比较是保守触发条件而非完整性断言：少于原始媒体数量时
        # 取得 Pandoc 候选，再由选择器决定是否替换。
        (source_media_count > _markdown_media_reference_count(markdown))
        or bool(ANYDOC_IMAGE_PLACEHOLDER_RE.search(markdown))
        # 只保留了部分公式同样不能视为可发布；Pandoc 候选可能恢复更多可见公式，若
        # 没有改善，后续选择器仍会保留 Anydoc 并把数量不一致列入人工复核。
        or formula_object_count > len(_extract_formulas(markdown))
    )


def _docx_formula_object_count(source_path: Path) -> int:
    """统计 Word 公式对象，用于发现转换器将公式静默丢失的情形。

    Word 文档中的公式既可能是 OMML ``m:oMath``，也可能是旧式 EQ 域。后者通常被
    Anydoc 转成空白，因而不能只数 OMML；这里仅把它纳入审计计数，绝不尝试从域代码
    猜测或还原 LaTeX。
    """
    try:
        with zipfile.ZipFile(source_path) as archive:
            document_xml = archive.read("word/document.xml")
    except (KeyError, OSError, zipfile.BadZipFile):
        return 0
    omml_count = document_xml.count(b"<m:oMath")
    try:
        document_text = document_xml.decode("utf-8", errors="ignore")
    except UnicodeError:
        return omml_count
    # EQ 域的指令可能被拆成多个 w:instrText 片段，故匹配文本内容中的 ``eq \\``。
    eq_field_count = len(re.findall(r"(?i)(?<![A-Za-z])eq\s+\\", document_text))
    return omml_count + eq_field_count


def _docx_math_count(source_path: Path) -> int:
    """兼容旧内部调用；返回 OMML 和 EQ 域公式对象总数。"""
    return _docx_formula_object_count(source_path)


def _suspected_formula_loss(markdown: str, docx_math_count: int, formula_count: int) -> bool:
    """以保守信号标出可能丢失的公式；不试图凭空恢复公式。"""
    # 当原 Word 中的公式对象数多于 Markdown 可见公式数时，也必须进入复核队列。
    # 一个对象不一定对应一个独立 LaTeX 片段，但这里宁可多复核，不能静默发布残缺公式。
    if docx_math_count > formula_count:
        return True
    return bool(FORMULA_LABEL_RE.search(markdown)) and formula_count == 0


def _document_record(
    source: dict[str, Any], document_id: str, markdown_relative: str, document_relative: str,
    asset_paths: list[str], status: str, issues: list[str]
) -> dict[str, Any]:
    return {
        "id": document_id,
        "source_id": source["id"],
        "relative_path": document_relative,
        "source_relative_path": source["relative_path"],
        "content_path": markdown_relative,
        "title": source["title"],
        "status": status,
        "extraction_profile": source["profile"],
        "asset_paths": asset_paths,
        "issues": issues,
    }


def _conversion_paths(source_id: str) -> tuple[str, str, str, str]:
    source_short = source_short_for(source_id)
    document_id = document_id_for(source_id)
    return (
        document_id,
        f"records/documents/{document_id}.md",
        f"records/documents/{document_id}.json",
        f"reports/conversion/{source_short}.json",
    )


def _is_source_asset_path(relative_path: object, source_id: str) -> bool:
    """只接受此来源自己的 original / derived 资产声明。"""
    return isinstance(relative_path, str) and (
        relative_path.startswith(f"assets/original/{source_id}/")
        or relative_path.startswith(f"assets/derived/{source_id}/")
    )


def _nonnegative_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _contains_issue(value: object, fragment: str) -> bool:
    return isinstance(value, list) and any(
        isinstance(item, str) and fragment in item for item in value
    )


def conversion_is_current(library_root: Path | str, source: dict[str, Any]) -> bool:
    """仅在输入、资产、Markdown 审计信号都未变化时跳过转换。

    这不是单纯的“文件还在”检查：图片锚点、Anydoc 占位符和 Word OMML 公式审计
    信号也要与成功日志一致。否则人工改过 Markdown 或旧版本日志缺字段时，会重新
    转换并重新进入人工复核，而不是把失真的结果当作可安全续跑。
    """
    try:
        root = safe_library_root(library_root)
        source_id = str(source["id"])
        _, markdown_relative, document_relative, log_relative = _conversion_paths(source_id)
        document = read_json(safe_output_path(root, document_relative, create_parent=False))
        log = read_json(safe_output_path(root, log_relative, create_parent=False))
        source_path = safe_source_path(root, str(source["relative_path"]))
    except (KeyError, OSError, PipelineError, ValueError):
        return False
    if not document or not log or log.get("status") != "success":
        return False
    if log.get("input_sha256") != source.get("sha256") or document.get("source_id") != source_id:
        return False
    try:
        markdown_path = safe_output_path(root, markdown_relative, create_parent=False)
        asset_paths = document.get("asset_paths")
        logged_asset_paths = log.get("asset_paths")
        reliable_asset_paths = log.get("reliable_asset_paths")
        if (
            not isinstance(asset_paths, list)
            or not isinstance(logged_asset_paths, list)
            or not isinstance(reliable_asset_paths, list)
            or asset_paths != logged_asset_paths
        ):
            return False
        if any(not _is_source_asset_path(relative_path, source_id) for relative_path in asset_paths):
            return False
        if any(
            not _is_source_asset_path(relative_path, source_id)
            or relative_path not in asset_paths
            for relative_path in reliable_asset_paths
        ):
            return False
        for relative_path in [*asset_paths, *reliable_asset_paths]:
            asset_path = safe_output_path(root, relative_path, create_parent=False)
            if not asset_path.is_file() or asset_path.is_symlink():
                return False
        if not markdown_path.is_file() or markdown_path.is_symlink():
            return False
        if sha256_file(source_path) != source.get("sha256"):
            return False
        markdown = markdown_path.read_text(encoding="utf-8", errors="replace")
        actual_reliable_assets = _referenced_asset_paths(markdown, markdown_relative)
        if actual_reliable_assets != reliable_asset_paths:
            return False
        expected_anchor_status = (
            "not_applicable"
            if not asset_paths
            else ("reliable" if actual_reliable_assets else "unresolved")
        )
        if log.get("asset_anchor_status") != expected_anchor_status:
            return False
        if expected_anchor_status == "unresolved" and not (
            _contains_issue(document.get("issues"), UNRESOLVED_ASSET_ANCHOR_ISSUE)
            and _contains_issue(log.get("issues"), UNRESOLVED_ASSET_ANCHOR_ISSUE)
        ):
            return False

        actual_placeholder_count = len(ANYDOC_IMAGE_PLACEHOLDER_RE.findall(markdown))
        if log.get("anydoc_image_placeholder_count") != actual_placeholder_count:
            return False
        if actual_placeholder_count and not (
            _contains_issue(document.get("issues"), ANYDOC_PLACEHOLDER_ISSUE_FRAGMENT)
            and _contains_issue(log.get("issues"), ANYDOC_PLACEHOLDER_ISSUE_FRAGMENT)
        ):
            return False

        formula_count = len(_extract_formulas(markdown))
        docx_math_count = _docx_math_count(source_path)
        formula_loss_suspected = _suspected_formula_loss(markdown, docx_math_count, formula_count)
        if not (
            _nonnegative_integer(log.get("formula_count"))
            and _nonnegative_integer(log.get("docx_math_count"))
            and isinstance(log.get("formula_loss_suspected"), bool)
        ):
            return False
        if (
            log.get("formula_count") != formula_count
            or log.get("docx_math_count") != docx_math_count
            or log.get("formula_loss_suspected") != formula_loss_suspected
        ):
            return False
        if formula_loss_suspected and not (
            _contains_issue(document.get("issues"), FORMULA_LOSS_ISSUE_FRAGMENT)
            and _contains_issue(log.get("issues"), FORMULA_LOSS_ISSUE_FRAGMENT)
        ):
            return False
        return True
    except (OSError, PipelineError, UnicodeError, zipfile.BadZipFile):
        return False


def _validate_source(source: dict[str, Any]) -> None:
    required = {"id", "relative_path", "sha256", "profile", "title"}
    missing = sorted(required - source.keys())
    if missing:
        raise PipelineError(f"来源清单缺少字段：{', '.join(missing)}")
    source_id = source["id"]
    if not isinstance(source_id, str) or not re.fullmatch(r"src\.bbg\.[0-9a-f]{64}", source_id):
        raise PipelineError("来源 ID 格式无效")
    if not isinstance(source["relative_path"], str) or not is_safe_relative_path(source["relative_path"]):
        raise PipelineError("来源 relative_path 格式无效")
    if not isinstance(source["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", source["sha256"]):
        raise PipelineError("来源 sha256 格式无效")
    if source["profile"] not in PROFILES:
        raise PipelineError("来源 profile 无效")
    if not isinstance(source["title"], str) or not source["title"].strip():
        raise PipelineError("来源 title 不能为空")


def _write_conversion_log(library_root: Path, log_relative: str, log: dict[str, Any]) -> None:
    write_bytes(library_root, log_relative, json_bytes(log))


def convert_source(
    library_root: Path | str,
    source: dict[str, Any],
    *,
    force: bool = False,
    command_runner: CommandRunner | None = None,
) -> dict[str, Any]:
    """转换一个 source，并始终将成功/失败细节记入 ``reports/conversion/``。

    优先调用当前 worktree 的 Anydoc；Anydoc 不可用或失败时回退到固定路径 Pandoc。
    """
    root = safe_library_root(library_root)
    try:
        _validate_source(source)
        source_id = source["id"]
        document_id, markdown_relative, document_relative, log_relative = _conversion_paths(source_id)
    except (PipelineError, KeyError, ValueError) as error:
        return {"success": False, "skipped": False, "issues": [str(error)], "error": str(error)}
    if not force and conversion_is_current(root, source):
        return {
            "success": True,
            "skipped": True,
            "source_id": source_id,
            "document_id": document_id,
            "document_path": document_relative,
            "markdown_path": markdown_relative,
            "issues": [],
        }

    source_path: Path | None = None
    issues: list[str] = []
    attempts: list[dict[str, object]] = []
    tool_versions: dict[str, str] = {}
    asset_paths: list[str] = []
    try:
        source_path = safe_source_path(root, source["relative_path"])
        actual_sha256 = sha256_file(source_path)
        if actual_sha256 != source["sha256"]:
            raise PipelineError("原始 Word 内容哈希与 sources.jsonl 不一致，已停止转换")
        tool_versions["anydoc"] = _tool_version(
            [str(ANYDOC_BINARY)], command_runner=command_runner, library_root=root, source_path=source_path
        )
        tool_versions["pandoc"] = _tool_version(
            [str(PANDOC_BINARY)], command_runner=command_runner, library_root=root, source_path=source_path
        )
        markdown_destination = safe_output_path(root, markdown_relative)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".convert-", suffix=".md", dir=markdown_destination.parent)
        os.close(descriptor)
        temporary_markdown = Path(temporary_name)
        used_tool: str | None = None
        try:
            # 默认优先 Anydoc；只有发现图像/公式信息可能丢失时才额外调用 Pandoc，
            # 并按可追溯性选择更好的候选。这样避免对全库无差别地改换转换器。
            candidates: list[tuple[str, str]] = []
            for tool, command in (("anydoc", [str(ANYDOC_BINARY), str(source_path), "-o", str(temporary_markdown)]),):
                try:
                    result = _run_command(command, command_runner=command_runner)
                except (OSError, PipelineError) as error:
                    attempts.append(
                        {"tool": tool, "returncode": None, "stdout": "", "stderr": sanitise_log_text(error, root, source_path)}
                    )
                    continue
                attempts.append(
                    {
                        "tool": tool,
                        "returncode": result.returncode,
                        "stdout": sanitise_log_text(result.stdout, root, source_path),
                        "stderr": sanitise_log_text(result.stderr, root, source_path),
                    }
                )
                if result.returncode == 0 and temporary_markdown.is_file():
                    used_tool = tool
                    candidates.append((tool, temporary_markdown.read_text(encoding="utf-8", errors="replace")))
                    break
            if used_tool is None:
                # Anydoc 完全不可用时，仍保留既有的 Pandoc 回退路径。
                result = _run_command(
                    [str(PANDOC_BINARY), "--from=docx", "--to=gfm", "--wrap=none", "-o", str(temporary_markdown), str(source_path)],
                    command_runner=command_runner,
                )
                attempts.append(
                    {
                        "tool": "pandoc",
                        "returncode": result.returncode,
                        "stdout": sanitise_log_text(result.stdout, root, source_path),
                        "stderr": sanitise_log_text(result.stderr, root, source_path),
                    }
                )
                if result.returncode != 0 or not temporary_markdown.is_file():
                    raise PipelineError("Anydoc 与 Pandoc 均未能生成 Markdown")
                used_tool = "pandoc"
                candidates.append(("pandoc", temporary_markdown.read_text(encoding="utf-8", errors="replace")))

            formula_object_count = _docx_formula_object_count(source_path)
            if used_tool == "anydoc" and _needs_quality_fallback(
                candidates[0][1],
                source_media_count=_docx_media_count(source_path),
                formula_object_count=formula_object_count,
            ):
                with tempfile.TemporaryDirectory(prefix="bbg-pandoc-fallback-") as fallback_directory:
                    fallback_markdown = Path(fallback_directory) / "fallback.md"
                    result = _run_command(
                        [
                            str(PANDOC_BINARY), "--from=docx", "--to=gfm", "--wrap=none",
                            f"--extract-media={Path(fallback_directory) / 'media'}",
                            "-o", str(fallback_markdown), str(source_path),
                        ],
                        command_runner=command_runner,
                    )
                    attempts.append(
                        {
                            "tool": "pandoc_quality_fallback",
                            "returncode": result.returncode,
                            "stdout": sanitise_log_text(result.stdout, root, source_path),
                            "stderr": sanitise_log_text(result.stderr, root, source_path),
                        }
                    )
                    if result.returncode == 0 and fallback_markdown.is_file():
                        candidates.append(("pandoc", fallback_markdown.read_text(encoding="utf-8", errors="replace")))

            def quality(candidate: tuple[str, str]) -> tuple[int, int, int]:
                _, text = candidate
                # 可追溯图像位置优先，其次公式数量，最后偏好 Anydoc（避免无差异换工具）。
                return (
                    _markdown_media_reference_count(text),
                    len(_extract_formulas(text)),
                    int(candidate[0] == "anydoc"),
                )

            used_tool, markdown = max(candidates, key=quality)
        finally:
            if temporary_markdown.exists():
                temporary_markdown.unlink()

        asset_paths, media_mapping, media_issues, media_attempts = _extract_docx_media(
            root, source_id, source_path, command_runner=command_runner
        )
        attempts.extend(media_attempts)
        issues.extend(media_issues)
        markdown = _normalise_inline_math_blocks(markdown)
        markdown = _rewrite_asset_links(markdown, markdown_relative, media_mapping)
        reliable_asset_paths = _referenced_asset_paths(markdown, markdown_relative)
        formulas = _extract_formulas(markdown)
        docx_math_count = _docx_formula_object_count(source_path)
        image_placeholder_count = len(ANYDOC_IMAGE_PLACEHOLDER_RE.findall(markdown))
        formula_loss_suspected = _suspected_formula_loss(markdown, docx_math_count, len(formulas))
        has_table = bool(MARKDOWN_TABLE_RE.search(markdown) or "<table" in markdown.lower())
        has_figure = bool(asset_paths or MARKDOWN_IMAGE_RE.search(markdown) or HTML_SOURCE_RE.search(markdown))
        if used_tool != "anydoc":
            if any(
                isinstance(attempt, dict)
                and attempt.get("tool") == "anydoc"
                and attempt.get("returncode") == 0
                for attempt in attempts
            ):
                issues.append("Anydoc 结果缺少可靠图像或公式信息，已改用 Pandoc 候选；需要人工复核版式")
            else:
                issues.append("Anydoc 转换失败，已由 Pandoc 回退；需要人工复核版式")
        if formulas:
            issues.append("检测到公式，需人工核对公式转换")
        if has_table:
            issues.append("检测到表格，需人工核对表格结构")
        if has_figure:
            issues.append("检测到图像或图表，需人工核对图文对应关系")
        if asset_paths and not reliable_asset_paths:
            issues.append(UNRESOLVED_ASSET_ANCHOR_ISSUE)
        if image_placeholder_count:
            issues.append(
                f"检测到 {image_placeholder_count} 个 {ANYDOC_PLACEHOLDER_ISSUE_FRAGMENT}，无法安全映射到原始媒体；图像位置未可靠关联"
            )
        if formula_loss_suspected:
            issues.append(f"原始 Word 公式对象与 Markdown 公式数量不一致，需人工核对{FORMULA_LOSS_ISSUE_FRAGMENT}")
        status = "pending_manual_review" if issues else "raw_extracted"
        write_text(root, markdown_relative, markdown)
        document = _document_record(
            source, document_id, markdown_relative, document_relative, asset_paths, status, issues
        )
        write_json(root, document_relative, document)
        log = {
            "source_id": source_id,
            "source_relative_path": source["relative_path"],
            "input_sha256": source["sha256"],
            "status": "success",
            "tool": used_tool,
            "tool_versions": tool_versions,
            "fallback_used": any(
                isinstance(attempt, dict) and attempt.get("tool") == "pandoc_quality_fallback"
                for attempt in attempts
            ) or (used_tool == "pandoc" and not any(
                isinstance(attempt, dict) and attempt.get("tool") == "anydoc" and attempt.get("returncode") == 0
                for attempt in attempts
            )),
            "paths": {
                "markdown": markdown_relative,
                "document": document_relative,
                "conversion_log": log_relative,
            },
            "asset_paths": asset_paths,
            "reliable_asset_paths": reliable_asset_paths,
            "asset_anchor_status": (
                "not_applicable" if not asset_paths else ("reliable" if reliable_asset_paths else "unresolved")
            ),
            "formula_count": len(formulas),
            "docx_math_count": docx_math_count,
            "formula_loss_suspected": formula_loss_suspected,
            "anydoc_image_placeholder_count": image_placeholder_count,
            "table_detected": has_table,
            "figure_detected": has_figure,
            "attempts": attempts,
            "issues": issues,
        }
        _write_conversion_log(root, log_relative, log)
        return {
            "success": True,
            "skipped": False,
            "source_id": source_id,
            "document_id": document_id,
            "document_path": document_relative,
            "markdown_path": markdown_relative,
            "issues": issues,
        }
    except (OSError, PipelineError, UnicodeError, zipfile.BadZipFile) as error:
        message = sanitise_log_text(error, root, source_path)
        issues.append(message)
        document = _document_record(
            source, document_id, markdown_relative, document_relative, asset_paths, "blocked", issues
        )
        write_json(root, document_relative, document)
        log = {
            "source_id": source_id,
            "source_relative_path": source["relative_path"],
            "input_sha256": source["sha256"],
            "status": "failed",
            "tool": None,
            "tool_versions": tool_versions,
            "fallback_used": False,
            "paths": {
                "markdown": markdown_relative,
                "document": document_relative,
                "conversion_log": log_relative,
            },
            "asset_paths": asset_paths,
            "attempts": attempts,
            "issues": issues,
        }
        _write_conversion_log(root, log_relative, log)
        return {
            "success": False,
            "skipped": False,
            "source_id": source_id,
            "document_id": document_id,
            "document_path": document_relative,
            "markdown_path": markdown_relative,
            "issues": issues,
            "error": message,
        }


def _read_manifest(root: Path) -> list[dict[str, Any]]:
    manifest = root / "sources" / "sources.jsonl"
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            import json

            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise PipelineError(f"sources.jsonl 第 {line_number} 行无效：{error.msg}") from error
        if not isinstance(value, dict):
            raise PipelineError(f"sources.jsonl 第 {line_number} 行必须是对象")
        records.append(value)
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="转换 sources.jsonl 中登记的单个步步高 Word 来源")
    parser.add_argument("--source-id", required=True, help="要转换的 src.bbg.* 来源 ID")
    parser.add_argument("--force", action="store_true", help="即使输入 hash 未变化也重新转换")
    args = parser.parse_args(argv)
    try:
        root = official_library_root()
        source = next(record for record in _read_manifest(root) if record.get("id") == args.source_id)
    except (StopIteration, OSError, PipelineError) as error:
        print(f"转换准备失败：{error}", file=sys.stderr)
        return 1
    result = convert_source(root, source, force=args.force)
    print(json_bytes(result).decode("utf-8"), end="")
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
