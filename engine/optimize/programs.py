"""Which candidates a plan is even allowed to choose from -- the resolution
of `docs/adr/0014-*.md`, recorded in `docs/adr/0027-*.md`.

**The problem this fixes.** `engine.optimize.objective`'s coverage function
receives two physically different quantities: a tree's *ambient* cooling
(C1, a Gaussian kernel spread over ~2,800 m² around the tree) and a cool
roof's *surface* temperature change at its own footprint (C3, undiluted,
mean ~12.9 °C). Ranked together, cool roofs win every budget: the default
$50,000 plan was 47 private-home cool roofs and zero trees, contradicting
the product's own question ("where should the next 40 trees go?").

**The fix is ADR-0014's own second option, not a conversion factor.**
Nothing ingested here supports converting surface ΔT into ambient ΔT, so
inventing one would be the fabricated fix ADR-0014 rightly refused. Instead
a plan picks a *program*, and each program ranks only interventions that
deliver the same kind of benefit to the same kind of beneficiary:

- ``"trees"`` -- street trees and park/lot tree clusters. Shade and ambient
  cooling for people outdoors. This is what urban-forestry heat grants
  actually fund, so it is the default.
- ``"cool_roofs"`` -- reflective roof coatings. Lower surface temperature
  for the people inside that building. Usually funded by energy or
  building programs, and a private roof needs its owner's consent.

``cool_pavement`` and ``shade_structure`` belong to neither pool: the
objective gives them zero population benefit (their EWCB is 0 by D4's
disclosed scope), so including them would only let a baseline strategy
waste budget on them and make the "beats the alternatives" comparison
look better than it is.

**Public land is a pool filter, not a side constraint.** Restricting to
public land removes candidates before solving; it does not couple picks to
each other the way a per-zone cap or a maintenance budget does. So it no
longer forces the slower non-lazy constrained greedy -- the plan still gets
CELF and its approximation guarantee, and the baseline comparison is run on
exactly the same pool the plan was solved on.
"""

from __future__ import annotations

from typing import Literal

import geopandas as gpd

from engine.optimize.constraints import PUBLIC_OWNERSHIP

Program = Literal["trees", "cool_roofs"]

PROGRAM_INTERVENTION_TYPES: dict[str, frozenset[str]] = {
    "trees": frozenset({"street_tree", "park_lot_tree_cluster"}),
    "cool_roofs": frozenset({"cool_roof"}),
}

DEFAULT_PROGRAM: Program = "trees"
DEFAULT_PUBLIC_LAND_ONLY = True


def candidate_pool(
    universe: gpd.GeoDataFrame,
    program: str = DEFAULT_PROGRAM,
    public_land_only: bool = DEFAULT_PUBLIC_LAND_ONLY,
) -> gpd.GeoDataFrame:
    """The candidates a plan in `program` may choose from, re-indexed from 0
    (the optimizer addresses candidates by position). Raises on an unknown
    program rather than silently falling back to every intervention type --
    that fallback is exactly the mixed ranking this module exists to stop."""
    if program not in PROGRAM_INTERVENTION_TYPES:
        raise ValueError(f"unknown program {program!r} -- expected one of {sorted(PROGRAM_INTERVENTION_TYPES)}")
    mask = universe["intervention_type"].isin(PROGRAM_INTERVENTION_TYPES[program])
    if public_land_only:
        mask &= universe["ownership"].isin(PUBLIC_OWNERSHIP)
    return universe.loc[mask].reset_index(drop=True)
