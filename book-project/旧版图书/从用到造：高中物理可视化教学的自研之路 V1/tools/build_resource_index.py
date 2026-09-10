#!/usr/bin/env python3
"""重建《从用到造》外部资源机械清单，并校验图书写作系统。

脚本只读取允许范围内的文件名和元数据，不读取正文，也不修改外部资源。
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parents[1]
OUTPUT_CSV = PROJECT_ROOT / "01_SOURCE" / "外部资源文件清单.csv"

ROOTS = (
    ("R01", "项目资源库", Path("/Users/yaril/个人文档/3 写作/项目资源库")),
    ("R02", "参考图书", Path("/Users/yaril/个人文档/3 写作/参考图书")),
    ("R03", "物理论文素材", Path("/Users/yaril/个人文档/3 写作/物理论文/素材")),
    ("R04", "课题与实验原件", Path("/Users/yaril/个人文档/0 物理实验项目课题/1 我的课题论文")),
    ("R05", "数智育才网站工程", Path("/Users/yaril/个人文档/数智育才网站")),
    ("R06", "继续教育课程原件", Path("/Users/yaril/个人文档/4 深圳继续教育课程设计")),
    (
        "R07",
        "特聘岗位月度佐证",
        Path("/Users/yaril/Documents/1育才中学个人资料/1深圳市基础教育特聘岗位/0 考核/月度考核详细内容"),
    ),
    ("R08", "中学物理论文精读营", Path("/Users/yaril/Documents/中学物理论文精读营（2025）第7期")),
    ("R09", "自制DIS与写作营论文", Path("/Users/yaril/Documents/2 论文阅读/raw/papers")),
    ("R10", "原始物理问题课题论文", Path("/Users/yaril/Documents/原始物理问题课题/原始物理问题课题论文")),
    ("R11", "人工智能名师工作室公众号", Path("/Users/yaril/Documents/《人工智能名师工作室》公众号")),
    (
        "R12",
        "从积木到智能体校本教材",
        Path("/Users/yaril/个人文档/2 智能硬件选修课/校本教材《从积木到智能体——ESP32 智能硬件创意编程》"),
    ),
    (
        "R13",
        "2026特优生AI作品评审",
        Path("/Users/yaril/个人文档/0 物理实验项目课题/2026特优生评选"),
    ),
    (
        "R14",
        "论文02学生AI协作评价",
        Path("/Users/yaril/个人文档/3 写作/物理论文/论文02-学生AI协作评价"),
    ),
)

EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".next",
    "dist",
    "build",
    "coverage",
    ".cache",
    ".turbo",
    ".playwright-cli",
    ".playwright-mcp",
    ".zcode",
}

EXTENSION_CLASS = {
    ".md": "文本与网页",
    ".markdown": "文本与网页",
    ".txt": "文本与网页",
    ".rtf": "文本与网页",
    ".html": "文本与网页",
    ".htm": "文本与网页",
    ".doc": "Office文档",
    ".docx": "Office文档",
    ".ppt": "Office文档",
    ".pptx": "Office文档",
    ".xls": "Office文档",
    ".xlsx": "Office文档",
    ".pages": "Office文档",
    ".key": "Office文档",
    ".numbers": "Office文档",
    ".pdf": "PDF",
    ".jpg": "图片",
    ".jpeg": "图片",
    ".png": "图片",
    ".webp": "图片",
    ".gif": "图片",
    ".svg": "图片",
    ".tif": "图片",
    ".tiff": "图片",
    ".heic": "图片",
    ".avif": "图片",
    ".bmp": "图片",
    ".emf": "图片",
    ".wmf": "图片",
    ".psd": "图片",
    ".ai": "图片",
    ".drawio": "图片",
    ".mp4": "视频",
    ".mov": "视频",
    ".m4v": "视频",
    ".webm": "视频",
    ".mkv": "视频",
    ".avi": "视频",
    ".wav": "音频与字幕",
    ".mp3": "音频与字幕",
    ".m4a": "音频与字幕",
    ".aac": "音频与字幕",
    ".srt": "音频与字幕",
    ".vtt": "音频与字幕",
    ".ass": "音频与字幕",
    ".csv": "结构化数据",
    ".tsv": "结构化数据",
    ".json": "结构化数据",
    ".yaml": "结构化数据",
    ".yml": "结构化数据",
    ".xml": "结构化数据",
    ".zip": "归档文件",
    ".rar": "归档文件",
    ".7z": "归档文件",
}

REQUIRED_FILES = (
    PROJECT_ROOT.parent / "AGENTS.md",
    PROJECT_ROOT / "00_CONTEXT" / "README.md",
    PROJECT_ROOT / "00_CONTEXT" / "BOOK_POSITION.md",
    PROJECT_ROOT / "00_CONTEXT" / "CHAPTER_MAP.md",
    PROJECT_ROOT / "00_CONTEXT" / "STYLE_REFERENCE.md",
    PROJECT_ROOT / "00_CONTEXT" / "VISUAL_STRATEGY.md",
    PROJECT_ROOT / "00_CONTEXT" / "WORKFLOW.md",
    PROJECT_ROOT / "00_CONTEXT" / "SKILL_ROUTER.md",
    PROJECT_ROOT / "00_CONTEXT" / "templates" / "章节任务书.md",
    PROJECT_ROOT / "00_CONTEXT" / "templates" / "素材考古表.md",
    PROJECT_ROOT / "00_CONTEXT" / "templates" / "视觉策划单.md",
    PROJECT_ROOT / "00_CONTEXT" / "templates" / "事实档案-template.yaml",
    PROJECT_ROOT / "00_CONTEXT" / "templates" / "章节审稿表.md",
    PROJECT_ROOT / "01_SOURCE" / "全书资源地图.md",
    PROJECT_ROOT / "01_SOURCE" / "章节资源索引.md",
    PROJECT_ROOT / "01_SOURCE" / "视觉证据索引.md",
    PROJECT_ROOT / "01_SOURCE" / "外部资源根目录.md",
    PROJECT_ROOT / "01_SOURCE" / "索引维护说明.md",
    PROJECT_ROOT / "01_SOURCE" / "本书资料台账.md",
    PROJECT_ROOT / "01_SOURCE" / "资料入口.md",
    PROJECT_ROOT / "01_SOURCE" / "资料转写索引.md",
    PROJECT_ROOT / "01_SOURCE" / "资料转写台账.csv",
    PROJECT_ROOT / "01_SOURCE" / "第5章" / "第5章资料深挖与引用矩阵.md",
    PROJECT_ROOT / "01_SOURCE" / "第5章" / "第5章视觉策划单.md",
    PROJECT_ROOT / "01_SOURCE" / "第5章" / "作者确认问题.md",
    PROJECT_ROOT / "01_SOURCE" / "第6章" / "章节任务书.md",
    PROJECT_ROOT / "01_SOURCE" / "第6章" / "第6章资料深挖与引用矩阵.md",
    PROJECT_ROOT / "01_SOURCE" / "第6章" / "第6章视觉策划单.md",
    PROJECT_ROOT / "01_SOURCE" / "第6章" / "作者确认问题.md",
    PROJECT_ROOT / "01_SOURCE" / "第6章" / "facts" / "shuzhiyucai-platform-001.yaml",
    PROJECT_ROOT / "01_SOURCE" / "第3章" / "作者确认-2026-08-12.md",
    PROJECT_ROOT / "01_SOURCE" / "第3章" / "第3章资料深挖与引用矩阵.md",
    PROJECT_ROOT / "专著框架蓝图_v1.md",
    PROJECT_ROOT / "02_MANUSCRIPT" / "第3章 创新实验与自制教具：让不可见变为可见.md",
    PROJECT_ROOT / "02_MANUSCRIPT" / "第5章 图形化编程：让代码驱动真实世界.md",
    PROJECT_ROOT / "02_MANUSCRIPT" / "第6章 数字化教学平台：让分散资源成为共同入口.md",
    PROJECT_ROOT / "02_MANUSCRIPT" / "assets" / "README.md",
    PROJECT_ROOT / "01_SOURCE" / "第3章" / "facts" / "exp-active-circuit-puzzle-001.yaml",
    PROJECT_ROOT / "01_SOURCE" / "第3章" / "facts" / "exp-static-field-mapper-001.yaml",
    PROJECT_ROOT / "03_REVIEW" / "README.md",
    PROJECT_ROOT / "03_REVIEW" / "第6章" / "审稿结论.md",
    PROJECT_ROOT / "review" / "第6章数字化教学平台" / "review.md",
    PROJECT_ROOT / "review" / "第6章数字化教学平台" / "index.html",
    PROJECT_ROOT / "review" / "图书写作系统搭建" / "review.md",
    PROJECT_ROOT / "review" / "图书写作系统搭建" / "index.html",
    PROJECT_ROOT / "review" / "图书写作系统搭建" / "assets" / "system-map.svg",
    PROJECT_ROOT / "review" / "图书写作系统搭建" / "assets" / "system-map.png",
    PROJECT_ROOT / "review" / "图书写作系统搭建" / "assets" / "review-desktop.png",
    WORKSPACE_ROOT / ".agents" / "skills" / "baoyu-article-illustrator" / "SKILL.md",
    WORKSPACE_ROOT / ".agents" / "skills" / "baoyu-diagram" / "SKILL.md",
    WORKSPACE_ROOT / ".agents" / "skills" / "baoyu-cover-image" / "SKILL.md",
    WORKSPACE_ROOT / ".agents" / "skills" / "baoyu-image-gen" / "SKILL.md",
    WORKSPACE_ROOT / ".agents" / "skills" / "huashu-proofreading" / "SKILL.md",
    WORKSPACE_ROOT / ".agents" / "skills" / "huashu-md-to-pdf" / "SKILL.md",
    WORKSPACE_ROOT / ".agents" / "skills" / "book-material-mining" / "SKILL.md",
)


def eligible_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDED_DIRS)
        base = Path(dirpath)
        for filename in sorted(filenames):
            path = base / filename
            suffix = path.suffix.lower()
            if suffix not in EXTENSION_CLASS:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            if not path.is_file():
                continue
            yield path, stat, suffix


def build_rows():
    rows = []
    missing_roots = []
    for root_id, category, root in ROOTS:
        if not root.is_dir():
            missing_roots.append(str(root))
            continue
        for path, stat, suffix in eligible_files(root):
            rows.append(
                {
                    "root_id": root_id,
                    "root_category": category,
                    "media_class": EXTENSION_CLASS[suffix],
                    "extension": suffix.lstrip("."),
                    "size_bytes": str(stat.st_size),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds"),
                    "filename": path.name,
                    "relative_path": str(path.relative_to(root)),
                    "absolute_path": str(path),
                }
            )
    rows.sort(key=lambda row: (row["root_id"], row["relative_path"].casefold()))
    return rows, missing_roots


def write_csv(rows):
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = (
        "root_id",
        "root_category",
        "media_class",
        "extension",
        "size_bytes",
        "modified_at",
        "filename",
        "relative_path",
        "absolute_path",
    )
    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_csv():
    if not OUTPUT_CSV.is_file():
        return []
    with OUTPUT_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def print_summary(rows):
    root_counts = Counter(row["root_id"] for row in rows)
    class_counts = Counter(row["media_class"] for row in rows)
    print(f"清单文件：{OUTPUT_CSV}")
    print(f"候选文件：{len(rows)}")
    print("按根目录：" + "，".join(f"{key}={root_counts[key]}" for key, _, _ in ROOTS))
    print("按类型：" + "，".join(f"{key}={value}" for key, value in sorted(class_counts.items())))


def check_system():
    errors = []
    warnings = []

    for path in REQUIRED_FILES:
        if not path.is_file():
            errors.append(f"缺少系统文件：{path}")

    for _, _, root in ROOTS:
        if not root.is_dir():
            errors.append(f"外部根目录不可访问：{root}")

    rows = load_csv()
    if not rows:
        errors.append(f"机械清单不存在或为空：{OUTPUT_CSV}")
    else:
        paths = [row.get("absolute_path", "") for row in rows]
        duplicate_paths = [path for path, count in Counter(paths).items() if count > 1]
        if duplicate_paths:
            errors.append(f"机械清单存在重复路径：{len(duplicate_paths)}条")

        missing_paths = [path for path in paths if not Path(path).is_file()]
        if missing_paths:
            errors.append(f"机械清单存在失效路径：{len(missing_paths)}条")
            for path in missing_paths[:10]:
                warnings.append(f"失效路径示例：{path}")

    ch03_assets = PROJECT_ROOT / "02_MANUSCRIPT" / "assets" / "ch03"
    asset_count = sum(1 for path in ch03_assets.iterdir() if path.is_file()) if ch03_assets.is_dir() else 0
    if asset_count != 17:
        errors.append(f"第3章基准图件应为17项，当前为{asset_count}项")

    ch05_assets = PROJECT_ROOT / "02_MANUSCRIPT" / "assets" / "ch05"
    ch05_asset_count = sum(1 for path in ch05_assets.iterdir() if path.is_file()) if ch05_assets.is_dir() else 0
    if ch05_asset_count != 15:
        errors.append(f"第5章基准图件应为15项，当前为{ch05_asset_count}项")

    ch06_assets = PROJECT_ROOT / "02_MANUSCRIPT" / "assets" / "ch06"
    ch06_png_count = sum(1 for path in ch06_assets.glob("*.png") if path.is_file()) if ch06_assets.is_dir() else 0
    if ch06_png_count != 19:
        errors.append(f"第6章正文PNG图件应为19项，当前为{ch06_png_count}项")

    for warning in warnings:
        print(f"警告：{warning}")
    if errors:
        for error in errors:
            print(f"失败：{error}")
        return 1

    print(
        f"通过：系统文件、{len(ROOTS)}个外部根目录、{len(rows)}条清单路径、"
        "17项第3章图件、15项第5章图件和19幅第6章正文图均有效。"
    )
    return 0


def main():
    parser = argparse.ArgumentParser(description="重建外部资源清单或校验图书写作系统")
    parser.add_argument("--check", action="store_true", help="只校验现有系统和清单，不重建")
    args = parser.parse_args()

    if args.check:
        return check_system()

    rows, missing_roots = build_rows()
    if missing_roots:
        for root in missing_roots:
            print(f"失败：外部根目录不可访问：{root}")
        return 1
    write_csv(rows)
    print_summary(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
