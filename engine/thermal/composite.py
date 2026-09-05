"""A1 -- the cloud-masked summer LST composite (COOLBLOCK-BUILD-PLAN.md §6.1 A1).

Per-pixel median across all cached Landsat scenes (D1), not mean -- a
single hot cloud-edge artefact destroys a mean. Cloud/shadow-masked via
QA_PIXEL bit flags, verified against a real scene during Phase 3
development (bit6 "clear"=1 with low-confidence cloud/shadow/cirrus/snow
bits on an actual clear Phoenix summer scene).
"""

from __future__ import annotations

import numpy as np
import xarray as xr

from engine.ingest import d01_landsat
from engine.ingest.manifest import version_dir

# QA_PIXEL bit positions (Landsat Collection 2 Level 2).
_BIT_FILL = 0
_BIT_DILATED_CLOUD = 1
_BIT_CIRRUS = 2
_BIT_CLOUD = 3
_BIT_CLOUD_SHADOW = 4
_BIT_CLEAR = 6


def clear_sky_mask(qa_pixel: xr.DataArray) -> xr.DataArray:
    """True where a pixel is usable: not fill, not cloud/shadow/cirrus, and
    the QA_PIXEL "clear" bit is set."""
    qa = qa_pixel.astype("uint16")

    def bit_is(value: xr.DataArray, bit: int) -> xr.DataArray:
        return (value & np.uint16(1 << bit)) != 0

    contaminated = bit_is(qa, _BIT_FILL) | bit_is(qa, _BIT_DILATED_CLOUD) | bit_is(qa, _BIT_CIRRUS)
    contaminated = contaminated | bit_is(qa, _BIT_CLOUD) | bit_is(qa, _BIT_CLOUD_SHADOW)
    return bit_is(qa, _BIT_CLEAR) & ~contaminated


def load_landsat_cube() -> xr.Dataset:
    path = version_dir(d01_landsat.SOURCE_ID, d01_landsat.VERSION) / "lwir11_qa_2021_2025.nc"
    return xr.open_dataset(path, decode_coords="all")


def lst_celsius(lwir11: xr.DataArray) -> xr.DataArray:
    """Collection 2 L2 thermal DN -> Celsius (§6.1 A1's conversion, shared
    with engine.ingest.d01_landsat so the two never drift apart)."""
    kelvin = lwir11.astype("float64") * d01_landsat.ST_SCALE + d01_landsat.ST_OFFSET
    return kelvin - 273.15


def build_composite(ds: xr.Dataset | None = None) -> xr.DataArray:
    """The per-pixel median summer LST composite, masked scene by scene."""
    if ds is None:
        ds = load_landsat_cube()

    mask = clear_sky_mask(ds["qa_pixel"])
    valid_st = lst_celsius(ds["lwir11"]).where(mask & (ds["lwir11"] > 0))

    composite = valid_st.median(dim="time", skipna=True)
    composite.name = "lst_composite_celsius"
    composite.attrs["long_name"] = "Median summer surface temperature, 2021-2025"
    composite.attrs["units"] = "degC"
    return composite


def scene_clear_fraction(ds: xr.Dataset | None = None) -> xr.DataArray:
    """Fraction of clear pixels per scene -- used to sanity-check coverage,
    not just trust that masking "worked"."""
    if ds is None:
        ds = load_landsat_cube()
    mask = clear_sky_mask(ds["qa_pixel"]) & (ds["lwir11"] > 0)
    return mask.mean(dim=["x", "y"])
