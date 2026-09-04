"""FastAPI entrypoint. `uvicorn coolblock_api.main:app --reload` from apps/api/.

Phase 0 scope: app boots, /health reports real config state (not a stub value).
The plans/scenarios/sites/exports surface is Phase 7.
"""

from __future__ import annotations

from engine.config import load_neighborhood_config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="CoolBlock API",
    description="Block-scale heat-mitigation siting optimizer.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    cfg = load_neighborhood_config()
    return {
        "status": "ok",
        "neighborhood": cfg.id,
        "city": cfg.city,
        "target_crs": f"EPSG:{cfg.target_epsg}",
    }
