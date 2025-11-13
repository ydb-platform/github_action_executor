"""
Workflow routes for triggering GitHub Actions
"""
import os
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from backend.services.permissions import is_contributor, check_repository_access
from backend.services.workflow import trigger_workflow
from backend.services.github_oauth import get_oauth_url

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")


@router.get("/form", response_class=HTMLResponse)
async def workflow_form(
    request: Request,
    owner: str = None,
    repo: str = None,
    workflow_id: str = None
):
    """Display workflow trigger form"""
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
    
    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "user": user,
            "owner": owner,
            "repo": repo,
            "workflow_id": workflow_id
        }
    )


@router.post("/trigger")
async def trigger_workflow_route(
    request: Request,
    owner: str = Form(None),
    repo: str = Form(None),
    workflow_id: str = Form(None),
    ref: str = Form("main"),
    tests: str = Form("")
):
    """Trigger GitHub Actions workflow"""
    # Check authentication
    user = request.session.get("user")
    access_token = request.session.get("access_token")
    
    if not user or not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Use defaults if not provided
    owner = owner or os.getenv("DEFAULT_REPO_OWNER")
    repo = repo or os.getenv("DEFAULT_REPO_NAME")
    workflow_id = workflow_id or os.getenv("DEFAULT_WORKFLOW_ID")
    
    if not all([owner, repo, workflow_id]):
        raise HTTPException(
            status_code=400,
            detail="Repository owner, name, and workflow_id are required"
        )
    
    # Check if user is a contributor
    username = user["login"]
    is_contrib = await is_contributor(owner, repo, username, access_token)
    
    if not is_contrib:
        # Also check repository access (might be collaborator but not contributor)
        has_access = await check_repository_access(owner, repo, access_token)
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail=f"User {username} is not a contributor or does not have access to {owner}/{repo}"
            )
    
    # Parse tests input (comma-separated string)
    inputs = {}
    if tests:
        # GitHub workflow_dispatch inputs are strings, so we pass comma-separated values
        inputs["tests"] = tests
    
    # Trigger workflow
    try:
        result = await trigger_workflow(
            owner=owner,
            repo=repo,
            workflow_id=workflow_id,
            inputs=inputs,
            ref=ref
        )
        
        if result["success"]:
            return JSONResponse(content={
                "success": True,
                "message": result["message"],
                "workflow": f"{owner}/{repo}/{workflow_id}"
            })
        else:
            raise HTTPException(
                status_code=result["status_code"],
                detail=result["message"]
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger workflow: {str(e)}")

