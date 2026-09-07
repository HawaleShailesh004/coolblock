"""Phase 7 -- structured request logging + request tracing
(COOLBLOCK-BUILD-PLAN.md §10 Phase 7: "Rate limiting, request tracing,
structured logging, Sentry"). One request id per request, propagated to
every structlog call made while handling it (via contextvars) and echoed
back in the `X-Request-Id` response header so a client-reported issue can
be matched to a specific log line."""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger("coolblock_api.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        start = time.perf_counter()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round((time.perf_counter() - start) * 1000, 2),
            )
            raise
        finally:
            structlog.contextvars.clear_contextvars()

        response.headers["x-request-id"] = request_id
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )
        return response


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
    )
