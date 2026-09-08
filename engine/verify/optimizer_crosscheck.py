"""§7.2.3 -- independent optimizer verification (COOLBLOCK-BUILD-PLAN.md):
"Run NMaximize on a reduced instance in a completely separate mathematical
system and confirm it agrees with CP-SAT. Two independent solvers
agreeing is a real engineering practice."

**Substituted per `docs/adr/0002-*.md`'s decision, made at Phase 0**: no
Wolfram Cloud credential was in hand, so this ships with the fallback the
plan itself specifies -- "a second, independent Python solver in place of
the Wolfram `NMaximize` cross-check." That solver is `engine.optimize.exact`
(an exact MILP formulation solved with HiGHS, E2's "second solver"), which
already exists and is independently verified against real brute-force
enumeration (`engine/tests/test_exact.py`). What this module adds is the
missing piece ADR-0002 calls out explicitly: *"`engine.verify` must be
written against an interface... checked at Phase 6/10 rather than
assumed"* -- until now, the CELF-vs-exact agreement on the real
candidate universe (`docs/METHODOLOGY.md`'s "E2 (second solver)" table,
99.6-99.9%) was measured once, by hand, in a notebook. This formalizes it
as real, reusable, tested code, callable the same way at any time -- not
prose that could silently drift from what the code actually does.

Genuinely two different algorithms, not one solver called twice: CELF's
cost-effective greedy (a heuristic with a provable but weak worst-case
bound) versus HiGHS's branch-and-bound MILP solver (an exact, general-
purpose optimizer with no knowledge of "greedy" or "submodular" at all).
Agreement between them on real data is real evidence, not a tautology.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from engine.optimize.celf import solve as celf_solve
from engine.optimize.exact import reduce_instance, solve_exact
from engine.optimize.objective import CoverageObjective

FloatArray = np.ndarray[Any, np.dtype[np.float64]]

# Measured on the real candidate universe (docs/METHODOLOGY.md): CELF
# reaches 99.6-99.9% of the proven exact optimum. 95% is a real margin
# below that measurement, not tuned to just barely pass -- this catches a
# genuine regression (a broken objective, a mis-wired constraint) without
# being so tight that ordinary floating-point/solve-order variation trips
# it on an unrelated change.
DEFAULT_AGREEMENT_TOLERANCE = 0.95


@dataclass(frozen=True)
class CrossCheckResult:
    greedy_value: float
    exact_value: float
    ratio: float
    is_proven_optimal: bool
    agrees_within_tolerance: bool
    n_candidates_in_reduced_instance: int
    exact_solve_time_s: float


def cross_check_optimizer(
    objective: CoverageObjective,
    costs: FloatArray,
    budget_usd: float,
    tolerance: float = DEFAULT_AGREEMENT_TOLERANCE,
    time_limit_s: float = 30.0,
) -> CrossCheckResult:
    """Solves the same instance two genuinely independent ways -- CELF
    greedy (`engine.optimize.celf`) and HiGHS's exact MILP
    (`engine.optimize.exact`, on the same `reduce_instance()`-selected
    reduced candidate set both solvers see) -- and reports whether they
    agree within `tolerance`. Raises nothing on disagreement; the caller
    (a test, a CI check, a one-off script) decides what to do with a
    `CrossCheckResult` whose `agrees_within_tolerance` is `False` --
    exactly the same "surface it, don't silently swallow it" posture as
    L6's provenance guard and every other honesty-rail check in this
    project."""
    reduced_objective, reduced_costs, _ = reduce_instance(objective, costs)

    exact = solve_exact(reduced_objective, reduced_costs, budget_usd, time_limit_s=time_limit_s)

    greedy_picks = list(celf_solve(reduced_objective, reduced_costs, budget_usd))
    greedy_value = greedy_picks[-1].cumulative_value if greedy_picks else 0.0

    ratio = (greedy_value / exact.objective_value) if exact.objective_value > 0 else 1.0

    return CrossCheckResult(
        greedy_value=greedy_value,
        exact_value=exact.objective_value,
        ratio=ratio,
        is_proven_optimal=exact.is_proven_optimal,
        agrees_within_tolerance=ratio >= tolerance,
        n_candidates_in_reduced_instance=len(reduced_objective.influences),
        exact_solve_time_s=exact.solve_time_s,
    )
