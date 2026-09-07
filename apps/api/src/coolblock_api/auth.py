"""Phase 7 -- authn/authz (COOLBLOCK-BUILD-PLAN.md §10 Phase 7): "Clerk auth
+ organization scoping; RBAC (owner/editor/viewer/public)."

**The local-dev fallback, and why it's here.** `docs/adr/0002-*.md` already
established this project's posture for infra not yet provisioned: ship
against an interface real code can use, keep the fallback tolerant and
explicit rather than pretending the real thing is wired up. No Clerk
tenant/credentials are provisioned yet (`.env.example`: "leave blank for
local-only Phase 0; required from Phase 7"). So:

- When `settings.clerk_jwks_url` + `settings.clerk_issuer` are set, every
  request must carry a real Clerk-issued JWT (`Authorization: Bearer ...`),
  verified against Clerk's own JWKS (RS256, cached, matching Clerk's
  documented session-token claim shape: `sub` = user id, `org_id` =
  workspace, `org_role` = `org:admin` / `org:editor` / `org:viewer` -> our
  `WorkspaceRole`).
- When they aren't set (local/test), identity comes from
  `X-Dev-User-Id` / `X-Dev-Workspace-Id` / `X-Dev-Role` headers instead --
  real headers a test can set per-request to get two independent
  identities, which is exactly what the authz-isolation test needs
  (`apps/api/tests/test_authz_isolation.py`). This path is refused outright
  in `environment=production` (`_require_dev_fallback_allowed`) so a
  misconfigured prod deploy fails loudly on the first request rather than
  silently running unauthenticated.

`docs/adr/0016-*.md` records this in full, including the honest caveat:
the Clerk-verification code path is unit-tested against a locally-signed
JWT with Clerk's documented claim shape (`tests/test_auth.py`), not yet
integration-tested against a live Clerk tenant, since no credentials are
provisioned yet.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, Request, status

from coolblock_api.db.models import WorkspaceRole
from coolblock_api.settings import Settings, get_settings


@dataclass(frozen=True)
class Identity:
    user_id: str
    workspace_id: str
    role: WorkspaceRole


class AuthConfigError(RuntimeError):
    """Raised at request time if `environment=production` but no real
    Clerk credential is configured -- refuses to fall back to the dev
    header path in prod rather than silently running unauthenticated."""


_CLERK_ORG_ROLE_MAP = {
    "org:admin": WorkspaceRole.owner,
    "org:editor": WorkspaceRole.editor,
    "org:viewer": WorkspaceRole.viewer,
}


@lru_cache(maxsize=1)
def _jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(jwks_url)


def _verify_clerk_jwt(token: str, settings: Settings) -> Identity:
    signing_key = _jwks_client(settings.clerk_jwks_url).get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=settings.clerk_issuer,
        options={"require": ["sub", "org_id", "org_role"]},
    )
    role = _CLERK_ORG_ROLE_MAP.get(claims["org_role"])
    if role is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"unrecognized org_role: {claims['org_role']!r}")
    return Identity(user_id=claims["sub"], workspace_id=claims["org_id"], role=role)


def _dev_identity_from_headers(request: Request) -> Identity:
    user_id = request.headers.get("x-dev-user-id", "dev-user")
    workspace_id = request.headers.get("x-dev-workspace-id", "dev-workspace")
    role_raw = request.headers.get("x-dev-role", "owner")
    try:
        role = WorkspaceRole(role_raw)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"invalid X-Dev-Role: {role_raw!r}") from exc
    return Identity(user_id=user_id, workspace_id=workspace_id, role=role)


def get_identity(request: Request, settings: Settings = Depends(get_settings)) -> Identity:
    if not settings.auth_is_dev_fallback:
        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing Bearer token")
        token = auth_header[len("bearer ") :]
        try:
            return _verify_clerk_jwt(token, settings)
        except jwt.PyJWTError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"invalid token: {exc}") from exc

    if settings.environment == "production":
        raise AuthConfigError(
            "CLERK_JWKS_URL/CLERK_ISSUER are not set in a production environment -- "
            "refusing to fall back to unauthenticated dev headers."
        )
    return _dev_identity_from_headers(request)


_ROLE_RANK = {WorkspaceRole.viewer: 0, WorkspaceRole.editor: 1, WorkspaceRole.owner: 2}


def require_role(minimum: WorkspaceRole) -> Callable[[Identity], Identity]:
    """A FastAPI dependency factory: `Depends(require_role(WorkspaceRole.editor))`
    rejects viewers from a mutating route while still resolving `Identity`
    for the handler."""

    def _dependency(identity: Identity = Depends(get_identity)) -> Identity:
        if _ROLE_RANK[identity.role] < _ROLE_RANK[minimum]:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, f"requires role >= {minimum.value}, has {identity.role.value}"
            )
        return identity

    return _dependency
