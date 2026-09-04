"""Runs every ingest module in dependency order. `make ingest` calls this.

Idempotent and resumable (COOLBLOCK-BUILD-PLAN.md Phase 1 DoD): each
module's own `is_cached()` check means a re-run only fetches what's missing
or was invalidated. D9 and D7 depend on D8 having already resolved the
neighborhood's tract FIPS, so D8 runs first.
"""

from __future__ import annotations

import sys
import time
import traceback
from collections.abc import Callable

from engine.ingest import (
    d01_landsat,
    d02_sentinel2,
    d03_naip,
    d04_osm,
    d06_parcels,
    d07_census,
    d08_svi,
    d09_places,
    d10_tree_equity_score,
    d11_nlcd,
    d12_dem,
    d13_open_meteo,
    d14_nasa_power,
    d15_phoenix_open_data,
    d16_literature,
)

# D8 first: D7 and D9 key off the tract FIPS it resolves for the bbox.
# D5 (MS Building Footprints) is intentionally absent -- see docs/DATA-SOURCES.md.
MODULES: list[tuple[str, Callable[[], object]]] = [
    ("D8 CDC SVI", d08_svi.run),
    ("D4 OSM/Overpass", d04_osm.run),
    ("D6 Maricopa parcels", d06_parcels.run),
    ("D7 Census ACS5", d07_census.run),
    ("D9 CDC PLACES", d09_places.run),
    ("D10 Tree Equity Score", d10_tree_equity_score.run),
    ("D11 NLCD", d11_nlcd.run),
    ("D12 USGS 3DEP DEM", d12_dem.run),
    ("D13 Open-Meteo", d13_open_meteo.run),
    ("D14 NASA POWER", d14_nasa_power.run),
    ("D15 Phoenix Shade Plan", d15_phoenix_open_data.run),
    ("D16 Literature citations", d16_literature.run),
    ("D1 Landsat 8/9 L2", d01_landsat.run),
    ("D2 Sentinel-2 L2A", d02_sentinel2.run),
    ("D3 NAIP", d03_naip.run),
]


def main() -> int:
    failures = []
    for label, fn in MODULES:
        start = time.monotonic()
        print(f"==> {label}")
        try:
            fn()
        except Exception:
            print(f"    FAILED after {time.monotonic() - start:.1f}s", file=sys.stderr)
            traceback.print_exc()
            failures.append(label)
        else:
            print(f"    ok ({time.monotonic() - start:.1f}s)")

    if failures:
        print(f"\n{len(failures)} source(s) failed: {', '.join(failures)}", file=sys.stderr)
        return 1
    print(f"\nAll {len(MODULES)} sources cached.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
