"""C1 -- the canopy cooling kernel (COOLBLOCK-BUILD-PLAN.md §6.3 C1).

    ΔT_peak = β · f_canopy_increment · g(impervious_fraction) · h(LST_anomaly)
    ΔT(d)   = ΔT_peak · exp(−d² / 2σ²)          σ ≈ 25-40 m for a mature street tree

β is **calibrated on this neighborhood's own data**, not imported from the
literature (the plan is explicit that the literature values --
npj Urban Sustainability's up to 1.5°C, Nature Communications' "roughly
halves UHI" -- anchor the *magnitude*, not substitute for a local fit).
`calibrate_beta()` runs an OLS regression of the Phase 3 downscaled 10m LST
field (`engine.thermal.downscale.run_downscaling`) against local existing
canopy fraction, controlling for % impervious (D11) so the canopy
coefficient isn't just re-capturing "impervious areas are also
tree-sparse." Canopy fraction reuses the same buffered-OSM-tree-point proxy
`engine.surface.rule_layer` uses for existing canopy (disclosed there:
no nDSM exists to measure real canopy height/extent), smoothed into a
continuous per-pixel fraction over the same radius the kernel itself
projects influence across.

Disclosed simplifications, beyond the canopy-proxy limitation above:

1. **No wind/aspect term.** The plan's w(wind/aspect) factor is omitted
   (held at 1.0) -- no urban-canyon wind-flow model exists in this
   project's data or scope, and Open-Meteo's (D13) neighborhood-average
   wind speed/direction has no way to resolve street-canyon channelling at
   individual-candidate scale. Faking a directional multiplier from a
   single averaged wind vector would be worse than omitting it.
2. **One Gaussian patch per candidate, not per planted tree.** A
   `park_lot_tree_cluster` candidate with capacity > 1 scales
   `f_canopy_increment` (more trees -> more new canopy area) rather than
   placing `capacity` separate kernel centers across the polygon. This
   keeps a cluster of N trees from "over-cooling" a shared footprint, and
   matches the plan's own framing that overlapping benefits are not
   additive (§6.5 E1) -- but it means candidates.py's polygon shape does
   not otherwise affect where the ΔT patch is centered (its centroid).
3. **`shade_structure` candidates get no canopy ΔT here.** They plant no
   canopy -- a `SINGLE_TREE_CROWN_AREA_M2`-based increment would be
   physically meaningless for a physical shade structure, not just
   imprecise. Their cooling benefit is a direct shading effect, captured
   by C2 (shade-hours delivered to pedestrian space), not this ambient
   canopy-regression kernel. `compute_delta_t_peak` sets their
   `delta_t_peak_degc` to 0.0 rather than silently running the tree
   formula on a non-tree intervention.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import geopandas as gpd
import numpy as np
import rasterio.features
from scipy import ndimage

from engine.ingest import d04_osm
from engine.ingest.grid import CanonicalGrid, get_canonical_grid
from engine.ingest.manifest import version_dir
from engine.surface.rule_layer import TREE_CANOPY_RADIUS_M
from engine.thermal.downscale import run_downscaling
from engine.thermal.predictors import load_impervious_predictor

FloatArray = np.ndarray[Any, np.dtype[np.float64]]

# Midpoint of the plan's literature-cited 25-40m mature-street-tree cooling
# radius -- a single project-wide default, not fit per candidate.
SIGMA_M = 30.0

# Same mature-crown-radius assumption already used for the *existing*
# canopy proxy (engine.surface.rule_layer.TREE_CANOPY_RADIUS_M) -- a newly
# planted tree is modeled as eventually reaching the same crown, since this
# is a siting tool, not a growth-timeline simulator.
SINGLE_TREE_CROWN_AREA_M2 = float(np.pi * TREE_CANOPY_RADIUS_M**2)

# The reference area a kernel's canopy increment is expressed as a fraction
# of -- the circle a sigma-radius Gaussian actually projects influence
# across, so f_canopy_increment means the same thing g() and beta's
# regression were fit against.
KERNEL_INFLUENCE_AREA_M2 = float(np.pi * SIGMA_M**2)

# g(impervious_fraction): trees measurably cool paved/built surfaces more
# than they cool already-vegetated ground (shading replaces solar heating
# of a hot impervious surface, vs. incrementally shading grass that was
# already evapotranspiring). A simple bounded linear form -- not a fitted
# function, disclosed as a planning-judgment shape, floored so a candidate
# over zero impervious ground still cools some.
G_FLOOR = 0.5
G_CEILING = 1.0

# h(LST_anomaly): candidates already sitting in a locally hotter spot get a
# modest additional boost, capped so it never dominates beta*f*g. Zero
# boost at or below the neighborhood mean LST -- an "anomaly" bonus, not a
# baseline-independent scaling.
H_ANOMALY_ZSCORE_CAP = 3.0
H_ANOMALY_WEIGHT = 0.15

# Patch rendering window half-width, in multiples of sigma -- beyond 3 sigma
# a Gaussian has decayed to <2% of peak, negligible for a "sparse" patch.
PATCH_RADIUS_SIGMA_MULTIPLES = 3.0

# Only these intervention types plant canopy; C1's ambient cooling kernel
# applies to them alone (see module docstring, disclosed simplification 3).
CANOPY_INTERVENTION_TYPES = {"street_tree", "park_lot_tree_cluster"}


@dataclass(frozen=True)
class CoolingKernelCalibration:
    beta_degc_per_canopy_fraction: float  # negative in the raw fit (more canopy -> lower LST); reported as a magnitude
    beta_ci95: tuple[float, float]
    intercept_degc: float
    impervious_coef_degc: float
    r2: float
    n_pixels: int


def _existing_canopy_fraction(grid: CanonicalGrid) -> FloatArray:
    """Continuous local canopy-fraction field on `grid`: the same buffered
    OSM tree-point mask `engine.surface.rule_layer` uses for existing
    canopy, rasterized at `grid`'s resolution and smoothed with a
    SIGMA_M-radius moving average -- so each pixel's value is "how much
    canopy is nearby," matching what a Gaussian-kernel cooling effect
    actually responds to, not just "is this exact pixel canopy."
    """
    trees = gpd.read_parquet(version_dir(d04_osm.SOURCE_ID, d04_osm.VERSION) / "trees.parquet")
    trees = trees.to_crs(epsg=grid.epsg)
    canopy = trees.copy()
    canopy["geometry"] = trees.geometry.buffer(TREE_CANOPY_RADIUS_M)

    mask = rasterio.features.rasterize(
        [(geom, 1) for geom in canopy.geometry if geom is not None and not geom.is_empty],
        out_shape=(grid.height, grid.width),
        transform=grid.transform,
        fill=0,
        dtype="uint8",
    ).astype("float64")

    window_px = max(1, round(SIGMA_M / grid.resolution_m))
    size = 2 * window_px + 1
    smoothed: FloatArray = ndimage.uniform_filter(mask, size=size, mode="constant", cval=0.0)
    return smoothed


def calibrate_beta() -> CoolingKernelCalibration:
    """OLS fit of downscaled 10m LST on local canopy fraction, controlling
    for % impervious. Returns beta as reported -- callers take its
    magnitude, since the raw coefficient is negative (canopy cools)."""
    grid = get_canonical_grid()
    downscaling = run_downscaling()
    lst = downscaling.lst_10m.values.astype("float64")

    canopy_fraction = _existing_canopy_fraction(grid)
    impervious_fraction = load_impervious_predictor(grid).values.astype("float64") / 100.0

    valid = np.isfinite(lst) & np.isfinite(canopy_fraction) & np.isfinite(impervious_fraction)
    y = lst[valid]
    design = np.column_stack([np.ones(valid.sum()), canopy_fraction[valid], impervious_fraction[valid]])

    coef, _, _, _ = np.linalg.lstsq(design, y, rcond=None)
    intercept, beta, impervious_coef = (float(c) for c in coef)

    residuals = y - design @ coef
    n, k = design.shape
    dof = n - k
    sigma2 = float(np.sum(residuals**2) / dof)
    xtx_inv = np.linalg.inv(design.T @ design)
    se_beta = float(np.sqrt(sigma2 * xtx_inv[1, 1]))
    ci95 = (beta - 1.96 * se_beta, beta + 1.96 * se_beta)

    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    return CoolingKernelCalibration(
        beta_degc_per_canopy_fraction=beta,
        beta_ci95=ci95,
        intercept_degc=intercept,
        impervious_coef_degc=impervious_coef,
        r2=r2,
        n_pixels=n,
    )


def _pixel_index(grid: CanonicalGrid, x: float, y: float) -> tuple[int, int]:
    col, row = ~grid.transform * (x, y)
    row_i = int(np.clip(round(row), 0, grid.height - 1))
    col_i = int(np.clip(round(col), 0, grid.width - 1))
    return row_i, col_i


def compute_delta_t_peak(
    candidates: gpd.GeoDataFrame,
    calibration: CoolingKernelCalibration,
) -> gpd.GeoDataFrame:
    """Adds `delta_t_peak_degc` to `candidates`: the modeled peak cooling
    (at the kernel's center) for each candidate's capacity and local
    context."""
    grid = get_canonical_grid()
    lst = run_downscaling().lst_10m.values.astype("float64")
    impervious = load_impervious_predictor(grid).values.astype("float64") / 100.0

    finite_lst = lst[np.isfinite(lst)]
    lst_mean = float(finite_lst.mean())
    lst_std = float(finite_lst.std()) or 1.0

    beta_magnitude = abs(calibration.beta_degc_per_canopy_fraction)

    peaks = np.empty(len(candidates), dtype="float64")
    for i, row in enumerate(candidates.itertuples()):
        if row.intervention_type not in CANOPY_INTERVENTION_TYPES:
            peaks[i] = 0.0
            continue

        centroid = row.geometry.centroid
        r, c = _pixel_index(grid, centroid.x, centroid.y)

        canopy_increment_fraction = min(
            1.0, row.capacity * SINGLE_TREE_CROWN_AREA_M2 / KERNEL_INFLUENCE_AREA_M2
        )

        local_impervious = impervious[r, c]
        local_impervious = 0.0 if not np.isfinite(local_impervious) else local_impervious
        g = G_FLOOR + (G_CEILING - G_FLOOR) * local_impervious

        local_lst = lst[r, c]
        z = 0.0 if not np.isfinite(local_lst) else (local_lst - lst_mean) / lst_std
        h = 1.0 + H_ANOMALY_WEIGHT * float(np.clip(z, 0.0, H_ANOMALY_ZSCORE_CAP))

        peaks[i] = beta_magnitude * canopy_increment_fraction * g * h

    out = candidates.copy()
    out["delta_t_peak_degc"] = peaks
    return out


def gaussian_patch(delta_t_peak_degc: float, sigma_m: float = SIGMA_M) -> tuple[FloatArray, int]:
    """A small, sparse square raster (in grid pixels) of ΔT(d) centered on
    its own middle cell -- `run_cooling_kernel` positions it. Returns the
    patch and its center-pixel offset (half-width) so callers can place it
    on the full grid without materializing a full-grid raster per
    candidate."""
    grid = get_canonical_grid()
    radius_px = max(1, round(PATCH_RADIUS_SIGMA_MULTIPLES * sigma_m / grid.resolution_m))
    size = 2 * radius_px + 1

    yy, xx = np.mgrid[-radius_px : radius_px + 1, -radius_px : radius_px + 1]
    d2_m2 = (yy * grid.resolution_m) ** 2 + (xx * grid.resolution_m) ** 2
    patch: FloatArray = delta_t_peak_degc * np.exp(-d2_m2 / (2 * sigma_m**2))
    assert patch.shape == (size, size)
    return patch, radius_px


def run_cooling_kernel(candidates: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, CoolingKernelCalibration]:
    """C1's full output: candidates with `delta_t_peak_degc`, plus the
    calibration used to compute them (stored alongside so its R^2 and CI
    travel with any downstream report, not just the point estimate)."""
    calibration = calibrate_beta()
    scored = compute_delta_t_peak(candidates, calibration)
    return scored, calibration
