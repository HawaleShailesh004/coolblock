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

## Sections (filled in as later phases land)

- **Plantable space** (Phase 4) — rule layer vs. ML layer, the fusion rule,
  the manual spot-check error rate.
- **Cooling impact** (Phase 5) — the cooling kernel, its calibration on
  local LST-vs-canopy data, the shade raytrace method, the albedo model and
  its Wolfram unit check (or the fallback noted in `docs/adr/0002-*.md` if
  Wolfram access isn't available yet).
- **Equity weighting** (Phase 5) — the HVI composite, its default weights,
  the sensitivity analysis.
- **The optimizer** (Phase 6) — why this is submodular maximization under a
  knapsack constraint, the three solvers, the measured greedy/exact ratio,
  the baseline comparison and its result.
- **Uncertainty** — how confidence bands are computed and propagated end to
  end, and where they are (and are not) shown in the UI.

See also `docs/LIMITATIONS.md` (Phase 14) for what the product does not
claim.
