# 30. The locked neighborhood's derived data is committed, without owner names

Date: 2026-09-16

## Status

Accepted.

## Context

Pushing this repo to a public GitHub remote and deploying it for real
surfaced two problems in `data/derived/edison-eastlake/`, which had never
been examined with "this could be public" in mind.

**1. It's gitignored, but the running app needs it.** `plan_service.py`'s
own docstring is explicit: the API "reads the cached, already-scored
candidate universe... instead of recomputing C1-C3/D1-D4 per request" —
recomputing it is the 20-90 minute cold pipeline (§4.1), the wrong thing
to do on every request, and the wrong thing to ask a free-tier deploy
with no persistent volume and no bundled source-data credentials to do
on every cold start either. A deploy with nothing in this directory
doesn't run a slower demo — it doesn't run at all
(`CandidateUniverseMissing`).

**2. `candidates.geojson` (and anything derived from it) carries a real
person's name.** `engine/surface/candidates.py`'s `classify_ownership()`
joins each candidate against Maricopa County parcel records and keeps the
matched `OWNER_NAME` as its own `owner_name` column — used only to
*derive* the public/private `ownership` classification the optimizer
actually needs, but the raw name was carried through into every export
and every API response, and `apps/web`'s `ContextPanel` genuinely renders
every property of every layer it's given, click-to-inspect. That
combination means a real private parcel owner's name has been visible in
this running app, locally, this entire build — not yet exposed
(nothing had been deployed or pushed), but not something this project's
own stated privacy posture ("Strip private homeowner names from any
public or deployed data") tolerates being one step away from either.

## Decision

**Strip `owner_name` at its one point of export**, not at each of its
several call sites: `scripts/export_map_layers.py::_build_scored_candidates()`
drops the column right after `ownership` is derived from it, before
either `export_candidates()` or `export_optimizer_solution()` writes a
file or the live API reads one back in. Nothing downstream ever reads
`owner_name` (checked: no test, no API code, no frontend component) — it
existed only as an accidental pass-through, not a feature to preserve.

**Commit the resulting derived outputs**, as a narrow, explicit exception
to the blanket `data/derived/*` ignore rule: exactly the 10 files under
`data/derived/edison-eastlake/` (~15 MB total), named individually in
`.gitignore` rather than un-ignoring the directory wholesale, so nothing
new lands there by accident without a matching gitignore change. Every
other field in these files is already public: Census/CDC data at
block-group/tract level, OSM, Landsat/Sentinel-2-derived rasters, and
parcels identified by APN (a public tax record number), not by owner.

## Consequences

- A fresh clone (or a fresh Render deploy) has a working app immediately
  — no ingest run required first, matching this project's own "the cold
  pipeline runs once, offline" design rather than fighting it.
- `data/derived/edison-eastlake/` will drift from a from-scratch pipeline
  re-run unless someone remembers to re-export and re-commit; a script
  drifting from its own committed output is now a real possibility this
  project didn't have to think about before. Re-run
  `uv run python scripts/export_map_layers.py` (and
  `export_heat_surface.py` if the thermal surface itself changed) and
  commit the result whenever the pipeline changes — same discipline
  already used for `apps/web/public/landing/*.json`
  (`scripts/export_landing_scene.py`, ADR-0029).
- If this project ever adds a second neighborhood, or a program with a
  materially different privacy posture (e.g. per-resident data, not
  per-parcel), this decision does not automatically extend to it —
  re-check before committing.
