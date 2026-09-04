#!/usr/bin/env bash
# Runs the API dev server alongside the JS dev servers (`pnpm turbo run dev`
# only touches JS workspaces -- it has no idea apps/api exists). Ctrl-C stops
# both.
set -euo pipefail

API_PORT="${API_PORT:-8000}"

cleanup() {
  if [[ -n "${API_PID:-}" ]] && kill -0 "$API_PID" 2>/dev/null; then
    kill "$API_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

uv run uvicorn coolblock_api.main:app --app-dir apps/api/src --reload --port "$API_PORT" &
API_PID=$!
echo "API dev server: http://localhost:${API_PORT} (pid $API_PID)"

pnpm turbo run dev
