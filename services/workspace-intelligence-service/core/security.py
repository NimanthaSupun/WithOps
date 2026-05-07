"""
Security utilities for Workspace Intelligence Service
Uses shared auth library for JWT validation
"""

import logging
from typing import Optional
from fastapi import Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Import from shared library
from withops_common.middleware.auth import verify_jwt_token, get_current_user_from_token

logger = logging.getLogger(__name__)

# Make auth optional for backward compatibility
security = HTTPBearer(auto_error=False)


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> Optional[str]:
    """
    Extract user ID from JWT token if provided
    Optional authentication - returns None if no credentials provided
    
    Args:
        credentials: HTTP Authorization Bearer token (optional)
        
    Returns:
        User ID from token (Auth0 ID like "google-oauth2|123456") or None if not authenticated
    """
    if not credentials:
        logger.info("🔓 No authentication credentials provided")
        return None
    
    try:
        token = credentials.credentials
        logger.info(f"🔐 Received auth token (length: {len(token)})")
        
        user_id = await get_current_user_from_token(token)
        
        logger.info(f"✅ Authenticated user: {user_id}")
        return user_id
        
    except ValueError as e:
        logger.warning(f"⚠️ Token validation failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected authentication error: {e}")
        return None


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
