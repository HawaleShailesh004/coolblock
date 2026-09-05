from __future__ import annotations

import numpy as np
import pytest
from engine.impact.albedo import (
    ALBEDO_PROXY_MAX,
    TARGET_ALBEDO_BY_INTERVENTION,
    compute_energy_balance_inputs,
    run_albedo_model,
)
from engine.impact.shade import find_design_day
from engine.ingest import d02_sentinel2, d04_osm, d13_open_meteo, d14_nasa_power
from engine.ingest.grid import get_canonical_grid
from engine.ingest.manifest import is_cached
from engine.surface.impervious_candidates import generate_impervious_candidates
from engine.thermal.predictors import load_sentinel2_predictors

pytestmark = pytest.mark.skipif(
    not all(
        is_cached(src.SOURCE_ID, src.VERSION) for src in (d02_sentinel2, d04_osm, d13_open_meteo, d14_nasa_power)
    ),
    reason="D2/D4/D13/D14 not all ingested yet",
)


def test_albedo_proxy_is_real_reflectance_not_raw_dn() -> None:
    """Regression guard for the scaling bug caught during Phase 5
    development: Sentinel-2 L2A digital numbers must be scaled by 1/10000
    before being used as a physical albedo proxy, or every value clips to
    ALBEDO_PROXY_MAX and no candidate ever shows a nonzero delta_t_degc."""
    ds = load_sentinel2_predictors(get_canonical_grid())
    albedo = ds["albedo_proxy"].values
    finite = albedo[np.isfinite(albedo)]
    assert finite.min() >= 0.0
    assert finite.max() <= 1.0
    assert 0.05 < finite.mean() < 0.6  # a plausible broadband-reflectance range, not raw DN (~1000s)


def test_energy_balance_inputs_are_physically_plausible() -> None:
    design_day = find_design_day()
    inputs = compute_energy_balance_inputs(design_day)
    # Clear-sky solar-noon peak irradiance for a Sonoran Desert summer day.
    assert 500.0 < inputs.s_down_peak_w_m2 < 1200.0
    assert inputs.wind_speed_m_s >= 0.0
    assert inputs.h_conv_w_m2_k > 5.7  # McAdams floor at zero wind


def test_albedo_delta_t_only_applies_to_scoped_intervention_types() -> None:
    candidates = generate_impervious_candidates()
    scored, _, _ = run_albedo_model(candidates)
    assert set(scored["intervention_type"].unique()) <= set(TARGET_ALBEDO_BY_INTERVENTION)
    assert (scored["delta_t_degc"] >= 0).all()
    assert (scored["current_albedo_proxy"].dropna() <= ALBEDO_PROXY_MAX + 1e-9).all()


def test_cool_roof_delta_t_matches_literature_order_of_magnitude() -> None:
    """Cool-roof surface-temperature reduction is well documented at
    roughly 11-28 degC in the literature -- this checks the model lands in
    a plausible band, not an exact figure."""
    candidates = generate_impervious_candidates()
    scored, _, _ = run_albedo_model(candidates)
    cool_roof = scored[scored["intervention_type"] == "cool_roof"]
    positive = cool_roof[cool_roof["delta_t_degc"] > 0]
    assert len(positive) > 0
    assert (positive["delta_t_degc"] < 30.0).all()
