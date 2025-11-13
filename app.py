"""
GitHub Action Executor - Main application entry point
Web interface for triggering GitHub Actions workflows with contributor verification
"""
import os
import logging
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

from backend.routes import auth, workflow, api

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GitHub Action Executor",
    description="Web interface for triggering GitHub Actions workflows",
    version="1.0.0"
)

# Add request logging middleware
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"Request: {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}")
        try:
            response = await call_next(request)
            logger.info(f"Response: {request.method} {request.url.path} - Status: {response.status_code}")
            return response
        except Exception as e:
            logger.error(f"Error processing {request.method} {request.url.path}: {str(e)}", exc_info=True)
            raise

app.add_middleware(LoggingMiddleware)

# Add session middleware for OAuth
secret_key = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
app.add_middleware(SessionMiddleware, secret_key=secret_key)

# Mount static files
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Templates
templates = Jinja2Templates(directory="frontend/templates")

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(workflow.router, prefix="/workflow", tags=["workflow"])
app.include_router(api.router, prefix="/api", tags=["api"])


@app.get("/", response_class=HTMLResponse)
async def root(
    request: Request,
    owner: str = Query(None),
    repo: str = Query(None),
    workflow_id: str = Query(None),
    ref: str = Query(None)
):
    """Main page with form"""
    user = request.session.get("user")
    # Используем query параметры или переменные окружения
    default_owner = owner or os.getenv("DEFAULT_REPO_OWNER", "")
    default_repo = repo or os.getenv("DEFAULT_REPO_NAME", "")
    default_workflow_id = workflow_id or os.getenv("DEFAULT_WORKFLOW_ID", "")
    default_ref = ref or "main"
    
    # Try to load branches and workflows if owner and repo are provided
    branches = []
    workflows_list = []
    if default_owner and default_repo:
        try:
            from backend.services.branches import get_branches
            from backend.services.workflows import get_workflows
            import asyncio
            
            branches_task = get_branches(default_owner, default_repo)
            workflows_task = get_workflows(default_owner, default_repo)
            branches, workflows_list = await asyncio.gather(
                branches_task,
                workflows_task,
                return_exceptions=True
            )
            
            if isinstance(branches, Exception):
                logger.warning(f"Failed to get branches for main page: {str(branches)}")
                branches = []
            if isinstance(workflows_list, Exception):
                logger.warning(f"Failed to get workflows for main page: {str(workflows_list)}")
                workflows_list = []
        except Exception as e:
            logger.warning(f"Failed to load branches/workflows for main page: {str(e)}")
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user,
            "default_owner": default_owner,
            "default_repo": default_repo,
            "default_workflow_id": default_workflow_id,
            "branches": branches,
            "workflows": workflows_list
        }
    )


@app.get("/health")
async def health():
    """Health check endpoint for Yandex Cloud"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(app, host=host, port=port)

