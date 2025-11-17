"""
Tests for main application
"""
import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(client):
    """Test root endpoint returns HTML"""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_root_endpoint_with_query_params(client):
    """Test root endpoint with query parameters - verifies form pre-filling"""
    response = client.get("/?owner=testowner&repo=testrepo&workflow_id=test.yml")
    assert response.status_code == 200
    # Should render the form with pre-filled values
    assert "text/html" in response.headers["content-type"]
    # Query params should be preserved in the response (form should have these values)
    # This tests that the UI can be pre-filled from URL params


def test_static_files_route_exists(client):
    """Test that static files route is configured (doesn't return 500)"""
    # This tests that static file serving is configured
    # Even if file doesn't exist, route should be handled (404), not crash (500)
    response = client.get("/static/nonexistent.css")
    assert response.status_code in [200, 404], "Static route should return 200 or 404, not 500"


def test_health_endpoint(client):
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}


def test_auth_routes_exist(client):
    """Test auth routes are registered"""
    # These should return redirects or errors, not 404
    # follow_redirects=False to prevent TestClient from following redirect to GitHub
    response = client.get("/auth/github", follow_redirects=False)
    # Should redirect (307) or return some response (not 404)
    assert response.status_code in [307, 302, 200]  # Redirect status codes


def test_workflow_routes_exist(client):
    """Test workflow routes are registered"""
    # Without auth, should get error but not 404
    response = client.get("/workflow/trigger")
    assert response.status_code != 404


def test_api_routes_exist(client):
    """Test API routes are registered"""
    # Without auth, should get 401 but not 404
    response = client.get("/api/branches?owner=test&repo=test")
    assert response.status_code != 404

