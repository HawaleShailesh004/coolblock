from __future__ import annotations

import numpy as np
import pytest
from engine.ingest import d01_landsat, d02_sentinel2, d11_nlcd
from engine.ingest.grid import get_canonical_grid
from engine.ingest.manifest import is_cached
from engine.thermal.downscale import run_downscaling

pytestmark = pytest.mark.skipif(
    not all(
        is_cached(src.SOURCE_ID, src.VERSION) for src in (d01_landsat, d02_sentinel2, d11_nlcd)
    ),
    reason="D1/D2/D11 not all ingested yet",
)


def test_downscaling_output_matches_canonical_grid() -> None:
    grid = get_canonical_grid()
    result = run_downscaling()
    assert result.lst_10m.shape == (grid.height, grid.width)
    assert result.uncertainty_10m.shape == (grid.height, grid.width)


def test_downscaling_is_physically_plausible() -> None:
    result = run_downscaling()
    valid = result.lst_10m.values[np.isfinite(result.lst_10m.values)]
    assert valid.size > 0
    assert ((valid > 20) & (valid < 75)).mean() > 0.9

    unc = result.uncertainty_10m.values
    unc_valid = unc[np.isfinite(unc)]
    assert unc_valid.size > 0
    assert (unc_valid >= 0).all(), "q90-q10 must never be negative"


def test_cv_metrics_are_real_numbers() -> None:
    result = run_downscaling()
    assert np.isfinite(result.r2_cv)
    assert np.isfinite(result.rmse_cv)
    assert result.rmse_cv > 0
    assert result.n_training_pixels > 0
