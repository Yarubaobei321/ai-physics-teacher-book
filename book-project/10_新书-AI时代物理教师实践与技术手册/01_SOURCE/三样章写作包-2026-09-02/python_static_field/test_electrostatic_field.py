import json
import tempfile
import unittest
from pathlib import Path

from electrostatic_field import (
    TankConfig,
    analytic_harmonic_2d_check,
    analytic_parallel_plate_check,
    boundary_definition_audit,
    boundary_errors,
    electrode_flux_balance,
    field_antialignment_audit,
    field_direction_audit,
    insulating_wall_errors,
    make_finite_plate_problem,
    maximum_principle_audit,
    potential_reference_shift_check,
    run,
    solve_laplace,
    stencil_residual,
    symmetry_errors,
)


class ElectrostaticFieldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = TankConfig()
        cls.solution = solve_laplace(
            *make_finite_plate_problem(cls.config, nx=81, ny=61)
        )

    def test_fixed_electrode_potentials_are_preserved(self):
        self.assertLessEqual(
            boundary_errors(self.solution)["fixed_potential_max_v"], 1.0e-12
        )

    def test_laplace_stencil_residual_is_small(self):
        self.assertLessEqual(
            stencil_residual(self.solution)["max_abs_v"], 1.0e-7
        )

    def test_expected_symmetries_hold(self):
        errors = symmetry_errors(self.solution)
        self.assertTrue(errors["left_right_applicable"])
        self.assertTrue(errors["top_bottom_applicable"])
        self.assertLessEqual(errors["left_right_antisymmetry_max_v"], 1.0e-6)
        self.assertLessEqual(errors["top_bottom_symmetry_max_v"], 1.0e-6)
        self.assertTrue(errors["passed"])

    def test_insulating_outer_walls_have_zero_normal_difference(self):
        errors = insulating_wall_errors(self.solution)
        self.assertLessEqual(errors["max_normal_gradient_v_per_m"], 1.0e-10)

    def test_solution_obeys_maximum_principle(self):
        self.assertTrue(maximum_principle_audit(self.solution)["passed"])

    def test_electrode_fluxes_are_balanced(self):
        self.assertLessEqual(
            electrode_flux_balance(self.solution)["relative_imbalance"], 5.0e-3
        )

    def test_correct_field_direction_passes(self):
        self.assertTrue(field_direction_audit(self.solution, gradient_sign=-1.0)["passed"])

    def test_article_style_reversed_field_direction_is_caught(self):
        self.assertFalse(field_direction_audit(self.solution, gradient_sign=+1.0)["passed"])

    def test_whole_field_direction_is_antiparallel_to_potential_gradient(self):
        self.assertTrue(
            field_antialignment_audit(self.solution, gradient_sign=-1.0)["passed"]
        )
        self.assertFalse(
            field_antialignment_audit(self.solution, gradient_sign=+1.0)["passed"]
        )

    def test_equal_potential_boundary_is_caught_for_this_declared_case(self):
        wrong = TankConfig(high_v=5.0, low_v=5.0)
        self.assertFalse(boundary_definition_audit(wrong)["passed"])

    def test_absolute_potential_zero_is_arbitrary(self):
        shifted = TankConfig(high_v=5.0, low_v=2.0)
        self.assertTrue(boundary_definition_audit(shifted)["passed"])

    def test_reference_potential_shift_leaves_field_unchanged(self):
        result = potential_reference_shift_check(self.config)
        self.assertTrue(result["passed"])

    def test_shifted_reference_case_passes_end_to_end(self):
        case_document = json.loads(
            Path(__file__).with_name("case_finite_parallel_plates.json").read_text(
                encoding="utf-8"
            )
        )
        case_document["case_id"] = "finite-parallel-plates-shifted-reference-test"
        case_document["tank"]["high_v"] = 5.0
        case_document["tank"]["low_v"] = 2.0
        with tempfile.TemporaryDirectory(prefix="static-field-shifted-") as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "case.json"
            config_path.write_text(
                json.dumps(case_document, ensure_ascii=False), encoding="utf-8"
            )
            result = run(temp_path / "output", config_path)

        symmetry = result["checks"]["symmetry"]
        self.assertTrue(result["overall_passed"])
        self.assertAlmostEqual(symmetry["potential_midpoint_v"], 3.5)
        self.assertTrue(symmetry["left_right_applicable"])
        self.assertLessEqual(symmetry["left_right_antisymmetry_max_v"], 1.0e-6)

    def test_asymmetric_geometry_skips_inapplicable_left_right_symmetry(self):
        case_document = json.loads(
            Path(__file__).with_name("case_finite_parallel_plates.json").read_text(
                encoding="utf-8"
            )
        )
        case_document["case_id"] = "finite-parallel-plates-asymmetric-test"
        # 0.0825 m同时落在三档网格上，使本测试只隔离对称性适用条件。
        case_document["tank"]["high_x_m"] = 0.0825
        case_document["tank"]["low_x_m"] = 0.21
        with tempfile.TemporaryDirectory(prefix="static-field-asymmetric-") as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "case.json"
            config_path.write_text(
                json.dumps(case_document, ensure_ascii=False), encoding="utf-8"
            )
            result = run(temp_path / "output", config_path)

        symmetry = result["checks"]["symmetry"]
        self.assertTrue(result["overall_passed"])
        self.assertFalse(symmetry["left_right_applicable"])
        self.assertIsNone(symmetry["left_right_antisymmetry_max_v"])
        self.assertIsNone(symmetry["left_right_passed"])
        self.assertTrue(symmetry["top_bottom_applicable"])
        self.assertTrue(symmetry["top_bottom_passed"])

    def test_solver_matches_linear_parallel_plate_solution(self):
        self.assertLessEqual(
            analytic_parallel_plate_check()["max_abs_error_v"], 2.0e-5
        )

    def test_solver_matches_2d_harmonic_solution_with_unequal_spacing(self):
        result = analytic_harmonic_2d_check()
        self.assertNotAlmostEqual(result["dx_m"], result["dy_m"])
        self.assertLessEqual(result["max_abs_error_v"], 2.0e-5)


if __name__ == "__main__":
    unittest.main()
