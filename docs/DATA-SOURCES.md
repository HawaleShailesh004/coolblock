# CoolBlock — Data sources

> Status: complete (all 16 sources ingested; Phase 1, COOLBLOCK-BUILD-PLAN.md §5). Every row
> below reflects a real ingest run against the locked bbox
> (`config/neighborhood.toml`), not a plan. The
> `data/cache/<source>/<version>/manifest.json` written by each ingest
> module (`engine/ingest/dNN_*.py`) is the machine-readable source of truth,
> checksummed and timestamped; this table is the human-readable index into
> it.

| # | Source | Gives us | Access | Resolution | Status |
|---|---|---|---|---|---|
| D1 | Landsat 8/9 Collection 2 L2 | Surface temperature (`lwir11`), QA mask | Planetary Computer STAC | 30 m | **Live** — 63 scenes, summer 2021-2025 |
| D2 | Sentinel-2 L2A | NDVI/NDBI/albedo predictors | Planetary Computer STAC | 10 m | **Live** — 1 least-cloudy scene/summer, 2021-2025 |
| D3 | NAIP | 4-band RGB+NIR aerial imagery | Planetary Computer STAC | 0.6 m | **Live** — most recent acquisition, mosaicked across tiles |
| D4 | OpenStreetMap / Overpass | Buildings, roads, land use, trees, amenities, parking lots | Overpass API → GeoParquet | Vector | **Live** — 2,844 buildings, 2,734 roads, 208 landuse, 832 trees, 72 amenities, 57 parking lots (added Phase 4, see note below) |
| D5 | Microsoft Building Footprints | Footprints + height estimates | Azure Blob (`abfs://`), partitioned by country | Vector | **Superseded by D4.** See note below. |
| D6 | Maricopa County Assessor parcels | Parcel geometry, ownership, land use code | County ArcGIS REST | Vector | **Live** — 2,956 parcels (R3 verified hour 1) |
| D7 | Census ACS 5-year (2022) | Income, poverty, age, tenure, vehicle access | `api.census.gov` | Block group (poverty/vehicle: tract) | **Live** — 23 block groups, 9 tracts |
| D8 | CDC/ATSDR SVI (2022) | Composite social vulnerability | onemap.cdc.gov ArcGIS REST | Tract | **Live** — 9 tracts |
| D9 | CDC PLACES | Asthma, COPD, CHD, diabetes prevalence | Socrata (`data.cdc.gov`) | Tract | **Live** — 9 tracts, keyed to D8's FIPS |
| D10 | Tree Equity Score | Canopy %, TES score, heat disparity | Third-party ArcGIS mirror (2020) | Block group | **Live** — 13 block groups. See note below. |
| D11 | NLCD | Land cover class, % impervious | MRLC ArcGIS ImageServer | 30 m, on the 10 m canonical grid | **Live** — classes 21-24 (developed), 2-98% impervious |
| D12 | USGS 3DEP DEM | Terrain for shadow model | Planetary Computer STAC | 10 m native, direct WarpedVRT | **Live** — 330-338 m elevation |
| D13 | Open-Meteo | Historical hourly air temperature | Keyless REST | Point (centroid) | **Live** — 14,640 hourly readings, 2021-2025 |
| D14 | NASA POWER | Solar irradiance | Keyless REST | Point (centroid) | **Live** — 610 daily readings, 2021-2025 |
| D15 | Phoenix Open Data | 2024 Shade Phoenix Plan: LST, canopy %, shade %, CEJST flags | City ArcGIS REST | Tract | **Live** — 9 tracts. See note below. |
| D16 | Literature corpus | The 5 papers + city plans, citation metadata | Manual, from the strategy brief | — | **Citations registered.** PDF acquisition + pgvector chunking deferred to Phase 10. |

## Notes on sources that didn't match their original one-line description

**D4 — a parking-lot layer was added in Phase 4.** The Phase 4 manual
spot-check (`docs/METHODOLOGY.md`) found a real paved parking lot flagged
as plantable space, because the original D4 query captured roads (linear
highway features) and buildings but not off-street parking lots, a
distinct OSM feature type (`amenity=parking` as a polygon). Added a
dedicated Overpass query; 57 real polygons, 17.8 ha, now excluded in
`engine/surface/rule_layer.py`.

**D5 (Microsoft Building Footprints) — superseded by D4.** Verified live: the
Planetary Computer `ms-buildings` STAC item's exposed schema carries only a
`geometry` column, no height field, so the data contract's "footprints +
height estimates" isn't actually available through this path. The dataset
itself lives in an Azure Blob container (`abfs://`), country-partitioned
(129M rows for `RegionName=United States`), reachable via DuckDB's `azure` +
`spatial` extensions but with no further spatial partition pruning below
country level — a full-dataset scan for one ~2 km neighborhood. Given D4
(OSM/Overpass) already supplies 2,844 real, validated building footprints
for Edison-Eastlake, this was judged not worth the access-path cost for the
marginal (and, per the exposed schema, nonexistent) height data. Building
heights for the shadow model (§6.3 C2) will instead come from DEM (D12) +
OSM `building:levels` tags where present, revisited in Phase 4/5 if that
proves insufficient.

**D10 (Tree Equity Score) — no official public API.** American Forests does
not expose one (verified against treeequityscore.org, not assumed — it's an
interactive map only). This uses a public third-party ArcGIS mirror of the
published Phoenix 2020 block-group scores instead, labeled as such in
`engine/ingest/d10_tree_equity_score.py` and in every manifest's `license`
field.

**D15 (Phoenix Open Data) — richer than "street-tree inventory."** The
city's actual published dataset for this purpose is the 2024 Shade Phoenix
Plan tract-level layer: average land surface temperature (the city's own
named hot spots — feeds the A3 validation gate in §6.1 directly), tree
canopy %, shade coverage at 12pm/3pm/6pm, sidewalk shade %, and federal
Justice40 (CEJST) / Qualified Census Tract flags. A literal street-tree
point inventory was not found on the city's open-data portal during Phase 1
research.

## Ingest discipline

See COOLBLOCK-BUILD-PLAN.md §5.1 — every fetch is cached, checksummed, and
manifest-tracked; one canonical CRS (EPSG:32612); the CRS invariant test
(`engine/tests/test_crs_invariant.py`) runs before any downstream work;
raster alignment is explicit onto a fixed 10 m UTM grid
(`engine/ingest/grid.py`); vintage is surfaced, never hidden.

Two things worth naming for whoever picks this up next:

1. **odc-stac silently returns wrong data for some collections.** It
   returned an all-NaN array for 3DEP DEM (native EPSG:4269 COGs) and only
   read band 1 of NAIP's multi-band `image` asset despite a correct
   `eo:bands` declaration. Both are worked around with a direct
   `rasterio.vrt.WarpedVRT` instead (see `d12_dem.py`, `d03_naip.py`). If a
   later phase adds another STAC raster source, verify the loaded array
   isn't all-NaN and has the expected band count before trusting odc-stac's
   default behaviour.
2. **A "search this bbox" query is not "clip to this bbox."** OSM/Overpass
   returns complete way/relation geometry for anything intersecting the
   query bbox — a long road or a large landuse polygon can extend far past
   the neighborhood. `engine/ingest/grid.py::clip_to_canonical_grid` exists
   specifically for this and is applied after reprojection in every vector
   module where it matters.
