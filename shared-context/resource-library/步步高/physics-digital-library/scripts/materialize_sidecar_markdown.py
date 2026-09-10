#!/usr/bin/env python3
"""在原始 Word 同目录生成可直接阅读的 Markdown 副本。

正式资料库内的 ``records/documents/*.md`` 始终是权威 Markdown。这个工具只把
它们复制为原始 ``.docx`` 同目录的同名阅读副本，方便在 Finder 中直接打开。
默认仅预览；只有传入 ``--apply`` 才写入副本。原始 Word、``raw/`` 链接和已有
非本工具生成的 Markdown 都不会被修改。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from urllib.parse import unquote, urlsplit


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from library_common import (  # noqa: E402
    LIBRARY_ROOT,
    PROFILES,
    PipelineError,
    SOURCE_ID_RE,
    document_id_for,
    is_safe_relative_path,
    official_library_root,
    sanitise_log_text,
    safe_library_root,
    safe_source_path,
    write_json,
)


REPORT_JSON_PATH = "reports/sidecar-markdown-materialization.json"
REPORT_VERSION = "1.0"
MARKER_PREFIX = "<!-- physics-digital-library-sidecar:"
HTML_IMAGE_SOURCE_RE = re.compile(
    r'(?P<prefix><img\b[^>]*?\bsrc=["\'])(?P<path>[^"\']+)(?P<suffix>["\'])',
    re.IGNORECASE,
)
MARKDOWN_IMAGE_SOURCE_RE = re.compile(
    r"(?P<prefix>!\[[^\]]*\]\(\s*)(?P<path><[^>]+>|(?:\\.|[^\s)])+)"
    r"(?P<suffix>(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\))"
)
MARKDOWN_REFERENCE_IMAGE_RE = re.compile(
    r"!\[(?P<alt>[^\]]*)\](?:\[(?P<label>[^\]]*)\]|(?![\[(]))"
)
MARKDOWN_REFERENCE_DEFINITION_RE = re.compile(
    r"^(?P<prefix>\s*\[(?P<label>[^\]]+)\]:\s*)(?P<path><[^>]+>|(?:\\.|[^\s])+)(?P<suffix>.*)$",
    re.MULTILINE,
)


class SidecarMaterializationError(RuntimeError):
    """旁置阅读副本无法安全生成时抛出。"""


class SidecarPlan:
    """一份来源的旁置副本预检结果。"""

    # 不使用 dataclass：项目现有的 unittest 通过 importlib 直接加载脚本，未将
    # module 注册到 sys.modules；Python 3.9 的 dataclass 在该场景会失败。
    def __init__(
        self,
        source_id: str,
        profile: str,
        source_relative_path: str,
        canonical_markdown: str | None,
        sidecar_filename: str | None,
        action: str,
        detail: str | None,
        canonical_bytes: int,
        sidecar_bytes: int,
        local_image_links_rewritten: int,
        source_path: Path | None = None,
        sidecar_path: Path | None = None,
        rendered_markdown: str | None = None,
    ) -> None:
        self.source_id = source_id
        self.profile = profile
        self.source_relative_path = source_relative_path
        self.canonical_markdown = canonical_markdown
        self.sidecar_filename = sidecar_filename
        self.action = action
        self.detail = detail
        self.canonical_bytes = canonical_bytes
        self.sidecar_bytes = sidecar_bytes
        self.local_image_links_rewritten = local_image_links_rewritten
        self.source_path = source_path
        self.sidecar_path = sidecar_path
        self.rendered_markdown = rendered_markdown


def marker_for(source_id: str, canonical_markdown: str) -> str:
    """返回唯一且可验证的生成标记；只允许刷新带完全相同标记的副本。"""
    if not SOURCE_ID_RE.fullmatch(source_id) or not is_safe_relative_path(canonical_markdown):
        raise ValueError("生成标记的来源 ID 或权威 Markdown 路径无效")
    return f"{MARKER_PREFIX} source_id={source_id} canonical={canonical_markdown} -->"


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _safe_library_file(root: Path, relative_path: object) -> Path:
    """解析资料库内普通文件，拒绝路径越界和任何符号链接成分。"""
    if not is_safe_relative_path(relative_path):
        raise SidecarMaterializationError("权威 Markdown 路径必须是资料库内的安全相对路径")
    target = root.joinpath(*PurePosixPath(str(relative_path)).parts)
    current = root
    for component in target.relative_to(root).parts:
        current = current / component
        if current.is_symlink():
            raise SidecarMaterializationError("权威 Markdown 或其父目录不能是符号链接")
    if not target.is_file():
        raise SidecarMaterializationError("权威 Markdown 不存在或不是普通文件")
    try:
        resolved = target.resolve(strict=True)
    except OSError as error:
        raise SidecarMaterializationError(f"无法读取权威 Markdown：{error}") from error
    if not _inside(resolved, root) or resolved != target:
        raise SidecarMaterializationError("权威 Markdown 解析后越出资料库")
    return target


def _load_sources(root: Path) -> list[dict[str, Any]]:
    manifest = _safe_library_file(root, "sources/sources.jsonl")
    sources: list[dict[str, Any]] = []
    seen: set[str] = set()
    try:
        lines = manifest.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise SidecarMaterializationError(f"无法读取来源清单：{error}") from error
    for line_number, line in enumerate(lines, start=1):
        try:
            source = json.loads(line)
        except json.JSONDecodeError as error:
            raise SidecarMaterializationError(
                f"sources/sources.jsonl 第 {line_number} 行无法解析：{error.msg}"
            ) from error
        source_id = source.get("id") if isinstance(source, dict) else None
        if not isinstance(source_id, str) or not SOURCE_ID_RE.fullmatch(source_id):
            raise SidecarMaterializationError(f"sources/sources.jsonl 第 {line_number} 行来源 ID 无效")
        if source_id in seen:
            raise SidecarMaterializationError(f"sources/sources.jsonl 中来源 ID 重复：{source_id}")
        seen.add(source_id)
        sources.append(source)
    return sources


def _document_relative_path(source_id: str) -> str:
    return f"records/documents/{document_id_for(source_id)}.json"


def _load_canonical_markdown(root: Path, source_id: str) -> tuple[str, Path, str]:
    """从 document 记录取得权威 Markdown 的安全路径和内容。"""
    document_relative_path = _document_relative_path(source_id)
    document_path = _safe_library_file(root, document_relative_path)
    try:
        document = json.loads(document_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SidecarMaterializationError(f"document 记录无法读取：{error}") from error
    if not isinstance(document, dict):
        raise SidecarMaterializationError("document 记录必须是 JSON 对象")
    if document.get("source_id") != source_id or document.get("relative_path") != document_relative_path:
        raise SidecarMaterializationError("document 记录与来源不匹配")
    content_path = document.get("content_path")
    if not isinstance(content_path, str) or not content_path.startswith("records/documents/"):
        raise SidecarMaterializationError("document 缺少受控的 content_path")
    markdown_path = _safe_library_file(root, content_path)
    if markdown_path.suffix.lower() != ".md":
        raise SidecarMaterializationError("document 的 content_path 必须是 Markdown 文件")
    try:
        return content_path, markdown_path, markdown_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise SidecarMaterializationError(f"权威 Markdown 无法读取：{error}") from error


def _safe_asset_path(root: Path, markdown_path: Path, reference: str) -> Path | None:
    """解析权威 Markdown 的本地图片引用，确保它是资料库内普通文件。

    网络、data URI 与锚点保持原样。任何声称为本地文件却越出资料库、缺失或落在
    符号链接上的引用都会拒绝该来源，避免生成一个表面成功、图片实际失效的副本。
    """
    raw_reference = reference.strip()
    if raw_reference.startswith("<") and raw_reference.endswith(">"):
        raw_reference = raw_reference[1:-1].strip()
    parsed = urlsplit(raw_reference)
    if raw_reference.startswith("#"):
        return None
    scheme = parsed.scheme.lower()
    if scheme in {"http", "https", "data"}:
        return None
    if parsed.netloc and scheme != "file":
        raise SidecarMaterializationError("图片引用只能使用 http(s)、data 或资料库内本地文件")
    if scheme and scheme != "file":
        raise SidecarMaterializationError("图片引用只能使用 http(s)、data 或资料库内本地文件")
    if scheme == "file" and parsed.netloc not in {"", "localhost"}:
        raise SidecarMaterializationError("file 图片引用只能指向本机资料库文件")
    if parsed.query or parsed.fragment:
        raise SidecarMaterializationError("本地图片引用不能含查询参数或锚点")
    reference_path = unquote(parsed.path)
    if not reference_path:
        raise SidecarMaterializationError("本地图片引用为空")
    candidate = Path(reference_path) if reference_path.startswith("/") else markdown_path.parent / reference_path
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise SidecarMaterializationError(f"本地图片不存在或无法解析：{reference}") from error
    if not _inside(resolved, root) or not resolved.is_file():
        raise SidecarMaterializationError("本地图片必须位于正式资料库内且为普通文件")
    # ``Path.is_symlink`` 只检查最后一段，因此所有中间目录也要逐段检查。
    try:
        relative = resolved.relative_to(root)
    except ValueError as error:  # defensive; _inside above already handles it
        raise SidecarMaterializationError("本地图片越出正式资料库") from error
    current = root
    for component in relative.parts:
        current = current / component
        if current.is_symlink():
            raise SidecarMaterializationError("本地图片不能位于符号链接路径上")
    return resolved


def _sidecar_image_reference(asset_path: Path, sidecar_parent: Path) -> str:
    """给旁置 Markdown 生成 VS Code 可渲染的相对图片路径。

    VS Code 预览不会可靠地处理带空格的绝对本机路径；相对于旁置文件目录的路径
    在 Finder、VS Code 与 Codex 中都可读取，且不复制图片。资产已经由调用方
    验证位于正式资料库中，允许 ``..`` 仅用于从原资料子目录回到资料库资产。
    """
    return PurePosixPath(os.path.relpath(asset_path, start=sidecar_parent)).as_posix()


def _unescape_markdown_path(value: str) -> str:
    """还原 inline Markdown URL 中的转义字符，供本地文件路径解析。"""
    return re.sub(r"\\(.)", r"\1", value)


def _reference_label(value: str) -> str:
    return " ".join(value.split()).casefold()


def _report_source_relative_path(value: object) -> str:
    """报告中只保留符合来源清单契约的相对路径。"""
    if isinstance(value, str) and is_safe_relative_path(value) and value.startswith("raw/"):
        return value
    return "<invalid>"


def _report_detail(root: Path, value: object, source_path: Path | None = None) -> str:
    """异常说明可以帮助定位，但不得把任何绝对路径写入正式报告。"""
    detail = sanitise_log_text(value, root, source_path)
    # 除工具已替换的 ``<source>`` 外，拒绝所有 Unix/Windows 形式的路径片段。
    detail = re.sub(r"(?<![\w.-])/(?:[^\s'\"<>)]*)", "<path>", detail)
    detail = re.sub(r"\b[A-Za-z]:[\\/](?:[^\s'\"<>)]*)", "<path>", detail)
    return detail or "旁置 Markdown 预检失败"


def rewrite_local_image_links(
    markdown: str, markdown_path: Path, root: Path, sidecar_parent: Path
) -> tuple[str, int]:
    """重写 HTML/Markdown 图片的本地引用，返回内容和改写数量。"""
    rewrites = 0

    def rewrite_html(match: re.Match[str]) -> str:
        nonlocal rewrites
        replacement = _safe_asset_path(root, markdown_path, match.group("path"))
        if replacement is None:
            return match.group(0)
        rewrites += 1
        return f"{match.group('prefix')}{_sidecar_image_reference(replacement, sidecar_parent)}{match.group('suffix')}"

    def rewrite_markdown(match: re.Match[str]) -> str:
        nonlocal rewrites
        replacement = _safe_asset_path(
            root, markdown_path, _unescape_markdown_path(match.group("path"))
        )
        if replacement is None:
            return match.group(0)
        rewrites += 1
        return f"{match.group('prefix')}{_sidecar_image_reference(replacement, sidecar_parent)}{match.group('suffix')}"

    rewritten = HTML_IMAGE_SOURCE_RE.sub(rewrite_html, markdown)
    rewritten = MARKDOWN_IMAGE_SOURCE_RE.sub(rewrite_markdown, rewritten)

    reference_labels: set[str] = set()
    for match in MARKDOWN_REFERENCE_IMAGE_RE.finditer(rewritten):
        label = match.group("label")
        reference_labels.add(_reference_label(label if label else match.group("alt")))

    def rewrite_reference_definition(match: re.Match[str]) -> str:
        nonlocal rewrites
        if _reference_label(match.group("label")) not in reference_labels:
            return match.group(0)
        replacement = _safe_asset_path(
            root, markdown_path, _unescape_markdown_path(match.group("path"))
        )
        if replacement is None:
            return match.group(0)
        rewrites += 1
        return f"{match.group('prefix')}{_sidecar_image_reference(replacement, sidecar_parent)}{match.group('suffix')}"

    rewritten = MARKDOWN_REFERENCE_DEFINITION_RE.sub(rewrite_reference_definition, rewritten)
    return rewritten, rewrites


def _read_existing_sidecar(path: Path) -> str | None:
    """读取一个普通既有副本；符号链接和目录都由调用方单独拒绝。"""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise SidecarMaterializationError(f"无法读取既有 Markdown：{error}") from error


def _existing_sidecar_action(target: Path, marker: str, rendered: str) -> tuple[str, str | None]:
    if target.is_symlink():
        return "blocked", "同名 Markdown 是符号链接，拒绝触碰"
    if not target.exists():
        return "would_create", None
    if not target.is_file():
        return "blocked", "同名路径不是普通文件，拒绝触碰"
    existing = _read_existing_sidecar(target)
    if not existing.startswith(marker + "\n"):
        return "conflict", "同名 Markdown 不是本工具生成，已保留原文件"
    if existing == rendered:
        return "unchanged", None
    return "would_refresh", None


def _render_sidecar(source_id: str, canonical_markdown: str, markdown: str) -> str:
    return f"{marker_for(source_id, canonical_markdown)}\n{markdown}"


def _plan_source(root: Path, source: dict[str, Any]) -> SidecarPlan:
    source_id = source.get("id")
    profile = source.get("profile")
    source_relative_path = source.get("relative_path")
    if not isinstance(source_id, str) or not SOURCE_ID_RE.fullmatch(source_id):
        return SidecarPlan("<invalid>", "", "", None, None, "blocked", "来源 ID 无效", 0, 0, 0)
    if not isinstance(profile, str) or profile not in PROFILES:
        return SidecarPlan(source_id, "<invalid>", "<invalid>", None, None, "blocked", "来源资料类型无效", 0, 0, 0)
    report_source_relative_path = _report_source_relative_path(source_relative_path)
    if report_source_relative_path == "<invalid>":
        return SidecarPlan(
            source_id,
            profile,
            report_source_relative_path,
            None,
            None,
            "blocked",
            "来源相对路径无效或不在 raw/ 下",
            0,
            0,
            0,
        )

    source_path: Path | None = None
    try:
        source_path = safe_source_path(root, report_source_relative_path)
        canonical_relative_path, canonical_path, canonical_markdown = _load_canonical_markdown(root, source_id)
        target = source_path.with_suffix(".md")
        # ``safe_source_path`` 已验证原始 Word 的父路径；这里再作显式同父目录
        # 检查，避免将文件写到其他位置。
        if target.parent.resolve(strict=True) != source_path.parent.resolve(strict=True):
            raise SidecarMaterializationError("旁置 Markdown 必须与原始 Word 位于同一目录")
        rewritten, rewrite_count = rewrite_local_image_links(
            canonical_markdown, canonical_path, root, target.parent.resolve(strict=True)
        )
        rendered = _render_sidecar(source_id, canonical_relative_path, rewritten)
        action, detail = _existing_sidecar_action(
            target, marker_for(source_id, canonical_relative_path), rendered
        )
        return SidecarPlan(
            source_id,
            profile,
            report_source_relative_path,
            canonical_relative_path,
            target.name,
            action,
            detail,
            len(canonical_markdown.encode("utf-8")),
            len(rendered.encode("utf-8")),
            rewrite_count,
            source_path,
            target,
            rendered,
        )
    except (PipelineError, SidecarMaterializationError, OSError) as error:
        return SidecarPlan(
            source_id,
            profile,
            report_source_relative_path,
            None,
            None,
            "blocked",
            _report_detail(root, error, source_path),
            0,
            0,
            0,
        )


def _select_sources(
    sources: Iterable[dict[str, Any]], source_ids: Iterable[str] | None, profiles: Iterable[str] | None
) -> list[dict[str, Any]]:
    requested_ids = set(source_ids or ())
    requested_profiles = set(profiles or ())
    if requested_ids:
        invalid = sorted(value for value in requested_ids if not SOURCE_ID_RE.fullmatch(value))
        if invalid:
            raise SidecarMaterializationError(f"无效 source_id：{', '.join(invalid)}")
    if requested_profiles:
        invalid_profiles = sorted(value for value in requested_profiles if value not in PROFILES)
        if invalid_profiles:
            raise SidecarMaterializationError(f"无效资料类型：{', '.join(invalid_profiles)}")
    selected = [
        source
        for source in sources
        if (not requested_ids or source.get("id") in requested_ids)
        and (not requested_profiles or source.get("profile") in requested_profiles)
    ]
    found_ids = {source.get("id") for source in selected}
    missing = sorted(requested_ids - found_ids)
    if missing:
        raise SidecarMaterializationError(f"来源清单中不存在指定 source_id：{', '.join(missing)}")
    return sorted(selected, key=lambda item: str(item.get("id")))


def _mark_duplicate_targets(plans: list[SidecarPlan]) -> list[SidecarPlan]:
    """预检中拒绝两个来源指向同一旁置路径，避免第二次写入覆盖第一次。"""
    paths: dict[Path, list[int]] = {}
    for index, plan in enumerate(plans):
        if plan.sidecar_path is not None and plan.action not in {"blocked", "conflict"}:
            paths.setdefault(plan.sidecar_path, []).append(index)
    duplicates = {index for indexes in paths.values() if len(indexes) > 1 for index in indexes}
    if not duplicates:
        return plans
    result = list(plans)
    for index in duplicates:
        plan = result[index]
        result[index] = SidecarPlan(
            plan.source_id,
            plan.profile,
            plan.source_relative_path,
            plan.canonical_markdown,
            plan.sidecar_filename,
            "blocked",
            "多个来源映射到同一个旁置 Markdown，拒绝写入",
            plan.canonical_bytes,
            plan.sidecar_bytes,
            plan.local_image_links_rewritten,
            plan.source_path,
            plan.sidecar_path,
            plan.rendered_markdown,
        )
    return result


def _atomic_write_sidecar(plan: SidecarPlan) -> str:
    """执行一条已经预检通过的写入，并在写前再次检查文件状态。"""
    if plan.sidecar_path is None or plan.rendered_markdown is None or plan.canonical_markdown is None:
        raise SidecarMaterializationError("旁置 Markdown 计划不完整")
    target = plan.sidecar_path
    marker = marker_for(plan.source_id, plan.canonical_markdown)
    current_action, detail = _existing_sidecar_action(target, marker, plan.rendered_markdown)
    if current_action == "unchanged":
        return "unchanged"
    if current_action == "conflict":
        return "conflict"
    if current_action == "blocked":
        return "blocked"
    if current_action not in {"would_create", "would_refresh"}:
        raise SidecarMaterializationError(detail or "旁置 Markdown 当前状态无效")

    descriptor, temporary_name = tempfile.mkstemp(prefix=".physics-sidecar-", suffix=".tmp", dir=target.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(plan.rendered_markdown)
            stream.flush()
            os.fsync(stream.fileno())
        # 最后一次显式拒绝符号链接；正常文件只可能是同一工具生成的副本。
        current_action, _ = _existing_sidecar_action(target, marker, plan.rendered_markdown)
        if current_action == "unchanged":
            return "unchanged"
        if current_action in {"conflict", "blocked"}:
            return current_action
        if current_action == "would_create":
            # ``link`` 是同目录内的原子“仅当目标不存在时创建”。即使预检之后
            # 别的程序刚写入了普通同名 Markdown，也会得到 EEXIST，而不会覆盖它。
            try:
                os.link(temporary_path, target)
            except FileExistsError:
                return "conflict"
            return "created"

        # 刷新只面向带本工具精确标记的副本；刚才的二次检查保证正常路径下不会
        # 覆盖用户文件。目标若在此刻被替换为普通文件，原子 replace 可能覆盖它，
        # 因此刷新使用已打开的受控文件描述符，而不是按路径 replace。
        if not hasattr(os, "O_NOFOLLOW"):
            return "blocked"
        descriptor = os.open(target, os.O_RDWR | os.O_NOFOLLOW)
        try:
            before = os.fstat(descriptor)
            existing = os.read(descriptor, before.st_size).decode("utf-8")
            if not existing.startswith(marker + "\n"):
                return "conflict"
            # 如果路径已指向另一个文件，不向新路径写；仅让已打开的旧文件自然失效。
            current = target.lstat()
            if current.st_ino != before.st_ino or current.st_dev != before.st_dev:
                return "conflict"
            os.lseek(descriptor, 0, os.SEEK_SET)
            os.ftruncate(descriptor, 0)
            os.write(descriptor, plan.rendered_markdown.encode("utf-8"))
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return "refreshed"
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _entry_for(plan: SidecarPlan, action: str | None = None) -> dict[str, Any]:
    return {
        "source_id": plan.source_id,
        "profile": plan.profile,
        "source_relative_path": plan.source_relative_path,
        "canonical_markdown": plan.canonical_markdown,
        "sidecar_filename": plan.sidecar_filename,
        "action": action or plan.action,
        "detail": plan.detail,
        "canonical_markdown_bytes": plan.canonical_bytes,
        "sidecar_markdown_bytes": plan.sidecar_bytes,
        "local_image_links_rewritten": plan.local_image_links_rewritten,
    }


def _summary(entries: Iterable[dict[str, Any]]) -> dict[str, int]:
    entries = list(entries)
    actions = Counter(str(entry["action"]) for entry in entries)
    return {
        "selected_sources": len(entries),
        "would_create": actions["would_create"],
        "would_refresh": actions["would_refresh"],
        "created": actions["created"],
        "refreshed": actions["refreshed"],
        "unchanged": actions["unchanged"],
        "conflict": actions["conflict"],
        "blocked": actions["blocked"],
        "written": actions["created"] + actions["refreshed"],
        "canonical_markdown_bytes": sum(int(entry["canonical_markdown_bytes"]) for entry in entries),
        "sidecar_markdown_bytes": sum(int(entry["sidecar_markdown_bytes"]) for entry in entries),
        "local_image_links_rewritten": sum(int(entry["local_image_links_rewritten"]) for entry in entries),
    }


def materialize_sidecars(
    library_root: Path | str = LIBRARY_ROOT,
    *,
    apply: bool = False,
    source_ids: Iterable[str] | None = None,
    profiles: Iterable[str] | None = None,
) -> dict[str, Any]:
    """预览或生成旁置 Markdown。

    ``apply=False`` 时不写任何文件；``apply=True`` 时只创建新副本或刷新带完全
    匹配标记的副本，并在正式库中记录一份不含绝对路径的统计报告。
    """
    root = safe_library_root(library_root)
    sources = _select_sources(_load_sources(root), source_ids, profiles)
    plans = _mark_duplicate_targets([_plan_source(root, source) for source in sources])
    entries: list[dict[str, Any]] = []
    if apply:
        for plan in plans:
            if plan.action not in {"would_create", "would_refresh", "unchanged"}:
                entries.append(_entry_for(plan))
                continue
            try:
                actual_action = _atomic_write_sidecar(plan)
            except (OSError, SidecarMaterializationError) as error:
                actual_action = "blocked"
                plan = SidecarPlan(
                    plan.source_id,
                    plan.profile,
                    plan.source_relative_path,
                    plan.canonical_markdown,
                    plan.sidecar_filename,
                    "blocked",
                    str(error),
                    plan.canonical_bytes,
                    plan.sidecar_bytes,
                    plan.local_image_links_rewritten,
                    plan.source_path,
                    plan.sidecar_path,
                    plan.rendered_markdown,
                )
            entries.append(_entry_for(plan, actual_action))
    else:
        entries = [_entry_for(plan) for plan in plans]

    result = {
        "report_version": REPORT_VERSION,
        "scope": "physics-digital-library-sidecar-markdown",
        "mode": "apply" if apply else "dry_run",
        "entries": entries,
        "summary": _summary(entries),
    }
    if apply:
        write_json(root, REPORT_JSON_PATH, result)
        result["report_path"] = REPORT_JSON_PATH
    return result


def _format_bytes(value: int) -> str:
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KiB"
    return f"{value / (1024 * 1024):.2f} MiB"


def _render_terminal_summary(result: dict[str, Any]) -> str:
    summary = result["summary"]
    mode_label = "已写入" if result["mode"] == "apply" else "预览（未写入）"
    lines = [
        f"旁置 Markdown：{mode_label}",
        f"选中来源：{summary['selected_sources']}；新建：{summary['created'] or summary['would_create']}；"
        f"刷新：{summary['refreshed'] or summary['would_refresh']}；未变化：{summary['unchanged']}；"
        f"冲突：{summary['conflict']}；阻断：{summary['blocked']}",
        f"权威 Markdown 内容：{_format_bytes(summary['canonical_markdown_bytes'])}；"
        f"旁置 Markdown 内容：{_format_bytes(summary['sidecar_markdown_bytes'])}；"
        f"本地图片链接改写：{summary['local_image_links_rewritten']} 处",
    ]
    if result["mode"] == "apply":
        lines.append(f"报告：{REPORT_JSON_PATH}")
    else:
        lines.append("这是预览；确认后加 --apply 才会在 Word 同目录写入 Markdown。")
    return "\n".join(lines)


def _arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--apply", action="store_true", help="真正写入旁置 Markdown；默认只预览")
    parser.add_argument("--source-id", action="append", help="只处理指定来源；可重复传入")
    parser.add_argument("--profile", choices=sorted(PROFILES), action="append", help="只处理指定资料类型；可重复传入")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="在原始 Word 同目录安全生成 Markdown 阅读副本")
    _arguments(parser)
    arguments = parser.parse_args(argv)
    try:
        root = official_library_root()
        result = materialize_sidecars(
            root,
            apply=arguments.apply,
            source_ids=arguments.source_id,
            profiles=arguments.profile,
        )
    except (PipelineError, SidecarMaterializationError) as error:
        parser.error(str(error))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) if arguments.json else _render_terminal_summary(result))
    summary = result["summary"]
    return 2 if summary["conflict"] or summary["blocked"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
