"""Test básico de health check — ampliar en Sección 10."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "transactions_loaded" in data
    assert "models_loaded" in data
