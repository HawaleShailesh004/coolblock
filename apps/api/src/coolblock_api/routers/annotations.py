"""Phase 7 -- `/plans/{plan_id}/annotations`: comments pinned to a map
location (full pinning-on-the-map UI is Phase 11; this is the persisted,
typed CRUD surface it will render against)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from coolblock_api.auth import Identity, require_role
from coolblock_api.db.base import get_db
from coolblock_api.db.models import Annotation, Plan, Workspace, WorkspaceRole
from coolblock_api.schemas import AnnotationCreate, AnnotationOut
from coolblock_api.workspace import get_current_workspace

router = APIRouter(prefix="/plans/{plan_id}/annotations", tags=["annotations"])


def _get_plan_or_404(db: Session, workspace: Workspace, plan_id: uuid.UUID) -> Plan:
    plan = db.execute(select(Plan).where(Plan.id == plan_id, Plan.workspace_id == workspace.id)).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "plan not found")
    return plan


@router.post("", response_model=AnnotationOut, status_code=status.HTTP_201_CREATED)
def create_annotation(
    plan_id: uuid.UUID,
    body: AnnotationCreate,
    identity: Identity = Depends(require_role(WorkspaceRole.viewer)),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> Annotation:
    plan = _get_plan_or_404(db, workspace, plan_id)
    annotation = Annotation(plan_id=plan.id, author_user_id=identity.user_id, lng=body.lng, lat=body.lat, body=body.body)
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return annotation


@router.get("", response_model=list[AnnotationOut])
def list_annotations(
    plan_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[Annotation]:
    plan = _get_plan_or_404(db, workspace, plan_id)
    return list(db.execute(select(Annotation).where(Annotation.plan_id == plan.id).order_by(Annotation.created_at)).scalars())


@router.delete("/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_annotation(
    plan_id: uuid.UUID,
    annotation_id: uuid.UUID,
    identity: Identity = Depends(require_role(WorkspaceRole.viewer)),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> None:
    plan = _get_plan_or_404(db, workspace, plan_id)
    annotation = db.execute(
        select(Annotation).where(Annotation.id == annotation_id, Annotation.plan_id == plan.id)
    ).scalar_one_or_none()
    if annotation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "annotation not found")
    if annotation.author_user_id != identity.user_id and identity.role != WorkspaceRole.owner:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "only the author or a workspace owner can delete this annotation")
    db.delete(annotation)
    db.commit()
