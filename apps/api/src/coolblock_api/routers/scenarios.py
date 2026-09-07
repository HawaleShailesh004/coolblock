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

import csv
import io
import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from sqlalchemy import select
from sqlalchemy.orm import Session

from coolblock_api.db.base import get_db
from coolblock_api.db.models import Plan, ScenarioVersion, Workspace
from coolblock_api.jobs.events import channel_key, replay_events_after
from coolblock_api.jobs.redis import get_redis
from coolblock_api.schemas import ScenarioSiteOut, ScenarioVersionDetailOut, ScenarioVersionOut
from coolblock_api.workspace import get_current_workspace

router = APIRouter(prefix="/plans/{plan_id}/scenarios", tags=["scenarios"])

# A scenario's own solve rarely takes more than a few seconds (Phase 6
# DoD: <8s for the full neighborhood), but a stalled/crashed worker must
# not hold a client connection open forever.
SSE_IDLE_TIMEOUT_SECONDS = 120


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

            while True:
                if await request.is_disconnected():
                    return
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=SSE_IDLE_TIMEOUT_SECONDS)
                if message is None:
                    return  # idle timeout -- the client (or EventSource) is expected to reconnect with Last-Event-ID
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
