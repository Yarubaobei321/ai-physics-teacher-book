#!/usr/bin/env python3
"""运行步步高正式资料库转换和结构化流水线。

命令行默认仅处理一个来源，避免误触发全库批处理。需要批量执行时可明确提供
``--limit`` 和 ``--workers``。每个来源的跳过依据均为 source hash、Markdown hash 和
成功阶段日志，所有阶段只写正式资料库输出目录。
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
from pathlib import Path
from typing import Any, Callable


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from convert_sources import CommandRunner, convert_source  # noqa: E402
from library_common import (  # noqa: E402
    LIBRARY_ROOT,
    PROFILES,
    PipelineError,
    read_json,
    json_bytes,
    official_library_root,
    remove_generated_file,
    safe_library_root,
    safe_output_path,
    source_short_for,
    write_json,
)
from source_state import SourceStateError, read_source_manifest, update_source_state  # noqa: E402
from structure_records import build_association_reports, structure_source  # noqa: E402


PIPELINE_REPORT_PATH = "reports/pipeline-last-run.json"


def _unique_issues(values: list[str]) -> list[str]:
    seen: set[str] = set()
    return [value for value in values if value and not (value in seen or seen.add(value))]


def _phase_report(root: Path, source_id: str, phase: str) -> dict[str, Any] | None:
    short_id = source_short_for(source_id)
    relative_path = f"reports/{phase}/{short_id}.json"
    try:
        return read_json(root / relative_path)
    except OSError:
        return None


def _source_output_paths(source_id: str, conversion: dict[str, Any] | None, structure: dict[str, Any] | None) -> dict[str, str]:
    """由成功阶段报告重建来源的全部可追溯输出路径。"""
    paths: dict[str, str] = {}
    for prefix, report in (("conversion", conversion), ("structure", structure)):
        if not report:
            continue
        report_paths = report.get("paths")
        if isinstance(report_paths, dict):
            for key, value in report_paths.items():
                if isinstance(key, str) and isinstance(value, str):
                    paths[f"{prefix}_{key}"] = value
    if conversion:
        assets = conversion.get("asset_paths")
        if isinstance(assets, list):
            for index, path in enumerate(assets, start=1):
                if isinstance(path, str):
                    paths[f"asset_{index:03d}"] = path
    if structure:
        for group, values in (("question", structure.get("question_paths")), ("knowledge", structure.get("knowledge_paths"))):
            if isinstance(values, list):
                for index, path in enumerate(values, start=1):
                    if isinstance(path, str):
                        paths[f"{group}_{index:03d}"] = path
    return paths


def _advance_source_state(
    root: Path, source: dict[str, Any], result: dict[str, Any]
) -> list[str]:
    """在主线程串行写回来源状态，避免 worker 竞争覆盖 sources.jsonl。"""
    source_id = str(source.get("id", ""))
    source_sha256 = str(source.get("sha256", ""))
    conversion = _phase_report(root, source_id, "conversion")
    structure = _phase_report(root, source_id, "structure")
    issues = _unique_issues(
        [
            *[str(item) for item in result.get("issues", []) if isinstance(item, str)],
            *[str(item) for item in (conversion or {}).get("issues", []) if isinstance(item, str)],
            *[str(item) for item in (structure or {}).get("issues", []) if isinstance(item, str)],
        ]
    )
    try:
        current_records = read_source_manifest(root)
        current = next(record for record in current_records if record["id"] == source_id)
        current_status = str(current["status"])
        if not result.get("success"):
            update_source_state(
                root,
                source_id,
                status="blocked",
                output_paths=_source_output_paths(source_id, conversion, structure),
                exceptions=issues or ["流水线阶段失败，详见转换或结构化报告"],
                tool_versions=(conversion or {}).get("tool_versions", {}),
                expected_sha256=source_sha256,
            )
            return []

        # 转换阶段已成功时先至少抵达 raw_extracted。即便该文档随后需要人工复核，
        # source_state 的合法状态机仍要求经过这一中间状态。
        has_converted_output = conversion is not None and conversion.get("status") == "success"
        if has_converted_output and current_status in {"discovered", "blocked"}:
            current = update_source_state(
                root,
                source_id,
                status="raw_extracted",
                output_paths=_source_output_paths(source_id, conversion, None),
                exceptions=issues,
                tool_versions=conversion.get("tool_versions", {}),
                expected_sha256=source_sha256,
            )
            current_status = str(current["status"])
        elif has_converted_output:
            current = update_source_state(
                root,
                source_id,
                output_paths=_source_output_paths(source_id, conversion, structure),
                exceptions=issues,
                tool_versions=conversion.get("tool_versions", {}),
                expected_sha256=source_sha256,
            )
            current_status = str(current["status"])

        has_structured_output = structure is not None and structure.get("status") == "success"
        if has_structured_output and not has_converted_output and current_status in {"discovered", "blocked"}:
            current = update_source_state(
                root,
                source_id,
                status="raw_extracted",
                output_paths=_source_output_paths(source_id, conversion, structure),
                exceptions=issues,
                tool_versions=current.get("tool_versions", {}),
                expected_sha256=source_sha256,
            )
            current_status = str(current["status"])
        if has_structured_output and current_status == "raw_extracted":
            current = update_source_state(
                root,
                source_id,
                status="ai_structured",
                output_paths=_source_output_paths(source_id, conversion, structure),
                exceptions=issues,
                tool_versions=(conversion or {}).get("tool_versions", current.get("tool_versions", {})),
                expected_sha256=source_sha256,
            )
            current_status = str(current["status"])
        elif has_structured_output:
            current = update_source_state(
                root,
                source_id,
                output_paths=_source_output_paths(source_id, conversion, structure),
                exceptions=issues,
                tool_versions=(conversion or {}).get("tool_versions", current.get("tool_versions", {})),
                expected_sha256=source_sha256,
            )
            current_status = str(current["status"])

        needs_manual_review = bool(issues)
        if has_structured_output and needs_manual_review and current_status == "ai_structured":
            update_source_state(
                root,
                source_id,
                status="pending_manual_review",
                output_paths=_source_output_paths(source_id, conversion, structure),
                exceptions=issues,
                tool_versions=(conversion or {}).get("tool_versions", current.get("tool_versions", {})),
                expected_sha256=source_sha256,
            )
        return []
    except (StopIteration, SourceStateError, PipelineError, ValueError, OSError) as error:
        return [f"来源状态未写回：{error}"]


def _synchronise_source_states(
    root: Path, selected: list[dict[str, Any]], results: list[dict[str, Any]]
) -> None:
    """在所有 worker 结束后按选择顺序串行写回 manifest，禁止并发写 JSONL。"""
    for source, result in zip(selected, results):
        state_errors = _advance_source_state(root, source, result)
        if state_errors:
            result["issues"] = _unique_issues([*result.get("issues", []), *state_errors])
            result["success"] = False
            result["skipped"] = False


def _source_asset_candidates(root: Path, source_id: str) -> list[str]:
    """枚举一个来源专属资产目录中的普通文件，供显式 reset 使用。

    失败可能发生在转换日志写入前；此时日志无法列出已抽取的媒体。资产目录本身由
    完整 source ID 命名，是唯一额外可安全推断的归属边界。只读取两个固定目录的
    第一层普通文件，跳过目录和任何符号链接，既不会递归扩大范围，也不会触碰 raw。
    """
    candidates: list[str] = []
    for prefix in ("assets/original", "assets/derived"):
        relative_directory = f"{prefix}/{source_id}"
        try:
            # 通过安全输出解析器验证所有父路径均为资料库内普通目录，且不创建目录。
            probe = safe_output_path(root, f"{relative_directory}/.reset-probe", create_parent=False)
        except PipelineError:
            continue
        directory = probe.parent
        try:
            children = list(directory.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_symlink() or not child.is_file():
                continue
            try:
                relative_path = child.relative_to(root).as_posix()
                # 再经输出边界验证，避免目录竞态或异常路径对象扩大删除范围。
                safe_output_path(root, relative_path, create_parent=False)
            except (OSError, PipelineError, ValueError):
                continue
            candidates.append(relative_path)
    return candidates


def reset_source_generated_outputs(library_root: Path | str, source: dict[str, Any]) -> list[str]:
    """移除单一来源的流水线输出，并把该来源状态安全重置为 discovered。

    只接受由该 source ID 派生的 document、转换/结构化报告，以及这些报告实际列出的
    questions/knowledge。为覆盖“媒体已抽取但转换在写报告前中断”的情形，另只删除
    ``assets/{original,derived}/<完整 source ID>/`` 第一层的普通文件；每个 JSON 删除
    前再次验证其 source 归属。因此该函数可用于清理试运行样本，不能扩大到 raw、
    他人来源或整个目录。
    """
    root = safe_library_root(library_root)
    source_id = str(source.get("id", ""))
    source_sha256 = str(source.get("sha256", ""))
    short_id = source_short_for(source_id)
    conversion = _phase_report(root, source_id, "conversion")
    structure = _phase_report(root, source_id, "structure")
    candidates: list[str] = [
        f"records/documents/doc.bbg.{short_id}.md",
        f"records/documents/doc.bbg.{short_id}.json",
        f"reports/conversion/{short_id}.json",
        f"reports/structure/{short_id}.json",
    ]
    for report in (conversion, structure):
        if not report or report.get("source_id") != source_id:
            continue
        for key in ("asset_paths", "question_paths", "knowledge_paths"):
            values = report.get(key)
            if isinstance(values, list):
                candidates.extend(value for value in values if isinstance(value, str))
    candidates.extend(_source_asset_candidates(root, source_id))
    removed: list[str] = []
    for relative_path in sorted(set(candidates), reverse=True):
        if not isinstance(relative_path, str):
            continue
        if relative_path.startswith("questions/"):
            record = read_json(root / relative_path)
            if not record or record.get("source_id") != source_id:
                continue
        elif relative_path.startswith("knowledge/"):
            record = read_json(root / relative_path)
            if not record or source_id not in record.get("source_ids", []):
                continue
        elif relative_path.startswith("records/documents/") and relative_path.endswith(".json"):
            record = read_json(root / relative_path)
            if record is not None and record.get("source_id") != source_id:
                continue
        try:
            if remove_generated_file(root, relative_path):
                removed.append(relative_path)
        except PipelineError:
            continue
    try:
        current = next(record for record in read_source_manifest(root) if record["id"] == source_id)
        # source_state 的正常流转不允许直接回退。先带着清理原因安全转入 blocked，
        # 再利用 blocked 的受控恢复路径回到 discovered，最终不保留任何试运行状态。
        if current["status"] != "discovered":
            current = update_source_state(
                root,
                source_id,
                status="blocked",
                output_paths={},
                exceptions=["试运行生成物已按来源范围安全清理，状态待重新处理"],
                tool_versions={},
                expected_sha256=source_sha256,
            )
        update_source_state(
            root,
            source_id,
            status="discovered",
            output_paths={},
            exceptions=[],
            tool_versions={},
            expected_sha256=source_sha256,
        )
    except (StopIteration, SourceStateError) as error:
        raise PipelineError(f"无法重置来源状态：{error}") from error
    return sorted(removed)


def load_sources(library_root: Path | str) -> list[dict[str, Any]]:
    """读取 sources.jsonl，不写入来源清单或 raw 目录。"""
    root = safe_library_root(library_root)
    manifest = root / "sources" / "sources.jsonl"
    if not manifest.is_file() or manifest.is_symlink():
        raise PipelineError("缺少普通文件 sources/sources.jsonl")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise PipelineError(f"sources.jsonl 第 {line_number} 行无效：{error.msg}") from error
        if not isinstance(value, dict):
            raise PipelineError(f"sources.jsonl 第 {line_number} 行必须是对象")
        records.append(value)
    return sorted(records, key=lambda record: (str(record.get("relative_path", "")), str(record.get("id", ""))))


def select_sources(
    sources: list[dict[str, Any]],
    *,
    profile: str | None = None,
    source_id: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """按 CLI 条件稳定筛选来源，limit 在筛选之后生效。"""
    if profile is not None and profile not in PROFILES:
        raise ValueError(f"profile 必须是 {', '.join(sorted(PROFILES))} 之一")
    if limit is not None and (not isinstance(limit, int) or isinstance(limit, bool) or limit < 1):
        raise ValueError("limit 必须是大于零的整数或 None")
    selected = [
        source
        for source in sources
        if (profile is None or source.get("profile") == profile)
        and (source_id is None or source.get("id") == source_id)
    ]
    return selected[:limit] if limit is not None else selected


def process_source_worker(task: dict[str, Any]) -> dict[str, Any]:
    """可测试的单来源 worker；任务字典也可交给线程池并发执行。"""
    root = Path(task["library_root"])
    source = task["source"]
    force = bool(task.get("force", False))
    structure_only = bool(task.get("structure_only", False))
    command_runner: CommandRunner | None = task.get("command_runner")
    source_id = source.get("id") if isinstance(source, dict) else None
    phases: dict[str, dict[str, Any]] = {}
    issues: list[str] = []
    if structure_only:
        structured = structure_source(root, source, force=force)
        phases["structure"] = structured
        issues.extend(structured.get("issues", []))
        return {
            "source_id": source_id,
            "success": bool(structured.get("success")),
            "skipped": bool(structured.get("success") and structured.get("skipped")),
            "phases": phases,
            "issues": _unique_issues(issues),
        }

    converted = convert_source(root, source, force=force, command_runner=command_runner)
    phases["convert"] = converted
    issues.extend(converted.get("issues", []))
    if not converted.get("success"):
        return {
            "source_id": source_id,
            "success": False,
            "skipped": False,
            "phases": phases,
            "issues": _unique_issues(issues),
        }
    structured = structure_source(root, source, force=force)
    phases["structure"] = structured
    issues.extend(structured.get("issues", []))
    successful = bool(structured.get("success"))
    skipped = bool(successful and converted.get("skipped") and structured.get("skipped"))
    return {
        "source_id": source_id,
        "success": successful,
        "skipped": skipped,
        "phases": phases,
        "issues": _unique_issues(issues),
    }


def run_pipeline(
    library_root: Path | str = LIBRARY_ROOT,
    *,
    profile: str | None = None,
    source_id: str | None = None,
    limit: int | None = None,
    workers: int = 1,
    force: bool = False,
    structure_only: bool = False,
    command_runner: CommandRunner | None = None,
) -> dict[str, Any]:
    """执行所选来源，写入一份包含实际 processed/skipped/failed/issue counts 的报告。"""
    root = safe_library_root(library_root)
    if not isinstance(workers, int) or isinstance(workers, bool) or workers < 1:
        raise ValueError("workers 必须是大于零的整数")
    selected = select_sources(load_sources(root), profile=profile, source_id=source_id, limit=limit)
    tasks = [
        {
            "library_root": str(root),
            "source": source,
            "force": force,
            "structure_only": structure_only,
            "command_runner": command_runner,
        }
        for source in selected
    ]
    results_by_index: dict[int, dict[str, Any]] = {}
    if workers == 1 or len(tasks) <= 1:
        for index, task in enumerate(tasks):
            results_by_index[index] = process_source_worker(task)
    else:
        # 线程共享同一受控根；各 source 的文件名由 hash 派生，互不覆盖。
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(process_source_worker, task): index for index, task in enumerate(tasks)}
            for future in concurrent.futures.as_completed(futures):
                index = futures[future]
                try:
                    results_by_index[index] = future.result()
                except BaseException as error:  # 防止单个来源异常中断其他来源。
                    results_by_index[index] = {
                        "source_id": selected[index].get("id"),
                        "success": False,
                        "skipped": False,
                        "phases": {},
                        "issues": [f"worker 未捕获异常：{error}"],
                    }
    results = [results_by_index[index] for index in range(len(tasks))]
    _synchronise_source_states(root, selected, results)
    association_paths: list[str] = []
    association_issues: list[str] = []
    try:
        # 关联报告独立于转换结果，且仅读取清单与声明式配置；不触发额外 Word 转换。
        association_paths = build_association_reports(root, load_sources(root))
    except (PipelineError, OSError, ValueError) as error:
        association_issues.append(f"资料包关联报告未写入：{error}")
    failed = sum(1 for result in results if not result["success"])
    skipped = sum(1 for result in results if result["success"] and result["skipped"])
    processed = len(results) - failed - skipped
    issue_count = sum(len(result["issues"]) for result in results) + len(association_issues)
    report = {
        "status": "success" if failed == 0 else "partial_failure",
        "scope": {
            "profile": profile,
            "source_id": source_id,
            "limit": limit,
            "workers": workers,
            "force": force,
            "structure_only": structure_only,
        },
        "selected": len(selected),
        "processed": processed,
        "skipped": skipped,
        "failed": failed,
        "issue_count": issue_count,
        "results": results,
        "association_paths": association_paths,
        "association_issues": association_issues,
    }
    write_json(root, PIPELINE_REPORT_PATH, report)
    return report


def _positive_integer(value: str) -> int:
    try:
        result = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("必须是正整数") from error
    if result < 1:
        raise argparse.ArgumentTypeError("必须是正整数")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="运行步步高正式资料库的安全转换和结构化流水线")
    parser.add_argument("--profile", choices=sorted(PROFILES), help="只处理指定来源类型")
    parser.add_argument("--source-id", help="只处理指定 src.bbg.* 来源")
    parser.add_argument("--limit", type=_positive_integer, default=1, help="最多处理的来源数；默认 1")
    parser.add_argument("--workers", type=_positive_integer, default=1, help="并发 worker 数，默认 1")
    parser.add_argument("--force", action="store_true", help="忽略成功阶段的断点记录，重新生成输出")
    parser.add_argument("--structure-only", action="store_true", help="跳过 Word 转换，只结构化现有 Markdown")
    args = parser.parse_args(argv)
    try:
        root = official_library_root()
        report = run_pipeline(
            root,
            profile=args.profile,
            source_id=args.source_id,
            limit=args.limit,
            workers=args.workers,
            force=args.force,
            structure_only=args.structure_only,
        )
    except (OSError, PipelineError, ValueError) as error:
        print(f"流水线启动失败：{error}", file=sys.stderr)
        return 1
    print(json_bytes(report).decode("utf-8"), end="")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
