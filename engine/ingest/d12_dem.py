"""D12 -- USGS 3DEP DEM (COOLBLOCK-BUILD-PLAN.md §5 data contract).

Terrain for the shadow model (§6.3 C2). Found via Planetary Computer STAC
(collection `3dep-seamless`), but loaded with a direct rasterio
`WarpedVRT` rather than odc-stac -- odc-stac returned an all-NaN array for
this collection's native EPSG:4269 COGs during Phase 1 testing (root cause
not chased further; a direct read+warp is simpler and was verified to
return real elevation data). Reprojected straight onto the canonical grid.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import planetary_computer
import pystac_client
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT

from engine.config import load_neighborhood_config
from engine.ingest.grid import CanonicalGrid, get_canonical_grid
from engine.ingest.manifest import is_cached, version_dir, write_manifest

SOURCE_ID = "usgs_3dep_dem"
VERSION = "2026-09-04"
LICENSE = "Public domain -- USGS 3D Elevation Program"
PC_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
COLLECTION = "3dep-seamless"
NODATA = -9999.0
# Phoenix sits at ~330-370m elevation; a plausibility band, not a model.
PLAUSIBLE_ELEV_M = (250.0, 500.0)


def _best_item_href() -> str:
    cfg = load_neighborhood_config()
    bbox = cfg.bbox_wgs84.as_tuple()
    catalog = pystac_client.Client.open(PC_STAC_URL, modifier=planetary_computer.sign_inplace)
    items = list(catalog.search(collections=[COLLECTION], bbox=bbox).items())
    if not items:
        raise RuntimeError(f"no {COLLECTION} items found for the locked bbox")
    # Prefer the finest-resolution seamless tile available (gsd in metres).
    best = min(items, key=lambda it: it.properties.get("gsd", 999))
    return str(best.assets["data"].href)


def fetch_raw(grid: CanonicalGrid) -> np.ndarray[Any, np.dtype[np.float32]]:
    href = _best_item_href()
    with rasterio.open(href) as src, WarpedVRT(
        src,
        crs=f"EPSG:{grid.epsg}",
        transform=grid.transform,
        width=grid.width,
        height=grid.height,
        resampling=Resampling.bilinear,
        nodata=NODATA,
    ) as vrt:
        band: np.ndarray[Any, np.dtype[np.float32]] = vrt.read(1)
        return band


def validate(arr: np.ndarray[Any, np.dtype[np.float32]]) -> None:
    valid = arr[arr != NODATA]
    assert valid.size > 0, "DEM tile is entirely nodata"
    lo, hi = PLAUSIBLE_ELEV_M
    assert ((valid >= lo) & (valid <= hi)).mean() > 0.9, "elevation outside a plausible range for Phoenix"


def run(force: bool = False) -> Path:
    if not force and is_cached(SOURCE_ID, VERSION):
        return version_dir(SOURCE_ID, VERSION)

    grid = get_canonical_grid()
    arr = fetch_raw(grid)
    validate(arr)

    vdir = version_dir(SOURCE_ID, VERSION)
    vdir.mkdir(parents=True, exist_ok=True)
    out_path = vdir / "dem.tif"
    with rasterio.open(
        out_path,
        "w",
        driver="GTiff",
        dtype="float32",
        width=grid.width,
        height=grid.height,
        count=1,
        crs=f"EPSG:{grid.epsg}",
        transform=grid.transform,
        nodata=NODATA,
        compress="deflate",
    ) as dst:
        dst.write(arr.astype("float32"), 1)

    write_manifest(
        source=SOURCE_ID,
        version=VERSION,
        url=PC_STAC_URL,
        license=LICENSE,
        files=[out_path],
        bbox_wgs84=None,
        extra={"grid_width": grid.width, "grid_height": grid.height, "resolution_m": grid.resolution_m},
    )
    return vdir


if __name__ == "__main__":
    result_dir = run()
    print(f"usgs_3dep_dem cached at {result_dir}")
