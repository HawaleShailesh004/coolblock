"""Phase 7 -- `coolblock_api.auth`. Two paths, both exercised for real:

1. The dev-header fallback (what every other Phase 7 test actually runs
   against, since no Clerk tenant is provisioned -- `docs/adr/0016-*.md`).
2. The Clerk-JWT verification path, unit-tested against a locally-signed
   RS256 JWT built with Clerk's own documented claim shape (`sub`,
   `org_id`, `org_role`) and a monkeypatched JWKS lookup, so the real
   signature-verification and claim-mapping logic is actually exercised
   end to end -- not integration-tested against a live Clerk tenant,
   since no credentials are provisioned yet (the same honest caveat
   `docs/adr/0002-*.md` already recorded for Wolfram).
"""

from __future__ import annotations

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException, Request

from coolblock_api.auth import AuthConfigError, Identity, get_identity, require_role
from coolblock_api.db.models import WorkspaceRole
from coolblock_api.settings import Settings


def _make_request(headers: dict[str, str]) -> Request:
    encoded_headers = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    scope = {"type": "http", "headers": encoded_headers, "method": "GET", "path": "/"}
    return Request(scope)


def _dev_settings(**overrides: object) -> Settings:
    base: dict[str, object] = {"clerk_jwks_url": "", "clerk_issuer": "", "environment": "local"}
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_dev_fallback_defaults_to_a_stable_demo_identity() -> None:
    identity = get_identity(_make_request({}), _dev_settings())
    assert identity == Identity(user_id="dev-user", workspace_id="dev-workspace", role=WorkspaceRole.owner)


def test_dev_fallback_reads_headers_for_two_independent_identities() -> None:
    a = get_identity(_make_request({"X-Dev-User-Id": "alice", "X-Dev-Workspace-Id": "org-a"}), _dev_settings())
    b = get_identity(_make_request({"X-Dev-User-Id": "bob", "X-Dev-Workspace-Id": "org-b"}), _dev_settings())
    assert a.workspace_id != b.workspace_id
    assert a.user_id != b.user_id


def test_dev_fallback_rejects_invalid_role_header() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_identity(_make_request({"X-Dev-Role": "superuser"}), _dev_settings())
    assert exc_info.value.status_code == 400


def test_dev_fallback_refused_in_production() -> None:
    with pytest.raises(AuthConfigError):
        get_identity(_make_request({}), _dev_settings(environment="production"))


def test_require_role_rejects_viewer_from_editor_route() -> None:
    dependency = require_role(WorkspaceRole.editor)
    with pytest.raises(HTTPException) as exc_info:
        dependency(Identity(user_id="u", workspace_id="w", role=WorkspaceRole.viewer))
    assert exc_info.value.status_code == 403


def test_require_role_allows_owner_on_editor_route() -> None:
    dependency = require_role(WorkspaceRole.editor)
    identity = Identity(user_id="u", workspace_id="w", role=WorkspaceRole.owner)
    assert dependency(identity) is identity


class _FakeSigningKey:
    def __init__(self, key: object) -> None:
        self.key = key


class _FakeJwksClient:
    def __init__(self, public_key: object) -> None:
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token: str) -> _FakeSigningKey:
        return _FakeSigningKey(self._public_key)


def test_clerk_jwt_path_verifies_signature_and_maps_org_role(monkeypatch: pytest.MonkeyPatch) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    token = jwt.encode(
        {
            "sub": "user_2abc",
            "org_id": "org_xyz",
            "org_role": "org:editor",
            "iss": "https://coolblock.clerk.accounts.dev",
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
        },
        private_key,
        algorithm="RS256",
    )

    monkeypatch.setattr("coolblock_api.auth._jwks_client", lambda url: _FakeJwksClient(public_key))

    settings = Settings(
        clerk_jwks_url="https://coolblock.clerk.accounts.dev/.well-known/jwks.json",
        clerk_issuer="https://coolblock.clerk.accounts.dev",
        environment="local",
    )
    identity = get_identity(_make_request({"Authorization": f"Bearer {token}"}), settings)
    assert identity == Identity(user_id="user_2abc", workspace_id="org_xyz", role=WorkspaceRole.editor)


def test_clerk_jwt_path_rejects_missing_bearer_header() -> None:
    settings = Settings(
        clerk_jwks_url="https://coolblock.clerk.accounts.dev/.well-known/jwks.json",
        clerk_issuer="https://coolblock.clerk.accounts.dev",
        environment="local",
    )
    with pytest.raises(HTTPException) as exc_info:
        get_identity(_make_request({}), settings)
    assert exc_info.value.status_code == 401


def test_clerk_jwt_path_rejects_token_signed_by_a_different_key(monkeypatch: pytest.MonkeyPatch) -> None:
    real_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    forged_token = jwt.encode(
        {"sub": "user_evil", "org_id": "org_xyz", "org_role": "org:admin"},
        attacker_key,
        algorithm="RS256",
    )
    monkeypatch.setattr("coolblock_api.auth._jwks_client", lambda url: _FakeJwksClient(real_key.public_key()))

    settings = Settings(
        clerk_jwks_url="https://coolblock.clerk.accounts.dev/.well-known/jwks.json",
        clerk_issuer="https://coolblock.clerk.accounts.dev",
        environment="local",
    )
    with pytest.raises(HTTPException) as exc_info:
        get_identity(_make_request({"Authorization": f"Bearer {forged_token}"}), settings)
    assert exc_info.value.status_code == 401
