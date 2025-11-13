"""
GitHub App service for generating installation tokens
Based on: https://stackoverflow.com/questions/74892481/how-to-authenticate-a-github-actions-workflow-as-a-github-app-so-it-can-trigger
"""
import os
import time
import jwt
import httpx
from pathlib import Path


def load_private_key(key_path: str = None) -> str:
    """
    Load GitHub App private key from file or environment variable
    
    Args:
        key_path: Path to private key file
        
    Returns:
        Private key content as string
    """
    if key_path and Path(key_path).exists():
        with open(key_path, 'r') as f:
            return f.read()
    
    # Try to get from environment variable
    private_key = os.getenv("GITHUB_APP_PRIVATE_KEY")
    if private_key:
        return private_key
    
    raise ValueError("GitHub App private key not found. Set GITHUB_APP_PRIVATE_KEY_PATH or GITHUB_APP_PRIVATE_KEY")


def generate_jwt(app_id: str, private_key: str) -> str:
    """
    Generate JWT token for GitHub App authentication
    
    Args:
        app_id: GitHub App ID
        private_key: Private key content (PEM format)
        
    Returns:
        JWT token string
    """
    now = int(time.time())
    
    payload = {
        "iat": now - 60,  # Issued at time (60 seconds in the past to allow for clock skew)
        "exp": now + 600,  # Expiration time (10 minutes in the future)
        "iss": app_id  # Issuer (GitHub App ID)
    }
    
    token = jwt.encode(payload, private_key, algorithm="RS256")
    return token


async def get_installation_token(app_id: str, installation_id: str, private_key: str) -> str:
    """
    Get installation access token from GitHub API
    
    Args:
        app_id: GitHub App ID
        installation_id: Installation ID
        private_key: Private key content (PEM format)
        
    Returns:
        Installation access token
    """
    # Generate JWT
    jwt_token = generate_jwt(app_id, private_key)
    
    # Request installation token
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["token"]

