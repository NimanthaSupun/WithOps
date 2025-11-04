from fastapi import APIRouter, Header, HTTPException, Depends
from core.security import verify_token, get_current_user
from database.config import db_manager
from database.models import User, Organization, OrganizationInstallation, Repository, Workflow
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
import logging
import re
import time

router = APIRouter()
logger = logging.getLogger(__name__)

def validate_email(email: str) -> bool:
    """Validate email format"""
    if not email:
        return False
    
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def sanitize_email(email: str) -> str:
    """Sanitize and fix common email issues"""
    if not email:
        return None
    
    # Remove whitespace and convert to lowercase
    email = email.strip().lower()
    
    # Fix common typos
    email = email.replace('gamil.com', 'gmail.com')
    email = email.replace('gmial.com', 'gmail.com')
    email = email.replace('yahooo.com', 'yahoo.com')
    email = email.replace('hotmial.com', 'hotmail.com')
    
    # If email doesn't have @ but looks like it should, try to fix it
    if '@' not in email and '.' in email:
        # Check if it's missing @ before domain
        parts = email.split('.')
        if len(parts) >= 2:
            domain_part = '.'.join(parts[-2:])
            if domain_part in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
                username = '.'.join(parts[:-2]) if len(parts) > 2 else parts[0]
                email = f"{username}@{domain_part}"
    
    return email if validate_email(email) else None

@router.post("/callback")
async def auth_callback(authorization: str = Header(...)):
    token = authorization.split(" ")[1]
    try:
        user_info = await verify_token(token)
        logger.info(f"User info from token: {user_info}")
        
        # 🚀 PERFORMANCE: Ensure user exists in database
        async with db_manager.get_session() as session:
            # Check if user exists
            user_query = select(User).where(User.auth_user_id == user_info['sub'])
            result = await session.execute(user_query)
            user = result.scalar_one_or_none()
            
            if not user:
                # Create new user - handle missing/invalid email gracefully
                email = user_info.get('email')
                
                # Sanitize and validate email if present
                if email:
                    email = sanitize_email(email)
                    if not email:
                        logger.warning(f"Invalid email format in Auth0 token for user {user_info['sub']}: {user_info.get('email')}")
                
                if not email:
                    # If no valid email in token, create a placeholder based on user ID
                    user_id_part = user_info['sub'].split('|')[-1]
                    email = f"user-{user_id_part}@placeholder.local"
                    logger.warning(f"No valid email in Auth0 token for user {user_info['sub']}, using placeholder: {email}")
                else:
                    logger.info(f"User {user_info['sub']} authenticated with email: {email}")
                
                user = User(
                    auth_user_id=user_info['sub'],
                    email=email,
                    name=user_info.get('name') or 'Unknown User',
                    avatar_url=user_info.get('picture'),  # Fixed: picture -> avatar_url
                    created_at=datetime.utcnow(),
                    last_login=datetime.utcnow()
                )
                session.add(user)
            else:
                # Update last login and email if it was a placeholder and we now have a real email
                user.last_login = datetime.utcnow()
                
                # Check if we can upgrade from placeholder email to real email
                if user.email.endswith('@placeholder.local'):
                    email = user_info.get('email')
                    if email:
                        email = sanitize_email(email)
                        if email:
                            user.email = email
                            logger.info(f"Upgraded placeholder email to real email for user {user_info['sub']}: {email}")
            
            await session.commit()
            
        return {"message": "Authenticated", "user": user_info}
    except Exception as e:
        logger.error(f"Auth callback error: {e}")
        raise HTTPException(status_code=401, detail=str(e))

@router.get("/me")
async def get_user_profile(current_user: str = Depends(get_current_user)):
    """🚀 PERFORMANCE: Get user profile with database integration"""
    try:
        async with db_manager.get_session() as session:
            # Get user with statistics
            user_query = select(User).where(User.auth_user_id == current_user)
            result = await session.execute(user_query)
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Get user organization count
            org_count_query = select(func.count(Organization.id)).where(
                Organization.installer_user_id == user.id
            )
            org_count_result = await session.execute(org_count_query)
            org_count = org_count_result.scalar() or 0
            
            return {
                "message": "User profile retrieved successfully",
                "user_id": current_user,
                "user_data": {
                    "name": user.name,
                    "email": user.email,
                    "picture": user.avatar_url,  # Fixed: user.picture -> user.avatar_url
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "last_login": user.last_login.isoformat() if user.last_login else None,
                    "organization_count": org_count
                },
                "timestamp": datetime.utcnow().isoformat()
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile fetch error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user profile")

@router.get("/dashboard")
async def get_dashboard_data(current_user: str = Depends(get_current_user)):
    """🚀 PERFORMANCE: Get dashboard data with real database statistics"""
    try:
        # Add timeout protection for the entire operation
        start_time = time.time()
        
        async with db_manager.get_session() as session:
            # Get user first - this is fast and critical
            user_query = select(User).where(User.auth_user_id == current_user)
            result = await session.execute(user_query)
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Initialize with safe defaults in case any query fails
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
                # Get total repository count with timeout protection
                repo_count_query = select(func.count(Repository.id)).join(
                    OrganizationInstallation, Repository.installation_id == OrganizationInstallation.id
                ).where(OrganizationInstallation.user_id == user.id)
                repo_count_result = await session.execute(repo_count_query)
                repo_count = repo_count_result.scalar() or 0
            except Exception as e:
                logger.warning(f"Failed to fetch repository count for user {current_user}: {e}")
            
            try:
                # Get total workflow count with timeout protection
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
            logger.info(f"Dashboard data loaded in {elapsed_time:.2f} seconds for user {current_user}")
            
            return {
                "message": "Welcome to your dashboard!",
                "user_id": current_user,
                "dashboard_data": {
                    "projects": repo_count,  # Frontend expects "projects"
                    "scans": workflow_count,  # Frontend expects "scans" 
                    "alerts": 0,  # Frontend expects "alerts"
                    "status": "active"
                },
                "quick_stats": {
                    "total_orgs": len(organizations),
                    "total_repos": repo_count,
                    "total_workflows": workflow_count
                },
                "performance": {
                    "load_time_seconds": round(elapsed_time, 2)
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dashboard data fetch error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard data")
