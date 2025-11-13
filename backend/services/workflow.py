"""
Service for triggering GitHub Actions workflows
"""
import os
import httpx
from backend.services.github_app import get_installation_token, load_private_key


async def trigger_workflow(
    owner: str,
    repo: str,
    workflow_id: str,
    inputs: dict = None,
    ref: str = "main"
) -> dict:
    """
    Trigger a GitHub Actions workflow using GitHub App authentication
    
    Args:
        owner: Repository owner
        repo: Repository name
        workflow_id: Workflow file name (e.g., "ci.yml") or workflow ID
        inputs: Input parameters for workflow_dispatch
        ref: Branch or tag to run workflow on (default: "main")
        
    Returns:
        Response dictionary with status and message
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
    
    # Trigger workflow
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"
    headers = {
        "Authorization": f"token {installation_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    payload = {
        "ref": ref,
        "inputs": inputs or {}
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            return {
                "success": True,
                "status_code": response.status_code,
                "message": "Workflow triggered successfully"
            }
    except httpx.HTTPStatusError as e:
        error_message = "Unknown error"
        try:
            error_data = e.response.json()
            error_message = error_data.get("message", str(e))
        except:
            error_message = str(e)
        
        return {
            "success": False,
            "status_code": e.response.status_code,
            "message": f"Failed to trigger workflow: {error_message}"
        }

