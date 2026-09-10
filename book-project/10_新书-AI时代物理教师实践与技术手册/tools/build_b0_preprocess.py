#!/usr/bin/env python3
"""生成 B0 预加工层的机械索引。

只读取明确登记的材料根目录，写入新书项目的
``01_SOURCE/B0_PREPROCESS/generated``。不改动任何原材料。
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = PROJECT_ROOT / "01_SOURCE" / "B0_PREPROCESS" / "generated"

WRITING_ROOT = Path("/Users/yaril/个人文档/3 写作")
RESOURCE_ROOT = WRITING_ROOT / "项目资源库"
REFERENCE_ROOT = WRITING_ROOT / "参考图书"


COLLECTIONS = [
    {
        "id": "AUTHOR-PROJECT-ENTRY",
        "name": "作者项目资源库入口层",
        "root": RESOURCE_ROOT / "00_AGENT入口",
        "owner": "黄灿斌",
        "identity": "作者项目导航",
        "boundary": "索引只负责路由，具体主张仍需回到项目原件。",
    },
    {
        "id": "TEXTBOOKS",
        "name": "高中物理教材与教师用书",
        "root": RESOURCE_ROOT / "教材",
        "owner": "教材原作者与出版社",
        "identity": "第三方教材",
        "boundary": "优先读精校版或官网 Hybrid 优化版；公式、常数、表格、题目和直接引语回查原 PDF。",
    },
    {
        "id": "OTHER-TEACHERS",
        "name": "其他教师材料",
        "root": RESOURCE_ROOT / "9 其他老师资源库",
        "owner": "王硕、严力耕、丁龙及相关学生",
        "identity": "他人原创与同侪参照",
        "boundary": "保持原作者；未经许可不作本书核心实证，涉及学生信息的材料不得默认打开。",
    },
    {
        "id": "OLD-BOOK",
        "name": "旧书作者反馈修订稿",
        "root": WRITING_ROOT / "图书出版" / "旧版图书" / "从用到造：高中物理可视化教学的自研之路 V1-作者反馈修订稿",
        "owner": "旧书各材料原作者",
        "identity": "旧书参考文本与已加工材料系统",
        "boundary": "只读复用材料卡和参考文本；不沿用旧书结构，具体事实回到当前原件。",
    },
    {
        "id": "REF-HUANG",
        "name": "黄正玉物理教育专著精校版",
        "root": REFERENCE_ROOT / "黄正玉书" / "高中物理习题实验化的实践与探索_精校版",
        "owner": "黄正玉",
        "identity": "第三方物理教育专著",
        "boundary": "结构与理论参考；不复制受版权保护的段落、案例和图片。",
    },
    {
        "id": "REF-GGB",
        "name": "GeoGebra 与高中物理专著精校版",
        "root": REFERENCE_ROOT / "GGB软件和高中物理的深度融合" / "GeoGebra软件和高中物理的深度融合_精校版",
        "owner": "乔永海",
        "identity": "第三方物理教育专著",
        "boundary": "结构与软件案例体例参考；动态软件状态另核，不照搬图件与操作清单。",
    },
    {
        "id": "REF-SMART-PHYSICS",
        "name": "聪明教物理精校版",
        "root": REFERENCE_ROOT / "聪明教物理" / "聪明教物理_精校版",
        "owner": "袁芳主编及原书作者",
        "identity": "第三方物理教育专著",
        "boundary": "理论与结构参考，不作为作者课堂事实来源。",
    },
    {
        "id": "REF-AI-ORANGE",
        "name": "AI 橙皮书系列",
        "root": REFERENCE_ROOT / "AI橙皮书系列" / "md",
        "owner": "各书原作者与译者",
        "identity": "外部 AI 方法与工具书",
        "boundary": "先读总索引和逐书导航；产品功能、模型能力、价格与政策在写作时重新核验。",
    },
    {
        "id": "REF-WORKBUDDY",
        "name": "WorkBuddyGuide 蓝皮书",
        "root": REFERENCE_ROOT / "WorkBuddyGuide蓝皮书" / "docs" / "bluebook",
        "owner": "WorkBuddy 社区作者",
        "identity": "外部 AI 工具与案例书",
        "boundary": "先读总目录；保留原作者与许可，产品信息重核，不推导教师培训效果。",
    },
]


TEXTBOOK_PRIMARY = [
    {
        "id": "TB-RJ-B1",
        "edition": "人教版",
        "volume": "必修第一册",
        "kind": "学生教材",
        "quality": "精校版",
        "path": RESOURCE_ROOT / "教材" / "精校版" / "人教版" / "人教版物理必修第一册" / "人教版物理必修第一册_精校版.md",
    },
    {
        "id": "TB-RJ-B2",
        "edition": "人教版",
        "volume": "必修第二册",
        "kind": "学生教材",
        "quality": "官网 Hybrid 优化版",
        "path": RESOURCE_ROOT / "教材" / "优化版" / "人教版" / "人教版物理必修第二册_官网Hybrid优化版" / "人教版物理必修第二册_官网Hybrid优化版.md",
    },
    {
        "id": "TB-RJ-B3",
        "edition": "人教版",
        "volume": "必修第三册",
        "kind": "学生教材",
        "quality": "官网 Hybrid 优化版",
        "path": RESOURCE_ROOT / "教材" / "优化版" / "人教版" / "人教版物理必修第三册_官网Hybrid优化版" / "人教版物理必修第三册_官网Hybrid优化版.md",
    },
    {
        "id": "TB-RJ-X1",
        "edition": "人教版",
        "volume": "选择性必修第一册",
        "kind": "学生教材",
        "quality": "官网 Hybrid 优化版",
        "path": RESOURCE_ROOT / "教材" / "优化版" / "人教版" / "人教版物理选择性必修第一册_官网Hybrid优化版" / "人教版物理选择性必修第一册_官网Hybrid优化版.md",
    },
    {
        "id": "TB-RJ-X2",
        "edition": "人教版",
        "volume": "选择性必修第二册",
        "kind": "学生教材",
        "quality": "官网 Hybrid 优化版",
        "path": RESOURCE_ROOT / "教材" / "优化版" / "人教版" / "人教版物理选择性必修第二册_官网Hybrid优化版" / "人教版物理选择性必修第二册_官网Hybrid优化版.md",
    },
    {
        "id": "TB-RJ-X3",
        "edition": "人教版",
        "volume": "选择性必修第三册",
        "kind": "学生教材",
        "quality": "官网 Hybrid 优化版",
        "path": RESOURCE_ROOT / "教材" / "优化版" / "人教版" / "人教版物理选择性必修第三册_官网Hybrid优化版" / "人教版物理选择性必修第三册_官网Hybrid优化版.md",
    },
    {
        "id": "TB-YJ-B1",
        "edition": "粤教版",
        "volume": "必修第一册",
        "kind": "学生教材",
        "quality": "官网 Hybrid 优化版",
        "path": RESOURCE_ROOT / "教材" / "优化版" / "粤教版" / "粤教版物理必修第一册_官网Hybrid优化版" / "粤教版物理必修第一册_官网Hybrid优化版.md",
    },
    {
        "id": "TB-YJ-B2",
        "edition": "粤教版",
        "volume": "必修第二册",
        "kind": "学生教材",
        "quality": "官网 Hybrid 优化版",
        "path": RESOURCE_ROOT / "教材" / "优化版" / "粤教版" / "粤教版物理必修第二册_官网Hybrid优化版" / "粤教版物理必修第二册_官网Hybrid优化版.md",
    },
    {
        "id": "TB-YJ-B3",
        "edition": "粤教版",
        "volume": "必修第三册",
        "kind": "学生教材",
        "quality": "官网 Hybrid 优化版",
        "path": RESOURCE_ROOT / "教材" / "优化版" / "粤教版" / "粤教版物理必修第三册_官网Hybrid优化版" / "粤教版物理必修第三册_官网Hybrid优化版.md",
    },
    {
        "id": "TB-YJ-X1",
        "edition": "粤教版",
        "volume": "选择性必修第一册",
        "kind": "学生教材",
        "quality": "官网 Hybrid 优化版",
        "path": RESOURCE_ROOT / "教材" / "优化版" / "粤教版" / "粤教版物理选择性必修第一册_官网Hybrid优化版" / "粤教版物理选择性必修第一册_官网Hybrid优化版.md",
    },
    {
        "id": "TB-YJ-X2",
        "edition": "粤教版",
        "volume": "选择性必修第二册",
        "kind": "学生教材",
        "quality": "官网 Hybrid 优化版",
        "path": RESOURCE_ROOT / "教材" / "优化版" / "粤教版" / "粤教版物理选择性必修第二册_官网Hybrid优化版" / "粤教版物理选择性必修第二册_官网Hybrid优化版.md",
    },
    {
        "id": "TB-YJ-X3",
        "edition": "粤教版",
        "volume": "选择性必修第三册",
        "kind": "学生教材",
        "quality": "精校版",
        "path": RESOURCE_ROOT / "教材" / "精校版" / "粤教版" / "粤教版物理选择性必修第三册" / "粤教版物理选择性必修第三册_精校版.md",
    },
    {
        "id": "TB-RJ-TEACHER-B2",
        "edition": "人教版",
        "volume": "教师用书·必修第二册",
        "kind": "教师用书",
        "quality": "精校版",
        "path": RESOURCE_ROOT / "教材" / "精校版" / "人教版" / "新物理教师用书必修2" / "新物理教师用书必修2_精校版.md",
    },
]

PRIMARY_TEXTBOOK_PATHS = {str(item["path"]) for item in TEXTBOOK_PRIMARY}


def should_skip(path: Path) -> bool:
    return any(
        part in {".git", "node_modules", "__pycache__"} or part == ".DS_Store"
        for part in path.parts
    ) or path.name.startswith("~$") or path.suffix.lower() == ".pyc"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_md(path: Path) -> tuple[str, int, int, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    title = ""
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    image_refs = len(re.findall(r"!\[[^\]]*\]\([^\)]+\)|<img\b", text, flags=re.I))
    return title, text.count("\n") + 1, len(text), image_refs


def classify_role(collection_id: str, rel: Path, path: Path) -> str:
    rel_text = rel.as_posix()
    ext = path.suffix.lower()
    if str(path) in PRIMARY_TEXTBOOK_PATHS:
        return "教材默认Markdown"
    if collection_id == "TEXTBOOKS":
        if "精校版/" in rel_text and ext == ".md":
            return "教材精校Markdown"
        if "优化版/" in rel_text and ext == ".md":
            return "教材优化Markdown"
        if "MinerU官网转换/" in rel_text and ext in {".md", ".tex", ".json"}:
            return "教材转换追溯文件"
        if ext == ".pdf":
            return "教材原PDF"
        if ext in {".jpg", ".jpeg", ".png", ".webp"}:
            return "教材配图"
        if "review/" in rel_text:
            return "教材处理审阅记录"
        return "教材过程或辅助文件"
    if collection_id == "OTHER-TEACHERS":
        if rel.name.endswith("素材卡片.md") or rel.name == "其他老师资源库-目录说明.md":
            return "他人材料导航卡"
        if "2026特优生评选/ai技能测试/" in rel_text:
            return "受限学生作品"
        if ext in {".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".pdf"}:
            return "他人原始教学或项目材料"
        if ext in {".html", ".py", ".js"}:
            return "他人技术材料"
        return "他人材料附件"
    if collection_id == "OLD-BOOK":
        if rel_text == "01_SOURCE/资料入口.md":
            return "旧书材料系统入口"
        if rel_text == "02_MANUSCRIPT/全书合订稿.md":
            return "旧书参考文本"
        if rel.name == "材料卡.md":
            return "旧书材料卡"
        if rel.name == "正文.md" and "资料转写库/" in rel_text:
            return "旧书转写正文"
        if ext == ".md":
            return "旧书加工文档"
        if ext in {".png", ".jpg", ".jpeg", ".svg", ".webp"}:
            return "旧书视觉材料"
        return "旧书辅助文件"
    if collection_id == "AUTHOR-PROJECT-ENTRY":
        return "作者项目入口卡" if ext == ".md" else "作者项目入口附件"
    if collection_id == "REF-AI-ORANGE":
        if rel_text == "00_总索引.md":
            return "AI工具书总索引"
        if rel_text.startswith("导航/") and ext == ".md":
            return "AI工具书逐书导航"
        if ext == ".md":
            return "AI工具书全文"
        return "AI工具书附件"
    if collection_id == "REF-WORKBUDDY":
        return "WorkBuddy总目录" if rel_text == "index.md" else (
            "WorkBuddy章节Markdown" if ext == ".md" else "WorkBuddy配图或附件"
        )
    if collection_id.startswith("REF-"):
        return "物理教育专著精校正文" if ext == ".md" else "物理教育专著配图"
    return "其他"


def sensitivity(collection_id: str, rel: Path) -> str:
    rel_text = rel.as_posix()
    if collection_id == "OTHER-TEACHERS" and "2026特优生评选/ai技能测试/" in rel_text:
        return "高：含学生姓名或作品"
    if collection_id == "OTHER-TEACHERS":
        return "中：他人原创或个人信息"
    if collection_id in {"TEXTBOOKS", "REF-HUANG", "REF-GGB", "REF-SMART-PHYSICS", "REF-AI-ORANGE", "REF-WORKBUDDY"}:
        return "中：第三方版权"
    return "低：仍按项目证据边界使用"


def default_read(collection_id: str, rel: Path, path: Path) -> str:
    rel_text = rel.as_posix()
    if str(path) in PRIMARY_TEXTBOOK_PATHS:
        return "按需"
    if collection_id == "AUTHOR-PROJECT-ENTRY" and rel.name in {
        "KNOWLEDGE_MAP.md", "PROJECT_INDEX.md", "EVIDENCE_INDEX.md", "CLAIMS.md", "TASK_ROUTER.md"
    }:
        return "入口"
    if collection_id == "OTHER-TEACHERS" and (
        rel.name.endswith("素材卡片.md") or rel.name == "其他老师资源库-目录说明.md"
    ):
        return "入口"
    if collection_id == "OLD-BOOK" and rel_text in {
        "01_SOURCE/资料入口.md", "01_SOURCE/全书资源地图.md", "01_SOURCE/章节资源索引.md",
        "02_MANUSCRIPT/全书合订稿.md"
    }:
        return "按需"
    if collection_id == "OLD-BOOK" and rel.name == "材料卡.md":
        return "按需"
    if collection_id == "REF-AI-ORANGE" and (
        rel_text == "00_总索引.md" or rel_text.startswith("导航/")
    ):
        return "入口"
    if collection_id == "REF-WORKBUDDY" and rel.name == "index.md":
        return "入口"
    if collection_id in {"REF-HUANG", "REF-GGB", "REF-SMART-PHYSICS"} and path.suffix.lower() == ".md":
        return "按需"
    return "否"


def file_owner(collection_id: str, default_owner: str, rel: Path) -> str:
    if collection_id == "OTHER-TEACHERS" and rel.parts:
        if rel.parts[0] in {"王硕", "严力耕", "丁龙"}:
            return rel.parts[0]
    return default_owner


def build_rows() -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    collection_stats: list[dict] = []
    for collection in COLLECTIONS:
        root = collection["root"]
        if not root.exists():
            raise FileNotFoundError(f"材料根目录不存在：{root}")
        files = sorted((p for p in root.rglob("*") if p.is_file() and not should_skip(p)), key=lambda p: str(p))
        ext_counts: Counter[str] = Counter()
        role_counts: Counter[str] = Counter()
        bytes_total = 0
        for path in files:
            rel = path.relative_to(root)
            stat = path.stat()
            ext = path.suffix.lower().lstrip(".") or "[无扩展名]"
            role = classify_role(collection["id"], rel, path)
            entry = default_read(collection["id"], rel, path)
            title = ""
            line_count = ""
            char_count = ""
            image_refs = ""
            if path.suffix.lower() == ".md":
                title, line_count, char_count, image_refs = read_md(path)
            file_hash = ""
            if path.suffix.lower() == ".md" and entry in {"入口", "按需"}:
                file_hash = sha256(path)
            row = {
                "collection_id": collection["id"],
                "collection": collection["name"],
                "owner": file_owner(collection["id"], collection["owner"], rel),
                "identity": collection["identity"],
                "role": role,
                "default_read": entry,
                "sensitivity": sensitivity(collection["id"], rel),
                "extension": ext,
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds"),
                "line_count": line_count,
                "char_count": char_count,
                "image_refs": image_refs,
                "title": title,
                "sha256": file_hash,
                "relative_path": rel.as_posix(),
                "absolute_path": str(path),
                "boundary": collection["boundary"],
            }
            rows.append(row)
            ext_counts[ext] += 1
            role_counts[role] += 1
            bytes_total += stat.st_size
        collection_stats.append({
            "id": collection["id"],
            "name": collection["name"],
            "root": str(root),
            "owner": collection["owner"],
            "identity": collection["identity"],
            "boundary": collection["boundary"],
            "file_count": len(files),
            "size_bytes": bytes_total,
            "extensions": dict(ext_counts.most_common()),
            "roles": dict(role_counts.most_common()),
        })
    return rows, collection_stats


def extract_textbook_outline(item: dict) -> dict:
    path: Path = item["path"]
    if not path.exists():
        raise FileNotFoundError(f"教材默认底本不存在：{path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    chapters: list[dict] = []
    current: dict | None = None
    chapter_re = re.compile(r"^#\s*(第[一二三四五六七八九十百0-9]+章[^#\n]*)$")
    section_re = re.compile(r"^##\s*((?:第[一二三四五六七八九十百0-9]+节\b|[0-9]+(?:[\.、\s]|$)|实验[:：]).*)$")
    for line in text.splitlines():
        chapter_match = chapter_re.match(line.strip())
        if chapter_match:
            current = {"title": chapter_match.group(1).strip(), "sections": []}
            chapters.append(current)
            continue
        section_match = section_re.match(line.strip())
        if section_match and current is not None:
            title = section_match.group(1).strip()
            if title not in current["sections"]:
                current["sections"].append(title)
    title, lines, chars, images = read_md(path)
    return {
        **{key: value for key, value in item.items() if key != "path"},
        "path": str(path),
        "title": title,
        "line_count": lines,
        "char_count": chars,
        "image_refs": images,
        "sha256": sha256(path),
        "chapters": chapters,
    }


def human_size(size: int) -> str:
    value = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024 or unit == "GB":
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}GB"


def write_outputs(rows: list[dict], stats: list[dict], outlines: list[dict]) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_ROOT / "B0-文件级索引.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    (OUTPUT_ROOT / "B0-集合统计.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUTPUT_ROOT / "B0-教材章目.json").write_text(
        json.dumps(outlines, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    total_size = sum(item["size_bytes"] for item in stats)
    lines = [
        "# B0机械索引统计摘要",
        "",
        "> 本文件由 `tools/build_b0_preprocess.py` 生成。它只说明发现了什么，不替代材料价值判断。",
        "",
        f"- 建档材料集合：{len(stats)}个",
        f"- 文件级记录：{len(rows)}条",
        f"- 记录文件总体量：{human_size(total_size)}",
        f"- 教材默认Markdown：{len(outlines)}册（12册学生教材＋1册教师用书）",
        "- 已排除：`.DS_Store`、`__pycache__`、`.pyc`和Office临时文件。",
        "",
        "## 材料集合",
        "",
        "| 集合 | 文件数 | 体量 | 默认入口 | 边界 |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    rows_by_collection = defaultdict(list)
    for row in rows:
        rows_by_collection[row["collection_id"]].append(row)
    for item in stats:
        entry_count = sum(1 for row in rows_by_collection[item["id"]] if row["default_read"] == "入口")
        ondemand_count = sum(1 for row in rows_by_collection[item["id"]] if row["default_read"] == "按需")
        lines.append(
            f"| {item['name']} | {item['file_count']} | {human_size(item['size_bytes'])} | "
            f"入口{entry_count}／按需{ondemand_count} | {item['boundary']} |"
        )
    lines.extend([
        "",
        "## 如何查询",
        "",
        "- Agent日常不读取完整CSV；先读上级轻量入口和材料卡。",
        "- 需要找文件时，用`rg '关键词' generated/B0-文件级索引.csv`定向检索。",
        "- `default_read=入口`只代表导航优先，不代表内容可以直接写入正文。",
        "- `敏感级别=高`的学生材料，未获作者裁决前不得打开正文或注入模型。",
        "",
    ])
    (OUTPUT_ROOT / "B0-机械索引统计摘要.md").write_text("\n".join(lines), encoding="utf-8")

    outline_lines = [
        "# 高中物理教材大纲卡片索引",
        "",
        "> 默认使用13份Markdown：12册学生教材＋1册教师用书。精校版优先于官网 Hybrid 优化版；官网原始Markdown只用于追溯。",
        "",
        "## 阅读规则",
        "",
        "1. 先按版别、册别和章目选择，不整本注入上下文。",
        "2. 需要比较教材表达时，同一知识主题只打开人教版、粤教版各1个相关章节。",
        "3. 公式、常数、数据表、题目和直接引语进入成稿前回查原PDF。",
        "4. 教材能支持概念边界、内容顺序和学习任务设计，不能证明作者课堂效果。",
        "",
    ]
    for item in outlines:
        outline_lines.extend([
            f"## {item['id']}｜{item['edition']}《{item['volume']}》",
            "",
            f"- 类型：{item['kind']}；底本：{item['quality']}；{item['line_count']}行；{item['image_refs']}处图片引用。",
            f"- 默认路径：`{item['path']}`",
            f"- SHA-256：`{item['sha256']}`",
            "- 章目：",
            "",
        ])
        for chapter in item["chapters"]:
            sections = "；".join(chapter["sections"])
            outline_lines.append(f"  - **{chapter['title']}**" + (f"：{sections}" if sections else ""))
        outline_lines.append("")
    (OUTPUT_ROOT / "B0-教材大纲卡片索引.md").write_text("\n".join(outline_lines), encoding="utf-8")


def main() -> None:
    rows, stats = build_rows()
    outlines = [extract_textbook_outline(item) for item in TEXTBOOK_PRIMARY]
    write_outputs(rows, stats, outlines)
    print(f"generated files={len(rows)} collections={len(stats)} textbooks={len(outlines)}")


if __name__ == "__main__":
    main()
