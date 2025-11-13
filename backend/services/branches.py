"""
Service for getting repository branches from GitHub API
"""
import os
import logging
import httpx
from backend.services.github_app import get_installation_token, load_private_key

logger = logging.getLogger(__name__)


async def get_branches(owner: str, repo: str) -> list:
    """
    Get list of branches from repository
    
    Args:
        owner: Repository owner
        repo: Repository name
        
    Returns:
        List of branch names (sorted, main/master first)
    """
    # Get GitHub App credentials
    app_id = os.getenv("GITHUB_APP_ID")
    installation_id = os.getenv("GITHUB_APP_INSTALLATION_ID")
    private_key_path = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")
    
    if not all([app_id, installation_id]):
        raise ValueError("GITHUB_APP_ID and GITHUB_APP_INSTALLATION_ID must be set")
    
    # Load private key and get installation token
    private_key = load_private_key(private_key_path)
    installation_token = await get_installation_token(app_id, installation_id, private_key)
    
    headers = {
        "Authorization": f"token {installation_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # Get branches (up to 100 by default)
            branches_url = f"https://api.github.com/repos/{owner}/{repo}/branches"
            response = await client.get(
                branches_url,
                headers=headers,
                params={"per_page": 100}  # GitHub default is 30, max is 100
            )
            response.raise_for_status()
            
            branches_data = response.json()
            branch_names = [branch["name"] for branch in branches_data]
            
            # Sort: main/master first, then alphabetically
            def sort_key(name):
                if name in ["main", "master"]:
                    return (0, name)
                return (1, name)
            
            branch_names.sort(key=sort_key)
            logger.info(f"Retrieved {len(branch_names)} branches for {owner}/{repo}")
            return branch_names
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to get branches: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting branches: {str(e)}", exc_info=True)
        raise

