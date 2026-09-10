#!/usr/bin/env python3
"""S3 题目改编流水线：结构审核、血缘记录与报告生成。"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import math
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "02_PROTOTYPE" / "sample" / "lineage.json"
DEFAULT_OUTPUT = ROOT / "03_RECORDS" / "generated"

GATES = [
    ("stage_boundary", "G1 学段边界"),
    ("physics_truth", "G2 物理真值"),
    ("condition_sufficiency", "G3 条件充分"),
    ("answer_design", "G4 答案设计"),
    ("cognitive_requirement", "G5 认知要求"),
    ("copyright", "G6 版权"),
    ("teachability", "G7 可教性"),
]

ALLOWED_SOURCE_KINDS = {
    "self_authored_internal",
    "public_domain",
    "explicitly_licensed",
}
ALLOWED_REVIEW_STATUS = {"pass", "return", "pending_manual"}


@dataclass
class GateResult:
    status: str
    evidence: str


class ValidationError(ValueError):
    pass


def _eval_node(node: ast.AST, variables: dict[str, float]) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, variables)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.Name):
        if node.id not in variables:
            raise ValidationError(f"表达式使用了未登记变量：{node.id}")
        return float(variables[node.id])
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _eval_node(node.operand, variables)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, variables)
        right = _eval_node(node.right, variables)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            if right == 0:
                raise ValidationError("表达式出现除以零")
            return left / right
        if isinstance(node.op, ast.Pow):
            if abs(right) > 8:
                raise ValidationError("指数超出原型允许范围")
            return left**right
    raise ValidationError(f"表达式包含不允许的语法：{type(node).__name__}")


def safe_eval(expression: str, variables: dict[str, float]) -> float:
    """只计算四则运算和小范围乘方，不执行函数或属性访问。"""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValidationError(f"表达式语法错误：{expression}") from exc
    result = _eval_node(tree, variables)
    if not math.isfinite(result):
        raise ValidationError("表达式结果不是有限数")
    return result


def load_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"找不到输入文件：{path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"JSON 无法解析：{exc}") from exc
    validate_lineage(payload)
    return payload


def validate_lineage(payload: dict[str, Any]) -> None:
    questions = payload.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValidationError("questions 必须是非空列表")
    if len(questions) > 10:
        raise ValidationError("试点题目数超过 10")

    question_ids: set[str] = set()
    for question in questions:
        qid = question.get("question_id")
        if not qid or qid in question_ids:
            raise ValidationError(f"题目 ID 缺失或重复：{qid}")
        question_ids.add(qid)
        versions = question.get("versions")
        if not isinstance(versions, list) or not versions:
            raise ValidationError(f"{qid} 没有版本")

        ids: set[str] = set()
        for version in versions:
            vid = version.get("version_id")
            if not vid or vid in ids:
                raise ValidationError(f"{qid} 的版本 ID 缺失或重复：{vid}")
            ids.add(vid)

        roots = 0
        for version in versions:
            parent = version.get("parent_id")
            if parent is None:
                roots += 1
            elif parent not in ids:
                raise ValidationError(
                    f"{version['version_id']} 的父版本 {parent} 不存在"
                )
            if parent == version.get("version_id"):
                raise ValidationError(f"{parent} 不能把自己作为父版本")
        if roots != 1:
            raise ValidationError(f"{qid} 必须且只能有一个原题根版本")

        # 检查循环血缘。
        by_id = {v["version_id"]: v for v in versions}
        for vid in ids:
            seen: set[str] = set()
            cursor: str | None = vid
            while cursor is not None:
                if cursor in seen:
                    raise ValidationError(f"{qid} 存在循环血缘：{vid}")
                seen.add(cursor)
                cursor = by_id[cursor].get("parent_id")


def _declared(version: dict[str, Any], gate: str) -> GateResult:
    item = version.get("declared_reviews", {}).get(gate, {})
    status = item.get("status", "pending_manual")
    if status not in ALLOWED_REVIEW_STATUS:
        return GateResult("return", f"审核状态不合法：{status}")
    reason = item.get("reason", "未填写人工理由")
    return GateResult(status, reason)


def _audit_physics(version: dict[str, Any]) -> GateResult:
    declared = _declared(version, "physics_truth")
    if declared.status != "pass":
        return declared
    checks = version.get("physics_checks", [])
    if not checks:
        return GateResult("pending_manual", "没有数值复算；需要人工物理审查。")

    notes: list[str] = []
    for check in checks:
        try:
            actual = safe_eval(check["expression"], check.get("variables", {}))
            expected = float(check["expected"])
            tolerance = float(check.get("tolerance", 1e-9))
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            return GateResult("return", f"{check.get('check_id', '未命名检查')} 无法复算：{exc}")
        if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance):
            return GateResult(
                "return",
                f"{check['check_id']} 复算为 {actual:g}，登记值为 {expected:g}",
            )
        notes.append(f"{check['check_id']}={actual:g} {check.get('unit', '')}".strip())
    reason = declared.evidence.rstrip("。； ")
    return GateResult("pass", f"{reason}；自动复算：{'；'.join(notes)}。")


def _audit_conditions(version: dict[str, Any]) -> GateResult:
    conditions = version.get("conditions", {})
    required = set(conditions.get("required", []))
    present = set(conditions.get("present", []))
    if not required:
        return GateResult("return", "没有登记得出结论所需的条件。")
    missing = sorted(required - present)
    if missing:
        return GateResult("return", f"题面缺少：{'、'.join(missing)}。")
    return GateResult("pass", f"{len(required)} 项必要条件均已在题面或约定中出现。")


def _audit_answer(version: dict[str, Any]) -> GateResult:
    answer = version.get("answer_design", {})
    mode = answer.get("mode")
    scoring = answer.get("scoring_points", [])
    if mode == "unique":
        if not answer.get("expected_answer"):
            return GateResult("return", "唯一答案题没有登记预期答案。")
        if not scoring:
            return GateResult("return", "唯一答案题没有评分点。")
        methods = answer.get("acceptable_methods", [])
        if len(methods) > 1 and not answer.get("method_fixed", False):
            return GateResult("return", "允许多种估算方法却标为唯一答案，且未固定方法或误差。")
        return GateResult("pass", "唯一答案、方法约定和评分点结构一致。")
    if mode == "open":
        criteria = answer.get("criteria", [])
        if not answer.get("acceptable_answer_space"):
            return GateResult("return", "开放题没有说明可接受的答案空间。")
        if len(criteria) < 2:
            return GateResult("return", "开放题至少需要两项共同评价标准。")
        return GateResult("pass", f"开放答案受 {len(criteria)} 项共同标准约束。")
    if mode == "mixed":
        unique_parts = answer.get("unique_parts", [])
        open_parts = answer.get("open_parts", [])
        if not unique_parts or not open_parts:
            return GateResult("return", "混合题必须同时登记唯一答案小问和开放答案小问。")
        for part in unique_parts:
            if not part.get("expected_answer") or not part.get("scoring_points"):
                return GateResult("return", f"{part.get('part', '未编号小问')} 缺唯一答案或评分点。")
        for part in open_parts:
            if not part.get("acceptable_answer_space") or len(part.get("criteria", [])) < 2:
                return GateResult("return", f"{part.get('part', '未编号小问')} 缺答案空间或共同标准。")
        return GateResult(
            "pass",
            f"混合题含 {len(unique_parts)} 个唯一答案小问和 {len(open_parts)} 个有界开放小问。",
        )
    return GateResult("return", "答案模式必须是 unique、open 或 mixed。")


def _audit_cognition(version: dict[str, Any]) -> GateResult:
    cognition = version.get("cognition", {})
    required = set(cognition.get("required_action_tags", []))
    actual = set(cognition.get("task_action_tags", []))
    if not required:
        return GateResult("return", "没有把认知目标改写为可观察的学生动作。")
    missing = sorted(required - actual)
    if missing:
        return GateResult(
            "return",
            f"目标为“{cognition.get('target_level', '未填')}”，但题面没有要求：{'、'.join(missing)}。",
        )
    return GateResult("pass", f"题面动作覆盖目标动作：{'、'.join(sorted(required))}。")


def _audit_copyright(question: dict[str, Any], version: dict[str, Any]) -> GateResult:
    declared = _declared(version, "copyright")
    if declared.status != "pass":
        return declared
    origin = question.get("origin", {})
    kind = origin.get("source_kind")
    if kind not in ALLOWED_SOURCE_KINDS:
        return GateResult("return", f"来源类型不在允许清单：{kind}")
    if origin.get("third_party_text_used") and kind != "explicitly_licensed":
        return GateResult("return", "含第三方题干，但未登记明确授权。")
    if not origin.get("authorization"):
        return GateResult("return", "没有登记使用／改编授权范围。")
    reason = declared.evidence.rstrip("。； ")
    return GateResult("pass", f"{reason}；来源类型：{kind}。")


def _audit_teachability(version: dict[str, Any]) -> GateResult:
    declared = _declared(version, "teachability")
    if declared.status != "pass":
        return declared
    item = version.get("teachability", {})
    minutes = item.get("estimated_minutes")
    if not isinstance(minutes, (int, float)) or minutes <= 0:
        return GateResult("return", "没有可用的课堂用时估计。")
    if minutes > 20:
        return GateResult("return", f"预计 {minutes:g} 分钟，超出本试点 20 分钟上限。")
    if item.get("safety_issue"):
        return GateResult("return", "存在尚未解决的安全问题。")
    if not isinstance(item.get("materials", []), list):
        return GateResult("return", "材料字段必须是列表。")
    reason = declared.evidence.rstrip("。； ")
    if reason.startswith("预计"):
        return GateResult("pass", f"{reason}。")
    return GateResult("pass", f"预计 {minutes:g} 分钟；{reason}。")


def audit_version(question: dict[str, Any], version: dict[str, Any]) -> dict[str, Any]:
    stage = _declared(version, "stage_boundary")
    if not question.get("stage_reference", {}).get("concepts"):
        stage = GateResult("return", "没有学段概念依据。")

    gates = {
        "stage_boundary": stage,
        "physics_truth": _audit_physics(version),
        "condition_sufficiency": _audit_conditions(version),
        "answer_design": _audit_answer(version),
        "cognitive_requirement": _audit_cognition(version),
        "copyright": _audit_copyright(question, version),
        "teachability": _audit_teachability(version),
    }

    teacher_status = version.get("teacher_decision", {}).get("status", "")
    has_return = any(item.status == "return" for item in gates.values())
    has_pending = any(item.status == "pending_manual" for item in gates.values())
    if teacher_status == "rejected":
        disposition = "否决"
    elif has_return:
        disposition = "退回"
    elif has_pending:
        disposition = "待人工确认"
    elif teacher_status == "baseline":
        disposition = "基线"
    elif teacher_status == "returned":
        disposition = "退回"
    elif teacher_status == "provisional_final":
        disposition = "内部试点定稿"
    else:
        disposition = "可审核候选"

    return {
        "version": version,
        "gates": gates,
        "disposition": disposition,
        "teacher_status": teacher_status,
    }


def audit_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for question in payload["questions"]:
        for version in question["versions"]:
            result = audit_version(question, version)
            result["question"] = question
            rows.append(result)
    return rows


def _status_cn(status: str) -> str:
    return {"pass": "通过", "return": "退回", "pending_manual": "待人工确认"}.get(status, status)


def write_markdown(payload: dict[str, Any], rows: list[dict[str, Any]], path: Path) -> None:
    lines = [
        "# S3 自动审核报告",
        "",
        "> 本报告检查记录结构、血缘和已登记的数值一致性，不替代命题审读、版权裁决和课堂试测。",
        "",
        "## 总览",
        "",
        f"- 原题数量：{len(payload['questions'])}（上限 10）",
        f"- 版本数量：{len(rows)}",
        f"- 生成依据：`{payload.get('project_id', '未登记')}` / schema {payload.get('schema_version', '未登记')}",
        "",
        "| 版本 | 父版本 | 角色 | 主要变化 | 流水线处置 | 教师处置 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        version = row["version"]
        change_types = "、".join(item.get("type", "未分类") for item in version.get("changes", [])) or "原题"
        lines.append(
            f"| {version['version_id']} | {version.get('parent_id') or '—'} | {version.get('role', '')} | {change_types} | {row['disposition']} | {version.get('teacher_decision', {}).get('status', '未填')} |"
        )

    lines.extend(["", "## 逐版本记录", ""])
    for row in rows:
        version = row["version"]
        lines.extend(
            [
                f"### {version['version_id']} · {row['disposition']}",
                "",
                f"**题面**：{version.get('question_text', '未填写')}",
                "",
                "**版本变化**：",
                "",
            ]
        )
        if version.get("changes"):
            for change in version["changes"]:
                lines.append(
                    f"- `{change.get('type', '未分类')}`：{change.get('before', '—')} → {change.get('after', '—')}；理由：{change.get('reason', '未填')}；风险：{change.get('risk', '未填')}"
                )
        else:
            lines.append("- 原题基线，无改动。")
        lines.extend(
            [
                "",
                "| 审核门 | 状态 | 证据或退回理由 |",
                "| --- | --- | --- |",
            ]
        )
        for gate_id, gate_name in GATES:
            gate = row["gates"][gate_id]
            lines.append(f"| {gate_name} | {_status_cn(gate.status)} | {gate.evidence} |")
        decision = version.get("teacher_decision", {})
        lines.extend(
            [
                "",
                f"**教师处置记录**：`{decision.get('status', '未填')}`。{decision.get('reason', '未填写理由')}",
                "",
            ]
        )

    question = payload["questions"][0]
    ref = question.get("stage_reference", {})
    lines.extend(
        [
            "## 来源与边界",
            "",
            f"- 题目来源：{question.get('origin', {}).get('note', '未登记')} ",
            f"- 教材核对：`{ref.get('local_source', '未登记')}`，只用于确认 {', '.join(ref.get('concepts', []))} 的学段边界。",
            "- 外部培训材料只提供问题和流程启发；没有导入题库、复写专家案例或采用登录题库做法。",
            "- Q001-C03 是内部试点定稿，仍待作者和另一位高中物理教师审读，未做课堂试测。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["question_id", "version_id", "parent_id", "gate", "status", "evidence", "disposition"])
        for row in rows:
            version = row["version"]
            for gate_id, gate_name in GATES:
                gate = row["gates"][gate_id]
                writer.writerow(
                    [
                        row["question"]["question_id"],
                        version["version_id"],
                        version.get("parent_id") or "",
                        gate_name,
                        _status_cn(gate.status),
                        gate.evidence,
                        row["disposition"],
                    ]
                )


def write_lineage_svg(rows: list[dict[str, Any]], path: Path) -> None:
    width, height = 940, 330
    box_w, box_h, x0, y0 = 205, 84, 35, 64
    colors = {
        "基线": "#dbeafe",
        "否决": "#fee2e2",
        "退回": "#fef3c7",
        "内部试点定稿": "#dcfce7",
        "待人工确认": "#e9d5ff",
    }
    items: list[str] = []
    by_id = {row["version"]["version_id"]: row for row in rows}
    depths: dict[str, int] = {}

    def depth_of(version_id: str) -> int:
        if version_id in depths:
            return depths[version_id]
        parent = by_id[version_id]["version"].get("parent_id")
        depths[version_id] = 0 if parent is None else depth_of(parent) + 1
        return depths[version_id]

    for version_id in by_id:
        depth_of(version_id)
    levels: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        levels.setdefault(depths[row["version"]["version_id"]], []).append(row)

    positions: dict[str, tuple[float, float]] = {}
    max_depth = max(levels)
    for level, level_rows in levels.items():
        x = x0 + level * ((width - 2 * x0 - box_w) / max(1, max_depth))
        if len(level_rows) == 1:
            ys = [(height - box_h) / 2]
        else:
            usable = height - 2 * y0 - box_h
            ys = [y0 + index * (usable / (len(level_rows) - 1)) for index in range(len(level_rows))]
        for row, y in zip(level_rows, ys):
            positions[row["version"]["version_id"]] = (x, y)

    # 先画真实父子连线，再画节点，避免把并列候选误画成顺序版本。
    for row in rows:
        version = row["version"]
        parent = version.get("parent_id")
        if parent is None:
            continue
        parent_x, parent_y = positions[parent]
        x, y = positions[version["version_id"]]
        start_x, start_y = parent_x + box_w, parent_y + box_h / 2
        end_x, end_y = x - 8, y + box_h / 2
        control = (start_x + end_x) / 2
        items.append(
            f'<path d="M {start_x} {start_y} C {control} {start_y}, {control} {end_y}, {end_x} {end_y}" fill="none" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)"/>'
        )

    for row in rows:
        version = row["version"]
        x, y = positions[version["version_id"]]
        version = row["version"]
        color = colors.get(row["disposition"], "#f3f4f6")
        items.append(f'<rect x="{x}" y="{y}" width="{box_w}" height="{box_h}" rx="12" fill="{color}" stroke="#334155"/>')
        items.append(f'<text x="{x + 14}" y="{y + 28}" font-size="17" font-weight="700">{escape(version["version_id"])}</text>')
        items.append(f'<text x="{x + 14}" y="{y + 55}" font-size="15">{escape(row["disposition"])}</text>')
        items.append(f'<text x="{x + 14}" y="{y + 76}" font-size="12">父：{escape(version.get("parent_id") or "—")}</text>')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill="#64748b"/></marker></defs>
<rect width="100%" height="100%" fill="#ffffff"/>
<text x="35" y="30" font-size="20" font-weight="700" fill="#0f172a">Q001 版本谱系</text>
{''.join(items)}
<text x="35" y="310" font-size="13" fill="#475569">并列候选共享同一父版本；否决和退回版本保留，不被最终版本覆盖。</text>
</svg>'''
    path.write_text(svg, encoding="utf-8")


def write_vt_svg(rows: list[dict[str, Any]], path: Path) -> None:
    target = next(
        (
            row["version"]
            for row in rows
            if row["version"].get("teacher_decision", {}).get("status") == "provisional_final"
            and row["version"].get("data_table")
        ),
        None,
    )
    if target is None:
        return
    data = target["data_table"]
    width, height = 640, 410
    left, right, top, bottom = 72, 32, 42, 62
    plot_w, plot_h = width - left - right, height - top - bottom
    max_t = max(float(p["t"]) for p in data)
    max_v = max(float(p["v"]) for p in data)

    def px(t: float) -> float:
        return left + (t / max_t) * plot_w

    def py(v: float) -> float:
        return top + plot_h - (v / max_v) * plot_h

    grid = []
    for i in range(int(max_t) + 1):
        x = px(i)
        grid.append(f'<line x1="{x}" y1="{top}" x2="{x}" y2="{top + plot_h}" stroke="#e2e8f0"/>')
        grid.append(f'<text x="{x}" y="{top + plot_h + 25}" text-anchor="middle" font-size="13">{i}</text>')
    for v in range(0, int(max_v) + 1, 3):
        y = py(v)
        grid.append(f'<line x1="{left}" y1="{y}" x2="{left + plot_w}" y2="{y}" stroke="#e2e8f0"/>')
        grid.append(f'<text x="{left - 12}" y="{y + 4}" text-anchor="end" font-size="13">{v}</text>')
    points = " ".join(f"{px(float(p['t']))},{py(float(p['v']))}" for p in data)
    dots = "".join(
        f'<circle cx="{px(float(p["t"]))}" cy="{py(float(p["v"]))}" r="5" fill="#2563eb"/>'
        for p in data
    )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="#ffffff"/>
<text x="{left}" y="26" font-size="19" font-weight="700" fill="#0f172a">Q001-C03 教师审核参考图（非学生作答）</text>
{''.join(grid)}
<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#0f172a" stroke-width="2"/>
<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#0f172a" stroke-width="2"/>
<polyline points="{points}" fill="none" stroke="#2563eb" stroke-width="3"/>
{dots}
<text x="{left + plot_w/2}" y="{height - 18}" text-anchor="middle" font-size="15">t / s</text>
<text x="18" y="{top + plot_h/2}" text-anchor="middle" font-size="15" transform="rotate(-90 18 {top + plot_h/2})">v / (m·s⁻¹)</text>
</svg>'''
    path.write_text(svg, encoding="utf-8")


STRATEGIES = {
    "situation": {
        "change_type": "situation",
        "prompt": "把物理对象放入确有使用意义的情境，不改变必要条件。",
        "review_focus": ["情境是否影响学生决策", "学生动作是否真的变化", "是否新增无关文字"],
    },
    "question_chain": {
        "change_type": "question_chain",
        "prompt": "让前一问的结果或证据成为后一问的条件，避免并列小问。",
        "review_focus": ["问题间是否有证据依赖", "任一小问是否可以删除", "评分点能否观察推理链"],
    },
    "data_image": {
        "change_type": "data_image",
        "prompt": "提供可解释的数据并要求学生选择或制作合适表征。",
        "review_focus": ["数据含义与精度", "图像坐标和单位", "趋势判断的证据", "估算方法和误差范围"],
    },
    "open_task": {
        "change_type": "open_task",
        "prompt": "开放方案或结论，同时给出共同约束、证据要求和评分标准。",
        "review_focus": ["开放的是选择空间还是遗漏条件", "可接受答案空间", "共同评价标准", "课堂评分负担"],
    },
}


def propose(payload: dict[str, Any], question_id: str, parent_id: str, strategy: str) -> dict[str, Any]:
    question = next((q for q in payload["questions"] if q["question_id"] == question_id), None)
    if question is None:
        raise ValidationError(f"找不到题目：{question_id}")
    parent = next((v for v in question["versions"] if v["version_id"] == parent_id), None)
    if parent is None:
        raise ValidationError(f"找不到父版本：{parent_id}")
    spec = STRATEGIES[strategy]
    return {
        "parent_id": parent_id,
        "strategy": strategy,
        "change_type": spec["change_type"],
        "generation_brief": spec["prompt"],
        "source_intent": parent.get("cognition", {}),
        "candidate_question_text": "待教师填写；不要在未复核条件和答案前直接定稿。",
        "must_record": ["变化前后", "改编理由", "预期学生动作", "可能破坏的条件", "退回或采用决定"],
        "review_focus": spec["review_focus"],
    }


def run_audit(input_path: Path, output_dir: Path) -> int:
    payload = load_payload(input_path)
    rows = audit_payload(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_markdown(payload, rows, output_dir / "audit_report.md")
    write_csv(rows, output_dir / "audit_ledger.csv")
    write_lineage_svg(rows, output_dir / "lineage.svg")
    write_vt_svg(rows, output_dir / "Q001-C03-vt-reference.svg")
    dispositions: dict[str, int] = {}
    for row in rows:
        dispositions[row["disposition"]] = dispositions.get(row["disposition"], 0) + 1
    print(f"审核完成：{len(payload['questions'])} 道原题，{len(rows)} 个版本。")
    print("处置：" + "，".join(f"{key} {value}" for key, value in dispositions.items()))
    print(f"输出：{output_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="S3 题目改编流水线")
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit", help="审核血缘和七道门，生成报告")
    audit.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    audit.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    draft = sub.add_parser("propose", help="生成候选工作单，不改原文件")
    draft.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    draft.add_argument("--question", required=True)
    draft.add_argument("--parent", required=True)
    draft.add_argument("--strategy", choices=sorted(STRATEGIES), required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "audit":
            return run_audit(args.input, args.output)
        payload = load_payload(args.input)
        print(json.dumps(propose(payload, args.question, args.parent, args.strategy), ensure_ascii=False, indent=2))
        return 0
    except ValidationError as exc:
        print(f"错误：{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
