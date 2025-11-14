"""
Service for triggering GitHub Actions workflows
"""
import os
import asyncio
import httpx
from datetime import datetime, timezone, timedelta
from backend.services.github_app import get_installation_token, load_private_key, generate_jwt


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
            # Запоминаем время перед запуском
            trigger_time = datetime.now(timezone.utc)
            
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            # GitHub API не возвращает run_id в ответе на POST /dispatches
            # Возвращаем trigger_time, фронтенд будет опрашивать API для поиска run
            return {
                "success": True,
                "status_code": response.status_code,
                "message": "Workflow triggered successfully",
                "trigger_time": trigger_time.isoformat(),
                "workflow_url": f"https://github.com/{owner}/{repo}/actions/workflows/{workflow_id}"
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


async def find_workflow_run(
    owner: str,
    repo: str,
    workflow_id: str,
    trigger_time: datetime,
    ref: str = None
) -> dict:
    """
    Find workflow run by trigger time and actor (GitHub App)
    
    Args:
        owner: Repository owner
        repo: Repository name
        workflow_id: Workflow ID
        trigger_time: When workflow was triggered (datetime object)
        ref: Optional branch name to filter by
        
    Returns:
        Run data if found, None otherwise
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
    
    async with httpx.AsyncClient() as client:
        # Get app info to identify actor
        app_url = f"https://api.github.com/app"
        app_headers = {
            "Authorization": f"Bearer {generate_jwt(app_id, private_key)}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        app_slug = None
        try:
            app_response = await client.get(app_url, headers=app_headers)
            if app_response.status_code == 200:
                app_data = app_response.json()
                app_slug = app_data.get("slug")  # e.g., "github-action-executor"
        except Exception:
            pass  # Если не удалось получить app info, будем искать по времени
        
        # Get workflow runs
        runs_url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs"
        params = {
            "per_page": 20,
        }
        if ref:
            params["branch"] = ref
        
        runs_response = await client.get(runs_url, headers=headers, params=params)
        runs_response.raise_for_status()
        
        runs_data = runs_response.json()
        workflow_runs = runs_data.get("workflow_runs", [])
        
        # Find run where actor matches our app and created_at >= trigger_time
        for run in workflow_runs:
            actor = run.get("actor", {})
            actor_login = actor.get("login", "")
            actor_type = actor.get("type", "")
            created_at_str = run.get("created_at")
            run_ref = run.get("head_branch")
            
            # Проверяем ветку если указана
            if ref and run_ref != ref:
                continue
            
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    
                    # Check if run was created after trigger time (с небольшим запасом назад)
                    time_threshold = trigger_time.replace(microsecond=0) - timedelta(seconds=2)
                    
                    if created_at >= time_threshold:
                        # Check if actor is our GitHub App
                        # Actor can be app slug, app name, or [bot] format
                        is_our_app = False
                        
                        if app_slug:
                            # Проверяем по slug
                            if (actor_login == app_slug or 
                                actor_login == f"{app_slug}[bot]"):
                                is_our_app = True
                        
                        # Также проверяем по типу Bot (GitHub Apps всегда имеют type="Bot")
                        if actor_type == "Bot" and not is_our_app:
                            # Если это бот и мы не нашли по slug, проверяем что время совпадает
                            # (может быть другой бот, но вероятность низкая если время совпадает)
                            is_our_app = True
                        
                        if is_our_app:
                            return run
                except (ValueError, AttributeError):
                    pass
        
        return None

