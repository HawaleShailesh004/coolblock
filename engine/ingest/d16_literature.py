"""D16 -- Literature corpus (COOLBLOCK-BUILD-PLAN.md §5 data contract).

The five papers cited in outputs/nextstep-2026-strategy-brief.md, plus city
planning documents, chunked into pgvector for grounded citation in the
council memo (§7.1 L3). Phase 1 scope is registering the citation list with
its provenance -- manual PDF acquisition (mixed publisher access, some
paywalled) and the chunk/embed pipeline are Phase 10 work
(engine.narrate), not automatable ingest like D1-D15.
"""

from __future__ import annotations

from pathlib import Path

from engine.ingest.manifest import is_cached, version_dir, write_manifest

SOURCE_ID = "literature"
VERSION = "2026-09-04"
LICENSE = "Mixed -- see per-entry `license` field; academic publishers, fair use for citation"

PAPERS = [
    {
        "title": (
            "The tree cover and temperature disparity in US urbanized areas: "
            "Quantifying the association with income across 5,723 communities"
        ),
        "venue": "PLOS ONE",
        "doi": "10.1371/journal.pone.0249715",
        "used_for": "4.0 degC / 30%-less-canopy disparity figures for low-income blocks",
        "license": "CC BY 4.0",
    },
    {
        "title": (
            "Trees halve urban heat island effect globally but unequal benefits "
            "only modestly mitigate climate-change warming"
        ),
        "venue": "Nature Communications",
        "doi": "10.1038/s41467-026-71825-x",
        "used_for": "cooling benefits accrue disproportionately to higher incomes/suburbs",
        "license": "CC BY 4.0 (dataset mirrored on Dryad, doi:10.5061/dryad.905qfttz0)",
    },
    {
        "title": "Increasing tree canopy lowers urban air temperature by up to 1.5 degC in heat-prone areas",
        "venue": "npj Urban Sustainability",
        "doi": "10.1038/s42949-025-00277-x",
        "used_for": "the canopy-increment -> degrees relationship behind the cooling kernel (§6.3 C1)",
        "license": "CC BY 4.0",
    },
    {
        "title": "Street trees provide an opportunity to mitigate urban heat and reduce risk of high heat exposure",
        "venue": "Scientific Reports",
        "doi": "10.1038/s41598-024-51921-y",
        "used_for": "shade/exposure framing for the equity-weighted objective (§6.4)",
        "license": "CC BY 4.0",
    },
    {
        "title": "Urban Heat Equity",
        "venue": "American Forests / Tree Equity Score",
        "doi": None,
        "url": "https://www.treeequityscore.org/stories/urban-heat-equity",
        "used_for": "the 62-million-tree gap and 92%-of-cities findings",
        "license": "See publisher terms",
    },
]

CITY_PLANS = [
    {
        "title": "Phoenix Tree and Shade Master Plan",
        "publisher": "City of Phoenix Office of Heat Response and Mitigation",
        "used_for": "the 25% canopy-by-2030 goal referenced throughout the plan",
    },
]


def run(force: bool = False) -> Path:
    if not force and is_cached(SOURCE_ID, VERSION):
        return version_dir(SOURCE_ID, VERSION)

    vdir = version_dir(SOURCE_ID, VERSION)
    vdir.mkdir(parents=True, exist_ok=True)

    import json

    out_path = vdir / "citations.json"
    with open(out_path, "w") as f:
        json.dump({"papers": PAPERS, "city_plans": CITY_PLANS}, f, indent=2)

    write_manifest(
        source=SOURCE_ID,
        version=VERSION,
        url="outputs/nextstep-2026-strategy-brief.md",
        license=LICENSE,
        files=[out_path],
        bbox_wgs84=None,
        extra={
            "paper_count": len(PAPERS),
            "note": "citation list only -- PDF acquisition and pgvector chunking are Phase 10 work",
        },
    )
    return vdir


if __name__ == "__main__":
    result_dir = run()
    print(f"literature citations registered at {result_dir}")
