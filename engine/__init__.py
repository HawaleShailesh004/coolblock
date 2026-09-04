"""CoolBlock engine: the science.

Submodules (see COOLBLOCK-BUILD-PLAN.md §3.4, §6):
    ingest    -- fetch, validate, reproject, checksum, cache every data source
    thermal   -- LST composite, TsHARP downscaling, validation
    surface   -- segmentation, plantable-space extraction
    impact    -- cooling kernel, shade raytrace, albedo model
    equity    -- dasymetric population, HVI, EWCB
    optimize  -- CELF greedy, CP-SAT/HiGHS, local search, efficient frontier
    narrate   -- Claude structured generation + numeric provenance guard
    verify    -- Wolfram cross-check
"""

__version__ = "0.1.0"
