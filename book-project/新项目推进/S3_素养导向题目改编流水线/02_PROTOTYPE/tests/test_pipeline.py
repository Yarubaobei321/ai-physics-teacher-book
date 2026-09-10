import copy
import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "02_PROTOTYPE" / "pipeline.py"
SPEC = importlib.util.spec_from_file_location("s3_pipeline", MODULE_PATH)
pipeline = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pipeline
SPEC.loader.exec_module(pipeline)


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sample_path = PROJECT_ROOT / "02_PROTOTYPE" / "sample" / "lineage.json"
        cls.payload = json.loads(sample_path.read_text(encoding="utf-8"))
        pipeline.validate_lineage(cls.payload)
        cls.rows = pipeline.audit_payload(cls.payload)
        cls.by_id = {row["version"]["version_id"]: row for row in cls.rows}

    def test_safe_eval_accepts_arithmetic(self):
        value = pipeline.safe_eval("v0*t + 0.5*a*t**2", {"v0": 12, "t": 4, "a": -3})
        self.assertAlmostEqual(value, 24.0)

    def test_safe_eval_rejects_function_calls(self):
        with self.assertRaises(pipeline.ValidationError):
            pipeline.safe_eval("__import__('os').system('echo unsafe')", {})

    def test_context_only_candidate_is_rejected(self):
        row = self.by_id["Q001-C01"]
        self.assertEqual(row["disposition"], "否决")
        self.assertEqual(row["gates"]["cognitive_requirement"].status, "return")

    def test_condition_and_answer_mismatch_is_returned(self):
        row = self.by_id["Q001-C02"]
        self.assertEqual(row["disposition"], "退回")
        self.assertEqual(row["gates"]["condition_sufficiency"].status, "return")
        self.assertEqual(row["gates"]["answer_design"].status, "return")

    def test_revised_candidate_passes_all_seven_gates(self):
        row = self.by_id["Q001-C03"]
        self.assertEqual(row["disposition"], "内部试点定稿")
        self.assertTrue(all(gate.status == "pass" for gate in row["gates"].values()))
        self.assertEqual(row["version"]["answer_design"]["mode"], "mixed")

    def test_mixed_answer_requires_both_kinds_of_parts(self):
        question = copy.deepcopy(self.payload["questions"][0])
        version = next(v for v in question["versions"] if v["version_id"] == "Q001-C03")
        version["answer_design"]["open_parts"] = []
        row = pipeline.audit_version(question, version)
        self.assertEqual(row["gates"]["answer_design"].status, "return")

    def test_missing_parent_breaks_lineage(self):
        broken = copy.deepcopy(self.payload)
        broken["questions"][0]["versions"][2]["parent_id"] = "Q001-NOT-FOUND"
        with self.assertRaises(pipeline.ValidationError):
            pipeline.validate_lineage(broken)

    def test_question_limit_is_enforced(self):
        broken = copy.deepcopy(self.payload)
        original = broken["questions"][0]
        broken["questions"] = []
        for index in range(11):
            item = copy.deepcopy(original)
            item["question_id"] = f"Q{index:03d}"
            broken["questions"].append(item)
        with self.assertRaises(pipeline.ValidationError):
            pipeline.validate_lineage(broken)

    def test_propose_does_not_write_or_claim_final_question(self):
        draft = pipeline.propose(self.payload, "Q001", "Q001-O", "data_image")
        self.assertEqual(draft["parent_id"], "Q001-O")
        self.assertIn("待教师填写", draft["candidate_question_text"])
        self.assertGreaterEqual(len(draft["review_focus"]), 3)

    def test_report_generation_outputs_expected_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir)
            self.assertEqual(
                pipeline.run_audit(PROJECT_ROOT / "02_PROTOTYPE" / "sample" / "lineage.json", output),
                0,
            )
            self.assertEqual(
                {path.name for path in output.iterdir()},
                {"audit_report.md", "audit_ledger.csv", "lineage.svg", "Q001-C03-vt-reference.svg"},
            )
            self.assertIn("内部试点定稿", (output / "audit_report.md").read_text(encoding="utf-8"))

    def test_relative_markdown_links_exist(self):
        link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
        missing = []
        for markdown in PROJECT_ROOT.rglob("*.md"):
            for target in link_pattern.findall(markdown.read_text(encoding="utf-8")):
                if target.startswith(("http://", "https://", "#", "/")):
                    continue
                resolved = (markdown.parent / target.split("#", 1)[0]).resolve()
                if not resolved.exists():
                    missing.append(f"{markdown.relative_to(PROJECT_ROOT)} -> {target}")
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
