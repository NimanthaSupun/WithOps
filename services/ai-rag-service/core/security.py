"""
Security Module - Token validation and user authorization
"""

import httpx
import logging
import os
from typing import Optional, Dict, List
import jwt
from functools import lru_cache

logger = logging.getLogger(__name__)


class SecurityService:
    """
    Handles JWT token validation and user authorization
    """
    
    def __init__(self):
        self.auth0_domain = os.getenv("AUTH0_DOMAIN")
        self.auth0_audience = os.getenv("AUTH0_AUDIENCE", "https://withops.com")
        self.jwks_uri = f"https://{self.auth0_domain}/.well-known/jwks.json"
        self._jwks_cache = None
        
    @lru_cache(maxsize=100)
    def _get_signing_key(self, token: str) -> str:
        """
        Get signing key from Auth0 JWKS endpoint
        Cached to avoid repeated fetches
        """
        try:
            # Decode header to get kid
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                raise ValueError("No kid in token header")
            
            # Fetch JWKS if not cached
            if not self._jwks_cache:
                response = httpx.get(self.jwks_uri, timeout=10.0)
                response.raise_for_status()
                self._jwks_cache = response.json()
            
            # Find matching key
            for key in self._jwks_cache.get("keys", []):
                if key.get("kid") == kid:
                    return jwt.algorithms.RSAAlgorithm.from_jwk(key)
            
            raise ValueError(f"Unable to find signing key with kid: {kid}")
            
        except Exception as e:
            logger.error(f"Error getting signing key: {str(e)}")
            raise
    
    def verify_token(self, token: str) -> Dict[str, str]:
        """
        Verify JWT token and extract user information
        
        Args:
            token: JWT token from Authorization header
            
        Returns:
            Dict with user_id, email, and other claims
            
        Raises:
            ValueError: If token is invalid
        """
        try:
            if not token:
                raise ValueError("No token provided")
            
            # Get signing key
            signing_key = self._get_signing_key(token)
            
            # Verify and decode token
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.auth0_audience,
                issuer=f"https://{self.auth0_domain}/"
            )
            
            # Extract user information
            user_info = {
                "user_id": payload.get("sub"),  # Auth0 user ID
                "email": payload.get("email"),
                "name": payload.get("name"),
                "exp": payload.get("exp"),
                "iat": payload.get("iat")
            }
            
            logger.info(f"✅ Token verified for user: {user_info['user_id']}")
            return user_info
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            raise ValueError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Error verifying token: {str(e)}")
            raise ValueError(f"Token verification failed: {str(e)}")


class PermissionService:
    """
    Handles user permissions and organization access
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.workspace_service_url = os.getenv(
            "WORKSPACE_SERVICE_URL", 
            "http://workspace-intelligence-service:8006"
        )
    
    async def check_org_access(self, user_id: str, org_name: str) -> bool:
        """
        Check if user has access to organization
        
        Args:
            user_id: Auth0 user ID
            org_name: Organization name
            
        Returns:
            True if user has access, False otherwise
        """
        try:
            # Check Redis cache first
            cache_key = f"user:{user_id}:orgs"
            cached_orgs = await self.redis.smembers(cache_key)
            
            if org_name.encode() in cached_orgs:
                return True
            
            # If not cached, verify with workspace-intelligence-service
            # In production, this would call an actual permissions API
            # For now, we'll cache the org if user is accessing it
            logger.info(f"Granting access to {org_name} for user {user_id}")
            await self.redis.sadd(cache_key, org_name)
            await self.redis.expire(cache_key, 3600)  # 1 hour TTL
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking org access: {str(e)}")
            return False
    
    async def get_user_organizations(self, user_id: str) -> List[str]:
        """
        Get list of organizations user has access to
        
        Args:
            user_id: Auth0 user ID
            
        Returns:
            List of organization names
        """
        try:
            cache_key = f"user:{user_id}:orgs"
            orgs = await self.redis.smembers(cache_key)
            return [org.decode() for org in orgs]
        except Exception as e:
            logger.error(f"Error getting user orgs: {str(e)}")
            return []
    
    async def store_user_context(
        self,
        user_id: str,
        session_id: str,
        context: Dict
    ):
        """
        Store user session context in Redis
        
        Args:
            user_id: Auth0 user ID
            session_id: Unique session identifier
            context: Context data (org, project, folder, etc.)
        """
        try:
            session_key = f"session:{user_id}:{session_id}"
            await self.redis.hset(session_key, mapping=context)
            await self.redis.expire(session_key, 3600)  # 1 hour TTL
            logger.debug(f"Stored context for session {session_id}")
        except Exception as e:
            logger.error(f"Error storing context: {str(e)}")
    
    async def get_user_context(
        self,
        user_id: str,
        session_id: str
    ) -> Optional[Dict]:
        """
        Get user session context from Redis
        
        Args:
            user_id: Auth0 user ID
            session_id: Unique session identifier
            
        Returns:
            Context dict or None if not found
        """
        try:
            session_key = f"session:{user_id}:{session_id}"
            context = await self.redis.hgetall(session_key)
            return {k.decode(): v.decode() for k, v in context.items()} if context else None
        except Exception as e:
            logger.error(f"Error getting context: {str(e)}")
            return None


# Global instances
security_service = SecurityService()


async def verify_token(token: str) -> dict:
    """
    FastAPI dependency for JWT token verification
    
    Args:
        token: JWT token string
        
    Returns:
        Dict with user_id and other claims
        
    Raises:
        HTTPException: If token is invalid
    """
    from fastapi import HTTPException, Header
    
    try:
        # Extract token from Authorization header
        if not token:
            raise HTTPException(status_code=401, detail="Missing authorization token")
        
        # Remove "Bearer " prefix if present
        if token.startswith("Bearer "):
            token = token[7:]
        
        # Validate token using security service
        payload = security_service.validate_token(token)
        
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "org_id": payload.get("org_id")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise HTTPException(status_code=401, detail="Token verification failed")
