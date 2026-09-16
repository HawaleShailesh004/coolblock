#!/usr/bin/env bash
# Runs both processes this app needs (docs/DEPLOYMENT.md) in the one process
# slot a free-tier host gives a single service: the FastAPI server (what the
# host's health check and the browser actually talk to) and the ARQ worker
# (what actually runs a solve -- without it, the API answers every request
# except "run the optimizer," which fails silently until someone notices).
#
# `wait -n` exits this script the moment EITHER process exits, so a crashed
# worker takes the whole container down with it rather than leaving a
# half-working API that looks healthy. The host's own restart policy is what
# actually recovers from that -- this script's job is only to make the
# failure visible and total, not partial and silent.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

# Plain venv binaries, not `uv run` -- `uv sync --frozen` already built the
# exact right environment at image-build time (Dockerfile), so there is
# nothing left for `uv run`'s own re-sync-on-every-invocation behavior to
# usefully do here. Confirmed by actually hitting this: two `uv run`
# invocations started seconds apart (arq, then uvicorn) each triggered a
# `Building coolblock-api / coolblock-engine` resync of the local packages,
# and racing that against each other during container start intermittently
# broke rasterio's import (`libexpat.so.1: cannot open shared object file`)
# even with the library actually present -- gone entirely once both
# processes below use the already-built venv directly instead.
echo "==> Applying Postgres migrations"
alembic upgrade head

echo "==> Starting ARQ worker"
arq coolblock_api.jobs.worker.WorkerSettings &
WORKER_PID=$!

echo "==> Starting API on port ${PORT:-8000}"
uvicorn coolblock_api.main:app --host 0.0.0.0 --port "${PORT:-8000}" &
API_PID=$!

trap 'kill "$WORKER_PID" "$API_PID" 2>/dev/null || true' EXIT INT TERM
wait -n "$WORKER_PID" "$API_PID"
