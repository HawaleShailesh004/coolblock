"""Exports cached Phase 1 vector layers to GeoJSON for the map app (Phase 2).

Phase 2 scope is "get pixels on screen," not the real API/DB serving layer
(that's Phase 7 -- FastAPI + PostGIS + PMTiles generation). This is a
one-off static export: data/cache/*.parquet (engine.ingest's output) ->
data/derived/edison-eastlake/*.geojson (apps/web reads these directly).
Re-run whenever the underlying ingest cache changes.

Building heights are estimated, not measured -- most OSM buildings here
carry no height/building:levels tag (94 of 2,844 have building:levels; 1
has an explicit height). Estimated heights are real numbers derived from a
documented, disclosed heuristic, not invented ones; the frontend labels
them as estimated. See _estimate_height_m below for the exact rule.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
from engine.impact.albedo import run_albedo_model
from engine.impact.cooling_kernel import run_cooling_kernel
from engine.impact.ewcb import compute_ewcb
from engine.impact.shade import run_shade_raytrace
from engine.ingest import d04_osm, d06_parcels
from engine.ingest.manifest import version_dir
from engine.surface.candidates import generate_candidates
from engine.surface.heights import estimate_height_m as _estimate_height_m
from engine.surface.impervious_candidates import generate_impervious_candidates

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "data" / "derived" / "edison-eastlake"


def export_buildings() -> Path:
    gdf = gpd.read_parquet(version_dir(d04_osm.SOURCE_ID, d04_osm.VERSION) / "buildings.parquet")
    gdf = gdf.to_crs(epsg=4326)  # GeoJSON is WGS84 by convention; MapLibre expects it

    heights, provenances = zip(*(_estimate_height_m(row) for _, row in gdf.iterrows()), strict=True)
    out = gpd.GeoDataFrame(
        {
            "name": gdf.get("name"),
            "building_type": gdf.get("building"),
            "height_m": heights,
            "height_provenance": provenances,
            "geometry": gdf.geometry,
        },
        crs="EPSG:4326",
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "buildings.geojson"
    out.to_file(out_path, driver="GeoJSON")
    return out_path


def export_roads() -> Path:
    gdf = gpd.read_parquet(version_dir(d04_osm.SOURCE_ID, d04_osm.VERSION) / "roads.parquet")
    gdf = gdf.to_crs(epsg=4326)
    out = gpd.GeoDataFrame(
        {"name": gdf.get("name"), "highway": gdf.get("highway"), "geometry": gdf.geometry},
        crs="EPSG:4326",
    )
    out_path = OUT_DIR / "roads.geojson"
    out.to_file(out_path, driver="GeoJSON")
    return out_path


def export_parcels() -> Path:
    gdf = gpd.read_parquet(version_dir(d06_parcels.SOURCE_ID, d06_parcels.VERSION) / "parcels.parquet")
    gdf = gdf.to_crs(epsg=4326)
    out = gpd.GeoDataFrame(
        {"apn": gdf.get("APN"), "land_use_code": gdf.get("LC_CUR"), "geometry": gdf.geometry},
        crs="EPSG:4326",
    )
    out_path = OUT_DIR / "parcels.geojson"
    out.to_file(out_path, driver="GeoJSON")
    return out_path


def export_candidates() -> Path:
    """Phase 4 plantable-space candidates (`engine.surface.candidates`) plus
    Phase 5's impervious-surface candidates
    (`engine.surface.impervious_candidates`), each carrying its full Phase 5
    impact/equity scoring: C1's `delta_t_peak_degc` (canopy candidates),
    C3's `delta_t_degc` (`cool_roof`/`cool_pavement`), C2's
    `shade_hours_delivered`, and D4's `ewcb_person_degree_hours` (with
    `ewcb_low`/`ewcb_high` confidence bounds) -- exactly the Phase 5
    checkpoint (COOLBLOCK-BUILD-PLAN.md line 854): "a card showing its
    modeled cooling, its shade contribution, and the number and
    vulnerability of people reached."

    The plan says "hover"; this map's existing interaction model
    (`apps/web/app/map/page.tsx`'s `ContextPanel`, already used for
    buildings/parcels since Phase 2) is click-to-inspect, generically
    rendering every GeoJSON property -- adding these fields here is
    already sufficient for them to appear there without new UI code, so
    "hover" is implemented as "click" for consistency with every other
    layer, not fixed to a different interaction just for this one."""
    tree_candidates = generate_candidates()
    tree_scored, calibration = run_cooling_kernel(tree_candidates)
    tree_scored, _design_day = run_shade_raytrace(tree_scored)

    impervious_candidates = generate_impervious_candidates()
    impervious_scored, _inputs, _design_day2 = run_albedo_model(impervious_candidates)

    combined = gpd.GeoDataFrame(
        pd.concat([tree_scored, impervious_scored], ignore_index=True),
        geometry="geometry",
        crs=tree_scored.crs,
    )
    combined = compute_ewcb(combined, cooling_calibration=calibration)

    out = combined.to_crs(epsg=4326)
    out_path = OUT_DIR / "candidates.geojson"
    out.to_file(out_path, driver="GeoJSON")
    return out_path


def main() -> None:
    for label, fn in [
        ("buildings", export_buildings),
        ("roads", export_roads),
        ("parcels", export_parcels),
        ("candidates", export_candidates),
    ]:
        path = fn()
        size_kb = path.stat().st_size / 1024
        print(f"{label}: {path} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
