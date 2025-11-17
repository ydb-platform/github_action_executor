"""
Service for triggering GitHub Actions workflows
"""
import os
import asyncio
import httpx
import logging
from datetime import datetime, timezone, timedelta
from backend.services.github_app import get_installation_token, load_private_key, generate_jwt

logger = logging.getLogger(__name__)


async def trigger_workflow(
    owner: str,
    repo: str,
    workflow_id: str,
    inputs: dict = None,
    ref: str = "main",
    user_token: str = None
) -> dict:
    """
    Trigger a GitHub Actions workflow using GitHub App or user OAuth token
    
    Args:
        owner: Repository owner
        repo: Repository name
        workflow_id: Workflow file name (e.g., "ci.yml") or workflow ID
        inputs: Input parameters for workflow_dispatch
        ref: Branch or tag to run workflow on (default: "main")
        user_token: Optional user OAuth token. If provided, workflow will be triggered as this user.
                   If None, uses GitHub App authentication.
        
    Returns:
        Response dictionary with status and message
    """
    # Use user token if provided, otherwise use GitHub App
    if user_token:
        auth_token = user_token
        logger.info(f"Triggering workflow {owner}/{repo}/{workflow_id} as authenticated user")
    else:
        # Get GitHub App credentials
        app_id = os.getenv("GITHUB_APP_ID")
        installation_id = os.getenv("GITHUB_APP_INSTALLATION_ID")
        private_key_path = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")
        
        if not all([app_id, installation_id]):
            raise ValueError("GITHUB_APP_ID and GITHUB_APP_INSTALLATION_ID must be set")
        
        # Load private key and get installation token
        private_key = load_private_key(private_key_path)
        auth_token = await get_installation_token(app_id, installation_id, private_key)
        logger.info(f"Triggering workflow {owner}/{repo}/{workflow_id} as GitHub App")
    
    # Trigger workflow
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"
    headers = {
        "Authorization": f"token {auth_token}",
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
        user_friendly_message = None
        
        try:
            error_data = e.response.json()
            error_message = error_data.get("message", str(e))
            
            # GitHub API returns "Must have admin rights to Repository", 
            # but actually Write permission is sufficient
            if "admin" in error_message.lower() and "right" in error_message.lower():
                user_friendly_message = (
                    f"Insufficient permissions to trigger workflow.\n\n"
                    f"GitHub API requires Write permission (or higher) in the repository to trigger workflows via API.\n"
                    f"Note: The error message mentions 'admin rights', but Write permission is sufficient.\n\n"
                    f"What to do:\n"
                    f"1. Ensure you have Write (or higher) permission in repository {owner}/{repo}\n"
                    f"2. If repository is in an organization, check organization settings:\n"
                    f"   - Organization Settings → Policies → Actions → enable Actions\n"
                    f"   - Organization Settings → Policies → Actions → Workflow permissions → Read and write\n"
                    f"3. Check permissions: Repo → Settings → Collaborators & teams\n\n"
                    f"Alternative: Set USE_USER_TOKEN_FOR_WORKFLOWS=false to use GitHub App account instead"
                )
        except:
            error_message = str(e)
        
        logger.error(f"Failed to trigger workflow: {error_message} (status: {e.response.status_code})")
        
        # Используем понятное сообщение, если доступно, иначе оригинальное
        final_message = user_friendly_message if user_friendly_message else f"Failed to trigger workflow: {error_message}"
        
        return {
            "success": False,
            "status_code": e.response.status_code,
            "message": final_message
        }


async def find_workflow_run(
    owner: str,
    repo: str,
    workflow_id: str,
    trigger_time: datetime,
    ref: str = None,
    user_token: str = None,
    expected_actor_login: str = None
) -> dict:
    """
    Find workflow run by trigger time and actor (GitHub App or User)
    
    Args:
        owner: Repository owner
        repo: Repository name
        workflow_id: Workflow ID
        trigger_time: When workflow was triggered (datetime object)
        ref: Optional branch name to filter by
        user_token: Optional user OAuth token. If provided, searches for runs triggered by this user.
        expected_actor_login: Optional expected actor login (username). Used when searching for user-triggered runs.
        
    Returns:
        Run data if found, None otherwise
    """
    # Use user token if provided, otherwise use GitHub App
    if user_token:
        auth_token = user_token
        logger.info(f"Searching for workflow run {owner}/{repo}/{workflow_id} triggered by user")
    else:
        # Get GitHub App credentials
        app_id = os.getenv("GITHUB_APP_ID")
        installation_id = os.getenv("GITHUB_APP_INSTALLATION_ID")
        private_key_path = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")
        
        if not all([app_id, installation_id]):
            raise ValueError("GITHUB_APP_ID and GITHUB_APP_INSTALLATION_ID must be set")
        
        # Load private key and get installation token
        private_key = load_private_key(private_key_path)
        auth_token = await get_installation_token(app_id, installation_id, private_key)
        logger.info(f"Searching for workflow run {owner}/{repo}/{workflow_id} triggered by GitHub App")
    
    headers = {
        "Authorization": f"token {auth_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    async with httpx.AsyncClient() as client:
        # Get app info to identify actor (only if using GitHub App)
        app_slug = None
        if not user_token:
            app_id = os.getenv("GITHUB_APP_ID")
            private_key_path = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")
            if app_id and private_key_path:
                private_key = load_private_key(private_key_path)
                app_url = f"https://api.github.com/app"
                app_headers = {
                    "Authorization": f"Bearer {generate_jwt(app_id, private_key)}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
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
        
        # Фильтруем runs по времени и другим критериям
        # Ищем самый свежий run, созданный после trigger_time
        candidate_runs = []
        
        # Определяем временное окно для поиска (от trigger_time до 30 секунд после)
        time_window_start = trigger_time - timedelta(seconds=5)  # Небольшой запас назад
        time_window_end = trigger_time + timedelta(seconds=30)   # Окно в будущее
        
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
                    
                    # Проверяем, что run создан в нашем временном окне
                    if time_window_start <= created_at <= time_window_end:
                        is_match = False
                        
                        if user_token and expected_actor_login:
                            # Ищем run от имени пользователя
                            if actor_login == expected_actor_login and actor_type == "User":
                                is_match = True
                                logger.debug(f"Found candidate user run: id={run.get('id')}, created_at={created_at_str}, actor={actor_login}")
                        else:
                            # Ищем run от имени GitHub App
                            if app_slug:
                                # Проверяем по slug
                                if (actor_login == app_slug or 
                                    actor_login == f"{app_slug}[bot]"):
                                    is_match = True
                            
                            # Также проверяем по типу Bot
                            # GitHub Apps всегда имеют type="Bot"
                            if actor_type == "Bot":
                                # Если app_slug не совпал, но это бот и время совпадает,
                                # считаем что это наш запуск (вероятность другого бота низкая)
                                if not app_slug or is_match:
                                    is_match = True
                            
                            if is_match:
                                logger.debug(f"Found candidate app run: id={run.get('id')}, created_at={created_at_str}, actor={actor_login}")
                        
                        if is_match:
                            candidate_runs.append((created_at, run))
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Error parsing created_at for run: {e}")
                    pass
        
        # Если нашли подходящие runs, возвращаем самый свежий (самый поздний по времени)
        if candidate_runs:
            # Сортируем по времени создания (самый свежий первым)
            candidate_runs.sort(key=lambda x: x[0], reverse=True)
            _, best_run = candidate_runs[0]
            run_id = best_run.get("id")
            run_url = best_run.get("html_url")
            logger.info(f"Found workflow run: id={run_id}, url={run_url}")
            return best_run
        
        logger.warning(f"Workflow run not found for {owner}/{repo}/{workflow_id} triggered at {trigger_time}")
        return None

