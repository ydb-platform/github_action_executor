"""
API routes for programmatic access
"""
import logging
import httpx
from fastapi import APIRouter, Request, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List

from backend.services.permissions import is_contributor, check_repository_access
from backend.services.workflow import trigger_workflow, find_workflow_run
from backend.services.branches import get_branches
from backend.services.workflows import get_workflows

logger = logging.getLogger(__name__)

router = APIRouter()


def get_user_from_session(request: Request):
    """Dependency to get authenticated user from session"""
    user = request.session.get("user")
    access_token = request.session.get("access_token")
    
    if not user or not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return user, access_token


class TriggerWorkflowRequest(BaseModel):
    owner: str
    repo: str
    workflow_id: str
    ref: Optional[str] = "main"
    inputs: Optional[dict] = {}
    tests: Optional[List[str]] = None


@router.post("/trigger")
async def api_trigger_workflow(
    request_data: TriggerWorkflowRequest,
    request: Request,
    user_data: tuple = Depends(get_user_from_session)
):
    """API endpoint to trigger workflow"""
    user, access_token = user_data
    username = user["login"]
    
    # Check permissions
    is_contrib = await is_contributor(
        request_data.owner,
        request_data.repo,
        username,
        access_token
    )
    
    if not is_contrib:
        has_access = await check_repository_access(
            request_data.owner,
            request_data.repo,
            access_token
        )
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail=f"User {username} is not a contributor or does not have access to {request_data.owner}/{request_data.repo}"
            )
    
    # Prepare inputs
    inputs = request_data.inputs or {}
    if request_data.tests:
        inputs["tests"] = request_data.tests
    
    # Trigger workflow
    result = await trigger_workflow(
        owner=request_data.owner,
        repo=request_data.repo,
        workflow_id=request_data.workflow_id,
        inputs=inputs,
        ref=request_data.ref
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=result["status_code"],
            detail=result["message"]
        )
    
    return result


@router.get("/branches")
async def api_get_branches(
    owner: str = Query(...),
    repo: str = Query(...),
    env: Optional[str] = Query(None),
    request: Request = None
):
    """
    API endpoint to get branches for a repository
    
    Args:
        owner: Repository owner
        repo: Repository name
        env: Optional comma-separated list of regex patterns to filter branches by name
             Example: "production,staging,.*-prod$"
    """
    try:
        env_patterns = None
        if env:
            # Split comma-separated patterns
            env_patterns = [p.strip() for p in env.split(",") if p.strip()]
            if len(env_patterns) == 0:
                env_patterns = None
        
        branches = await get_branches(owner, repo, env_patterns=env_patterns)
        return {"branches": branches}
    except httpx.HTTPStatusError as e:
        # Извлекаем сообщение об ошибке из ответа GitHub
        status_code = e.response.status_code
        try:
            error_data = e.response.json()
            error_message = error_data.get("message", str(e))
        except:
            error_message = str(e)
        
        logger.error(f"GitHub API error getting branches for {owner}/{repo}: {status_code} - {error_message}")
        raise HTTPException(status_code=status_code, detail=error_message)
    except Exception as e:
        logger.error(f"Unexpected error getting branches for {owner}/{repo}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get branches: {str(e)}")


@router.get("/workflows")
async def api_get_workflows(
    owner: str = Query(...),
    repo: str = Query(...),
    request: Request = None
):
    """API endpoint to get workflows for a repository"""
    try:
        workflows = await get_workflows(owner, repo)
        return {"workflows": workflows}
    except httpx.HTTPStatusError as e:
        # Извлекаем сообщение об ошибке из ответа GitHub
        status_code = e.response.status_code
        try:
            error_data = e.response.json()
            error_message = error_data.get("message", str(e))
        except:
            error_message = str(e)
        
        logger.error(f"GitHub API error getting workflows for {owner}/{repo}: {status_code} - {error_message}")
        raise HTTPException(status_code=status_code, detail=error_message)
    except Exception as e:
        logger.error(f"Unexpected error getting workflows for {owner}/{repo}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get workflows: {str(e)}")


@router.get("/workflow-info")
async def api_get_workflow_info(
    owner: str = Query(...),
    repo: str = Query(...),
    workflow_id: str = Query(...),
    request: Request = None
):
    """API endpoint to get workflow info including inputs"""
    try:
        from backend.services.workflow_info import get_workflow_info
        workflow_info = await get_workflow_info(owner, repo, workflow_id)
        return {
            "found": workflow_info.get("found", False),
            "inputs": workflow_info.get("inputs", {})
        }
    except httpx.HTTPStatusError as e:
        # Извлекаем сообщение об ошибке из ответа GitHub
        status_code = e.response.status_code
        try:
            error_data = e.response.json()
            error_message = error_data.get("message", str(e))
        except:
            error_message = str(e)
        
        logger.error(f"GitHub API error getting workflow info for {owner}/{repo}/{workflow_id}: {status_code} - {error_message}")
        raise HTTPException(status_code=status_code, detail=error_message)
    except Exception as e:
        logger.error(f"Unexpected error getting workflow info for {owner}/{repo}/{workflow_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get workflow info: {str(e)}")


@router.get("/find-run")
async def api_find_run(
    owner: str = Query(...),
    repo: str = Query(...),
    workflow_id: str = Query(...),
    trigger_time: str = Query(...),  # ISO format timestamp
    ref: Optional[str] = Query(None),
    request: Request = None
):
    """
    API endpoint to find workflow run by trigger time and actor
    
    Args:
        owner: Repository owner
        repo: Repository name
        workflow_id: Workflow ID
        trigger_time: ISO format timestamp when workflow was triggered
        ref: Optional branch name
    """
    try:
        from datetime import datetime
        
        # Parse trigger_time from ISO format
        trigger_dt = datetime.fromisoformat(trigger_time.replace('Z', '+00:00'))
        run_data = await find_workflow_run(owner, repo, workflow_id, trigger_dt, ref=ref)
        
        if run_data:
            return {
                "found": True,
                "run_id": run_data.get("id"),
                "run_url": run_data.get("html_url"),
                "status": run_data.get("status"),
                "conclusion": run_data.get("conclusion")
            }
        else:
            return {"found": False}
    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        try:
            error_data = e.response.json()
            error_message = error_data.get("message", str(e))
        except:
            error_message = str(e)
        
        logger.error(f"GitHub API error finding run for {owner}/{repo}/{workflow_id}: {status_code} - {error_message}")
        raise HTTPException(status_code=status_code, detail=error_message)
    except Exception as e:
        logger.error(f"Unexpected error finding run for {owner}/{repo}/{workflow_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to find run: {str(e)}")

