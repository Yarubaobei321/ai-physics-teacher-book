#!/usr/bin/env python3
"""验收 B0 预加工层、资料台账和静态审阅页。"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRE = ROOT / "01_SOURCE" / "B0_PREPROCESS"
GEN = PRE / "generated"
REVIEW = ROOT / "review" / "B0材料全景与Agent入口-2026-08-29"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def verify_generated() -> tuple[list[dict], list[dict]]:
    required = [
        GEN / "B0-文件级索引.csv",
        GEN / "B0-集合统计.json",
        GEN / "B0-教材章目.json",
        GEN / "B0-教材大纲卡片索引.md",
        GEN / "B0-机械索引统计摘要.md",
    ]
    for path in required:
        require(path.is_file() and path.stat().st_size > 0, f"缺失或为空：{path}")

    rows = load_csv(GEN / "B0-文件级索引.csv")
    stats = json.loads((GEN / "B0-集合统计.json").read_text(encoding="utf-8"))
    outlines = json.loads((GEN / "B0-教材章目.json").read_text(encoding="utf-8"))
    require(len(rows) == 10491, f"文件级记录应为10491，实际{len(rows)}")
    require(sum(item["file_count"] for item in stats) == len(rows), "集合文件数与CSV不一致")
    keys = [(row["collection_id"], row["absolute_path"]) for row in rows]
    require(len(keys) == len(set(keys)), "文件级索引存在重复collection_id＋path")
    missing = [row["absolute_path"] for row in rows if not Path(row["absolute_path"]).exists()]
    require(not missing, f"文件级索引有失效路径：{missing[:3]}")
    restricted = [row for row in rows if row["sensitivity"].startswith("高")]
    require(len(restricted) == 271, f"高敏感记录应为271，实际{len(restricted)}")

    require(len(outlines) == 13, f"教材默认底本应为13，实际{len(outlines)}")
    for item in outlines:
        path = Path(item["path"])
        require(path.is_file(), f"教材底本缺失：{path}")
        require(digest(path) == item["sha256"], f"教材指纹变化：{item['id']}")
        require(item["chapters"], f"教材章目为空：{item['id']}")
    return rows, outlines


def verify_registry(outlines: list[dict]) -> None:
    registry = load_csv(ROOT / "01_SOURCE" / "资料转写台账.csv")
    require(len(registry) == 34, f"资料转写台账应为34项，实际{len(registry)}")
    ids = [row["resource_id"] for row in registry]
    require(len(ids) == len(set(ids)), "资料转写台账resource_id重复")
    for row in registry:
        path = Path(row["source_path"])
        require(path.is_file(), f"资料台账路径失效：{row['resource_id']} {path}")
        require(path.stat().st_size == int(row["source_size"]), f"资料台账大小变化：{row['resource_id']}")
        require(digest(path) == row["source_sha256"], f"资料台账指纹变化：{row['resource_id']}")
    outline_ids = {f"B0-{item['id']}" for item in outlines}
    require(outline_ids.issubset(set(ids)), "教材默认底本未全部进入资料转写台账")


def verify_cards() -> None:
    required = [
        PRE / "README.md",
        PRE / "B0-AGENT轻量入口.md",
        PRE / "B0-全景材料分类索引.md",
        PRE / "cards" / "B0-作者项目卡片索引.md",
        PRE / "cards" / "B0-教材主题导航卡.md",
        PRE / "cards" / "B0-其他教师材料卡片索引.md",
        PRE / "cards" / "B0-旧书与参考书卡片索引.md",
        PRE / "cards" / "B0-写作工作区补充材料卡.md",
    ]
    for path in required:
        require(path.is_file() and path.stat().st_size > 500, f"人工卡缺失或过短：{path}")
    author_card = (PRE / "cards" / "B0-作者项目卡片索引.md").read_text(encoding="utf-8")
    require(len(re.findall(r"^## PRJ-", author_card, flags=re.M)) == 13, "作者项目卡数量不是13")
    peer_card = (PRE / "cards" / "B0-其他教师材料卡片索引.md").read_text(encoding="utf-8")
    primary_peer_cards = re.findall(r"^### (?:WS|YL|DL)-\d+", peer_card, flags=re.M)
    require(len(primary_peer_cards) == 15, f"其他教师主要项目包应为15，实际{len(primary_peer_cards)}")


def verify_html(rows: list[dict]) -> None:
    index = REVIEW / "index.html"
    converted = REVIEW / "review.html"
    review_md = REVIEW / "review.md"
    for path in [index, converted, review_md]:
        require(path.is_file() and path.stat().st_size > 0, f"审阅交付缺失：{path}")
    html = index.read_text(encoding="utf-8")
    require("http://" not in html and "https://" not in html, "主HTML包含外部网络地址")
    card_count = html.count("m('")
    require(card_count == 48, f"HTML材料卡应为48，实际{card_count}")
    require("10,491" in html and "271" in html, "HTML缺少关键统计")
    require(html.count("<script>") == html.count("</script>") == 1, "HTML脚本标签不配对")
    restricted_paths = [row["absolute_path"] for row in rows if row["sensitivity"].startswith("高")]
    leaked = [path for path in restricted_paths if path in html]
    require(not leaked, "HTML泄露了高敏感学生文件路径")
    for relative in [
        "../../01_SOURCE/B0_PREPROCESS/B0-AGENT轻量入口.md",
        "../../01_SOURCE/B0_PREPROCESS/B0-全景材料分类索引.md",
        "../../01_SOURCE/B0-可用材料总表.md",
        "review.md",
    ]:
        require((REVIEW / relative).resolve().is_file(), f"HTML相对链接失效：{relative}")


def main() -> None:
    rows, outlines = verify_generated()
    verify_registry(outlines)
    verify_cards()
    verify_html(rows)
    print("B0 preprocess verification: PASS")
    print("collections=9 files=10491 textbooks=13 author_projects=13 peer_packages=15 restricted=271 registry=34 html_cards=48")


if __name__ == "__main__":
    main()
