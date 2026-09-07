"""Phase 7 -- the persistence schema (COOLBLOCK-BUILD-PLAN.md §10 Phase 7):
"Postgres schema: workspaces, users, plans, scenario versions, annotations,
audit log."

Design notes, recorded in full in `docs/adr/0017-*.md`:

- **UUID primary keys, generated in Python (`uuid.uuid4`), not server-side.**
  The Postgres extensions actually installed here (`infra/postgres/init/001_extensions.sql`:
  `postgis`, `postgis_topology`, `pgvector`, `pg_trgm`) do not include
  `pgcrypto`/`uuid-ossp`, and adding one for this alone isn't worth a new
  infra dependency when Python-side generation is just as correct.
- **`ScenarioSite` is a real table with a PostGIS geometry column**
  (`geoalchemy2.Geometry`), not a JSON blob on `ScenarioVersion`. A solve's
  sites are exactly the kind of row-per-record, independently-queryable,
  spatially-joinable data this stack's "spatial joins in the DB" choice
  (§3.3) exists for, and the CSV/GeoJSON export endpoints (Phase 7) need
  per-site rows regardless.
- **No separate `User` table.** Identity (`user_id`, email) comes from
  Clerk (or the local-dev fallback, `coolblock_api.auth`) at request time;
  this schema only needs a stable string id to attribute rows to, which
  `WorkspaceMember.user_id` / `*.created_by` already give it. Adding a
  locally-owned mirror of Clerk's own user table would just be a second,
  driftable copy of data Clerk already owns.
- **`Workspace.id` is Clerk's own organization id (a string), not a
  second, locally-generated UUID.** `coolblock_api.auth.Identity.workspace_id`
  already carries Clerk's `org_id` claim (or the dev-header equivalent) on
  every request; minting a separate local UUID and maintaining a mapping
  between the two would be a second identity for the same real-world
  organization, for no benefit -- "Clerk ... Organizations out of the box
  = workspaces on day one" (§3.3) means Clerk's id *is* the workspace id
  here. `routers/plans.py`'s `ensure_workspace` upserts the row (name
  defaulted to the id itself, since Clerk's own org name isn't available
  to a backend request without an extra Clerk API call this phase doesn't
  make) the first time a given workspace is seen.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from coolblock_api.db.base import Base


class WorkspaceRole(enum.StrEnum):
    owner = "owner"
    editor = "editor"
    viewer = "viewer"


class ScenarioStatus(enum.StrEnum):
    pending = "pending"
    running = "running"
    done = "done"
    error = "error"


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(200), primary_key=True)  # Clerk org id / dev-header workspace id -- see module docstring
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    members: Mapped[list[WorkspaceMember]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    plans: Mapped[list[Plan]] = relationship(back_populates="workspace", cascade="all, delete-orphan")


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(String(200))
    role: Mapped[WorkspaceRole] = mapped_column(Enum(WorkspaceRole, name="workspace_role"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace: Mapped[Workspace] = relationship(back_populates="members")


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    budget_usd: Mapped[float] = mapped_column(Float)
    constraints: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_by: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    workspace: Mapped[Workspace] = relationship(back_populates="plans")
    scenario_versions: Mapped[list[ScenarioVersion]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="ScenarioVersion.version_number"
    )
    annotations: Mapped[list[Annotation]] = relationship(back_populates="plan", cascade="all, delete-orphan")


class ScenarioVersion(Base):
    __tablename__ = "scenario_versions"
    __table_args__ = (UniqueConstraint("plan_id", "version_number", name="uq_plan_version_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[ScenarioStatus] = mapped_column(Enum(ScenarioStatus, name="scenario_status"), default=ScenarioStatus.pending)
    solver: Mapped[str | None] = mapped_column(String(50), nullable=True)
    objective_value_ewcb: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    job_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    plan: Mapped[Plan] = relationship(back_populates="scenario_versions")
    sites: Mapped[list[ScenarioSite]] = relationship(
        back_populates="scenario_version", cascade="all, delete-orphan", order_by="ScenarioSite.rank"
    )
    share_links: Mapped[list[ShareLink]] = relationship(back_populates="scenario_version", cascade="all, delete-orphan")


class ScenarioSite(Base):
    __tablename__ = "scenario_sites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scenario_versions.id", ondelete="CASCADE"), index=True
    )
    rank: Mapped[int] = mapped_column(Integer)
    candidate_id: Mapped[str] = mapped_column(String(100))
    intervention_type: Mapped[str] = mapped_column(String(50))
    cost_usd: Mapped[float] = mapped_column(Float)
    marginal_gain_ewcb: Mapped[float] = mapped_column(Float)
    cumulative_ewcb: Mapped[float] = mapped_column(Float)
    cumulative_cost_usd: Mapped[float] = mapped_column(Float)
    geometry: Mapped[Any] = mapped_column(Geometry(geometry_type="POLYGON", srid=4326))
    properties: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    scenario_version: Mapped[ScenarioVersion] = relationship(back_populates="sites")


class ShareLink(Base):
    __tablename__ = "share_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scenario_versions.id", ondelete="CASCADE"), index=True
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_by: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    scenario_version: Mapped[ScenarioVersion] = relationship(back_populates="share_links")


class Annotation(Base):
    __tablename__ = "annotations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), index=True)
    author_user_id: Mapped[str] = mapped_column(String(200))
    lng: Mapped[float] = mapped_column(Float)
    lat: Mapped[float] = mapped_column(Float)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    plan: Mapped[Plan] = relationship(back_populates="annotations")


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(100))
    target_type: Mapped[str] = mapped_column(String(50))
    target_id: Mapped[str] = mapped_column(String(200))
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
