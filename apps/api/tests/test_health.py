from fastapi.testclient import TestClient

from coolblock_api.main import app

client = TestClient(app)


def test_health_reports_real_config() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["neighborhood"] == "edison-eastlake-phoenix-az"
    assert body["target_crs"] == "EPSG:32612"
