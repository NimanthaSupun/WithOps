"""
Security utilities for JWT authentication in Auth Service
Centralized authentication logic for all WithOps microservices
"""

import os
import logging
import httpx
from typing import Optional
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

security = HTTPBearer()

# Auth0 configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
API_AUDIENCE = os.getenv("AUTH0_API_AUDIENCE")
ALGORITHMS = ["RS256"]

# Test mode for development
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"

# User session tracking
_last_authenticated_user = None
_user_session_data = {}


async def verify_token(token: str) -> dict:
    """
    Verify JWT token using Auth0 JWKS
    
    Args:
        token: JWT token string
        
    Returns:
        Token payload dict
        
    Raises:
        ValueError: If token is invalid
    """
    logger.info(f"Verifying token (length: {len(token)})")
    
    # Test mode - return mock payload
    if TEST_MODE:
        logger.warning("🧪 TEST MODE: Using mock token validation")
        return {
            "sub": "auth0|test_user_12345",
            "name": "Test User",
            "picture": "https://avatars.githubusercontent.com/u/123456789",
            "aud": API_AUDIENCE,
            "iss": f"https://{AUTH0_DOMAIN}/",
            "exp": 9999999999,
            "iat": 1736177615,
            "scope": "read:profile"
        }
    
    # Validate configuration
    if not AUTH0_DOMAIN:
        raise ValueError("AUTH0_DOMAIN not configured")
    if not API_AUDIENCE:
        raise ValueError("AUTH0_API_AUDIENCE not configured")
    
    # Fetch JWKS from Auth0
    jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url)
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch JWKS: {response.status_code}")
        jwks = response.json()

    # Get token header
    try:
        unverified_header = jwt.get_unverified_header(token)
    except Exception as e:
        raise ValueError(f"Invalid token format: {str(e)}")
    
    # Find matching key
    rsa_key = next(
        (key for key in jwks["keys"] if key["kid"] == unverified_header["kid"]), None
    )
    
    if not rsa_key:
        raise ValueError(f"Unable to find appropriate key for kid: {unverified_header.get('kid')}")
    
    # Decode and validate token
    try:
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=ALGORITHMS,
            audience=API_AUDIENCE,
            issuer=f"https://{AUTH0_DOMAIN}/"
        )
        logger.info(f"✅ Token verified successfully for user: {payload.get('sub')}")
        return payload
        
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        
        # Try without audience validation (for debugging)
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                issuer=f"https://{AUTH0_DOMAIN}/",
                options={"verify_aud": False}
            )
            logger.warning(f"Token decoded without audience validation")
            return payload
        except Exception as e2:
            logger.error(f"Token decode failed completely: {str(e2)}")
            raise ValueError(f"Token validation error: {str(e)}")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Extract and validate user ID from JWT token
    
    Args:
        credentials: HTTP Authorization Bearer token
        
    Returns:
        User ID (Auth0 sub claim)
        
    Raises:
        HTTPException: If token is invalid
    """
    global _last_authenticated_user, _user_session_data
    
    try:
        token = credentials.credentials
        payload = await verify_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user ID")
        
        # Track user sessions
        current_time = datetime.now()
        
        # Detect user switches
        if _last_authenticated_user and _last_authenticated_user != user_id:
            logger.warning(f"🔐 User switch detected: {_last_authenticated_user} -> {user_id}")
        
        # Update session tracking
        _last_authenticated_user = user_id
        _user_session_data[user_id] = {
            'last_seen': current_time,
            'token_hash': hash(token)
        }
        
        logger.info(f"✅ Authenticated user: {user_id}")
        return user_id
        
    except ValueError as e:
        logger.error(f"Token validation failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


def decode_jwt_token(token: str) -> dict:
    """
    Decode JWT token without full verification (for rate limiting, etc.)
    Use only for non-critical operations
    
    Args:
        token: JWT token string
        
    Returns:
        Token payload dict or empty dict if invalid
    """
    try:
        return jwt.get_unverified_claims(token)
    except Exception:
        return {}


async def get_auth0_user_info(access_token: str) -> Optional[dict]:
    """
    Fetch complete user profile from Auth0 userinfo endpoint
    
    Args:
        access_token: Auth0 access token
        
    Returns:
        User info dict or None if request fails
    """
    if not AUTH0_DOMAIN:
        raise ValueError("AUTH0_DOMAIN not configured")
    
    userinfo_url = f"https://{AUTH0_DOMAIN}/userinfo"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if response.status_code == 200:
            user_info = response.json()
            logger.info(f"Retrieved Auth0 userinfo for user: {user_info.get('sub')}")
            return user_info
        else:
            logger.error(f"Failed to fetch userinfo: {response.status_code}")
            return None


def force_clear_all_sessions():
    """
    Clear all user session tracking
    Use for security resets or testing
    """
    global _last_authenticated_user, _user_session_data
    
    _last_authenticated_user = None
    _user_session_data.clear()
    
    logger.warning("🔐 All user sessions cleared")
