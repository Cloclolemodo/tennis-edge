"""
Tests basiques de l'API.

Pour les lancer :  docker-compose exec api pytest
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Tennis Edge API"


def test_docs_available():
    """Swagger UI doit être accessible."""
    response = client.get("/docs")
    assert response.status_code == 200
