"""
Repository Tree API Routes
Handles repository folder structure operations for workspace analysis
Completely separate from workflow treeview API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import logging
from sqlalchemy import select

from database.config import db_manager
from core.repository_tree_manager import RepositoryTreeManager
from core.security import get_current_user
from database.models import Organization, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/repository-tree", tags=["Repository Tree"])


# =============================================================================
# Helper Functions
# =============================================================================

async def get_user_uuid_from_auth_id(session, auth_user_id: str) -> str:
    """
    Get user UUID from Auth0 user ID
    
    Args:
        session: Database session
        auth_user_id: Auth0 user ID (e.g., 'google-oauth2|123')
    
    Returns:
        User UUID string
        
    Raises:
        HTTPException: If user not found
    """
    result = await session.execute(
        select(User).filter(User.auth_user_id == auth_user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found in database. Please log in again."
        )
    
    return user.id


# =============================================================================
# Pydantic Models for Request/Response
# =============================================================================

class RepositoryTreeSaveRequest(BaseModel):
    """Request model for saving repository tree"""
    organization_login: str
    tree_data: List[Dict[str, Any]]
    name: Optional[str] = "Repository Structure"
    description: Optional[str] = None


class RepositoryTreeResponse(BaseModel):
    """Response model for repository tree operations"""
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    message: Optional[str] = None


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/{org_login}")
async def get_repository_tree(
    org_login: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get repository tree structure for an organization
    
    GET /api/repository-tree/{org_login}
    
    Returns:
        Repository tree data with folders and repositories
    """
    try:
        auth_user_id = current_user  # Auth0 user ID
        
        if not auth_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )
        
        # Get organization from database
        async with db_manager.get_session() as session:
            # Get user UUID from Auth0 ID
            user_id = await get_user_uuid_from_auth_id(session, auth_user_id)
            
            result = await session.execute(
                select(Organization).filter(Organization.login == org_login)
            )
            org = result.scalar_one_or_none()
            
            if not org:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Organization '{org_login}' not found"
                )
            
            # Get repository tree
            manager = RepositoryTreeManager(session)
            tree_result = await manager.get_repository_tree(org.id, user_id)
            
            if tree_result.get("success"):
                return {
                    "success": True,
                    "data": tree_result.get("data", []),
                    "metadata": tree_result.get("metadata", {})
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=tree_result.get("error", "Failed to get repository tree")
                )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_repository_tree: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/save")
async def save_repository_tree(
    request: RepositoryTreeSaveRequest,
    current_user: str = Depends(get_current_user)
):
    """
    Save or update repository tree structure
    
    POST /api/repository-tree/save
    Body: {
        "organization_login": "org-name",
        "tree_data": [...],
        "name": "Repository Structure",
        "description": "Optional description"
    }
    
    Returns:
        Success status and tree ID
    """
    try:
        logger.info(f"📥 Save repository tree request: org={request.organization_login}, data_length={len(request.tree_data)}")
        
        auth_user_id = current_user  # Auth0 user ID
        
        if not auth_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )
        
        # Get organization from database
        async with db_manager.get_session() as session:
            # Get user UUID from Auth0 ID
            user_id = await get_user_uuid_from_auth_id(session, auth_user_id)
            
            result = await session.execute(
                select(Organization).filter(Organization.login == request.organization_login)
            )
            org = result.scalar_one_or_none()
            
            if not org:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Organization '{request.organization_login}' not found"
                )
            
            # Save repository tree
            manager = RepositoryTreeManager(session)
            save_result = await manager.save_repository_tree(
                organization_id=org.id,
                user_id=user_id,
                tree_data=request.tree_data,
                name=request.name,
                description=request.description
            )
            
            if save_result.get("success"):
                return {
                    "success": True,
                    "tree_id": save_result.get("tree_id"),
                    "version": save_result.get("version"),
                    "message": save_result.get("message")
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=save_result.get("error", "Failed to save repository tree")
                )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in save_repository_tree: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{org_login}")
async def delete_repository_tree(
    org_login: str,
    current_user: str = Depends(get_current_user)
):
    """
    Delete repository tree structure
    
    DELETE /api/repository-tree/{org_login}
    
    Returns:
        Success status
    """
    try:
        auth_user_id = current_user  # Auth0 user ID
        
        if not auth_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )
        
        # Get organization from database
        async with db_manager.get_session() as session:
            # Get user UUID from Auth0 ID
            user_id = await get_user_uuid_from_auth_id(session, auth_user_id)
            
            result = await session.execute(
                select(Organization).filter(Organization.login == org_login)
            )
            org = result.scalar_one_or_none()
            
            if not org:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Organization '{org_login}' not found"
                )
            
            # Delete repository tree
            manager = RepositoryTreeManager(session)
            delete_result = await manager.delete_repository_tree(org.id, user_id)
            
            if delete_result.get("success"):
                return {
                    "success": True,
                    "message": delete_result.get("message")
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=delete_result.get("error", "Failed to delete repository tree")
                )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_repository_tree: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{org_login}/statistics")
async def get_repository_tree_statistics(
    org_login: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get statistics about repository tree structure
    
    GET /api/repository-tree/{org_login}/statistics
    
    Returns:
        Statistics: folder count, repository count, workflow count
    """
    try:
        auth_user_id = current_user  # Auth0 user ID
        
        if not auth_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )
        
        # Get organization from database
        async with db_manager.get_session() as session:
            # Get user UUID from Auth0 ID
            user_id = await get_user_uuid_from_auth_id(session, auth_user_id)
            
            result = await session.execute(
                select(Organization).filter(Organization.login == org_login)
            )
            org = result.scalar_one_or_none()
            
            if not org:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Organization '{org_login}' not found"
                )
            
            # Get statistics
            manager = RepositoryTreeManager(session)
            stats_result = await manager.get_tree_statistics(org.id, user_id)
            
            if stats_result.get("success"):
                return {
                    "success": True,
                    "statistics": stats_result.get("statistics", {})
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=stats_result.get("error", "Failed to get statistics")
                )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_repository_tree_statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

