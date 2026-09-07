"""Phase 7 -- the Pydantic request/response models FastAPI's own OpenAPI
schema is generated from, which `packages/schema`'s `generate.mjs` turns
into the TypeScript types the frontend imports (§11: "packages/schema is
generated from Pydantic models and is the single source of truth between
lanes... never hand-edited")."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from coolblock_api.db.models import ScenarioStatus


class ConstraintsIn(BaseModel):
    """The E3 side-constraint surface (§6.5 E3), mirroring
    `engine.optimize.plan_service.SolveParams` minus `budget_usd` (which
    lives on the plan itself, not nested inside its constraints)."""

    public_land_only: bool = False
    max_sites_per_zone: int | None = None
    min_spend_per_zone_usd: float | None = None
    annual_maintenance_cap_usd: float | None = None
    mandatory_include_ids: list[str] = Field(default_factory=list)
    mandatory_exclude_ids: list[str] = Field(default_factory=list)


class PlanCreate(BaseModel):
    name: str
    budget_usd: float = Field(gt=0)
    constraints: ConstraintsIn = Field(default_factory=ConstraintsIn)


class PlanUpdate(BaseModel):
    name: str | None = None
    budget_usd: float | None = Field(default=None, gt=0)
    constraints: ConstraintsIn | None = None


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: str
    name: str
    budget_usd: float
    constraints: dict[str, Any]
    created_by: str
    created_at: datetime
    updated_at: datetime


class ScenarioVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plan_id: uuid.UUID
    version_number: int
    status: ScenarioStatus
    solver: str | None
    objective_value_ewcb: float | None
    cost_usd: float | None
    job_id: str | None
    error_message: str | None
    created_by: str
    created_at: datetime
    completed_at: datetime | None


class ScenarioSiteOut(BaseModel):
    rank: int
    candidate_id: str
    intervention_type: str
    cost_usd: float
    marginal_gain_ewcb: float
    cumulative_ewcb: float
    cumulative_cost_usd: float
    geometry: dict[str, Any]
    properties: dict[str, Any]


class ScenarioVersionDetailOut(ScenarioVersionOut):
    sites: list[ScenarioSiteOut]


class AnnotationCreate(BaseModel):
    lng: float
    lat: float
    body: str


class AnnotationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plan_id: uuid.UUID
    author_user_id: str
    lng: float
    lat: float
    body: str
    created_at: datetime


class ShareLinkOut(BaseModel):
    token: str
    scenario_version_id: uuid.UUID
    created_at: datetime
