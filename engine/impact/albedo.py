"""C3 -- albedo interventions (COOLBLOCK-BUILD-PLAN.md §6.3 C3): cool-roof
and cool-pavement ΔT via a first-order surface energy-balance perturbation,
not a full radiative-transfer model:

    ΔT = Δα · S_down / (h_conv + 4εσT³)

Derived by linearizing the surface energy balance around the baseline
state: raising a surface's albedo by Δα reduces absorbed shortwave energy
by Δα·S_down; at steady state that reduction is balanced by less
convective + longwave-radiative heat loss, (h_conv + 4εσT³)·ΔT, which is
the linearization of the T⁴ Stefan-Boltzmann term (d(σT⁴)/dT = 4σT³) plus
a linear convective term.

**Manual unit check** (Wolfram MCP not available this session --
COOLBLOCK-BUILD-PLAN.md §7.2's documented condition, see
`docs/adr/0002-*.md` for the general fallback): S_down [W/m²] × Δα
[dimensionless] = ΔQ_abs [W/m²]. h_conv is [W/(m²·K)] by definition;
σ is [W/(m²·K⁴)], so σT³ is [W/(m²·K⁴)]·[K³] = [W/(m²·K)], matching
h_conv's units, and their sum stays [W/(m²·K)]. [W/m²] / [W/(m²·K)] = [K].
Dimensionally consistent.

Real inputs, disclosed literature constants where no direct measurement
exists:

- **S_down**: NASA POWER's (D14) real `ALLSKY_SFC_SW_DWN` for the design
  day (the same real hottest-day-on-record C2 uses), converted from a
  daily kWh/m² total to an estimated solar-noon peak via the standard
  sinusoidal-insolation approximation (Duffie & Beckman): peak ≈
  (daily kWh/m² × 1000) / daylight_hours × (π/2). Daylight hours for the
  design day come from `pvlib`'s real sunrise/sunset (NREL SPA algorithm),
  not an assumed constant.
- **T**: the Phase 3 downscaled 10m LST field at each candidate's
  location, Celsius converted to Kelvin.
- **h_conv**: McAdams' empirical natural+forced convection correlation,
  h = 5.7 + 3.8·wind_speed (W/m²·K) -- a standard, cited building-physics
  formula, not invented here -- driven by Open-Meteo's (D13) real
  design-day wind speed.
- **Current albedo**: sampled from the real Sentinel-2 albedo proxy
  (`engine.thermal.predictors`, already disclosed there as an unweighted
  reflectance-band mean, not a validated broadband albedo retrieval) at
  each candidate's location -- not assumed uniform across the
  neighborhood.
- **Target albedo**: literature planning values for cool-roof/cool-
  pavement coatings (Levinson & Akbari-range figures for retrofit
  products): 0.65 for a cool-roof coating, 0.40 for cool/reflective
  pavement. Disclosed as planning estimates -- these are retrofit
  products not yet installed anywhere in this neighborhood, so there is
  no way to measure their real achieved albedo here.
- **ε (surface emissivity)**: 0.95, a standard broadband literature value
  for built (roof/pavement) surfaces.

**Important interpretation note, not a bug**: measured on real candidates,
cool roofs average **ΔT ≈ 12.9°C**, cool pavement **ΔT ≈ 3.3°C**. These are
large next to C1's tree ΔT_peak (0.1-7.9°C) because they measure a
*different quantity*: C3's ΔT is the retrofit surface's own temperature
change at its own footprint, undiluted by area-averaging -- it is not an
ambient 2m-air-temperature or neighborhood-wide LST effect the way C1's
Gaussian-kernel ΔT_peak already is. The magnitude matches published cool-
roof literature for *roof surface* temperature reduction (commonly cited
as 11-22°C, up to ~28°C in extreme cases) -- consistent, not inflated --
but any downstream objective (D4's EWCB) that sums C1 and C3 contributions
must not treat these two ΔT values as directly interchangeable "degrees of
neighborhood cooling" without first accounting for that difference.

**Also disclosed**: `current_albedo_proxy` is sampled from a single 10m
Sentinel-2 pixel at each candidate's centroid -- for a small parking lot
or building footprint, that pixel can blend in adjacent, differently-
surfaced ground (bilinear resampling in `load_sentinel2_predictors`), so
the "before" albedo for small candidates is an approximation, not a
footprint-exact measurement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import pvlib

from engine.config import load_neighborhood_config
from engine.impact.shade import DesignDay, find_design_day
from engine.ingest import d13_open_meteo, d14_nasa_power
from engine.ingest.grid import get_canonical_grid
from engine.ingest.manifest import version_dir
from engine.thermal.downscale import run_downscaling
from engine.thermal.predictors import load_sentinel2_predictors

STEFAN_BOLTZMANN_W_M2_K4 = 5.670374419e-8
SURFACE_EMISSIVITY = 0.95

TARGET_ALBEDO_COOL_ROOF = 0.65
TARGET_ALBEDO_COOL_PAVEMENT = 0.40

TARGET_ALBEDO_BY_INTERVENTION = {
    "cool_roof": TARGET_ALBEDO_COOL_ROOF,
    "cool_pavement": TARGET_ALBEDO_COOL_PAVEMENT,
}

# Sentinel-2 reflectance is 0-1 already; the albedo proxy is a raw
# reflectance-band average so it can plausibly exceed typical broadband
# albedo for very bright surfaces -- clip to a physically sane range
# rather than let a bad pixel produce a negative or >1 Delta-alpha.
ALBEDO_PROXY_MIN = 0.0
ALBEDO_PROXY_MAX = 0.9


@dataclass(frozen=True)
class EnergyBalanceInputs:
    s_down_peak_w_m2: float
    wind_speed_m_s: float
    h_conv_w_m2_k: float


def _daylight_hours(design_day: DesignDay) -> float:
    cfg = load_neighborhood_config()
    b = cfg.bbox_wgs84
    lat, lon = (b.min_lat + b.max_lat) / 2, (b.min_lon + b.max_lon) / 2

    day_start = design_day.hours[0].normalize()
    times = pd.DatetimeIndex([day_start], tz=design_day.hours.tz)
    rst = pvlib.solarposition.sun_rise_set_transit_spa(times, lat, lon)
    sunrise, sunset = rst["sunrise"].iloc[0], rst["sunset"].iloc[0]
    return float((sunset - sunrise).total_seconds() / 3600.0)


def _s_down_peak_w_m2(design_day: DesignDay) -> float:
    """Solar-noon peak shortwave irradiance, estimated from NASA POWER's
    real daily total via the sinusoidal-insolation approximation."""
    df = pd.read_parquet(version_dir(d14_nasa_power.SOURCE_ID, d14_nasa_power.VERSION) / "daily_summer_2021_2025.parquet")
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d").dt.date
    match = df[df["date"] == design_day.date.date()]
    if len(match) == 0:
        raise RuntimeError(f"no NASA POWER record for design day {design_day.date.date()}")
    daily_kwh_m2 = float(match["ALLSKY_SFC_SW_DWN"].iloc[0])

    daylight_hours = _daylight_hours(design_day)
    return (daily_kwh_m2 * 1000.0 / daylight_hours) * (np.pi / 2.0)


def _wind_speed_m_s(design_day: DesignDay) -> float:
    """Real design-day-average wind speed from Open-Meteo (D13), converted
    from its native km/h to m/s for the McAdams convection formula."""
    df = pd.read_parquet(version_dir(d13_open_meteo.SOURCE_ID, d13_open_meteo.VERSION) / "hourly_summer_2021_2025.parquet")
    df["time"] = pd.to_datetime(df["time"])
    day_rows = df[df["time"].dt.date == design_day.date.date()]
    day_rows = day_rows[
        (day_rows["time"].dt.hour >= design_day.hours[0].hour)
        & (day_rows["time"].dt.hour <= design_day.hours[-1].hour)
    ]
    kmh = float(pd.to_numeric(day_rows["wind_speed_10m"], errors="coerce").mean())
    return kmh / 3.6


def compute_energy_balance_inputs(design_day: DesignDay) -> EnergyBalanceInputs:
    s_down = _s_down_peak_w_m2(design_day)
    wind_speed = _wind_speed_m_s(design_day)
    h_conv = 5.7 + 3.8 * wind_speed  # McAdams natural+forced convection correlation, W/(m^2 K)
    return EnergyBalanceInputs(s_down_peak_w_m2=s_down, wind_speed_m_s=wind_speed, h_conv_w_m2_k=h_conv)


def _pixel_index(grid: Any, x: float, y: float) -> tuple[int, int]:
    col, row = ~grid.transform * (x, y)
    row_i = int(np.clip(round(row), 0, grid.height - 1))
    col_i = int(np.clip(round(col), 0, grid.width - 1))
    return row_i, col_i


def compute_delta_t(
    candidates: gpd.GeoDataFrame,
    inputs: EnergyBalanceInputs,
) -> gpd.GeoDataFrame:
    """Adds `delta_t_degc` and `current_albedo_proxy` to `candidates` --
    only `cool_roof`/`cool_pavement` rows get a nonzero value; any other
    intervention type is out of scope for this module and set to 0.0."""
    grid = get_canonical_grid()
    lst_k = run_downscaling().lst_10m.values.astype("float64") + 273.15
    albedo_proxy = load_sentinel2_predictors(grid)["albedo_proxy"].values.astype("float64")
    albedo_proxy = np.clip(albedo_proxy, ALBEDO_PROXY_MIN, ALBEDO_PROXY_MAX)

    denom_base = inputs.h_conv_w_m2_k  # + 4*eps*sigma*T^3, added per-candidate below

    delta_t = np.zeros(len(candidates), dtype="float64")
    current_albedo = np.full(len(candidates), np.nan, dtype="float64")

    for i, row in enumerate(candidates.itertuples()):
        target_albedo = TARGET_ALBEDO_BY_INTERVENTION.get(row.intervention_type)
        if target_albedo is None:
            continue

        centroid = row.geometry.centroid
        r, c = _pixel_index(grid, centroid.x, centroid.y)

        local_albedo = albedo_proxy[r, c]
        if not np.isfinite(local_albedo):
            continue
        current_albedo[i] = local_albedo

        delta_alpha = max(0.0, target_albedo - local_albedo)
        if delta_alpha == 0.0:
            continue

        local_t_k = lst_k[r, c]
        if not np.isfinite(local_t_k):
            continue

        radiative_term = 4.0 * SURFACE_EMISSIVITY * STEFAN_BOLTZMANN_W_M2_K4 * local_t_k**3
        denom = denom_base + radiative_term
        delta_t[i] = delta_alpha * inputs.s_down_peak_w_m2 / denom

    out = candidates.copy()
    out["delta_t_degc"] = delta_t
    out["current_albedo_proxy"] = current_albedo
    return out


def run_albedo_model(candidates: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, EnergyBalanceInputs, DesignDay]:
    """C3's full output: candidates with `delta_t_degc`, the energy-balance
    inputs used (so S_down/h_conv travel with any downstream report), and
    the design day they were computed for."""
    design_day = find_design_day()
    inputs = compute_energy_balance_inputs(design_day)
    scored = compute_delta_t(candidates, inputs)
    return scored, inputs, design_day
