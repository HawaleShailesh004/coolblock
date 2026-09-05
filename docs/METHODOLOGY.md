# CoolBlock — Methodology

> Status: Phase 3 in progress. This page is the honesty rail (COOLBLOCK-BUILD-PLAN.md
> §1.4) rendered in-app — every claim the product makes must trace back to a
> section here. It is not written once at the end; each phase appends its own
> section as that piece of the pipeline lands.

## How to read this document

Every modeled number in CoolBlock carries an epistemic status: computed,
modeled with a stated confidence band, or a prioritization score standing in
for a model that didn't validate. This page is where that status is defined
and where the honesty-rail decisions (§1.4) get recorded when they're made,
not after the fact.

## The heat surface (Phase 3)

**Status: validation gate FAILED (2 of 3 checks pass) — language downgraded.
See the decision below.** Full numbers and figures:
[`notebooks/01-thermal-validation.ipynb`](../notebooks/01-thermal-validation.ipynb).

### Method

- **A1, the composite** (`engine/thermal/composite.py`): the median (not
  mean — a single hot cloud-edge artefact destroys a mean) surface
  temperature across 63 cloud/shadow-masked Landsat 8/9 scenes, summer
  2021–2025. Masking uses the Collection 2 `QA_PIXEL` bit flags (fill,
  dilated cloud, cirrus, cloud, cloud shadow all clear; the "clear" bit
  set). 91.8% of pixels are clear on the average scene.
- **A2, TsHARP downscaling** (`engine/thermal/downscale.py`): a
  gradient-boosted regressor (`HistGradientBoostingRegressor`) fit at 30m
  on NDVI, NDBI, an albedo proxy (Sentinel-2), and % impervious (NLCD),
  spatially cross-validated (5-fold, spatially blocked — not a random
  shuffle, which would leak information between adjacent, correlated
  pixels). The fitted model's 30m residual is bilinearly upsampled and
  added back onto the 10m prediction (mass-conserving). Per-pixel
  uncertainty comes from a pair of quantile regressors (q10/q90).
  - **R² (spatial CV) = 0.215, RMSE = 0.94°C**, n = 4,556 training pixels.
    A modest R² — expected for a small, thermally homogeneous dense-urban
    neighborhood with limited predictor variance to explain, not a
    red flag on its own.
  - Uncertainty band (q90−q10): mean 1.94°C, range 0.09–4.93°C.
- **A3, the validation gate** (`engine/thermal/validate.py`): three
  independent checks, detailed in the notebook.

### The three checks and the result

| # | Check | Result | Threshold | Pass? |
|---|---|---|---|---|
| 1 | LST vs. Open-Meteo air temp, per scene (Pearson r) | **r = 0.369** (n=59 scenes) | ≥ 0.30 | ✅ |
| 2 | Parking-lot vs. park/grass contrast (°C) | **−13.2°C** (wrong sign) | ≥ +0.5°C | ❌ |
| 3 | Tract-mean LST vs. Phoenix's own 2024 Shade Plan (Spearman ρ) | **ρ = 0.683** (n=9 tracts) | ≥ 0.30 | ✅ |

Check 2 was investigated, not dismissed. All 10 OSM `amenity=parking`
polygons in this bbox that carry a `building:levels` tag show 4–7 levels —
these are multi-storey parking **structures**, so the satellite reads
rooftop temperature, not open pavement. Re-running the comparison against
the full set of OSM `landuse` categories shows `grass`-tagged parcels
reading *hotter* on average than `residential`, `commercial`, and `retail`
land — not just hotter than parking structures. There is no clean "cool,
irrigated, shaded park" ground-truth polygon available in this
neighborhood's OSM tagging to validate against either way. (This finding —
that nominally "green" land reads hot here — is itself consistent with the
canopy/irrigation-gap literature this project cites, but it means check #2
cannot currently confirm or refute the surface.)

### The honesty-rail decision

