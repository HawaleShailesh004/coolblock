from __future__ import annotations

import pytest
import xarray as xr
from engine.ingest.d02_sentinel2 import SOURCE_ID, VERSION
from engine.ingest.manifest import is_cached, version_dir

pytestmark = pytest.mark.skipif(
    not is_cached(SOURCE_ID, VERSION), reason="D2 not ingested yet -- run engine.ingest.d02_sentinel2"
)


def test_smoke() -> None:
    ds = xr.open_dataset(version_dir(SOURCE_ID, VERSION) / "predictors_one_per_summer.nc")
    assert 1 <= ds.sizes["time"] <= 5  # one scene per summer, 2021-2025

    red = ds["B04"].astype("float64")
    nir = ds["B08"].astype("float64")
    ndvi = (nir - red) / (nir + red).where((nir + red) != 0)
    valid = ndvi.values[~ndvi.isnull().values]
    assert valid.size > 0
    assert ((valid >= -1) & (valid <= 1)).mean() > 0.99
    ds.close()


def test_crs_is_canonical() -> None:
    import rioxarray  # noqa: F401
    from engine.config import load_neighborhood_config

    cfg = load_neighborhood_config()
    ds = xr.open_dataset(
        version_dir(SOURCE_ID, VERSION) / "predictors_one_per_summer.nc", decode_coords="all"
    )
    assert ds.rio.crs.to_epsg() == cfg.target_epsg
    ds.close()
