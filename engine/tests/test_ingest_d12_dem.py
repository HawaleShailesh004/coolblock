from __future__ import annotations

import pytest
import rasterio
from engine.ingest.d12_dem import NODATA, PLAUSIBLE_ELEV_M, SOURCE_ID, VERSION
from engine.ingest.grid import get_canonical_grid
from engine.ingest.manifest import is_cached, version_dir

pytestmark = pytest.mark.skipif(
    not is_cached(SOURCE_ID, VERSION), reason="D12 not ingested yet -- run engine.ingest.d12_dem"
)


def test_smoke() -> None:
    grid = get_canonical_grid()
    with rasterio.open(version_dir(SOURCE_ID, VERSION) / "dem.tif") as src:
        assert src.width == grid.width
        assert src.height == grid.height
        assert src.crs.to_epsg() == grid.epsg

        arr = src.read(1)
        valid = arr[arr != NODATA]
        assert valid.size > 0
        lo, hi = PLAUSIBLE_ELEV_M
        assert ((valid >= lo) & (valid <= hi)).mean() > 0.9
