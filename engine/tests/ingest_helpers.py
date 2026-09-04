"""Shared smoke-test helpers for engine.ingest modules.

Every source needs the same four checks (shape, CRS, bounds, null rate) --
see COOLBLOCK-BUILD-PLAN.md Phase 1 DoD: "every source has a smoke test
asserting shape, bounds, and null rate." This is reused by all sixteen
per-source test files, so it earns being factored out (not a speculative
abstraction -- the duplication already exists sixteen times over).
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from engine.config import load_neighborhood_config
from engine.ingest.manifest import version_dir


def load_cached_vector(source_id: str, version: str, filename: str) -> gpd.GeoDataFrame:
    return gpd.read_parquet(version_dir(source_id, version) / filename)


def assert_vector_smoke(
    gdf: gpd.GeoDataFrame,
    *,
    required_columns: list[str],
    min_rows: int = 1,
    null_check_columns: list[str] | None = None,
    min_non_null_fraction: float = 0.99,
    bbox_pad_m: float = 250.0,
) -> None:
    """The four checks every ingested vector source must pass."""
    assert len(gdf) >= min_rows, f"expected >= {min_rows} rows, got {len(gdf)}"
    for col in required_columns:
        assert col in gdf.columns, f"missing expected column {col!r}"

    cfg = load_neighborhood_config()
    assert gdf.crs is not None and gdf.crs.to_epsg() == cfg.target_epsg, (
        f"expected EPSG:{cfg.target_epsg}, got {gdf.crs}"
    )

    from engine.ingest.grid import get_canonical_grid

    minx, miny, maxx, maxy = gdf.total_bounds
    gminx, gminy, gmaxx, gmaxy = get_canonical_grid().bounds
    assert minx >= gminx - bbox_pad_m and maxx <= gmaxx + bbox_pad_m, "features fall outside the canonical grid (x)"
    assert miny >= gminy - bbox_pad_m and maxy <= gmaxy + bbox_pad_m, "features fall outside the canonical grid (y)"

    for col in null_check_columns or required_columns:
        frac = gdf[col].notna().mean()
        assert frac >= min_non_null_fraction, f"{col!r} null rate too high: {1 - frac:.2%} null"


def cache_file_path(source_id: str, version: str, filename: str) -> Path:
    return version_dir(source_id, version) / filename
