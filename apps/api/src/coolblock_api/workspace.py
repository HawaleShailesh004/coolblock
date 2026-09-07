"""Phase 7 -- resolves the current request's `Workspace` row, creating it
(and upserting the caller's `WorkspaceMember` row) the first time a given
workspace is seen. See `docs/adr/0017-*.md` and `db.models`'s module
docstring for why `Workspace.id` is the external (Clerk org / dev-header)
id directly rather than a second, locally-minted one."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from coolblock_api.auth import Identity, get_identity
from coolblock_api.db.base import get_db
from coolblock_api.db.models import Workspace, WorkspaceMember


def ensure_workspace(db: Session, identity: Identity) -> Workspace:
    workspace = db.get(Workspace, identity.workspace_id)
    if workspace is None:
        workspace = Workspace(id=identity.workspace_id, name=identity.workspace_id)
        db.add(workspace)
        db.flush()

    member = db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == identity.workspace_id,
            WorkspaceMember.user_id == identity.user_id,
        )
    ).scalar_one_or_none()
    if member is None:
        db.add(WorkspaceMember(workspace_id=identity.workspace_id, user_id=identity.user_id, role=identity.role))
    elif member.role != identity.role:
        member.role = identity.role  # the token/header is the source of truth for the current role, not this cache

    db.commit()
    return workspace


def get_current_workspace(
    identity: Identity = Depends(get_identity),
    db: Session = Depends(get_db),
) -> Workspace:
    return ensure_workspace(db, identity)
