from __future__ import annotations

import itertools
from typing import Any

import numpy as np
from engine.optimize.best_plan import best_plan, order_by_contribution
from engine.optimize.celf import solve
from engine.optimize.objective import CandidateInfluence, CoverageObjective

FloatArray = np.ndarray[Any, np.dtype[np.float64]]


def _instance(
    seed: int, n_candidates: int = 8, n_population: int = 12
) -> tuple[CoverageObjective, FloatArray]:
    rng = np.random.default_rng(seed)
    influences = []
    for _ in range(n_candidates):
        size = int(rng.integers(1, 5))
        indices = rng.choice(n_population, size=size, replace=False)
        deltas = rng.uniform(0.5, 5.0, size=size)
        influences.append(CandidateInfluence(indices.astype("int64"), deltas.astype("float64")))
    weight = rng.uniform(1.0, 10.0, size=n_population)
    costs: FloatArray = rng.uniform(100.0, 800.0, size=n_candidates)
    return CoverageObjective(influences=influences, weight=weight, n_population=n_population), costs


def _brute_force_optimum(objective: CoverageObjective, costs: FloatArray, budget: float) -> float:
    n = len(objective.influences)
    best = 0.0
    for r in range(n + 1):
        for subset in itertools.combinations(range(n), r):
            if sum(costs[i] for i in subset) <= budget:
                best = max(best, objective.value(set(subset)))
    return best


def test_small_pool_gets_the_proven_optimal_plan_not_the_greedy_one() -> None:
    """The whole point of docs/adr/0028-*.md: when the optimum can be
    proven in seconds, that -- not greedy's guarantee -- is what a user
    gets. Checked against exhaustive enumeration, so the claim doesn't
    rest on the MILP being its own witness."""
    for seed in (1, 2, 3, 5, 8):
        objective, costs = _instance(seed)
        budget = float(costs.sum() * 0.4)
        plan = best_plan(objective, costs, budget)
        assert plan.solver == "exact_milp"
        assert plan.proven_optimal
        assert (
            plan.value == 0.0 or plan.value >= _brute_force_optimum(objective, costs, budget) - 1e-6
        )
        assert plan.cost_usd <= budget + 1e-6


def test_plan_is_never_worse_than_greedy() -> None:
    for seed in (11, 12, 13):
        objective, costs = _instance(seed)
        budget = float(costs.sum() * 0.3)
        greedy = list(solve(objective, costs, budget))
        greedy_value = greedy[-1].cumulative_value if greedy else 0.0
        assert best_plan(objective, costs, budget).value >= greedy_value - 1e-6


def test_pool_too_large_to_prove_falls_back_to_celf_and_says_so() -> None:
    """A bigger pool (private cool roofs, thousands of candidates) must not
    hang or fail -- it gets the greedy plan, labeled greedy."""
    objective, costs = _instance(21)
    budget = float(costs.sum() * 0.3)
    plan = best_plan(objective, costs, budget, exact_pool_limit=3)
    assert plan.solver == "celf"
    assert not plan.proven_optimal
    assert [p.candidate_index for p in plan.picks] == [
        p.candidate_index for p in solve(objective, costs, budget)
    ]


def test_sites_are_ordered_so_each_one_adds_the_most_cooling_left() -> None:
    """The ranked table and the sites-landing-one-at-a-time animation read
    top-down, so the emitted order has to be a real contribution order with
    running totals that end at the plan's own value."""
    objective, costs = _instance(4)
    budget = float(costs.sum() * 0.5)
    plan = best_plan(objective, costs, budget)
    gains = [p.marginal_gain for p in plan.picks]
    assert gains == sorted(gains, reverse=True)
    assert plan.picks[-1].cumulative_value == sum(gains)
    assert abs(plan.value - objective.value({p.candidate_index for p in plan.picks})) < 1e-6


def test_ordering_an_empty_selection_is_an_empty_plan_not_a_crash() -> None:
    objective, costs = _instance(6)
    assert order_by_contribution(objective, costs, frozenset()) == []
    empty = best_plan(objective, costs, 0.0)
    assert empty.picks == []
    assert empty.value == 0.0 and empty.cost_usd == 0.0
