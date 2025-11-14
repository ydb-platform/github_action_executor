"""
Service for checking user permissions and collaborator access
"""
import httpx
import logging

logger = logging.getLogger(__name__)


async def check_repository_access(owner: str, repo: str, access_token: str) -> bool:
    """
    Check if user has access to the repository
    
    Args:
        owner: Repository owner
        repo: Repository name
        access_token: GitHub OAuth access token
        
    Returns:
        True if user has access, False otherwise
    """
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                logger.info(f"User HAS access to {owner}/{repo} (collaborator)")
                return True
            elif response.status_code == 401:
                # Unauthorized - token invalid, expired, or insufficient permissions
                logger.warning(f"Unauthorized access to {owner}/{repo}. Token may be invalid, expired, or lack required scopes.")
                return False
            elif response.status_code == 403:
                # Forbidden - user doesn't have permission to access this repository
                logger.warning(f"Forbidden: Cannot access {owner}/{repo}. User may not have repository access.")
                return False
            elif response.status_code == 404:
                # Repository not found or no access
                logger.warning(f"Repository {owner}/{repo} not found or no access")
                return False
            else:
                logger.warning(f"Unexpected status code when checking repository access for {owner}/{repo}: {response.status_code}")
                return False
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (401, 403, 404):
            logger.warning(f"HTTP {e.response.status_code} when checking repository access for {owner}/{repo}: {e.response.text}")
            return False
        logger.error(f"HTTP error checking repository access for {owner}/{repo}: {e.response.status_code} - {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"Error checking repository access for {owner}/{repo}: {str(e)}")
        return False

