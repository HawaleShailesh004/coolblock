"""FastAPI entrypoint. `uvicorn coolblock_api.main:app --reload` from apps/api/.

Phase 7 (COOLBLOCK-BUILD-PLAN.md §10): the real product surface --
plans/scenarios/sites/constraints/exports/share-links, backed by Postgres
(`coolblock_api.db`), Clerk-or-dev-header auth (`coolblock_api.auth`), and
an ARQ+Redis job queue with SSE progress streaming
(`coolblock_api.jobs`). See `docs/adr/0016-*.md` (auth) and
`docs/adr/0017-*.md` (schema/jobs) for the design decisions.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from engine.config import load_neighborhood_config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from coolblock_api.jobs.pool import close_arq_pool, get_arq_pool
from coolblock_api.logging_middleware import RequestLoggingMiddleware, configure_logging
from coolblock_api.routers import annotations as annotations_router
from coolblock_api.routers import plans, scenarios, share
from coolblock_api.settings import get_settings

configure_logging()

settings = get_settings()
if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment, traces_sample_rate=0.1)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await get_arq_pool()  # fail fast on a bad REDIS_URL at boot, not on the first solve request
    yield
    await close_arq_pool()


app = FastAPI(
    title="CoolBlock API",
    description="Block-scale heat-mitigation siting optimizer.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(plans.router)
app.include_router(scenarios.router)
app.include_router(annotations_router.router)
app.include_router(share.plan_scoped_router)
app.include_router(share.public_router)


@app.get("/health")
def health() -> dict[str, str]:
    cfg = load_neighborhood_config()
    return {
        "status": "ok",
        "neighborhood": cfg.id,
        "city": cfg.city,
        "target_crs": f"EPSG:{cfg.target_epsg}",
    }
