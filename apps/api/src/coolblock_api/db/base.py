"""Phase 7 -- SQLAlchemy engine/session setup against the real
Postgres 16 + PostGIS + pgvector container from `docker-compose.yml`
(`coolblock_api.settings.Settings.database_url`)."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from coolblock_api.settings import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True, future=True)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
