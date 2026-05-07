"""
Security utilities for GitHub Service
Uses shared auth library for JWT validation
"""

import logging
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Import from shared library
from withops_common.middleware.auth import verify_jwt_token, get_current_user_from_token

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Validate JWT token and extract user ID (Auth0 ID)
    Uses shared auth library for validation
    
    Args:
        credentials: HTTP Authorization Bearer token
        
    Returns:
        User ID from token (Auth0 ID like "google-oauth2|123456")
        
    Raises:
        HTTPException: If token is invalid
    """
    try:
        token = credentials.credentials
        user_id = await get_current_user_from_token(token)
        
        logger.info(f"✅ Authenticated user: {user_id}")
        return user_id
        
    except ValueError as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected authentication error: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")


# For backward compatibility - expose verify_token
async def verify_token(token: str) -> dict:
    """
    Verify JWT token and return payload
    Uses shared auth library
    
    Args:
        token: JWT token string
        
    Returns:
        Token payload dict
    """
    return await verify_jwt_token(token)
