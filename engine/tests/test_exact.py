from __future__ import annotations

import itertools
from typing import Any

import numpy as np
import pytest
from engine.optimize.celf import solve
from engine.optimize.exact import MAX_EXACT_CANDIDATES, reduce_instance, solve_exact
from engine.optimize.objective import CandidateInfluence, CoverageObjective

FloatArray = np.ndarray[Any, np.dtype[np.float64]]


def _influence(indices: list[int], deltas: list[float]) -> CandidateInfluence:
    return CandidateInfluence(np.array(indices, dtype="int64"), np.array(deltas, dtype="float64"))


def _small_instance() -> tuple[CoverageObjective, FloatArray]:
    rng = np.random.default_rng(7)
    n_candidates, n_population = 6, 10
    influences = []
    for _ in range(n_candidates):
        size = rng.integers(1, 4)
        indices = rng.choice(n_population, size=size, replace=False)
        deltas = rng.uniform(0.5, 5.0, size=size)
        influences.append(_influence(list(indices), list(deltas)))
    weight = rng.uniform(1.0, 10.0, size=n_population)
    costs = rng.uniform(100.0, 800.0, size=n_candidates)
    return CoverageObjective(influences=influences, weight=weight, n_population=n_population), costs


def _brute_force_optimum(objective: CoverageObjective, costs: FloatArray, budget: float) -> float:
    n = len(objective.influences)
    best = 0.0
    for r in range(n + 1):
        for subset in itertools.combinations(range(n), r):
            if sum(costs[i] for i in subset) > budget:
                continue
            best = max(best, objective.value(set(subset)))
    return best


def test_exact_solve_matches_brute_force_on_small_instance() -> None:
    """The MILP formulation must be exactly correct, not an approximation
    -- verified against real brute-force enumeration, not just internal
    consistency."""
    objective, costs = _small_instance()
    budget = float(costs.sum()) * 0.5

    exact = solve_exact(objective, costs, budget)
    brute_force = _brute_force_optimum(objective, costs, budget)

    assert exact.is_proven_optimal
    assert exact.objective_value == pytest.approx(brute_force, abs=1e-6)
    assert exact.cost_usd <= budget + 1e-6


def test_exact_solution_value_matches_recomputed_value() -> None:
    """The selected set's value, recomputed independently via
    CoverageObjective.value(), must match HiGHS's reported objective --
    confirming the z-variable formulation truly reproduces max-coverage,
    not merely a plausible-looking linear relaxation."""
    objective, costs = _small_instance()
    budget = float(costs.sum()) * 0.6
    exact = solve_exact(objective, costs, budget)
    recomputed = objective.value(set(exact.selected))
    assert recomputed == pytest.approx(exact.objective_value, abs=1e-6)


def test_reduce_instance_is_a_noop_below_the_cap() -> None:
    objective, costs = _small_instance()
    reduced_obj, reduced_costs, indices = reduce_instance(objective, costs, max_candidates=100)
    assert reduced_obj is objective
    assert len(reduced_obj.influences) == len(objective.influences)
    assert list(indices) == list(range(len(objective.influences)))


def test_reduce_instance_keeps_highest_standalone_gain_candidates() -> None:
    objective, costs = _small_instance()
    reduced_obj, reduced_costs, indices = reduce_instance(objective, costs, max_candidates=3)
    assert len(reduced_obj.influences) == 3
    zero_max = np.zeros(objective.n_population)
    all_gains = sorted((objective.marginal_gain(i, zero_max) for i in range(len(costs))), reverse=True)
    kept_gains = sorted(objective.marginal_gain(int(i), zero_max) for i in indices)
    assert kept_gains == sorted(all_gains[:3])


def test_solve_exact_rejects_instance_above_the_cap() -> None:
    influences = [CandidateInfluence(np.array([0], dtype="int64"), np.array([1.0])) for _ in range(MAX_EXACT_CANDIDATES + 1)]
    objective = CoverageObjective(influences=influences, weight=np.array([1.0]), n_population=1)
    costs = np.ones(MAX_EXACT_CANDIDATES + 1)
    with pytest.raises(ValueError, match="exceeds MAX_EXACT_CANDIDATES"):
        solve_exact(objective, costs, budget_usd=10.0)


def test_greedy_at_least_063_of_exact_on_small_instance() -> None:
    """The Phase 6 DoD property test, checked against the real MILP exact
    solver rather than brute force -- the two should agree, but this
    exercises the actual solver the pipeline uses."""
    objective, costs = _small_instance()
    budget = float(costs.sum()) * 0.5

    greedy_picks = list(solve(objective, costs, budget))
    greedy_value = greedy_picks[-1].cumulative_value if greedy_picks else 0.0
    exact = solve_exact(objective, costs, budget)

    assert exact.objective_value > 0
    assert greedy_value / exact.objective_value >= 0.63
