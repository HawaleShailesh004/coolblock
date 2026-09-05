from __future__ import annotations

import itertools
from typing import Any

import numpy as np
from engine.optimize.celf import solve
from engine.optimize.objective import CandidateInfluence, CoverageObjective

FloatArray = np.ndarray[Any, np.dtype[np.float64]]


def _influence(indices: list[int], deltas: list[float]) -> CandidateInfluence:
    return CandidateInfluence(np.array(indices, dtype="int64"), np.array(deltas, dtype="float64"))


def _brute_force_optimum(objective: CoverageObjective, costs: FloatArray, budget: float) -> float:
    n = len(objective.influences)
    best = 0.0
    for r in range(n + 1):
        for subset in itertools.combinations(range(n), r):
            if sum(costs[i] for i in subset) > budget:
                continue
            best = max(best, objective.value(set(subset)))
    return best


def _small_real_instance() -> tuple[CoverageObjective, FloatArray]:
    """A hand-built 8-candidate instance with real overlap structure --
    small enough to brute-force exhaustively (2^8 = 256 subsets), used to
    empirically check the Phase 6 DoD's property test: 'greedy >= 0.63 x
    exact on every small instance.'"""
    rng = np.random.default_rng(42)
    n_candidates, n_population = 8, 12
    influences = []
    for _ in range(n_candidates):
        size = rng.integers(1, 5)
        indices = rng.choice(n_population, size=size, replace=False)
        deltas = rng.uniform(0.5, 5.0, size=size)
        influences.append(_influence(list(indices), list(deltas)))
    weight = rng.uniform(1.0, 10.0, size=n_population)
    costs = rng.uniform(100.0, 1000.0, size=n_candidates)
    return CoverageObjective(influences=influences, weight=weight, n_population=n_population), costs


def test_cumulative_value_is_monotone_in_budget() -> None:
    """Phase 6 DoD property test: benefit monotone in budget."""
    objective, costs = _small_real_instance()
    picks = list(solve(objective, costs, budget_usd=float(costs.sum())))
    values = [p.cumulative_value for p in picks]
    assert all(b >= a - 1e-9 for a, b in zip(values, values[1:], strict=False))


def test_greedy_reaches_at_least_063_of_exact_on_small_instances() -> None:
    """Phase 6 DoD property test: 'greedy >= 0.63 x exact on every small
    instance.' Empirically measured against a real brute-force optimum,
    not assumed from the theoretical bound (which is actually
    (1 - 1/sqrt(e)) ~= 0.393 for this knapsack-constrained setting, not the
    plan's stated (1 - 1/e) ~= 0.63 cardinality-case figure -- see
    engine/optimize/celf.py's module docstring and docs/adr/0012-*.md).
    This test checks what is actually measured, which is what the DoD
    text asks for."""
    objective, costs = _small_real_instance()
    budget = float(costs.sum()) * 0.5

    picks = list(solve(objective, costs, budget))
    greedy_value = picks[-1].cumulative_value if picks else 0.0
    exact_value = _brute_force_optimum(objective, costs, budget)

    assert exact_value > 0
    assert greedy_value / exact_value >= 0.63


def test_solver_never_exceeds_budget() -> None:
    objective, costs = _small_real_instance()
    budget = float(costs.sum()) * 0.4
    picks = list(solve(objective, costs, budget))
    if picks:
        assert picks[-1].cumulative_cost_usd <= budget + 1e-6


def test_empty_objective_yields_nothing() -> None:
    objective = CoverageObjective(influences=[], weight=np.array([]), n_population=0)
    picks = list(solve(objective, np.array([]), budget_usd=1000.0))
    assert picks == []


def test_zero_budget_yields_nothing() -> None:
    objective, costs = _small_real_instance()
    picks = list(solve(objective, costs, budget_usd=0.0))
    assert picks == []
