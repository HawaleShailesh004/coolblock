from __future__ import annotations

import geopandas as gpd
import pandas as pd
import pytest
from engine.impact.albedo import run_albedo_model
from engine.impact.cooling_kernel import CoolingKernelCalibration, run_cooling_kernel
from engine.impact.ewcb import compute_ewcb, load_population_points
from engine.ingest import (
    d01_landsat,
    d02_sentinel2,
    d04_osm,
    d07_census,
    d07b_tiger_bg,
    d08_svi,
    d09_places,
    d11_nlcd,
)
from engine.ingest.manifest import is_cached
from engine.surface.candidates import generate_candidates
from engine.surface.impervious_candidates import generate_impervious_candidates

_REQUIRED_SOURCES = (d01_landsat, d02_sentinel2, d04_osm, d07_census, d07b_tiger_bg, d08_svi, d09_places, d11_nlcd)

pytestmark = pytest.mark.skipif(
    not all(is_cached(src.SOURCE_ID, src.VERSION) for src in _REQUIRED_SOURCES),
    reason="not all required sources ingested yet",
)


def _real_scored_candidates() -> tuple[gpd.GeoDataFrame, CoolingKernelCalibration]:
    tree_scored, cal = run_cooling_kernel(generate_candidates())
    imp_scored, _, _ = run_albedo_model(generate_impervious_candidates())
    combined = pd.concat([tree_scored, imp_scored], ignore_index=True)
    return gpd.GeoDataFrame(combined, geometry="geometry", crs=tree_scored.crs), cal


def test_load_population_points_has_hvi_and_exposure() -> None:
    population = load_population_points()
    assert len(population) > 0
    assert population["hvi"].notna().all()
    assert (population["exposure"] >= 1.0).all()


def test_shade_structure_and_cool_pavement_get_zero_ewcb() -> None:
    """Neither intervention type has a population-attribution model in
    this phase (see engine/impact/ewcb.py's module docstring) -- their
    real benefit is reported by C2/C3 directly, not invented here."""
    scored, _ = _real_scored_candidates()
    result = compute_ewcb(scored)
    unscored = result[result["intervention_type"].isin(["shade_structure", "cool_pavement"])]
    if len(unscored) > 0:
        assert (unscored["ewcb_person_degree_hours"] == 0.0).all()
        assert (unscored["ewcb_low"] == 0.0).all()
        assert (unscored["ewcb_high"] == 0.0).all()


def test_ewcb_can_be_negative_for_low_vulnerability_sites() -> None:
    """HVI is a z-score centered at 0 -- a real, intended consequence is
    that some candidates score a negative equity-weighted benefit despite
    having a strictly positive raw delta_t. Not a bug (see module
    docstring)."""
    scored, _ = _real_scored_candidates()
    result = compute_ewcb(scored)
    canopy = result[result["intervention_type"].isin(["street_tree", "park_lot_tree_cluster"])]
    assert (canopy["ewcb_person_degree_hours"] < 0).any()
    assert (canopy["ewcb_person_degree_hours"] > 0).any()


def test_cool_roof_ewcb_only_nonzero_for_matched_residential_buildings() -> None:
    scored, _ = _real_scored_candidates()
    result = compute_ewcb(scored)
    cool_roof = result[result["intervention_type"] == "cool_roof"]
    assert len(cool_roof) > 0
    nonzero_fraction = (cool_roof["ewcb_person_degree_hours"] != 0.0).mean()
    # Most, not all, cool-roof candidates are residential buildings D1 assigned population to.
    assert 0.5 < nonzero_fraction < 1.0


def test_canopy_confidence_interval_brackets_the_point_estimate() -> None:
    """DoD (COOLBLOCK-BUILD-PLAN.md Phase 5): every candidate carries an
    EWCB with confidence bounds -- for canopy candidates, propagated
    linearly from C1's own beta_ci95."""
    scored, cal = _real_scored_candidates()
    result = compute_ewcb(scored, cooling_calibration=cal)
    canopy = result[result["intervention_type"].isin(["street_tree", "park_lot_tree_cluster"])]
    assert (canopy["ewcb_low"] <= canopy["ewcb_person_degree_hours"] + 1e-6).all()
    assert (canopy["ewcb_person_degree_hours"] <= canopy["ewcb_high"] + 1e-6).all()
    assert (canopy["ewcb_low"] < canopy["ewcb_high"]).any()  # a real, nonzero band for at least some candidates


def test_non_canopy_confidence_interval_equals_point_estimate() -> None:
    """No fitted uncertainty source exists for cool_roof/cool_pavement/
    shade_structure this phase -- their bounds must equal the point
    estimate exactly, not a fabricated band."""
    scored, cal = _real_scored_candidates()
    result = compute_ewcb(scored, cooling_calibration=cal)
    non_canopy = result[~result["intervention_type"].isin(["street_tree", "park_lot_tree_cluster"])]
    pd.testing.assert_series_equal(
        non_canopy["ewcb_low"], non_canopy["ewcb_person_degree_hours"], check_names=False
    )
    pd.testing.assert_series_equal(
        non_canopy["ewcb_high"], non_canopy["ewcb_person_degree_hours"], check_names=False
    )
