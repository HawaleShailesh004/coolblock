"""D3 -- NAIP (COOLBLOCK-BUILD-PLAN.md §5 data contract).

4-band (RGB+NIR) 0.6m aerial imagery for the surface segmentation module
(§6.2 B1/B2), which needs current-state imagery, not a time series. NAIP's
tile grid is unrelated to our neighborhood, so the locked bbox can straddle
more than one tile at a given acquisition date -- verified live (a
single-tile fetch left >50% of the target grid as nodata). This module
fetches every tile from the most recent acquisition date and mosaics them
onto the canonical grid, not just the single "most recent" item.

Uses a direct rasterio WarpedVRT per tile rather than odc-stac -- odc-stac
only read band 1 of NAIP's multi-band "image" asset (its `eo:bands`
declaration wasn't enough for odc-stac to expand it), silently dropping
G/B/NIR. Verified live during Phase 1; a direct multi-band read has no
such ambiguity.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import numpy as np
import planetary_computer
import pystac
import pystac_client
import rasterio
from affine import Affine
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT

from engine.config import load_neighborhood_config
from engine.ingest.grid import get_canonical_grid
from engine.ingest.manifest import is_cached, version_dir, write_manifest

SOURCE_ID = "naip"
VERSION = "2026-09-04"
LICENSE = "Public domain -- USDA NAIP, via Microsoft Planetary Computer"
PC_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
COLLECTION = "naip"
NATIVE_RESOLUTION_M = 0.6
BAND_NAMES = ["red", "green", "blue", "nir"]


def _item_date(item: pystac.Item) -> dt.date:
    assert item.datetime is not None, f"STAC item {item.id} has no datetime"
    return item.datetime.date()


def _most_recent_date_items() -> list[pystac.Item]:
    cfg = load_neighborhood_config()
    bbox = cfg.bbox_wgs84.as_tuple()
    catalog = pystac_client.Client.open(PC_STAC_URL, modifier=planetary_computer.sign_inplace)
    items = list(catalog.search(collections=[COLLECTION], bbox=bbox).items())
    if not items:
        raise RuntimeError("no NAIP acquisitions found for the locked bbox")
    most_recent_date = max(_item_date(it) for it in items)
    return [it for it in items if _item_date(it) == most_recent_date]


def _target_transform_and_size() -> tuple[Affine, int, int]:
    grid_10m = get_canonical_grid()
    minx, miny, maxx, maxy = grid_10m.bounds
    width = round((maxx - minx) / NATIVE_RESOLUTION_M)
    height = round((maxy - miny) / NATIVE_RESOLUTION_M)
    transform = Affine(NATIVE_RESOLUTION_M, 0.0, minx, 0.0, -NATIVE_RESOLUTION_M, maxy)
    return transform, width, height


def fetch_raw(items: list[pystac.Item]) -> np.ndarray[Any, np.dtype[np.uint8]]:
    cfg = load_neighborhood_config()
    transform, width, height = _target_transform_and_size()

    mosaic = np.zeros((4, height, width), dtype="uint8")
    for item in items:
        href = str(item.assets["image"].href)
        with rasterio.open(href) as src, WarpedVRT(
            src,
            crs=f"EPSG:{cfg.target_epsg}",
            transform=transform,
            width=width,
            height=height,
            resampling=Resampling.bilinear,
        ) as vrt:
            tile = vrt.read()
        # Fill only where the mosaic is still empty -- tiles don't overlap in
        # practice, but this keeps the merge order-independent either way.
        empty = mosaic.sum(axis=0) == 0
        for b in range(4):
            mosaic[b] = np.where(empty, tile[b], mosaic[b])

    return mosaic


def validate(arr: np.ndarray[Any, np.dtype[np.uint8]]) -> None:
    assert arr.shape[0] == 4, f"expected 4 bands (RGB+NIR), got {arr.shape[0]}"
    nonzero_frac = (arr > 0).mean()
    assert nonzero_frac > 0.9, "NAIP mosaic leaves significant nodata inside the neighborhood grid"
    assert np.issubdtype(arr.dtype, np.integer)
    assert arr.max() <= 255, "unexpected NAIP pixel value range for 8-bit imagery"


def run(force: bool = False) -> Path:
    if not force and is_cached(SOURCE_ID, VERSION):
        return version_dir(SOURCE_ID, VERSION)

    items = _most_recent_date_items()
    arr = fetch_raw(items)
    validate(arr)

    cfg = load_neighborhood_config()
    transform, width, height = _target_transform_and_size()

    vdir = version_dir(SOURCE_ID, VERSION)
    vdir.mkdir(parents=True, exist_ok=True)
    out_path = vdir / "naip_rgbir.tif"
    with rasterio.open(
        out_path,
        "w",
        driver="GTiff",
        dtype="uint8",
        width=width,
        height=height,
        count=4,
        crs=f"EPSG:{cfg.target_epsg}",
        transform=transform,
        compress="deflate",
    ) as dst:
        dst.write(arr)
        for i, name in enumerate(BAND_NAMES, start=1):
            dst.set_band_description(i, name)

    write_manifest(
        source=SOURCE_ID,
        version=VERSION,
        url=PC_STAC_URL,
        license=LICENSE,
        files=[out_path],
        bbox_wgs84=cfg.bbox_wgs84.as_tuple(),
        extra={
            "acquisition_date": _item_date(items[0]).isoformat(),
            "tile_count": len(items),
            "resolution_m": NATIVE_RESOLUTION_M,
            "bands": BAND_NAMES,
            "scene_ids": [it.id for it in items],
        },
    )
    return vdir


if __name__ == "__main__":
    result_dir = run()
    print(f"naip cached at {result_dir}")
