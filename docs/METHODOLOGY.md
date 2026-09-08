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

### C2 — shade raytracing

`engine/impact/shade.py` answers the plan's "visual centrepiece" question
per candidate: how many hours of the design day does its shadow actually
reach real pedestrian space?

The **design day** is the real hottest day on record in the ingested
Open-Meteo series (D13, 2021-2025 summers) — **2025-07-09, 46.9°C** — not
an assumed or literature date. For each hour 09:00-18:00 that day, real
solar geometry (`pvlib.solarposition`, at the neighborhood centroid) gives
the sun's azimuth and elevation; midday elevation on that date peaks at
~77°, consistent with Phoenix's near-tropical July sun angle. Each
candidate's assumed canopy or structure height/width casts a rectangular
shadow whose length (`height / tan(elevation)`, capped at 60m) and
direction (opposite the sun's azimuth) follow directly from that geometry.
The shadow is intersected against real pedestrian-surface vector data:
OSM footways/steps/pedestrian ways, bus stops (buffered), playgrounds, and
school grounds (buffered, standing in for "school routes" — see
simplification 4 below).

Measured on the real candidate set (1,472 candidates): street trees —
sited near roads by construction (`engine/surface/candidates.py`) —
deliver a median of **7 of 10** design-day hours of shade; park-lot tree
clusters, sited in larger interior lots away from footways, deliver a
median of **0**; shade structures (sited near bus stops) deliver a median
of **1.5**. 896 of 1,472 candidates (61%) deliver shade for at least one
hour. This is a real, disclosed geographic finding, not a modeling
artifact: candidates.py's own siting logic determines proximity to
pedestrian infrastructure, and C2 is just measuring the consequence of
where Phase 4 already put things.

**Disclosed simplifications** (see the module docstring for the full
reasoning behind each):

1. **No full height-field/DEM occlusion.** This computes each candidate's
   own shadow reaching nearby pedestrian surfaces directly from solar
   geometry, without checking whether an intervening building would
   already block or shade that path first. The plan's literal
   "GPU-style horizon-angle sweeping on the height raster" (DEM + building
   heights + existing + proposed canopy) is a natural upgrade — the
   ingested DEM (D12) and building heights (`engine/surface/heights.py`)
   are both already available — but was not built this phase.
2. **One representative crown/structure per candidate, not per planted
   tree**, matching C1's same simplification.
3. **Assumed, disclosed dimensions**: a mature street tree at 8m tall,
   8m crown width (matching the 4m crown-radius proxy already used
   elsewhere); a shade structure at 3m tall, 3m wide (typical bus-shelter
   canopy scale). No OSM source carries height/width tags for
   not-yet-built candidates.
4. **No "school route" network exists in this bbox's OSM extract** —
   school *grounds* (buffered) stand in for the plan's "school walking
   routes," which is narrower than what the plan describes.
5. **Shadow length is capped at 60m** — near sunrise/sunset a physically
   correct shadow can stretch hundreds of metres, well past where modeling
   it as a constant-width rectangle remains a meaningful approximation of
   a real tree's dappled, foreshortened shadow.

Unlike C1, `shade_structure` candidates *are* scored by C2 (with their own
height/width) — the split is deliberate: C1 models ambient,
evapotranspiration/albedo-driven canopy cooling, which a physical
structure does not provide, while C2 models direct shading, which both
trees and structures provide by blocking the sun. `docs/adr/0007-*.md`
disclosed this split when it excluded shade structures from C1; this is
where their cooling benefit is actually captured.

### C3 — albedo interventions

`engine/impact/albedo.py` scores two new intervention types generated
this phase (`engine/surface/impervious_candidates.py`) that Phase 4
deliberately deferred (`docs/adr/0005-*.md`): **cool roof** (over every
OSM building footprint, 2,842 candidates) and **cool/reflective pavement**
(over every OSM off-street parking lot, 57 candidates) — the two
intervention types that target *impervious* surfaces the plantable-space
rule layer explicitly excludes.

The model is a first-order surface energy-balance perturbation —
ΔT = Δα·S_down / (h_conv + 4εσT³) — not a full radiative-transfer
simulation, cross-checked by hand for unit consistency since Wolfram
access isn't available this session (`docs/adr/0002-*.md`'s documented
fallback): see the module docstring for the term-by-term check. Every
input is real or a disclosed literature constant:

