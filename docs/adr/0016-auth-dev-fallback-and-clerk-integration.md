# 16. Auth: Clerk-shaped verification, dev-header fallback until credentials land

Date: 2026-09-08

## Status

Accepted

## Context

COOLBLOCK-BUILD-PLAN.md §10 Phase 7 calls for "Clerk auth + organization
scoping; RBAC (owner/editor/viewer/public)." ADR-0002 already recorded
that no Clerk tenant/credentials are provisioned yet, and set this
project's general posture for that situation (Wolfram, at the time):
ship against a real interface, keep a tolerant, explicit fallback rather
than pretending the real thing is wired up, and say so plainly.

The same call has to be made again here, and the stakes are higher than
Wolfram's: auth gates every workspace-scoped endpoint, and the Phase 7
DoD explicitly requires a *tested* authz-isolation guarantee ("Two users
in two orgs cannot see each other's plans").

## Decision

1. **`coolblock_api.auth.get_identity` has two paths**, selected by
   whether `CLERK_JWKS_URL`/`CLERK_ISSUER` are set:
   - **Real path**: verifies a Bearer JWT against Clerk's own JWKS
     (RS256, via `PyJWT`'s `PyJWKClient`), and maps Clerk's documented
     session-token claims (`sub`, `org_id`, `org_role`) onto this
     project's `Identity` (`user_id`, `workspace_id`, `WorkspaceRole`).
   - **Dev-header fallback**: reads `X-Dev-User-Id` / `X-Dev-Workspace-Id`
     / `X-Dev-Role` directly, defaulting to a stable demo identity when
     absent. This is what every other Phase 7 test actually runs against.
2. **The fallback is refused outright when `ENVIRONMENT=production`** and
   no Clerk credential is configured (`AuthConfigError`, raised at
   request time) -- a misconfigured prod deploy fails loudly on its first
   request instead of silently serving every caller as `dev-user`/owner.
3. **`Workspace.id` is Clerk's own organization id (a string), not a
   second, locally-minted UUID.** `Identity.workspace_id` already carries
   the real identity (Clerk's `org_id`, or the dev-header equivalent) on
   every request; a mapping table between "our workspace id" and "Clerk's
   org id" would be a second identity for the same real-world
   organization, for no benefit. `coolblock_api.workspace.ensure_workspace`
   upserts the `Workspace`/`WorkspaceMember` rows the first time a given
   id is seen, rather than requiring a separate provisioning step.
4. **The Clerk-verification code path is unit-tested against a
   locally-signed RS256 JWT** built with Clerk's documented claim shape,
   with the JWKS lookup monkeypatched to a key pair generated in the test
   (`apps/api/tests/test_auth.py`) -- not integration-tested against a
   live Clerk tenant, since no credentials are provisioned yet. This is
   the same honest caveat ADR-0002 recorded for Wolfram's `NMaximize`
   cross-check: the logic is real and exercised, the live third-party
   integration is not yet proven end-to-end.

## Consequences

- Every Phase 7 API test runs against the dev-header path. This is
  sufficient to prove the authz-isolation guarantee the DoD asks for
  (two independent `Identity` values via two independent header sets is
  exactly "two users in two orgs"), but it does **not** prove Clerk's own
  JWKS endpoint, key rotation, or org-membership sync behave as this code
  assumes -- that remains open until real Clerk credentials are
  provisioned and `apps/api/tests/test_auth.py` (or a new test) is run
  against them.
- `RBAC` currently has three tiers (owner/editor/viewer); "public" from
  the plan's own phrasing ("owner/editor/viewer/public") is implemented
  as the *absence* of a `WorkspaceMember` row and a role-independent path
  (`GET /share/{token}`, `routers/share.py`), not a fourth `WorkspaceRole`
  value -- a public viewer never resolves to an `Identity` at all.
- `WorkspaceMember` is a local cache of the token's own role claim,
  upserted on every authenticated request; it is not the RBAC source of
  truth (the token/header is, every time) and should not be hand-edited
  to grant access -- the next authenticated request from that user
  overwrites it with whatever the token says.
