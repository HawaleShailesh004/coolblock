"""Phase 7 -- the shared ARQ enqueue pool, created lazily on first use and
reused for the life of the process (one Redis connection pool, not one
per request)."""

from __future__ import annotations

import asyncio

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from coolblock_api.settings import get_settings

_pool: ArqRedis | None = None
_pool_lock = asyncio.Lock()


async def get_arq_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:
                _pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    return _pool


async def close_arq_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
