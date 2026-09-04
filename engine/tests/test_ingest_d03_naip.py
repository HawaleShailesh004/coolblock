from __future__ import annotations

import pytest
import rasterio
from engine.ingest.d03_naip import BAND_NAMES, SOURCE_ID, VERSION
from engine.ingest.grid import get_canonical_grid
from engine.ingest.manifest import is_cached, version_dir

pytestmark = pytest.mark.skipif(
    not is_cached(SOURCE_ID, VERSION), reason="D3 not ingested yet -- run engine.ingest.d03_naip"
)


def test_smoke() -> None:
    with rasterio.open(version_dir(SOURCE_ID, VERSION) / "naip_rgbir.tif") as src:
        assert src.count == len(BAND_NAMES)
        arr = src.read()
        nonzero_frac = (arr > 0).mean()
        assert nonzero_frac > 0.9  # near-full coverage after the multi-tile mosaic fix
        assert arr.max() <= 255


def test_covers_the_canonical_grid_extent() -> None:
    grid = get_canonical_grid()
    with rasterio.open(version_dir(SOURCE_ID, VERSION) / "naip_rgbir.tif") as src:
        assert src.crs.to_epsg() == grid.epsg
        gminx, gminy, gmaxx, gmaxy = grid.bounds
        sminx, sminy, smaxx, smaxy = src.bounds
        tol = 1.0  # metres
        assert sminx <= gminx + tol and smaxx >= gmaxx - tol
        assert sminy <= gminy + tol and smaxy >= gmaxy - tol
