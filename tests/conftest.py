"""
Pytest configuration and fixtures
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import os

# Set test environment variables before importing app
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["GITHUB_CLIENT_ID"] = "test_client_id"
os.environ["GITHUB_CLIENT_SECRET"] = "test_client_secret"
os.environ["GITHUB_APP_ID"] = "123456"
os.environ["GITHUB_APP_INSTALLATION_ID"] = "12345678"
os.environ["CHECK_PERMISSIONS"] = "false"  # Disable permission checks in tests
os.environ["USE_USER_TOKEN_FOR_WORKFLOWS"] = "false"

from app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def mock_session():
    """Mock session with authenticated user"""
    return {
        "user": {
            "login": "testuser",
            "name": "Test User",
            "avatar_url": "https://github.com/testuser.png"
        },
        "access_token": "test_access_token_12345"
    }


@pytest.fixture
def mock_github_response():
    """Mock GitHub API response"""
    def _create_response(data, status_code=200):
        response = Mock()
        response.status_code = status_code
        response.json.return_value = data
        response.raise_for_status = Mock()
        return response
    return _create_response

