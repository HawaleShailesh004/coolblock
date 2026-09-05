"""The one canonical CRS (COOLBLOCK-BUILD-PLAN.md §5.1.2): every ingest module
ends with a call into this file. WGS84 exists only at the API boundary.

Every ingest module reprojects through these two functions, never through a
hand-rolled `.to_crs()` call of its own -- that's what makes the CRS
invariant test (engine/tests/test_crs_invariant.py) a guarantee about the
whole pipeline rather than about one function nobody else uses.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from engine.config import load_neighborhood_config

if TYPE_CHECKING:
    import geopandas as gpd
    import xarray as xr

    from engine.ingest.grid import CanonicalGrid


def to_canonical_crs_vector(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        raise ValueError(
            "GeoDataFrame has no CRS set -- fix the source's declared CRS before "
            "reprojecting; guessing here is exactly the silent-failure mode this "
            "function exists to prevent."
        )
    cfg = load_neighborhood_config()
    return gdf.to_crs(epsg=cfg.target_epsg)


def to_canonical_crs_raster(
    da: xr.DataArray, *, resampling: str = "bilinear", grid: CanonicalGrid | None = None
) -> xr.DataArray:
    """Reproject onto a canonical grid (engine.ingest.grid) with an explicit,
    named resampling method -- see COOLBLOCK-BUILD-PLAN.md §5.1.4. Defaults
    to the 10m grid; pass `grid=get_grid_at_resolution(30)` etc. for a
    coarser nested grid (§6.1 A2's 30m fitting resolution)."""
    from rasterio.enums import Resampling

    from engine.ingest.grid import get_canonical_grid

    grid = grid or get_canonical_grid()
    reprojected = da.rio.reproject(
        f"EPSG:{grid.epsg}",
        transform=grid.transform,
        shape=(grid.height, grid.width),
        resampling=Resampling[resampling],
    )
    return reprojected  # type: ignore[no-any-return]  # rioxarray's .rio accessor is untyped
