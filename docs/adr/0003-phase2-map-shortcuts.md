# 3. Phase 2 shortcuts: static layer serving, estimated building heights

Date: 2026-09-05

## Status

Accepted

## Context

Phase 2's goal (§10) is "get pixels on screen on day one so the front end
never becomes an end-loaded risk" -- explicitly before Phase 7 builds the
real FastAPI + PostGIS + PMTiles serving path. Two decisions were needed
now that Phase 7 will supersede.

## Decisions

1. **Vector layers are served as static GeoJSON via a Next.js API route**
   (`apps/web/app/api/layers/[name]/route.ts`), reading directly from
   `data/derived/edison-eastlake/*.geojson` (produced by
   `scripts/export_map_layers.py` from the Phase 1 ingest cache). No
   database, no dynamic tiling. This is intentionally temporary -- Phase 7
   replaces it with real PostGIS-backed endpoints and PMTiles generation.
   The source of truth stays `data/cache/` (Phase 1); nothing is
   duplicated into `apps/web/public`.

2. **Building heights are estimated, not measured, for ~97% of buildings.**
   Verified live: only 94 of 2,844 OSM buildings carry `building:levels`,
   and only 1 carries an explicit `height`. `scripts/export_map_layers.py`
   uses measured height where present, `levels * 3.5m + 1m roof` where
   `building:levels` is present, and a documented per-building-type default
   otherwise (§ module docstring for the exact table). Every feature
   carries a `height_provenance` field (`measured` / `levels` /
   `estimated_default`), and the extrusion layer renders estimated
   buildings at visibly lower opacity -- the honesty rail (§1.4) applied at
   the map layer, not just in prose.

3. **The basemap is a neighborhood-scoped Protomaps extract, not a full
   planet file.** `scripts/build_basemap.sh` pulls ~3.7MB via HTTP range
   requests from Protomaps' public daily build
   (build.protomaps.com/YYYYMMDD.pmtiles, ~120GB) for a bbox around the
   locked neighborhood, then uploads to the local MinIO stand-in
   (`coolblock-tiles/basemap.pmtiles`) -- matching §3.3's "Protomaps +
   PMTiles on R2, self-hosted."

## Consequences

- Anyone regenerating the map data must run `scripts/export_map_layers.py`
  (Phase 1 cache -> GeoJSON) after any ingest change, and
  `scripts/build_basemap.sh` once (or if the bbox changes).
- The `/api/layers/[name]` route and its 3-item allowlist (`buildings`,
  `roads`, `parcels`) are deleted, not extended, when Phase 7 lands --
  extending it instead of replacing it would leave two parallel serving
  paths.
- `height_provenance` needs to survive into whatever Phase 7's schema
  looks like; dropping it would silently upgrade estimated heights to
  looking measured.
