"""
Health and API root endpoint tests.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Test GET /health returns 200 and expected payload."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "mota-scholarship-backend"
    }


def test_api_v1_root():
    """Test GET /api/v1 returns API metadata."""
    response = client.get("/api/v1")
    assert response.status_code == 200
    assert response.json() == {
        "message": "MoTA Scholarship API",
        "version": "1.0.0"
    }


def test_api_v1_slash():
    """Test GET /api/v1/ returns API metadata."""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "MoTA Scholarship API",
        "version": "1.0.0"
    }
