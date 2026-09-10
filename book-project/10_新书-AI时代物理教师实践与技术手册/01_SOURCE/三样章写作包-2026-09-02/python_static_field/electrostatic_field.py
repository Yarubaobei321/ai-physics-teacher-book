#!/usr/bin/env python3
"""有限水槽中的二维稳恒电势：教学用、可审查的最小原型。

模型：均匀浅水层内无内源，求解 Laplace 方程；内部两片电极给定电势，
水槽外壁默认绝缘（法向导数为零）。本程序输出电势、等势线和 E=-grad(V)。

它是 2026-09-02 新建的 Python 独立路线，不是旧 COMSOL 工程的复原。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager


_CHINESE_FONT = Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")
if _CHINESE_FONT.exists():
    font_manager.fontManager.addfont(str(_CHINESE_FONT))
    plt.rcParams["font.family"] = "Arial Unicode MS"
plt.rcParams["axes.unicode_minus"] = False


@dataclass(frozen=True)
class TankConfig:
    """示例水槽与电极的几何、边界条件。长度单位为米，电势单位为伏。"""

    width_m: float = 0.30
    height_m: float = 0.20
    high_x_m: float = 0.09
    low_x_m: float = 0.21
    electrode_y_min_m: float = 0.06
    electrode_y_max_m: float = 0.14
    high_v: float = 5.0
    low_v: float = -5.0


@dataclass
class Solution:
    potential: np.ndarray
    fixed_mask: np.ndarray
    fixed_values: np.ndarray
    x_m: np.ndarray
    y_m: np.ndarray
    iterations: int
    max_update_v: float

    @property
    def dx_m(self) -> float:
        return float(self.x_m[1] - self.x_m[0])

    @property
    def dy_m(self) -> float:
        return float(self.y_m[1] - self.y_m[0])


def load_case_config(path: Path) -> tuple[TankConfig, dict[str, object]]:
    """读取独立案例配置，并拒绝本原型尚未实现的方程或外壁边界。"""

    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("equation") != "laplace_constant_conductivity":
        raise ValueError("本原型只实现常电导率二维 Laplace 方程。")
    if document.get("outer_wall_boundary") != "insulating_neumann":
        raise ValueError("本原型只实现绝缘外壁 Neumann 边界。")
    tank = document.get("tank")
    if not isinstance(tank, dict):
        raise ValueError("配置缺少 tank 对象。")
    return TankConfig(**tank), document


def _nearest_index(values: np.ndarray, target: float) -> int:
    return int(np.argmin(np.abs(values - target)))


def make_finite_plate_problem(
    config: TankConfig, nx: int, ny: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """建立“内部有限平行板 + 外壁绝缘”的网格问题。"""

    if nx < 21 or ny < 21:
        raise ValueError("网格至少为 21×21。")
    x_m = np.linspace(0.0, config.width_m, nx)
    y_m = np.linspace(0.0, config.height_m, ny)
    fixed_mask = np.zeros((ny, nx), dtype=bool)
    fixed_values = np.zeros((ny, nx), dtype=float)

    i_high = _nearest_index(x_m, config.high_x_m)
    i_low = _nearest_index(x_m, config.low_x_m)
    j_min = _nearest_index(y_m, config.electrode_y_min_m)
    j_max = _nearest_index(y_m, config.electrode_y_max_m)
    if j_min > j_max:
        j_min, j_max = j_max, j_min

    fixed_mask[j_min : j_max + 1, i_high] = True
    fixed_values[j_min : j_max + 1, i_high] = config.high_v
    fixed_mask[j_min : j_max + 1, i_low] = True
    fixed_values[j_min : j_max + 1, i_low] = config.low_v
    return fixed_mask, fixed_values, x_m, y_m


def make_boundary_plate_problem(
    width_m: float,
    height_m: float,
    left_v: float,
    right_v: float,
    nx: int,
    ny: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """建立有解析解的平行板校准题：左右定电势，上下绝缘。"""

    x_m = np.linspace(0.0, width_m, nx)
    y_m = np.linspace(0.0, height_m, ny)
    fixed_mask = np.zeros((ny, nx), dtype=bool)
    fixed_values = np.zeros((ny, nx), dtype=float)
    fixed_mask[:, 0] = True
    fixed_values[:, 0] = left_v
    fixed_mask[:, -1] = True
    fixed_values[:, -1] = right_v
    return fixed_mask, fixed_values, x_m, y_m


def _apply_insulating_walls(potential: np.ndarray) -> None:
    """用相邻网格值实现外壁零法向导数；定电势点随后会被重新覆盖。"""

    potential[0, 1:-1] = potential[1, 1:-1]
    potential[-1, 1:-1] = potential[-2, 1:-1]
    potential[1:-1, 0] = potential[1:-1, 1]
    potential[1:-1, -1] = potential[1:-1, -2]
    potential[0, 0] = 0.5 * (potential[0, 1] + potential[1, 0])
    potential[0, -1] = 0.5 * (potential[0, -2] + potential[1, -1])
    potential[-1, 0] = 0.5 * (potential[-1, 1] + potential[-2, 0])
    potential[-1, -1] = 0.5 * (potential[-1, -2] + potential[-2, -1])


def solve_laplace(
    fixed_mask: np.ndarray,
    fixed_values: np.ndarray,
    x_m: np.ndarray,
    y_m: np.ndarray,
    *,
    tolerance_v: float = 1.0e-8,
    max_iterations: int = 40_000,
    omega: float = 1.85,
) -> Solution:
    """用红黑 SOR 迭代求解二维 Laplace 方程。"""

    if fixed_mask.shape != fixed_values.shape:
        raise ValueError("fixed_mask 与 fixed_values 尺寸不一致。")
    if fixed_mask.shape != (len(y_m), len(x_m)):
        raise ValueError("边界数组与坐标尺寸不一致。")
    if not np.any(fixed_mask):
        raise ValueError("至少需要一个定电势边界。")
    if not 0.0 < omega < 2.0:
        raise ValueError("SOR 松弛因子须在 0 与 2 之间。")

    initial_free_potential_v = float(np.mean(fixed_values[fixed_mask]))
    potential = np.full_like(
        fixed_values, initial_free_potential_v, dtype=float
    )
    potential[fixed_mask] = fixed_values[fixed_mask]
    dx_m = float(x_m[1] - x_m[0])
    dy_m = float(y_m[1] - y_m[0])
    inv_dx2 = 1.0 / dx_m**2
    inv_dy2 = 1.0 / dy_m**2
    denominator = 2.0 * (inv_dx2 + inv_dy2)
    yy, xx = np.indices((potential.shape[0] - 2, potential.shape[1] - 2))
    free_interior = ~fixed_mask[1:-1, 1:-1]
    max_update_v = float("inf")

    for iteration in range(1, max_iterations + 1):
        max_update_v = 0.0
        for parity in (0, 1):
            interior = potential[1:-1, 1:-1]
            average = (
                (potential[1:-1, :-2] + potential[1:-1, 2:]) * inv_dx2
                + (potential[:-2, 1:-1] + potential[2:, 1:-1]) * inv_dy2
            ) / denominator
            update_mask = free_interior & (((xx + yy) & 1) == parity)
            delta = omega * (average - interior)
            if np.any(update_mask):
                max_update_v = max(
                    max_update_v, float(np.max(np.abs(delta[update_mask])))
                )
                interior[update_mask] += delta[update_mask]

        previous_walls = np.concatenate(
            (potential[0], potential[-1], potential[1:-1, 0], potential[1:-1, -1])
        ).copy()
        _apply_insulating_walls(potential)
        potential[fixed_mask] = fixed_values[fixed_mask]
        current_walls = np.concatenate(
            (potential[0], potential[-1], potential[1:-1, 0], potential[1:-1, -1])
        )
        max_update_v = max(
            max_update_v, float(np.max(np.abs(current_walls - previous_walls)))
        )
        if max_update_v < tolerance_v:
            break
    else:
        raise RuntimeError(
            f"在 {max_iterations} 次迭代内未收敛；末次最大更新量为 {max_update_v:.3e} V。"
        )

    return Solution(
        potential=potential,
        fixed_mask=fixed_mask,
        fixed_values=fixed_values,
        x_m=x_m,
        y_m=y_m,
        iterations=iteration,
        max_update_v=max_update_v,
    )


def electric_field(
    solution: Solution, *, gradient_sign: float = -1.0
) -> tuple[np.ndarray, np.ndarray]:
    """计算电场；物理定义必须使用 gradient_sign=-1，即 E=-grad(V)。"""

    d_v_dy, d_v_dx = np.gradient(
        solution.potential, solution.dy_m, solution.dx_m
    )
    return gradient_sign * d_v_dx, gradient_sign * d_v_dy


def stencil_residual(solution: Solution) -> dict[str, float]:
    """返回自由内部节点的五点差分残差，单位为伏。"""

    v = solution.potential
    inv_dx2 = 1.0 / solution.dx_m**2
    inv_dy2 = 1.0 / solution.dy_m**2
    average = (
        (v[1:-1, :-2] + v[1:-1, 2:]) * inv_dx2
        + (v[:-2, 1:-1] + v[2:, 1:-1]) * inv_dy2
    ) / (2.0 * (inv_dx2 + inv_dy2))
    residual = v[1:-1, 1:-1] - average
    free = ~solution.fixed_mask[1:-1, 1:-1]
    selected = residual[free]
    return {
        "max_abs_v": float(np.max(np.abs(selected))),
        "rms_v": float(np.sqrt(np.mean(selected**2))),
    }


def symmetry_errors(
    solution: Solution, *, tolerance_v: float = 1.0e-6
) -> dict[str, object]:
    """只在固定边界具备相应镜像关系时检查对称性。

    左右反对称针对以两电极电势中值为零点的电势检查，因此不会把
    `+5 V/-5 V`与整体平移后的`5 V/2 V`区别对待。若固定边界本身不具备
    某一方向的镜像关系，该方向标为不适用，不参与总验收。
    """

    v = solution.potential
    fixed_values = solution.fixed_values[solution.fixed_mask]
    high_v = float(np.max(fixed_values))
    low_v = float(np.min(fixed_values))
    potential_midpoint_v = 0.5 * (high_v + low_v)

    high_mask = solution.fixed_mask & np.isclose(solution.fixed_values, high_v)
    low_mask = solution.fixed_mask & np.isclose(solution.fixed_values, low_v)
    left_right_applicable = bool(
        np.array_equal(high_mask, np.fliplr(low_mask))
        and np.array_equal(low_mask, np.fliplr(high_mask))
    )

    fixed_only_values = np.where(
        solution.fixed_mask, solution.fixed_values, potential_midpoint_v
    )
    top_bottom_applicable = bool(
        np.array_equal(solution.fixed_mask, np.flipud(solution.fixed_mask))
        and np.allclose(
            fixed_only_values,
            np.flipud(fixed_only_values),
            rtol=0.0,
            atol=1.0e-12,
        )
    )

    centered_v = v - potential_midpoint_v
    left_right_error = (
        float(np.max(np.abs(centered_v + np.fliplr(centered_v))))
        if left_right_applicable
        else None
    )
    top_bottom_error = (
        float(np.max(np.abs(v - np.flipud(v))))
        if top_bottom_applicable
        else None
    )
    left_right_passed = (
        bool(left_right_error <= tolerance_v)
        if left_right_error is not None
        else None
    )
    top_bottom_passed = (
        bool(top_bottom_error <= tolerance_v)
        if top_bottom_error is not None
        else None
    )
    return {
        "reference": "V_centered = V - (V_high + V_low) / 2",
        "potential_midpoint_v": potential_midpoint_v,
        "left_right_applicable": left_right_applicable,
        "left_right_antisymmetry_max_v": left_right_error,
        "left_right_passed": left_right_passed,
        "top_bottom_applicable": top_bottom_applicable,
        "top_bottom_symmetry_max_v": top_bottom_error,
        "top_bottom_passed": top_bottom_passed,
        "tolerance_v": tolerance_v,
        "passed": bool(
            left_right_passed is not False and top_bottom_passed is not False
        ),
    }


def boundary_errors(solution: Solution) -> dict[str, float]:
    selected = np.abs(
        solution.potential[solution.fixed_mask]
        - solution.fixed_values[solution.fixed_mask]
    )
    return {"fixed_potential_max_v": float(np.max(selected))}


def insulating_wall_errors(solution: Solution) -> dict[str, float]:
    """检查外壁的离散零法向导数条件。

    这一检查只适用于外壁全部绝缘、定电势电极位于水域内部的主案例。
    """

    v = solution.potential
    differences_v = np.concatenate(
        (
            v[0, 1:-1] - v[1, 1:-1],
            v[-1, 1:-1] - v[-2, 1:-1],
            v[1:-1, 0] - v[1:-1, 1],
            v[1:-1, -1] - v[1:-1, -2],
        )
    )
    normal_gradients = np.concatenate(
        (
            (v[0, 1:-1] - v[1, 1:-1]) / solution.dy_m,
            (v[-1, 1:-1] - v[-2, 1:-1]) / solution.dy_m,
            (v[1:-1, 0] - v[1:-1, 1]) / solution.dx_m,
            (v[1:-1, -1] - v[1:-1, -2]) / solution.dx_m,
        )
    )
    return {
        "max_neighbor_difference_v": float(np.max(np.abs(differences_v))),
        "max_normal_gradient_v_per_m": float(np.max(np.abs(normal_gradients))),
    }


def maximum_principle_audit(solution: Solution) -> dict[str, object]:
    """检查调和解是否超出定电势边界的取值范围。"""

    fixed = solution.fixed_values[solution.fixed_mask]
    free = solution.potential[~solution.fixed_mask]
    fixed_min_v = float(np.min(fixed))
    fixed_max_v = float(np.max(fixed))
    free_min_v = float(np.min(free))
    free_max_v = float(np.max(free))
    undershoot_v = max(0.0, fixed_min_v - free_min_v)
    overshoot_v = max(0.0, free_max_v - fixed_max_v)
    return {
        "fixed_min_v": fixed_min_v,
        "fixed_max_v": fixed_max_v,
        "free_min_v": free_min_v,
        "free_max_v": free_max_v,
        "undershoot_v": undershoot_v,
        "overshoot_v": overshoot_v,
        "passed": bool(max(undershoot_v, overshoot_v) <= 1.0e-10),
    }


def electrode_flux_balance(solution: Solution) -> dict[str, object]:
    """以单位电导率和单位厚度估算两电极通量平衡。"""

    fixed_values = solution.fixed_values[solution.fixed_mask]
    high_v = float(np.max(fixed_values))
    low_v = float(np.min(fixed_values))
    if abs(high_v - low_v) <= 1.0e-12:
        return {
            "high_outward_flux_proxy": 0.0,
            "low_outward_flux_proxy": 0.0,
            "net_flux_proxy": 0.0,
            "relative_imbalance": float("inf"),
            "passed": False,
        }

    high_flux = 0.0
    low_flux = 0.0
    ny, nx = solution.potential.shape
    for j, i in np.argwhere(solution.fixed_mask):
        electrode_v = float(solution.fixed_values[j, i])
        for dj, di, edge_length, distance in (
            (-1, 0, solution.dx_m, solution.dy_m),
            (1, 0, solution.dx_m, solution.dy_m),
            (0, -1, solution.dy_m, solution.dx_m),
            (0, 1, solution.dy_m, solution.dx_m),
        ):
            jj, ii = int(j + dj), int(i + di)
            if not (0 <= jj < ny and 0 <= ii < nx):
                continue
            if solution.fixed_mask[jj, ii]:
                continue
            outward = (electrode_v - solution.potential[jj, ii]) * edge_length / distance
            if np.isclose(electrode_v, high_v):
                high_flux += float(outward)
            elif np.isclose(electrode_v, low_v):
                low_flux += float(outward)

    net_flux = high_flux + low_flux
    scale = max(abs(high_flux), abs(low_flux), 1.0e-30)
    relative_imbalance = abs(net_flux) / scale
    return {
        "high_outward_flux_proxy": high_flux,
        "low_outward_flux_proxy": low_flux,
        "net_flux_proxy": net_flux,
        "relative_imbalance": relative_imbalance,
        "passed": bool(relative_imbalance <= 5.0e-3),
    }


def boundary_definition_audit(config: TankConfig) -> dict[str, object]:
    """审查本案例的高、低电势端；电势零点本身可以任意平移。"""

    potential_difference_v = config.high_v - config.low_v
    high_exceeds_low = potential_difference_v > 1.0e-12
    separated = abs(config.high_x_m - config.low_x_m) > 1.0e-12
    inside = (
        0.0 < config.high_x_m < config.width_m
        and 0.0 < config.low_x_m < config.width_m
        and 0.0 <= config.electrode_y_min_m < config.electrode_y_max_m <= config.height_m
    )
    return {
        "high_potential_exceeds_low_potential": high_exceeds_low,
        "potential_difference_v": potential_difference_v,
        "electrode_positions_distinct": separated,
        "electrodes_inside_tank": inside,
        "passed": bool(high_exceeds_low and separated and inside),
    }


def field_direction_audit(
    solution: Solution, *, gradient_sign: float
) -> dict[str, object]:
    """检查槽中央电场是否由左侧高电势端指向右侧低电势端。"""

    ex, ey = electric_field(solution, gradient_sign=gradient_sign)
    j = len(solution.y_m) // 2
    i = len(solution.x_m) // 2
    boundary_values = solution.fixed_values[solution.fixed_mask]
    high_v = float(np.max(boundary_values))
    low_v = float(np.min(boundary_values))
    _, high_indices = np.where(
        solution.fixed_mask & np.isclose(solution.fixed_values, high_v)
    )
    _, low_indices = np.where(
        solution.fixed_mask & np.isclose(solution.fixed_values, low_v)
    )
    high_x_m = float(np.mean(solution.x_m[high_indices]))
    low_x_m = float(np.mean(solution.x_m[low_indices]))
    expected_ex_sign = float(np.sign(low_x_m - high_x_m))
    passed = bool(
        expected_ex_sign * ex[j, i] > 0.0
        and abs(ey[j, i]) < 0.02 * abs(ex[j, i])
    )
    return {
        "gradient_sign": gradient_sign,
        "center_ex_v_per_m": float(ex[j, i]),
        "center_ey_v_per_m": float(ey[j, i]),
        "expected_ex_sign": expected_ex_sign,
        "expected": "电场由高电势电极指向低电势电极，且对称轴上 Ey 接近 0",
        "passed": passed,
    }


def field_antialignment_audit(
    solution: Solution, *, gradient_sign: float
) -> dict[str, object]:
    """检查全域自由节点上电场是否与电势梯度反向。"""

    d_v_dy, d_v_dx = np.gradient(
        solution.potential, solution.dy_m, solution.dx_m
    )
    ex, ey = electric_field(solution, gradient_sign=gradient_sign)
    dot = ex * d_v_dx + ey * d_v_dy
    active = (~solution.fixed_mask) & ((d_v_dx**2 + d_v_dy**2) > 1.0e-18)
    selected = dot[active]
    max_dot = float(np.max(selected))
    positive_fraction = float(np.mean(selected > 1.0e-12))
    return {
        "gradient_sign": gradient_sign,
        "max_e_dot_grad_v": max_dot,
        "positive_fraction": positive_fraction,
        "expected": "E·grad(V) <= 0",
        "passed": bool(max_dot <= 1.0e-10),
    }


def _sample_values(solution: Solution, points: Iterable[tuple[float, float]]) -> list[float]:
    values: list[float] = []
    for x_fraction, y_fraction in points:
        i = int(round(x_fraction * (len(solution.x_m) - 1)))
        j = int(round(y_fraction * (len(solution.y_m) - 1)))
        values.append(float(solution.potential[j, i]))
    return values


def grid_convergence(config: TankConfig) -> tuple[list[dict[str, float]], dict[str, float]]:
    """比较三档网格在同一批无量纲位置上的电势。"""

    points = [(0.20, 0.50), (0.40, 0.50), (0.40, 0.80), (0.80, 0.50)]
    rows: list[dict[str, float]] = []
    solutions: list[Solution] = []
    for nx, ny in ((81, 61), (121, 91), (161, 121)):
        problem = make_finite_plate_problem(config, nx, ny)
        solution = solve_laplace(*problem)
        solutions.append(solution)
        values = _sample_values(solution, points)
        row: dict[str, float] = {
            "nx": float(nx),
            "ny": float(ny),
            "iterations": float(solution.iterations),
            "max_update_v": solution.max_update_v,
        }
        for index, value in enumerate(values, start=1):
            row[f"sample_{index}_v"] = value
        rows.append(row)

    coarse = np.array(_sample_values(solutions[0], points))
    medium = np.array(_sample_values(solutions[1], points))
    fine = np.array(_sample_values(solutions[2], points))
    coarse_medium = np.abs(coarse - medium)
    medium_fine = np.abs(medium - fine)
    comparison = {
        "max_sample_difference_v": float(np.max(np.abs(coarse - fine))),
        "rms_sample_difference_v": float(np.sqrt(np.mean((coarse - fine) ** 2))),
        "coarse_to_medium_max_sample_difference_v": float(np.max(coarse_medium)),
        "medium_to_fine_max_sample_difference_v": float(np.max(medium_fine)),
        "max_successive_sample_difference_v": float(
            max(np.max(coarse_medium), np.max(medium_fine))
        ),
    }
    return rows, comparison


def analytic_parallel_plate_check() -> dict[str, float]:
    """用 V(x) 的线性解析解检验求解器，而不是用彩图自证正确。"""

    width_m, height_m = 0.30, 0.20
    left_v, right_v = 5.0, -5.0
    problem = make_boundary_plate_problem(
        width_m, height_m, left_v, right_v, nx=121, ny=81
    )
    solution = solve_laplace(*problem)
    exact_line = left_v + (right_v - left_v) * solution.x_m / width_m
    exact = np.repeat(exact_line[np.newaxis, :], len(solution.y_m), axis=0)
    error = solution.potential - exact
    return {
        "max_abs_error_v": float(np.max(np.abs(error))),
        "rms_error_v": float(np.sqrt(np.mean(error**2))),
        "iterations": float(solution.iterations),
    }


def analytic_harmonic_2d_check() -> dict[str, float]:
    """用 V=x^2-y^2 检查真正二维且 dx!=dy 的加权差分实现。"""

    x_m = np.linspace(-1.5, 1.5, 73)
    y_m = np.linspace(-1.0, 1.0, 45)
    x_grid, y_grid = np.meshgrid(x_m, y_m)
    exact = x_grid**2 - y_grid**2
    fixed_mask = np.zeros_like(exact, dtype=bool)
    fixed_mask[0, :] = True
    fixed_mask[-1, :] = True
    fixed_mask[:, 0] = True
    fixed_mask[:, -1] = True
    fixed_values = np.zeros_like(exact)
    fixed_values[fixed_mask] = exact[fixed_mask]
    solution = solve_laplace(fixed_mask, fixed_values, x_m, y_m)
    error = solution.potential - exact
    return {
        "max_abs_error_v": float(np.max(np.abs(error))),
        "rms_error_v": float(np.sqrt(np.mean(error**2))),
        "dx_m": solution.dx_m,
        "dy_m": solution.dy_m,
        "iterations": float(solution.iterations),
    }


def potential_reference_shift_check(config: TankConfig) -> dict[str, float | bool]:
    """同时平移两电极电势时，电势整体平移而电场不变。"""

    shift_v = 7.0
    base = solve_laplace(*make_finite_plate_problem(config, nx=81, ny=61))
    shifted_config = replace(
        config, high_v=config.high_v + shift_v, low_v=config.low_v + shift_v
    )
    shifted = solve_laplace(
        *make_finite_plate_problem(shifted_config, nx=81, ny=61)
    )
    offset_error = shifted.potential - base.potential - shift_v
    base_ex, base_ey = electric_field(base)
    shifted_ex, shifted_ey = electric_field(shifted)
    field_error = np.hypot(shifted_ex - base_ex, shifted_ey - base_ey)
    max_offset_error_v = float(np.max(np.abs(offset_error)))
    max_field_error_v_per_m = float(np.max(field_error))
    return {
        "applied_shift_v": shift_v,
        "max_potential_offset_error_v": max_offset_error_v,
        "max_field_difference_v_per_m": max_field_error_v_per_m,
        "passed": bool(
            max_offset_error_v <= 2.0e-6 and max_field_error_v_per_m <= 2.0e-3
        ),
    }


def _mask_near_electrodes(fixed_mask: np.ndarray) -> np.ndarray:
    """屏蔽电极节点及一格邻域，避免把差分值误画成导体内电场。"""

    padded = np.pad(fixed_mask, 1, mode="constant", constant_values=False)
    expanded = np.zeros_like(fixed_mask)
    for dj in range(3):
        for di in range(3):
            expanded |= padded[dj : dj + fixed_mask.shape[0], di : di + fixed_mask.shape[1]]
    return expanded


def save_main_figure(solution: Solution, output_path: Path) -> None:
    x_cm, y_cm = solution.x_m * 100.0, solution.y_m * 100.0
    ex, ey = electric_field(solution)
    vector_mask = _mask_near_electrodes(solution.fixed_mask)
    ex_plot = np.where(vector_mask, np.nan, ex)
    ey_plot = np.where(vector_mask, np.nan, ey)
    electrode_values = solution.fixed_values[solution.fixed_mask]
    low_v = float(np.min(electrode_values))
    high_v = float(np.max(electrode_values))

    fig, ax = plt.subplots(figsize=(10.5, 6.6), constrained_layout=True)
    image = ax.pcolormesh(
        x_cm,
        y_cm,
        solution.potential,
        shading="auto",
        cmap="coolwarm",
        vmin=low_v,
        vmax=high_v,
    )
    levels = np.linspace(low_v, high_v, 21)[1:-1]
    contours = ax.contour(x_cm, y_cm, solution.potential, levels=levels, colors="black", linewidths=0.55)
    ax.clabel(contours, inline=True, fontsize=7, fmt="%.1f V")
    ax.streamplot(
        x_cm,
        y_cm,
        ex_plot,
        ey_plot,
        color="white",
        linewidth=0.8,
        density=1.35,
        arrowsize=0.8,
    )
    electrode_y, electrode_x = np.where(solution.fixed_mask)
    values = solution.fixed_values[electrode_y, electrode_x]
    high = np.isclose(values, high_v)
    low = np.isclose(values, low_v)
    ax.scatter(
        x_cm[electrode_x[high]],
        y_cm[electrode_y[high]],
        c="#7f0000",
        s=9,
        label=f"{high_v:g} V 高电势电极",
    )
    ax.scatter(
        x_cm[electrode_x[low]],
        y_cm[electrode_y[low]],
        c="#08306b",
        s=9,
        label=f"{low_v:g} V 低电势电极",
    )
    ax.set(
        title="有限水槽中的电势、等势线与电场（示例预测图）",
        xlabel="x / cm",
        ylabel="y / cm",
        aspect="equal",
    )
    ax.legend(loc="upper right")
    colorbar = fig.colorbar(image, ax=ax, label="电势 V / V")
    colorbar.ax.tick_params(labelsize=8)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def save_direction_comparison(solution: Solution, output_path: Path) -> None:
    x_cm, y_cm = solution.x_m * 100.0, solution.y_m * 100.0
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.8), constrained_layout=True)
    for ax, sign, title in (
        (axes[0], -1.0, "通过：E = -grad(V)"),
        (axes[1], +1.0, "故意错误：E = +grad(V)"),
    ):
        ex, ey = electric_field(solution, gradient_sign=sign)
        vector_mask = _mask_near_electrodes(solution.fixed_mask)
        ex = np.where(vector_mask, np.nan, ex)
        ey = np.where(vector_mask, np.nan, ey)
        ax.contour(x_cm, y_cm, solution.potential, levels=17, colors="#444444", linewidths=0.55)
        skip = (slice(None, None, 7), slice(None, None, 7))
        ax.quiver(
            x_cm[skip[1]],
            y_cm[skip[0]],
            ex[skip],
            ey[skip],
            color="#1f77b4" if sign < 0 else "#c62828",
            pivot="mid",
        )
        ax.set(title=title, xlabel="x / cm", ylabel="y / cm", aspect="equal")
    fig.suptitle("同一电势图，梯度符号写错会让箭头整体反向")
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def snapped_electrode_geometry(solution: Solution) -> dict[str, dict[str, float]]:
    """记录配置值吸附到规则网格后的实际电极坐标。"""

    selected_values = solution.fixed_values[solution.fixed_mask]
    high_v = float(np.max(selected_values))
    low_v = float(np.min(selected_values))
    result: dict[str, dict[str, float]] = {}
    for name, value in (("high", high_v), ("low", low_v)):
        mask = solution.fixed_mask & np.isclose(solution.fixed_values, value)
        js, is_ = np.where(mask)
        result[name] = {
            "potential_v": value,
            "x_m": float(np.mean(solution.x_m[is_])),
            "y_min_m": float(np.min(solution.y_m[js])),
            "y_max_m": float(np.max(solution.y_m[js])),
            "node_count": float(len(js)),
        }
    return result


def run(output_dir: Path, config_path: Path | None = None) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if config_path is None:
        config_path = Path(__file__).resolve().parent / "case_finite_parallel_plates.json"
    config, case_document = load_case_config(config_path)
    correct_boundary = boundary_definition_audit(config)
    if not correct_boundary["passed"]:
        raise ValueError(f"案例边界定义未通过预检：{correct_boundary}")
    problem = make_finite_plate_problem(config, nx=161, ny=121)
    tolerance_v = 1.0e-8
    max_iterations = 40_000
    omega = 1.85
    solution = solve_laplace(
        *problem,
        tolerance_v=tolerance_v,
        max_iterations=max_iterations,
        omega=omega,
    )

    residual = stencil_residual(solution)
    symmetry_tolerance_v = 1.0e-6
    symmetry = symmetry_errors(solution, tolerance_v=symmetry_tolerance_v)
    boundary = boundary_errors(solution)
    wall = insulating_wall_errors(solution)
    maximum_principle = maximum_principle_audit(solution)
    flux_balance = electrode_flux_balance(solution)
    correct_direction = field_direction_audit(solution, gradient_sign=-1.0)
    wrong_direction = field_direction_audit(solution, gradient_sign=+1.0)
    correct_antialignment = field_antialignment_audit(solution, gradient_sign=-1.0)
    wrong_antialignment = field_antialignment_audit(solution, gradient_sign=+1.0)
    wrong_boundary = boundary_definition_audit(
        replace(config, high_v=config.high_v, low_v=config.high_v)
    )
    convergence_rows, convergence = grid_convergence(config)
    analytic = analytic_parallel_plate_check()
    analytic_2d = analytic_harmonic_2d_check()
    reference_shift = potential_reference_shift_check(config)

    save_main_figure(solution, output_dir / "静电场_Python预测_有限平行板.png")
    save_direction_comparison(solution, output_dir / "静电场_正确与错误方向对照.png")

    csv_path = output_dir / "静电场_网格收敛.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(convergence_rows[0].keys()))
        writer.writeheader()
        writer.writerows(convergence_rows)

    acceptance = {
        "prototype_identity": {
            "created": "2026-09-02",
            "status": "internally_verified_not_externally_validated_or_classroom_tested",
            "statement": "新建 Python 独立路线，不是旧 COMSOL 工程复原，也不含虚构实测点；当前尺寸为方法演示值，尚未按实物测绘定标。",
            "case_id": case_document.get("case_id"),
            "case_status": case_document.get("status"),
            "config_path": str(config_path.resolve()),
            "source_sha256": _sha256(Path(__file__).resolve()),
            "config_sha256": _sha256(config_path.resolve()),
            "runtime": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "matplotlib": matplotlib.__version__,
                "platform": platform.platform(),
            },
        },
        "config": asdict(config),
        "snapped_electrode_geometry": snapped_electrode_geometry(solution),
        "solver": {
            "grid": [len(solution.x_m), len(solution.y_m)],
            "initialization": "mean_of_fixed_boundary_potentials",
            "initial_free_potential_v": float(
                np.mean(problem[1][problem[0]])
            ),
            "iterations": solution.iterations,
            "max_update_v": solution.max_update_v,
            "tolerance_v": tolerance_v,
            "max_iterations": max_iterations,
            "omega": omega,
        },
        "checks": {
            "fixed_boundary": boundary,
            "insulating_outer_wall": wall,
            "stencil_residual": residual,
            "symmetry": symmetry,
            "maximum_principle": maximum_principle,
            "electrode_flux_balance": flux_balance,
            "grid_convergence": convergence,
            "analytic_parallel_plate": analytic,
            "analytic_harmonic_2d_unequal_spacing": analytic_2d,
            "potential_reference_shift": reference_shift,
            "correct_field_direction": correct_direction,
            "intentional_wrong_field_direction": wrong_direction,
            "correct_field_antialignment": correct_antialignment,
            "intentional_wrong_field_antialignment": wrong_antialignment,
            "correct_boundary_definition": correct_boundary,
            "intentional_equal_potential_boundary_definition": wrong_boundary,
        },
        "thresholds": {
            "fixed_potential_max_v": 1.0e-12,
            "insulating_wall_max_normal_gradient_v_per_m": 1.0e-10,
            "stencil_residual_max_abs_v": 1.0e-7,
            "symmetry_max_v": symmetry_tolerance_v,
            "grid_max_successive_sample_difference_v": 5.0e-2,
            "analytic_max_abs_error_v": 2.0e-5,
            "harmonic_2d_max_abs_error_v": 2.0e-5,
            "electrode_flux_relative_imbalance": 5.0e-3,
        },
    }
    checks = acceptance["checks"]
    thresholds = acceptance["thresholds"]
    passed = bool(
        boundary["fixed_potential_max_v"] <= thresholds["fixed_potential_max_v"]
        and wall["max_normal_gradient_v_per_m"]
        <= thresholds["insulating_wall_max_normal_gradient_v_per_m"]
        and residual["max_abs_v"] <= thresholds["stencil_residual_max_abs_v"]
        and symmetry["passed"]
        and maximum_principle["passed"]
        and flux_balance["relative_imbalance"]
        <= thresholds["electrode_flux_relative_imbalance"]
        and convergence["max_successive_sample_difference_v"]
        <= thresholds["grid_max_successive_sample_difference_v"]
        and analytic["max_abs_error_v"] <= thresholds["analytic_max_abs_error_v"]
        and analytic_2d["max_abs_error_v"] <= thresholds["harmonic_2d_max_abs_error_v"]
        and reference_shift["passed"]
        and correct_direction["passed"]
        and not wrong_direction["passed"]
        and correct_antialignment["passed"]
        and not wrong_antialignment["passed"]
        and correct_boundary["passed"]
        and not wrong_boundary["passed"]
    )
    acceptance["overall_passed"] = passed
    report_path = output_dir / "静电场_验收报告.json"
    report_path.write_text(
        json.dumps(acceptance, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return acceptance


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "output",
        help="图件与验收记录输出目录",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parent / "case_finite_parallel_plates.json",
        help="独立案例配置JSON",
    )
    args = parser.parse_args()
    acceptance = run(args.output_dir, args.config)
    print(json.dumps(acceptance, ensure_ascii=False, indent=2))
    if not acceptance["overall_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
