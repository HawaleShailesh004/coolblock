# 5. Plantable space: rule layer only, ML segmentation deferred

Date: 2026-09-05

## Status

Accepted

## Context

COOLBLOCK-BUILD-PLAN.md §6.2 specifies plantable space as a fusion of a
rule layer (B1, deterministic) and an ML layer (B2, a SegFormer-B0 fine-
tuned on Chesapeake Land Cover weights), with the ML layer catching cases
the rule layer's building/road/canopy subtraction misses. The plan's own
risk register (R4) already anticipates this might not ship: "Segmentation
quality is poor... The rule layer alone is sufficient for a working
product; ML is an accuracy upgrade, not a dependency. Ship rule-first."

Fine-tuning a segmentation model requires labeled training data, GPU/CPU
training time, and non-trivial ML engineering (tiled inference, seam
blending, weight fine-tuning) -- a substantial undertaking relative to
the marginal value over the rule layer for a single ~2 km² neighborhood
that already has real, high-resolution (0.6m) NAIP imagery and complete
OSM building/road/tree vector data.

## Decision

Phase 4 ships B1 (`engine/surface/rule_layer.py`) and B3
(`engine/surface/candidates.py`) without B2. There is no "ML mask" to
fuse with, so there is no disagreement region to flag as
"needs-verification" either -- every candidate here is rule-derived, not
fusion-derived. This is disclosed in the UI copy and in
`docs/METHODOLOGY.md`, not silently presented as a fused product.

Two real adaptations to the rule layer itself, both disclosed in the
module docstring:

1. Existing tree canopy is identified via real OSM tree points (832 of
   them) buffered by an assumed 4m crown radius, not via a normalized
   surface model (DSM - DEM) as the plan describes -- we have a bare-earth
   DEM (D12) but no DSM, so vegetation *height* cannot currently be
   computed from ingested sources. This under-counts unmapped trees.
2. Cool-pavement, cool-roof, and depave-to-bioswale interventions are not
   generated in Phase 4. They target impervious surfaces (parking lots,
   rooftops), which the plantable-space rule layer explicitly *excludes*
   (it identifies bare ground). Generating those candidates needs a
   different source polygon set (parking lot / rooftop geometry) that
   Phase 4 doesn't build. Deferred to Phase 5/6 when the optimizer needs
   that cost/benefit heterogeneity.

## Consequences

- `engine/surface/candidates.py` currently emits three intervention types
  (`street_tree`, `park_lot_tree_cluster`, `shade_structure`), not the six
  in §6.2's cost table. The optimizer (Phase 6) will initially solve over
  a narrower candidate set than the plan envisions.
- If B2 is revisited later, `run_rule_layer()`'s boolean mask is the
  natural place to fuse in an ML mask (agreement -> high confidence,
  disagreement -> flagged) without restructuring the candidate-generation
  code in `candidates.py`, which already consumes a plain plantable
  GeoDataFrame.
- The manual spot-check (Phase 4 DoD) is against the rule layer's actual
  output, not a fused product -- see `docs/METHODOLOGY.md` for the result.
