#!/usr/bin/env python3
"""校验单篇或多篇逐段审阅与润色 JSON 是否完整、图片路径是否保留、字段是否齐全。"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
UNITS_DIR = BASE / "units"
REVIEWS_DIR = BASE / "reviews"

IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def validate_one(doc_id: str) -> list[str]:
    errors = []
    u_path = UNITS_DIR / f"{doc_id}.json"
    r_path = REVIEWS_DIR / f"{doc_id}.json"
    if not u_path.is_file():
        return [f"{doc_id}: missing units file {u_path}"]
    if not r_path.is_file():
        return [f"{doc_id}: missing review file {r_path}"]

    u_data = json.loads(u_path.read_text(encoding="utf-8"))
    r_data = json.loads(r_path.read_text(encoding="utf-8"))

    units = u_data["units"]
    items = r_data.get("items", [])
    ch_rev = r_data.get("chapter_review", {})
    if not ch_rev.get("reader_impression") or not ch_rev.get("editorial_critique"):
        errors.append(f"{doc_id}: missing chapter_review.reader_impression or editorial_critique")

    if len(units) != len(items):
        errors.append(f"{doc_id}: unit count mismatch: expected {len(units)}, got {len(items)}")
        return errors

    for u, it in zip(units, items):
        uid = u["unit_id"]
        if it.get("unit_id") != uid:
            errors.append(f"{doc_id}: unit_id mismatch at index {u['index']}: {it.get('unit_id')} != {uid}")
        if it.get("status") not in ("keep", "polish", "struct"):
            errors.append(f"{uid}: invalid status {it.get('status')!r}")
        if not str(it.get("tag", "")).strip():
            errors.append(f"{uid}: empty tag")
        if not str(it.get("comment", "")).strip():
            errors.append(f"{uid}: empty comment")
        p_md = str(it.get("polished_md", "")).strip()
        if not p_md:
            errors.append(f"{uid}: empty polished_md")
        # 校验原段中的图片路径在润色稿中未丢失
        orig_imgs = IMG_RE.findall(u["orig_md"])
        pol_imgs = IMG_RE.findall(p_md)
        if orig_imgs != pol_imgs:
            errors.append(f"{uid}: image paths changed! orig={orig_imgs}, polished={pol_imgs}")
    return errors


def main() -> None:
    doc_ids = sys.argv[1:]
    if not doc_ids:
        manifest = json.loads((BASE / "manifest.json").read_text(encoding="utf-8"))
        doc_ids = [m["doc_id"] for m in manifest]
    all_err = []
    for did in doc_ids:
        errs = validate_one(did)
        if errs:
            all_err.extend(errs)
        else:
            print(f"[OK] {did}")
    if all_err:
        print("\nERRORS:")
        for e in all_err:
            print(" -", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
