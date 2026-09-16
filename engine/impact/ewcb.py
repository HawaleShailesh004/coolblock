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

from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd

from engine.config import REPO_ROOT, load_neighborhood_config
from engine.equity.exposure import compute_exposure_multiplier
from engine.equity.hvi import compute_hvi
from engine.equity.population import redistribute_population
from engine.impact.cooling_kernel import (
    CANOPY_INTERVENTION_TYPES,
    SIGMA_M,
    CoolingKernelCalibration,
)

DESIGN_DAY_HOURS = 10.0  # matches engine.impact.shade's 09:00-18:00 window

INFLUENCE_RADIUS_SIGMA_MULTIPLES = 3.0  # matches cooling_kernel.gaussian_patch's render radius


# Matches `engine.optimize.plan_service.NEIGHBORHOOD_SLUG` and
# `scripts/export_map_layers.py`'s `OUT_DIR` exactly -- deliberately a
# literal, not `load_neighborhood_config().id` (that resolves to
# "edison-eastlake-phoenix-az", a *different* string; see
# `plan_service.py`'s own comment for why the directory name is a literal
# for the scope-locked life of this build, not a second lookup that could
# silently drift from the one every other cache path already uses).
_NEIGHBORHOOD_SLUG = "edison-eastlake"


def _cached_population_points_path() -> Path:
    return REPO_ROOT / "data" / "derived" / _NEIGHBORHOOD_SLUG / "population_scored.geojson"


def load_population_points(*, use_cache: bool = True) -> gpd.GeoDataFrame:
    """D1's residential buildings, each carrying its block group's HVI
    (D2) and its own exposure multiplier (D3) -- the population side of
    the EWCB sum, built once and reused across every candidate.

    **Every solve calls this** (via `build_coverage_objective`, always with
    default HVI weights -- the live app's per-indicator HVI weight sliders
    only ever recompute the *map choropleth* client-side, never the
    optimizer's own objective, so a cached default-weight result is always
    the right answer here, not a stale approximation of a sometimes-different
    one). Recomputing it from raw ingest cache on every request -- as this
    function did until this cache-read was added -- means a request to
    `/plans/{id}/solve` isn't actually only "a fast re-solve over an
    already-scored candidate set" (`engine.optimize.plan_service`'s own
    stated design): it also silently re-touches `data/cache/maricopa_parcels/`,
    `data/cache/census_acs5/`, `data/cache/cdc_*/` and more -- real
    per-person data (parcel owner names *and home addresses*, unlike the
    already-scrubbed `owner_name`-only issue in `docs/adr/0030-*.md`) that
    must never be assumed present on a deploy target, files that are also
    considerably larger and more sensitive than anything already committed.

    So: read the cached, precomputed result
    (`scripts/export_map_layers.py`'s `export_population_scored()`) if it
    exists, matching `plan_service.load_candidate_universe()`'s own
    cache-first pattern exactly. Falls back to the full raw recompute if
    the cache is missing (a fresh ingest, or `use_cache=False` to force a
    real recompute, e.g. from the export script that regenerates the
    cache itself)."""
    cache_path = _cached_population_points_path()
    if use_cache and cache_path.exists():
        return gpd.read_file(cache_path).to_crs(epsg=load_neighborhood_config().target_epsg)

    buildings = redistribute_population()
    hvi = compute_hvi()[["geoid", "hvi"]]

    joined = buildings.merge(hvi, left_on="block_group_geoid", right_on="geoid", how="left")
    # Block groups outside D7b's coverage (5 of 23, see docs/adr/0006-*.md)
    # have no HVI to join -- neutral (0.0, the within-neighborhood z-score
    # mean by construction) rather than dropping their population.
    joined["hvi"] = joined["hvi"].fillna(0.0)
    joined["exposure"] = compute_exposure_multiplier(joined)
    return joined


