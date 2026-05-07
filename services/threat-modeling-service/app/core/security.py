"""
Security utilities for Threat Modeling Service
Uses shared auth library for JWT validation
"""

import os
import logging
from typing import Optional
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Import from shared library
from withops_common.middleware.auth import verify_jwt_token, get_current_user_from_token

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Validate JWT token and extract user ID
    Uses shared auth library for validation
    
    Args:
        credentials: HTTP Authorization Bearer token
        
    Returns:
        User ID from token (Auth0 ID)
        
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


# Optional: JWT secret key for simple validation (if not using Auth0)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def create_token(user_id: str, expires_delta: Optional[int] = None) -> str:
    """
    Create JWT token for user (for testing purposes)
    
    Args:
        user_id: User identifier
        expires_delta: Token expiration in minutes
        
    Returns:
        JWT token string
    """
    from datetime import datetime, timedelta
    from jose import jwt
    
    expire = datetime.utcnow() + timedelta(minutes=expires_delta or 30)
    payload = {
        "sub": user_id,
        "exp": expire
    }
    
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
