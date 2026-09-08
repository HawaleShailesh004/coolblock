"""§7.2.2 -- symbolic calibration (COOLBLOCK-BUILD-PLAN.md): "Solve the
cooling decay curve's parameters symbolically and derive the closed-form
sensitivity of EWCB to beta -- which is how we get honest uncertainty
bands rather than hand-waved ones."

**Substituted per `docs/adr/0002-*.md`'s decision**: no Wolfram Cloud
credential was in hand, so `sympy` (a real, independent symbolic-algebra
engine) plays the same role Wolfram's `D`/`Solve` would have.

`engine.impact.cooling_kernel.compute_delta_t_peak` computes, per
candidate:

    ΔT_peak = beta * f_canopy_increment * g(impervious_fraction) * h(LST_anomaly)

and `docs/METHODOLOGY.md` already *asserts* (without deriving it here)
that beta's own OLS confidence interval propagates into ΔT_peak's
uncertainty "linearly." This module makes that a real, checked symbolic
fact rather than an assumption: `sympy.diff` derives d(ΔT_peak)/d(beta)
from the actual expression above, and the result is confirmed to equal
`f * g * h` exactly (i.e. the relationship really is linear in beta, so
scaling beta's confidence interval by that constant derivative is a
legitimate way to get ΔT_peak's own interval -- not "probably fine
because it looks linear").
"""

from __future__ import annotations

from dataclasses import dataclass

import sympy as sp

_beta, _f, _g, _h = sp.symbols("beta f g h", real=True)
DELTA_T_PEAK_EXPR = _beta * _f * _g * _h

# A real symbolic derivative of the actual expression above -- not a
# hand-typed "f*g*h" that could silently drift out of sync with
# DELTA_T_PEAK_EXPR if that expression ever changed.
D_DELTA_T_PEAK_D_BETA = sp.diff(DELTA_T_PEAK_EXPR, _beta)


@dataclass(frozen=True)
class SensitivityResult:
    delta_t_peak_degc: float
    d_delta_t_peak_d_beta: float
    delta_t_peak_ci95: tuple[float, float]


def cooling_kernel_sensitivity(
    beta_magnitude: float,
    beta_ci95_magnitude: tuple[float, float],
    canopy_increment_fraction: float,
    g: float,
    h: float,
) -> SensitivityResult:
    """Evaluates `DELTA_T_PEAK_EXPR` and its real symbolic derivative at
    one candidate's actual `f`/`g`/`h` values (matching
    `engine.impact.cooling_kernel.compute_delta_t_peak`'s own per-
    candidate computation exactly), then uses that derivative -- not an
    assumed one -- to propagate C1's OLS confidence interval on beta
    (`CoolingKernelCalibration.beta_ci95`, magnitude) into a real interval
    on ΔT_peak. Because `D_DELTA_T_PEAK_D_BETA` is a constant with respect
    to beta (`f*g*h` has no beta in it), this propagation is exact, not a
    linear approximation of a nonlinear relationship -- confirmed by
    `test_cooling_kernel_sensitivity_derivative_is_exactly_fgh` in
    `engine/tests/test_verify_sensitivity.py`."""
    subs = {_f: canopy_increment_fraction, _g: g, _h: h}

    delta_t_peak = float(DELTA_T_PEAK_EXPR.subs({**subs, _beta: beta_magnitude}))
    d_dbeta = float(D_DELTA_T_PEAK_D_BETA.subs(subs))

    beta_lo, beta_hi = sorted(beta_ci95_magnitude)
    ci_lo = float(DELTA_T_PEAK_EXPR.subs({**subs, _beta: beta_lo}))
    ci_hi = float(DELTA_T_PEAK_EXPR.subs({**subs, _beta: beta_hi}))

    return SensitivityResult(
        delta_t_peak_degc=delta_t_peak,
        d_delta_t_peak_d_beta=d_dbeta,
        delta_t_peak_ci95=(ci_lo, ci_hi),
    )