Per §1.4, a gate that does not clear all three checks does not get quietly
waved through. **Two of three checks pass, with the strongest evidence
(check 3) coming from comparison against the city's own published data,
not a proxy. One check fails for a data-availability reason, not a
demonstrated flaw in the composite or downscaling method.**

Decision (recorded here and in `docs/adr/0004-thermal-validation-honesty-rail.md`):
**the product's language is "prioritization score," not "predicted
cooling," everywhere the heat surface's output is shown**, until check #2
can be re-run against better ground truth (Maricopa parcel land-use codes,
D6, instead of OSM tags — flagged as Phase 5+ follow-up work). This is not
a project failure; it is the validation gate doing its job, and it is
disclosed rather than hidden.

## Plantable space (Phase 4)

**Status: rule layer only (B1 + B3); ML fusion (B2) deliberately deferred.**
See `docs/adr/0005-plantable-space-rule-first.md`. Full numbers and figures:
[`notebooks/02-plantable-space.ipynb`](../notebooks/02-plantable-space.ipynb).

### Method

From NAIP (0.6m), subtract buildings (+1m buffer), road carriageways
(+lane buffer, by OSM highway class), off-street parking lots, and
existing tree canopy — a proxy from real OSM tree points (832 of them)
buffered by an assumed 4m crown radius, since a normalized surface model
(DSM − DEM) needed to compute actual canopy *height* isn't available from
currently ingested sources (D12 is bare-earth only). What's left —
**1,481 polygons, 300.8 ha, 52% of the neighborhood** — is plantable.

For each polygon: ownership (public right-of-way / public parcel / private,
from a real parcel-owner-name join — 109 genuinely government-owned
parcels identified, e.g. "PHOENIX CITY OF"), capacity (area ÷ spacing²),
and feasible intervention types. **1,472 candidates**: 801 park/lot tree
clusters, 649 street trees, 22 shade structures at bus stops. Cool
pavement, cool roofs, and depave-to-bioswale are not generated — they
target impervious surfaces the rule layer explicitly excludes, and need a
different source polygon set (Phase 5/6 follow-up).

### The manual spot-check (Phase 4 DoD)

30 random candidates, checked against real NAIP image chips, twice:

- **Round 1** found a real paved, striped parking lot flagged as
  plantable. Traced to a genuine gap — the original rule layer excluded
  roads (linear highway features) and buildings, but not off-street
  parking lots, a distinct OSM feature type. Fixed: added a dedicated
  Overpass query for `amenity=parking` (57 real polygons, 17.8 ha) and
  excluded them.
- **Round 2** (fresh random sample, seed=7, after the fix): **2 of 30**
  still showed real paved lots with visible cars — traced to those
  specific lots not being tagged `amenity=parking` in OpenStreetMap at
  all. This is OSM tagging *incompleteness*, not a repeat of the same
  logic gap, and there is no complete ground-truth parking-lot layer
  available to close it fully.

**Error rate: 2/30 = 6.7%**, attributable to open-data completeness, not
the rule layer's logic. Disclosed rather than chased indefinitely.

## Cooling impact (Phase 5)

### C1 — the canopy cooling kernel

`engine/impact/cooling_kernel.py` implements the plan's kernel exactly as
specified in §6.3 C1:

    ΔT_peak = β · f_canopy_increment · g(impervious_fraction) · h(LST_anomaly)
    ΔT(d)   = ΔT_peak · exp(−d² / 2σ²)          σ = 30 m (literature midpoint, 25-40 m)

**β is calibrated on this neighborhood's own data, not imported from the
literature** — an OLS regression of the Phase 3 downscaled 10m LST field
against local existing canopy fraction (the same buffered-OSM-tree-point
proxy `engine/surface/rule_layer.py` uses for existing canopy, smoothed
over the same 30m radius the kernel itself projects influence across),
controlling for % impervious (D11) so the canopy coefficient isn't just
re-capturing "impervious areas are also tree-sparse."

