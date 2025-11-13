"""
Service for triggering GitHub Actions workflows
"""
import os
import asyncio
import httpx
from datetime import datetime, timezone
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
            # Запоминаем время перед запуском
            trigger_time = datetime.now(timezone.utc)
            
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            # Попытаемся получить run_id из последнего запуска workflow
            # GitHub может не сразу создать новый run, поэтому ждем немного и проверяем несколько раз
            run_id = None
            run_url = None
            
            try:
                # Небольшая задержка, чтобы GitHub успел создать run
                await asyncio.sleep(1)
                
                # Получаем последние workflow runs и ищем тот, который был создан после нашего запроса
                runs_url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs"
                
                # Пробуем несколько раз с небольшими задержками
                for attempt in range(3):
                    runs_response = await client.get(
                        runs_url,
                        headers=headers,
                        params={"per_page": 5}  # Берем больше, чтобы найти новый
                    )
                    
                    if runs_response.status_code == 200:
                        runs_data = runs_response.json()
                        workflow_runs = runs_data.get("workflow_runs", [])
                        
                        if workflow_runs:
                            # Ищем run, который был создан после нашего запроса
                            # Или просто берем самый свежий, если не нашли по времени
                            for run in workflow_runs:
                                created_at_str = run.get("created_at")
                                if created_at_str:
                                    try:
                                        # Парсим время создания run
                                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                                        
                                        # Если run создан после нашего запроса (с небольшим запасом)
                                        if created_at >= trigger_time.replace(microsecond=0):
                                            run_id = run.get("id")
                                            run_url = run.get("html_url")
                                            break
                                    except (ValueError, AttributeError):
                                        pass
                            
                            # Если не нашли по времени, берем самый первый (самый свежий)
                            if not run_id and workflow_runs:
                                run = workflow_runs[0]
                                run_id = run.get("id")
                                run_url = run.get("html_url")
                            
                            if run_id:
                                break
                    
                    # Если не нашли, ждем еще немного
                    if attempt < 2:
                        await asyncio.sleep(0.5)
                        
            except Exception as e:
                # Если не удалось получить run_id - не критично
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to get run_id after workflow trigger: {str(e)}")
            
            return {
                "success": True,
                "status_code": response.status_code,
                "message": "Workflow triggered successfully",
                "run_id": run_id,
                "run_url": run_url,
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

