# 22. Self-hosted basemap glyphs and sprite (a real offline-demo-mode gap)

Date: 2026-09-08

## Status

Accepted

## Context

Phase 13's DoD is explicit: *"Offline demo mode -- a flag that serves
everything from the cached artefacts, verified with the network
throttled to zero,"* with the checkpoint *"disconnect the internet and
run the entire demo."* Auditing the frontend for exactly this (the first
concrete piece of Phase 13 work attempted) found one real, concrete gap:
`packages/map/src/basemapStyle.ts` set `glyphs`/`sprite` to live
`https://protomaps.github.io/basemaps-assets/...` URLs. The basemap
*tiles* themselves were already self-hosted from local MinIO
(`scripts/build_basemap.sh`, `NEXT_PUBLIC_PMTILES_URL`), so the map would
still render its shapes with no internet -- but every label (street
names, park names) and every icon (the sprite sheet) would silently fail
to load, which is a real, visible degradation a judge would notice, not
a hypothetical one.

## Decision

Added `scripts/build_map_assets.sh`, matching `build_basemap.sh`'s own
established pattern (download once from the public source, upload to the
same `coolblock-tiles` MinIO bucket, self-host from there after that).
Downloads only what this neighborhood's real labels need: the three
fontstacks `protomaps-themes-base`'s "black" theme actually declares
(`Noto Sans Regular/Medium/Italic`, confirmed by grepping the installed
package, not guessed) at Unicode ranges 0-255 and 256-511 (Basic Latin +
Latin-1 Supplement + Latin Extended-A -- covers this neighborhood's real
English street/park/POI names, with headroom for the occasional accented
proper noun), plus the "black" sprite sheet (both `@1x` and `@2x`).
Total: ~620 KB, six glyph files and four sprite files.

`basemapStyle.ts`'s `buildBasemapStyle()` now takes a second parameter,
`assetsBaseUrl`, and builds `glyphs`/`sprite` from it instead of the
hardcoded protomaps.github.io URLs -- threaded through `CoolBlockMap`'s
own props and `apps/web/app/map/page.tsx`'s new `NEXT_PUBLIC_MAP_ASSETS_URL`
env var (defaulting to the same local MinIO bucket
`NEXT_PUBLIC_PMTILES_URL` already uses).

**A real Windows/Docker bug found and fixed while writing the upload
script**: `docker run -v <path>:/upload` silently bound to nothing when
`<path>` was a plain Git-Bash POSIX path (e.g.
`/d/Hackathons/Next Steps/.map_assets_tmp`) -- the container's `/upload`
came up empty even though the files existed on disk, failing with
`mc: <ERROR> Unable to prepare URL for copying. Object does not exist`.
Root cause: Docker Desktop for Windows needs a Windows-style path for a
bind mount; MSYS's own path only translates automatically for certain
path shapes, and this one wasn't among them. Fixed by converting through
`cygpath -w` when available (a no-op skip on real POSIX hosts, where
`cygpath` doesn't exist). `build_basemap.sh`'s own `-v "$OUT_DIR:/upload"`
uses the exact same POSIX-path pattern and may carry the identical latent
bug -- not fixed here (out of this ADR's scope; that script wasn't
touched), but worth checking the next time it's re-run on Windows.

## Consequences

- `curl -I http://localhost:9000/coolblock-tiles/sprites/black.json` and
  `.../glyphs/Noto%20Sans%20Regular/0-255.pbf` both return real `200`s
  after running `scripts/build_map_assets.sh` once (containers up) --
  confirmed directly, not assumed from the upload log alone.
- Re-running `scripts/build_map_assets.sh` is required after a fresh
  `docker compose up` on a new machine, the same way `build_basemap.sh`
  and `export_map_layers.py` already are -- added to the same "one-time
  setup" category, not something `docker compose up` triggers itself.
- This is one concrete slice of Phase 13's much larger scope (E2E
  Playwright suite, golden-file tests, error-boundary coverage, security
  hardening, performance/bundle work, cross-browser testing) -- not a
  claim that Phase 13 as a whole is done. It was chosen first because it
  is the one item that directly and silently breaks the literal
  checkpoint ("disconnect the internet and run the entire demo") in a way
  a judge would visibly notice (missing labels/icons), and because it was
  concretely verifiable in one pass.
