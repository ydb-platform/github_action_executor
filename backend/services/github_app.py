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
    import logging
    logger = logging.getLogger(__name__)
    
    now = int(time.time())
    
    # Ensure app_id is a string (GitHub expects it as string in JWT)
    app_id_str = str(app_id)
    
    payload = {
        "iat": now - 60,  # Issued at time (60 seconds in the past to allow for clock skew)
        "exp": now + 600,  # Expiration time (10 minutes in the future)
        "iss": app_id_str  # Issuer (GitHub App ID as string)
    }
    
    try:
        # Clean up private key - remove any extra whitespace
        private_key_clean = private_key.strip()
        
        # Ensure key has proper line endings
        if not private_key_clean.endswith('\n'):
            private_key_clean += '\n'
        
        logger.debug(f"Generating JWT for App ID: {app_id_str}, key length: {len(private_key_clean)}")
        token = jwt.encode(payload, private_key_clean, algorithm="RS256")
        logger.debug(f"JWT generated successfully, token length: {len(token)}")
        return token
    except Exception as e:
        logger.error(f"Failed to generate JWT: {str(e)}", exc_info=True)
        raise


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
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Generate JWT
        logger.info(f"Generating JWT for App ID: {app_id}, Installation ID: {installation_id}")
        jwt_token = generate_jwt(app_id, private_key)
        logger.debug(f"JWT token generated: {jwt_token[:50]}...")
        
        # Request installation token
        url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers)
            if response.status_code != 201:
                error_text = response.text
                logger.error(f"Failed to get installation token: {response.status_code} - {error_text}")
                try:
                    error_json = response.json()
                    error_msg = error_json.get("message", error_text)
                    logger.error(f"GitHub API error: {error_msg}")
                except:
                    pass
                response.raise_for_status()
            data = response.json()
            logger.info("Installation token obtained successfully")
            return data["token"]
    except Exception as e:
        logger.error(f"Error getting installation token: {str(e)}", exc_info=True)
        raise

