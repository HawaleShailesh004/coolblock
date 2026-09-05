"""The downscaling predictors (COOLBLOCK-BUILD-PLAN.md §6.1 A2 step 1):
NDVI, NDBI, an albedo proxy from Sentinel-2 (D2), and % impervious from
NLCD (D11) -- all reprojected onto the canonical grid so they line up with
each other and with the LST composite pixel for pixel.
"""

from __future__ import annotations

import rioxarray  # noqa: F401 -- registers the .rio accessor
import xarray as xr

from engine.ingest import d02_sentinel2, d11_nlcd
from engine.ingest.crs import to_canonical_crs_raster
from engine.ingest.grid import CanonicalGrid, get_canonical_grid
from engine.ingest.manifest import version_dir

# A simple, disclosed broadband albedo proxy (unweighted mean of the
# available Sentinel-2 bands) -- not a validated physical albedo retrieval.
# Good enough as one predictor among several in the downscaling regression;
# flagged here so nobody mistakes it for the real thing later.
ALBEDO_PROXY_NOTE = (
    "Unweighted mean of Sentinel-2 B02/B04/B08/B11 reflectance -- a proxy for "
    "regression purposes, not a validated broadband albedo retrieval."
)

# Sentinel-2 L2A surface reflectance is delivered as scaled digital numbers
# (the ESA-standard 1/10000 scale factor), not 0-1 reflectance directly.
# NDVI/NDBI are band ratios so the scale cancels out and this never
# mattered for them -- but albedo_proxy is an absolute value, and going
# out ~unscaled (DN ~1000-9000) was a real, previously-unnoticed bug: it
# didn't affect the Phase 3 downscaling regression (a gradient-boosted
# model splits on feature values regardless of their scale) but silently
# broke Phase 5's albedo energy-balance model (engine/impact/albedo.py),
# which needs a real 0-1 physical albedo. Caught when every candidate's
# current_albedo_proxy came back pegged at the model's clip ceiling.
SENTINEL2_REFLECTANCE_SCALE = 1.0 / 10000.0


def load_sentinel2_predictors(grid: CanonicalGrid | None = None) -> xr.Dataset:
    """The most recent cached Sentinel-2 scene's NDVI/NDBI/albedo-proxy,
    reprojected onto `grid` (default: the 10m canonical grid)."""
    grid = grid or get_canonical_grid()
    path = version_dir(d02_sentinel2.SOURCE_ID, d02_sentinel2.VERSION) / "predictors_one_per_summer.nc"
    ds = xr.open_dataset(path, decode_coords="all")
    latest = ds.isel(time=-1)

    red, nir, swir, blue = (
        latest["B04"].astype("float64") * SENTINEL2_REFLECTANCE_SCALE,
        latest["B08"].astype("float64") * SENTINEL2_REFLECTANCE_SCALE,
        latest["B11"].astype("float64") * SENTINEL2_REFLECTANCE_SCALE,
        latest["B02"].astype("float64") * SENTINEL2_REFLECTANCE_SCALE,
    )
    ndvi = (nir - red) / (nir + red).where((nir + red) != 0)
    ndbi = (swir - nir) / (swir + nir).where((swir + nir) != 0)
    albedo_proxy = (blue + red + nir + swir) / 4.0

    out = xr.Dataset({"ndvi": ndvi, "ndbi": ndbi, "albedo_proxy": albedo_proxy})
    out = out.rio.write_crs(ds.rio.crs)

    aligned = {name: to_canonical_crs_raster(out[name], resampling="bilinear", grid=grid) for name in out}
    return xr.Dataset(aligned)


def load_impervious_predictor(grid: CanonicalGrid | None = None) -> xr.DataArray:
    """% impervious (D11/NLCD). Reused directly at 10m, or aggregated onto a
    coarser `grid` with average resampling -- a physical percentage, not a
    category, so averaging 3x3 blocks is the correct aggregation."""
    grid = grid or get_canonical_grid()
    path = version_dir(d11_nlcd.SOURCE_ID, d11_nlcd.VERSION) / "impervious_pct.tif"

    raw = rioxarray.open_rasterio(path, masked=True)
    assert isinstance(raw, xr.DataArray), f"expected a single-band raster, got {type(raw)}"
    da = raw.squeeze("band", drop=True).astype("float64")
    da.name = "impervious_pct"

    native = get_canonical_grid()
    if grid.resolution_m == native.resolution_m:
        return da

    return to_canonical_crs_raster(da, resampling="average", grid=grid)


