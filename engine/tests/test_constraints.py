from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from engine.optimize.celf import solve
from engine.optimize.constraints import (
    ANNUAL_MAINTENANCE_USD_PER_TREE,
    ConstraintConfig,
    annual_maintenance_cost,
    constrained_greedy,
)
from engine.optimize.objective import CandidateInfluence, CoverageObjective

FloatArray = np.ndarray[Any, np.dtype[np.float64]]


def _influence(indices: list[int], deltas: list[float]) -> CandidateInfluence:
    return CandidateInfluence(np.array(indices, dtype="int64"), np.array(deltas, dtype="float64"))


def _instance() -> tuple[CoverageObjective, FloatArray]:
    rng = np.random.default_rng(3)
    n_candidates, n_population = 20, 15
    influences = []
    for _ in range(n_candidates):
        size = rng.integers(1, 5)
        indices = rng.choice(n_population, size=size, replace=False)
        deltas = rng.uniform(0.5, 5.0, size=size)
        influences.append(_influence(list(indices), list(deltas)))
    weight = rng.uniform(1.0, 10.0, size=n_population)
    costs = rng.uniform(100.0, 800.0, size=n_candidates)
    return CoverageObjective(influences=influences, weight=weight, n_population=n_population), costs


def test_annual_maintenance_cost_is_zero_for_non_tree_types() -> None:
    types = ["street_tree", "cool_roof", "cool_pavement", "shade_structure", "park_lot_tree_cluster"]
    capacities = np.array([2.0, 1.0, 1.0, 1.0, 5.0])
    cost = annual_maintenance_cost(types, capacities)
    assert cost[0] == pytest.approx(2 * ANNUAL_MAINTENANCE_USD_PER_TREE)
    assert cost[4] == pytest.approx(5 * ANNUAL_MAINTENANCE_USD_PER_TREE)
    assert cost[1] == 0.0
    assert cost[2] == 0.0
    assert cost[3] == 0.0


def test_unconstrained_matches_celf_exactly() -> None:
    """The regression guard for the real bug caught during Phase 6
    development: an earlier version of constrained_greedy ranked by raw
    marginal gain instead of gain-per-dollar, understating the
    unconstrained value by 38% relative to CELF on real data. With no
    constraints active, this solver must reproduce CELF's value exactly."""
    objective, costs = _instance()
    budget = float(costs.sum()) * 0.4

    celf_picks = list(solve(objective, costs, budget))
    celf_value = celf_picks[-1].cumulative_value if celf_picks else 0.0

    result = constrained_greedy(objective, costs, ConstraintConfig(budget_usd=budget))
    assert result.objective_value == pytest.approx(celf_value, abs=1e-6)


def test_public_land_only_excludes_private_candidates() -> None:
    objective, costs = _instance()
    ownership = ["private" if i % 2 == 0 else "public_row" for i in range(len(costs))]
    budget = float(costs.sum())

    result = constrained_greedy(
        objective, costs, ConstraintConfig(budget_usd=budget, public_land_only=True), ownership=ownership
    )
    assert all(ownership[i] == "public_row" for i in result.selected)


def test_max_sites_per_zone_is_respected() -> None:
    objective, costs = _instance()
    zone_ids = ["A" if i < 10 else "B" for i in range(len(costs))]
    budget = float(costs.sum())

    result = constrained_greedy(
        objective, costs, ConstraintConfig(budget_usd=budget, max_sites_per_zone=2), zone_ids=zone_ids
    )
    assert all(count <= 2 for count in result.zone_site_counts.values())


def test_min_spend_per_zone_is_met_when_affordable() -> None:
    objective, costs = _instance()
    zone_ids = ["A" if i < 10 else "B" for i in range(len(costs))]
    floor = 200.0
    budget = float(costs.sum())

    result = constrained_greedy(
        objective, costs, ConstraintConfig(budget_usd=budget, min_spend_per_zone_usd=floor), zone_ids=zone_ids
    )
    for zone, spend in result.zone_spend_usd.items():
        assert spend >= floor - 1e-6 or spend == pytest.approx(sum(costs[i] for i in range(len(costs)) if zone_ids[i] == zone))


def test_mandatory_include_is_always_selected_if_affordable() -> None:
    objective, costs = _instance()
    budget = float(costs.sum())
    result = constrained_greedy(
        objective, costs, ConstraintConfig(budget_usd=budget, mandatory_include=frozenset({0}))
    )
    assert 0 in result.selected


def test_mandatory_exclude_is_never_selected() -> None:
    objective, costs = _instance()
    budget = float(costs.sum())
    result = constrained_greedy(
        objective, costs, ConstraintConfig(budget_usd=budget, mandatory_exclude=frozenset({0, 1, 2}))
    )
    assert not ({0, 1, 2} & result.selected)


def test_maintenance_cap_is_respected() -> None:
    objective, costs = _instance()
    maintenance = np.full(len(costs), 100.0)
    budget = float(costs.sum())
    cap = 250.0

    result = constrained_greedy(
        objective, costs, ConstraintConfig(budget_usd=budget, annual_maintenance_cap_usd=cap), maintenance_costs=maintenance
    )
    assert result.annual_maintenance_usd <= cap + 1e-6


def test_never_exceeds_budget() -> None:
    objective, costs = _instance()
    budget = float(costs.sum()) * 0.3
    result = constrained_greedy(objective, costs, ConstraintConfig(budget_usd=budget))
    assert result.cost_usd <= budget + 1e-6


def test_picks_record_true_commit_order_and_are_internally_consistent() -> None:
    """Phase 7 addition: the SSE live-solve stream needs a constrained
    solve's picks in the order `commit()` actually ran, with cumulative
    totals that agree with the final result -- not a re-sort by some
    other proxy ordering."""
    objective, costs = _instance()
    budget = float(costs.sum()) * 0.5
    result = constrained_greedy(objective, costs, ConstraintConfig(budget_usd=budget))

    assert {p.candidate_index for p in result.picks} == result.selected
    assert len(result.picks) == len(result.selected)  # no duplicate/dropped picks
    assert result.picks[-1].cumulative_cost_usd == pytest.approx(result.cost_usd)
    assert result.picks[-1].cumulative_value == pytest.approx(result.objective_value)
    # cumulative cost and value are both non-decreasing pick over pick
    for prev, curr in zip(result.picks, result.picks[1:], strict=False):
        assert curr.cumulative_cost_usd >= prev.cumulative_cost_usd
        assert curr.cumulative_value >= prev.cumulative_value - 1e-9
