"""B3b -- cool-roof / cool-pavement candidate generation
(COOLBLOCK-BUILD-PLAN.md §6.2 B3), the two intervention types
`docs/adr/0005-*.md` deferred out of Phase 4: they target *impervious*
surfaces (rooftops, parking lots), which the plantable-space rule layer
(`engine/surface/rule_layer.py`) explicitly excludes.

Real source polygons, not synthetic footprints: every OSM building (D4,
2,844 in this bbox) is a cool-roof candidate; every OSM off-street parking
lot (D4, 57 polygons, already ingested in Phase 4 to *exclude* from
plantable space) is a cool-pavement candidate.

**Disclosed limitation**: cool-roof coatings are only cost-effective on
flat or low-slope roofs in practice, but OSM carries no roof-shape/slope
tag for this bbox's buildings, and no other ingested source distinguishes
flat commercial/institutional roofs from pitched residential ones. Every
building footprint becomes a candidate regardless of actual roof geometry
-- over-inclusive of what a city could realistically act on, not silently
narrowed by an invented heuristic.

**Depaving-to-bioswale is still not generated** (carried over from
`docs/adr/0005-*.md`): no ingested source identifies which pavement is
*excess* capacity (safe to remove) versus functionally load-bearing
(a working parking space, an access lane). Guessing that distinction
would be worse than declining to generate the candidate type.
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from engine.ingest import d04_osm, d06_parcels
from engine.ingest.manifest import version_dir
from engine.surface.candidates import classify_ownership

# Midpoints of COOLBLOCK-BUILD-PLAN.md §6.2's planning-estimate cost table.
UNIT_COST_COOL_ROOF_USD_M2 = 5.5  # midpoint of $3-8/m2
UNIT_COST_COOL_PAVEMENT_USD_M2 = 17.5  # midpoint of $10-25/m2

MIN_CANDIDATE_AREA_M2 = 4.0  # matches rule_layer.py's tree-pit floor -- below this, rasterization/digitizing noise


def _to_candidates(
    footprints: gpd.GeoDataFrame,
    parcels: gpd.GeoDataFrame,
    intervention_type: str,
    unit_cost_usd_m2: float,
    id_prefix: str,
) -> gpd.GeoDataFrame:
    footprints = footprints[footprints.geometry.notna() & ~footprints.geometry.is_empty].copy()
    footprints["area_m2"] = footprints.geometry.area
    footprints = footprints[footprints["area_m2"] >= MIN_CANDIDATE_AREA_M2].reset_index(drop=True)

    classified = classify_ownership(footprints[["geometry", "area_m2"]], parcels)
    classified["candidate_id"] = [f"{id_prefix}-{i:05d}-{intervention_type}" for i in range(len(classified))]
    classified["intervention_type"] = intervention_type
    classified["capacity"] = 1
    classified["unit_cost_usd"] = unit_cost_usd_m2
    classified["total_cost_usd"] = classified["area_m2"] * unit_cost_usd_m2
    return classified[
        ["candidate_id", "area_m2", "ownership", "owner_name", "intervention_type",
         "capacity", "unit_cost_usd", "total_cost_usd", "geometry"]
    ]


def generate_impervious_candidates() -> gpd.GeoDataFrame:
    parcels = gpd.read_parquet(version_dir(d06_parcels.SOURCE_ID, d06_parcels.VERSION) / "parcels.parquet")

    buildings = gpd.read_parquet(version_dir(d04_osm.SOURCE_ID, d04_osm.VERSION) / "buildings.parquet").to_crs(
        parcels.crs
    )
    parking = gpd.read_parquet(version_dir(d04_osm.SOURCE_ID, d04_osm.VERSION) / "parking.parquet").to_crs(
        parcels.crs
    )

    cool_roof = _to_candidates(buildings, parcels, "cool_roof", UNIT_COST_COOL_ROOF_USD_M2, "roof")
    cool_pavement = _to_candidates(parking, parcels, "cool_pavement", UNIT_COST_COOL_PAVEMENT_USD_M2, "pave")

    combined = gpd.GeoDataFrame(
        pd.concat([cool_roof, cool_pavement], ignore_index=True),
        geometry="geometry",
        crs=parcels.crs,
    )
    return combined
