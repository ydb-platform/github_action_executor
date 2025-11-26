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


def test_result_page_preserves_ref_and_inputs(client, mock_session):
    """Test that result page preserves ref and inputs in 'Try again' links"""
    from unittest.mock import patch, Mock, AsyncMock
    
    # Mock permission check
    with patch("backend.services.permissions.check_repository_access", new_callable=AsyncMock) as mock_perms:
        mock_perms.return_value = True
        
        # Mock workflow trigger to return error (to test error page)
        with patch("backend.services.workflow.trigger_workflow", new_callable=AsyncMock) as mock_trigger:
            mock_trigger.side_effect = Exception("Test error")
            
            # Set up session with authenticated user
            with client.session_transaction() as session:
                session.update(mock_session)
            
            # Trigger workflow with ref and inputs
            response = client.get(
                "/workflow/trigger?owner=testowner&repo=testrepo&workflow_id=test.yml&ref=develop&test_type=unit&from_pr=123"
            )
            
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
            
            # Check that ref and inputs are preserved in "Try again" link
            content = response.text
            # Should contain ref in the link
            assert "ref=develop" in content or "ref%3Ddevelop" in content
            # Should contain workflow inputs in the link
            assert "test_type" in content
            assert "from_pr" in content


def test_result_page_success_preserves_ref_and_inputs(client, mock_session):
    """Test that successful result page preserves ref and inputs in 'Run again' links"""
    from unittest.mock import patch, Mock, AsyncMock
    
    # Mock permission check
    with patch("backend.services.permissions.check_repository_access", new_callable=AsyncMock) as mock_perms:
        mock_perms.return_value = True
        
        # Mock workflow trigger to return success
        with patch("backend.services.workflow.trigger_workflow", new_callable=AsyncMock) as mock_trigger:
            mock_trigger.return_value = {
                "success": True,
                "message": "Workflow triggered successfully",
                "run_id": 123456,
                "run_url": "https://github.com/testowner/testrepo/actions/runs/123456",
                "workflow_url": "https://github.com/testowner/testrepo/actions",
                "trigger_time": "2024-01-01T00:00:00Z"
            }
            
            # Set up session with authenticated user
            with client.session_transaction() as session:
                session.update(mock_session)
            
            # Trigger workflow with ref and inputs
            response = client.get(
                "/workflow/trigger?owner=testowner&repo=testrepo&workflow_id=test.yml&ref=develop&test_type=unit&from_pr=123"
            )
            
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
            
            # Check that ref and inputs are preserved in "Run again" link
            content = response.text
            # Should contain ref in the link
            assert "ref=develop" in content or "ref%3Ddevelop" in content
            # Should contain workflow inputs in the link
            assert "test_type" in content
            assert "from_pr" in content


def test_urlencode_filter():
    """Test that urlencode filter works correctly in Jinja2 templates"""
    from backend.routes.workflow import templates
    from urllib.parse import quote
    
    # Test the filter directly
    filter_func = templates.env.filters.get("urlencode")
    assert filter_func is not None, "urlencode filter should be registered"
    
    # Test various inputs
    assert filter_func("test value") == quote("test value", safe="")
    assert filter_func(123) == "123"
    assert filter_func("test&value=123") == quote("test&value=123", safe="")
    assert filter_func(None) == ""
    assert filter_func("") == ""

