"""D1 -- dasymetric population redistribution (COOLBLOCK-BUILD-PLAN.md §6.4 D1).

Block-group population (D7) redistributed onto residential building
footprints, weighted by footprint area x floor count -- turning a coarse
polygon average into a realistic point cloud of where people actually are.

Real block-group *boundaries* come from D7b (Census TIGER/Line, added this
phase -- see engine/ingest/d07b_tiger_bg.py's docstring for why the
already-cached D10/TES boundaries weren't usable: different vintage,
different block-group delineation).

One disclosed judgment call: OSM's generic `building=yes` tag (1,155 of
2,844 buildings here, the largest single bucket) doesn't distinguish use.
Edison-Eastlake is overwhelmingly residential (verified visually against
NAIP imagery in Phase 4) so `yes` defaults to residential here rather than
being dropped -- dropping it would undercount the housing stock by nearly
half. This can still misclassify a small footprint (a shed, a bus
shelter) as residential, which barely matters under area x floor-count
weighting -- but it can also silently misclassify a *large* one. Two real
cases caught live during Phase 5 development, both fixed:

1. A `building=yes` hospital oncology clinic ("Dignity Health - Cancer
   Institute...", tagged `amenity=clinic`, `healthcare=clinic`, no
   residential tag at all) was absorbing over 10% of its block group's
   entire population. Fixed: `yes`-tagged buildings carrying any
   non-residential secondary tag (amenity, healthcare, shop, office,
   tourism, leisure, religion) are excluded regardless of footprint size.
2. A `building=yes` park structure ("Lath House Pavilion" -- a garden
   shade structure, not a dwelling) had *no* secondary tag at all to catch
   it, just a `name`. Checked every named `building=yes` in this bbox (43
   of them): all but a handful of Heritage Square's preserved historic
   houses (now museum/event-venue use, not inhabited) are clearly
   non-residential -- churches, a fire station, auto shops, a medical
   plaza, hotels. Actual dwellings are essentially never individually
   named in OSM. Fixed: any named `building=yes` is now excluded too.

One residual limitation, capped rather than hidden: in a mixed-use block
group where only one or two buildings end up classified residential (a
university/stadium district near Chase Field has exactly this shape --
30 buildings, mostly `university`/`stadium`/`roof`, only 1 left after the
fixes above), that lone building would otherwise absorb the *entire*
block group's ACS population -- 2,061 people in a single-storey, 370 sq m
structure, which is physically impossible. `MAX_PERSONS_PER_M2_FLOOR_AREA`
caps per-building density at a plausible dense-residential rate; population
that a block group's identified buildings can't plausibly hold is tracked
in `unallocated_population`, not silently dropped or overstated.
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from engine.ingest import d04_osm, d07_census, d07b_tiger_bg
from engine.ingest.manifest import version_dir
from engine.surface.heights import estimate_floor_count

RESIDENTIAL_BUILDING_TYPES = {
    "house",
    "apartments",
    "residential",
    "terrace",
    "detached",
    "semidetached_house",
    "bungalow",
    "dormitory",
    "yes",  # see module docstring -- excluded below if a non-residential secondary tag is present
}

# A building=yes with any of these set is not a dwelling, however large its footprint.
NON_RESIDENTIAL_SECONDARY_TAGS = ["amenity", "healthcare", "shop", "office", "tourism", "leisure", "religion"]

# A plausibility cap, not a measured density: ~15 sq m of total floor area
# (footprint x floors) per resident is a dense-apartment/dormitory rate.
# Prevents one identified building in a sparsely-classified block group
# from absorbing physically implausible population.
MAX_PERSONS_PER_M2_FLOOR_AREA = 1.0 / 15.0


def load_residential_buildings() -> gpd.GeoDataFrame:
    buildings = gpd.read_parquet(version_dir(d04_osm.SOURCE_ID, d04_osm.VERSION) / "buildings.parquet")
    candidate = buildings[buildings["building"].isin(RESIDENTIAL_BUILDING_TYPES)].copy()

    has_non_residential_tag = candidate.get("name", pd.Series(index=candidate.index)).notna()
    for tag in NON_RESIDENTIAL_SECONDARY_TAGS:
        if tag in candidate.columns:
            has_non_residential_tag |= candidate[tag].notna()
    residential = candidate[~((candidate["building"] == "yes") & has_non_residential_tag)].copy()

    residential["floor_count"] = residential.apply(estimate_floor_count, axis=1)
    residential["footprint_m2"] = residential.geometry.area
    residential["weight"] = residential["footprint_m2"] * residential["floor_count"]
    return residential


def redistribute_population() -> gpd.GeoDataFrame:
    """Returns the residential buildings GeoDataFrame with an added
    `population` column -- each building's share of its block group's
    total ACS population, proportional to area x floor-count weight."""
    buildings = load_residential_buildings()

    block_groups = gpd.read_parquet(
        version_dir(d07b_tiger_bg.SOURCE_ID, d07b_tiger_bg.VERSION) / "block_groups.parquet"
    ).to_crs(buildings.crs)
    acs = pd.read_parquet(version_dir(d07_census.SOURCE_ID, d07_census.VERSION) / "acs5_block_groups.parquet")
    acs["total_population"] = pd.to_numeric(acs["total_population"], errors="coerce")
    block_groups = block_groups.merge(acs[["geoid", "total_population"]], left_on="GEOID", right_on="geoid")

    centroids = gpd.GeoDataFrame(geometry=buildings.geometry.centroid, crs=buildings.crs)
    joined = gpd.sjoin(centroids, block_groups[["GEOID", "total_population", "geometry"]], how="left", predicate="within")
    joined = joined[~joined.index.duplicated(keep="first")]

    buildings["block_group_geoid"] = joined["GEOID"].to_numpy()
    buildings["block_group_population"] = joined["total_population"].to_numpy()

    weight_sum_by_bg = buildings.groupby("block_group_geoid")["weight"].transform("sum")
    buildings["population_uncapped"] = (
        buildings["block_group_population"] * buildings["weight"] / weight_sum_by_bg
    ).fillna(0.0)

    max_plausible = buildings["footprint_m2"] * buildings["floor_count"] * MAX_PERSONS_PER_M2_FLOOR_AREA
    buildings["population"] = buildings["population_uncapped"].clip(upper=max_plausible)

    return buildings


def summarize_unallocated_population(buildings: gpd.GeoDataFrame) -> pd.DataFrame:
    """Per block group: how much ACS population the density cap left
    without a plausible building to sit on. Not dropped silently -- a
    planner using this data should see where the model's ancillary data
    (building classification) was too coarse to place people confidently."""
    by_bg = buildings.groupby("block_group_geoid").agg(
        block_group_population=("block_group_population", "first"),
        allocated_population=("population", "sum"),
        n_buildings=("population", "size"),
    )
    by_bg["unallocated_population"] = by_bg["block_group_population"] - by_bg["allocated_population"]
    by_bg["unallocated_fraction"] = by_bg["unallocated_population"] / by_bg["block_group_population"]
    return by_bg.sort_values("unallocated_fraction", ascending=False)
