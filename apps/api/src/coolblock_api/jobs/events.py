"""Phase 7 -- the SSE event envelope and its Redis transport (COOLBLOCK-BUILD-PLAN.md
§10 Phase 7: "ARQ workers + Redis; SSE progress streaming with named
pipeline stages").

**Why a Redis list *and* a pubsub channel, not just pubsub.** Pure pubsub
loses every message published before a subscriber connects, and loses
anything published during a dropped connection -- which is exactly the
"SSE reconnects cleanly on drop" DoD requirement this phase has to meet.
So every event is (1) `RPUSH`ed onto a durable, sequence-numbered list
(`job:{id}:events`) *and* (2) published on `job:{id}:channel` for anyone
already listening. A client (re)connecting sends `Last-Event-ID` (or
`?after=`); the SSE endpoint replays everything after that sequence
number from the list, then subscribes to the channel for whatever arrives
next -- no gap, no duplicate delivery of anything the client already has.

Each envelope is one JSON object: `{"seq": int, "type": "stage"|"site"|"done"|"error", "data": {...}}`.
`engine.optimize.plan_service`'s dataclasses (`StageEvent`/`SiteEvent`/`DoneEvent`)
are converted to this shape here, at the one place `engine`'s plain-dataclass
output meets this app's JSON/Redis boundary.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Any, Literal, cast

from engine.optimize.plan_service import SiteEvent, SolveEvent, StageEvent
from redis.asyncio import Redis

EVENT_TTL_SECONDS = 60 * 60  # a finished job's event log survives an hour -- long enough to reconnect after a real network blip, short enough not to accumulate forever

EventType = Literal["stage", "site", "done", "error"]


@dataclass(frozen=True)
class EventEnvelope:
    seq: int
    type: EventType
    data: dict[str, Any]

    def to_json(self) -> str:
        return json.dumps(dataclasses.asdict(self))

    @staticmethod
    def from_json(raw: str) -> EventEnvelope:
        obj = json.loads(raw)
        return EventEnvelope(seq=obj["seq"], type=obj["type"], data=obj["data"])


def _event_type(event: SolveEvent) -> EventType:
    if isinstance(event, StageEvent):
        return "stage"
    if isinstance(event, SiteEvent):
        return "site"
    return "done"


def solve_event_to_envelope(event: SolveEvent, seq: int) -> EventEnvelope:
    return EventEnvelope(seq=seq, type=_event_type(event), data=dataclasses.asdict(event))


def error_envelope(seq: int, message: str) -> EventEnvelope:
    return EventEnvelope(seq=seq, type="error", data={"message": message})


def events_key(job_id: str) -> str:
    return f"job:{job_id}:events"


def channel_key(job_id: str) -> str:
    return f"job:{job_id}:channel"


async def publish_event(redis: Redis, job_id: str, envelope: EventEnvelope) -> None:
    """Durably records the event (for replay) and notifies anyone
    currently subscribed (for the live/no-reconnect case) -- in that
    order, so a subscriber woken by the publish can immediately find the
    event already in the list if it re-reads from there."""
    payload = envelope.to_json()
    key = events_key(job_id)
    async with redis.pipeline(transaction=True) as pipe:
        pipe.rpush(key, payload)
        pipe.expire(key, EVENT_TTL_SECONDS)
        await pipe.execute()
    await redis.publish(channel_key(job_id), payload)


async def replay_events_after(redis: Redis, job_id: str, after_seq: int) -> list[EventEnvelope]:
    # redis-py's stubs share one return-type alias (`Awaitable[T] | T`)
    # between the sync and async clients; `redis` here is always the async
    # one, so the `Awaitable` branch is the only one that's ever real.
    raw_events = await cast("Awaitable[list[str]]", redis.lrange(events_key(job_id), 0, -1))
    envelopes = [EventEnvelope.from_json(raw) for raw in raw_events]
    return [e for e in envelopes if e.seq > after_seq]
