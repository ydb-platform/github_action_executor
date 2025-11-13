"""
Authentication routes for GitHub OAuth
"""
import secrets
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse

from backend.services.github_oauth import get_oauth_url, get_access_token, get_user_info

router = APIRouter()


@router.get("/github")
async def github_login(request: Request):
    """Initiate GitHub OAuth login"""
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    
    # Redirect to GitHub OAuth
    oauth_url = get_oauth_url(state=state)
    return RedirectResponse(url=oauth_url)


@router.get("/github/callback")
async def github_callback(request: Request, code: str = None, state: str = None):
    """Handle GitHub OAuth callback"""
    # Verify state
    session_state = request.session.get("oauth_state")
    if not session_state or session_state != state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")
    
    try:
        # Exchange code for access token
        access_token = await get_access_token(code)
        
        # Get user info
        user_info = await get_user_info(access_token)
        
        # Store in session
        request.session["access_token"] = access_token
        request.session["user"] = {
            "login": user_info["login"],
            "name": user_info.get("name"),
            "avatar_url": user_info.get("avatar_url")
        }
        request.session.pop("oauth_state", None)
        
        # Redirect to main page
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@router.get("/logout")
async def logout(request: Request):
    """Logout user"""
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@router.get("/user")
async def get_current_user(request: Request):
    """Get current authenticated user"""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

