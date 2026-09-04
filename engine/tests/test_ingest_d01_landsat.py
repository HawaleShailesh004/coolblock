from __future__ import annotations

import pytest
import xarray as xr
from engine.ingest.d01_landsat import SOURCE_ID, ST_OFFSET, ST_SCALE, VERSION
from engine.ingest.manifest import is_cached, version_dir

pytestmark = pytest.mark.skipif(
    not is_cached(SOURCE_ID, VERSION), reason="D1 not ingested yet -- run engine.ingest.d01_landsat"
)


def test_smoke() -> None:
    ds = xr.open_dataset(version_dir(SOURCE_ID, VERSION) / "lwir11_qa_2021_2025.nc")
    assert ds.sizes["time"] > 30  # ~60+ scenes expected across 5 summers
    assert ds.sizes["time"] < 100  # sanity ceiling -- catches an unbounded query regression

    st_kelvin = ds["lwir11"].astype("float64") * ST_SCALE + ST_OFFSET
    st_celsius = (st_kelvin - 273.15).values
    valid = st_celsius[ds["lwir11"].values > 0]
    assert valid.size > 0
    assert ((valid > 10) & (valid < 90)).mean() > 0.5
    ds.close()


def test_crs_is_canonical() -> None:
    import rioxarray  # noqa: F401 -- registers the .rio accessor
    from engine.config import load_neighborhood_config

    cfg = load_neighborhood_config()
    ds = xr.open_dataset(version_dir(SOURCE_ID, VERSION) / "lwir11_qa_2021_2025.nc", decode_coords="all")
    assert ds.rio.crs.to_epsg() == cfg.target_epsg
    ds.close()


def test_no_all_nan_scenes() -> None:
    ds = xr.open_dataset(version_dir(SOURCE_ID, VERSION) / "lwir11_qa_2021_2025.nc")
    per_scene_valid = (ds["lwir11"] > 0).sum(dim=["x", "y"])
    assert (per_scene_valid.values == 0).sum() == 0, "at least one scene is entirely fill value"
    ds.close()
