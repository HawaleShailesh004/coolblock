from __future__ import annotations

import numpy as np
import pytest
from engine.ingest import (
    d01_landsat,
    d02_sentinel2,
    d04_osm,
    d11_nlcd,
    d13_open_meteo,
    d15_phoenix_open_data,
)
from engine.ingest.manifest import is_cached
from engine.thermal.validate import run_validation

_REQUIRED = (d01_landsat, d02_sentinel2, d04_osm, d11_nlcd, d13_open_meteo, d15_phoenix_open_data)

pytestmark = pytest.mark.skipif(
    not all(is_cached(src.SOURCE_ID, src.VERSION) for src in _REQUIRED),
    reason="not all Phase 1 sources needed for A3 validation are ingested",
)


def test_validation_runs_and_produces_real_numbers() -> None:
    verdict = run_validation()

    assert np.isfinite(verdict.station.pearson_r)
    assert verdict.station.n_scenes > 10
    # LST should read hotter than air temperature for a sunny urban scene.
    assert verdict.station.mean_lst_minus_air_c > 0

    assert verdict.hotspot.n_tracts >= 3
    assert np.isfinite(verdict.hotspot.spearman_rho)

    assert isinstance(verdict.passed, bool)
    if not verdict.passed:
        assert len(verdict.reasons) > 0, "a failing verdict must say why"
