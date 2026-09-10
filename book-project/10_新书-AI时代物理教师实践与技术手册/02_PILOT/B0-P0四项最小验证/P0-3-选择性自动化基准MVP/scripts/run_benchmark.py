#!/usr/bin/env python3
"""P0-3 选择性自动化离线基准。

本脚本不调用任何AI模型。它用确定性规则和预设压力测试变体验证：
识别、评分、物理判断、教学解释、最终决定能否分层留痕。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import statistics
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data" / "synthetic_responses.csv"
DEFAULT_RUBRIC = ROOT / "data" / "rubric.json"
DEFAULT_APPEALS = ROOT / "data" / "appeals.csv"
DEFAULT_OUTPUT = ROOT / "outputs"
POLICY_THRESHOLDS = (0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def normalize(text: str) -> str:
    """用于机械比对；保留公式运算符，只去空白和常见标点。"""
    return re.sub(r"[\s，。；、：！？,.!?;:（）()\[\]【】“”‘’]", "", text).lower()


def terms(value: str) -> list[str]:
    return [item.strip() for item in value.split(";") if item.strip()]


def contains(text: str, term: str) -> bool:
    return normalize(term) in normalize(text)


def recognition(reference_text: str, observed_text: str) -> tuple[float, str]:
    ratio = SequenceMatcher(None, normalize(reference_text), normalize(observed_text)).ratio()
    if ratio >= 0.98:
        status = "pass"
    elif ratio >= 0.85:
        status = "degraded"
    else:
        status = "failed"
    return ratio, status


def stable_variant_delta(sample_id: str, run_index: int, uncertain: bool) -> int:
    """用固定哈希生成可复现的压力测试波动，不模拟具体AI模型。"""
    if not uncertain:
        return 0
    digest = hashlib.sha256(f"{sample_id}:{run_index}:p0-3".encode("utf-8")).digest()
    return (-1, 0, 0, 0, 1)[digest[0] % 5]


def score_once(sample: dict[str, str], run_index: int) -> dict[str, Any]:
    observed = sample["observed_text"]
    required = terms(sample["required_terms"])
    forbidden = terms(sample["forbidden_terms"])
    present_required = [item for item in required if contains(observed, item)]
    missing_required = [item for item in required if item not in present_required]
    hit_forbidden = [item for item in forbidden if contains(observed, item)]
    coverage = len(present_required) / len(required) if required else 0.0

    ratio, recognition_status = recognition(sample["reference_response"], observed)
    base_score = round(4 * coverage) if required else 0
    if hit_forbidden:
        base_score = min(base_score, 1)

    uncertain = (
        recognition_status != "pass"
        or bool(missing_required)
        or sample["risk_level"] != "low"
    )
    delta = stable_variant_delta(sample["sample_id"], run_index, uncertain)
    machine_score = max(0, min(4, base_score + delta))

    if hit_forbidden:
        physics_status = "contradiction"
    elif missing_required or recognition_status != "pass":
        physics_status = "uncertain"
    else:
        physics_status = "supported"

    if hit_forbidden:
        teaching_code = "misconception"
    elif missing_required:
        teaching_code = "incomplete_evidence"
    elif recognition_status != "pass":
        teaching_code = "recognition_uncertain"
    else:
        teaching_code = "no_priority_error"

    return {
        "sample_id": sample["sample_id"],
        "run_index": run_index,
        "simulator_variant": f"stress-{run_index}",
        "recognition_ratio": round(ratio, 4),
        "recognition_status": recognition_status,
        "required_coverage": round(coverage, 4),
        "missing_required": " | ".join(missing_required),
        "hit_forbidden": " | ".join(hit_forbidden),
        "machine_score": machine_score,
        "physics_status": physics_status,
        "teaching_code": teaching_code,
    }


def hard_escalation_reasons(
    sample: dict[str, str], first_repeat: dict[str, Any]
) -> list[str]:
    """所有最终分流和阈值曲线共用的不可越过边界。"""
    reasons: list[str] = []
    if first_repeat["physics_status"] == "contradiction":
        reasons.append("physical_contradiction")
    if first_repeat["recognition_status"] != "pass":
        reasons.append("recognition_not_pass")
    if (
        sample["risk_level"] == "high"
        and sample["response_type"] in {"diagram_description", "experiment_report"}
    ):
        reasons.append("high_risk_complex_response")
    return reasons


def aggregate_sample(
    sample: dict[str, str],
    repeats: list[dict[str, Any]],
    rubric: dict[str, Any],
) -> dict[str, Any]:
    scores = [int(row["machine_score"]) for row in repeats]
    median_score = float(statistics.median(scores))
    spread = max(scores) - min(scores)
    first = repeats[0]
    ratio = float(first["recognition_ratio"])
    missing_count = len([x for x in str(first["missing_required"]).split(" | ") if x])

    base_risk = float(rubric["response_type_base_risk"][sample["response_type"]])
    risk = base_risk
    risk += min(0.35, max(0.0, 1.0 - ratio) * 0.8)
    risk += 0.12 if first["physics_status"] == "contradiction" else 0.0
    risk += 0.10 if spread > 0 else 0.0
    risk += min(0.18, missing_count * 0.06)
    risk = round(min(1.0, risk), 4)

    reference_score = float(sample["reference_score"])
    physics_status = str(first["physics_status"])
    teaching_code = str(first["teaching_code"])

    thresholds = rubric["decision_thresholds"]
    # 三条硬升级规则优先于数值阈值。数值看起来低，也不能越过明确冲突、
    # 识别失败或高风险图像／实验报告。这是选择性自动化的核心安全边界。
    hard_reasons = hard_escalation_reasons(sample, first)
    if "high_risk_complex_response" in hard_reasons:
        final_decision = "manual_only"
    elif hard_reasons:
        final_decision = "human_review"
    elif risk < float(thresholds["auto_accept_below"]):
        final_decision = "auto_accept"
    elif risk < float(thresholds["human_review_below"]):
        final_decision = "human_review"
    else:
        final_decision = "manual_only"

    disagreements: list[str] = []
    if first["recognition_status"] != "pass":
        disagreements.append("recognition")
    if median_score != reference_score:
        disagreements.append("scoring")
    if physics_status != sample["reference_physics_status"]:
        disagreements.append("physics_judgment")
    if teaching_code != sample["reference_teaching_code"]:
        disagreements.append("teaching_explanation")
    if final_decision != sample["reference_final_decision"]:
        disagreements.append("final_decision")

    error_cost = abs(median_score - reference_score) * 2.0
    if physics_status != sample["reference_physics_status"]:
        contradiction_involved = "contradiction" in {
            physics_status,
            sample["reference_physics_status"],
        }
        error_cost += 5.0 if contradiction_involved else 3.0
    if teaching_code != sample["reference_teaching_code"]:
        error_cost += 1.0
    if first["recognition_status"] != "pass":
        error_cost += 2.0

    caution_rank = {"auto_accept": 0, "human_review": 1, "manual_only": 2}
    machine_rank = caution_rank[final_decision]
    reference_rank = caution_rank[sample["reference_final_decision"]]
    if machine_rank < reference_rank:
        error_cost += 4.0 * (reference_rank - machine_rank)
    elif machine_rank > reference_rank:
        error_cost += 0.5 * (machine_rank - reference_rank)

    confidence = 1.0 - spread * 0.18 - (1.0 - ratio) * 0.8 - missing_count * 0.08
    return {
        "sample_id": sample["sample_id"],
        "response_type": sample["response_type"],
        "risk_level": sample["risk_level"],
        "reference_identity": rubric["reference_identity"],
        "reference_score": int(reference_score),
        "median_machine_score": median_score,
        "score_min": min(scores),
        "score_max": max(scores),
        "score_spread": spread,
        "score_confidence": round(max(0.0, min(1.0, confidence)), 4),
        "recognition_ratio": ratio,
        "recognition_status": first["recognition_status"],
        "machine_physics_status": physics_status,
        "reference_physics_status": sample["reference_physics_status"],
        "machine_teaching_code": teaching_code,
        "reference_teaching_code": sample["reference_teaching_code"],
        "risk_score": risk,
        "hard_escalation_reasons": " | ".join(hard_reasons),
        "machine_final_decision": final_decision,
        "reference_final_decision": sample["reference_final_decision"],
        "disagreement_layers": " | ".join(disagreements),
        "weighted_error_cost": round(error_cost, 2),
        "upgrade_reason": build_upgrade_reason(first, spread, risk, final_decision),
    }


def build_upgrade_reason(
    first: dict[str, Any], spread: int, risk: float, final_decision: str
) -> str:
    if final_decision == "auto_accept":
        return "风险阈值内；仍保留抽查"
    reasons: list[str] = []
    if first["recognition_status"] != "pass":
        reasons.append("识别与原始作答不一致")
    if first["missing_required"]:
        reasons.append("关键证据缺失")
    if first["physics_status"] == "contradiction":
        reasons.append("出现物理关系冲突")
    if spread > 0:
        reasons.append("重复评分存在波动")
    if not reasons:
        reasons.append("作答类型基础风险较高")
    return f"{final_decision}（风险{risk:.2f}）：" + "；".join(reasons)


def build_curve(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total = len(results)
    hard_escalation_floor = sum(bool(row["hard_escalation_reasons"]) for row in results)
    rows: list[dict[str, Any]] = []
    for threshold in POLICY_THRESHOLDS:
        automated = [
            row
            for row in results
            if float(row["risk_score"]) <= threshold
            and not row["hard_escalation_reasons"]
        ]
        disagreement_count = sum(
            1 for row in automated if float(row["weighted_error_cost"]) > 0
        )
        total_cost = sum(float(row["weighted_error_cost"]) for row in automated)
        rows.append(
            {
                "risk_threshold": threshold,
                "auto_processed_count": len(automated),
                "auto_processing_ratio": round(len(automated) / total, 4),
                "disagreement_count": disagreement_count,
                "disagreement_rate_among_auto": round(
                    disagreement_count / len(automated), 4
                )
                if automated
                else 0.0,
                "total_weighted_error_cost": round(total_cost, 2),
                "error_cost_per_auto": round(total_cost / len(automated), 2)
                if automated
                else 0.0,
                "teacher_review_count": total - len(automated),
                "hard_escalation_floor": hard_escalation_floor,
            }
        )
    return rows


def apply_appeals(
    appeals: list[dict[str, str]], results: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_id = {row["sample_id"]: row for row in results}
    appeal_results: list[dict[str, Any]] = []
    for appeal in appeals:
        initial = by_id[appeal["sample_id"]]
        revised_score = float(appeal["revised_score"])
        changed_fields: list[str] = []
        if revised_score != float(initial["median_machine_score"]):
            changed_fields.append("score")
        if appeal["revised_physics_status"] != initial["machine_physics_status"]:
            changed_fields.append("physics_judgment")
        if appeal["revised_teaching_code"] != initial["machine_teaching_code"]:
            changed_fields.append("teaching_explanation")
        appeal_results.append(
            {
                "appeal_id": appeal["appeal_id"],
                "sample_id": appeal["sample_id"],
                "appeal_reason": appeal["appeal_reason"],
                "initial_score": initial["median_machine_score"],
                "initial_physics_status": initial["machine_physics_status"],
                "initial_teaching_code": initial["machine_teaching_code"],
                "review_action": appeal["review_action"],
                "revised_score": revised_score,
                "revised_physics_status": appeal["revised_physics_status"],
                "revised_teaching_code": appeal["revised_teaching_code"],
                "changed_fields": " | ".join(changed_fields) if changed_fields else "confirmed",
                "reviewer_basis": appeal["reviewer_basis"],
            }
        )
    return appeal_results


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    rows = list(rows)
    if not rows:
        raise ValueError(f"refuse to write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def write_summary(
    path: Path,
    samples: list[dict[str, str]],
    results: list[dict[str, Any]],
    curve: list[dict[str, Any]],
    appeal_results: list[dict[str, Any]],
    repeat_count: int,
) -> None:
    type_counts = Counter(sample["response_type"] for sample in samples)
    decision_counts = Counter(row["machine_final_decision"] for row in results)
    changed_appeals = sum(row["changed_fields"] != "confirmed" for row in appeal_results)
    confirmed_appeals = len(appeal_results) - changed_appeals
    lines = [
        "# 离线演示结果",
        "",
        "> 身份：确定性模拟评分器的管线演示。以下数字不是任何AI模型准确率。",
        "",
        "## 样本与运行",
        "",
        f"- 合成作答：{len(samples)}份；文字解释、公式／计算、图像描述、实验报告各{type_counts['textual_explanation']}、{type_counts['formula_calculation']}、{type_counts['diagram_description']}、{type_counts['experiment_report']}份；",
        f"- 重复压力测试：每份{repeat_count}次，共{len(samples) * repeat_count}条评分记录；",
        f"- 管线推荐结果：自动接受{decision_counts['auto_accept']}份、教师复核{decision_counts['human_review']}份、仅人工处理{decision_counts['manual_only']}份；",
        f"- 申诉／改判演练：{len(appeal_results)}项，其中{changed_appeals}项至少改变一个机器层输出，{confirmed_appeals}项由人工确认原结果；",
        "",
        "## 阈值对照",
        "",
        "| 风险阈值 | 自动处理 | 自动比例 | 自动样本不一致率 | 加权错误代价 | 教师复核量 |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in curve:
        lines.append(
            f"| {row['risk_threshold']:.2f} | {row['auto_processed_count']} | "
            f"{row['auto_processing_ratio']:.1%} | {row['disagreement_rate_among_auto']:.1%} | "
            f"{row['total_weighted_error_cost']:.2f} | {row['teacher_review_count']} |"
        )
    lines.extend(
        [
            "",
            "阈值越宽松，进入自动处理的样本只会增加，教师复核量只会减少；与此同时，不一致和错误代价可能累积。所有阈值始终执行同一组硬升级规则，因此最高阈值也不会自动处理明确物理冲突、识别未通过或高风险图像／实验报告。这里的代价权重是演示设定，正式研究前必须由教师预先裁决。",
            "",
            "## 读取顺序",
            "",
            "1. `sample_results.csv`：逐份查看五层结果、风险和升级原因；",
            "2. `repeat_scores.csv`：查看五次压力测试是否有分数波动；",
            "3. `selective_automation_curve.csv`：比较不同阈值；",
            "4. `appeals_results.csv`：查看人工复核如何改变或确认结果。",
            "",
        ]
    )
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("\n".join(lines), encoding="utf-8")
    temporary.replace(path)


def validate_inputs(
    samples: list[dict[str, str]], appeals: list[dict[str, str]], repeat_count: int
) -> None:
    required_types = {
        "textual_explanation",
        "formula_calculation",
        "diagram_description",
        "experiment_report",
    }
    if len(samples) < 20:
        raise ValueError("至少需要20份合成作答")
    if Counter(sample["sample_id"] for sample in samples).most_common(1)[0][1] != 1:
        raise ValueError("sample_id必须唯一")
    if {sample["response_type"] for sample in samples} != required_types:
        raise ValueError("样本必须覆盖四类作答")
    if repeat_count < 3:
        raise ValueError("重复压力测试至少3次")
    sample_ids = {sample["sample_id"] for sample in samples}
    missing_appeals = [a["sample_id"] for a in appeals if a["sample_id"] not in sample_ids]
    if missing_appeals:
        raise ValueError(f"申诉引用未知样本：{missing_appeals}")


def run(
    data_path: Path,
    rubric_path: Path,
    appeals_path: Path,
    output_dir: Path,
    repeat_count: int = 5,
) -> dict[str, Any]:
    samples = read_csv(data_path)
    appeals = read_csv(appeals_path)
    rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
    validate_inputs(samples, appeals, repeat_count)

    repeat_rows: list[dict[str, Any]] = []
    sample_results: list[dict[str, Any]] = []
    for sample in samples:
        sample_repeats = [score_once(sample, index) for index in range(1, repeat_count + 1)]
        repeat_rows.extend(sample_repeats)
        sample_results.append(aggregate_sample(sample, sample_repeats, rubric))

    curve = build_curve(sample_results)
    appeal_results = apply_appeals(appeals, sample_results)
    write_csv(output_dir / "repeat_scores.csv", repeat_rows)
    write_csv(output_dir / "sample_results.csv", sample_results)
    write_csv(output_dir / "selective_automation_curve.csv", curve)
    write_csv(output_dir / "appeals_results.csv", appeal_results)
    write_summary(
        output_dir / "summary.md",
        samples,
        sample_results,
        curve,
        appeal_results,
        repeat_count,
    )
    return {
        "sample_count": len(samples),
        "repeat_row_count": len(repeat_rows),
        "appeal_count": len(appeal_results),
        "output_dir": str(output_dir),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行P0-3选择性自动化离线基准")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--rubric", type=Path, default=DEFAULT_RUBRIC)
    parser.add_argument("--appeals", type=Path, default=DEFAULT_APPEALS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--repeats", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = run(args.data, args.rubric, args.appeals, args.output_dir, args.repeats)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
