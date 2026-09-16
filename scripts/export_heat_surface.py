"""Exports the Phase 3 downscaled heat surface as a Cloud-Optimized GeoTIFF
and uploads it to MinIO (the R2 stand-in) for TiTiler to serve.

COOLBLOCK-BUILD-PLAN.md §10 Phase 3: "Export to COG -> R2 -> TiTiler; a
HeatSurfaceLayer in packages/map." A one-off script, same pattern as
scripts/export_map_layers.py -- re-run whenever the downscaling model
changes.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from engine.ingest.grid import get_canonical_grid
from engine.thermal.downscale import run_downscaling
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "data" / "derived" / "edison-eastlake"
NODATA = -9999.0
BUCKET = "coolblock-data"

FloatArray = np.ndarray[Any, np.dtype[np.float64]]


def _write_cog(data: FloatArray, out_path: Path) -> None:
    grid = get_canonical_grid()
    filled = np.where(np.isfinite(data), data, NODATA).astype("float32")

    src_profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": grid.width,
        "height": grid.height,
        "count": 1,
        "crs": f"EPSG:{grid.epsg}",
        "transform": grid.transform,
        "nodata": NODATA,
    }
    tmp_path = out_path.with_suffix(".tmp.tif")
    with rasterio.open(tmp_path, "w", **src_profile) as dst:
        dst.write(filled, 1)

    # rio-cogeo ships no stubs; its profile dict is plain JSON-ish data.
    cog_profile: dict[str, Any] = cog_profiles.get("deflate")  # type: ignore[no-untyped-call]
    with rasterio.open(tmp_path) as src:
        cog_translate(src, out_path, cog_profile, in_memory=False, quiet=True)
    tmp_path.unlink()


def upload_to_minio(local_path: Path, bucket: str) -> None:
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "coolblock_default",
            "-v",
            f"{local_path.parent}:/upload",
            "--entrypoint",
            "sh",
            "minio/mc:latest",
            "-c",
            f"mc alias set local http://minio:9000 coolblock coolblock123 && "
            f"mc mb -p local/{bucket} && "
            f"mc cp /upload/{local_path.name} local/{bucket}/{local_path.name}",
        ],
        check=True,
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Running the downscaling model...")
    result = run_downscaling()

    lst_path = OUT_DIR / "heat_surface_lst.tif"
    unc_path = OUT_DIR / "heat_surface_uncertainty.tif"
    _write_cog(result.lst_10m.values, lst_path)
    _write_cog(result.uncertainty_10m.values, unc_path)
    print(f"Wrote {lst_path} ({lst_path.stat().st_size / 1024:.0f} KB)")
    print(f"Wrote {unc_path} ({unc_path.stat().st_size / 1024:.0f} KB)")

    print(f"Uploading to MinIO bucket '{BUCKET}'...")
    upload_to_minio(lst_path, BUCKET)
    upload_to_minio(unc_path, BUCKET)
    print("Done.")


if __name__ == "__main__":
    main()
