"""Phase 7 -- `/plans/{plan_id}/annotations`."""

from __future__ import annotations

from conftest import auth_headers
from fastapi.testclient import TestClient


def _make_plan(client: TestClient) -> str:
    return client.post("/plans", json={"name": "P", "budget_usd": 1000}, headers=auth_headers()).json()["id"]


def test_create_and_list_annotation(client: TestClient) -> None:
    plan_id = _make_plan(client)
    resp = client.post(
        f"/plans/{plan_id}/annotations",
        json={"lng": -112.055, "lat": 33.452, "body": "check this bus stop"},
        headers=auth_headers(),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["body"] == "check this bus stop"
    assert body["author_user_id"] == "alice"

    listed = client.get(f"/plans/{plan_id}/annotations", headers=auth_headers()).json()
    assert len(listed) == 1
    assert listed[0]["id"] == body["id"]


def test_author_can_delete_own_annotation(client: TestClient) -> None:
    plan_id = _make_plan(client)
    annotation = client.post(
        f"/plans/{plan_id}/annotations", json={"lng": 0, "lat": 0, "body": "x"}, headers=auth_headers(user_id="alice")
    ).json()

    resp = client.delete(f"/plans/{plan_id}/annotations/{annotation['id']}", headers=auth_headers(user_id="alice"))
    assert resp.status_code == 204
    assert client.get(f"/plans/{plan_id}/annotations", headers=auth_headers()).json() == []


def test_non_author_non_owner_cannot_delete_annotation(client: TestClient) -> None:
    plan_id = _make_plan(client)
    annotation = client.post(
        f"/plans/{plan_id}/annotations", json={"lng": 0, "lat": 0, "body": "x"}, headers=auth_headers(user_id="alice")
    ).json()

    resp = client.delete(
        f"/plans/{plan_id}/annotations/{annotation['id']}",
        headers=auth_headers(user_id="bob", role="editor"),
    )
    assert resp.status_code == 403


def test_owner_can_delete_someone_elses_annotation(client: TestClient) -> None:
    plan_id = _make_plan(client)
    annotation = client.post(
        f"/plans/{plan_id}/annotations", json={"lng": 0, "lat": 0, "body": "x"}, headers=auth_headers(user_id="alice")
    ).json()

    resp = client.delete(
        f"/plans/{plan_id}/annotations/{annotation['id']}",
        headers=auth_headers(user_id="owner-bob", role="owner"),
    )
    assert resp.status_code == 204
