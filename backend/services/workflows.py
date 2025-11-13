"""
Service for getting repository workflows from GitHub API
"""
import os
import logging
import httpx
from backend.services.github_app import get_installation_token, load_private_key

logger = logging.getLogger(__name__)


async def get_workflows(owner: str, repo: str) -> list:
    """
    Get list of workflows from repository
    
    Args:
        owner: Repository owner
        repo: Repository name
        
    Returns:
        List of workflows with id and name
        Format: [{"id": "workflow_id", "name": "Workflow Name", "path": ".github/workflows/ci.yml"}, ...]
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
            # Get workflows
            workflows_url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows"
            response = await client.get(
                workflows_url,
                headers=headers,
                params={"per_page": 100}  # GitHub default is 30, max is 100
            )
            response.raise_for_status()
            
            workflows_data = response.json()
            workflows_list = []
            
            for workflow in workflows_data.get("workflows", []):
                # Extract workflow file name from path
                path = workflow.get("path", "")
                workflow_id = path.split("/")[-1] if "/" in path else path
                
                workflows_list.append({
                    "id": workflow_id,
                    "name": workflow.get("name", workflow_id),
                    "path": path,
                    "state": workflow.get("state", "active")
                })
            
            # Sort by name
            workflows_list.sort(key=lambda x: x["name"].lower())
            logger.info(f"Retrieved {len(workflows_list)} workflows for {owner}/{repo}")
            return workflows_list
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to get workflows: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting workflows: {str(e)}", exc_info=True)
        raise

