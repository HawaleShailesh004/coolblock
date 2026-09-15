"""Phase 7 -- the Pydantic request/response models FastAPI's own OpenAPI
schema is generated from, which `packages/schema`'s `generate.mjs` turns
into the TypeScript types the frontend imports (§11: "packages/schema is
generated from Pydantic models and is the single source of truth between
lanes... never hand-edited")."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from coolblock_api.db.models import ScenarioStatus


class ConstraintsIn(BaseModel):
    """The E3 side-constraint surface (§6.5 E3), mirroring
    `engine.optimize.plan_service.SolveParams` minus `budget_usd` (which
    lives on the plan itself, not nested inside its constraints).

    `program` and `public_land_only` default to a trees-on-public-land plan
    -- what an urban-forestry heat grant can actually be spent on, and the
    only default that answers the product's own question about trees
    (docs/adr/0027-*.md; engine.optimize.programs)."""

    program: Literal["trees", "cool_roofs"] = "trees"
    public_land_only: bool = True
    max_sites_per_zone: int | None = None
    min_spend_per_zone_usd: float | None = None
    annual_maintenance_cap_usd: float | None = None
    mandatory_include_ids: list[str] = Field(default_factory=list)
    mandatory_exclude_ids: list[str] = Field(default_factory=list)


class ParseConstraintsIn(BaseModel):
    """§7.1 L1: one plain-English sentence to parse into `ConstraintsIn`."""

    text: str = Field(min_length=1, max_length=2000)
    provider: Literal["anthropic", "groq"] | None = None


class PlaceResolutionOut(BaseModel):
    """One named place L1 tried to resolve via a real tool call against
    the cached OSM amenities export, and the real candidate ids (if any)
    found near it -- lets the UI show *why* a site was included."""

    query: str
    found: bool
    matched_name: str | None = None
    lat: float | None = None
    lon: float | None = None
    candidate_ids: list[str] = Field(default_factory=list)


class ParsedConstraintsOut(BaseModel):
    constraints: ConstraintsIn
    unsupported_requests: list[str]
    place_resolutions: list[PlaceResolutionOut]


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


class MemoNumberOut(BaseModel):
    """One number the memo's text cites, and whether L6's provenance
    guard could trace it back to the real payload -- lets the frontend
    render each number with a hover showing its source, or a warning if
    it couldn't be verified (§7.1 L6)."""

    raw: str
    value: float
    start: int
    end: int
    verified: bool
    path: str | None


class MemoOut(BaseModel):
    text: str
    numbers: list[MemoNumberOut]
    unverified_count: int
    regenerated: bool