Measured on real data: **β = −6.95°C per unit canopy-fraction increment**
(95% CI: [−7.20, −6.71], tight and clearly non-zero) — meaning going from
0% to 100% canopy coverage within a 30m radius is associated with roughly
7°C lower surface temperature, consistent in order of magnitude with the
plan's literature anchors (up to 1.5°C for realistic single-tree/street
canopy increments, which this model reproduces: a single street tree's
canopy increment is ~1.8% of the kernel's influence area, yielding
ΔT_peak ≈ 0.1-0.3°C once g() and h() are applied). **R² = 0.073** — canopy
alone explains a small share of raw LST variance (LST is driven by many
factors besides local canopy: albedo, building mass, irrigation, distance
to bare desert soil), which is disclosed here rather than hidden behind
the confidence interval on β alone. The coefficient is precise; the model
is not a complete explanation of temperature.

**Disclosed simplifications:**

1. **No wind/aspect term** (the plan's `w(wind/aspect)`, held at 1.0) — no
   urban-canyon wind-flow model exists in this project's scope, and
   Open-Meteo's (D13) single neighborhood-average wind vector has no way
   to resolve street-canyon channelling at individual-candidate scale.
   Faking a directional multiplier from one averaged wind reading would be
   worse than omitting it.
2. **One Gaussian patch per candidate, not per planted tree.** A
   `park_lot_tree_cluster` candidate with capacity > 1 scales
   `f_canopy_increment` rather than placing multiple kernel centers across
   its polygon — consistent with the plan's own point that overlapping
   tree benefits are not additive (§6.5 E1).
3. **`shade_structure` candidates get zero canopy ΔT.** They plant no
   canopy, so the tree-crown formula would be physically meaningless for
   them (caught as a real bug during development — see
   `engine/tests/test_cooling_kernel.py::test_shade_structures_get_no_canopy_delta_t`).
   Their cooling benefit is a direct shading effect, to be captured by C2
   (shade-hours delivered to pedestrian space) once implemented, not by
   this ambient canopy-regression kernel.

Measured candidate output (1,472 real candidates from Phase 4's rule
layer): street trees ΔT_peak ≈ 0.11-0.29°C, tree clusters ≈ 0.07-7.9°C
(scaling with cluster capacity up to full local canopy saturation), shade
structures = 0.0°C by construction.

## Equity weighting (Phase 5)

Two composites feed the equity side of scoring: who lives where
(population), and how vulnerable they are to heat (HVI). Both are computed
at Census block-group level — the granularity D7 (ACS5) is published at,
and the level D7b's real block-group polygons (see below) support.

### D1 — dasymetric population redistribution

`engine/equity/population.py` redistributes each block group's ACS total
population onto its residential building footprints, weighted by
footprint area × estimated floor count, rather than treating population as
uniform across the block group polygon (the standard "dasymetric" fix for
the modifiable-areal-unit problem).

Real block-group *boundaries* come from **D7b** (Census TIGER/Line 2022),
a source added this phase, not one of the original 16 in the data
contract. The only other block-group polygon set already cached (D10, Tree
Equity Score, 2020 vintage) only matched 9 of D7's 23 block groups — Census
periodically redraws block-group boundaries, and TES/ACS don't share a
vintage. D7b is keyless REST, direct from Census, clipped to the same
locked bbox as every other source.

Floor counts reuse the same building-height model as the map's 3D
extrusion (`engine/surface/heights.py`, shared rather than duplicated):
the OSM `building:levels` tag when present, otherwise height ÷ 3.5m/level
derived from the same OSM `height` tag or per-type default used for
rendering.

**Disclosed judgment call:** OSM's generic `building=yes` tag (1,155 of
2,844 buildings in this bbox — the largest single bucket) doesn't
distinguish residential from other use. Edison-Eastlake is overwhelmingly
residential (verified visually against NAIP imagery during Phase 4's
spot-check), so `yes` defaults to residential rather than being dropped —
dropping it would undercount the housing stock by nearly half. Two real
misclassifications this caused were caught and fixed during development
(see the module docstring in `engine/equity/population.py` for the exact
cases — a hospital oncology clinic and a park pavilion, both `yes`-tagged
with no residential signal): any `yes`-tagged building carrying a
non-residential secondary tag (`amenity`, `healthcare`, `shop`, `office`,
`tourism`, `leisure`, `religion`) or a `name` is excluded, since actual
dwellings are essentially never individually named in OSM.

