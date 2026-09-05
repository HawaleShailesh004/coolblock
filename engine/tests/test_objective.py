from __future__ import annotations

import numpy as np
import pytest
from engine.optimize.objective import CandidateInfluence, CoverageObjective


def _influence(indices: list[int], deltas: list[float]) -> CandidateInfluence:
    return CandidateInfluence(np.array(indices, dtype="int64"), np.array(deltas, dtype="float64"))


def test_disjoint_candidates_sum_linearly() -> None:
    """When two candidates influence entirely different population points,
    the coverage function must reduce to plain addition -- overlap
    handling should never under-count non-overlapping benefit."""
    objective = CoverageObjective(
        influences=[_influence([0], [2.0]), _influence([1], [3.0])],
        weight=np.array([1.0, 1.0]),
        n_population=2,
    )
    assert objective.value({0}) == pytest.approx(2.0)
    assert objective.value({1}) == pytest.approx(3.0)
    assert objective.value({0, 1}) == pytest.approx(5.0)


def test_overlapping_candidates_do_not_double_count() -> None:
    """Two candidates covering the *same* population point: selecting both
    must yield max(delta_t), not their sum -- this is the whole point of
    the coverage-function objective (COOLBLOCK-BUILD-PLAN.md §6.5 E1's
    'two trees 8m apart do not deliver double the cooling')."""
    objective = CoverageObjective(
        influences=[_influence([0], [2.0]), _influence([0], [5.0])],
        weight=np.array([1.0]),
        n_population=1,
    )
    assert objective.value({0}) == pytest.approx(2.0)
    assert objective.value({1}) == pytest.approx(5.0)
    combined = objective.value({0, 1})
    assert combined == pytest.approx(5.0)  # max, not 7.0
    assert combined < 2.0 + 5.0


def test_marginal_gain_matches_value_difference() -> None:
    objective = CoverageObjective(
        influences=[_influence([0, 1], [2.0, 1.0]), _influence([1, 2], [4.0, 3.0])],
        weight=np.array([1.0, 1.0, 1.0]),
        n_population=3,
    )
    current_max = np.zeros(3)
    gain0 = objective.marginal_gain(0, current_max)
    assert gain0 == pytest.approx(objective.value({0}))
    objective.apply(0, current_max)

    gain1 = objective.marginal_gain(1, current_max)
    assert gain1 == pytest.approx(objective.value({0, 1}) - objective.value({0}))


def test_submodularity_diminishing_returns() -> None:
    """Candidate 1's marginal gain after candidate 0 is already selected
    must not exceed its marginal gain against the empty set -- the
    defining diminishing-returns property of a submodular function."""
    objective = CoverageObjective(
        influences=[_influence([0, 1], [3.0, 3.0]), _influence([1, 2], [4.0, 2.0])],
        weight=np.array([1.0, 1.0, 1.0]),
        n_population=3,
    )
    empty = np.zeros(3)
    gain_alone = objective.marginal_gain(1, empty)

    after_zero = np.zeros(3)
    objective.apply(0, after_zero)
    gain_after = objective.marginal_gain(1, after_zero)

    assert gain_after <= gain_alone + 1e-9
    assert gain_after < gain_alone  # candidate 0 already covers point 1 at delta_t=3.0, capping candidate 1's gain there


def test_negative_weight_is_never_constructed_by_build() -> None:
    """OPTIMIZER_HVI_FLOOR must keep every population weight non-negative
    -- a negative weight would break monotonicity (adding coverage could
    lower the objective), violating the Phase 6 DoD's own 'benefit
    monotone in budget' property test."""
    from engine.optimize.objective import OPTIMIZER_HVI_FLOOR

    assert OPTIMIZER_HVI_FLOOR >= 0.0
