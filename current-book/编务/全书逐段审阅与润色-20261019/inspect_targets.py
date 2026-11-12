#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from pathlib import Path

BASE = Path("/Users/yaril/个人文档/3 写作/图书出版/00_这本书的全部进展/编务/全书逐段审阅与润色-20261019")
manifest = json.loads((BASE / "manifest.json").read_text(encoding="utf-8"))

for doc in manifest:
    doc_id = doc["doc_id"]
    data = json.loads((BASE / "units" / f"{doc_id}.json").read_text(encoding="utf-8"))
    units = data["units"]
    p_count = sum(1 for u in units if u["kind"] == "paragraph")
    c_count = sum(1 for u in units if u["kind"] == "code")
    t_count = sum(1 for u in units if u["kind"] == "table")
    f_count = sum(1 for u in units if u["kind"] == "figure")
    h_count = sum(1 for u in units if u["kind"] == "heading")
    fw_count = sum(1 for u in units if u["kind"] == "framework")
    print(f"{doc_id:12s} | total={len(units):3d} | p={p_count:3d} h={h_count:2d} fig={f_count:2d} tbl={t_count:2d} code={c_count:2d} fw={fw_count:1d} | {doc['title']}")
