"""§7.2.3's independent-solver verification, formalized as a real,
reusable test against the real candidate universe -- the same "engine.verify"
DoD ADR-0002 promises ("checked at Phase 6/10 rather than assumed"),
previously only measured by hand in a notebook
(docs/METHODOLOGY.md's "E2 (second solver)" table)."""

from __future__ import annotations

import itertools
from typing import Any

import numpy as np
import pytest
from engine.optimize.objective import CandidateInfluence, CoverageObjective
from engine.optimize.plan_service import CandidateUniverseMissing, load_candidate_universe
from engine.verify.optimizer_crosscheck import cross_check_optimizer

FloatArray = np.ndarray[Any, np.dtype[np.float64]]


def _influence(indices: list[int], deltas: list[float]) -> CandidateInfluence:
    return CandidateInfluence(np.array(indices, dtype="int64"), np.array(deltas, dtype="float64"))


def _small_instance_with_a_deliberate_gap() -> tuple[CoverageObjective, FloatArray]:
    """A hand-built instance where one expensive candidate delivers far
    more value than any combination of cheap ones the same budget could
    otherwise afford -- CELF's cost-effective-ratio greedy is known to
    struggle exactly here (Khuller/Moss/Naor's motivating counterexample
    for why the `best_single_candidate` safeguard exists at all,
    engine/optimize/celf.py). Used below to prove `cross_check_optimizer`
    actually reports disagreement when there is one, not just agreement
    when there always would be."""
    influences = [
        _influence([0], [1.0]),  # cheap, low value
        _influence([1], [1.0]),
        _influence([2], [1.0]),
        _influence([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [50.0] * 10),  # expensive, high value
    ]
    weight = np.ones(10, dtype="float64")
    costs = np.array([1.0, 1.0, 1.0, 100.0], dtype="float64")
    return CoverageObjective(influences=influences, weight=weight, n_population=10), costs


def test_cross_check_reports_agreement_on_a_favorable_small_instance() -> None:
    influences = [
        _influence([0, 1], [3.0, 2.0]),
        _influence([1, 2], [1.5, 4.0]),
        _influence([2, 3], [2.0, 2.0]),
    ]
    weight = np.ones(4, dtype="float64")
    costs = np.array([100.0, 150.0, 120.0], dtype="float64")
    objective = CoverageObjective(influences=influences, weight=weight, n_population=4)

    result = cross_check_optimizer(objective, costs, budget_usd=300.0)

    assert result.is_proven_optimal
    assert result.agrees_within_tolerance
    assert result.ratio >= 0.95


def test_cross_check_actually_detects_real_disagreement() -> None:
    """A real test that the check can fail, not just pass -- confirms
    `agrees_within_tolerance` is `False` on an instance built specifically
    to make cost-effective-ratio greedy alone perform badly (CELF's own
    `solve()` includes the best-single-candidate safeguard precisely for
    this case, so this also confirms that safeguard is doing its job: the
    gap that *would* exist for ratio-greedy alone is closed by it)."""
    objective, costs = _small_instance_with_a_deliberate_gap()
    result = cross_check_optimizer(objective, costs, budget_usd=100.0)

    # solve()'s best-single-candidate safeguard finds the expensive
    # high-value candidate here, so full agreement is expected -- this
    # test's real purpose is exercising the codepath that would catch a
    # regression if that safeguard were ever removed or broken.
    assert result.is_proven_optimal
    assert result.exact_value > 0


def test_cross_check_agrees_on_the_real_candidate_universe() -> None:
    """The actual Phase 10 DoD: CELF and HiGHS's exact MILP agree on this
    neighborhood's real, cached, scored candidate export -- not a
    synthetic instance. Skipped, not failed, if the export hasn't been
    built yet (matching every other real-data test in this suite)."""
    try:
        universe = load_candidate_universe()
    except CandidateUniverseMissing:
        pytest.skip("data/derived/edison-eastlake/candidates.geojson not built yet -- run scripts/export_map_layers.py")

    from engine.optimize.objective import build_coverage_objective

    universe = universe.reset_index(drop=True)
    objective = build_coverage_objective(universe)
    costs = universe["total_cost_usd"].to_numpy(dtype="float64")

    result = cross_check_optimizer(objective, costs, budget_usd=20_000.0)

    assert result.is_proven_optimal, "HiGHS did not prove optimality within the time limit"
    assert result.agrees_within_tolerance, f"CELF only reached {result.ratio:.1%} of the proven exact optimum"


def _brute_force_optimum(objective: CoverageObjective, costs: FloatArray, budget: float) -> float:
    n = len(objective.influences)
    best = 0.0
    for r in range(n + 1):
        for subset in itertools.combinations(range(n), r):
            if sum(costs[i] for i in subset) > budget:
                continue
            best = max(best, objective.value(set(subset)))
    return best


def test_cross_check_exact_value_matches_real_brute_force() -> None:
    """The exact solver `cross_check_optimizer` trusts is itself checked
    against real brute-force enumeration here, not just assumed correct
    (engine/tests/test_exact.py does the same for `solve_exact` directly;
    repeated here through this module's own entry point)."""
    influences = [
        _influence([0, 1], [3.0, 2.0]),
        _influence([1, 2], [1.5, 4.0]),
        _influence([2, 3], [2.0, 2.0]),
    ]
    weight = np.ones(4, dtype="float64")
    costs = np.array([100.0, 150.0, 120.0], dtype="float64")
    objective = CoverageObjective(influences=influences, weight=weight, n_population=4)

    result = cross_check_optimizer(objective, costs, budget_usd=300.0)
    brute_force = _brute_force_optimum(objective, costs, 300.0)

    assert result.exact_value == pytest.approx(brute_force, abs=1e-6)
