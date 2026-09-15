# 27. Trees and cool roofs are separate programs, never ranked together

Date: 2026-09-15

## Status

Accepted. Supersedes the "disclosed, not fixed" decision in
[`0014-cool-roof-dominance-disclosed-not-fixed.md`](0014-cool-roof-dominance-disclosed-not-fixed.md).
Changes the headline comparison recorded in
[`0013-baselines-scope-and-comparison-fairness.md`](0013-baselines-scope-and-comparison-fairness.md).

## Context

ADR-0014 found that the optimizer's coverage function adds up two
different physical quantities: a tree's ambient cooling (spread over
~2,800 m² around it) and a cool roof's surface temperature change at its
own footprint (undiluted, mean ~12.9 °C). Ranked together, cool roofs win
every budget. It chose to disclose this rather than invent a conversion
factor, and named two ways a later phase could actually fix it.

Reviewing the product end to end on 2026-09-15 made the cost of leaving it
concrete:

- The default $50,000 plan — the first thing a visitor or judge sees —
  was **47 cool roofs on private homes and zero trees**, while the product
  asks "Where should the next 40 trees go?"
- That plan isn't one a city could carry out with the grant the product's
  own persona holds: tree-planting heat grants fund trees, and a private
  roof needs its owner's consent.
- The headline "4.6–14× better than Tree Equity Score ranking" was measured
  on that mixed pool, so a reader couldn't tell how much of it was smart
  siting and how much was "picked roofs."

## Decision

Take ADR-0014's second option. A plan chooses a **program**, and each
program only ranks interventions that deliver the same kind of benefit to
the same kind of beneficiary (`engine/optimize/programs.py`):

| Program | Interventions | Benefit | Default |
|---|---|---|---|
| `trees` | street trees, park/lot tree clusters | shade and ambient cooling for people outdoors | **yes**, on public land |
| `cool_roofs` | reflective roof coatings | lower surface temperature for the people inside | no |

`cool_pavement` and `shade_structure` are in neither pool: the objective
gives them zero population benefit (D4's disclosed scope), and leaving them
in only let a baseline strategy waste budget on them.

**Public land became a pool filter instead of a side constraint.** It
removes candidates before solving and doesn't couple picks to each other,
so the default plan still runs CELF (with its approximation guarantee)
rather than the slower non-lazy constrained greedy. The baseline comparison
now runs on exactly the pool the plan was solved on.

No conversion factor between surface and ambient temperature was
introduced. The fix changes *what is compared*, not the physics.

## Measured result (real data, real solver, real baselines)

Multiple = CoolBlock's equity-weighted cooling benefit ÷ the best
alternative strategy's, at the same budget and on the same pool. In every
row below the best alternative was Tree Equity Score ranking.

| Pool | $20,000 | $50,000 | $100,000 |
|---|---|---|---|
| All types, mixed (old default) | 4.6× — 22 cool roofs | 7.2× — 47 cool roofs | 14.0× — 89 cool roofs |
| Trees, any land | 7.9× — 5 sites | 3.3× — 15 sites | 3.1× — 16 sites |
| **Trees, public land (new default)** | **3.0× — 10 sites, 43 trees** | **1.4× — 9 sites, 115 trees** | **2.5× — 10 sites, 234 trees** |

So the advantage is real without the roof artifact — CoolBlock still beats
every baseline on trees — but it is smaller, and it is honestly 1.4–3.0×
on the plan a city would actually run, not 4.6–14×.

## Consequences

- API: `ConstraintsIn` gained `program` (default `"trees"`), and
  `public_land_only` now defaults to `true`. Existing plans without a
  stored `program` are solved as `trees`.
- The default-plan map layer (`optimizer_selection.geojson`) was
  regenerated from the real pipeline: 9 public sites, 115 trees, $50,000.
- The UI asks "What are you funding?" (Trees / Cool roofs) before the
  budget. Switching to cool roofs turns off the public-land filter, since
  almost all roofs are private.
- If an L1 plain-English request resolves a place to candidates outside the
  plan's pool (e.g. roofs near a school in a tree plan), the solve reports
  how many required sites were skipped instead of dropping them silently.
- Every public headline number (README, GUIDE, landing page) moves from
  4.6–14× to 1.4–3.0× for trees on public land.
