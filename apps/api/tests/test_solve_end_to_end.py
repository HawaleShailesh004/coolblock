"""Phase 7 -- the full solve path: enqueue -> real ARQ task execution ->
Redis event stream (with reconnect replay) -> Postgres persistence ->
GeoJSON/CSV export -> share link. Everything here is real: the actual
cached candidate universe, the actual CELF/constrained-greedy solver, a
real Redis instance, a real Postgres database.

`coolblock_api.jobs.worker.run_plan_solve` is called directly with a
hand-built ARQ `ctx` rather than through a live `arq` worker subprocess --
same function, same Redis, same DB writes; skipping only the process
supervision, which isn't what this test is verifying. (`docs/RUNNING-AND-TESTING.md`
documents `uv run arq coolblock_api.jobs.worker.WorkerSettings` as the
real way to run it, and the Phase 7 checkpoint --
"`curl` a solve and watch the stages stream in" -- was verified by hand
against that real worker before this test was written.)

Skips if the cached candidate export doesn't exist yet on this machine
(same guard as `engine/tests/test_plan_service.py`)."""

from __future__ import annotations

import asyncio

import httpx
import pytest
from conftest import auth_headers
from engine.optimize.plan_service import CANDIDATES_PATH, SolveParams
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(
    not CANDIDATES_PATH.exists(),
    reason=f"{CANDIDATES_PATH} not built yet -- run `uv run python scripts/export_map_layers.py`",
)


async def _run_solve_job(scenario: dict[str, object], budget_usd: float) -> dict[str, object]:
    """Runs the real solve for a scenario the `/solve` endpoint already
    created. Reuses *that* scenario's own `job_id` (minted by
    `routers/plans.py::solve_plan` and stored on the row) rather than a
    fresh one -- the real worker (`uv run arq
    coolblock_api.jobs.worker.WorkerSettings`) always gets that same id
    handed to it via `ctx["job_id"]`, and the SSE endpoint looks events up
    by the scenario's stored `job_id`, so a test-only mismatch here would
    silently test something the real system never does."""
    from coolblock_api.jobs.redis import get_redis
    from coolblock_api.jobs.worker import run_plan_solve

    job_id = scenario["job_id"]
    assert isinstance(job_id, str)
    ctx = {"redis": get_redis(), "job_id": job_id}
    result = await run_plan_solve(ctx, str(scenario["id"]), SolveParams(budget_usd=budget_usd))
    return {"job_id": job_id, **result}


@pytest.mark.asyncio
async def test_solve_persists_sites_and_marks_scenario_done(client: TestClient) -> None:
    plan = client.post("/plans", json={"name": "Solve me", "budget_usd": 20000}, headers=auth_headers()).json()
    solve_resp = client.post(f"/plans/{plan['id']}/solve", headers=auth_headers())
    assert solve_resp.status_code == 202
    scenario = solve_resp.json()
    assert scenario["status"] == "pending"
    assert scenario["job_id"] is not None

    result = await _run_solve_job(scenario, plan["budget_usd"])
    assert result["n_sites"] > 0

    detail = client.get(f"/plans/{plan['id']}/scenarios/{scenario['version_number']}", headers=auth_headers()).json()
    assert detail["status"] == "done"
    # Unconstrained solve: exact when HiGHS proves it inside the wall-clock
    # limit (the usual case on the default pool), CELF when it does not --
    # both are honest answers, and the API reports which one ran.
    assert detail["solver"] in ("exact_milp", "celf")
    assert detail["cost_usd"] <= plan["budget_usd"] + 1e-6
    assert len(detail["sites"]) == result["n_sites"]
    assert detail["sites"][0]["rank"] == 1
    assert detail["sites"][0]["geometry"]["type"] == "Polygon"


@pytest.mark.asyncio
async def test_sse_endpoint_does_not_close_before_the_worker_publishes_anything(client: TestClient) -> None:
    """Regression test for a real bug caught during Phase 8 frontend
    integration (docs/adr/0017-*.md's amendment): `redis.asyncio`'s
    `pubsub.get_message(timeout=N)` returns `None` almost instantly on its
    *first* call right after `subscribe()` -- it consumes the
    subscribe-confirmation control message Redis sends immediately, and
    filters it out. An earlier version of the SSE endpoint treated any
    single `None` as "nothing is ever coming" and closed the stream within
    milliseconds of connecting, before the worker had even started.

    The original Phase 7 SSE test (`test_sse_stream_replays_from_a_given_sequence_after_solve_completes`,
    below) never caught this because it called `replay_events_after`
    directly against an *already-finished* job -- pure replay, never
    touching the live-wait branch this bug lived in. This test opens the
    real HTTP endpoint and starts reading *before* the solve has published
    anything, racing it against the real job the same way a real, fast
    client (this test, or the actual frontend) does."""
    from coolblock_api.main import app

    plan = client.post("/plans", json={"name": "SSE race test", "budget_usd": 15000}, headers=auth_headers()).json()
    scenario = client.post(f"/plans/{plan['id']}/solve", headers=auth_headers()).json()

    event_types: list[str] = []

    async def read_stream() -> None:
        transport = httpx.ASGITransport(app=app)
        async with (
            httpx.AsyncClient(transport=transport, base_url="http://test") as http_client,
            http_client.stream(
                "GET",
                f"/plans/{plan['id']}/scenarios/{scenario['version_number']}/events",
                headers=auth_headers(),
                timeout=30.0,
            ) as response,
        ):
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    event_types.append(line.split(":", 1)[1].strip())

    # Concurrent, not sequential -- the stream-reader starts before the
    # solve job has run at all, which is exactly the timing the bug needed.
    await asyncio.gather(read_stream(), _run_solve_job(scenario, plan["budget_usd"]))

    assert event_types[0] == "stage"
    assert event_types.count("site") > 0
    assert event_types[-1] == "done"


