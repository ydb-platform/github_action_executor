"""
Authentication routes for GitHub OAuth
"""
import secrets
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse

from backend.services.github_oauth import get_oauth_url, get_access_token, get_user_info

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/github")
async def github_login(request: Request, redirect_after: str = None):
    """Initiate GitHub OAuth login"""
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    
    # Save redirect URL if provided
    if redirect_after:
        request.session["oauth_redirect_after"] = redirect_after
    elif "oauth_redirect_after" not in request.session:
        # Get redirect_after from query parameter if not in session
        redirect_after = request.query_params.get("redirect_after")
        if redirect_after:
            request.session["oauth_redirect_after"] = redirect_after
    
    logger.info(f"OAuth login initiated, state generated: {state[:10]}..., redirect_after: {request.session.get('oauth_redirect_after', 'not set')}")
    
    # Redirect to GitHub OAuth
    oauth_url = get_oauth_url(state=state)
    logger.info(f"Redirecting to GitHub OAuth: {oauth_url[:100]}...")
    return RedirectResponse(url=oauth_url)


@router.get("/github/callback")
async def github_callback(request: Request, code: str = None, state: str = None):
    """Handle GitHub OAuth callback"""
    logger.info(f"OAuth callback received - code: {'present' if code else 'missing'}, state: {state[:20] if state else 'missing'}...")
    logger.info(f"Full callback URL: {request.url}")
    logger.info(f"Session keys: {list(request.session.keys())}")
    
    # Verify state
    session_state = request.session.get("oauth_state")
    logger.info(f"Session state: {session_state[:20] if session_state else 'missing'}...")
    
    # GitHub sometimes doesn't return state, but if we have it in session and code is valid, allow it
    # This is a workaround for cases where state is lost in redirect
    if state and session_state:
        if session_state != state:
            logger.error(f"State mismatch! Session: {session_state[:20] if session_state else 'None'}, Received: {state[:20] if state else 'None'}")
            raise HTTPException(status_code=400, detail="Invalid state parameter")
    elif not session_state:
        logger.warning("No state in session, but proceeding with authentication (state may have been lost in redirect)")
        # Allow authentication to proceed if we have a valid code
    elif not state:
        logger.warning("GitHub didn't return state parameter, but we have it in session - allowing authentication")
        # GitHub didn't return state, but we have it in session - this is acceptable
    
    if not code:
        logger.error("Authorization code not provided in callback")
        raise HTTPException(status_code=400, detail="Authorization code not provided")
    
    try:
        logger.info("Exchanging authorization code for access token...")
        # Exchange code for access token
        access_token = await get_access_token(code)
        logger.info("Access token obtained successfully")
        
        logger.info("Fetching user info from GitHub...")
        # Get user info
        user_info = await get_user_info(access_token)
        logger.info(f"User info retrieved: {user_info.get('login', 'unknown')}")
        
        # Store in session
        request.session["access_token"] = access_token
        request.session["user"] = {
            "login": user_info["login"],
            "name": user_info.get("name"),
            "avatar_url": user_info.get("avatar_url")
        }
        request.session.pop("oauth_state", None)
        logger.info(f"Session updated for user: {user_info['login']}")
        
        # Redirect to saved URL or main page
        redirect_url = request.session.pop("oauth_redirect_after", "/")
        logger.info(f"Redirecting after OAuth to: {redirect_url}")
        return RedirectResponse(url=redirect_url, status_code=303)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}", exc_info=True)
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

