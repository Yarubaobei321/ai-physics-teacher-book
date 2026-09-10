from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_benchmark.py"
SPEC = importlib.util.spec_from_file_location("run_benchmark", SCRIPT)
assert SPEC and SPEC.loader
BENCHMARK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BENCHMARK)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class BenchmarkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.samples = read_csv(ROOT / "data" / "synthetic_responses.csv")

    def test_sample_pack_has_24_balanced_synthetic_items(self) -> None:
        self.assertEqual(len(self.samples), 24)
        counts = Counter(row["response_type"] for row in self.samples)
        self.assertEqual(
            counts,
            {
                "textual_explanation": 6,
                "formula_calculation": 6,
                "diagram_description": 6,
                "experiment_report": 6,
            },
        )
        self.assertEqual(len({row["sample_id"] for row in self.samples}), 24)

    def test_pack_contains_no_direct_personal_identifiers(self) -> None:
        joined = "\n".join("|".join(row.values()) for row in self.samples)
        forbidden_patterns = ("身份证", "学号", "手机号", "@qq.com", "@163.com", "真实学生")
        for pattern in forbidden_patterns:
            self.assertNotIn(pattern, joined)

    def test_pipeline_writes_five_repeat_records_and_all_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = BENCHMARK.run(
                ROOT / "data" / "synthetic_responses.csv",
                ROOT / "data" / "rubric.json",
                ROOT / "data" / "appeals.csv",
                Path(temp_dir),
                5,
            )
            self.assertEqual(report["sample_count"], 24)
            self.assertEqual(report["repeat_row_count"], 120)
            for name in (
                "repeat_scores.csv",
                "sample_results.csv",
                "selective_automation_curve.csv",
                "appeals_results.csv",
                "summary.md",
            ):
                self.assertTrue((Path(temp_dir) / name).is_file(), name)

    def test_layers_and_reference_identity_are_explicit(self) -> None:
        rubric = json.loads((ROOT / "data" / "rubric.json").read_text(encoding="utf-8"))
        self.assertEqual(rubric["reference_identity"], "单作者暂定参考")
        self.assertEqual(
            [layer["id"] for layer in rubric["layers"]],
            [
                "recognition",
                "scoring",
                "physics_judgment",
                "teaching_explanation",
                "final_decision",
            ],
        )

    def test_curve_is_monotonic_and_preserves_tradeoffs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            BENCHMARK.run(
                ROOT / "data" / "synthetic_responses.csv",
                ROOT / "data" / "rubric.json",
                ROOT / "data" / "appeals.csv",
                Path(temp_dir),
                5,
            )
            curve = read_csv(Path(temp_dir) / "selective_automation_curve.csv")
            auto_counts = [int(row["auto_processed_count"]) for row in curve]
            review_counts = [int(row["teacher_review_count"]) for row in curve]
            costs = [float(row["total_weighted_error_cost"]) for row in curve]
            self.assertEqual(auto_counts, sorted(auto_counts))
            self.assertEqual(review_counts, sorted(review_counts, reverse=True))
            self.assertEqual(costs, sorted(costs))
            self.assertGreater(auto_counts[-1], auto_counts[0])

    def test_curve_never_bypasses_hard_escalation_at_highest_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            BENCHMARK.run(
                ROOT / "data" / "synthetic_responses.csv",
                ROOT / "data" / "rubric.json",
                ROOT / "data" / "appeals.csv",
                Path(temp_dir),
                5,
            )
            results = read_csv(Path(temp_dir) / "sample_results.csv")
            curve = read_csv(Path(temp_dir) / "selective_automation_curve.csv")
            hard_ids = {
                row["sample_id"] for row in results if row["hard_escalation_reasons"]
            }
            highest = curve[-1]
            self.assertGreater(len(hard_ids), 0)
            self.assertEqual(int(highest["hard_escalation_floor"]), len(hard_ids))
            self.assertGreaterEqual(int(highest["teacher_review_count"]), len(hard_ids))
            self.assertLess(int(highest["auto_processed_count"]), len(results))
            expected_auto = {
                row["sample_id"]
                for row in results
                if float(row["risk_score"]) <= float(highest["risk_threshold"])
                and not row["hard_escalation_reasons"]
            }
            self.assertEqual(int(highest["auto_processed_count"]), len(expected_auto))
            for row in results:
                if (
                    row["machine_physics_status"] == "contradiction"
                    or row["recognition_status"] != "pass"
                    or (
                        row["risk_level"] == "high"
                        and row["response_type"]
                        in {"diagram_description", "experiment_report"}
                    )
                ):
                    self.assertIn(row["sample_id"], hard_ids)

    def test_appeals_preserve_initial_and_revised_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            BENCHMARK.run(
                ROOT / "data" / "synthetic_responses.csv",
                ROOT / "data" / "rubric.json",
                ROOT / "data" / "appeals.csv",
                Path(temp_dir),
                5,
            )
            appeals = read_csv(Path(temp_dir) / "appeals_results.csv")
            self.assertEqual(len(appeals), 4)
            self.assertTrue(all(row["reviewer_basis"] for row in appeals))
            self.assertTrue(any(row["changed_fields"] != "confirmed" for row in appeals))

    def test_hard_escalation_blocks_contradictions_and_high_risk_complex_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            BENCHMARK.run(
                ROOT / "data" / "synthetic_responses.csv",
                ROOT / "data" / "rubric.json",
                ROOT / "data" / "appeals.csv",
                Path(temp_dir),
                5,
            )
            results = read_csv(Path(temp_dir) / "sample_results.csv")
            for row in results:
                if row["machine_physics_status"] == "contradiction":
                    self.assertNotEqual(row["machine_final_decision"], "auto_accept")
                if row["risk_level"] == "high" and row["response_type"] in {
                    "diagram_description",
                    "experiment_report",
                }:
                    self.assertEqual(row["machine_final_decision"], "manual_only")


if __name__ == "__main__":
    unittest.main()
