"""A2 -- TsHARP-style statistical downscaling, 30m -> 10m
(COOLBLOCK-BUILD-PLAN.md §6.1 A2). Published, defensible methodology, not
invention:

1. Fit `LST ~ f(NDVI, NDBI, albedo, %impervious)` at 30m with a
   gradient-boosted regressor, spatially cross-validated (block CV, not
   random shuffle -- adjacent pixels are correlated, so a random split
   leaks information between train and test).
2. Compute the 30m residual field (observed - predicted).
3. Apply the fitted model to the 10m predictors -> a 10m LST prediction.
4. Add the bilinearly-interpolated 30m residual back -> mass-conserving
   10m LST.
5. Report R^2, RMSE (from the spatial CV, not in-sample), and a per-pixel
   uncertainty raster from a pair of quantile regressors (q10/q90).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import xarray as xr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold

from engine.ingest.crs import to_canonical_crs_raster
from engine.ingest.grid import CanonicalGrid, get_canonical_grid, get_grid_at_resolution
from engine.thermal.composite import build_composite
from engine.thermal.predictors import load_impervious_predictor, load_sentinel2_predictors

FIT_RESOLUTION_M = 30.0
PREDICTOR_NAMES = ["ndvi", "ndbi", "albedo_proxy", "impervious_pct"]
N_SPATIAL_FOLDS = 5
# Block size for the spatial CV grouping, in 30m pixels -- large enough that
# a fold's train/test pixels aren't adjacent (avoids autocorrelation leakage).
SPATIAL_BLOCK_PIXELS = 3


@dataclass(frozen=True)
class DownscalingResult:
    lst_10m: xr.DataArray  # final mass-conserving prediction
    uncertainty_10m: xr.DataArray  # q90 - q10 predictive band width, degC
    r2_cv: float
    rmse_cv: float
    n_training_pixels: int


def _stack_predictors(grid: CanonicalGrid) -> xr.Dataset:
    s2 = load_sentinel2_predictors(grid)
    impervious = load_impervious_predictor(grid)
    return xr.Dataset({**{k: s2[k] for k in ("ndvi", "ndbi", "albedo_proxy")}, "impervious_pct": impervious})


def _lst_composite_on_grid(grid: CanonicalGrid) -> xr.DataArray:
    composite = build_composite()  # native ~30m Landsat grid
    composite = composite.rio.write_crs(f"EPSG:{get_canonical_grid().epsg}")
    return to_canonical_crs_raster(composite, resampling="bilinear", grid=grid)


def _spatial_groups(height: int, width: int, block: int) -> np.ndarray[Any, np.dtype[np.int_]]:
    """Coarse block id per pixel, for GroupKFold -- pixels in the same block
    never split across train/test."""
    row_block = np.arange(height) // block
    col_block = np.arange(width) // block
    return (row_block[:, None] * (width // block + 1) + col_block[None, :]).astype(int)


def _to_training_table(
    predictors: xr.Dataset, target: xr.DataArray
) -> tuple[np.ndarray[Any, np.dtype[np.float64]], np.ndarray[Any, np.dtype[np.float64]], np.ndarray[Any, np.dtype[np.int_]]]:
    stacked = np.stack([predictors[name].values for name in PREDICTOR_NAMES], axis=-1)
    y = target.values
    groups = _spatial_groups(y.shape[0], y.shape[1], SPATIAL_BLOCK_PIXELS)

    valid = np.isfinite(y) & np.all(np.isfinite(stacked), axis=-1)
    return stacked[valid], y[valid], groups[valid]


def run_downscaling() -> DownscalingResult:
    grid_30m = get_grid_at_resolution(FIT_RESOLUTION_M)
    grid_10m = get_canonical_grid()

    predictors_30m = _stack_predictors(grid_30m)
    lst_30m = _lst_composite_on_grid(grid_30m)

    X, y, groups = _to_training_table(predictors_30m, lst_30m)
    if X.shape[0] < N_SPATIAL_FOLDS * 5:
        raise RuntimeError(f"too few valid 30m training pixels ({X.shape[0]}) for {N_SPATIAL_FOLDS}-fold spatial CV")

    # Spatial cross-validation -- report R^2/RMSE from held-out folds only.
    gkf = GroupKFold(n_splits=min(N_SPATIAL_FOLDS, len(np.unique(groups))))
    cv_pred = np.full_like(y, np.nan)
    for train_idx, test_idx in gkf.split(X, y, groups):
        model = HistGradientBoostingRegressor(random_state=0)
        model.fit(X[train_idx], y[train_idx])
        cv_pred[test_idx] = model.predict(X[test_idx])

    residual_cv = y - cv_pred
    rmse_cv = float(np.sqrt(np.mean(residual_cv**2)))
    ss_res = float(np.sum(residual_cv**2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2_cv = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    # The production model: fit on all 30m data (the CV above only measured it).
    main_model = HistGradientBoostingRegressor(random_state=0)
    main_model.fit(X, y)

    q10_model = HistGradientBoostingRegressor(loss="quantile", quantile=0.1, random_state=0)
    q90_model = HistGradientBoostingRegressor(loss="quantile", quantile=0.9, random_state=0)
    q10_model.fit(X, y)
    q90_model.fit(X, y)

    # Step 2: the 30m residual field (in-sample, by design -- TsHARP corrects
    # the *pattern* the regression misses, using the same fit it corrects).
    stacked_30m = np.stack([predictors_30m[n].values for n in PREDICTOR_NAMES], axis=-1)
    valid_mask_30m = np.isfinite(lst_30m.values) & np.all(np.isfinite(stacked_30m), axis=-1)

    pred_grid_30m = np.full(lst_30m.shape, np.nan)
    pred_grid_30m[valid_mask_30m] = main_model.predict(stacked_30m[valid_mask_30m])
    residual_30m = xr.full_like(lst_30m, np.nan)
    residual_30m.values = lst_30m.values - pred_grid_30m

    # Step 3: predict at 10m.
    predictors_10m = _stack_predictors(grid_10m)
    stacked_10m = np.stack([predictors_10m[n].values for n in PREDICTOR_NAMES], axis=-1)
    valid_10m = np.all(np.isfinite(stacked_10m), axis=-1)

    pred_10m = np.full((grid_10m.height, grid_10m.width), np.nan)
    q10_10m = np.full_like(pred_10m, np.nan)
    q90_10m = np.full_like(pred_10m, np.nan)
    flat_valid = stacked_10m[valid_10m]
    pred_10m[valid_10m] = main_model.predict(flat_valid)
    q10_10m[valid_10m] = q10_model.predict(flat_valid)
    q90_10m[valid_10m] = q90_model.predict(flat_valid)

    pred_10m_da = xr.DataArray(pred_10m, dims=("y", "x"), coords=predictors_10m["ndvi"].coords)
    pred_10m_da = pred_10m_da.rio.write_crs(f"EPSG:{grid_10m.epsg}")

    # Step 4: bilinearly upsample the 30m residual and add it back.
    residual_10m = to_canonical_crs_raster(residual_30m, resampling="bilinear", grid=grid_10m)
    final_10m = pred_10m_da + residual_10m
    final_10m.name = "lst_downscaled_10m_celsius"

    uncertainty_10m = xr.DataArray(
        q90_10m - q10_10m, dims=("y", "x"), coords=predictors_10m["ndvi"].coords
    )
    uncertainty_10m = uncertainty_10m.rio.write_crs(f"EPSG:{grid_10m.epsg}")
    uncertainty_10m.name = "lst_uncertainty_q90_minus_q10"

    return DownscalingResult(
        lst_10m=final_10m,
        uncertainty_10m=uncertainty_10m,
        r2_cv=r2_cv,
        rmse_cv=rmse_cv,
        n_training_pixels=int(X.shape[0]),
    )
