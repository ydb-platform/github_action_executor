"""
Workflow routes for triggering GitHub Actions
"""
import os
import logging
from fastapi import APIRouter, Request, HTTPException, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from backend.services.permissions import is_contributor, check_repository_access
from backend.services.workflow import trigger_workflow
from backend.services.workflow_info import get_workflow_info
from backend.services.branches import get_branches
from backend.services.workflows import get_workflows
from backend.services.github_oauth import get_oauth_url

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")


@router.get("/form", response_class=HTMLResponse)
async def workflow_form(
    request: Request,
    owner: str = None,
    repo: str = None,
    workflow_id: str = None,
    ref: str = None
):
    """Display workflow trigger form with dynamic inputs"""
    # Check authentication
    user = request.session.get("user")
    access_token = request.session.get("access_token")
    
    if not user or not access_token:
        # Redirect to login
        oauth_url = get_oauth_url()
        return RedirectResponse(url=oauth_url)
    
    # Use defaults if not provided
    owner = owner or os.getenv("DEFAULT_REPO_OWNER")
    repo = repo or os.getenv("DEFAULT_REPO_NAME")
    workflow_id = workflow_id or os.getenv("DEFAULT_WORKFLOW_ID")
    ref = ref or "main"
    
    # Get workflow information including inputs
    workflow_info = None
    inputs_schema = {}
    try:
        if owner and repo and workflow_id:
            logger.info(f"Getting workflow info for {owner}/{repo}/{workflow_id}")
            workflow_info = await get_workflow_info(owner, repo, workflow_id)
            logger.info(f"Workflow info found: {workflow_info.get('found')}, inputs count: {len(workflow_info.get('inputs', {}))}")
            
            if workflow_info.get("found"):
                inputs_schema = workflow_info.get("inputs", {})
                logger.info(f"Inputs schema keys: {list(inputs_schema.keys())}")
                for key, value in inputs_schema.items():
                    logger.debug(f"Input '{key}': {value}")
            else:
                logger.warning(f"Workflow {workflow_id} not found in {owner}/{repo}")
    except Exception as e:
        logger.error(f"Failed to get workflow info: {str(e)}", exc_info=True)
        # Continue without workflow info - form will work with default fields
    
    # Get branches and workflows lists
    branches = []
    workflows_list = []
    try:
        if owner and repo:
            # Получаем ветки и workflows параллельно
            import asyncio
            branches_task = get_branches(owner, repo)
            workflows_task = get_workflows(owner, repo)
            branches, workflows_list = await asyncio.gather(
                branches_task,
                workflows_task,
                return_exceptions=True
            )
            
            # Обработка исключений
            if isinstance(branches, Exception):
                logger.warning(f"Failed to get branches: {str(branches)}")
                branches = []
            if isinstance(workflows_list, Exception):
                logger.warning(f"Failed to get workflows: {str(workflows_list)}")
                workflows_list = []
    except Exception as e:
        logger.warning(f"Failed to get branches/workflows: {str(e)}")
        # Continue without branches/workflows - user can type manually
    
    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "user": user,
            "owner": owner,
            "repo": repo,
            "workflow_id": workflow_id,
            "ref": ref,
            "workflow_info": workflow_info,
            "inputs_schema": inputs_schema,
            "branches": branches,
            "workflows": workflows_list
        }
    )


