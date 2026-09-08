# 20. L1: natural language to optimizer constraints, via real tool calls

Date: 2026-09-08

## Status

Accepted

## Context

COOLBLOCK-BUILD-PLAN.md §7.1 L1 asks for exactly one thing: *"Keep it to
public land, prioritize blocks near Garfield Elementary, cap maintenance
at $8k/yr" -> validated JSON config -> the solver*, done as "structured
output against a strict Pydantic schema, with tool calls to resolve place
names against the actual OSM feature table. Round-trips into real
compute" -- explicitly not a chat wrapper that free-parses a sentence and
hopes.

§12.1 marks L1 SHOULD-tier (this build is exactly on the compressed
calendar's Day 5 as of writing, ahead of pace on Phase 9/10 work relative
to the plan), and this session chose it over the other SHOULD-tier Phase
10 item (Wolfram verification) as the next concrete build, deferring L2
(per-site rationale), L4 (grant packet), and L5 (analyst agent) --
explicitly COULD-tier / roadmap-only per §12.1.

## Decision

### Scope: mirrors `ConstraintsIn`, not a bigger surface

`ParsedConstraints` (`engine/narrate/constraints_nl.py`) has exactly the
fields `apps/api`'s `ConstraintsIn` already has (`public_land_only`,
`max_sites_per_zone`, `min_spend_per_zone_usd`, `annual_maintenance_cap_usd`,
`mandatory_include_ids`, `mandatory_exclude_ids`) plus one addition,
`unsupported_requests: list[str]` -- the honesty-rail field. Budget is
deliberately excluded: `ConstraintsIn`'s own docstring already says
budget "lives on the plan itself, not nested inside its constraints," and
a sentence's budget mention (if any) is left to the existing budget
slider, not silently absorbed here as a second, possibly-conflicting
source of truth.

A model asked for something with no real field -- a species/genus
diversity cap, a water/irrigation budget, both already disclosed as
unmodeled in `engine.optimize.constraints`'s own docstring -- is
instructed to describe the request in `unsupported_requests` rather than
invent a field. This is the same honesty-rail pattern as L6's provenance
guard and L3's memo prompt: disclose a real gap, never paper over it.

### Real tool calls, not invented coordinates

Two tools, both run against this project's own real cached data:

- **`resolve_place(name)`** -- looks up a named location against
  `engine/ingest/d04_osm.py`'s cached "amenities" OSM export (schools,
  playgrounds, transit stops for this exact bbox). Substring + fuzzy
  matching only (`difflib`, cutoff 0.75) -- no geocoding API call, since
  this project's whole universe is the one cached bbox. Discloses "not
  found" rather than guessing when nothing matches closely enough.
- **`nearby_candidate_ids(lat, lon, radius_m)`** -- queries the exact same
  cached, scored candidate universe the solver itself reads
  (`engine.optimize.plan_service.load_candidate_universe`) for real
  candidate ids within a real metric radius of a resolved point.

The model's final answer is captured by forcing a third tool call,
`submit_constraints`, whose arguments are validated against
`ParsedConstraints` before anything is returned -- not free-text JSON
parsed out of a chat response.

### Two real bugs found in the first live run against real data

1. **A CRS bug in `resolve_place`.** The cached amenities parquet is
   stored in the neighborhood's own metric CRS (`EPSG:32612`, UTM zone
   12N) rather than WGS84 -- `row.geometry.centroid.y/.x` returned raw
   UTM northing/easting (e.g. `lat=3701340`), not degrees. Every
   downstream lat/lon (including the coordinates handed to
   `nearby_candidate_ids`) was silently wrong until this was caught by
   printing the actual return value against a real query
   ("Booker T Washington School," a real school in the cached bbox) and
   noticing the "latitude" was in the millions. Fixed by reprojecting the
   centroid to EPSG:4326 before returning it.
2. **A fuzzy-match threshold too permissive to disclose absence
   honestly.** At `difflib` cutoff 0.5, a genuinely nonexistent query
   ("Nonexistent Imaginary School") matched a real, unrelated place
   ("Bioscience High School") purely because both are multi-word strings
   ending in "School." Silently returning the wrong real place is worse
   than correctly reporting "not found" -- raised the cutoff to 0.75,
   confirmed the same query now returns `found: false`.

### A third bug, found only once Groq (not Claude) ran the tool loop live

Groq's `openai/gpt-oss-120b` (docs/adr/0019-*.md) emitted `null` for
`mandatory_include_ids`/`mandatory_exclude_ids` when it had nothing to
put there, rather than `[]`. Groq's own tool-call validator checks the
model's output against the schema *before* the response ever reaches
this code, and rejected it with an HTTP 400 (`"expected array, but got
null"`) -- a real failure hit running the live-gated test suite
(`RUN_LLM_TESTS=1`), not a hypothetical. Fixed two ways: the JSON schema
sent to both providers now explicitly widens the three list fields to
`anyOf: [array, null]` (so a model's `null` passes provider-side
validation), and `_normalize_submit_args` turns any such `null` back into
`[]` before `ParsedConstraints` ever sees it -- the dataclass's own
"always a list" guarantee is preserved regardless of what a given
provider's model chooses to emit.

### Verified end-to-end against the real API, real data, real model (Groq)

```
"Keep it to public land only, prioritize sites near Booker T Washington
School, cap annual maintenance at $8,000, and no more than 20% of one
tree species."
```

produced, through `POST /plans/parse-constraints`:
`public_land_only: true`, `annual_maintenance_cap_usd: 8000.0`, ten real
`mandatory_include_ids` (real candidate ids within 300m of the school's
real, resolved coordinates), and one `unsupported_requests` entry noting
the species cap has no real field -- disclosed, not invented. A second
real run against a nonexistent school name correctly reported
`found: false` rather than a false match.

## Consequences

- `apps/api`'s `POST /plans/parse-constraints` (new) is rate-limited
  (5/min/workspace) the same way `POST .../memo` is -- a real LLM API
  cost per call, plus a real geospatial query, not free.
- The frontend's `OptimizerPanel` gained the same provider choice L3's
  memo panel has (Groq default, Claude available), a free-text box, and
  a results readout showing exactly which real place resolved to which
  real candidate ids -- so a planner can see *why* a site was included,
  not just that it was.
- Same limitation as ADR-0018/0019: `RUN_LLM_TESTS=1` tests run against
  whichever provider `MEMO_LLM_PROVIDER` currently resolves to; the two
  live L1 tests in this pass were run and passed against Groq (the
  account's current working balance) -- Anthropic's own credit balance
  remains exhausted as of this writing, so this path is unverified
  end-to-end against Claude specifically, though the schema-widening and
  CRS fixes apply identically regardless of provider.
- `resolve_place`'s substring-then-fuzzy matching is intentionally simple
  (no embeddings, no external geocoder) -- correct for this project's one
  cached bbox, and would need real reconsideration (a proper geocoding
  service, most likely) before ever pointing this at a second
  neighborhood (§15, stretch/post-deadline).
