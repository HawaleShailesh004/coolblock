from __future__ import annotations

import numpy as np
import pytest
from engine.impact.cooling_kernel import (
    CANOPY_INTERVENTION_TYPES,
    G_CEILING,
    H_ANOMALY_WEIGHT,
    H_ANOMALY_ZSCORE_CAP,
    calibrate_beta,
    gaussian_patch,
    run_cooling_kernel,
)
from engine.ingest import d01_landsat, d02_sentinel2, d04_osm, d11_nlcd
from engine.ingest.manifest import is_cached
from engine.surface.candidates import generate_candidates

pytestmark = pytest.mark.skipif(
    not all(is_cached(src.SOURCE_ID, src.VERSION) for src in (d01_landsat, d02_sentinel2, d04_osm, d11_nlcd)),
    reason="D1/D2/D4/D11 not all ingested yet",
)


def test_beta_is_negative_and_significant() -> None:
    """More local canopy should predict lower LST -- a positive beta would
    mean the fitted kernel cools nothing, or cools backwards."""
    cal = calibrate_beta()
    assert cal.beta_degc_per_canopy_fraction < 0
    lo, hi = cal.beta_ci95
    assert lo < hi < 0  # the 95% CI must not cross zero


def test_shade_structures_get_no_canopy_delta_t() -> None:
    """C1 is a canopy-cooling kernel -- shade structures plant no canopy,
    so applying the tree-crown formula to them would be physically
    meaningless, not just imprecise (see module docstring, simplification 3)."""
    candidates = generate_candidates()
    scored, _ = run_cooling_kernel(candidates)
    non_canopy = scored[~scored["intervention_type"].isin(CANOPY_INTERVENTION_TYPES)]
    if len(non_canopy) > 0:
        assert (non_canopy["delta_t_peak_degc"] == 0.0).all()


def test_canopy_candidates_get_positive_bounded_delta_t() -> None:
    candidates = generate_candidates()
    scored, cal = run_cooling_kernel(candidates)
    canopy = scored[scored["intervention_type"].isin(CANOPY_INTERVENTION_TYPES)]
    assert len(canopy) > 0
    assert (canopy["delta_t_peak_degc"] > 0).all()
    # Ceiling: canopy_increment_fraction and g() both saturate at 1.0, and
    # h()'s anomaly boost is capped -- see cooling_kernel.py's constants.
    max_multiplier = G_CEILING * (1.0 + H_ANOMALY_WEIGHT * H_ANOMALY_ZSCORE_CAP)
    ceiling = abs(cal.beta_degc_per_canopy_fraction) * max_multiplier
    assert (canopy["delta_t_peak_degc"] <= ceiling + 1e-6).all()


def test_gaussian_patch_peaks_at_center_and_decays() -> None:
    patch, radius_px = gaussian_patch(2.0, sigma_m=30.0)
    assert patch[radius_px, radius_px] == pytest.approx(2.0)
    assert patch[0, 0] < patch[radius_px, radius_px]
    assert np.all(patch >= 0)
