"""Phase 7 -- `/plans` CRUD, against the real (test) Postgres database."""

from __future__ import annotations

from conftest import auth_headers
from fastapi.testclient import TestClient


def test_create_and_get_plan(client: TestClient) -> None:
    resp = client.post("/plans", json={"name": "Edison-Eastlake baseline", "budget_usd": 50000}, headers=auth_headers())
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Edison-Eastlake baseline"
    assert body["budget_usd"] == 50000.0
    assert body["workspace_id"] == "org-a"
    assert body["created_by"] == "alice"

    got = client.get(f"/plans/{body['id']}", headers=auth_headers())
    assert got.status_code == 200
    assert got.json() == body


def test_create_plan_rejects_non_positive_budget(client: TestClient) -> None:
    resp = client.post("/plans", json={"name": "bad", "budget_usd": 0}, headers=auth_headers())
    assert resp.status_code == 422


def test_viewer_cannot_create_plan(client: TestClient) -> None:
    resp = client.post(
        "/plans", json={"name": "nope", "budget_usd": 1000}, headers=auth_headers(role="viewer")
    )
    assert resp.status_code == 403


def test_list_plans_scoped_to_workspace(client: TestClient) -> None:
    client.post("/plans", json={"name": "A", "budget_usd": 1000}, headers=auth_headers(workspace_id="org-a"))
    client.post("/plans", json={"name": "B", "budget_usd": 2000}, headers=auth_headers(workspace_id="org-b"))

    org_a_plans = client.get("/plans", headers=auth_headers(workspace_id="org-a")).json()
    org_b_plans = client.get("/plans", headers=auth_headers(workspace_id="org-b")).json()

    assert [p["name"] for p in org_a_plans] == ["A"]
    assert [p["name"] for p in org_b_plans] == ["B"]


def test_update_plan(client: TestClient) -> None:
    plan = client.post("/plans", json={"name": "Draft", "budget_usd": 10000}, headers=auth_headers()).json()
    resp = client.patch(f"/plans/{plan['id']}", json={"name": "Final", "budget_usd": 15000}, headers=auth_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Final"
    assert body["budget_usd"] == 15000.0


def test_update_plan_constraints_round_trips(client: TestClient) -> None:
    plan = client.post("/plans", json={"name": "Constrained", "budget_usd": 10000}, headers=auth_headers()).json()
    resp = client.patch(
        f"/plans/{plan['id']}",
        json={"constraints": {"public_land_only": True, "max_sites_per_zone": 2}},
        headers=auth_headers(),
    )
    body = resp.json()
    assert body["constraints"]["public_land_only"] is True
    assert body["constraints"]["max_sites_per_zone"] == 2


def test_editor_can_update_but_only_owner_can_delete(client: TestClient) -> None:
    plan = client.post("/plans", json={"name": "P", "budget_usd": 1000}, headers=auth_headers(role="owner")).json()

    update_as_editor = client.patch(f"/plans/{plan['id']}", json={"name": "P2"}, headers=auth_headers(role="editor"))
    assert update_as_editor.status_code == 200

    delete_as_editor = client.delete(f"/plans/{plan['id']}", headers=auth_headers(role="editor"))
    assert delete_as_editor.status_code == 403

    delete_as_owner = client.delete(f"/plans/{plan['id']}", headers=auth_headers(role="owner"))
    assert delete_as_owner.status_code == 204

    assert client.get(f"/plans/{plan['id']}", headers=auth_headers()).status_code == 404


def test_get_nonexistent_plan_is_404(client: TestClient) -> None:
    resp = client.get("/plans/00000000-0000-0000-0000-000000000000", headers=auth_headers())
    assert resp.status_code == 404
