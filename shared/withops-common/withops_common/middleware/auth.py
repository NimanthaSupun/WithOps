"""
JWT Authentication middleware for microservices
Shared authentication logic using Auth0 JWKS validation
"""

from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx
import os
import logging
from typing import Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

security = HTTPBearer()

# Cache for JWKS to avoid repeated network calls
_jwks_cache = None
_jwks_cache_timestamp = 0
JWKS_CACHE_TTL = 3600  # 1 hour


@lru_cache(maxsize=1)
def get_auth0_config():
    """Get Auth0 configuration from environment (cached)"""
    domain = os.getenv('AUTH0_DOMAIN')
    audience = os.getenv('AUTH0_API_AUDIENCE') or os.getenv('AUTH0_AUDIENCE')
    
    if not domain:
        raise ValueError("AUTH0_DOMAIN not configured")
    if not audience:
        raise ValueError("AUTH0_API_AUDIENCE not configured")
    
    return {
        'domain': domain,
        'audience': audience,
        'algorithms': ['RS256'],
        'jwks_url': f"https://{domain}/.well-known/jwks.json"
    }


async def fetch_jwks():
    """Fetch JWKS from Auth0 with caching"""
    global _jwks_cache, _jwks_cache_timestamp
    
    import time
    current_time = time.time()
    
    # Return cached JWKS if still valid
    if _jwks_cache and (current_time - _jwks_cache_timestamp) < JWKS_CACHE_TTL:
        return _jwks_cache
    
    # Fetch fresh JWKS
    config = get_auth0_config()
    
    async with httpx.AsyncClient() as client:
        response = await client.get(config['jwks_url'])
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch JWKS: {response.status_code}")
        
        _jwks_cache = response.json()
        _jwks_cache_timestamp = current_time
        return _jwks_cache


async def verify_jwt_token(token: str) -> dict:
    """
    Verify JWT token using Auth0 JWKS
    
    Args:
        token: JWT token string
        
    Returns:
        Token payload dict
        
    Raises:
        ValueError: If token is invalid
    """
    config = get_auth0_config()
    
    # Get JWKS
    jwks = await fetch_jwks()
    
    # Get token header
    try:
        unverified_header = jwt.get_unverified_header(token)
    except Exception as e:
        raise ValueError(f"Invalid token format: {str(e)}")
    
    # Find matching key
    rsa_key = next(
        (key for key in jwks["keys"] if key["kid"] == unverified_header["kid"]), 
        None
    )
    
    if not rsa_key:
        raise ValueError(f"Unable to find key for kid: {unverified_header.get('kid')}")
    
    # Decode and validate token
    try:
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=config['algorithms'],
            audience=config['audience'],
            issuer=f"https://{config['domain']}/"
        )
        return payload
        
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.JWTClaimsError as e:
        raise ValueError(f"Invalid token claims: {str(e)}")
    except Exception as e:
        # Try without audience validation for compatibility
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=config['algorithms'],
                issuer=f"https://{config['domain']}/",
                options={"verify_aud": False}
            )
            logger.warning("Token validated without audience verification")
            return payload
        except Exception:
            raise ValueError(f"Token validation failed: {str(e)}")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """
    FastAPI dependency to get current user from JWT token
    
    Args:
        credentials: HTTP Authorization Bearer token
        
    Returns:
        User ID (Auth0 sub claim)
        
    Raises:
        HTTPException: If token is invalid
    """
    try:
        token = credentials.credentials
        payload = await verify_jwt_token(token)
        user_id = payload.get('sub')
        
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="User ID not found in token"
            )
        
        return user_id
        
    except ValueError as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


async def get_current_user_from_token(token: str) -> str:
    """
    Extract user ID from token string (without FastAPI dependencies)
    Useful for services that want to validate tokens directly
    
    Args:
        token: JWT token string
        
    Returns:
        User ID (Auth0 sub claim)
        
    Raises:
        ValueError: If token is invalid
    """
    payload = await verify_jwt_token(token)
    user_id = payload.get('sub')
    
    if not user_id:
        raise ValueError("User ID not found in token")
    
    return user_id


def decode_token_unsafe(token: str) -> dict:
    """
    Decode JWT token without verification (for rate limiting, logging, etc.)
    DO NOT use for authentication - use verify_jwt_token instead
    
    Args:
        token: JWT token string
        
    Returns:
        Token payload dict or empty dict if invalid
    """
    try:
        return jwt.get_unverified_claims(token)
    except Exception:
        return {}
