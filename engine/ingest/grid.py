"""The canonical 10 m raster grid -- defined once (COOLBLOCK-BUILD-PLAN.md §5.1.4).

Every raster in the pipeline is reprojected onto this exact grid (same CRS,
origin, resolution) with a named resampling method. No implicit alignment,
ever -- two rasters that both claim "10m over Edison-Eastlake" must be
pixel-for-pixel co-registered, or every downstream sum/compare is wrong.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from affine import Affine
from pyproj import Transformer

from engine.config import NeighborhoodConfig, load_neighborhood_config

if TYPE_CHECKING:
    import geopandas as gpd

# Buffer around the locked bbox so edge candidates (a tree near the block's
# edge; a shadow cast in from a neighboring building) aren't clipped away.
GRID_BUFFER_M = 200.0


@dataclass(frozen=True)
class CanonicalGrid:
    epsg: int
    resolution_m: float
    transform: Affine
    width: int
    height: int

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        minx, maxy = self.transform.c, self.transform.f
        maxx = minx + self.width * self.resolution_m
        miny = maxy - self.height * self.resolution_m
        return (minx, miny, maxx, maxy)


def _canonical_grid(cfg: NeighborhoodConfig) -> CanonicalGrid:
    transformer = Transformer.from_crs(cfg.wgs84_epsg, cfg.target_epsg, always_xy=True)
    bbox = cfg.bbox_wgs84
    x0, y0 = transformer.transform(bbox.min_lon, bbox.min_lat)
    x1, y1 = transformer.transform(bbox.max_lon, bbox.max_lat)
    minx, maxx = min(x0, x1), max(x0, x1)
    miny, maxy = min(y0, y1), max(y0, y1)

    res = float(cfg.grid_resolution_m)
    # Snap the origin to a multiple of the resolution so the grid is a fixed,
    # reproducible artifact -- not a function of floating-point bbox noise.
    origin_x = math.floor((minx - GRID_BUFFER_M) / res) * res
    origin_y = math.ceil((maxy + GRID_BUFFER_M) / res) * res  # top-left; rows run north->south
    width = math.ceil((maxx + GRID_BUFFER_M - origin_x) / res)
    height = math.ceil((origin_y - (miny - GRID_BUFFER_M)) / res)

    transform = Affine(res, 0.0, origin_x, 0.0, -res, origin_y)
    return CanonicalGrid(
        epsg=cfg.target_epsg,
        resolution_m=res,
        transform=transform,
        width=width,
        height=height,
    )


def get_canonical_grid() -> CanonicalGrid:
    return _canonical_grid(load_neighborhood_config())


def get_grid_at_resolution(resolution_m: float) -> CanonicalGrid:
    """A grid at a coarser resolution that exactly nests the canonical grid
    (COOLBLOCK-BUILD-PLAN.md §6.1 A2: TsHARP fits at 30m, predicts at 10m).

    `resolution_m` must be an integer multiple of the base resolution --
    the origin is snapped to a multiple of `resolution_m` itself (not just
    the base grid's origin), so every coarse pixel covers exactly
    `(resolution_m / base_resolution)**2` base pixels with no partial
    overlap at the edges.
    """
    base = get_canonical_grid()
    if resolution_m == base.resolution_m:
        return base
    if resolution_m % base.resolution_m != 0:
        raise ValueError(
            f"{resolution_m}m must be an integer multiple of the base {base.resolution_m}m grid"
        )

    minx, miny, maxx, maxy = base.bounds
    origin_x = math.floor(minx / resolution_m) * resolution_m
    origin_y = math.ceil(maxy / resolution_m) * resolution_m
    width = math.ceil((maxx - origin_x) / resolution_m)
    height = math.ceil((origin_y - miny) / resolution_m)

    transform = Affine(resolution_m, 0.0, origin_x, 0.0, -resolution_m, origin_y)
    return CanonicalGrid(epsg=base.epsg, resolution_m=resolution_m, transform=transform, width=width, height=height)


def clip_to_canonical_grid(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Clip a GeoDataFrame (already in the canonical CRS) to the grid bounds.

    Several vector sources (notably OSM/Overpass) return complete
    way/relation geometry for anything intersecting the query bbox, not a
    bbox-clipped fragment -- a long road or a large landuse polygon can
    extend far past the neighborhood. Cached data should stay scoped to the
    locked neighborhood (§1.3), not to whatever a source's API happened to
    return whole.
    """
    from shapely.geometry import box

    grid = get_canonical_grid()
    return gdf.clip(box(*grid.bounds))
