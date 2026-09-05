from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from engine.optimize.frontier import compute_efficient_frontier, default_budget_sweep
from engine.optimize.objective import CandidateInfluence, CoverageObjective

FloatArray = np.ndarray[Any, np.dtype[np.float64]]


def _influence(indices: list[int], deltas: list[float]) -> CandidateInfluence:
    return CandidateInfluence(np.array(indices, dtype="int64"), np.array(deltas, dtype="float64"))


def _instance() -> tuple[CoverageObjective, FloatArray]:
    rng = np.random.default_rng(11)
    n_candidates, n_population = 15, 12
    influences = []
    for _ in range(n_candidates):
        size = rng.integers(1, 4)
        indices = rng.choice(n_population, size=size, replace=False)
        deltas = rng.uniform(0.5, 5.0, size=size)
        influences.append(_influence(list(indices), list(deltas)))
    weight = rng.uniform(1.0, 10.0, size=n_population)
    costs = rng.uniform(50.0, 400.0, size=n_candidates)
    return CoverageObjective(influences=influences, weight=weight, n_population=n_population), costs


def test_default_budget_sweep_spans_the_plans_range() -> None:
    sweep = default_budget_sweep()
    assert sweep[0] == pytest.approx(5_000.0)
    assert sweep[-1] == pytest.approx(500_000.0)
    assert sweep == sorted(sweep)


def test_frontier_value_is_monotone_nondecreasing_in_budget() -> None:
    """Diminishing returns, not decreasing ones -- more budget must never
    produce a lower value, even though re-solving fresh at each point
    means picks are not guaranteed nested."""
    objective, costs = _instance()
    budgets = [float(costs.sum()) * f for f in (0.1, 0.3, 0.5, 0.7, 1.0)]
    points = compute_efficient_frontier(objective, costs, budgets_usd=budgets)
    values = [p.objective_value for p in points]
    assert all(b >= a - 1e-9 for a, b in zip(values, values[1:], strict=False))


def test_frontier_never_exceeds_its_own_budget() -> None:
    objective, costs = _instance()
    budgets = [float(costs.sum()) * f for f in (0.2, 0.6, 1.0)]
    points = compute_efficient_frontier(objective, costs, budgets_usd=budgets)
    for p in points:
        assert p.cost_usd <= p.budget_usd + 1e-6


def test_marginal_value_is_computed_relative_to_the_previous_point() -> None:
    objective, costs = _instance()
    budgets = [100.0, 200.0, 300.0]
    points = compute_efficient_frontier(objective, costs, budgets_usd=budgets)
    assert points[0].marginal_value_per_1000usd == pytest.approx(points[0].objective_value / (100.0 / 1000.0))
    expected_second = (points[1].objective_value - points[0].objective_value) / (100.0 / 1000.0)
    assert points[1].marginal_value_per_1000usd == pytest.approx(expected_second)


def test_zero_budget_frontier_point_is_zero() -> None:
    objective, costs = _instance()
    points = compute_efficient_frontier(objective, costs, budgets_usd=[0.0, 100.0])
    assert points[0].objective_value == 0.0
    assert points[0].n_candidates_selected == 0