- **S_down** (peak solar-noon irradiance): from NASA POWER's (D14) real
  daily total for the design day, converted via the standard
  sinusoidal-insolation approximation using real `pvlib`-computed
  sunrise/sunset — **≈872 W/m²** for 2025-07-09.
- **h_conv**: McAdams' empirical convection correlation driven by
  Open-Meteo's (D13) real design-day wind speed — **≈13.7 W/(m²·K)** at
  2.1 m/s average wind.
- **Current albedo**: sampled per-candidate from the real Sentinel-2
  albedo proxy, not assumed uniform.
- **Target albedo**: literature planning values (0.65 cool roof, 0.40
  cool pavement) — disclosed as planning estimates for not-yet-installed
  retrofit products.

**A real bug was caught and fixed while building this**: the existing
Phase 3 albedo proxy (`engine/thermal/predictors.py`) was an unweighted
mean of *raw* Sentinel-2 L2A digital numbers (~1,450-8,670), not scaled to
0-1 reflectance. This never affected the Phase 3 downscaling regression
(a gradient-boosted model splits on relative feature values regardless of
scale) but silently broke C3's physical use of the same value — every
candidate's current albedo clipped to the model's ceiling and every ΔT
came back zero. Fixed by scaling Sentinel-2 bands by the standard ESA
1/10000 factor before computing `albedo_proxy` (NDVI/NDBI are ratios, so
they were never affected). Re-ran the Phase 3 downscaling and validation
tests after the fix — unchanged, as expected. See
`engine/tests/test_albedo.py::test_albedo_proxy_is_real_reflectance_not_raw_dn`
for the regression guard.

Measured on real data (post-fix): cool roofs average **ΔT ≈ 12.9°C** at
their own footprint; cool pavement averages **ΔT ≈ 3.3°C**. These numbers
are large next to C1's tree ΔT_peak (0.1-7.9°C) because **they measure a
different quantity** — C3's ΔT is the retrofit surface's own undiluted
temperature change at its own footprint, not an area-averaged ambient
effect the way C1's Gaussian kernel already is. The magnitude matches
published cool-roof literature for *roof surface* temperature reduction
(commonly 11-22°C, up to ~28°C) — consistent, not inflated — but this
distinction must travel with any objective (D4's EWCB) that combines C1
and C3 contributions; they are not directly interchangeable "degrees of
cooling" without accounting for it.

**Disclosed limitations:**

1. **No roof-slope/flatness data.** Cool-roof coatings are only
   cost-effective on flat/low-slope roofs in practice, but OSM carries no
   roof-shape tag for this bbox — every building becomes a candidate
   regardless of actual roof geometry, over-inclusive of what a city could
   realistically act on.
2. **Depaving-to-bioswale is still not generated** — no ingested source
   distinguishes excess/removable pavement from functionally necessary
   pavement (a working parking space, an access lane); guessing that
   distinction would be worse than omitting the candidate type.
3. **10m-pixel albedo sampling.** A small parking lot or building
   footprint's centroid pixel can blend in adjacent, differently-surfaced
   ground via bilinear resampling — the "before" albedo for small
   candidates is an approximation, not a footprint-exact measurement.

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

### D3 — exposure weighting

`engine/equity/exposure.py` computes a per-building exposure multiplier —
1.0 baseline, raised for real OSM-derived proximity (within 400m, a
5-minute-walk transit-catchment radius) to bus stops
(**×1.3**, transit riders wait outdoors unshaded) and schools (**×1.2**,
children walk to and from them). Measured on real data: 4 distinct
multiplier values occur across D1's residential buildings (1.0, 1.2, 1.3,
1.56 for near-both), with the large majority of buildings (1,863 of 2,401)
near a bus stop only — a real reflection of this neighborhood's dense bus
network, not a modeling artifact.

