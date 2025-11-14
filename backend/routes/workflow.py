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
from backend.services.github_oauth import get_oauth_url
import config

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")


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
            response = templates.TemplateResponse(
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
            # Prevent caching
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response
    
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
                json_response = JSONResponse(content=result)
                # Prevent caching for JSON responses too
                json_response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                json_response.headers["Pragma"] = "no-cache"
                json_response.headers["Expires"] = "0"
                return json_response
            else:
                raise HTTPException(
                    status_code=result["status_code"],
                    detail=result["message"]
                )
        
        # Return HTML result page with no-cache headers
        response = templates.TemplateResponse(
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
                "trigger_time": result.get("trigger_time"),
                "auto_open_run": config.AUTO_OPEN_RUN,
                "error": result.get("message") if not result["success"] else None
            }
        )
        # Prevent caching to ensure workflow is triggered on each request
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger workflow: {str(e)}", exc_info=True)
        if return_json:
            raise HTTPException(status_code=500, detail=f"Failed to trigger workflow: {str(e)}")
        response = templates.TemplateResponse(
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
        # Prevent caching
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


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
    
    # Если нужна форма - редирект на главную страницу со всеми параметрами
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
        
        # Добавляем все остальные параметры (workflow inputs)
        query_params = dict(request.query_params)
        excluded_params = {"owner", "repo", "workflow_id", "ref", "ui", "tests"}
        for key, value in query_params.items():
            if key not in excluded_params and value:
                params.append(f"{key}={value}")
        
        # Если есть tests, добавляем его
        if tests:
            params.append(f"tests={tests}")
        
        query_string = "&".join(params)
        return RedirectResponse(url=f"/?{query_string}")
    
    # Use defaults if not provided
    owner = owner or os.getenv("DEFAULT_REPO_OWNER")
    repo = repo or os.getenv("DEFAULT_REPO_NAME")
    workflow_id = workflow_id or os.getenv("DEFAULT_WORKFLOW_ID")
    
    if not all([owner, repo, workflow_id]):
        error_msg = "Repository owner, name, and workflow_id are required"
        if return_json:
            raise HTTPException(status_code=400, detail=error_msg)
        response = templates.TemplateResponse(
            "result.html",
            {
                "request": request,
                "user": request.session.get("user"),
                "success": False,
                "error": error_msg
            }
        )
        # Prevent caching
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    
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

