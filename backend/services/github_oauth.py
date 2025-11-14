"""
GitHub OAuth service for user authentication
"""
import os
import logging
import httpx
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


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
        "scope": "read:user repo"  # read:user for user info, repo for triggering workflows (workflow_dispatch requires repo scope)
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
    
    if not client_id:
        logger.error("GITHUB_CLIENT_ID is not set")
        raise ValueError("GITHUB_CLIENT_ID is not set")
    if not client_secret:
        logger.error("GITHUB_CLIENT_SECRET is not set")
        raise ValueError("GITHUB_CLIENT_SECRET is not set")
    
    logger.info(f"Exchanging code for token - Client ID: {client_id[:10]}..., Callback: {callback_url}")
    
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": callback_url
    }
    
    headers = {
        "Accept": "application/json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            logger.debug(f"POST to {GITHUB_TOKEN_URL} with data: client_id={client_id[:10]}..., code={code[:10]}...")
            response = await client.post(GITHUB_TOKEN_URL, data=data, headers=headers)
            
            logger.info(f"GitHub token response status: {response.status_code}")
            
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"GitHub API error ({response.status_code}): {error_text}")
                try:
                    error_json = response.json()
                    error_msg = error_json.get("error_description", error_json.get("error", error_text))
                    raise ValueError(f"GitHub API error: {error_msg}")
                except:
                    raise ValueError(f"GitHub API error ({response.status_code}): {error_text}")
            
            result = response.json()
            logger.debug(f"GitHub response keys: {list(result.keys())}")
            
            if "access_token" not in result:
                error_msg = result.get("error_description", result.get("error", "Unknown error"))
                logger.error(f"GitHub did not return access_token: {error_msg}")
                logger.error(f"Full response: {result}")
                raise ValueError(f"GitHub did not return access_token: {error_msg}")
            
            logger.info("Access token obtained successfully")
            return result["access_token"]
    except httpx.HTTPError as e:
        logger.error(f"HTTP error while exchanging code for token: {str(e)}", exc_info=True)
        raise ValueError(f"HTTP error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error while exchanging code for token: {str(e)}", exc_info=True)
        raise


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
    
    try:
        async with httpx.AsyncClient() as client:
            logger.debug(f"GET {GITHUB_API_URL} with token: {access_token[:10]}...")
            response = await client.get(GITHUB_API_URL, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"GitHub API error getting user info: {response.status_code} - {response.text}")
                response.raise_for_status()
            
            user_info = response.json()
            logger.info(f"User info retrieved: login={user_info.get('login')}, id={user_info.get('id')}")
            return user_info
    except httpx.HTTPError as e:
        logger.error(f"HTTP error while getting user info: {str(e)}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error while getting user info: {str(e)}", exc_info=True)
        raise