async def _trigger_and_show_result(
    request: Request,
    owner: str,
    repo: str,
    workflow_id: str,
    ref: str,
    inputs: dict,
    return_json: bool = False
):
    """Вспомогательная функция для запуска workflow и показа результата"""
    # Check authentication
    user = request.session.get("user")
    access_token = request.session.get("access_token")
    
    if not user or not access_token:
        # Save current URL for redirect after OAuth
        current_url = str(request.url)
        request.session["oauth_redirect_after"] = current_url
        logger.info(f"No session found, saving redirect URL: {current_url}")
        
        # Redirect to login
        oauth_url = get_oauth_url()
        if return_json:
            raise HTTPException(
                status_code=401,
                detail="Not authenticated. Please authorize via OAuth first.",
                headers={"Location": oauth_url}
            )
        return RedirectResponse(url=oauth_url)
    
    # Check if user is a contributor
    username = user["login"]
    is_contrib = await is_contributor(owner, repo, username, access_token)
    
    if not is_contrib:
        # Also check repository access (might be collaborator but not contributor)
        has_access = await check_repository_access(owner, repo, access_token)
        if not has_access:
            error_msg = f"User {username} is not a contributor or does not have access to {owner}/{repo}"
            if return_json:
                raise HTTPException(status_code=403, detail=error_msg)
            return templates.TemplateResponse(
                "result.html",
                {
                    "request": request,
                    "user": user,
                    "success": False,
                    "error": error_msg,
                    "owner": owner,
                    "repo": repo,
                    "workflow_id": workflow_id
                }
            )
    
    # Trigger workflow
    try:
        logger.info(f"Triggering workflow: {owner}/{repo}/{workflow_id} on {ref} with inputs: {inputs}")
        result = await trigger_workflow(
            owner=owner,
            repo=repo,
            workflow_id=workflow_id,
            inputs=inputs,
            ref=ref
        )
        
        if return_json:
            if result["success"]:
                return JSONResponse(content=result)
            else:
                raise HTTPException(
                    status_code=result["status_code"],
                    detail=result["message"]
                )
        
        # Return HTML result page
        return templates.TemplateResponse(
            "result.html",
            {
                "request": request,
                "user": user,
                "success": result["success"],
                "message": result["message"],
                "owner": owner,
                "repo": repo,
                "workflow_id": workflow_id,
                "ref": ref,
                "inputs": inputs,
                "run_id": result.get("run_id"),
                "run_url": result.get("run_url"),
                "workflow_url": result.get("workflow_url"),
                "error": result.get("message") if not result["success"] else None
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger workflow: {str(e)}", exc_info=True)
        if return_json:
            raise HTTPException(status_code=500, detail=f"Failed to trigger workflow: {str(e)}")
        return templates.TemplateResponse(
            "result.html",
            {
                "request": request,
                "user": user,
                "success": False,
                "error": str(e),
                "owner": owner,
                "repo": repo,
                "workflow_id": workflow_id
            }
        )


@router.get("/trigger")
async def trigger_workflow_get(
    request: Request,
    owner: str = Query(None),
    repo: str = Query(None),
    workflow_id: str = Query(None),
    ref: str = Query("main"),
    tests: str = Query(None),
    ui: bool = Query(False)
):
    """
    GET endpoint для запуска workflow через URL
    
    Примеры:
    - /workflow/trigger?owner=naspirato&repo=my-repo&workflow_id=ci.yml
    - /workflow/trigger?owner=naspirato&repo=my-repo&workflow_id=ci.yml&ref=main&tests=unit,integration
    """
    # Определяем режим (UI или JSON)
    accept_header = request.headers.get("Accept", "")
    return_json = not ui and "application/json" in accept_header
    
    # Если нужна форма - редирект
    if ui:
        params = []
        if owner:
            params.append(f"owner={owner}")
        if repo:
            params.append(f"repo={repo}")
        if workflow_id:
            params.append(f"workflow_id={workflow_id}")
        if ref and ref != "main":
            params.append(f"ref={ref}")
        query_string = "&".join(params)
        return RedirectResponse(url=f"/workflow/form?{query_string}")
    
    # Use defaults if not provided
    owner = owner or os.getenv("DEFAULT_REPO_OWNER")
    repo = repo or os.getenv("DEFAULT_REPO_NAME")
    workflow_id = workflow_id or os.getenv("DEFAULT_WORKFLOW_ID")
    
    if not all([owner, repo, workflow_id]):
        error_msg = "Repository owner, name, and workflow_id are required"
        if return_json:
            raise HTTPException(status_code=400, detail=error_msg)
        return templates.TemplateResponse(
            "result.html",
            {
                "request": request,
                "user": request.session.get("user"),
                "success": False,
                "error": error_msg
            }
        )
    
    # Parse inputs from query parameters
    # Все параметры кроме служебных считаются inputs
    inputs = {}
    query_params = dict(request.query_params)
    excluded_params = {"owner", "repo", "workflow_id", "ref", "ui"}
    
    for key, value in query_params.items():
        if key not in excluded_params and value:
            inputs[key] = value
    
    # Если есть tests (для обратной совместимости)
    if tests:
        inputs["tests"] = tests
    
    return await _trigger_and_show_result(
        request, owner, repo, workflow_id, ref, inputs, return_json
    )


@router.post("/trigger")
async def trigger_workflow_post(
    request: Request,
    owner: str = Form(None),
    repo: str = Form(None),
    workflow_id: str = Form(None),
    ref: str = Form("main"),
    tests: str = Form("")
):
    """
    POST endpoint для запуска workflow из формы
    
    Возвращает HTML страницу с результатом
    """
    # Use defaults if not provided
    owner = owner or os.getenv("DEFAULT_REPO_OWNER")
    repo = repo or os.getenv("DEFAULT_REPO_NAME")
    workflow_id = workflow_id or os.getenv("DEFAULT_WORKFLOW_ID")
    
    if not all([owner, repo, workflow_id]):
        return templates.TemplateResponse(
            "result.html",
            {
                "request": request,
                "user": request.session.get("user"),
                "success": False,
                "error": "Repository owner, name, and workflow_id are required"
            }
        )
    
    # Получаем все inputs из формы (динамические поля)
    form_data = await request.form()
    inputs = {}
    
    # Обрабатываем все поля кроме служебных
    excluded_fields = {"owner", "repo", "workflow_id", "ref", "tests"}
    for key, value in form_data.items():
        if key not in excluded_fields:
            # Обработка boolean полей - если значение есть, используем его
            if value:
                if value == "true" or value == "false":
                    inputs[key] = value
                else:
                    inputs[key] = value
            # Если значение пустое, но это может быть необязательное поле - пропускаем
    
    # Если есть tests (для обратной совместимости)
    if tests:
        inputs["tests"] = tests
    
    return await _trigger_and_show_result(
        request, owner, repo, workflow_id, ref, inputs, return_json=False
    )

