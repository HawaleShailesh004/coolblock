#!/usr/bin/env bash
# Self-hosts the map's glyph (font) and sprite assets that
# packages/map/src/basemapStyle.ts otherwise loaded live from
# protomaps.github.io -- a real gap found during Phase 13 hardening
# (docs/adr/0022-*.md): "offline demo mode... verified with the network
# throttled to zero" would fail on this today, silently dropping map
# labels and icons with no internet, even though the basemap tiles
# themselves are already self-hosted (scripts/build_basemap.sh).
#
# Small, one-time downloads (a few hundred KB total), not the full
# font/sprite catalog -- only the fontstacks the "black" theme
# (protomaps-themes-base) actually declares (Noto Sans Regular/Medium/
# Italic) and Unicode ranges 0-511 (Basic Latin, Latin-1 Supplement,
# Latin Extended-A), which cover this neighborhood's real label text
# (English street/park/POI names, with headroom for the odd accented
# proper noun).
#
# Requires: Docker Compose infra up (`make up`).
# Re-run if protomaps-themes-base's fontstacks ever change, or to widen
# Unicode range coverage for a different neighborhood/language.
set -euo pipefail

# A repo-relative scratch dir, not system mktemp -- on Windows, a Git-Bash
# `/tmp/...` path doesn't reliably translate into something Docker Desktop
# can bind-mount (a real failure hit running this script: the upload
# container saw an empty directory even though the files were really
# downloaded). A path under the repo is the same volume Docker Desktop
# already shares successfully for every other `-v` mount in this project.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$REPO_ROOT/.map_assets_tmp"
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT

ASSETS_BASE="https://protomaps.github.io/basemaps-assets"
FONTSTACKS=("Noto Sans Regular" "Noto Sans Medium" "Noto Sans Italic")
RANGES=("0-255" "256-511")

echo "==> Downloading glyphs (fonts)"
for stack in "${FONTSTACKS[@]}"; do
  mkdir -p "$TMP_DIR/glyphs/$stack"
  encoded_stack="${stack// /%20}"
  for range in "${RANGES[@]}"; do
    curl -sf "$ASSETS_BASE/fonts/$encoded_stack/$range.pbf" -o "$TMP_DIR/glyphs/$stack/$range.pbf"
  done
done

echo "==> Downloading sprite (black theme)"
mkdir -p "$TMP_DIR/sprites"
for suffix in "" "@2x"; do
  curl -sf "$ASSETS_BASE/sprites/v4/black$suffix.json" -o "$TMP_DIR/sprites/black$suffix.json"
  curl -sf "$ASSETS_BASE/sprites/v4/black$suffix.png" -o "$TMP_DIR/sprites/black$suffix.png"
done

echo "==> Uploading to MinIO (coolblock-tiles/glyphs, coolblock-tiles/sprites)"
# `docker run -v` needs a Windows-style path on Windows -- the plain
# Git-Bash POSIX path (e.g. /d/Hackathons/Next Steps/...) silently binds
# to nothing (a real failure hit running this script: the container saw
# an empty /upload even though the files existed on disk). `cygpath -w`
# is a no-op passthrough on real POSIX systems that lack it... except it
# doesn't exist there either, so only convert when it's actually available.
MOUNT_DIR="$TMP_DIR"
if command -v cygpath >/dev/null 2>&1; then
  MOUNT_DIR="$(cygpath -w "$TMP_DIR")"
fi
docker run --rm --network coolblock_default \
  -v "$MOUNT_DIR:/upload" \
  --entrypoint sh \
  minio/mc:latest \
  -c "mc alias set local http://minio:9000 \${S3_ACCESS_KEY_ID:-coolblock} \${S3_SECRET_ACCESS_KEY:-coolblock123} && mc cp -r /upload/glyphs local/coolblock-tiles/ && mc cp -r /upload/sprites local/coolblock-tiles/"

echo "==> Done -- verify: curl -I http://localhost:9000/coolblock-tiles/sprites/black.json"
