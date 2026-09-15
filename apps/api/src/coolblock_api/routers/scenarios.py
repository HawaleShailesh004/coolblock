"""Phase 7 -- `/plans/{plan_id}/scenarios`: list/read a plan's solve
history, export a scenario's sites (GeoJSON/CSV), and stream a running
solve's progress over SSE.

**The SSE reconnect contract** (COOLBLOCK-BUILD-PLAN.md §10 Phase 7 DoD:
"SSE reconnects cleanly on drop"): the client sends the sequence number of
the last event it already has via the `Last-Event-ID` header (browsers'
`EventSource` does this automatically on reconnect) or an `after` query
param for the first connection; the endpoint replays everything after
that from Redis's durable event list (`coolblock_api.jobs.events`) before
subscribing for whatever comes next. A client that never disconnects
just sees one continuous stream -- replay-then-subscribe is a superset of
the plain-subscribe case, not a special path for it.
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import uuid
from collections.abc import AsyncIterator
from typing import Literal

import anthropic
import groq
from engine.config import load_neighborhood_config
from engine.narrate.memo import build_memo_payload, generate_council_memo
from engine.optimize.plan_service import run_baseline_comparison
from engine.optimize.programs import DEFAULT_PROGRAM, DEFAULT_PUBLIC_LAND_ONLY
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from sqlalchemy import select
from sqlalchemy.orm import Session

from coolblock_api.db.base import get_db
from coolblock_api.db.models import Plan, ScenarioStatus, ScenarioVersion, Workspace
from coolblock_api.jobs.events import channel_key, replay_events_after
from coolblock_api.jobs.redis import get_redis
from coolblock_api.rate_limit import rate_limit
from coolblock_api.schemas import (
    MemoNumberOut,
    MemoOut,
    ScenarioSiteOut,
    ScenarioVersionDetailOut,
    ScenarioVersionOut,
)
from coolblock_api.workspace import get_current_workspace

router = APIRouter(prefix="/plans/{plan_id}/scenarios", tags=["scenarios"])

# A scenario's own solve rarely takes more than a few seconds (Phase 6
# DoD: <8s for the full neighborhood), but a stalled/crashed worker must
# not hold a client connection open forever.
SSE_IDLE_TIMEOUT_SECONDS = 120

# Poll interval for pubsub.get_message()'s own `timeout`, not the idle
# timeout above -- see the loop below for why this must be short.
SSE_POLL_INTERVAL_SECONDS = 1.0


def _get_scenario_or_404(db: Session, workspace: Workspace, plan_id: uuid.UUID, version: int) -> ScenarioVersion:
    scenario = db.execute(
        select(ScenarioVersion)
        .join(Plan, ScenarioVersion.plan_id == Plan.id)
        .where(
            ScenarioVersion.plan_id == plan_id,
            ScenarioVersion.version_number == version,
            Plan.workspace_id == workspace.id,
        )
    ).scalar_one_or_none()
    if scenario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "scenario version not found")
    return scenario


@router.get("", response_model=list[ScenarioVersionOut])
def list_scenarios(
    plan_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[ScenarioVersion]:
    return list(
        db.execute(
            select(ScenarioVersion)
            .join(Plan, ScenarioVersion.plan_id == Plan.id)
            .where(ScenarioVersion.plan_id == plan_id, Plan.workspace_id == workspace.id)
            .order_by(ScenarioVersion.version_number.desc())
        ).scalars()
    )


@router.get("/{version}", response_model=ScenarioVersionDetailOut)
def get_scenario(
    plan_id: uuid.UUID,
    version: int,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> ScenarioVersionDetailOut:
    scenario = _get_scenario_or_404(db, workspace, plan_id, version)
    return ScenarioVersionDetailOut(
        **ScenarioVersionOut.model_validate(scenario).model_dump(),
        sites=[
            ScenarioSiteOut(
                rank=s.rank,
                candidate_id=s.candidate_id,
                intervention_type=s.intervention_type,
                cost_usd=s.cost_usd,
                marginal_gain_ewcb=s.marginal_gain_ewcb,
                cumulative_ewcb=s.cumulative_ewcb,
                cumulative_cost_usd=s.cumulative_cost_usd,
                geometry=mapping(to_shape(s.geometry)),
                properties=s.properties,
            )
            for s in scenario.sites
        ],
    )


@router.get("/{version}/events")
async def stream_scenario_events(
    plan_id: uuid.UUID,
    version: int,
    request: Request,
    after: int = 0,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    scenario = _get_scenario_or_404(db, workspace, plan_id, version)
    if scenario.job_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "this scenario version was never solved via a job")
    job_id = scenario.job_id

    last_event_id_header = request.headers.get("last-event-id")
    after_seq = int(last_event_id_header) if last_event_id_header else after

    async def event_stream() -> AsyncIterator[str]:
        redis = get_redis()
        seq = after_seq

        # Subscribe *before* replaying the durable list -- closes the race
        # where an event is published between "read the list" and "start
        # listening," which would otherwise be silently missed by both.
        # Anything already in the list by replay time is delivered once
        # here; anything published after subscribe() is queued by the
        # client and picked up below (de-duplicated by the `seq` check).
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel_key(job_id))
        try:
            for envelope in await replay_events_after(redis, job_id, seq):
                seq = envelope.seq
                yield f"id: {envelope.seq}\nevent: {envelope.type}\ndata: {json.dumps(envelope.data)}\n\n"
                if envelope.type in ("done", "error"):
                    return

            # redis-py's `get_message(timeout=N)` does not reliably block
            # for the full N seconds: its *first* call right after
            # `subscribe()` consumes the subscribe-confirmation control
            # message Redis sends immediately, and -- because
            # `ignore_subscribe_messages=True` filters that message out --
            # returns `None` for that call almost instantly rather than
            # continuing to wait out the rest of the timeout budget for an
            # actual data message. Treating any single `None` as "nothing
            # is coming, give up" (the first version of this loop) closed
            # the stream within milliseconds of a real client connecting
            # before the solve had even started -- caught by a genuine
            # client (not curl, whose own process-start latency usually
            # let *something* land in the replay list first and masked
            # it), see docs/adr/0017-*.md's amendment. The fix: poll in
            # short (`SSE_POLL_INTERVAL_SECONDS`) increments, re-checking
            # disconnection each time, and only give up once that many
            # *consecutive* short polls -- not one single wait call -- have
            # come back empty.
            idle_seconds = 0.0
            while True:
                if await request.is_disconnected():
                    return
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=SSE_POLL_INTERVAL_SECONDS)
                if message is None:
                    idle_seconds += SSE_POLL_INTERVAL_SECONDS
                    if idle_seconds >= SSE_IDLE_TIMEOUT_SECONDS:
                        return  # idle timeout -- the client (or EventSource) is expected to reconnect with Last-Event-ID
                    continue
                idle_seconds = 0.0
                envelope_data = json.loads(message["data"])
                if envelope_data["seq"] <= seq:
                    continue  # already replayed above; a live publish can race the replay read
                seq = envelope_data["seq"]
                yield f"id: {envelope_data['seq']}\nevent: {envelope_data['type']}\ndata: {json.dumps(envelope_data['data'])}\n\n"
                if envelope_data["type"] in ("done", "error"):
                    return
        finally:
            await pubsub.unsubscribe(channel_key(job_id))
            # redis-py's PubSub.aclose has no type stub.
            await pubsub.aclose()  # type: ignore[no-untyped-call]

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{version}/baselines", response_model=dict[str, float])
async def compare_baselines(
    plan_id: uuid.UUID,
    version: int,
    workspace: Workspace = Depends(rate_limit("baselines", limit_per_minute=5)),
    db: Session = Depends(get_db),
) -> dict[str, float]:
    """§9 ★5: "we beat the alternatives." Runs CoolBlock's own CELF solve
    alongside the four real E5 baselines (`engine.optimize.baselines`) at
    this scenario's own plan's budget -- the same number the scenario
    itself was solved at, not a separately-entered one. Real cost
    (~15-20s, dominated by `worst_first`'s real LST-raster sample), run
    via a thread so it doesn't block the event loop for other requests
    while it computes; rate-limited (5/min/workspace) for the same reason
    the solve endpoint is."""
    scenario = _get_scenario_or_404(db, workspace, plan_id, version)
    program, public_land_only = _candidate_pool_of(scenario.plan)
    return await asyncio.to_thread(
        run_baseline_comparison, scenario.plan.budget_usd, program=program, public_land_only=public_land_only
    )


def _candidate_pool_of(plan: Plan) -> tuple[str, bool]:
    """The same pool the plan's own solve used (plans.py's `solve_plan`),
    so a baseline is never allowed to pick from candidates the plan
    couldn't (docs/adr/0027-*.md)."""
    constraints = plan.constraints or {}
    return (
        constraints.get("program", DEFAULT_PROGRAM),
        constraints.get("public_land_only", DEFAULT_PUBLIC_LAND_ONLY),
    )


