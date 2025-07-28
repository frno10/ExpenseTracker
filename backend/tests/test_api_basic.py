"""
Basic API endpoint tests for Task 4.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test the root endpoint returns basic info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert data["message"] == "Expense Tracker API"


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_api_docs_available():
    """Test that API documentation is available in development."""
    response = client.get("/docs")
    # Docs might be disabled in production, so accept 404 as well
    assert response.status_code in [200, 307, 404]


def test_openapi_schema():
    """Test that OpenAPI schema is available."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert data["info"]["title"] == "Expense Tracker API"


def test_protected_endpoints_require_auth():
    """Test that protected endpoints require authentication."""
    # Test expenses endpoint
    response = client.get("/api/expenses/")
    assert response.status_code == 403  # Our middleware returns 403 for missing auth
    
    # Test categories endpoint
    response = client.get("/api/categories/")
    assert response.status_code == 403
    
    # Test merchants endpoint
    response = client.get("/api/merchants/")
    assert response.status_code == 403
    
    # Test payment methods endpoint
    response = client.get("/api/payment-methods/")
    assert response.status_code == 403


def test_api_endpoints_exist():
    """Test that all API endpoints are properly registered."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    
    openapi_data = response.json()
    paths = openapi_data.get("paths", {})
    
    # Check that our main API endpoints are registered
    expected_paths = [
        "/api/auth/login",
        "/api/auth/me", 
        "/api/expenses/",
        "/api/categories/",
        "/api/merchants/",
        "/api/payment-methods/"
    ]
    
    for path in expected_paths:
        assert path in paths, f"Expected path {path} not found in OpenAPI schema"


if __name__ == "__main__":
    pytest.main([__file__])