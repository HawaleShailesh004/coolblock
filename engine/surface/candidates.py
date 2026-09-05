"""B3 -- fusion & candidate generation (COOLBLOCK-BUILD-PLAN.md §6.2 B3).

No ML fusion yet -- B2 (SegFormer-B0) is deliberately not implemented this
phase. The plan's own risk register (R4) says the rule layer alone is
sufficient for a working product and ML is an accuracy upgrade, not a
dependency: "ship rule-first." Documented in docs/adr/0005-*.md.

For each plantable polygon (B1): ownership (public ROW / public parcel /
private, from a real parcel join), capacity, and feasible intervention
types. Only tree-planting interventions are generated here -- cool
pavement, cool roofs, and depave-to-bioswale target *impervious* surfaces
(parking lots, roofs), which the rule layer explicitly excludes from
"plantable" (bare ground). Those need their own candidate generation pass
against different source polygons and are deferred to Phase 5/6, not
faked here with unsupported heuristics.
"""

from __future__ import annotations

from typing import Any

import geopandas as gpd
import numpy as np

from engine.ingest import d04_osm, d06_parcels
from engine.ingest.manifest import version_dir
from engine.surface.rule_layer import run_rule_layer

# Real government owners identified in the Maricopa parcel data during
# Phase 4 (109 of ~2,956 parcels) -- not a guess, verified against the
# actual OWNER_NAME values present for this neighborhood.
PUBLIC_OWNER_PATTERN = (
    r"^PHOENIX CITY OF|^STATE OF ARIZONA|^MARICOPA COUNTY$|SCHOOL DISTRICT|"
    r"STADIUM DISTRICT|HOUSING AUTHORITY|^UNITED STATES"
)

STREET_TREE_SPACING_M = 6.0
TREE_CLUSTER_SPACING_M = 8.0
MIN_CLUSTER_AREA_M2 = 100.0  # below this, a "cluster" is just one tree -- classify as street tree instead
ROAD_PROXIMITY_M = 10.0  # a private/parcel candidate this close to a road is still street-tree feasible
BUS_STOP_PROXIMITY_M = 20.0

# Planning-estimate unit costs (COOLBLOCK-BUILD-PLAN.md §6.2 B3 table), USD.
UNIT_COST_STREET_TREE = 800.0  # midpoint of $400-1,200 planted
UNIT_COST_CLUSTER_TREE = 425.0  # midpoint of $250-600
UNIT_COST_SHADE_STRUCTURE = 16_500.0  # midpoint of $8,000-25,000


def classify_ownership(plantable: gpd.GeoDataFrame, parcels: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    parcels = parcels.copy()
    parcels["is_public"] = parcels["OWNER_NAME"].fillna("").str.contains(
        PUBLIC_OWNER_PATTERN, case=False, regex=True
    )

    centroids = gpd.GeoDataFrame(geometry=plantable.geometry.centroid, crs=plantable.crs)
    joined = gpd.sjoin(centroids, parcels[["OWNER_NAME", "is_public", "geometry"]], how="left", predicate="within")
    joined = joined[~joined.index.duplicated(keep="first")]

    ownership = np.where(
        joined["OWNER_NAME"].isna(),
        "public_row",
        np.where(joined["is_public"].fillna(False), "public_parcel", "private"),
    )
    out = plantable.copy()
    out["ownership"] = ownership
    out["owner_name"] = joined["OWNER_NAME"].to_numpy()
    return out


def _near_any(
    points: gpd.GeoDataFrame, geoms: gpd.GeoSeries, distance_m: float
) -> np.ndarray[Any, np.dtype[np.bool_]]:
    if len(geoms) == 0:
        return np.zeros(len(points), dtype=bool)
    sindex = geoms.sindex
    result = np.zeros(len(points), dtype=bool)
    for i, geom in enumerate(points.geometry):
        buffered = geom.buffer(distance_m)
        candidates = sindex.query(buffered, predicate="intersects")
        result[i] = len(candidates) > 0
    return result


def generate_candidates() -> gpd.GeoDataFrame:
    plantable = run_rule_layer()
    parcels = gpd.read_parquet(version_dir(d06_parcels.SOURCE_ID, d06_parcels.VERSION) / "parcels.parquet")
    plantable = classify_ownership(plantable, parcels)

    roads = gpd.read_parquet(version_dir(d04_osm.SOURCE_ID, d04_osm.VERSION) / "roads.parquet").to_crs(
        plantable.crs
    )
    amenities = gpd.read_parquet(version_dir(d04_osm.SOURCE_ID, d04_osm.VERSION) / "amenities.parquet").to_crs(
        plantable.crs
    )
    bus_stops = amenities[amenities.get("highway") == "bus_stop"]

    centroids = gpd.GeoDataFrame(geometry=plantable.geometry.centroid, crs=plantable.crs)
    near_road = _near_any(centroids, roads.geometry, ROAD_PROXIMITY_M)
    near_bus_stop = _near_any(centroids, bus_stops.geometry, BUS_STOP_PROXIMITY_M)

    records: list[dict[str, object]] = []
    for i, row in plantable.iterrows():
        area = row["area_m2"]
        ownership = row["ownership"]
        base = {
            "area_m2": area,
            "ownership": ownership,
            "owner_name": row["owner_name"],
            "geometry": row.geometry,
        }

        is_cluster_eligible = area >= MIN_CLUSTER_AREA_M2
        is_street_tree_eligible = (ownership == "public_row") or near_road[i]

        if is_cluster_eligible:
            capacity = int(area // (TREE_CLUSTER_SPACING_M**2))
            if capacity > 0:
                records.append({
                    **base,
                    "candidate_id": f"plant-{i:05d}-park_lot_tree_cluster",
                    "intervention_type": "park_lot_tree_cluster",
                    "capacity": capacity,
                    "unit_cost_usd": UNIT_COST_CLUSTER_TREE,
                    "total_cost_usd": capacity * UNIT_COST_CLUSTER_TREE,
                })
        elif is_street_tree_eligible:
            capacity = max(1, int(area // (STREET_TREE_SPACING_M**2))) if area >= 4.0 else 0
            if capacity > 0:
                records.append({
                    **base,
                    "candidate_id": f"plant-{i:05d}-street_tree",
                    "intervention_type": "street_tree",
                    "capacity": capacity,
                    "unit_cost_usd": UNIT_COST_STREET_TREE,
                    "total_cost_usd": capacity * UNIT_COST_STREET_TREE,
                })

        if ownership == "public_row" and near_bus_stop[i]:
            records.append({
                **base,
                "candidate_id": f"plant-{i:05d}-shade_structure",
                "intervention_type": "shade_structure",
                "capacity": 1,
                "unit_cost_usd": UNIT_COST_SHADE_STRUCTURE,
                "total_cost_usd": UNIT_COST_SHADE_STRUCTURE,
            })

    if not records:
        return gpd.GeoDataFrame(
            columns=[
                "candidate_id", "area_m2", "ownership", "owner_name", "intervention_type",
                "capacity", "unit_cost_usd", "total_cost_usd", "geometry",
            ],
            geometry="geometry",
            crs=plantable.crs,
        )

    return gpd.GeoDataFrame(records, geometry="geometry", crs=plantable.crs)
