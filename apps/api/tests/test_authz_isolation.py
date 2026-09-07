"""Phase 7 DoD (COOLBLOCK-BUILD-PLAN.md §10): "Two users in two orgs
cannot see each other's plans (tested)." This is that test -- for plans,
scenarios, and annotations, since all three are workspace-scoped
resources with the same potential failure mode (a query that forgets the
`workspace_id` filter)."""

from __future__ import annotations

from conftest import auth_headers
from fastapi.testclient import TestClient

ORG_A = auth_headers(user_id="alice", workspace_id="org-a")
ORG_B = auth_headers(user_id="mallory", workspace_id="org-b")


def test_plan_created_in_one_org_is_invisible_to_another(client: TestClient) -> None:
    plan = client.post("/plans", json={"name": "Secret plan", "budget_usd": 5000}, headers=ORG_A).json()

    assert client.get(f"/plans/{plan['id']}", headers=ORG_A).status_code == 200
    assert client.get(f"/plans/{plan['id']}", headers=ORG_B).status_code == 404


def test_org_b_cannot_update_or_delete_org_as_plan(client: TestClient) -> None:
    plan = client.post("/plans", json={"name": "P", "budget_usd": 5000}, headers=ORG_A).json()

    assert client.patch(f"/plans/{plan['id']}", json={"name": "hijacked"}, headers=ORG_B).status_code == 404
    assert client.delete(f"/plans/{plan['id']}", headers=ORG_B).status_code == 404

    # untouched from org A's own point of view
    assert client.get(f"/plans/{plan['id']}", headers=ORG_A).json()["name"] == "P"


def test_org_b_cannot_read_org_as_scenario_versions(client: TestClient) -> None:
    plan = client.post("/plans", json={"name": "P", "budget_usd": 5000}, headers=ORG_A).json()

    assert client.get(f"/plans/{plan['id']}/scenarios", headers=ORG_B).json() == []
    assert client.get(f"/plans/{plan['id']}/scenarios/1", headers=ORG_B).status_code == 404


def test_org_b_cannot_read_org_as_annotations(client: TestClient) -> None:
    plan = client.post("/plans", json={"name": "P", "budget_usd": 5000}, headers=ORG_A).json()
    client.post("/plans/" + plan["id"] + "/annotations", json={"lng": -112.05, "lat": 33.45, "body": "note"}, headers=ORG_A)

    assert client.get(f"/plans/{plan['id']}/annotations", headers=ORG_B).status_code == 404


def test_two_orgs_plan_lists_never_overlap(client: TestClient) -> None:
    client.post("/plans", json={"name": "A1", "budget_usd": 1000}, headers=ORG_A)
    client.post("/plans", json={"name": "A2", "budget_usd": 1000}, headers=ORG_A)
    client.post("/plans", json={"name": "B1", "budget_usd": 1000}, headers=ORG_B)

    org_a_names = {p["name"] for p in client.get("/plans", headers=ORG_A).json()}
    org_b_names = {p["name"] for p in client.get("/plans", headers=ORG_B).json()}

    assert org_a_names == {"A1", "A2"}
    assert org_b_names == {"B1"}
    assert org_a_names.isdisjoint(org_b_names)