@router.post("/{version}/memo", response_model=MemoOut)
async def generate_memo(
    plan_id: uuid.UUID,
    version: int,
    include_baselines: bool = False,
    provider: Literal["anthropic", "groq"] | None = None,
    workspace: Workspace = Depends(rate_limit("memo", limit_per_minute=3)),
    db: Session = Depends(get_db),
) -> MemoOut:
    """§7.1 L3/L6: the council memo, verified by the numeric provenance
    guard. A real API cost per call (and a second call if L6's guard has
    to trigger one regeneration) -- rate limited harder than
    solve/baselines for that reason, and never cached server-side: the
    frontend keeps one generated memo in its own state and only calls
    this again if the user explicitly asks for a new one.

    `provider` overrides `MEMO_LLM_PROVIDER` (env, default `"anthropic"`)
    for this one call -- `"anthropic"` (claude-opus-5, "quality, run
    once") or `"groq"` (openai/gpt-oss-120b, much faster; added when the
    Anthropic account's credit balance ran out mid-build,
    docs/adr/0019-*.md).

    `include_baselines=true` also runs the ~15-20s E5 comparison
    (`compare_baselines`, above) so the memo can include a real "how this
    compares to other approaches" section -- optional because it roughly
    doubles this endpoint's latency and isn't needed for the memo's core
    sections."""
    scenario = _get_scenario_or_404(db, workspace, plan_id, version)
    if scenario.status != ScenarioStatus.done:
        raise HTTPException(status.HTTP_409_CONFLICT, "the scenario must finish solving before a memo can be generated")

    plan = scenario.plan
    cfg = load_neighborhood_config()
    sites = [
        {
            "rank": s.rank,
            "candidate_id": s.candidate_id,
            "intervention_type": s.intervention_type,
            "cost_usd": s.cost_usd,
            "marginal_gain_ewcb": s.marginal_gain_ewcb,
            "cumulative_ewcb": s.cumulative_ewcb,
            "cumulative_cost_usd": s.cumulative_cost_usd,
        }
        for s in scenario.sites
    ]

    program, public_land_only = _candidate_pool_of(plan)
    baseline_comparison = None
    if include_baselines:
        baseline_comparison = await asyncio.to_thread(
            run_baseline_comparison, plan.budget_usd, program=program, public_land_only=public_land_only
        )

    payload = build_memo_payload(
        neighborhood_name=cfg.name,
        city=cfg.city,
        state=cfg.state,
        plan_name=plan.name,
        budget_usd=plan.budget_usd,
        solver=scenario.solver or "unknown",
        sites=sites,
        total_cost_usd=scenario.cost_usd or 0.0,
        total_ewcb=scenario.objective_value_ewcb or 0.0,
        baseline_comparison=baseline_comparison,
        program=program,
        public_land_only=public_land_only,
    )
    try:
        result = await asyncio.to_thread(generate_council_memo, payload, provider=provider)
    except (anthropic.APIError, groq.APIError) as exc:
        # A real, expected failure mode (rate limits, an exhausted credit
        # balance, a transient outage) -- surfaced as a clear 502 with the
        # SDK's own message, not an opaque 500 the client can't act on.
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"memo generation failed: {exc.message}") from exc
    return MemoOut(
        text=result.text,
        numbers=[
            MemoNumberOut(raw=n.raw, value=n.value, start=n.start, end=n.end, verified=n.verified, path=n.path)
            for n in result.numbers
        ],
        unverified_count=result.unverified_count,
        regenerated=result.regenerated,
    )


