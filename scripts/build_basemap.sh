#!/usr/bin/env bash
# Extracts a neighborhood-scoped Protomaps basemap (Phase 2, §3.3 "Protomaps +
# PMTiles on R2") and uploads it to the local MinIO stand-in. Self-hosted,
# free, bespoke: a couple of MB pulled via HTTP range requests from
# Protomaps' public 120GB daily planet build, not a 120GB download.
#
# Requires: go-pmtiles (`go install github.com/protomaps/go-pmtiles@latest`),
# Docker Compose infra up (`make up`).
#
# Re-run whenever the locked neighborhood bbox changes, or to refresh to a
# newer daily build.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$REPO_ROOT/data/derived/edison-eastlake"
OUT_FILE="$OUT_DIR/basemap.pmtiles"

# A recent Protomaps daily build (https://maps.protomaps.com/builds/). Pin a
# working date here rather than "latest" -- builds occasionally 404 for a day.
BUILD_DATE="${PROTOMAPS_BUILD_DATE:-20260904}"
SOURCE_URL="https://build.protomaps.com/${BUILD_DATE}.pmtiles"

# Locked bbox (config/neighborhood.toml) plus a buffer so panning slightly
# outside the neighborhood isn't blank.
BBOX="-112.09,33.43,-112.02,33.48"

PMTILES_BIN="${PMTILES_BIN:-go-pmtiles}"
if ! command -v "$PMTILES_BIN" >/dev/null 2>&1; then
  echo "go-pmtiles not found. Install: go install github.com/protomaps/go-pmtiles@latest" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
echo "==> Extracting bbox $BBOX from $SOURCE_URL"
"$PMTILES_BIN" extract "$SOURCE_URL" "$OUT_FILE" --bbox="$BBOX" --maxzoom=16

echo "==> Uploading to MinIO (coolblock-tiles/basemap.pmtiles)"
docker run --rm --network coolblock_default \
  -v "$OUT_DIR:/upload" \
  --entrypoint sh \
  minio/mc:latest \
  -c "mc alias set local http://minio:9000 \${S3_ACCESS_KEY_ID:-coolblock} \${S3_SECRET_ACCESS_KEY:-coolblock123} && mc cp /upload/basemap.pmtiles local/coolblock-tiles/basemap.pmtiles"

echo "==> Done: $OUT_FILE"
