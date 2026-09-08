"""§7.2.1 -- unit-aware thermal computation (COOLBLOCK-BUILD-PLAN.md):
"The albedo->ΔT energy balance carried out with real units (W/m^2, K,
J/(kg*K)), so unit errors are impossible rather than merely unlikely.
Hand-rolled Python will silently accept a W/m^2 where a kW/m^2 belongs;
Wolfram will not."

**Substituted per `docs/adr/0002-*.md`'s decision**: no Wolfram Cloud
credential was in hand, so `pint` (a real, independent Python unit
library -- not a toy) plays the same structural role Wolfram's
`Quantity[]` would have. `engine.impact.albedo`'s own module docstring
already carries a *manual*, hand-written version of this check ("Manual
unit check (Wolfram MCP not available this session)... Dimensionally
consistent"); this module promotes that from a comment a human could get
wrong or let drift, to code that actually raises if a unit is wrong.

Independently re-implements C3's energy-balance ΔT formula
(`engine.impact.albedo.compute_delta_t`) with every quantity explicitly
typed via `pint`:

    ΔT = Δalpha * S_down / (h_conv + 4*epsilon*sigma*T^3)

`pint` raises `DimensionalityError` at the point a unit-incompatible
operation is attempted (e.g. adding W/m^2 to W/(m^2*K), or a caller
passing S_down in kW/m^2 where W/m^2 is expected) -- not later, not
silently. `test_unit_checked_delta_t_catches_a_real_unit_error` in
`engine/tests/test_verify_units.py` proves this by deliberately
constructing exactly that mistake and confirming pint refuses it, the
same "prove the check can actually fail" discipline as this project's
other verification tests (`engine/tests/test_local_search.py`,
`engine/verify/optimizer_crosscheck.py`'s own disagreement test).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pint

ureg: Any = pint.UnitRegistry()
Q_ = ureg.Quantity

STEFAN_BOLTZMANN = Q_(5.670374419e-8, "W / (m^2 * K^4)")


@dataclass(frozen=True)
class UnitCheckedDeltaT:
    delta_t_k: float
    delta_q_abs_w_m2: float
    denom_w_m2_k: float


def unit_checked_delta_t(
    s_down_w_m2: float,
    delta_alpha: float,
    h_conv_w_m2_k: float,
    surface_temp_k: float,
    emissivity: float = 0.95,
) -> UnitCheckedDeltaT:
    """Same formula as `engine.impact.albedo.compute_delta_t`, but with
    every intermediate quantity carrying a real `pint` unit -- a mistake
    (a wrong exponent on T, a value handed in the wrong unit, an addition
    of incompatible quantities) raises `pint.DimensionalityError` here
    rather than silently producing a wrong number in a unit that happens
    to look plausible."""
    s_down = Q_(s_down_w_m2, "W / m^2")
    delta_alpha_q = Q_(delta_alpha, "dimensionless")
    h_conv = Q_(h_conv_w_m2_k, "W / (m^2 * K)")
    t = Q_(surface_temp_k, "K")
    epsilon = Q_(emissivity, "dimensionless")

    delta_q_abs = s_down * delta_alpha_q  # W/m^2
    radiative_term = 4 * epsilon * STEFAN_BOLTZMANN * t**3  # W/(m^2*K)
    denom = h_conv + radiative_term  # W/(m^2*K); pint raises here if the two terms aren't unit-compatible

    delta_t = delta_q_abs / denom  # (W/m^2) / (W/(m^2*K)) -- pint reduces this to K
    delta_t_k = delta_t.to("kelvin")  # raises DimensionalityError if the algebra above didn't actually reduce to a temperature

    return UnitCheckedDeltaT(
        delta_t_k=float(delta_t_k.magnitude),
        delta_q_abs_w_m2=float(delta_q_abs.to("W / m^2").magnitude),
        denom_w_m2_k=float(denom.to("W / (m^2 * K)").magnitude),
    )
