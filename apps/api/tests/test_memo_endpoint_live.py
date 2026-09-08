"""L3/L6 -- `POST /plans/{id}/scenarios/{version}/memo`, through the full
real stack (Postgres, the real solve, the real Claude API)."""

from __future__ import annotations

import os

import pytest
from conftest import auth_headers
from engine.optimize.plan_service import CANDIDATES_PATH
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(not CANDIDATES_PATH.exists(), reason=f"{CANDIDATES_PATH} not built yet")

# Only the test that actually calls the real Claude API is gated -- the
# 409-rejection test below never reaches that call and costs nothing, so
# it runs every time like the rest of this suite.
_requires_live_llm = pytest.mark.skipif(
    os.environ.get("RUN_LLM_TESTS") != "1", reason="costs a real Claude API call -- set RUN_LLM_TESTS=1 to run"
)


@_requires_live_llm
@pytest.mark.asyncio
async def test_memo_endpoint_generates_a_verified_memo_for_a_done_scenario(client: TestClient) -> None:
    from test_solve_end_to_end import _run_solve_job  # reuse the same real-worker helper

    plan = client.post("/plans", json={"name": "Memo test", "budget_usd": 20000}, headers=auth_headers()).json()
    scenario = client.post(f"/plans/{plan['id']}/solve", headers=auth_headers()).json()
    await _run_solve_job(scenario, plan["budget_usd"])

    resp = client.post(f"/plans/{plan['id']}/scenarios/{scenario['version_number']}/memo", headers=auth_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert "EXECUTIVE SUMMARY" in body["text"]
    assert "predicted cooling" not in body["text"].lower()
    assert body["unverified_count"] == 0
    assert len(body["numbers"]) > 0


@pytest.mark.asyncio
async def test_memo_endpoint_rejects_a_scenario_that_never_finished_solving(client: TestClient) -> None:
    plan = client.post("/plans", json={"name": "Memo pending test", "budget_usd": 20000}, headers=auth_headers()).json()
    scenario = client.post(f"/plans/{plan['id']}/solve", headers=auth_headers()).json()
    # Deliberately not running the solve job -- the scenario stays "pending".

    resp = client.post(f"/plans/{plan['id']}/scenarios/{scenario['version_number']}/memo", headers=auth_headers())
    assert resp.status_code == 409