**Disclosed, exactly matching the plan's own framing** ("exposure
multipliers derived from OSM features," not demographic microdata this
project doesn't have):

1. **No outdoor-worker exposure** — no ingested source identifies outdoor
   workplaces in this bbox; omitted rather than faked.
2. **The multipliers are planning judgments**, not fitted from
   ridership/enrollment data — no such data is ingested for this
   neighborhood.
3. **Proximity is a population-wide proxy**, not a survey of who actually
   rides transit or walks children to school from each specific building.

### D4 — Equity-Weighted Cooling Benefit (EWCB)

`engine/impact/ewcb.py` is the objective Phase 6's optimizer will
maximize — the module that actually combines every other Phase 5 piece:

    EWCB(S) = Σ_p  ΔT_S(x_p) · HVI(p) · exposure(p) · hours(p)

C1's canopy ΔT and C3's cool-roof ΔT are each evaluated at real
population points (D1's residential buildings, each carrying its block
group's HVI from D2 and its own D3 exposure multiplier), summed and
scaled by a constant 10-hour `hours(p)` (matching C2's design-day
daylight window — the disclosed simplification that C1/C3's steady-state
ΔT is treated as present for the full daylight window, since duration is
what C2 already measures on its own).

**Population attribution is mechanism-specific, and disclosed per type:**

- **Canopy candidates** (`street_tree`, `park_lot_tree_cluster`): C1's
  actual Gaussian ΔT(d) is evaluated at the true distance to every nearby
  population point within its 3σ (90m) influence radius — the same
  spatial footprint C1 itself models, not a flat per-candidate estimate.
- **`cool_roof`**: attributed to the same building's own occupants, only
  when that building is one of D1's *residential* buildings (spatially
  joined back to its own footprint). Non-residential cool-roof candidates
  (schools, offices — D1 only redistributes population onto residential
  buildings) score `ewcb_person_degree_hours = 0`: no occupancy data
  exists for them, so nothing is invented. Measured: 2,321 of 2,842
  cool-roof candidates (82%) matched a residential building and scored
  nonzero, consistent with D1's ~2,401 identified residential buildings.
- **`cool_pavement`** and **`shade_structure`**: score exactly 0 — no
  population-attribution model exists for either (a parking lot or a bus
  shelter has no "occupants," and nothing links passers-by to a home
  address). Their real benefit (ΔT / shade-hours) is still reported
  directly by C3/C2 — EWCB's silence on them is a scope gap, not a claim
  that they help nobody.

**C2's shade-hours-delivered is deliberately not folded into this sum.**
It is already a duration, a different kind of quantity from a ΔT field to
be hours-weighted, and merging the two would require an unjustified
conversion factor between "hours shaded" and "degrees cooled." Both
numbers must travel together in any report or UI — EWCB does not
supersede C2's metric.

**EWCB can be negative, and that is intended, not a bug.** HVI is a
z-score centered at 0 — roughly half of this neighborhood's block groups
score below the neighborhood average and carry negative HVI. A candidate
sited there produces a negative `ewcb_person_degree_hours` despite a
strictly positive ΔT: the formula is an equity *weighting* of cooling
against this neighborhood's own vulnerability distribution, not a pure
magnitude. Measured on real candidates: canopy candidates range from
about −2,948 to +9,027 person-degree-hours; cool-roof candidates range
from about −20,993 to +10,945. Any UI or report copy must describe this
number as cooling weighted by *relative* vulnerability, not as "degrees
of cooling delivered" on its own.

**Confidence bounds** (`ewcb_low`/`ewcb_high`), satisfying the Phase 5 DoD
requirement that "every candidate carries... an EWCB with confidence
[bounds]": for canopy candidates, C1's own `beta_ci95` is propagated
linearly through the EWCB calculation (`ewcb_person_degree_hours` is
linear in β), giving an exact confidence band from C1's real regression
uncertainty — not a separately fitted or invented uncertainty model.
`cool_roof`, `cool_pavement`, and `shade_structure` have no fitted
uncertainty source this phase (C3's energy-balance model reports a point
estimate only), so their bounds equal the point estimate exactly — a
disclosed gap, not a fabricated band.