@pytest.mark.asyncio
async def test_sse_stream_replays_from_a_given_sequence_after_solve_completes(client: TestClient) -> None:
    from coolblock_api.jobs.events import replay_events_after
    from coolblock_api.jobs.redis import get_redis

    plan = client.post("/plans", json={"name": "SSE test", "budget_usd": 15000}, headers=auth_headers()).json()
    scenario = client.post(f"/plans/{plan['id']}/solve", headers=auth_headers()).json()
    await _run_solve_job(scenario, plan["budget_usd"])

    redis = get_redis()
    all_events = await replay_events_after(redis, scenario["job_id"], after_seq=0)
    assert all_events[0].type == "stage"
    assert all_events[-1].type == "done"

    # reconnecting after the 2nd event should only replay what's left
    partial = await replay_events_after(redis, scenario["job_id"], after_seq=2)
    assert len(partial) == len(all_events) - 2
    assert [e.seq for e in partial] == [e.seq for e in all_events[2:]]


@pytest.mark.asyncio
async def test_baselines_endpoint_returns_all_five_strategies_and_coolblock_wins(client: TestClient) -> None:
    """§9 ★5. Real cost (~15-20s, see engine/tests/test_plan_service.py's
    matching test) -- kept to one test, not duplicated per budget."""
    plan = client.post("/plans", json={"name": "Baselines test", "budget_usd": 50000}, headers=auth_headers()).json()
    scenario = client.post(f"/plans/{plan['id']}/solve", headers=auth_headers()).json()

    resp = client.get(f"/plans/{plan['id']}/scenarios/{scenario['version_number']}/baselines", headers=auth_headers())
    assert resp.status_code == 200
    result = resp.json()
    assert set(result.keys()) == {"spread_evenly", "worst_first", "squeaky_wheel", "tes_score_only", "coolblock"}
    assert result["coolblock"] > result["tes_score_only"] > 0


@pytest.mark.asyncio
async def test_export_geojson_and_csv_after_solve(client: TestClient) -> None:
    plan = client.post("/plans", json={"name": "Export test", "budget_usd": 15000}, headers=auth_headers()).json()
    scenario = client.post(f"/plans/{plan['id']}/solve", headers=auth_headers()).json()
    result = await _run_solve_job(scenario, plan["budget_usd"])

    geojson = client.get(
        f"/plans/{plan['id']}/scenarios/{scenario['version_number']}/export.geojson", headers=auth_headers()
    ).json()
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == result["n_sites"]
    assert geojson["features"][0]["properties"]["candidate_id"]

    csv_resp = client.get(
        f"/plans/{plan['id']}/scenarios/{scenario['version_number']}/export.csv", headers=auth_headers()
    )
    assert csv_resp.status_code == 200
    assert csv_resp.headers["content-type"].startswith("text/csv")
    lines = csv_resp.text.strip().splitlines()
    assert lines[0] == "rank,candidate_id,intervention_type,cost_usd,marginal_gain_ewcb,cumulative_ewcb,cumulative_cost_usd"
    assert len(lines) - 1 == result["n_sites"]


@pytest.mark.asyncio
async def test_share_link_exposes_a_solved_scenario_publicly(client: TestClient) -> None:
    plan = client.post("/plans", json={"name": "Share test", "budget_usd": 15000}, headers=auth_headers()).json()
    scenario = client.post(f"/plans/{plan['id']}/solve", headers=auth_headers()).json()
    await _run_solve_job(scenario, plan["budget_usd"])

    share_resp = client.post(
        f"/plans/{plan['id']}/scenarios/{scenario['version_number']}/share", headers=auth_headers()
    )
    assert share_resp.status_code == 201
    token = share_resp.json()["token"]

    # no auth headers at all -- this is the point of a public share link
    public_resp = client.get(f"/share/{token}")
    assert public_resp.status_code == 200
    assert public_resp.json()["status"] == "done"

    assert client.get("/share/not-a-real-token").status_code == 404


@pytest.mark.asyncio
async def test_solve_endpoint_is_rate_limited(client: TestClient) -> None:
    from coolblock_api.settings import get_settings

    plan = client.post("/plans", json={"name": "Rate limited", "budget_usd": 15000}, headers=auth_headers()).json()
    limit = get_settings().solve_rate_limit_per_minute

    statuses = [client.post(f"/plans/{plan['id']}/solve", headers=auth_headers()).status_code for _ in range(limit + 3)]
    assert statuses.count(202) == limit
    assert statuses.count(429) == 3