@router.get("/{version}/export.geojson")
def export_scenario_geojson(
    plan_id: uuid.UUID,
    version: int,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    scenario = _get_scenario_or_404(db, workspace, plan_id, version)
    features = [
        {
            "type": "Feature",
            "geometry": mapping(to_shape(s.geometry)),
            "properties": {
                "rank": s.rank,
                "candidate_id": s.candidate_id,
                "intervention_type": s.intervention_type,
                "cost_usd": s.cost_usd,
                "marginal_gain_ewcb": s.marginal_gain_ewcb,
                "cumulative_ewcb": s.cumulative_ewcb,
                "cumulative_cost_usd": s.cumulative_cost_usd,
                **s.properties,
            },
        }
        for s in scenario.sites
    ]
    return {"type": "FeatureCollection", "features": features}


@router.get("/{version}/export.csv")
def export_scenario_csv(
    plan_id: uuid.UUID,
    version: int,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    scenario = _get_scenario_or_404(db, workspace, plan_id, version)
    buffer = io.StringIO()
    fieldnames = [
        "rank",
        "candidate_id",
        "intervention_type",
        "cost_usd",
        "marginal_gain_ewcb",
        "cumulative_ewcb",
        "cumulative_cost_usd",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for s in scenario.sites:
        writer.writerow({field: getattr(s, field) for field in fieldnames})
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="plan-{plan_id}-v{version}.csv"'},
    )