**Disclosed limitation, capped rather than hidden:** in a block group
where only one or two buildings end up classified residential (a
university/stadium district near Chase Field has exactly this shape),
that lone building would otherwise absorb its block group's *entire* ACS
population — thousands of people in a single small structure, which is
physically impossible. `MAX_PERSONS_PER_M2_FLOOR_AREA` (a dense-apartment
rate, 1 person per 15 m² of total floor area) caps per-building density;
population a block group's identified buildings can't plausibly hold is
tracked per block group by `summarize_unallocated_population()` rather
than silently dropped or overstated onto a building. Across all 23 block
groups, roughly a third of the neighborhood's ACS population (13,253 of
25,953 allocated) currently lands in this unallocated bucket — a real
finding about OSM residential-building under-coverage in this
neighborhood, not a modeling artifact, and it is surfaced rather than
smoothed away.

### D2 — Heat Vulnerability Index (HVI)

`engine/equity/hvi.py` computes, per block group:

    HVI = mean( z(SVI), z(%age65+), z(%age<5), z(asthma+CHD prevalence),
                z(%renter), z(%no-vehicle) )

Weights default to equal (`DEFAULT_WEIGHTS`) but are a parameter, not a
hardcoded formula — a planner can and should argue with them, and
`compute_hvi(weights=...)` makes re-weighting a function call. A
sensitivity check (`engine/tests/test_equity_hvi.py::test_hvi_sensitivity_to_weights`)
confirms that an SVI-only weighting produces a genuinely different block
group ranking from the equal weighting, not just a rescaled copy of it.

**Disclosed adaptations:**

1. **No AC-access indicator.** No such data source exists in the current
   data contract, and none is ingested to fake one — HVI here is the mean
   of six available z-scores, not the seven the plan's formula lists.
2. **Tract-to-block-group broadcast.** SVI (D8) and PLACES (D9, asthma/CHD
   prevalence) are published at Census *tract* level; each tract's value
   is broadcast to its constituent block groups, the same approach already
   used for D7's own tract-level poverty/vehicle fields.
3. **Relative, not absolute, vulnerability.** Z-scores are computed
   *within this neighborhood's 23 block groups*, not against a citywide or
   national reference population (which would require ingesting every
   Maricopa County block group — out of scope for a single-neighborhood
   tool). HVI here ranks Edison-Eastlake block groups against each other,
   not against the region. Any UI or report copy referencing HVI must
   describe it as relative vulnerability within the neighborhood.

Validated against real data: HVI ranges from −0.86 to +1.35 across the 23
block groups, and correctly surfaces the block group with the highest raw
SVI (0.98) as its highest-HVI block group.

## Sections (filled in as later phases land)

- **Shade raytracing (C2)** and **the albedo model (C3)** (Phase 5) — the
  design-day shadow sweep and shade-hours-to-pedestrian-surfaces metric,
  and the surface-energy-balance albedo model with its Wolfram unit check
  (or the fallback noted in `docs/adr/0002-*.md` if Wolfram access isn't
  available yet). C1 (the canopy cooling kernel) is documented above.
- **The optimizer** (Phase 6) — why this is submodular maximization under a
  knapsack constraint, the three solvers, the measured greedy/exact ratio,
  the baseline comparison and its result.
- **Uncertainty** — how confidence bands are computed and propagated end to
  end, and where they are (and are not) shown in the UI.

See also `docs/LIMITATIONS.md` (Phase 14) for what the product does not
claim.
