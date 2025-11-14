"""
Simple in-memory cache with TTL (Time To Live)
"""
import time
import logging
from typing import Optional, Any, Dict, Tuple
from functools import wraps

logger = logging.getLogger(__name__)

# Cache storage: {key: (value, expiry_timestamp)}
_cache: Dict[str, Tuple[Any, float]] = {}
_default_ttl = 300  # 5 minutes default TTL


def get(key: str) -> Optional[Any]:
    """
    Get value from cache if it exists and hasn't expired
    
    Args:
        key: Cache key
        
    Returns:
        Cached value or None if not found/expired
    """
    if key not in _cache:
        return None
    
    value, expiry = _cache[key]
    
    if time.time() > expiry:
        # Expired, remove from cache
        del _cache[key]
        logger.debug(f"Cache expired for key: {key}")
        return None
    
    logger.debug(f"Cache hit for key: {key}")
    return value


def set(key: str, value: Any, ttl: int = None) -> None:
    """
    Store value in cache with TTL
    
    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds (default: 5 minutes)
    """
    if ttl is None:
        ttl = _default_ttl
    
    expiry = time.time() + ttl
    _cache[key] = (value, expiry)
    logger.debug(f"Cached key: {key} with TTL: {ttl}s")


def clear(key: str = None) -> None:
    """
    Clear cache entry or all cache
    
    Args:
        key: Cache key to clear, or None to clear all
    """
    if key is None:
        _cache.clear()
        logger.debug("Cache cleared")
    elif key in _cache:
        del _cache[key]
        logger.debug(f"Cache cleared for key: {key}")


def cached(ttl: int = None, key_prefix: str = ""):
    """
    Decorator to cache function results
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
        
    Usage:
        @cached(ttl=300)
        async def my_function(arg1, arg2):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{key_prefix}{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            # Try to get from cache
            cached_value = get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = await func(*args, **kwargs)
            set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    current_time = time.time()
    valid_count = sum(1 for _, expiry in _cache.values() if current_time <= expiry)
    expired_count = len(_cache) - valid_count
    
    return {
        "total_keys": len(_cache),
        "valid_keys": valid_count,
        "expired_keys": expired_count,
        "max_size": None  # No limit currently
    }

