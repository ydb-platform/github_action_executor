"""
Service for checking user permissions and contributor status
"""
import httpx


async def is_contributor(owner: str, repo: str, username: str, access_token: str) -> bool:
    """
    Check if user is a contributor to the repository
    
    Args:
        owner: Repository owner
        repo: Repository name
        username: GitHub username to check
        access_token: GitHub OAuth access token
        
    Returns:
        True if user is a contributor, False otherwise
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/contributors"
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # Use pagination to get all contributors
            page = 1
            per_page = 100
            
            while True:
                params = {"page": page, "per_page": per_page}
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                
                contributors = response.json()
                
                # Check if user is in this page
                if any(contributor["login"].lower() == username.lower() for contributor in contributors):
                    return True
                
                # Check if there are more pages
                if len(contributors) < per_page:
                    break
                
                page += 1
            
            return False
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            # Repository not found or no access
            return False
        raise
    except Exception:
        return False


async def check_repository_access(owner: str, repo: str, access_token: str) -> bool:
    """
    Check if user has access to the repository
    
    Args:
        owner: Repository owner
        repo: Repository name
        access_token: GitHub OAuth access token
        
    Returns:
        True if user has access, False otherwise
    """
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            return response.status_code == 200
    except httpx.HTTPStatusError:
        return False

