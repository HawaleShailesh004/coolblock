# CoolBlock — Data sources

> Status: Phase 0 skeleton, tracking COOLBLOCK-BUILD-PLAN.md §5. Populated
> for real (licence text, exact vintage, checksum) as each source is ingested
> in Phase 1 — see `engine/ingest/`. The `data/cache/<source>/<version>/manifest.json`
> written by each ingest module is the machine-readable source of truth;
> this table is the human-readable index into it.

| # | Source | Gives us | Access | Resolution | Status |
|---|---|---|---|---|---|
| D1 | Landsat 8/9 Collection 2 L2 | Surface temperature (`ST_B10`), QA mask | Planetary Computer STAC | 30 m | Not ingested |
| D2 | Sentinel-2 L2A | NDVI, NDBI, NDWI, albedo proxy | Planetary Computer STAC | 10 m | Not ingested |
| D3 | NAIP | 4-band RGB+NIR aerial imagery | Planetary Computer STAC | 0.6 m | Not ingested |
| D4 | OpenStreetMap / Overpass | Buildings, roads, land use, trees, amenities | Overpass API → GeoParquet | Vector | Not ingested |
| D5 | Microsoft Building Footprints | Footprints + height estimates | Open S3 / PC | Vector | Not ingested |
| D6 | Maricopa County Assessor parcels | Parcel geometry, ownership, land use code | County open-data portal | Vector | Not ingested — **verify access hour 1 (R3)** |
| D7 | Census ACS 5-year | Income, poverty, age, tenure, vehicle access | `api.census.gov` | Block group | Not ingested |
| D8 | CDC/ATSDR SVI | Composite social vulnerability | CDC CSV | Tract | Not ingested |
| D9 | CDC PLACES | Asthma, COPD, CHD, diabetes prevalence | CDC API | Tract | Not ingested |
| D10 | American Forests Tree Equity Score | Canopy %, TES score, heat disparity | Free API | Block group | Not ingested — cache day 1 |
| D11 | NLCD | Tree canopy cover, % impervious | MRLC / PC | 30 m | Not ingested |
| D12 | USGS 3DEP DEM | Terrain for shadow model | Planetary Computer | 1–10 m | Not ingested |
| D13 | Open-Meteo | Historical hourly air temperature | Keyless REST | Point | Not ingested |
| D14 | NASA POWER | Solar irradiance | Keyless REST | Point | Not ingested |
| D15 | Phoenix Open Data | Street-tree inventory, ROW, planned projects | City portal | Vector | Not ingested — city-specific |
| D16 | Literature corpus | The 5 papers + city plans, chunked for pgvector | Manual PDF ingest | — | Not ingested |

## Ingest discipline

See COOLBLOCK-BUILD-PLAN.md §5.1 — every fetch is cached, checksummed, and
manifest-tracked; one canonical CRS (EPSG:32612); the CRS invariant test
runs in CI before any downstream work; raster alignment is explicit onto a
fixed 10 m UTM grid; vintage is surfaced, never hidden.
