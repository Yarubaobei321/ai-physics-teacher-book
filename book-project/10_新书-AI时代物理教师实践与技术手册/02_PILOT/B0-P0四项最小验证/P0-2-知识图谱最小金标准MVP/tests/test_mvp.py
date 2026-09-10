from __future__ import annotations

import csv
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build_mvp  # noqa: E402


class MVPSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = build_mvp.load_bundle()

    def test_expected_counts(self) -> None:
        self.assertEqual(len(self.bundle["components"]), 10)
        self.assertEqual(len(self.bundle["questions"]), 20)
        self.assertEqual(len(self.bundle["responses"]), 60)
        self.assertGreaterEqual(len(self.bundle["mappings"]), 20)

    def test_all_questions_are_self_authored(self) -> None:
        identities = {row["source_identity"] for row in self.bundle["questions"]}
        self.assertEqual(identities, {"本项目自编"})

    def test_all_responses_are_synthetic(self) -> None:
        identities = {row["data_identity"] for row in self.bundle["responses"]}
        self.assertEqual(identities, {"合成轨迹"})

    def test_every_question_has_one_primary_mapping(self) -> None:
        primary = {row["question_id"] for row in self.bundle["mappings"] if row["role"] == "primary"}
        questions = {row["question_id"] for row in self.bundle["questions"]}
        self.assertEqual(primary, questions)

    def test_bkt_update_moves_in_expected_direction(self) -> None:
        correct_posterior, correct_after = build_mvp.bkt_update(0.25, True, 0.20, 0.10, 0.12)
        wrong_posterior, wrong_after = build_mvp.bkt_update(0.25, False, 0.20, 0.10, 0.12)
        self.assertGreater(correct_after, 0.25)
        self.assertLess(wrong_posterior, 0.25)
        self.assertGreater(correct_after, wrong_after)


class MVPOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        build_mvp.main()

    def test_outputs_exist_and_are_nonempty(self) -> None:
        for relative in ["generated/index.html", "generated/comparison.md", "generated/student_state_updates.csv"]:
            path = ROOT / relative
            self.assertTrue(path.is_file(), relative)
            self.assertGreater(path.stat().st_size, 100, relative)

    def test_update_rows_stay_in_probability_range(self) -> None:
        with (ROOT / "generated/student_state_updates.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertGreater(len(rows), 60)
        for row in rows:
            self.assertEqual(row["data_identity"], "合成轨迹／演示参数")
            for key in ["prior", "posterior_before_learning", "state_after_learning"]:
                self.assertGreaterEqual(float(row[key]), 0.0)
                self.assertLessEqual(float(row[key]), 1.0)

    def test_html_contains_core_boundaries(self) -> None:
        page = (ROOT / "generated/index.html").read_text(encoding="utf-8")
        self.assertIn("全部合成", page)
        self.assertIn("参数人为设定", page)
        self.assertIn("教师仍需做的六次裁决", page)


if __name__ == "__main__":
    unittest.main()
