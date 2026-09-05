from __future__ import annotations

import numpy as np
import pytest
import xarray as xr
from engine.ingest import d01_landsat
from engine.ingest.manifest import is_cached
from engine.thermal.composite import build_composite, clear_sky_mask, lst_celsius

pytestmark = pytest.mark.skipif(
    not is_cached(d01_landsat.SOURCE_ID, d01_landsat.VERSION),
    reason="D1 not ingested yet -- run engine.ingest.d01_landsat",
)


def test_clear_sky_mask_bit_logic() -> None:
    # bit6 (clear) set, all contamination bits clear -> usable.
    clear = xr.DataArray([0b0100_0000])
    # bit3 (cloud) set -> not usable, even with bit6 set.
    cloudy = xr.DataArray([0b0100_1000])
    mask = clear_sky_mask(xr.concat([clear, cloudy], dim="scene"))
    assert bool(mask.isel(scene=0)) is True
    assert bool(mask.isel(scene=1)) is False


def test_lst_celsius_conversion() -> None:
    # DN such that Kelvin conversion lands near a known reference point.
    dn = xr.DataArray([(313.15 - d01_landsat.ST_OFFSET) / d01_landsat.ST_SCALE])
    celsius = lst_celsius(dn)
    assert float(celsius.isel(dim_0=0)) == pytest.approx(40.0, abs=0.1)


def test_composite_is_physically_plausible() -> None:
    composite = build_composite()
    valid = composite.values[np.isfinite(composite.values)]
    assert valid.size > 0
    # Phoenix summer median surface temperature -- a plausibility band, not a model.
    assert ((valid > 20) & (valid < 75)).mean() > 0.95
