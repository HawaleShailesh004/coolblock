"""Phase 7 -- the ARQ worker (COOLBLOCK-BUILD-PLAN.md §10 Phase 7: "ARQ
workers + Redis; SSE progress streaming with named pipeline stages").

Run with `uv run arq coolblock_api.jobs.worker.WorkerSettings` from
`apps/api/`. One job type: `run_plan_solve`, which runs the real warm
solve (`engine.optimize.plan_service.stream_solve`), publishes each
stage/site/done event to Redis as it's produced
(`coolblock_api.jobs.events`), and persists the finished result (or the
error) to Postgres. The event-bridging (`thread_bridge.iterate_in_thread`)
is what lets a synchronous, CPU-bound generator publish incrementally
from inside this async task without blocking the worker's event loop for
the whole solve.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from arq.connections import RedisSettings
from engine.optimize.plan_service import DoneEvent, SiteEvent, SolveParams, stream_solve
from geoalchemy2.shape import from_shape
from shapely.geometry import shape

from coolblock_api.db.base import SessionLocal
from coolblock_api.db.models import ScenarioSite, ScenarioStatus, ScenarioVersion
from coolblock_api.jobs.events import error_envelope, publish_event, solve_event_to_envelope
from coolblock_api.jobs.thread_bridge import iterate_in_thread
from coolblock_api.settings import get_settings


def _set_scenario_status(scenario_version_id: str, **fields: Any) -> None:
    with SessionLocal() as db:
        scenario_version = db.get(ScenarioVersion, uuid.UUID(scenario_version_id))
        if scenario_version is None:
            return
        for key, value in fields.items():
            setattr(scenario_version, key, value)
        db.commit()


def _persist_result(
    scenario_version_id: str,
    solver: str,
    done: DoneEvent,
    sites: list[SiteEvent],
) -> None:
    with SessionLocal() as db:
        scenario_version = db.get(ScenarioVersion, uuid.UUID(scenario_version_id))
        if scenario_version is None:
            return
        scenario_version.status = ScenarioStatus.done
        scenario_version.solver = solver
        scenario_version.objective_value_ewcb = done.total_ewcb
        scenario_version.cost_usd = done.total_cost_usd
        scenario_version.completed_at = datetime.now(UTC)
        for site in sites:
            db.add(
                ScenarioSite(
                    scenario_version_id=scenario_version.id,
                    rank=site.rank,
                    candidate_id=site.candidate_id,
                    intervention_type=site.intervention_type,
                    cost_usd=site.cost_usd,
                    marginal_gain_ewcb=site.marginal_gain_ewcb,
                    cumulative_ewcb=site.cumulative_ewcb,
                    cumulative_cost_usd=site.cumulative_cost_usd,
                    geometry=from_shape(shape(site.geometry), srid=4326),
                    properties=site.properties,
                )
            )
        db.commit()


async def run_plan_solve(ctx: dict[str, Any], scenario_version_id: str, params: SolveParams) -> dict[str, Any]:
    redis = ctx["redis"]
    job_id = str(ctx["job_id"])

    await asyncio.to_thread(
        _set_scenario_status, scenario_version_id, status=ScenarioStatus.running, job_id=job_id
    )

    seq = 0
    sites: list[SiteEvent] = []
    done: DoneEvent | None = None
    try:
        async for event in iterate_in_thread(lambda: stream_solve(params)):
            seq += 1
            await publish_event(redis, job_id, solve_event_to_envelope(event, seq))
            if isinstance(event, SiteEvent):
                sites.append(event)
            elif isinstance(event, DoneEvent):
                done = event
    except Exception as exc:  # noqa: BLE001 -- deliberately broad: every failure must reach the client as a real SSE error event, not vanish into the worker's own log
        seq += 1
        await publish_event(redis, job_id, error_envelope(seq, str(exc)))
        await asyncio.to_thread(
            _set_scenario_status,
            scenario_version_id,
            status=ScenarioStatus.error,
            error_message=str(exc),
            completed_at=datetime.now(UTC),
        )
        raise

    assert done is not None, "stream_solve always yields exactly one DoneEvent as its last event"
    await asyncio.to_thread(_persist_result, scenario_version_id, done.solver, done, sites)
    return {"n_sites": done.n_sites, "total_cost_usd": done.total_cost_usd, "total_ewcb": done.total_ewcb}


class WorkerSettings:
    functions = [run_plan_solve]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    job_timeout = 300  # a full-neighborhood solve is measured at a few seconds (Phase 6 DoD: <8s) -- this is generous headroom, not a tuned budget
    poll_delay = get_settings().arq_poll_delay_s  # see Settings.arq_poll_delay_s -- tuned up in production against a request-metered Redis
