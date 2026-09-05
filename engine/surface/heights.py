"""Building height estimation -- shared by the map export
(scripts/export_map_layers.py) and Phase 5's floor-count-weighted
dasymetric population redistribution (engine/equity/population.py).

Moved here from the export script once a second real consumer showed up
-- not a speculative abstraction. Most OSM buildings here carry no
height/building:levels tag (94 of 2,844 have building:levels; 1 has an
explicit height); estimated heights are real numbers derived from a
documented, disclosed heuristic, not invented ones. Every caller must
carry `height_provenance` through to wherever the number is used, not
blend it silently with measured values.
"""

from __future__ import annotations

import geopandas as gpd

METRES_PER_LEVEL = 3.5
ROOF_ALLOWANCE_M = 1.0
# Fallback height by OSM `building` tag value, for the ~97% of buildings
# with no height/levels tag at all. Rough, disclosed, and labeled as
# estimated wherever it's rendered -- not presented as measured.
DEFAULT_HEIGHT_BY_TYPE = {
    "house": 5.0,
    "residential": 5.0,
    "detached": 5.0,
    "terrace": 6.0,
    "apartments": 12.0,
    "commercial": 8.0,
    "retail": 7.0,
    "industrial": 8.0,
    "university": 10.0,
    "school": 8.0,
    "church": 12.0,
    "garage": 3.0,
    "carport": 3.0,
    "shed": 3.0,
    "roof": 3.0,
    "service": 4.0,
}
DEFAULT_HEIGHT_M = 5.0


def parse_height_tag(value: object) -> float | None:
    if value is None or (isinstance(value, float) and value != value):  # NaN
        return None
    s = str(value).strip().lower().replace("m", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def estimate_height_m(row: gpd.GeoSeries) -> tuple[float, str]:
    """Returns (height_m, provenance) -- provenance must be carried
    alongside the number, never silently blended with measured values."""
    height = parse_height_tag(row.get("height"))
    if height is not None and height > 0:
        return height, "measured"

    levels = parse_height_tag(row.get("building:levels"))
    if levels is not None and levels > 0:
        return levels * METRES_PER_LEVEL + ROOF_ALLOWANCE_M, "levels"

    building_type = str(row.get("building") or "").lower()
    return DEFAULT_HEIGHT_BY_TYPE.get(building_type, DEFAULT_HEIGHT_M), "estimated_default"


def estimate_floor_count(row: gpd.GeoSeries) -> int:
    """Whole-floor count for dasymetric weighting -- levels tag if present,
    else derived from the same height estimate divided by metres/level."""
    levels = parse_height_tag(row.get("building:levels"))
    if levels is not None and levels > 0:
        return max(1, round(levels))
    height_m, _ = estimate_height_m(row)
    return max(1, round(height_m / METRES_PER_LEVEL))
