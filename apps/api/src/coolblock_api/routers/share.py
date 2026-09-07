"""Phase 7 -- share links: "a public read-only scenario link" (§1.2's
product-level bar for Sharing). Creating one requires being a real,
authenticated editor of the workspace; reading one (`GET /share/{token}`)
requires nothing at all by design -- that's the point of a public link,
and the whole reason it's a separate, unguessable token rather than the
scenario's own (sequential, workspace-scoped) id."""

from __future__ import annotations

import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from sqlalchemy import select
from sqlalchemy.orm import Session

from coolblock_api.auth import Identity, require_role
from coolblock_api.db.base import get_db
from coolblock_api.db.models import Plan, ScenarioVersion, ShareLink, Workspace, WorkspaceRole
from coolblock_api.schemas import (
    ScenarioSiteOut,
    ScenarioVersionDetailOut,
    ScenarioVersionOut,
    ShareLinkOut,
)
from coolblock_api.workspace import get_current_workspace

plan_scoped_router = APIRouter(prefix="/plans/{plan_id}/scenarios/{version}/share", tags=["share"])
public_router = APIRouter(prefix="/share", tags=["share"])


@plan_scoped_router.post("", response_model=ShareLinkOut, status_code=status.HTTP_201_CREATED)
def create_share_link(
    plan_id: uuid.UUID,
    version: int,
    identity: Identity = Depends(require_role(WorkspaceRole.editor)),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> ShareLink:
    scenario = db.execute(
        select(ScenarioVersion)
        .join(Plan, ScenarioVersion.plan_id == Plan.id)
        .where(
            ScenarioVersion.plan_id == plan_id,
            ScenarioVersion.version_number == version,
            Plan.workspace_id == workspace.id,
        )
    ).scalar_one_or_none()
    if scenario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "scenario version not found")

    link = ShareLink(scenario_version_id=scenario.id, token=secrets.token_urlsafe(24), created_by=identity.user_id)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@public_router.get("/{token}", response_model=ScenarioVersionDetailOut)
def read_shared_scenario(token: str, db: Session = Depends(get_db)) -> ScenarioVersionDetailOut:
    link = db.execute(select(ShareLink).where(ShareLink.token == token)).scalar_one_or_none()
    if link is None or link.revoked_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "share link not found or revoked")

    scenario = link.scenario_version
    return ScenarioVersionDetailOut(
        **ScenarioVersionOut.model_validate(scenario).model_dump(),
        sites=[
            ScenarioSiteOut(
                rank=s.rank,
                candidate_id=s.candidate_id,
                intervention_type=s.intervention_type,
                cost_usd=s.cost_usd,
                marginal_gain_ewcb=s.marginal_gain_ewcb,
                cumulative_ewcb=s.cumulative_ewcb,
                cumulative_cost_usd=s.cumulative_cost_usd,
                geometry=mapping(to_shape(s.geometry)),
                properties=s.properties,
            )
            for s in scenario.sites
        ],
    )
