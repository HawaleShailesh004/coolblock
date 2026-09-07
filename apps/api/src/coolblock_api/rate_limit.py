"""Phase 7 -- rate limiting (COOLBLOCK-BUILD-PLAN.md §10 Phase 7: "Rate
limiting, request tracing, structured logging, Sentry"). A real solve
enqueues an ARQ job and runs actual geopandas/numpy computation -- the
one endpoint in this API where a client hammering it costs real CPU, so
it's the one this phase actually rate-limits, per-workspace, not
globally (one noisy workspace shouldn't throttle every other one).

Fixed-window counter in Redis: `INCR` a key scoped to
`(bucket, workspace_id, current_minute)`, `EXPIRE` it once, reject once
the count exceeds the limit for that minute. A fixed window admits a
short burst right at the window boundary (the well-known tradeoff against
a sliding-window/token-bucket implementation) -- an accepted simplicity
tradeoff for a single rate-limited endpoint at hackathon scope, not
presented as a sliding-window guarantee it doesn't provide.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, status

from coolblock_api.db.models import Workspace
from coolblock_api.jobs.redis import get_redis
from coolblock_api.settings import get_settings
from coolblock_api.workspace import get_current_workspace


def rate_limit(bucket: str, limit_per_minute: int | None = None) -> Callable[[Workspace], Awaitable[Workspace]]:
    async def _dependency(workspace: Workspace = Depends(get_current_workspace)) -> Workspace:
        settings = get_settings()
        limit = limit_per_minute if limit_per_minute is not None else settings.solve_rate_limit_per_minute
        window = int(time.time() // 60)
        key = f"ratelimit:{bucket}:{workspace.id}:{window}"

        redis = get_redis()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)
        if count > limit:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"rate limit exceeded: {limit}/min for {bucket!r} in this workspace",
            )
        return workspace

    return _dependency
