from fastapi.testclient import TestClient

from services.api.app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_city_contract():
    response = client.get("/v1/city")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["city"]["nodes"]) == 48
    assert payload["criticality"]["summary"]["edges"] > 80


def test_extraction_endpoint():
    response = client.post("/v1/extraction/analyze", json={"seed": 2026})
    assert response.status_code == 200
    payload = response.json()
    assert payload["raw"]["metrics"]["iou"] >= 0
    assert payload["recovered"]["connectivity"] >= 0


def test_scenario_endpoint_and_validation():
    response = client.post(
        "/v1/scenarios/simulate",
        json={"kind": "critical_link", "severity": 0.7},
    )
    assert response.status_code == 200
    assert response.json()["removed_edges"]
    invalid = client.post(
        "/v1/scenarios/simulate",
        json={"removed_edges": ["NOT-AN-EDGE"]},
    )
    assert invalid.status_code == 422


def test_route_alternatives_endpoint():
    response = client.post(
        "/v1/routes/alternatives",
        json={"origin": "N0000", "destination": "N0507", "alternatives": 2},
    )
    assert response.status_code == 200
    assert len(response.json()["alternatives"]) == 2
