"""
Service for getting repository branches from GitHub API
"""
import os
import logging
import re
import httpx
import asyncio
from typing import List, Optional
from backend.services.github_app import get_installation_token, load_private_key
from backend.services.cache import get as cache_get, set as cache_set

logger = logging.getLogger(__name__)

# Cache TTL in seconds (30 minutes - branches don't change frequently)
CACHE_TTL = 1800

# Maximum number of parallel requests to GitHub API
MAX_PARALLEL_REQUESTS = 10


async def _fetch_all_branches_from_api(owner: str, repo: str) -> list:
    """
    Fetch all branches from GitHub API using parallel requests (internal function, not cached)
    
    Args:
        owner: Repository owner
        repo: Repository name
        
    Returns:
        List of all branch names (unsorted)
    """
    # Get GitHub App credentials
    app_id = os.getenv("GITHUB_APP_ID")
    installation_id = os.getenv("GITHUB_APP_INSTALLATION_ID")
    private_key_path = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")
    
    if not all([app_id, installation_id]):
        raise ValueError("GITHUB_APP_ID and GITHUB_APP_INSTALLATION_ID must be set")
    
    # Load private key and get installation token
    private_key = load_private_key(private_key_path)
    installation_token = await get_installation_token(app_id, installation_id, private_key)
    
    headers = {
        "Authorization": f"token {installation_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        branches_url = f"https://api.github.com/repos/{owner}/{repo}/branches"
        per_page = 100
        
        # Fetch first page to determine if there are more pages
        first_response = await client.get(
            branches_url,
            headers=headers,
            params={"per_page": per_page, "page": 1}
        )
        first_response.raise_for_status()
        
        first_page_data = first_response.json()
        if not first_page_data:
            return []
        
        all_branch_names = [branch["name"] for branch in first_page_data]
        
        # If first page is not full, we're done
        if len(first_page_data) < per_page:
            return all_branch_names
        
        # Parse Link header to find total number of pages
        link_header = first_response.headers.get("Link", "")
        total_pages = None
        
        if link_header:
            # Extract last page number from Link header
            # Format: <url?page=2>; rel="next", <url?page=19>; rel="last"
            import re as regex_module
            last_match = regex_module.search(r'page=(\d+)>; rel="last"', link_header)
            if last_match:
                total_pages = int(last_match.group(1))
        
        # If we know total pages, fetch all remaining pages in parallel
        if total_pages and total_pages > 1:
            semaphore = asyncio.Semaphore(MAX_PARALLEL_REQUESTS)
            
            async def fetch_page(page_num: int) -> List[str]:
                """Fetch a single page of branches"""
                async with semaphore:
                    response = await client.get(
                        branches_url,
                        headers=headers,
                        params={"per_page": per_page, "page": page_num}
                    )
                    response.raise_for_status()
                    branches_data = response.json()
                    return [branch["name"] for branch in branches_data] if branches_data else []
            
            # Fetch all remaining pages (2 to total_pages) in parallel
            remaining_pages = list(range(2, total_pages + 1))
            tasks = [fetch_page(page) for page in remaining_pages]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results
            for result in results:
                if isinstance(result, Exception):
                    logger.warning(f"Error fetching page: {str(result)}")
                elif result:
                    all_branch_names.extend(result)
        else:
            # Fallback: sequential fetching if we can't determine total pages
            # This should rarely happen, but keep it as fallback
            page = 2
            while True:
                response = await client.get(
                    branches_url,
                    headers=headers,
                    params={"per_page": per_page, "page": page}
                )
                response.raise_for_status()
                
                branches_data = response.json()
                if not branches_data:
                    break
                
                all_branch_names.extend([branch["name"] for branch in branches_data])
                
                if len(branches_data) < per_page:
                    break
                
                page += 1
        
        return all_branch_names


async def get_branches(owner: str, repo: str, env_patterns: Optional[List[str]] = None) -> list:
    """
    Get list of branches from repository with optional filtering by environment patterns
    Uses caching for improved performance.
    
    Args:
        owner: Repository owner
        repo: Repository name
        env_patterns: Optional list of regex patterns to filter branches. If None or empty, returns all branches.
                     Patterns are matched against branch names.
        
    Returns:
        List of branch names (sorted, main/master first, then filtered by patterns)
    """
    # Cache key for all branches (without filtering)
    cache_key = f"branches:{owner}:{repo}"
    
    # Try to get all branches from cache
    all_branch_names = cache_get(cache_key)
    
    if all_branch_names is None:
        # Not in cache, fetch from API
        try:
            all_branch_names = await _fetch_all_branches_from_api(owner, repo)
            # Cache all branches for 30 minutes
            cache_set(cache_key, all_branch_names, CACHE_TTL)
            logger.info(f"Fetched {len(all_branch_names)} branches from API for {owner}/{repo}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get branches: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting branches: {str(e)}", exc_info=True)
            raise
    else:
        logger.debug(f"Using cached branches for {owner}/{repo} ({len(all_branch_names)} branches)")
    
    # Filter by env patterns if provided
    if env_patterns and len(env_patterns) > 0:
        # Remove empty patterns
        patterns = [p.strip() for p in env_patterns if p.strip()]
        if patterns:
            filtered_branches = []
            for branch_name in all_branch_names:
                # Check if branch matches any pattern
                for pattern in patterns:
                    try:
                        if re.search(pattern, branch_name, re.IGNORECASE):
                            filtered_branches.append(branch_name)
                            break
                    except re.error:
                        # If pattern is invalid regex, treat it as literal string
                        if pattern in branch_name:
                            filtered_branches.append(branch_name)
                            break
            all_branch_names = filtered_branches
            logger.info(f"Filtered to {len(all_branch_names)} branches matching patterns: {patterns}")
    
    # Sort: main/master first, then alphabetically
    def sort_key(name):
        if name in ["main", "master"]:
            return (0, name)
        return (1, name)
    
    all_branch_names.sort(key=sort_key)
    logger.info(f"Retrieved {len(all_branch_names)} branches for {owner}/{repo} (env_patterns: {env_patterns})")
    return all_branch_names

