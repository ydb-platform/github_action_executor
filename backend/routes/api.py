"""
API routes for programmatic access
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List

from backend.services.permissions import is_contributor, check_repository_access
from backend.services.workflow import trigger_workflow

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

