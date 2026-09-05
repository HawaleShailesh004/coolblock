"""D4 -- Equity-Weighted Cooling Benefit (COOLBLOCK-BUILD-PLAN.md §6.4 D4),
the objective Phase 6's optimizer will maximize:

    EWCB(S) = Σ_p  ΔT_S(x_p) · HVI(p) · exposure(p) · hours(p)

Units: equity-weighted person-degree-hours.

This combines every other Phase 5 module: C1's canopy ΔT field
(`engine.impact.cooling_kernel`), C3's albedo ΔT
(`engine.impact.albedo`), D1's dasymetric population
(`engine.equity.population`), D2's HVI (`engine.equity.hvi`), and D3's
exposure multiplier (`engine.equity.exposure`) -- each already built,
tested, and documented on its own.

**C2's shade-hours is deliberately NOT folded into this sum.** It is
already itself a duration ("hours of relief"), a fundamentally different
kind of quantity from a ΔT field to be duration-weighted by `hours(p)`.
Merging the two would either double-count (a shaded tree already has its
canopy's ambient ΔT counted via C1) or require an arbitrary conversion
factor between "hours shaded" and "degrees cooled" that nothing in this
project's data justifies. C2's shade-hours-delivered stays a separate,
real, standalone per-candidate metric -- both numbers should travel
together in any report or UI, not be collapsed into one.

`hours(p)` is modeled as the constant `DESIGN_DAY_HOURS` (10, matching
C2's 09:00-18:00 window) for every candidate, not a per-person behavioral
estimate: the disclosed simplification is that C1's and C3's ΔT values
are steady-state temperature reductions, treated as present for the full
design-day daylight window, rather than a time-varying duration (which is
exactly what C2 already captures on its own).

**Population attribution differs by mechanism, and is disclosed per
type:**

- **Canopy candidates** (`street_tree`, `park_lot_tree_cluster`): C1's
  Gaussian ΔT(d) is evaluated at the true distance to every residential
  building with redistributed population within its 3-sigma influence
  radius, exactly matching the spatial footprint C1 itself models.
- **`cool_roof`**: the ΔT applies to the building's own occupants, if the
  building is one of D1's residential buildings (spatially joined back to
  its own footprint). Non-residential cool-roof candidates (schools,
  offices, churches -- D1 only redistributes population onto residential
  buildings) get `ewcb_person_degree_hours = 0` -- no occupancy data
  exists for them, so their benefit isn't invented, only left unscored
  here (their real ΔT is still reported by C3).
- **`cool_pavement`** and **`shade_structure`**: no population-attribution
  model exists in this phase -- a parking lot or a bus shelter has no
  "occupants" and no ingested data links passers-by to a home address.
  `ewcb_person_degree_hours = 0` for both, matching the same disclosed-gap
  pattern already used for `shade_structure` in C1
  (`docs/adr/0007-*.md`). Their real benefit (ΔT / shade-hours) is
  reported by C3/C2 directly.

**EWCB can be negative, and that is intended, not a bug.** HVI (D2) is a
z-score composite, centered at 0 across this neighborhood's 23 block
groups -- roughly half score below the neighborhood average and carry a
*negative* HVI. A candidate sited in one of those relatively
lower-vulnerability block groups produces a negative
`ewcb_person_degree_hours`: the formula is an equity *weighting* of raw
cooling benefit against the neighborhood's own vulnerability
distribution, not a pure magnitude, so a real, positive ΔT can still
carry a negative equity weight relative to the neighborhood mean. Any UI
or report surfacing this number must not describe it as "degrees of
cooling delivered" on its own -- it is cooling weighted by *relative*
vulnerability, and can legitimately go negative.
"""

from __future__ import annotations

from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd

from engine.equity.exposure import compute_exposure_multiplier
from engine.equity.hvi import compute_hvi
from engine.equity.population import redistribute_population
from engine.impact.cooling_kernel import CANOPY_INTERVENTION_TYPES, SIGMA_M

DESIGN_DAY_HOURS = 10.0  # matches engine.impact.shade's 09:00-18:00 window

INFLUENCE_RADIUS_SIGMA_MULTIPLES = 3.0  # matches cooling_kernel.gaussian_patch's render radius


