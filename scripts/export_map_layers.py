"""Exports cached Phase 1 vector layers to GeoJSON for the map app (Phase 2).

Phase 2 scope is "get pixels on screen," not the real API/DB serving layer
(that's Phase 7 -- FastAPI + PostGIS + PMTiles generation). This is a
one-off static export: data/cache/*.parquet (engine.ingest's output) ->
data/derived/edison-eastlake/*.geojson (apps/web reads these directly).
Re-run whenever the underlying ingest cache changes.

Building heights are estimated, not measured -- most OSM buildings here
carry no height/building:levels tag (94 of 2,844 have building:levels; 1
has an explicit height). Estimated heights are real numbers derived from a
documented, disclosed heuristic, not invented ones; the frontend labels
them as estimated. See _estimate_height_m below for the exact rule.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
from engine.equity.hvi import compute_hvi
from engine.equity.population import redistribute_population
from engine.impact.albedo import run_albedo_model
from engine.impact.cooling_kernel import CoolingKernelCalibration, run_cooling_kernel
from engine.impact.ewcb import compute_ewcb
from engine.impact.shade import run_shade_raytrace
from engine.ingest import d04_osm, d06_parcels, d07b_tiger_bg
from engine.ingest.manifest import version_dir
from engine.optimize.best_plan import best_plan
from engine.optimize.objective import build_coverage_objective
from engine.optimize.programs import DEFAULT_PROGRAM, DEFAULT_PUBLIC_LAND_ONLY, candidate_pool
from engine.surface.candidates import generate_candidates
from engine.surface.heights import estimate_height_m as _estimate_height_m
from engine.surface.impervious_candidates import generate_impervious_candidates

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "data" / "derived" / "edison-eastlake"

# A representative demo budget for the exported optimizer selection --
# matches the figure used throughout docs/METHODOLOGY.md's Phase 6
# section, not picked separately here.
DEFAULT_OPTIMIZER_BUDGET_USD = 50_000.0


def export_buildings() -> Path:
    gdf = gpd.read_parquet(version_dir(d04_osm.SOURCE_ID, d04_osm.VERSION) / "buildings.parquet")
    gdf = gdf.to_crs(epsg=4326)  # GeoJSON is WGS84 by convention; MapLibre expects it

    heights, provenances = zip(*(_estimate_height_m(row) for _, row in gdf.iterrows()), strict=True)
    out = gpd.GeoDataFrame(
        {
            "name": gdf.get("name"),
            "building_type": gdf.get("building"),
            "height_m": heights,
            "height_provenance": provenances,
            "geometry": gdf.geometry,
        },
        crs="EPSG:4326",
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "buildings.geojson"
    out.to_file(out_path, driver="GeoJSON")
    return out_path


def export_roads() -> Path:
    gdf = gpd.read_parquet(version_dir(d04_osm.SOURCE_ID, d04_osm.VERSION) / "roads.parquet")
    gdf = gdf.to_crs(epsg=4326)
    out = gpd.GeoDataFrame(
        {"name": gdf.get("name"), "highway": gdf.get("highway"), "geometry": gdf.geometry},
        crs="EPSG:4326",
    )
    out_path = OUT_DIR / "roads.geojson"
    out.to_file(out_path, driver="GeoJSON")
    return out_path


def export_parcels() -> Path:
    gdf = gpd.read_parquet(version_dir(d06_parcels.SOURCE_ID, d06_parcels.VERSION) / "parcels.parquet")
    gdf = gdf.to_crs(epsg=4326)
    out = gpd.GeoDataFrame(
        {"apn": gdf.get("APN"), "land_use_code": gdf.get("LC_CUR"), "geometry": gdf.geometry},
        crs="EPSG:4326",
    )
    out_path = OUT_DIR / "parcels.geojson"
    out.to_file(out_path, driver="GeoJSON")
    return out_path


def _build_scored_candidates() -> tuple[gpd.GeoDataFrame, CoolingKernelCalibration]:
    """Phase 4 plantable-space candidates (`engine.surface.candidates`) plus
    Phase 5's impervious-surface candidates
    (`engine.surface.impervious_candidates`), each carrying its full Phase 5
    impact/equity scoring: C1's `delta_t_peak_degc` (canopy candidates),
    C3's `delta_t_degc` (`cool_roof`/`cool_pavement`), C2's
    `shade_hours_delivered`, and D4's `ewcb_person_degree_hours` (with
    `ewcb_low`/`ewcb_high` confidence bounds). Shared by `export_candidates`
    and `export_optimizer_solution` so both export functions score the
    same candidate universe identically, not two independently-computed
    (and potentially drifting) copies. Geometry stays in the projected CRS
    here -- callers reproject to WGS84 for GeoJSON output themselves."""
    tree_candidates = generate_candidates()
    tree_scored, calibration = run_cooling_kernel(tree_candidates)
    tree_scored, _design_day = run_shade_raytrace(tree_scored)

    impervious_candidates = generate_impervious_candidates()
    impervious_scored, _inputs, _design_day2 = run_albedo_model(impervious_candidates)

    combined = gpd.GeoDataFrame(
        pd.concat([tree_scored, impervious_scored], ignore_index=True),
        geometry="geometry",
        crs=tree_scored.crs,
    )
    combined = compute_ewcb(combined, cooling_calibration=calibration)
    return combined, calibration


def export_candidates() -> Path:
    """Exactly the Phase 5 checkpoint (COOLBLOCK-BUILD-PLAN.md line 854):
    "a card showing its modeled cooling, its shade contribution, and the
    number and vulnerability of people reached."

    The plan says "hover"; this map's existing interaction model
    (`apps/web/app/map/page.tsx`'s `ContextPanel`, already used for
    buildings/parcels since Phase 2) is click-to-inspect, generically
    rendering every GeoJSON property -- adding these fields here is
    already sufficient for them to appear there without new UI code, so
    "hover" is implemented as "click" for consistency with every other
    layer, not fixed to a different interaction just for this one."""
    combined, _calibration = _build_scored_candidates()
    out = combined.to_crs(epsg=4326)
    out_path = OUT_DIR / "candidates.geojson"
    out.to_file(out_path, driver="GeoJSON")
    return out_path


def export_optimizer_solution(budget_usd: float = DEFAULT_OPTIMIZER_BUDGET_USD) -> Path:
    """CoolBlock's own CELF solve (E2, `engine.optimize.celf`) at a
    representative demo budget -- the Phase 6 checkpoint
    (COOLBLOCK-BUILD-PLAN.md line 875): "the ranked plan... it is
    obviously sensible when you look at where the sites are," adapted
    from a terminal printout to a highlighted map layer so the ranked
    plan is inspectable in the same UI as every other layer (click a
    selected site for its rank/marginal-gain/cumulative-value/cost),
    consistent with how the Phase 5 checkpoint's "hover" was adapted to
    this map's existing click-to-inspect interaction model.

    Solving is deterministic given the same candidate universe and
    budget, so this re-solves fresh from `_build_scored_candidates()`
    rather than reading `candidates.geojson` back in -- one source of
    truth for the scored candidate set, not two files that could drift
    out of sync if only one is re-exported.

    Solved on the default candidate pool (trees on public land,
    `engine.optimize.programs`, docs/adr/0027-*.md) -- the same plan a
    visitor gets from the live optimizer's defaults, so this layer and the
    app never disagree about what "CoolBlock's plan" is."""
    combined, _calibration = _build_scored_candidates()
    pool = candidate_pool(combined, DEFAULT_PROGRAM, DEFAULT_PUBLIC_LAND_ONLY)
    objective = build_coverage_objective(pool)
    costs = pool["total_cost_usd"].to_numpy()

    picks = best_plan(objective, costs, budget_usd).picks
    indices = [p.candidate_index for p in picks]
    selected = pool.iloc[indices].copy()
    selected["solve_rank"] = range(1, len(indices) + 1)
    selected["marginal_gain_ewcb"] = [p.marginal_gain for p in picks]
    selected["cumulative_ewcb"] = [p.cumulative_value for p in picks]
    selected["cumulative_cost_usd"] = [p.cumulative_cost_usd for p in picks]
    selected["solve_budget_usd"] = budget_usd

    out = selected.to_crs(epsg=4326)
    out_path = OUT_DIR / "optimizer_selection.geojson"
    out.to_file(out_path, driver="GeoJSON")
    return out_path


def export_population() -> Path:
    """Phase 8 -- D1's dasymetric population (`engine.equity.population.redistribute_population`)
    as its own map layer: real residential building footprints, each
    carrying its share of its block group's ACS population (weighted by
    footprint area x floor count, capped at a plausible density -- see
    that module's docstring for the two real OSM misclassifications this
    caught and fixed). Distinct from `buildings.geojson` (Phase 1, every
    building) -- this is only the subset D1 classified residential, with
    the population fields D1 computed, not a duplicate export."""
    buildings = redistribute_population()
    out = buildings[
        [
            "block_group_geoid",
            "population",
            "population_uncapped",
            "block_group_population",
            "footprint_m2",
            "floor_count",
            "geometry",
        ]
    ].to_crs(epsg=4326)
    out_path = OUT_DIR / "population.geojson"
    out.to_file(out_path, driver="GeoJSON")
    return out_path


def export_hvi_choropleth() -> Path:
    """Phase 8 -- D2's Heat Vulnerability Index (`engine.equity.hvi.compute_hvi`)
    joined onto real Census TIGER block-group polygons (D7b) for a
    choropleth. HVI is a signed z-score composite (see that module's
    docstring for why: relative to this neighborhood's 23 block groups,
    not an absolute/citywide scale) -- `hvi` here is the same number D4's
    EWCB reporting uses, not a separately-computed one.

    Also exports the six per-indicator z-scores `compute_hvi()` already
    computes on the way to `hvi` (called here with its default, all-1.0
    weights, so these six columns are exactly the *raw*, unweighted
    z-scores -- multiplying by 1.0 is a no-op). This is what lets the
    frontend's HVI weight sliders (§6.4 D2: "a planner can and should
    argue with them") recompute the weighted composite live, client-side,
    from real per-indicator data -- not by re-fetching or re-deriving
    anything, since the six numbers a slider needs are already sitting
    right here."""
    block_groups = gpd.read_parquet(
        version_dir(d07b_tiger_bg.SOURCE_ID, d07b_tiger_bg.VERSION) / "block_groups.parquet"
    )
    hvi = compute_hvi()
    z_columns = [c for c in hvi.columns if c.startswith("z_")]
    merged = block_groups.merge(hvi, left_on="GEOID", right_on="geoid", how="inner")
    out = gpd.GeoDataFrame(
        {
            "geoid": merged["GEOID"],
            "total_population": merged["total_population"],
            "hvi": merged["hvi"],
            **{col: merged[col] for col in z_columns},
            "geometry": merged.geometry,
        },
        crs=block_groups.crs,
    ).to_crs(epsg=4326)
    out_path = OUT_DIR / "hvi.geojson"
    out.to_file(out_path, driver="GeoJSON")
    return out_path


def main() -> None:
    for label, fn in [
        ("buildings", export_buildings),
        ("roads", export_roads),
        ("parcels", export_parcels),
        ("candidates", export_candidates),
        ("optimizer_selection", export_optimizer_solution),
        ("population", export_population),
        ("hvi", export_hvi_choropleth),
    ]:
        path = fn()
        size_kb = path.stat().st_size / 1024
        print(f"{label}: {path} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
