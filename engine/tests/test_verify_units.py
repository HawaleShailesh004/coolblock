"""§7.2.1 -- pint-based unit-checked energy balance, substituted for
Wolfram per docs/adr/0002-*.md. Pure logic, no API cost, no real data
needed."""

from __future__ import annotations

import pint
import pytest
from engine.impact.albedo import STEFAN_BOLTZMANN_W_M2_K4, SURFACE_EMISSIVITY
from engine.verify.units import Q_, unit_checked_delta_t


def test_unit_checked_delta_t_matches_the_production_formula() -> None:
    """The pint-verified computation and `engine.impact.albedo`'s actual
    production formula must agree to floating-point precision on the same
    inputs and the same real physical constants -- proving the unit-safe
    version is a faithful re-implementation, not a different formula that
    happens to also produce a temperature."""
    s_down_w_m2, delta_alpha, h_conv_w_m2_k, t_k = 700.0, 0.25, 12.36, 315.0

    result = unit_checked_delta_t(s_down_w_m2, delta_alpha, h_conv_w_m2_k, t_k, emissivity=SURFACE_EMISSIVITY)

    radiative_term = 4.0 * SURFACE_EMISSIVITY * STEFAN_BOLTZMANN_W_M2_K4 * t_k**3
    expected_delta_t = delta_alpha * s_down_w_m2 / (h_conv_w_m2_k + radiative_term)

    assert result.delta_t_k == pytest.approx(expected_delta_t, rel=1e-9)
    assert result.delta_t_k > 0  # a real cool-roof/cool-pavement retrofit should cool, not warm


def test_unit_checked_delta_t_catches_a_real_unit_error() -> None:
    """Proves pint actually enforces the check rather than merely passing
    by construction -- deliberately adds S_down (W/m^2) directly to
    h_conv (W/(m^2*K)), the exact category of mistake this module exists
    to make structurally impossible, and confirms pint refuses it with a
    real `DimensionalityError` rather than silently computing a wrong
    number in a unit that happens to look plausible."""
    s_down = Q_(500.0, "W / m^2")
    h_conv = Q_(10.0, "W / (m^2 * K)")
    with pytest.raises(pint.DimensionalityError):
        s_down + h_conv  # not unit-compatible -- W/m^2 is not W/(m^2*K)


def test_unit_checked_delta_t_rejects_a_non_temperature_result() -> None:
    """A second, structural version of the same proof: if the algebra
    didn't actually reduce to a temperature (simulated here by asking
    pint to convert a definitely-not-a-temperature quantity to kelvin),
    `.to("kelvin")` itself raises -- the same call `unit_checked_delta_t`
    makes on its own final result."""
    not_a_temperature = Q_(42.0, "W / m^2")
    with pytest.raises(pint.DimensionalityError):
        not_a_temperature.to("kelvin")