def load_population_points() -> gpd.GeoDataFrame:
    """D1's residential buildings, each carrying its block group's HVI
    (D2) and its own exposure multiplier (D3) -- the population side of
    the EWCB sum, built once and reused across every candidate."""
    buildings = redistribute_population()
    hvi = compute_hvi()[["geoid", "hvi"]]

    joined = buildings.merge(hvi, left_on="block_group_geoid", right_on="geoid", how="left")
    # Block groups outside D7b's coverage (5 of 23, see docs/adr/0006-*.md)
    # have no HVI to join -- neutral (0.0, the within-neighborhood z-score
    # mean by construction) rather than dropping their population.
    joined["hvi"] = joined["hvi"].fillna(0.0)
    joined["exposure"] = compute_exposure_multiplier(joined)
    return joined


def _ewcb_canopy(candidates: gpd.GeoDataFrame, population: gpd.GeoDataFrame) -> np.ndarray[Any, np.dtype[np.float64]]:
    radius_m = INFLUENCE_RADIUS_SIGMA_MULTIPLES * SIGMA_M
    sindex = population.sindex
    pop_centroids = population.geometry.centroid

    result = np.zeros(len(candidates), dtype="float64")
    for i, row in enumerate(candidates.itertuples()):
        center = row.geometry.centroid
        nearby_idx = list(sindex.query(center.buffer(radius_m), predicate="intersects"))
        if not nearby_idx:
            continue
        nearby = population.iloc[nearby_idx]
        nearby_centroids = pop_centroids.iloc[nearby_idx]

        d2 = nearby_centroids.distance(center).to_numpy() ** 2
        delta_t = row.delta_t_peak_degc * np.exp(-d2 / (2 * SIGMA_M**2))

        result[i] = float(
            np.sum(delta_t * nearby["hvi"].to_numpy() * nearby["exposure"].to_numpy() * nearby["population"].to_numpy())
            * DESIGN_DAY_HOURS
        )
    return result


def _ewcb_cool_roof(candidates: gpd.GeoDataFrame, population: gpd.GeoDataFrame) -> np.ndarray[Any, np.dtype[np.float64]]:
    centroids = gpd.GeoDataFrame(geometry=candidates.geometry.centroid, crs=candidates.crs)
    joined = gpd.sjoin(
        centroids, population[["population", "hvi", "exposure", "geometry"]], how="left", predicate="within"
    )
    joined = joined[~joined.index.duplicated(keep="first")]

    population_vals = joined["population"].fillna(0.0).to_numpy()
    hvi_vals = joined["hvi"].fillna(0.0).to_numpy()
    exposure_vals = joined["exposure"].fillna(0.0).to_numpy()

    delta_t = candidates["delta_t_degc"].to_numpy()
    result: np.ndarray[Any, np.dtype[np.float64]] = delta_t * hvi_vals * exposure_vals * population_vals * DESIGN_DAY_HOURS
    return result


def compute_ewcb(candidates: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Adds `ewcb_person_degree_hours` to `candidates`. Requires
    `delta_t_peak_degc` (from `cooling_kernel.run_cooling_kernel`) for
    canopy candidates and/or `delta_t_degc` (from `albedo.run_albedo_model`)
    for `cool_roof` candidates already present -- whichever column is
    missing, that intervention type's rows score 0.0 rather than raising."""
    population = load_population_points()
    ewcb = pd.Series(0.0, index=candidates.index)

    canopy_mask = candidates["intervention_type"].isin(CANOPY_INTERVENTION_TYPES)
    if canopy_mask.any() and "delta_t_peak_degc" in candidates.columns:
        ewcb.loc[canopy_mask] = _ewcb_canopy(candidates[canopy_mask], population)

    cool_roof_mask = candidates["intervention_type"] == "cool_roof"
    if cool_roof_mask.any() and "delta_t_degc" in candidates.columns:
        ewcb.loc[cool_roof_mask] = _ewcb_cool_roof(candidates[cool_roof_mask], population)

    out = candidates.copy()
    out["ewcb_person_degree_hours"] = ewcb
    return out
