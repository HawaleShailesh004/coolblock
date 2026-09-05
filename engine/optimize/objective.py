"""E1 -- the submodular coverage objective (COOLBLOCK-BUILD-PLAN.md §6.5 E1).

D4's EWCB formula (`engine.impact.ewcb`) sums each candidate's benefit
independently -- correct for *reporting* one candidate's own effect, but
wrong as an optimizer objective: it would make selecting a *set* of
candidates just "sort by score, take the top ones under budget," which
the plan explicitly says is not what this problem is ("not solvable by
sorting sites by score"). Two trees 8m apart do not deliver double the
cooling at the point exactly between them -- their Gaussian ΔT fields
overlap, and a resident standing there is cooled by whichever nearby tree
helps them most, not by the sum of every tree that reaches them.

This module defines EWCB as a **weighted coverage function** instead:

    F(S) = Σ_p  weight(p) · max_{i ∈ S} ΔT_i(x_p)

Weighted coverage functions are a canonical example of a monotone
submodular set function (adding a candidate to S can only raise, never
lower, the max at any point, and the marginal gain from adding one more
candidate shrinks as S already covers more ground) -- this is the actual
mathematical structure the plan's "submodular maximization under a
knapsack constraint" claim needs, not an assertion.

**A real, disclosed conflict with D4 had to be resolved: HVI can be
negative.** D4's `weight(p)` intentionally keeps HVI's raw z-score sign
for transparent *reporting* (`docs/adr/0010-*.md`) -- a below-average-
vulnerability building can show a negative EWCB contribution. But a
coverage function with a negative-weighted point is not monotone: adding
a candidate that newly reaches that point would *decrease* F(S), which
breaks both CELF's approximation guarantee and the Phase 6 DoD's own
"benefit monotone in budget" property test. For this module only,
`weight(p)` clips HVI at a floor of 0 (`OPTIMIZER_HVI_FLOOR`): a
below-average-vulnerability building contributes zero optimizer weight
(no penalty, no reward) rather than a negative one. D4's own reported
EWCB numbers are untouched by this -- this is strictly an internal
requirement of the optimizer's objective, not a change to what gets
reported per candidate.

**Population attribution inherits D4's disclosed scope exactly.**
`cool_pavement` and `shade_structure` candidates get an empty influence
set (no population point they measurably benefit under this objective),
matching D4's own `ewcb_person_degree_hours = 0` for both -- the
optimizer will correctly never select either for *equity* credit under
this objective (their cost is real, their EWCB marginal gain is zero),
which is a real, disclosed consequence of D4's scope, not a bug introduced
here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import geopandas as gpd
import numpy as np

from engine.equity.exposure import (
    EXPOSURE_RADIUS_M,  # noqa: F401 -- re-exported for callers building reports
)
from engine.impact.cooling_kernel import CANOPY_INTERVENTION_TYPES, SIGMA_M
from engine.impact.ewcb import (
    DESIGN_DAY_HOURS,
    INFLUENCE_RADIUS_SIGMA_MULTIPLES,
    load_population_points,
)

OPTIMIZER_HVI_FLOOR = 0.0

IntArray = np.ndarray[Any, np.dtype[np.int64]]
FloatArray = np.ndarray[Any, np.dtype[np.float64]]


@dataclass(frozen=True)
class CandidateInfluence:
    """One candidate's effect on the population points it actually
    reaches: parallel arrays, `population_index[k]` gets `delta_t[k]`
    degrees of cooling from this candidate alone (not yet combined with
    any other candidate -- that combination is `CoverageObjective`'s job)."""

    population_index: IntArray
    delta_t: FloatArray


@dataclass(frozen=True)
class CoverageObjective:
    """Precomputed once per candidate set; supports repeated efficient
    `marginal_gain` calls for CELF's lazy greedy without recomputing
    spatial joins on every evaluation."""

    influences: list[CandidateInfluence]
    weight: FloatArray  # per population point, HVI-floored (see module docstring)
    n_population: int

    def value(self, selected: set[int]) -> float:
        """F(S) for a given selection, from scratch -- used for exact/
        brute-force comparisons and tests, not the hot greedy loop."""
        if not selected:
            return 0.0
        current_max = np.zeros(self.n_population, dtype="float64")
        for i in selected:
            inf = self.influences[i]
            np.maximum.at(current_max, inf.population_index, inf.delta_t)
        return float(np.sum(current_max * self.weight))

    def marginal_gain(self, candidate_index: int, current_max: FloatArray) -> float:
        """The exact gain from adding `candidate_index` given the current
        per-population-point max ΔT already achieved by the selection so
        far (`current_max`) -- O(candidate's own influence size), not
        O(population), which is what makes CELF's lazy re-evaluation loop
        cheap enough to run live."""
        inf = self.influences[candidate_index]
        if inf.population_index.size == 0:
            return 0.0
        prior = current_max[inf.population_index]
        gain = np.maximum(inf.delta_t - prior, 0.0)
        return float(np.sum(gain * self.weight[inf.population_index]))

    def apply(self, candidate_index: int, current_max: FloatArray) -> None:
        """Mutates `current_max` in place to reflect adding `candidate_index`
        to the selection -- call only after committing to a pick."""
        inf = self.influences[candidate_index]
        if inf.population_index.size == 0:
            return
        np.maximum.at(current_max, inf.population_index, inf.delta_t)


def _canopy_influence(row: Any, pop_centroids: gpd.GeoSeries, sindex: Any) -> CandidateInfluence:
    radius_m = INFLUENCE_RADIUS_SIGMA_MULTIPLES * SIGMA_M
    center = row.geometry.centroid
    nearby_idx = list(sindex.query(center.buffer(radius_m), predicate="intersects"))
    if not nearby_idx:
        return CandidateInfluence(np.array([], dtype="int64"), np.array([], dtype="float64"))

    nearby_centroids = pop_centroids.iloc[nearby_idx]
    d2 = nearby_centroids.distance(center).to_numpy() ** 2
    delta_t = row.delta_t_peak_degc * np.exp(-d2 / (2 * SIGMA_M**2))
    return CandidateInfluence(np.asarray(nearby_idx, dtype="int64"), delta_t.astype("float64"))


def _cool_roof_influence(row: Any, sindex: Any) -> CandidateInfluence:
    center = row.geometry.centroid
    matches = list(sindex.query(center, predicate="within"))
    if not matches:
        return CandidateInfluence(np.array([], dtype="int64"), np.array([], dtype="float64"))
    # A building's own footprint should contain its own centroid exactly once;
    # if OSM data ever produced an overlap, take the first match rather than
    # double-counting one candidate's benefit across multiple buildings.
    idx = matches[0]
    return CandidateInfluence(np.array([idx], dtype="int64"), np.array([row.delta_t_degc], dtype="float64"))


def build_coverage_objective(candidates: gpd.GeoDataFrame) -> CoverageObjective:
    """Precomputes each candidate's `CandidateInfluence` and the
    HVI-floored per-population-point weight, from the same real D1/D2/D3
    data D4 uses. Requires `delta_t_peak_degc` (canopy) and/or
    `delta_t_degc` (`cool_roof`) already present on `candidates`."""
    population = load_population_points().reset_index(drop=True)
    weight = (
        np.clip(population["hvi"].to_numpy(), OPTIMIZER_HVI_FLOOR, None)
        * population["exposure"].to_numpy()
        * population["population"].to_numpy()
        * DESIGN_DAY_HOURS
    ).astype("float64")

    building_sindex = population.sindex
    pop_centroids = population.geometry.centroid

    influences: list[CandidateInfluence] = []
    for row in candidates.itertuples():
        if row.intervention_type in CANOPY_INTERVENTION_TYPES and hasattr(row, "delta_t_peak_degc"):
            influences.append(_canopy_influence(row, pop_centroids, building_sindex))
        elif row.intervention_type == "cool_roof" and hasattr(row, "delta_t_degc"):
            influences.append(_cool_roof_influence(row, building_sindex))
        else:
            influences.append(CandidateInfluence(np.array([], dtype="int64"), np.array([], dtype="float64")))

    return CoverageObjective(influences=influences, weight=weight, n_population=len(population))
