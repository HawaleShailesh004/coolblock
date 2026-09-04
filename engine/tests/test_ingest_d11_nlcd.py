from __future__ import annotations

import pytest
import rasterio
from engine.ingest.d11_nlcd import NODATA_IMPERVIOUS, NODATA_LANDCOVER, SOURCE_ID, VERSION
from engine.ingest.manifest import is_cached, version_dir

pytestmark = pytest.mark.skipif(
    not is_cached(SOURCE_ID, VERSION), reason="D11 not ingested yet -- run engine.ingest.d11_nlcd"
)


def test_landcover_smoke() -> None:
    with rasterio.open(version_dir(SOURCE_ID, VERSION) / "landcover.tif") as src:
        arr = src.read(1)
        assert src.crs is not None
        valid = arr[arr != NODATA_LANDCOVER]
        assert valid.size > 0
        assert valid.min() >= 11 and valid.max() <= 95  # full NLCD legend range


def test_impervious_smoke() -> None:
    with rasterio.open(version_dir(SOURCE_ID, VERSION) / "impervious_pct.tif") as src:
        arr = src.read(1).astype(float)
        valid = arr[arr != NODATA_IMPERVIOUS]
        assert valid.size > 0
        assert ((valid >= 0) & (valid <= 100)).mean() > 0.95


def test_grids_are_aligned() -> None:
    from engine.ingest.grid import get_canonical_grid

    grid = get_canonical_grid()
    for name in ("landcover.tif", "impervious_pct.tif"):
        with rasterio.open(version_dir(SOURCE_ID, VERSION) / name) as src:
            assert src.width == grid.width
            assert src.height == grid.height
            assert src.crs.to_epsg() == grid.epsg
