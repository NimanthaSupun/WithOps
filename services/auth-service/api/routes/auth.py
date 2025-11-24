"""
Authentication routes for Auth Service
Handles Auth0 callbacks, user profiles, and authentication status
"""

from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging
import time
import json

from core.security import verify_token, get_current_user
from core.user_manager import get_or_create_user, get_user_by_auth_id
from database.config import get_db_session
from database.models import User, Organization, OrganizationInstallation, Repository, Workflow
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

router = APIRouter()
logger = logging.getLogger(__name__)

# Redis cache for dashboard data
_redis_client = None

async def get_redis():
    """Get Redis client"""
    global _redis_client
    if not _redis_client:
        import redis.asyncio as redis
        import os
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        _redis_client = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
    return _redis_client


class AuthCallbackResponse(BaseModel):
    """Response for auth callback"""
    message: str
    user: dict


class UserProfileResponse(BaseModel):
    """Response for user profile"""
    message: str
    user_id: str
    user_data: dict
    timestamp: str


@router.post("/callback", response_model=AuthCallbackResponse)
async def auth_callback(
    authorization: str = Header(...),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Handle Auth0 authentication callback
    Creates or updates user in database
    
    Args:
        authorization: Bearer token from Auth0
        session: Database session
        
    Returns:
        Authentication confirmation with user info
    """
    try:
        # Extract token
        token = authorization.split(" ")[1]
        
        # Verify token and get user info
        user_info = await verify_token(token)
        auth_user_id = user_info['sub']
        
        logger.info(f"Auth callback for user: {auth_user_id}")
        
        # Get or create user
        user = await get_or_create_user(session, auth_user_id, user_info)
        
        return {
            "message": "Authenticated",
            "user": {
                "sub": auth_user_id,
                "email": user.email,
                "name": user.name,
                "picture": user.avatar_url,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None
            }
        }
        
    except Exception as e:
        logger.error(f"Auth callback error: {e}")
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/me", response_model=UserProfileResponse)
async def get_user_profile(
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get current user profile
    
    Args:
        current_user: Auth0 user ID from token
        session: Database session
        
    Returns:
        User profile data
    """
    try:
        # Get user from database
        user = await get_user_by_auth_id(session, current_user)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "message": "User profile retrieved successfully",
            "user_id": current_user,
            "user_data": {
                "name": user.name,
                "email": user.email,
                "picture": user.avatar_url,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile fetch error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user profile")


@router.get("/validate")
async def validate_token_endpoint(
    current_user: str = Depends(get_current_user)
):
    """
    Validate JWT token
    Used by other microservices to validate user tokens
    
    Args:
        current_user: Auth0 user ID from token
        
    Returns:
        Validation result with user ID
    """
    return {
        "valid": True,
        "user_id": current_user,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/dashboard")
async def get_dashboard_data(
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get dashboard data with database statistics
    Uses Redis cache with 5-minute TTL
    
    Args:
        current_user: Auth0 user ID from token
        session: Database session
        
    Returns:
        Dashboard statistics including organizations, repositories, and workflows
    """
    try:
        start_time = time.time()
        
        # Try to get from cache first
        cache_key = f"dashboard:{current_user}"
        redis = await get_redis()
        
        try:
            cached_data = await redis.get(cache_key)
            if cached_data:
                logger.info(f"✅ Dashboard data served from cache for user {current_user}")
                data = json.loads(cached_data)
                data["performance"]["cache_hit"] = True
                data["performance"]["load_time_seconds"] = round(time.time() - start_time, 2)
                return data
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        
        # Get user first
        user_query = select(User).where(User.auth_user_id == current_user)
        result = await session.execute(user_query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Initialize with safe defaults
        organizations = []
        repo_count = 0
        workflow_count = 0
        
        try:
            # Get user's organizations through OrganizationInstallation
            org_query = select(Organization).join(
                OrganizationInstallation, Organization.id == OrganizationInstallation.organization_id
            ).where(OrganizationInstallation.user_id == user.id)
            org_result = await session.execute(org_query)
            organizations = org_result.scalars().all()
        except Exception as e:
            logger.warning(f"Failed to fetch organizations for user {current_user}: {e}")
        
        try:
            # Get total repository count
            repo_count_query = select(func.count(Repository.id)).join(
                OrganizationInstallation, Repository.installation_id == OrganizationInstallation.id
            ).where(OrganizationInstallation.user_id == user.id)
            repo_count_result = await session.execute(repo_count_query)
            repo_count = repo_count_result.scalar() or 0
        except Exception as e:
            logger.warning(f"Failed to fetch repository count for user {current_user}: {e}")
        
        try:
            # Get total workflow count
            workflow_count_query = select(func.count(Workflow.id)).join(
                Repository, Workflow.repository_id == Repository.id
            ).join(
                OrganizationInstallation, Repository.installation_id == OrganizationInstallation.id
            ).where(OrganizationInstallation.user_id == user.id)
            workflow_count_result = await session.execute(workflow_count_query)
            workflow_count = workflow_count_result.scalar() or 0
        except Exception as e:
            logger.warning(f"Failed to fetch workflow count for user {current_user}: {e}")
        
        elapsed_time = time.time() - start_time
        logger.info(f"📊 Dashboard data loaded in {elapsed_time:.2f} seconds for user {current_user}")
        
        response_data = {
            "message": "Welcome to your dashboard!",
            "user_id": current_user,
            "dashboard_data": {
                "projects": repo_count,
                "scans": workflow_count,
                "alerts": 0,
                "status": "active"
            },
            "quick_stats": {
                "total_orgs": len(organizations),
                "total_repos": repo_count,
                "total_workflows": workflow_count
            },
            "performance": {
                "load_time_seconds": round(elapsed_time, 2),
                "cache_hit": False
            }
        }
        
        # Cache for 5 minutes (300 seconds)
        try:
            await redis.setex(cache_key, 300, json.dumps(response_data))
            logger.info(f"💾 Dashboard data cached for user {current_user}")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dashboard data fetch error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard data")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "auth-service",
        "version": "1.0.0"
    }
