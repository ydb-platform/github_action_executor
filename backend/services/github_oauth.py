"""
GitHub OAuth service for user authentication
"""
import os
import httpx
from urllib.parse import urlencode


GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_URL = "https://api.github.com/user"


def get_oauth_url(state: str = None) -> str:
    """
    Generate GitHub OAuth authorization URL
    
    Args:
        state: Optional state parameter for CSRF protection
        
    Returns:
        OAuth authorization URL
    """
    client_id = os.getenv("GITHUB_CLIENT_ID")
    callback_url = os.getenv("GITHUB_CALLBACK_URL", "http://localhost:8000/auth/github/callback")
    
    params = {
        "client_id": client_id,
        "redirect_uri": callback_url,
        "scope": "read:user"
    }
    
    if state:
        params["state"] = state
    
    return f"{GITHUB_AUTH_URL}?{urlencode(params)}"


async def get_access_token(code: str) -> str:
    """
    Exchange authorization code for access token
    
    Args:
        code: Authorization code from GitHub
        
    Returns:
        Access token
    """
    client_id = os.getenv("GITHUB_CLIENT_ID")
    client_secret = os.getenv("GITHUB_CLIENT_SECRET")
    callback_url = os.getenv("GITHUB_CALLBACK_URL", "http://localhost:8000/auth/github/callback")
    
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": callback_url
    }
    
    headers = {
        "Accept": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(GITHUB_TOKEN_URL, data=data, headers=headers)
        response.raise_for_status()
        result = response.json()
        return result["access_token"]


async def get_user_info(access_token: str) -> dict:
    """
    Get authenticated user information from GitHub
    
    Args:
        access_token: GitHub OAuth access token
        
    Returns:
        User information dictionary
    """
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(GITHUB_API_URL, headers=headers)
        response.raise_for_status()
        return response.json()

