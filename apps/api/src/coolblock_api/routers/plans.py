"""Phase 7 -- `/plans`: create/list/get/update/delete a plan, and trigger a
solve. Every route is scoped to `get_current_workspace()`'s workspace --
the query that fetches a plan always filters `Plan.workspace_id ==
workspace.id`, which is what makes cross-workspace access return a 404
instead of someone else's data (`apps/api/tests/test_authz_isolation.py`
is the DoD check for this: "Two users in two orgs cannot see each other's
plans")."""

from __future__ import annotations

import uuid

from engine.optimize.plan_service import SolveParams
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from coolblock_api.auth import Identity, require_role
from coolblock_api.db.base import get_db
from coolblock_api.db.models import Plan, ScenarioStatus, ScenarioVersion, Workspace, WorkspaceRole
from coolblock_api.jobs.pool import get_arq_pool
from coolblock_api.rate_limit import rate_limit
from coolblock_api.schemas import PlanCreate, PlanOut, PlanUpdate, ScenarioVersionOut
from coolblock_api.workspace import get_current_workspace

router = APIRouter(prefix="/plans", tags=["plans"])


def _get_plan_or_404(db: Session, workspace: Workspace, plan_id: uuid.UUID) -> Plan:
    plan = db.execute(select(Plan).where(Plan.id == plan_id, Plan.workspace_id == workspace.id)).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "plan not found")
    return plan


@router.post("", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
def create_plan(
    body: PlanCreate,
    identity: Identity = Depends(require_role(WorkspaceRole.editor)),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> Plan:
    plan = Plan(
        workspace_id=workspace.id,
        name=body.name,
        budget_usd=body.budget_usd,
        constraints=body.constraints.model_dump(),
        created_by=identity.user_id,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("", response_model=list[PlanOut])
def list_plans(
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[Plan]:
    return list(db.execute(select(Plan).where(Plan.workspace_id == workspace.id).order_by(Plan.created_at.desc())).scalars())


@router.get("/{plan_id}", response_model=PlanOut)
def get_plan(
    plan_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> Plan:
    return _get_plan_or_404(db, workspace, plan_id)


@router.patch("/{plan_id}", response_model=PlanOut)
def update_plan(
    plan_id: uuid.UUID,
    body: PlanUpdate,
    _identity: Identity = Depends(require_role(WorkspaceRole.editor)),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> Plan:
    plan = _get_plan_or_404(db, workspace, plan_id)
    if body.name is not None:
        plan.name = body.name
    if body.budget_usd is not None:
        plan.budget_usd = body.budget_usd
    if body.constraints is not None:
        plan.constraints = body.constraints.model_dump()
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(
    plan_id: uuid.UUID,
    _identity: Identity = Depends(require_role(WorkspaceRole.owner)),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> None:
    plan = _get_plan_or_404(db, workspace, plan_id)
    db.delete(plan)
    db.commit()


@router.post("/{plan_id}/solve", response_model=ScenarioVersionOut, status_code=status.HTTP_202_ACCEPTED)
async def solve_plan(
    plan_id: uuid.UUID,
    identity: Identity = Depends(require_role(WorkspaceRole.editor)),
    workspace: Workspace = Depends(rate_limit("solve")),
    db: Session = Depends(get_db),
) -> ScenarioVersion:
    """Creates a new `ScenarioVersion` (status `pending`) and enqueues the
    real solve as an ARQ job (`coolblock_api.jobs.worker.run_plan_solve`).
    The job id is minted here (not left to ARQ to generate) so it can be
    handed back to the caller immediately -- the client opens
    `GET /plans/{plan_id}/scenarios/{version}/events?job_id=...` (Phase
    7's SSE endpoint) without a second round trip to discover it."""
    plan = _get_plan_or_404(db, workspace, plan_id)

    last_version = db.execute(
        select(ScenarioVersion.version_number)
        .where(ScenarioVersion.plan_id == plan.id)
        .order_by(ScenarioVersion.version_number.desc())
        .limit(1)
    ).scalar_one_or_none()
    next_version = (last_version or 0) + 1

    job_id = str(uuid.uuid4())
    scenario_version = ScenarioVersion(
        plan_id=plan.id,
        version_number=next_version,
        status=ScenarioStatus.pending,
        job_id=job_id,
        created_by=identity.user_id,
    )
    db.add(scenario_version)
    db.commit()
    db.refresh(scenario_version)

    constraints = plan.constraints or {}
    params = SolveParams(
        budget_usd=plan.budget_usd,
        public_land_only=constraints.get("public_land_only", False),
        max_sites_per_zone=constraints.get("max_sites_per_zone"),
        min_spend_per_zone_usd=constraints.get("min_spend_per_zone_usd"),
        annual_maintenance_cap_usd=constraints.get("annual_maintenance_cap_usd"),
        mandatory_include_ids=frozenset(constraints.get("mandatory_include_ids", [])),
        mandatory_exclude_ids=frozenset(constraints.get("mandatory_exclude_ids", [])),
    )

    pool = await get_arq_pool()
    await pool.enqueue_job("run_plan_solve", str(scenario_version.id), params, _job_id=job_id)

    return scenario_version
