#!/usr/bin/env python3
"""检查代表性提示词是否覆盖技能的主要路由与负向边界。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_IDS = {f"T{i:02d}" for i in range(1, 9)}
REQUIRED_ROUTES = {
    "core:A", "core:B", "core:C", "core:D", "core:E", "core:F",
    "reject-theme-drift", "reject-imitation",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("test_file", type=Path)
    args = parser.parse_args()
    tests = json.loads(args.test_file.read_text(encoding="utf-8"))
    ids = {item.get("id") for item in tests}
    routes = {route for item in tests for route in item.get("route", [])}
    issues = []
    if len(tests) < 8:
        issues.append("代表性提示词少于8个")
    missing_ids = sorted(REQUIRED_IDS - ids)
    if missing_ids:
        issues.append(f"缺少测试ID：{', '.join(missing_ids)}")
    missing_routes = sorted(REQUIRED_ROUTES - routes)
    if missing_routes:
        issues.append(f"缺少关键路由：{', '.join(missing_routes)}")
    for item in tests:
        for field in ("id", "task", "route", "must_include", "must_not"):
            if not item.get(field):
                issues.append(f"{item.get('id', '未知ID')} 缺少 {field}")
    payload = {
        "tests": len(tests),
        "routes": sorted(routes),
        "issues": issues,
        "ready": not issues,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
