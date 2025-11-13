"""
GitHub Action Executor - Main application entry point
Web interface for triggering GitHub Actions workflows with contributor verification
"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

from backend.routes import auth, workflow, api

# Load environment variables
load_dotenv()

app = FastAPI(
    title="GitHub Action Executor",
    description="Web interface for triggering GitHub Actions workflows",
    version="1.0.0"
)

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
async def root(request: Request):
    """Main page with form"""
    user = request.session.get("user")
    default_owner = os.getenv("DEFAULT_REPO_OWNER", "")
    default_repo = os.getenv("DEFAULT_REPO_NAME", "")
    default_workflow_id = os.getenv("DEFAULT_WORKFLOW_ID", "")
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user,
            "default_owner": default_owner,
            "default_repo": default_repo,
            "default_workflow_id": default_workflow_id
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

