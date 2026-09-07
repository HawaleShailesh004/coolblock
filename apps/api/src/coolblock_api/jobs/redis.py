"""Phase 7 -- an async Redis client, cached per event loop rather than
process-wide.

**Why per-loop, not a single global singleton.** `redis.asyncio`
connections are bound to the event loop they were first used on; reusing
one client object across two different loops (in this app: a single long-
running loop in production, but *at least two* in tests -- the
`TestClient`'s own internal loop, run via an anyio portal in a background
thread, and `pytest-asyncio`'s per-test loop) doesn't cleanly raise, it
can hang indefinitely waiting on a future tied to a loop that never runs
it. That failure mode is exactly what caused `apps/api/tests` to hang
during Phase 7 development -- this module is the fix, not a workaround
bolted onto the tests. In production there is only ever one running
loop for the process's lifetime, so this is a single cached client there,
identical in effect to the plain-singleton version it replaced.
"""

from __future__ import annotations

import asyncio
from typing import cast

from redis.asyncio import Redis

from coolblock_api.settings import get_settings

_clients_by_loop: dict[int, Redis] = {}


def get_redis() -> Redis:
    loop = asyncio.get_running_loop()
    key = id(loop)
    if key not in _clients_by_loop:
        _clients_by_loop[key] = cast(Redis, Redis.from_url(get_settings().redis_url, decode_responses=True))
    return _clients_by_loop[key]
