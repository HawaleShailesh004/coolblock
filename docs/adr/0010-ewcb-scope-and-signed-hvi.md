# 10. EWCB: mechanism-specific population attribution, signed HVI kept as-is

Date: 2026-09-05

## Status

Accepted

## Context

COOLBLOCK-BUILD-PLAN.md §6.4 D3/D4 specify exposure multipliers "derived
from OSM features" and:

    EWCB(S) = Σ_p  ΔT_S(x_p) · HVI(p) · exposure(p) · hours(p)

Building this against Phase 5's actual candidate set (five intervention
types across two physically distinct cooling mechanisms -- ambient
canopy cooling from C1, direct shading from C2, surface-temperature
change from C3) surfaced two real design questions the plan's formula
doesn't resolve on its own:

1. **`ΔT_S(x_p)` means something different for each mechanism.** C1's
   canopy ΔT is a Gaussian field with real spatial decay; C3's albedo ΔT
   is a point value at the retrofit's own footprint; C2's output isn't a
   ΔT at all, it's a duration (shade-hours). There is no single spatial
   join that correctly attributes all three to nearby population without
   either fabricating a decay model for C3 (no data supports one -- a cool
   roof's benefit doesn't obviously extend outward the way canopy
   evapotranspiration does) or inventing a ΔT-to-hours conversion factor
   to fold C2 in (nothing in this project's data justifies one).
2. **HVI is signed.** Running EWCB on real candidates immediately produced
   negative values (e.g. a cool-roof candidate at −20,993 person-degree-
   hours) -- mathematically correct given D2's z-scored HVI (centered at
   0, `docs/METHODOLOGY.md`'s D2 section), but a number a city council
   reader could easily mistake for an error.

## Decision

1. **Population attribution is mechanism-specific and only implemented
   where a real spatial linkage exists:**
   - Canopy candidates use C1's actual Gaussian ΔT(d) against every
     population point within 3σ (90m) -- reusing C1's own spatial model,
     not inventing a new one.
   - `cool_roof` attributes to the same building's own residential
     occupants (spatially joined back to D1), when the building is
     residential. Non-residential cool-roof candidates score 0 -- D1
     doesn't model non-residential occupancy, so nothing is guessed.
   - `cool_pavement` and `shade_structure` score 0 in EWCB. Neither has an
     "occupant" concept a residential-population dataset can attach to.
     Their real benefit is still reported directly by C3 and C2
     respectively -- EWCB's silence on them is a scope boundary, not a
     claim that they help nobody.
2. **C2's shade-hours is not folded into EWCB.** It stays a separate,
   real, standalone per-candidate metric. `hours(p)` in the EWCB formula
   is instead modeled as a constant (`DESIGN_DAY_HOURS = 10`, matching
   C2's daylight window) applied uniformly to C1/C3's steady-state ΔT
   values.
3. **HVI's sign is kept as specified, not floored or rescaled to force
   positivity.** A negative EWCB is disclosed and explained (module
   docstring, `docs/METHODOLOGY.md`'s D4 section) rather than silently
   "fixed" by an unstated rescaling that would deviate from the plan's
   literal z-score formula without a principled reason to prefer one
   offset over another.

## Consequences

- EWCB values from this phase's implementation are **not** a complete
  neighborhood-wide accounting of Phase 5's total modeled benefit --
  `cool_pavement` and `shade_structure` candidates always show 0 in this
  column despite having real, nonzero benefit elsewhere (C2/C3). Phase 6's
  optimizer, if it consumes `ewcb_person_degree_hours` directly as its
  objective, will effectively never select those two intervention types
  on equity grounds alone (their cost/benefit ratio for EWCB is
  undefined/zero) -- a real scope limitation to carry forward, not a
  reason to invent a number for them now.
- Any report or UI surfacing raw EWCB values must explain the sign (this
  is relative-to-neighborhood-mean equity weighting, not an absolute
  benefit magnitude) or a reader will reasonably interpret a negative
  "person-degree-hours" figure as a defect.
- If a future phase adds occupancy estimates for non-residential
  buildings, or a decay model for cool-roof/cool-pavement's areal
  influence, `_ewcb_cool_roof`'s pattern (spatial join, then multiply by
  HVI/exposure/hours) generalizes directly -- the gap is missing data, not
  a structural limitation of `engine/impact/ewcb.py`.