## The optimizer (Phase 6)

### Why this is genuinely hard

Benefits **overlap** — two trees 8m apart do not deliver double the
cooling to a resident standing between them. D4's EWCB
(`engine/impact/ewcb.py`) sums each candidate's benefit independently,
which is correct for reporting one candidate's own effect but wrong as an
objective to maximize over a *set*: it would reduce to "sort by score,
take the top ones under budget," which is exactly what this problem is
not (COOLBLOCK-BUILD-PLAN.md §6.5 E1).

### E1 — the coverage-function objective

`engine/optimize/objective.py` redefines EWCB as a **weighted coverage
function** for optimization purposes:

    F(S) = Σ_p  weight(p) · max_{i ∈ S} ΔT_i(x_p)

taking the *max* ΔT any selected candidate delivers to a population
point, not the sum. Weighted coverage functions are a canonical monotone
submodular set function — this is the actual mathematical structure
behind the plan's submodularity claim, not an assertion. Verified
directly: `engine/tests/test_objective.py` confirms two overlapping
candidates covering the same point combine to `max(ΔT₁, ΔT₂)`, not
`ΔT₁ + ΔT₂`, and that a candidate's marginal gain strictly shrinks once
another candidate already covers the same ground (submodularity's
diminishing-returns property, checked directly).

**A real conflict with D4 had to be resolved: HVI can be negative.** D2's
HVI is a signed z-score, and D4 deliberately keeps that sign for
transparent reporting. A coverage function with a negative-weighted point
is not monotone, which breaks both CELF's guarantee and the DoD's own
"benefit monotone in budget" property test. `OPTIMIZER_HVI_FLOOR = 0.0`
clips HVI at zero for the optimizer's internal objective only — a
below-average-vulnerability point contributes zero weight, not a penalty.
D4's own reported numbers are untouched. See `docs/adr/0012-*.md`.

`cool_pavement` and `shade_structure` candidates inherit D4's disclosed
zero-attribution scope exactly — the optimizer will never select either
for equity credit under this objective, a real, disclosed consequence of
D4's scope rather than a new gap.

### E2 — CELF lazy greedy

`engine/optimize/celf.py` implements Cost-Effective Lazy Forward
selection (Leskovec et al. 2007): a max-heap keyed by each candidate's
last-known marginal-gain-per-dollar, lazily re-evaluated (a candidate's
true marginal gain can only fall as the selection grows, never rise, so a
stale heap entry only needs recomputing when it reaches the top) — close
to `O(n)` total evaluations rather than `O(n·k)`, which is what keeps this
solver fast enough to run interactively.

**A correction to the plan's stated approximation ratio.** The plan cites
"(1 − 1/e) ≈ 0.63" for CELF — exact for *cardinality*-constrained
submodular maximization, not the **budget** (knapsack) constraint this
problem actually has, where the correctly-citable worst-case guarantee is
(1 − 1/√e) ≈ 0.393 (Khuller, Moss, Naor 1999), achieved by taking the
better of cost-effective greedy and the single best affordable candidate
alone (both implemented; `solve()` returns whichever wins). Restating the
plan's figure without this caveat would have been a real, avoidable
inaccuracy — corrected and recorded in `docs/adr/0012-*.md`.

**What actually matters is measured, not assumed.** The Phase 6 DoD's own
bar — "greedy ≥ 0.63 × exact on every small instance" — is checked as an
*empirical* property test against a real brute-force optimum on small
synthetic instances
(`engine/tests/test_celf.py::test_greedy_reaches_at_least_063_of_exact_on_small_instances`),
and it passes. Benefit-monotone-in-budget is checked the same way.

**Measured on the real, full candidate universe** (4,371 candidates,
2,401 population points): `build_coverage_objective` takes under 1
second; `solve()` takes 0.05-0.2 seconds across budgets from $5,000 to $5
million — well inside the DoD's "< 8s for the full neighborhood" bar.

