"""The manifest + checksum system (COOLBLOCK-BUILD-PLAN.md §5.1.1).

Every fetch writes to `data/cache/<source>/<version>/manifest.json` carrying
URL, timestamp, bbox, checksum, and licence. Nothing re-fetches silently --
`is_cached()` is the idempotency check every ingest module's `cache()` calls
before hitting the network, which is what makes `make ingest` resumable.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from engine.config import REPO_ROOT

CACHE_ROOT = REPO_ROOT / "data" / "cache"
MANIFEST_FILENAME = "manifest.json"


@dataclass(frozen=True)
class FileRecord:
    path: str  # relative to the version directory
    sha256: str
    bytes: int


@dataclass(frozen=True)
class Manifest:
    source: str
    version: str
    fetched_at: str
    url: str
    license: str
    bbox_wgs84: tuple[float, float, float, float] | None
    files: list[FileRecord]
    extra: dict[str, Any] = field(default_factory=dict)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def version_dir(source: str, version: str) -> Path:
    return CACHE_ROOT / source / version


def manifest_path(source: str, version: str) -> Path:
    return version_dir(source, version) / MANIFEST_FILENAME


def write_manifest(
    *,
    source: str,
    version: str,
    url: str,
    license: str,
    files: list[Path],
    bbox_wgs84: tuple[float, float, float, float] | None = None,
    extra: dict[str, Any] | None = None,
) -> Manifest:
    vdir = version_dir(source, version)
    records = [
        FileRecord(path=str(p.relative_to(vdir)), sha256=sha256_file(p), bytes=p.stat().st_size)
        for p in files
    ]
    manifest = Manifest(
        source=source,
        version=version,
        fetched_at=datetime.now(UTC).isoformat(),
        url=url,
        license=license,
        bbox_wgs84=bbox_wgs84,
        files=records,
        extra=extra or {},
    )
    vdir.mkdir(parents=True, exist_ok=True)
    with open(manifest_path(source, version), "w") as f:
        json.dump(asdict(manifest), f, indent=2, sort_keys=True)
    return manifest


def read_manifest(source: str, version: str) -> Manifest | None:
    p = manifest_path(source, version)
    if not p.exists():
        return None
    with open(p) as f:
        raw = json.load(f)
    raw["files"] = [FileRecord(**r) for r in raw["files"]]
    return Manifest(**raw)


def is_cached(source: str, version: str) -> bool:
    """True iff a manifest exists and every file it lists is present with a matching checksum."""
    manifest = read_manifest(source, version)
    if manifest is None:
        return False
    vdir = version_dir(source, version)
    for record in manifest.files:
        fpath = vdir / record.path
        if not fpath.exists():
            return False
        if sha256_file(fpath) != record.sha256:
            return False
    return True
