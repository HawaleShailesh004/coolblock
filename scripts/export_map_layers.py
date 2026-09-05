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
from engine.ingest import d04_osm, d06_parcels
from engine.ingest.manifest import version_dir
from engine.surface.candidates import generate_candidates
from engine.surface.heights import estimate_height_m as _estimate_height_m

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
    """Phase 4 plantable-space candidates (engine.surface). Every feature
    carries `intervention_type`, `ownership`, `capacity`, and cost fields --
    the map's context panel shows these on click so a candidate's basis is
    never hidden behind a colour."""
    gdf = generate_candidates()
    out = gdf.to_crs(epsg=4326)
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