def _ewcb_canopy(
    candidates: gpd.GeoDataFrame, population: gpd.GeoDataFrame, beta_scale: float = 1.0
) -> np.ndarray[Any, np.dtype[np.float64]]:
    """`beta_scale` rescales `delta_t_peak_degc` -- since that column is
    itself `beta_magnitude * (other factors)` (`engine.impact.cooling_kernel`),
    multiplying by `ci_bound / beta_magnitude` propagates C1's beta
    confidence interval through to an EWCB confidence bound linearly,
    without re-deriving the whole per-candidate calculation."""
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
        delta_t = (beta_scale * row.delta_t_peak_degc) * np.exp(-d2 / (2 * SIGMA_M**2))

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


def compute_ewcb(
    candidates: gpd.GeoDataFrame,
    cooling_calibration: CoolingKernelCalibration | None = None,
) -> gpd.GeoDataFrame:
    """Adds `ewcb_person_degree_hours` to `candidates`. Requires
    `delta_t_peak_degc` (from `cooling_kernel.run_cooling_kernel`) for
    canopy candidates and/or `delta_t_degc` (from `albedo.run_albedo_model`)
    for `cool_roof` candidates already present -- whichever column is
    missing, that intervention type's rows score 0.0 rather than raising.

    Passing the `CoolingKernelCalibration` C1 already produces (its own
    `beta_ci95`) also fills `ewcb_low`/`ewcb_high` for canopy candidates --
    the plan's DoD requirement (§6.3/§6.4) that "every candidate carries...
    an EWCB with confidence [bounds]." Linear in beta (see `_ewcb_canopy`),
    so this is an exact propagation of C1's own regression uncertainty, not
    a separately fitted or invented uncertainty model. `cool_roof`,
    `cool_pavement`, and `shade_structure` have no fitted uncertainty
    source in this phase (C3's energy-balance model reports a point
    estimate only) -- their `ewcb_low`/`ewcb_high` stay equal to the point
    estimate, disclosed here and in `docs/METHODOLOGY.md` rather than
    fabricating a band."""
    population = load_population_points()
    ewcb = pd.Series(0.0, index=candidates.index)
    ewcb_low = pd.Series(0.0, index=candidates.index)
    ewcb_high = pd.Series(0.0, index=candidates.index)

    canopy_mask = candidates["intervention_type"].isin(CANOPY_INTERVENTION_TYPES)
    if canopy_mask.any() and "delta_t_peak_degc" in candidates.columns:
        canopy_candidates = candidates[canopy_mask]
        ewcb.loc[canopy_mask] = _ewcb_canopy(canopy_candidates, population)

        if cooling_calibration is not None:
            beta_magnitude = abs(cooling_calibration.beta_degc_per_canopy_fraction)
            ci_low, ci_high = cooling_calibration.beta_ci95
            scale_low, scale_high = abs(ci_low) / beta_magnitude, abs(ci_high) / beta_magnitude
            bound_a = _ewcb_canopy(canopy_candidates, population, beta_scale=scale_low)
            bound_b = _ewcb_canopy(canopy_candidates, population, beta_scale=scale_high)
            ewcb_low.loc[canopy_mask] = np.minimum(bound_a, bound_b)
            ewcb_high.loc[canopy_mask] = np.maximum(bound_a, bound_b)
        else:
            ewcb_low.loc[canopy_mask] = ewcb.loc[canopy_mask]
            ewcb_high.loc[canopy_mask] = ewcb.loc[canopy_mask]

    cool_roof_mask = candidates["intervention_type"] == "cool_roof"
    if cool_roof_mask.any() and "delta_t_degc" in candidates.columns:
        ewcb.loc[cool_roof_mask] = _ewcb_cool_roof(candidates[cool_roof_mask], population)

    # No fitted uncertainty source for cool_roof/cool_pavement/shade_structure
    # this phase -- their low/high bounds equal the point estimate, not a
    # fabricated band (see docstring above).
    unbounded_mask = ~canopy_mask
    ewcb_low.loc[unbounded_mask] = ewcb.loc[unbounded_mask]
    ewcb_high.loc[unbounded_mask] = ewcb.loc[unbounded_mask]

    out = candidates.copy()
    out["ewcb_person_degree_hours"] = ewcb
    out["ewcb_low"] = ewcb_low
    out["ewcb_high"] = ewcb_high
    return out
