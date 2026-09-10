#!/usr/bin/env python3
"""步步高正式资料库转换流水线的共享基础。

这里的函数只处理正式资料库的输出目录。原始 Word 由 ``raw/`` 的受控链接提供，
本模块不会向该目录写入任何内容。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any


LIBRARY_ROOT = Path(__file__).resolve().parents[1]
PROFILES = frozenset({"teacher", "gaokao", "textbook"})
APPROVED_RAW_COLLECTIONS = frozenset(
    {
        "bbg-2026-yilun",
        "bbg-required-1",
        "bbg-required-2",
        "bbg-required-3",
        "bbg-elective-1",
        "bbg-elective-2",
        "bbg-elective-3",
    }
)
SOURCE_ID_RE = re.compile(r"^src\.bbg\.[0-9a-f]{64}$")
SOURCE_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
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


class PipelineError(RuntimeError):
    """资料库流水线遇到安全边界或不可恢复输入错误时抛出。"""


def is_safe_relative_path(value: object) -> bool:
    """返回值是否为资料库内的 POSIX 相对路径。"""
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    if re.match(r"^[A-Za-z]:", value):
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and "." not in path.parts


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def safe_library_root(root: Path | str = LIBRARY_ROOT) -> Path:
    """解析一个可写资料库根，拒绝符号链接根和不存在目录。

    CLI 只传入本脚本所属的正式根；接受显式根是为了让离线测试能在临时目录验证
    同一套安全输出逻辑。
    """
    candidate = Path(root)
    if candidate.is_symlink() or not candidate.is_dir():
        raise PipelineError("资料库根必须是现有且非符号链接的目录")
    try:
        return candidate.resolve(strict=True)
    except OSError as error:
        raise PipelineError(f"无法解析资料库根：{error}") from error


def official_library_root(candidate: Path | str = LIBRARY_ROOT) -> Path:
    """只接受当前脚本所属的正式资料库根，用于命令行入口。"""
    resolved_candidate = safe_library_root(candidate)
    resolved_official = safe_library_root(LIBRARY_ROOT)
    if resolved_candidate != resolved_official:
        raise PipelineError("命令行只允许在当前 physics-digital-library 正式根运行")
    return resolved_official


def source_short_for(source_id: str) -> str:
    """生成可读且稳定的来源短标识；完整 hash 仍保留在 source ID 中。"""
    if not SOURCE_ID_RE.fullmatch(source_id):
        raise ValueError(f"来源 ID 格式无效：{source_id!r}")
    return source_id.rsplit(".", 1)[-1][:16]


def document_id_for(source_id: str) -> str:
    return f"doc.bbg.{source_short_for(source_id)}"


def document_topic_id_for(source_id: str) -> str:
    return f"kn.bbg.{source_short_for(source_id)}"


def heading_knowledge_id_for(source_id: str, sequence: int) -> str:
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise ValueError("标题知识点序号必须是大于零的整数")
    return f"{document_topic_id_for(source_id)}.h{sequence:03d}"


def question_id_for(source_id: str, sequence: int) -> str:
    """按资料库计划生成与来源完整绑定的稳定题目 ID。"""
    if not SOURCE_ID_RE.fullmatch(source_id):
        raise ValueError(f"来源 ID 格式无效：{source_id!r}")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise ValueError("题目序号必须是大于零的整数")
    return f"q.{source_id}.{sequence:03d}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_source_path(library_root: Path | str, relative_path: str) -> Path:
    """安全地解析 ``raw/`` 内已登记的 docx，只读且不接受越界路径。"""
    root = safe_library_root(library_root)
    if not is_safe_relative_path(relative_path) or not relative_path.startswith("raw/"):
        raise PipelineError("来源路径必须是 raw/ 下的安全相对路径")
    parts = PurePosixPath(relative_path).parts
    if len(parts) < 3 or parts[0] != "raw" or not relative_path.lower().endswith(".docx"):
        raise PipelineError("来源必须是 raw/ 内登记的 .docx 文件")
    raw_root = root / "raw"
    collection_name = parts[1]
    collection_root = raw_root / collection_name
    if collection_name not in APPROVED_RAW_COLLECTIONS:
        raise PipelineError(f"来源 collection 未获批准：{collection_name}")
    if not raw_root.is_dir() or not collection_root.is_symlink():
        raise PipelineError(f"来源文件不存在：{relative_path}")
    current = collection_root
    for component in parts[2:]:
        current = current / component
        if current.is_symlink():
            raise PipelineError(f"来源路径不能包含嵌套符号链接：{relative_path}")
    try:
        resolved_collection = collection_root.resolve(strict=True)
        resolved_source = current.resolve(strict=True)
    except OSError as error:
        raise PipelineError(f"来源文件不可读取：{relative_path}（{error}）") from error
    # worktree 的一级 raw 链接允许精确地指向同名受控资料目录，即使最终目录在
    # 原工作树。边界由批准 collection 名、顶级链接和『最终 source 必须仍在该
    # collection 内』三层共同约束；子级符号链接则一律拒绝。
    if not resolved_collection.is_dir() or not _is_within(resolved_source, resolved_collection):
        raise PipelineError(f"来源路径越出批准资料范围：{relative_path}")
    if not resolved_source.is_file() or resolved_source.is_symlink():
        raise PipelineError(f"来源必须是普通文件：{relative_path}")
    return resolved_source


def _output_is_allowed(relative_path: str) -> bool:
    return any(relative_path.startswith(prefix) for prefix in OUTPUT_PREFIXES)


def safe_output_path(
    library_root: Path | str, relative_path: str, *, create_parent: bool = True
) -> Path:
    """返回正式资料库允许写入的路径，并拒绝输出目录中的符号链接。"""
    root = safe_library_root(library_root)
    if not is_safe_relative_path(relative_path) or not _output_is_allowed(relative_path):
        raise PipelineError(f"不允许写入此路径：{relative_path!r}")
    target = root.joinpath(*PurePosixPath(relative_path).parts)
    current = root
    for component in target.relative_to(root).parts[:-1]:
        current = current / component
        if current.exists():
            if current.is_symlink() or not current.is_dir():
                raise PipelineError(f"输出父目录必须是普通目录：{relative_path}")
        elif create_parent:
            current.mkdir()
        else:
            raise PipelineError(f"输出父目录不存在：{relative_path}")
    if target.is_symlink():
        raise PipelineError(f"输出文件不能是符号链接：{relative_path}")
    try:
        resolved_parent = target.parent.resolve(strict=True)
        resolved_target = target.resolve(strict=False)
    except OSError as error:
        raise PipelineError(f"无法解析输出路径：{relative_path}（{error}）") from error
    if not _is_within(resolved_parent, root) or not _is_within(resolved_target, root):
        raise PipelineError(f"输出路径越出正式资料库：{relative_path}")
    return target


def write_bytes(library_root: Path | str, relative_path: str, data: bytes) -> Path:
    """原子写入受控输出路径；可覆盖先前生成的同名产物，绝不触及 raw。"""
    target = safe_output_path(library_root, relative_path)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".pipeline-", dir=target.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        if target.is_symlink():
            raise PipelineError(f"输出文件不能是符号链接：{relative_path}")
        os.replace(temporary_path, target)
    except BaseException:
        if temporary_path.exists():
            temporary_path.unlink()
        raise
    return target


def write_text(library_root: Path | str, relative_path: str, text: str) -> Path:
    return write_bytes(library_root, relative_path, text.encode("utf-8"))


def json_bytes(value: Any, *, indent: int = 2) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=indent) + "\n").encode("utf-8")


def write_json(library_root: Path | str, relative_path: str, value: Any) -> Path:
    return write_bytes(library_root, relative_path, json_bytes(value))


def remove_generated_file(library_root: Path | str, relative_path: str) -> bool:
    """仅删除一份受控正式输出文件；绝不接受 raw 或目录目标。"""
    target = safe_output_path(library_root, relative_path, create_parent=False)
    if not target.exists():
        return False
    if target.is_symlink() or not target.is_file():
        raise PipelineError(f"只能删除普通生成文件：{relative_path}")
    target.unlink()
    return True


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def markdown_relative_path(markdown_relative_path: str, asset_relative_path: str) -> str:
    """返回从 documents Markdown 到正式库资产的统一 POSIX 相对引用。"""
    if not is_safe_relative_path(markdown_relative_path) or not is_safe_relative_path(asset_relative_path):
        raise ValueError("Markdown 和资产路径必须是安全的资料库相对路径")
    markdown_parent = PurePosixPath(markdown_relative_path).parent
    return PurePosixPath(os.path.relpath(asset_relative_path, markdown_parent.as_posix())).as_posix()


def sanitise_log_text(value: object, library_root: Path | str, source_path: Path | None = None) -> str:
    """保留命令异常信息，同时把其中的本地绝对路径替换为资料库相对路径。"""
    text = str(value or "")
    root = safe_library_root(library_root)
    replacements: list[tuple[str, str]] = [(str(root), ".")]
    if source_path is not None:
        try:
            replacements.append((str(source_path.resolve()), "<source>"))
        except OSError:
            replacements.append((str(source_path), "<source>"))
    for absolute, replacement in sorted(replacements, key=lambda item: len(item[0]), reverse=True):
        text = text.replace(absolute, replacement)
    return text
