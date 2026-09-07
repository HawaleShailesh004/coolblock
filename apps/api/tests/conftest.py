"""Phase 7 -- test fixtures for `apps/api`.

Runs against a **real** Postgres and Redis (the same `docker-compose.yml`
containers every other part of this project uses), not a mock -- this
project's own posture (§1.1's "No-Fake Rule") is that a mocked DB is
exactly the kind of thing that lets a broken authz query pass a test
while still being broken in production. A dedicated `coolblock_test`
database (same instance, same extensions) keeps these tests from
clobbering whatever a developer is looking at in the real `coolblock`
database via `/map` or `db-shell`.

**`DATABASE_URL`/`REDIS_URL` must be overridden before `coolblock_api.db.base`
is ever imported** -- that module builds its SQLAlchemy engine from
`get_settings().database_url` at *module import time*, not per-call. This
file does that at the very top, before any `coolblock_api` import, which
is exactly why it has to happen in `conftest.py` (loaded by pytest before
test module collection) rather than inside a fixture.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

os.environ["DATABASE_URL"] = "postgresql+psycopg://coolblock:coolblock@localhost:5433/coolblock_test"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"  # a separate logical DB from dev's default 0, same instance

import psycopg  # noqa: E402
import pytest  # noqa: E402
import redis as sync_redis  # noqa: E402 -- a plain sync client for test cleanup only, see _clean_state
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402


def _ensure_test_database_exists() -> None:
    with psycopg.connect(
        "postgresql://coolblock:coolblock@localhost:5433/coolblock", autocommit=True
    ) as admin_conn:
        exists = admin_conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = 'coolblock_test'"
        ).fetchone()
        if not exists:
            admin_conn.execute("CREATE DATABASE coolblock_test")

    with psycopg.connect(
        "postgresql://coolblock:coolblock@localhost:5433/coolblock_test", autocommit=True
    ) as test_conn:
        for ext in ("postgis", "postgis_topology", "vector", "pg_trgm"):
            test_conn.execute(f"CREATE EXTENSION IF NOT EXISTS {ext}")


@pytest.fixture(scope="session", autouse=True)
def _test_database() -> None:
    _ensure_test_database_exists()
    from coolblock_api.db.base import Base, engine

    Base.metadata.create_all(engine)


@pytest.fixture(autouse=True)
def _clean_state() -> Iterator[None]:
    """Truncates every app table and flushes the (dedicated, db-index-1)
    test Redis before each test -- fast at this scale, and simpler (and
    more honest about what's actually being tested) than a
    nested-transaction/SAVEPOINT rollback scheme layered on top of code
    that calls `session.commit()` directly. The Redis flush matters as
    much as the truncate: rate-limit counters and ARQ's own queue keys
    are workspace/job scoped, not per-test, so a leftover counter from
    one test silently changes another's expected quota. Uses a plain
    synchronous `redis` client here, not `coolblock_api.jobs.redis.get_redis()`'s
    cached async one -- an `asyncio`-bound client reused across a fresh
    event loop per test would attach it to a different loop than it was
    created on, which `redis.asyncio` connections don't support."""
    from coolblock_api.db.base import Base, engine

    with engine.begin() as conn:
        table_names = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
        conn.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))
    yield
    sync_redis.Redis.from_url(os.environ["REDIS_URL"]).flushdb()


@pytest.fixture
def db() -> Iterator[Session]:
    from coolblock_api.db.base import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Iterator[TestClient]:
    from coolblock_api.main import app

    with TestClient(app) as test_client:
        yield test_client


def auth_headers(user_id: str = "alice", workspace_id: str = "org-a", role: str = "owner") -> dict[str, str]:
    return {"X-Dev-User-Id": user_id, "X-Dev-Workspace-Id": workspace_id, "X-Dev-Role": role}
