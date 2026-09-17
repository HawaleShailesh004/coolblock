#!/usr/bin/env bash
# Runs this image's process(es), selected by $PROCESS_ROLE
# (docs/adr/0034-*.md). Three modes:
#
#   PROCESS_ROLE=api     Migrations + the FastAPI server alone.
#   PROCESS_ROLE=worker  The ARQ worker alone, no migrations, no port.
#   (unset / "both")     Both together, one container -- the ORIGINAL
#                        design (docs/adr/0031-*.md), kept for local
#                        `docker run` convenience only. **Do not use this
#                        mode on Render's free tier**: a real production
#                        deploy in this mode crash-looped every few
#                        minutes under an actual solve's memory load (a
#                        single API process alone was already measured at
#                        392 MB RSS against a 512 MB limit; running the
#                        ARQ worker in the same process space pushed it
#                        over during real requests, not just at boot).
#                        Deploy `api` and `worker` as two separate Render
#                        services instead -- docs/DEPLOYMENT.md.
#
# Plain venv binaries, not `uv run`, in every mode -- `uv sync --frozen`
# already built the exact right environment at image-build time
# (Dockerfile), so there is nothing left for `uv run`'s own
# resync-on-every-invocation to usefully do here. Confirmed by actually
# hitting this: two `uv run` invocations started seconds apart (arq, then
# uvicorn) each triggered a `Building coolblock-api / coolblock-engine`
# resync of the local packages, and racing that against each other during
# container start intermittently broke rasterio's import
# (`libexpat.so.1: cannot open shared object file`) even with the library
# actually present -- gone entirely once every process here uses the
# already-built venv directly instead.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

ROLE="${PROCESS_ROLE:-both}"

if [[ "$ROLE" == "api" || "$ROLE" == "both" ]]; then
  echo "==> Applying Postgres migrations"
  alembic upgrade head
fi

case "$ROLE" in
  api)
    echo "==> Starting API on port ${PORT:-8000}"
    exec uvicorn coolblock_api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
    ;;
  worker)
    echo "==> Starting ARQ worker"
    exec arq coolblock_api.jobs.worker.WorkerSettings
    ;;
  both)
    # `wait -n` exits this script the moment EITHER process exits, so a
    # crashed worker takes the whole container down with it rather than
    # leaving a half-working API that looks healthy. The host's own
    # restart policy is what actually recovers from that -- this script's
    # job is only to make the failure visible and total, not partial and
    # silent.
    echo "==> Starting ARQ worker"
    arq coolblock_api.jobs.worker.WorkerSettings &
    WORKER_PID=$!

    echo "==> Starting API on port ${PORT:-8000}"
    uvicorn coolblock_api.main:app --host 0.0.0.0 --port "${PORT:-8000}" &
    API_PID=$!

    trap 'kill "$WORKER_PID" "$API_PID" 2>/dev/null || true' EXIT INT TERM
    wait -n "$WORKER_PID" "$API_PID"
    ;;
  *)
    echo "Unknown PROCESS_ROLE: $ROLE (expected api, worker, or both)" >&2
    exit 1
    ;;
esac