### E2 (second solver) — exact MILP solve, and the measured ratio

`engine/optimize/exact.py` solves the coverage objective exactly with
HiGHS (`highspy`), on a **reduced instance** (`MAX_EXACT_CANDIDATES = 300`,
matching the plan's own "~300 candidates" spec) selected by
`reduce_instance()` — the candidates with the highest standalone marginal
gain, so the reduced instance still contains what greedy itself would
consider first, not an arbitrary subset that could favor one solver over
the other.

**The MILP formulation is exact, not a linearized approximation of max-
coverage.** For each (population point, candidate) influence pair, a
binary "achiever" variable ties to the candidate's selection variable
(`z[p,i] <= x_i`) with at most one achiever per point
(`Σ_i z[p,i] <= 1`); because every objective coefficient is
non-negative, the solver is *incentivized* to make the achiever the
single highest-ΔT active candidate at each point — exactly reproducing
`CoverageObjective.value()` at the optimum, with no big-M relaxation.
Verified directly: `engine/tests/test_exact.py` confirms the MILP's
reported objective matches real brute-force enumeration on small
instances, and matches an independent recomputation via
`CoverageObjective.value()` on the exact solver's own selected set.

**Measured on the real candidate universe, at the plan's own reduced-
instance size (300 candidates):**

| Budget | Greedy | Exact (proven optimal) | Ratio | Solve time |
|---|---|---|---|---|
| $20,000 | 57,064 | 57,317 | **99.6%** | 1.8s |
| $100,000 | 223,844 | 224,101 | **99.9%** | 1.1s |

CELF greedy reaches 99.6-99.9% of the *proven* exact optimum on this
neighborhood's real data — far above both the plan's cited 0.63 figure
and the knapsack-correct 0.393 worst-case bound (`docs/adr/0012-*.md`).
Worst-case guarantees describe adversarial instances; this real
instance's overlap structure is evidently far more favorable to greedy
than the worst case, which is itself worth stating plainly rather than
implying the worst-case bound is what was measured.

**This measurement was originally a one-off notebook run; it is now real,
reusable code** (§7.2.3's independent-solver verification, substituted
for Wolfram's `NMaximize` cross-check per `docs/adr/0002-*.md`/`0021-*.md`):
`engine.verify.optimizer_crosscheck.cross_check_optimizer()` reproduces
this exact comparison on demand, and
`engine/tests/test_optimizer_crosscheck.py`'s real-candidate-universe test
reruns it automatically as part of the default test suite — a regression
in either solver or in `CoverageObjective` itself would fail a real test,
not silently drift from what this table says.

### E2 (third solver) — local search

`engine/optimize/local_search.py` runs a bounded swap-based improvement
pass on CELF's output: it repeatedly tries replacing the current
selection's *least* valuable member (its exact marginal contribution,
recomputed via `CoverageObjective.value()`, not its standalone gain) with
the best-fitting candidate from a pool of the top `SWAP_POOL_SIZE`
unselected candidates by standalone gain, keeping a swap only if it
provably raises the objective.

**Disclosed scope**: this is a bounded local search, not an exhaustive
2-opt — checking every selected candidate against every unselected one
for the full ~4,300-candidate universe would be millions of value
recomputations. Restricting the swap-in pool to the highest-standalone-
gain candidates is the honest tradeoff for running in real time, stated
here rather than silently narrowed. Verified with a hand-built instance
containing a deliberately obvious improving swap
(`engine/tests/test_local_search.py`), confirming the search actually
finds it.

**Measured on real data**: on the same 100-candidate reduced instance,
$20,000 budget used for the exact-solve comparison, local search applied
1 swap in 2 iterations (10ms), raising the selection's value from 56,619
(greedy alone) to 56,669 — closing part of the gap to HiGHS's proven
exact optimum (56,821), from 99.64% to 99.73%. The improvement is real
but modest here precisely *because* greedy already performs so well on
this neighborhood's real data (§E2's earlier measurement) — there is
simply little gap left to close, which is itself informative: local
search's value depends on how far from optimal the starting solution
already is, and CoolBlock's greedy starting point is usually already very
close.

