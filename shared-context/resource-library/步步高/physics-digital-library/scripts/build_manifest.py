#!/usr/bin/env python3
"""建立步步高物理资料库的可复现源文件清单。

脚本只读取 ``raw/`` 内批准的七个原始资料链接，绝不写入链接目标或原始 Word。
清单和统计报告只能写入本正式资料库内经过安全检查的 ``sources/``、``reports/``。
它不转换 Word，也不解析题目。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from source_state import (  # noqa: E402
    SourceStateError,
    default_source_state,
    read_source_manifest,
    reconcile_source_states as _reconcile_source_states,
    write_source_manifest,
)


LIBRARY_ROOT = Path(__file__).resolve().parents[1]
PROFILE_ORDER = ("teacher", "gaokao", "textbook")
OUTPUT_PATHS = frozenset({"sources/sources.jsonl", "reports/source-inventory.json"})
APPROVED_RAW_LINKS = {
    "bbg-2026-yilun": "2026 大一轮",
    "bbg-required-1": "步步高必修1",
    "bbg-required-2": "步步高必修2",
    "bbg-required-3": "步步高必修3",
    "bbg-elective-1": "步步高选修1",
    "bbg-elective-2": "步步高选修2",
    "bbg-elective-3": "步步高选修3",
}
TEXTBOOK_COLLECTIONS = {
    "bbg-required-1": "必修1",
    "bbg-required-2": "必修2",
    "bbg-required-3": "必修3",
    "bbg-elective-1": "选修1",
    "bbg-elective-2": "选修2",
    "bbg-elective-3": "选修3",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
CHAPTER_RE = re.compile(r"第[一二三四五六七八九十百零〇两0-9]+章")
LESSON_RE = re.compile(r"第\s*(\d+)\s*课时")
EXAM_YEAR_RE = re.compile(r"(?<!\d)(20(?:2[0-4]))(?=年|物理高考题|高考)")
KNOWN_VERSION_HINTS = ("精校版", "搜集版", "收集版")
KNOWN_BUNDLES = (
    "教师用书Word版文档",
    "全书完整的Word版文档",
    "配套WORD",
    "配套练习",
    "学习笔记",
    "练透",
    "答案精析",
)


class ManifestBuildError(RuntimeError):
    """清单不能安全生成时抛出。"""


def is_relative_library_path(value: str) -> bool:
    """判断是否是资料库内的 POSIX 相对路径。"""
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


def official_library_root(candidate: Path = LIBRARY_ROOT) -> Path:
    """只接受当前脚本所属的正式资料库根及其安全解析等价路径。"""
    candidate = Path(candidate)
    try:
        resolved_candidate = candidate.resolve(strict=True)
        resolved_official = LIBRARY_ROOT.resolve(strict=True)
    except OSError as error:
        raise ManifestBuildError(f"无法解析正式资料库根：{error}") from error
    if not resolved_candidate.is_dir() or resolved_candidate != resolved_official:
        raise ManifestBuildError("只允许在当前 physics-digital-library 正式根构建清单")
    return resolved_official


def safe_output_path(library_root: Path, relative_path: str) -> Path:
    """返回可安全写入的清单输出路径，拒绝链接和资料库外目标。"""
    if relative_path not in OUTPUT_PATHS:
        raise ManifestBuildError(f"不允许写入此输出路径：{relative_path!r}")
    root = Path(library_root)
    if root.is_symlink() or not root.is_dir():
        raise ManifestBuildError("输出根必须是现有且非符号链接的目录")
    resolved_root = root.resolve(strict=True)
    target = resolved_root.joinpath(*PurePosixPath(relative_path).parts)
    if target.parent.is_symlink() or not target.parent.is_dir():
        raise ManifestBuildError(f"输出父目录必须预先存在：{relative_path}")
    if target.is_symlink():
        raise ManifestBuildError(f"输出文件不能是符号链接：{relative_path}")
    if target.exists() and not target.is_file():
        raise ManifestBuildError(f"输出文件必须是普通文件：{relative_path}")
    resolved_parent = target.parent.resolve(strict=True)
    resolved_target = target.resolve(strict=False)
    if not _is_within(resolved_parent, resolved_root) or not _is_within(resolved_target, resolved_root):
        raise ManifestBuildError(f"输出路径越出正式资料库：{relative_path}")
    return target


def source_id_for_hash(sha256: str) -> str:
    """以完整内容哈希生成稳定 source ID。"""
    if not SHA256_RE.fullmatch(sha256):
        raise ValueError("sha256 必须是 64 位小写十六进制字符串")
    return f"src.bbg.{sha256}"


def sha256_file(path: Path) -> str:
    """流式计算文件完整 SHA-256，避免一次读入大型 Word 文件。"""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path_parts(relative_path: str) -> tuple[str, ...]:
    if not is_relative_library_path(relative_path):
        raise ValueError(f"路径必须是资料库内相对路径：{relative_path!r}")
    return PurePosixPath(relative_path).parts


def classify_profile(relative_path: str) -> str:
    """仅按批准原始资料链接下的路径分类，不读取 Word 内容。"""
    parts = _path_parts(relative_path)
    if len(parts) < 3 or parts[0] != "raw":
        raise ManifestBuildError(f"无法按约定资料范围分类：{relative_path}")
    collection = parts[1]
    if collection == "bbg-2026-yilun" and parts[2] == "教师用书Word版文档":
        return "teacher"
    if collection == "bbg-2026-yilun" and parts[2] == "2020-2024物理高考题":
        return "gaokao"
    if collection in TEXTBOOK_COLLECTIONS:
        return "textbook"
    raise ManifestBuildError(f"无法按约定资料范围分类：{relative_path}")


def _normalise_title(stem: str) -> str:
    return re.sub(r"\s+", " ", stem).strip()


def _extract_chapter(parts: tuple[str, ...]) -> tuple[str | None, str | None]:
    """目录章节优先于文件名，避免历史文件名与目录发生冲突时误覆盖。"""
    for component in reversed(parts[:-1]):
        match = CHAPTER_RE.search(component)
        if match:
            return match.group(0), "directory"
    match = CHAPTER_RE.search(PurePosixPath(parts[-1]).stem)
    if match:
        return match.group(0), "filename"
    return None, None


def _first_matching_component(parts: tuple[str, ...], values: Iterable[str]) -> str | None:
    choices = set(values)
    for component in parts:
        if component in choices:
            return component
    return None


def extract_metadata(relative_path: str, profile: str) -> dict[str, Any]:
    """从路径和文件名提取无需内容解析即可获得的提示字段。"""
    parts = _path_parts(relative_path)
    raw_collection = parts[1] if len(parts) > 1 and parts[0] == "raw" else None
    chapter, chapter_origin = _extract_chapter(parts)
    filename = PurePosixPath(parts[-1]).stem
    lesson = LESSON_RE.search(filename)

    exam_year: int | None = None
    if profile == "gaokao":
        for component in parts:
            match = EXAM_YEAR_RE.search(component)
            if match:
                exam_year = int(match.group(1))
                break

    return {
        "raw_collection": raw_collection,
        "series_year": 2026 if raw_collection == "bbg-2026-yilun" else None,
        "exam_year": exam_year,
        "course": TEXTBOOK_COLLECTIONS.get(raw_collection),
        "chapter": chapter,
        "chapter_origin": chapter_origin,
        "lesson_no": int(lesson.group(1)) if lesson else None,
        "version_hint": _first_matching_component(parts, KNOWN_VERSION_HINTS),
        "source_bundle": _first_matching_component(parts, KNOWN_BUNDLES),
    }


def _approved_raw_target(raw_root: Path, source_container: Path, link_name: str, source_name: str) -> Path:
    link = raw_root / link_name
    if not link.is_symlink():
        raise ManifestBuildError(f"raw/{link_name} 必须是原始资料符号链接")
    expected_link_text = f"../../{source_name}"
    try:
        link_text = os.readlink(link)
    except OSError as error:
        raise ManifestBuildError(f"raw/{link_name} 的链接目标不可读取：{error}") from error
    if link_text != expected_link_text:
        raise ManifestBuildError(
            f"raw/{link_name} 必须精确链接到 {expected_link_text!r}"
        )
    try:
        resolved_container = source_container.resolve(strict=True)
        resolved_target = link.resolve(strict=True)
        expected_target = (resolved_container / source_name).resolve(strict=True)
    except OSError as error:
        raise ManifestBuildError(f"raw/{link_name} 的链接目标不可读取：{error}") from error
    if (
        not resolved_container.is_dir()
        or not resolved_target.is_dir()
        or resolved_target != expected_target
    ):
        raise ManifestBuildError(f"raw/{link_name} 的最终目标不是批准的原始资料目录")
    return resolved_target


def iter_docx_files(raw_root: Path, source_container: Path) -> Iterable[tuple[str, Path]]:
    """稳定扫描七个批准链接，且不跟随任何子级符号链接。"""
    raw_root = Path(raw_root)
    if raw_root.is_symlink() or not raw_root.is_dir():
        raise ManifestBuildError("raw 必须是现有且非符号链接的目录")
    try:
        source_container = Path(source_container).resolve(strict=True)
    except OSError as error:
        raise ManifestBuildError(f"无法解析 项目资源库/步步高 原始资料范围：{error}") from error
    if not source_container.is_dir():
        raise ManifestBuildError("项目资源库/步步高 原始资料范围必须是目录")
    collected: list[tuple[str, Path]] = []
    for link_name, source_name in APPROVED_RAW_LINKS.items():
        source_target = _approved_raw_target(raw_root, source_container, link_name, source_name)
        for directory, subdirectories, filenames in os.walk(source_target, followlinks=False):
            directory_path = Path(directory)
            subdirectories[:] = sorted(
                name for name in subdirectories if not (directory_path / name).is_symlink()
            )
            for filename in sorted(filenames):
                if not filename.lower().endswith(".docx"):
                    continue
                candidate = directory_path / filename
                if candidate.is_symlink() or not candidate.is_file():
                    continue
                relative_under_source = candidate.relative_to(source_target).as_posix()
                relative_path = (PurePosixPath("raw") / link_name / relative_under_source).as_posix()
                collected.append((relative_path, candidate))
    yield from sorted(collected, key=lambda item: item[0])


def collect_sources(library_root: Path = LIBRARY_ROOT) -> list[dict[str, Any]]:
    """读取批准的 raw 资料链接，生成尚未处理的 source 记录。"""
    root = official_library_root(library_root)
    records: list[dict[str, Any]] = []
    ids: set[str] = set()
    for relative_path, path in iter_docx_files(root / "raw", root.parent):
        if not is_relative_library_path(relative_path) or not relative_path.startswith("raw/"):
            raise ManifestBuildError(f"原始资料路径越出资料库根：{relative_path}")
        profile = classify_profile(relative_path)
        sha256 = sha256_file(path)
        source_id = source_id_for_hash(sha256)
        if source_id in ids:
            raise ManifestBuildError(f"发现内容哈希重复的原始资料：{relative_path} ({source_id})")
        ids.add(source_id)
        records.append(
            {
                "id": source_id,
                "metadata": extract_metadata(relative_path, profile),
                "profile": profile,
                "relative_path": relative_path,
                "sha256": sha256,
                "title": _normalise_title(path.stem),
                **default_source_state(),
            }
        )
    return sorted(records, key=lambda record: record["relative_path"])


def reconcile_source_states(
    fresh_records: Iterable[dict[str, Any]], previous_records: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    """只为内容身份未变的来源回填已验证的处理状态。

    具体字段和身份校验由 ``source_state`` 集中实现；此处保留薄包装，方便清单构建
    与基础层测试使用同一契约。
    """
    return _reconcile_source_states(fresh_records, previous_records)


def _previous_source_records(root: Path) -> list[dict[str, object]]:
    """读取已有状态；格式陈旧或损坏时安全放弃继承，仍可从原始资料重建清单。"""
    path = safe_output_path(root, "sources/sources.jsonl")
    if not path.exists():
        return []
    try:
        return read_source_manifest(root)
    except SourceStateError:
        return []


def build_inventory_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    """从清单记录生成同样可复现的来源统计报告。"""
    profiles = Counter(record["profile"] for record in records)
    collections = Counter(record["metadata"]["raw_collection"] for record in records)
    return {
        "by_profile": {profile: profiles[profile] for profile in PROFILE_ORDER},
        "by_raw_collection": {
            collection: collections[collection]
            for collection in sorted(collection for collection in collections if collection is not None)
        },
        "manifest_path": "sources/sources.jsonl",
        "raw_root": "raw",
        "schema_version": "1.1",
        "total_sources": len(records),
    }


def json_bytes(value: Any, *, indent: int | None = None) -> bytes:
    """序列化为稳定的 UTF-8 JSON 字节。"""
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=indent) + "\n").encode("utf-8")


def jsonl_bytes(records: list[dict[str, Any]]) -> bytes:
    """序列化为稳定排序后的 JSONL 字节。"""
    return b"".join(json_bytes(record) for record in records)


def _write_if_changed(root: Path, relative_path: str, data: bytes) -> None:
    path = safe_output_path(root, relative_path)
    if path.exists() and path.read_bytes() == data:
        return
    path.write_bytes(data)


def build_manifest(library_root: Path = LIBRARY_ROOT) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """在唯一正式资料库内构建并写入清单与来源统计报告。"""
    root = official_library_root(library_root)
    previous_records = _previous_source_records(root)
    records = reconcile_source_states(collect_sources(root), previous_records)
    report = build_inventory_report(records)
    write_source_manifest(root, records)
    _write_if_changed(root, "reports/source-inventory.json", json_bytes(report, indent=2))
    return records, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="建立步步高物理资料库原始来源清单")
    parser.add_argument(
        "--root",
        type=Path,
        default=LIBRARY_ROOT,
        help="仅接受当前脚本所属的 physics-digital-library 正式根",
    )
    args = parser.parse_args(argv)
    try:
        records, report = build_manifest(args.root)
    except (ManifestBuildError, OSError, ValueError) as error:
        print(f"清单构建失败：{error}", file=sys.stderr)
        return 1
    counts = report["by_profile"]
    print(
        "已写入 sources/sources.jsonl："
        f"{report['total_sources']} 条（teacher {counts['teacher']} / "
        f"gaokao {counts['gaokao']} / textbook {counts['textbook']}）"
    )
    print("已写入 reports/source-inventory.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
