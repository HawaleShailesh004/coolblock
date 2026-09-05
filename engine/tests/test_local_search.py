from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from engine.optimize.celf import solve
from engine.optimize.local_search import local_search
from engine.optimize.objective import CandidateInfluence, CoverageObjective

FloatArray = np.ndarray[Any, np.dtype[np.float64]]


def _influence(indices: list[int], deltas: list[float]) -> CandidateInfluence:
    return CandidateInfluence(np.array(indices, dtype="int64"), np.array(deltas, dtype="float64"))


def _instance_with_an_obvious_swap() -> tuple[CoverageObjective, FloatArray]:
    """A hand-built instance where greedy's ratio-first choice leaves an
    obvious improving swap on the table: candidate 0 is cheap but
    mediocre, candidate 1 is a little pricier but covers the same points
    much better and just barely doesn't fit once 0 and a filler candidate
    are both selected."""
    influences = [
        _influence([0, 1], [2.0, 2.0]),  # 0: cheap, mediocre
        _influence([0, 1], [5.0, 5.0]),  # 1: pricier, clearly better -- the "obvious swap"
        _influence([2], [1.0]),  # 2: filler, cheap
    ]
    weight = np.array([1.0, 1.0, 1.0])
    costs = np.array([10.0, 14.0, 5.0])
    return CoverageObjective(influences=influences, weight=weight, n_population=3), costs


def test_local_search_never_decreases_value() -> None:
    objective, costs = _instance_with_an_obvious_swap()
    budget = 15.0
    greedy_picks = list(solve(objective, costs, budget))
    greedy_selection = {p.candidate_index for p in greedy_picks}
    greedy_value = objective.value(greedy_selection)

    result = local_search(objective, costs, budget, greedy_selection)
    assert result.objective_value >= greedy_value - 1e-9


def test_local_search_finds_the_obvious_swap() -> None:
    """Candidate 0 (cheap, mediocre) should be swapped for candidate 1
    (better) once budget allows -- the textbook case local search exists
    to catch."""
    objective, costs = _instance_with_an_obvious_swap()
    budget = 14.0  # only fits one of {0, 1}, not both -- greedy's ratio pick may not be optimal alone
    result = local_search(objective, costs, budget, initial_selection={0})
    assert result.objective_value >= objective.value({1})


def test_local_search_never_exceeds_budget() -> None:
    objective, costs = _instance_with_an_obvious_swap()
    budget = 15.0
    result = local_search(objective, costs, budget, initial_selection={0, 2})
    assert result.cost_usd <= budget + 1e-6


def test_local_search_on_empty_selection_is_a_noop() -> None:
    objective, costs = _instance_with_an_obvious_swap()
    result = local_search(objective, costs, budget_usd=100.0, initial_selection=set())
    assert result.selected == frozenset()
    assert result.objective_value == pytest.approx(0.0)
    assert result.n_swaps_applied == 0
