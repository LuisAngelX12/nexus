from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_request_id_is_generated() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers


def test_request_id_is_preserved() -> None:
    response = client.get(
        "/health",
        headers={
            "X-Request-ID": "TEST-123",
        },
    )

    assert response.headers["X-Request-ID"] == "TEST-123"
