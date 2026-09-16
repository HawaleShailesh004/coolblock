"""Exports the real data the marketing homepage's 3D scene and comparison
chart render (apps/web/public/landing/), so the landing page never hand-types
a number or draws an illustration of a neighborhood it could show for real.

Writes:

- ``heat.png`` -- the Phase 3 downscaled land-surface temperature
  (``data/derived/<n>/heat_surface_lst.tif``), colored with this project's own
  thermal-ramp tokens (packages/ui/src/tokens.css §8.2) over the same fixed
  51-59 °C range the live app uses (packages/map/src/heatSurface.ts), with
  no-data pixels transparent.
- ``scene.json`` -- everything in that raster's footprint, in local metres
  around its center: real building footprints and heights, every public-land
  tree site the default plan could choose from, and the default plan itself
  at $20,000 (engine.optimize.plan_service.stream_solve -- the exact path the
  live app runs), plus the plan's real totals and the pipeline's real counts.
- ``baselines.json`` -- the real five-strategy comparison
  (engine.optimize.plan_service.run_baseline_comparison) for trees on public
  land at $20k, $50k and $100k.

Deliberately excluded: parcel owner names. Public-land sites belong to
agencies, but nothing identifying a person is needed to draw a tree site,
and this output ships in a public web bundle.

Run after ``scripts/export_map_layers.py``:

    uv run python scripts/export_landing_scene.py
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import rasterio
from engine.optimize.plan_service import (
    DoneEvent,
    SiteEvent,
    SolveParams,
    load_candidate_universe,
    run_baseline_comparison,
    stream_solve,
)
from engine.optimize.programs import (
    DEFAULT_PROGRAM,
    DEFAULT_PUBLIC_LAND_ONLY,
    PROGRAM_INTERVENTION_TYPES,
    candidate_pool,
)
from PIL import Image
from shapely.geometry import box

warnings.filterwarnings("ignore")

REPO_ROOT = Path(__file__).resolve().parent.parent
DERIVED = REPO_ROOT / "data" / "derived" / "edison-eastlake"
OUT_DIR = REPO_ROOT / "apps" / "web" / "public" / "landing"

# packages/map/src/heatSurface.ts's HEAT_SURFACE_RESCALE -- the same range the
# live app colors the heat surface with, so the homepage and the product agree.
LST_MIN_C, LST_MAX_C = 51.0, 59.0
# packages/ui/src/tokens.css --t-00 .. --t-100
THERMAL_STOPS = ["#0b0a1f", "#3b0f70", "#8c2981", "#de4968", "#fe9f6d", "#fcfdbf"]
HERO_BUDGET_USD = 20_000.0
COMPARISON_BUDGETS_USD = (20_000.0, 50_000.0, 100_000.0)
SIMPLIFY_TOLERANCE_M = 0.8

FloatArray = np.ndarray[Any, np.dtype[np.float64]]
BoolArray = np.ndarray[Any, np.dtype[np.bool_]]


def _hex_to_rgb(h: str) -> FloatArray:
    return np.array([int(h[i : i + 2], 16) for i in (1, 3, 5)], dtype="float64")


def _thermal_ramp(values_c: FloatArray) -> FloatArray:
    t = np.clip((values_c - LST_MIN_C) / (LST_MAX_C - LST_MIN_C), 0.0, 1.0) * (
        len(THERMAL_STOPS) - 1
    )
    lo = np.floor(t).astype(int).clip(0, len(THERMAL_STOPS) - 2)
    frac = (t - lo)[..., None]
    stops = np.stack([_hex_to_rgb(h) for h in THERMAL_STOPS])
    ramped: FloatArray = stops[lo] * (1 - frac) + stops[lo + 1] * frac
    return ramped


def export_heat_png() -> tuple[rasterio.coords.BoundingBox, str]:
    with rasterio.open(DERIVED / "heat_surface_lst.tif") as src:
        lst = src.read(1).astype("float64")
        nodata = src.nodata
        bounds, crs = src.bounds, src.crs.to_string()
    valid: BoolArray = np.isfinite(lst) & (lst != nodata)
    rgba = np.zeros((*lst.shape, 4), dtype="uint8")
    rgba[..., :3] = _thermal_ramp(np.where(valid, lst, LST_MIN_C)).round().astype("uint8")
    rgba[..., 3] = np.where(valid, 255, 0)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(OUT_DIR / "heat.png", optimize=True)
    return bounds, crs


def _local(x: float, y: float, cx: float, cy: float) -> list[float]:
    # three.js convention: +x east, -z north (so north is "into" the screen).
    return [round(x - cx, 1), round(-(y - cy), 1)]


def export_scene(bounds: rasterio.coords.BoundingBox, crs: str) -> dict[str, Any]:
    frame = box(bounds.left, bounds.bottom, bounds.right, bounds.top)
    cx, cy = (bounds.left + bounds.right) / 2, (bounds.bottom + bounds.top) / 2

    buildings = gpd.read_file(DERIVED / "buildings.geojson").to_crs(crs)
    buildings = buildings[buildings.geometry.centroid.within(frame)]
    footprints = []
    for geom, height in zip(
        buildings.geometry.simplify(SIMPLIFY_TOLERANCE_M), buildings["height_m"], strict=True
    ):
        polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        for poly in polys:
            ring = list(poly.exterior.coords)[:-1]
            if len(ring) < 3:
                continue
            flat = [v for x, y in ring for v in _local(x, y, cx, cy)]
            footprints.append([round(float(height or 5.0), 1), *flat])

    universe = load_candidate_universe()
    pool = candidate_pool(universe, DEFAULT_PROGRAM, DEFAULT_PUBLIC_LAND_ONLY)
    in_frame = pool[pool.geometry.centroid.within(frame)]
    possible = [
        [*_local(p.x, p.y, cx, cy), int(cap)]
        for p, cap in zip(in_frame.geometry.centroid, in_frame["capacity"], strict=True)
    ]

    events = list(stream_solve(SolveParams(budget_usd=HERO_BUDGET_USD)))
    done = next(e for e in events if isinstance(e, DoneEvent))
    sites = [e for e in events if isinstance(e, SiteEvent)]
    site_rows = gpd.GeoDataFrame.from_features(
        [{"type": "Feature", "geometry": s.geometry, "properties": {}} for s in sites],
        crs="EPSG:4326",
    ).to_crs(crs)
    chosen: list[dict[str, Any]] = []
    for s, geom in zip(sites, site_rows.geometry, strict=True):
        c = geom.centroid
        chosen.append(
            {
                "rank": s.rank,
                "type": s.intervention_type,
                "trees": int(s.properties.get("capacity") or 0),
                "cost_usd": round(s.cost_usd),
                "xz": _local(c.x, c.y, cx, cy),
                "in_frame": bool(c.within(frame)),
            }
        )

    all_tree_candidates = universe[
        universe["intervention_type"].isin(PROGRAM_INTERVENTION_TYPES[DEFAULT_PROGRAM])
    ]
    return {
        "frame": {
            "crs": crs,
            "width_m": round(bounds.right - bounds.left, 1),
            "depth_m": round(bounds.top - bounds.bottom, 1),
            "lst_range_c": [LST_MIN_C, LST_MAX_C],
        },
        "counts": {
            "buildings_mapped": int(len(gpd.read_file(DERIVED / "buildings.geojson"))),
            "tree_sites_possible": int(len(all_tree_candidates)),
            "tree_sites_public": int(len(pool)),
            "vulnerability_factors": 6,
        },
        "plan": {
            "budget_usd": HERO_BUDGET_USD,
            "solver": done.solver,
            "sites": done.n_sites,
            "trees": int(sum(int(c["trees"]) for c in chosen)),
            "cost_usd": round(done.total_cost_usd),
            "ewcb": round(done.total_ewcb),
        },
        "buildings": footprints,
        "possible_sites": possible,
        "chosen_sites": chosen,
    }


def export_baselines() -> dict[str, Any]:
    return {
        "program": DEFAULT_PROGRAM,
        "public_land_only": DEFAULT_PUBLIC_LAND_ONLY,
        "unit": "equity-weighted cooling benefit (person-degree-hours)",
        "by_budget": {
            str(int(b)): {k: round(v, 1) for k, v in run_baseline_comparison(b).items()}
            for b in COMPARISON_BUDGETS_USD
        },
    }


def main() -> None:
    bounds, crs = export_heat_png()
    scene = export_scene(bounds, crs)
    (OUT_DIR / "scene.json").write_text(json.dumps(scene, separators=(",", ":")), encoding="utf-8")
    (OUT_DIR / "baselines.json").write_text(
        json.dumps(export_baselines(), indent=2), encoding="utf-8"
    )
    kb = {p.name: round(p.stat().st_size / 1024, 1) for p in OUT_DIR.iterdir()}
    print(
        f"buildings={len(scene['buildings'])} possible={len(scene['possible_sites'])} "
        f"chosen={len(scene['chosen_sites'])} plan={scene['plan']} counts={scene['counts']} sizes_kb={kb}"
    )


if __name__ == "__main__":
    main()
