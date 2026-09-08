"""§7.2.2 -- sympy-based symbolic sensitivity of the cooling kernel to
beta, substituted for Wolfram per docs/adr/0002-*.md. Uses the real
calibration (`engine.impact.cooling_kernel.calibrate_beta`, cached-data-
only -- no network call) for beta's own real, measured confidence
interval; f/g/h are representative synthetic values, matching this
project's own test convention (test_celf.py, test_exact.py) of a small,
hand-built instance for the actual assertion, not raw raster I/O."""

from __future__ import annotations

import sympy as sp
from engine.impact.cooling_kernel import calibrate_beta
from engine.verify.sensitivity import (
    D_DELTA_T_PEAK_D_BETA,
    _beta,
    _f,
    _g,
    _h,
    cooling_kernel_sensitivity,
)


def test_derivative_of_delta_t_peak_with_respect_to_beta_is_exactly_fgh() -> None:
    """The real symbolic fact this whole module exists to establish:
    d(ΔT_peak)/d(beta) = f*g*h exactly, with no remaining beta term --
    proving the beta->ΔT_peak relationship really is linear, which is
    what makes scaling beta's confidence interval by this derivative a
    legitimate (not merely plausible-looking) way to get ΔT_peak's own
    interval."""
    assert sp.simplify(D_DELTA_T_PEAK_D_BETA - _f * _g * _h) == 0
    assert _beta not in D_DELTA_T_PEAK_D_BETA.free_symbols


def test_cooling_kernel_sensitivity_uses_the_real_calibration() -> None:
    """Grounded in this neighborhood's real OLS calibration (cached data,
    no network call) -- not a synthetic beta -- combined with
    representative f/g/h values in the same [0, 1]-ish ranges
    `engine.impact.cooling_kernel.compute_delta_t_peak` actually uses."""
    calibration = calibrate_beta()
    beta_magnitude = abs(calibration.beta_degc_per_canopy_fraction)
    beta_lo, beta_hi = sorted(abs(b) for b in calibration.beta_ci95)
    beta_ci95_magnitude = (beta_lo, beta_hi)

    canopy_increment_fraction, g, h = 0.6, 0.85, 1.05
    result = cooling_kernel_sensitivity(beta_magnitude, beta_ci95_magnitude, canopy_increment_fraction, g, h)

    expected_delta_t = beta_magnitude * canopy_increment_fraction * g * h
    expected_derivative = canopy_increment_fraction * g * h

    assert result.delta_t_peak_degc == expected_delta_t
    assert result.d_delta_t_peak_d_beta == expected_derivative
    assert result.delta_t_peak_ci95[0] <= result.delta_t_peak_degc <= result.delta_t_peak_ci95[1]
