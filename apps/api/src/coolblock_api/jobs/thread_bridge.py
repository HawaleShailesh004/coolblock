"""Phase 7 -- bridges a plain synchronous generator (CPU-bound geopandas/
numpy work, `engine.optimize.plan_service.stream_solve`) into an async
iterator, so the ARQ worker can `await` each item and publish it to Redis
the moment it's produced, without blocking the worker's event loop for
the whole solve.

Runs the generator in a real background thread -- not
`asyncio.to_thread(list, generator)`, which would run it to completion
before yielding anything back, defeating the entire point of a live,
incremental SSE stream (§9 ★2: "the algorithm genuinely emits sites in
that order," not a batch result reshaped into fake progress after the
fact)."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator, Callable, Iterator
from typing import TypeVar

T = TypeVar("T")

_SENTINEL = object()


async def iterate_in_thread(make_generator: Callable[[], Iterator[T]]) -> AsyncIterator[T]:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[object] = asyncio.Queue()

    def _run() -> None:
        try:
            for item in make_generator():
                loop.call_soon_threadsafe(queue.put_nowait, item)
        except Exception as exc:  # noqa: BLE001 -- deliberately broad: forwarded to the async side, not swallowed
            loop.call_soon_threadsafe(queue.put_nowait, exc)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, _SENTINEL)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    while True:
        item = await queue.get()
        if item is _SENTINEL:
            return
        if isinstance(item, Exception):
            raise item
        yield item  # type: ignore[misc]
