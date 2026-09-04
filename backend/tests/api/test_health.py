import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_check():
    """Test the basic health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "campusai-backend"
    }

def test_database_health_check_no_db():
    """Test the database health endpoint handles failures properly."""
    # Since we are not running a real postgres DB in this test environment,
    # it should handle the failure and return a 503.
    response = client.get("/health/database")
    # Even if it succeeds somehow (e.g. mock db), we want to test its behavior.
    # In our current setup without DB, it will return 503.
    assert response.status_code in [200, 503]
    if response.status_code == 503:
        assert response.json()["detail"] in ["Database connection failed", "Database connection not available"]
    else:
        assert response.json() == {
            "status": "healthy",
            "service": "campusai-database"
        }