### A real, disclosed finding: the unconstrained solve is cool-roof-heavy

Testing the constraints module (below) against the unconstrained solve
surfaced something worth stating plainly rather than only in a code
comment: **at a $50,000 budget, CoolBlock's unconstrained solve selects
47 candidates, and all 47 are `cool_roof`** — zero trees. Investigated,
not assumed: this is a real, correct consequence of the objective's
construction, not a bug.

C1's canopy ΔT (0.1-7.9°C, `docs/METHODOLOGY.md`'s C1 section) is already
an *area-diluted ambient* effect — a Gaussian kernel spreading one tree's
cooling over a ~2,827m² neighborhood. C3's cool-roof ΔT (mean ≈12.9°C,
C3's section above) is the retrofit's own *undiluted surface* temperature
change at its own footprint — a fundamentally different physical
quantity, as already disclosed when C3 was built (`docs/adr/0009-*.md`,
`docs/adr/0012-*.md`). Combining both directly into one coverage
objective, without a further normalization this project has no data to
justify, means cool-roof's much larger raw ΔT number dominates
cost-effectiveness by a wide margin at every budget tested — the
optimizer is doing exactly what the objective asks it to, but the
objective is comparing two quantities that are not on equal footing.

**Not fixed by inventing a conversion factor between "surface ΔT" and
"ambient ΔT"** — nothing in this project's ingested data supports one, and
guessing would be worse than disclosing the limitation directly, per the
project's own honesty-rail posture. Two honest paths forward for a later
phase: (a) recalibrate C3's ΔT onto an ambient-equivalent basis using a
real convective mixing model (would need boundary-layer data this project
doesn't have), or (b) treat "surface hardening interventions" and "canopy
interventions" as two separate objectives/budgets in the UI rather than
one combined ranking. Neither is implemented this phase; this section
exists so nobody mistakes an all-cool-roof recommendation for a
demonstration bug rather than a real, disclosed property of the current
model.

### E5 — the baselines: "the proof the product works"

`engine/optimize/baselines.py` solves the same real candidate universe
and budget with four naive/status-quo strategies, then scores each one's
resulting selection with the exact same `CoverageObjective` (D4's EWCB)
CoolBlock itself maximizes — an apples-to-apples comparison by
construction, not a hand-picked metric:

- **Spread evenly** — an equal dollar allocation per real Census block
  group (D7b), spent on that zone's own candidates until exhausted.
- **Worst-first** — candidates ranked by real downscaled 10m LST at their
  own location, hottest first.
- **Squeaky wheel** — randomized (seeded, reproducible), weighted by each
  candidate's block group's real median household income (D7) — the
  documented higher-income bias the name refers to.
- **TES-score-only** — ranked by each candidate's block group's real Tree
  Equity Score (D10, third-party mirror, `docs/adr/`-disclosed provenance
  already at ingestion), lowest score (worst tree equity) first.

**Measured on real data, at real budgets:**

| Strategy | $20,000 budget | $100,000 budget |
|---|---|---|
| Squeaky wheel | 0.1 | 0.1 |
| Spread evenly | 992 | 1,417 |
| Worst-first | 2,650 | 2,650 |
| TES-score-only | 12,328 | 15,992 |
| **CoolBlock** | **57,064** | **223,852** |

CoolBlock beats TES-score-only — the best existing tool — by **4.6× at
$20k and 14.0× at $100k**, and beats every other baseline by a much wider
margin. This clears the plan's own bar ("if CoolBlock does not beat
TES-score-only by a clear margin, we have not built anything") decisively.

**A genuinely informative, not just favorable, finding**: worst-first's
value is *identical* at both budgets (2,650) — it doesn't improve with 5×
more money. The reason is real, not an artifact: ranking purely by local
heat has no way to know that `cool_pavement` and `shade_structure`
candidates carry zero EWCB attribution in this phase's scope
(`docs/adr/0010-*.md`) — and impervious surfaces (parking lots, existing
pavement) are exactly the *hottest* locations, so "plant where it's
hottest" spends most of its budget on candidate types that are
structurally incapable of scoring under this objective. This is worth
stating in the product's own comparison screen as a real insight about
why naive heat-ranking fails, not smoothed over.

### E3 — constraints: "all real, all user-facing"

`engine/optimize/constraints.py` implements five of the plan's real
constraints against this neighborhood's actual data: an annual
maintenance-cost cap ($75/yr per planted tree, the plan's own cost-table
figure; $0/yr — not modeled, disclosed as such — for cool-roof/
cool-pavement/shade-structure), a minimum spend per real Census block
group (an equity floor), a maximum sites per block group (dispersion), a
public-land-only mode (the real `ownership` column already computed by
Phase 4's candidate generation), and mandatory inclusion/exclusion of
specific candidates. **Not implemented, disclosed rather than faked**:
species diversity (no per-species/genus data exists for any candidate —
they are generic `street_tree` records, not species-level plantings) and
a water-budget cap (no irrigation/evapotranspiration demand estimate is
ingested anywhere in this project).

Side constraints break CELF's lazy-heap invariant (a cached marginal gain
can't be trusted stale once a per-zone cap could newly bind), so this is
a non-lazy constrained greedy — still ranked by marginal gain per dollar
(cost-effectiveness), matching E2's CELF. **A real bug was caught by
cross-checking this solver's unconstrained output against CELF's on
identical inputs**: an early version ranked by raw marginal gain instead
of gain-per-dollar, understating the unconstrained value by 38% (81,687 vs
CELF's 134,977 at $50,000). Fixed to match CELF's ranking exactly —
verified the unconstrained mode now reproduces CELF's value bit-for-bit.

**Measured on real data, $50,000 budget:**

| Constraint | Value | vs. unconstrained |
|---|---|---|
| None (reference) | 134,978 | — |
| Public-land-only | 62,573 | −54% |
| Max 3 sites/block group | 19,627 | −85% |
| Min $500 spend/block group | 97,969 | −27% |
| Maintenance cap $2,000/yr | 134,978 | 0% (never binds — see below) |

Every real constraint costs real EWCB, as expected — equity floors and
dispersion requirements are trading some efficiency for a real planning
goal, exactly the tradeoff a city would actually face. The maintenance
cap not binding is not an error: at $50,000 unconstrained, all 47 selected
candidates are `cool_roof` (see below), which carries $0/yr assumed
maintenance, so a $2,000/yr cap has nothing to constrain.

### A real, disclosed finding: the unconstrained solve is cool-roof-heavy

Testing the constraints module against the unconstrained solve surfaced
something worth stating plainly rather than only in a code comment: **at
a $50,000 budget, CoolBlock's unconstrained solve selects 47 candidates,
and all 47 are `cool_roof`** — zero trees. Investigated, not assumed:
this is a real, correct consequence of the objective's construction, not
a bug.

C1's canopy ΔT (0.1-7.9°C) is already an *area-diluted ambient* effect —
a Gaussian kernel spreading one tree's cooling over a ~2,827m²
neighborhood. C3's cool-roof ΔT (mean ≈12.9°C) is the retrofit's own
*undiluted surface* temperature change at its own footprint — a
fundamentally different physical quantity, as already disclosed when C3
was built (`docs/adr/0009-*.md`, `docs/adr/0012-*.md`). Combining both
directly into one coverage objective, without a further normalization
this project has no data to justify, means cool-roof's much larger raw ΔT
dominates cost-effectiveness by a wide margin at every budget tested — the
optimizer is doing exactly what the objective asks it to, but the
objective is comparing two quantities that are not on equal footing.

**Not fixed by inventing a conversion factor between "surface ΔT" and
"ambient ΔT"** — nothing in this project's ingested data supports one, and
guessing would be worse than disclosing the limitation directly. Two
honest paths forward for a later phase: (a) recalibrate C3's ΔT onto an
ambient-equivalent basis using a real convective mixing model (would need
boundary-layer data this project doesn't have), or (b) treat
"surface-hardening interventions" and "canopy interventions" as two
separate objectives/budgets in the UI rather than one combined ranking.
Neither is implemented this phase; the more "balanced" portfolios the E3
constraints table above shows (public-land-only, max-sites-per-zone) are
a *side effect* of removing high-cost-effectiveness cool-roof candidates
from eligibility, not a fix to the underlying ΔT-comparability issue —
`docs/adr/0014-*.md` records this distinction explicitly so it is never
mistaken for one.

### E4 — the efficient frontier

`engine/optimize/frontier.py` re-solves the real candidate universe with
E2's CELF greedy across a $5,000-$500,000 sweep (51 points, $10k steps,
the plan's own stated range) — "the single most persuasive artefact for
the business-strategy judge... diminishing returns, marginal cost of
outcome." Every budget point is solved **fresh**, not incrementally
extended from the previous point: `solve()` picks the better of
cost-effective greedy and the single best affordable candidate
(`engine.optimize.celf`), and which strategy wins can differ between
budgets, so a larger budget's selection is not guaranteed to be a
superset of a smaller one's — re-solving is the honest choice over
assuming nesting the solver itself doesn't guarantee.

**A real off-by-one was caught building this**: computing the sweep's
step count as `round((500,000-5,000)/10,000)+1` silently overshot to
$505,000 (495,000/10,000 = 49.5 is not an integer, and Python's
round-half-to-even rounds it up) — caught by a test asserting the sweep's
last point equals exactly $500,000, not "close to." Fixed by generating
steps up to (not including) the max and appending the exact max
explicitly (`docs/adr/0015-*.md`).

**Measured on real data** — a clean diminishing-returns curve, exactly
the shape the plan's framing describes:

| Budget | EWCB | Candidates | Marginal EWCB / $1,000 |
|---|---|---|---|
| $5,000 | 14,869 | 6 | 2,973.8 |
| $105,000 | 230,505 | 91 | 1,316.4 |
| $205,000 | 322,875 | 128 | 495.0 |
| $305,000 | 342,687 | 161 | 66.5 |
| $405,000 | 348,498 | 252 | 47.5 |
| $500,000 | 351,634 | 275 | 37.2 |

Marginal value per $1,000 falls by nearly two orders of magnitude across
the sweep (2,974 → 37) — the neighborhood's real, finite pool of
high-cost-effectiveness candidates (largely `cool_roof`, per the finding
above) gets exhausted well before $500k, after which additional spend
buys markedly less. The full 51-point sweep solves in ~2.5 seconds total.

### Phase 6 status: complete except Wolfram's independent cross-check

E1 (submodular coverage objective), E2 (all three solvers -- CELF greedy,
exact MILP, local search), E3 (five real constraints), E4 (the efficient
frontier), and E5 (the five baselines) are all built, tested against real
data, and documented above. The checkpoint notebook
(`notebooks/03-optimizer-benchmarks.ipynb`) is written and executed with
real outputs. The map's context panel shows CoolBlock's actual ranked
plan at a representative budget, verified with a real browser
click-through (not just a code read).

**Deferred**: Wolfram `NMaximize` independent cross-check (§7.2.3) --
Wolfram access isn't available this session, deferred the same way as
every other Wolfram-dependent piece (`docs/adr/0002-*.md`). HiGHS's exact
MILP solve (E2) already provides one independent verification of greedy's
quality; Wolfram would be a second, in a different mathematical system,
per the plan's own reasoning for wanting it ("we did not want to trust
our own implementation") -- valuable, but not load-bearing for the DoD's
own greedy-vs-exact ratio requirement, which HiGHS already satisfies.

## Sections (filled in as later phases land)

- **Uncertainty** — how confidence bands are computed and propagated end to
  end, and where they are (and are not) shown in the UI.

See also `docs/LIMITATIONS.md` (Phase 14) for what the product does not
claim.
