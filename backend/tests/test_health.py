from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_200() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"


def test_health_response_body() -> None:
    client = TestClient(app)
    response = client.get("/health")
    data = response.json()
    assert data == {"status": "ok", "service": "tradepilot-backend"}, (
        f"Unexpected response body: {data}"
    )


def test_health_no_db_required() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
