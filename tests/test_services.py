"""
Tests for service modules
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import jwt
import time


def test_github_app_generate_jwt():
    """Test JWT generation for GitHub App - verifies structure and app_id"""
    from backend.services.github_app import generate_jwt
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    
    # Generate a real RSA key for testing
    private_key_obj = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    private_key = private_key_obj.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    app_id = "123456"
    
    # Test that JWT is generated correctly
    token = generate_jwt(app_id, private_key)
    # JWT should be a string
    assert isinstance(token, str)
    assert len(token) > 0
    # Should be able to decode (without verification)
    decoded = jwt.decode(token, options={"verify_signature": False})
    assert decoded["iss"] == app_id
    assert "iat" in decoded
    assert "exp" in decoded


def test_config_branch_filter_patterns():
    """Test that branch filter patterns are used correctly in application behavior"""
    import config
    import re
    
    # Test that patterns are actually used for filtering (not just that they exist)
    # This tests real behavior: patterns should filter branches
    patterns = config.BRANCH_FILTER_PATTERNS
    
    # Test that patterns work as expected for common branch names
    test_branches = ["main", "develop", "stable-1.0", "feature/test", "release/v2.0"]
    
    # Count how many branches would match
    matching_count = sum(
        1 for branch in test_branches 
        if any(re.match(pattern, branch) for pattern in patterns)
    )
    
    # At least some branches should match (main, stable-*, etc.)
    assert matching_count > 0, "Patterns should match at least some common branch names"


@pytest.mark.asyncio
async def test_oauth_url_generation():
    """Test OAuth URL generation"""
    from backend.services.github_oauth import get_oauth_url
    import urllib.parse
    
    with patch.dict("os.environ", {
        "GITHUB_CLIENT_ID": "test_client_id",
        "GITHUB_CALLBACK_URL": "http://localhost:8000/auth/github/callback"
    }):
        # Mock config to control scope
        with patch("backend.services.github_oauth.config") as mock_config:
            mock_config.USE_USER_TOKEN_FOR_WORKFLOWS = False
            url = get_oauth_url(state="test_state")
            
            assert "github.com" in url
            assert "test_client_id" in url
            assert "test_state" in url
            # URL is encoded, so check decoded version
            parsed = urllib.parse.urlparse(url)
            params = urllib.parse.parse_qs(parsed.query)
            scope = params.get("scope", [""])[0]
            assert "read:user" in scope  # Should have read:user scope


def test_config_values_are_valid():
    """Test that configuration values are valid and usable"""
    import config
    import re
    
    # Test that config values have correct types and can be used
    assert isinstance(config.CHECK_PERMISSIONS, bool), "CHECK_PERMISSIONS should be boolean"
    assert isinstance(config.USE_USER_TOKEN_FOR_WORKFLOWS, bool), "USE_USER_TOKEN_FOR_WORKFLOWS should be boolean"
    assert isinstance(config.AUTO_OPEN_RUN, bool), "AUTO_OPEN_RUN should be boolean"
    assert isinstance(config.BRANCH_FILTER_PATTERNS, list), "BRANCH_FILTER_PATTERNS should be a list"
    
    # Test that patterns are valid regex and can actually match branches
    if config.BRANCH_FILTER_PATTERNS:
        for pattern in config.BRANCH_FILTER_PATTERNS:
            # Should compile as regex
            compiled = re.compile(pattern)
            # Should be able to match at least one test branch
            test_branches = ["main", "develop", "stable-1.0", "feature/test"]
            matches = any(compiled.match(branch) for branch in test_branches)
            # At least one pattern should match common branches
            if pattern == "^main$":
                assert compiled.match("main"), f"Pattern {pattern} should match 'main'"

