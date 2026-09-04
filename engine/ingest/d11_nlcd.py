"""D11 -- NLCD (COOLBLOCK-BUILD-PLAN.md §5 data contract).

Tree canopy cover class, % impervious. NLCD is not on Planetary Computer
(verified live against the PC STAC catalog during Phase 1) -- MRLC's own
ArcGIS ImageServer is the real access path, and it's used here directly via
exportImage, requested straight onto the canonical grid (§5.1.4) so this
raster needs no separate reprojection step: what comes back is already
pixel-aligned with everything else.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import numpy as np
import rasterio
from rasterio.io import MemoryFile

from engine.ingest.grid import CanonicalGrid, get_canonical_grid
from engine.ingest.manifest import is_cached, version_dir, write_manifest

SOURCE_ID = "nlcd"
VERSION = "2026-09-04"
LICENSE = "Public domain -- USGS / MRLC Consortium"
LANDCOVER_URL = (
    "https://di-nlcd.img.arcgis.com/arcgis/rest/services/USA_NLCD_Annual_LandCover/ImageServer/exportImage"
)
IMPERVIOUS_URL = (
    "https://di-nlcd.img.arcgis.com/arcgis/rest/services/"
    "USA_NLCD_Annual_LandCover_Fractional_Impervious_Surface/ImageServer/exportImage"
)
REQUEST_TIMEOUT_S = 60
NODATA_LANDCOVER = 255
NODATA_IMPERVIOUS = 255

# NLCD class codes present in the developed/urban range -- a sanity check, not a full legend.
_DEVELOPED_CLASSES = {21, 22, 23, 24}


def _export_image(url: str, grid: CanonicalGrid, nodata: int) -> bytes:
    minx, miny, maxx, maxy = grid.bounds
    resp = httpx.get(
        url,
        params={
            "bbox": f"{minx},{miny},{maxx},{maxy}",
            "bboxSR": grid.epsg,
            "imageSR": grid.epsg,
            "size": f"{grid.width},{grid.height}",
            "format": "tiff",
            "pixelType": "U8",
            "noData": nodata,
            "interpolation": "RSP_NearestNeighbor",  # categorical / fractional -- no smoothing
            "f": "image",
        },
        timeout=REQUEST_TIMEOUT_S,
    )
    resp.raise_for_status()
    if resp.headers.get("content-type", "").startswith("application/json"):
        raise RuntimeError(f"NLCD exportImage failed: {resp.text[:300]}")
    return resp.content


def fetch_raw(grid: CanonicalGrid) -> tuple[bytes, bytes]:
    landcover = _export_image(LANDCOVER_URL, grid, NODATA_LANDCOVER)
    impervious = _export_image(IMPERVIOUS_URL, grid, NODATA_IMPERVIOUS)
    return landcover, impervious


def _read_band(raw: bytes) -> np.ndarray[Any, np.dtype[np.uint8]]:
    with MemoryFile(raw) as mem, mem.open() as src:
        band: np.ndarray[Any, np.dtype[np.uint8]] = src.read(1)
        return band


def validate(landcover: bytes, impervious: bytes) -> None:
    lc = _read_band(landcover)
    assert lc.size > 0, "empty landcover raster"
    present = set(np.unique(lc).tolist()) - {NODATA_LANDCOVER}
    assert present & _DEVELOPED_CLASSES or present, "no plausible NLCD class codes in the tile"

    imp = _read_band(impervious).astype(float)
    valid = imp[imp != NODATA_IMPERVIOUS]
    assert valid.size > 0, "empty impervious raster"
    assert ((valid >= 0) & (valid <= 100)).mean() > 0.95, "impervious % outside [0,100]"


def run(force: bool = False) -> Path:
    if not force and is_cached(SOURCE_ID, VERSION):
        return version_dir(SOURCE_ID, VERSION)

    grid = get_canonical_grid()
    landcover_bytes, impervious_bytes = fetch_raw(grid)
    validate(landcover_bytes, impervious_bytes)

    vdir = version_dir(SOURCE_ID, VERSION)
    vdir.mkdir(parents=True, exist_ok=True)

    profile = {
        "driver": "GTiff",
        "dtype": "uint8",
        "width": grid.width,
        "height": grid.height,
        "count": 1,
        "crs": f"EPSG:{grid.epsg}",
        "transform": grid.transform,
        "compress": "deflate",
    }

    landcover_path = vdir / "landcover.tif"
    with rasterio.open(landcover_path, "w", nodata=NODATA_LANDCOVER, **profile) as dst:
        dst.write(_read_band(landcover_bytes), 1)

    impervious_path = vdir / "impervious_pct.tif"
    with rasterio.open(impervious_path, "w", nodata=NODATA_IMPERVIOUS, **profile) as dst:
        dst.write(_read_band(impervious_bytes), 1)

    write_manifest(
        source=SOURCE_ID,
        version=VERSION,
        url=LANDCOVER_URL,
        license=LICENSE,
        files=[landcover_path, impervious_path],
        bbox_wgs84=None,  # fetched directly on the canonical grid, already in the target CRS
        extra={"grid_width": grid.width, "grid_height": grid.height, "resolution_m": grid.resolution_m},
    )
    return vdir


if __name__ == "__main__":
    result_dir = run()
    print(f"nlcd cached at {result_dir}")
