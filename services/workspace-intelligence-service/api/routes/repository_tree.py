"""
Repository Tree API Routes
Handles repository folder structure operations for workspace analysis
Completely separate from workflow treeview API
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import logging
from sqlalchemy import select

from database.config import db_manager
from database.models import User
from core.repository_tree_manager import RepositoryTreeManager
from core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/repository-tree", tags=["Repository Tree"])


# =============================================================================
# Helper Functions
# =============================================================================

async def resolve_user_uuid(auth_user_id: str, session) -> str:
    """
    Resolve Auth0 user ID to internal UUID
    
    Args:
        auth_user_id: Auth0 user ID (e.g., "google-oauth2|123456")
        session: Database session
        
    Returns:
        User UUID from database
        
    Raises:
        HTTPException: If user not found
    """
    result = await session.execute(
        select(User.id).where(User.auth_user_id == auth_user_id)
    )
    user_uuid = result.scalar()
    
    if not user_uuid:
        logger.warning(f"⚠️ No UUID found for auth_user_id: {auth_user_id}")
        raise HTTPException(
            status_code=404, 
            detail=f"User not found in database. Please login to backend first."
        )
    
    logger.info(f"✅ Resolved {auth_user_id} → {user_uuid}")
    return user_uuid


# =============================================================================
# Pydantic Models for Request/Response
# =============================================================================

class RepositoryTreeSaveRequest(BaseModel):
    """Request model for saving repository tree"""
    organization_login: str  # Match backend API contract
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
    current_user: Optional[str] = Depends(get_current_user)
):
    """
    Get repository tree structure for an organization
    
    GET /api/repository-tree/{org_login}
    
    Returns:
        Repository tree data with folders and repositories
    """
    try:
        async with db_manager.get_session() as session:
            # Resolve user_id from auth token if authenticated
            user_id = "system"  # Default for unauthenticated requests
            if current_user:
                user_id = await resolve_user_uuid(current_user, session)
                logger.info(f"🔐 Authenticated request from user: {user_id}")
            
            # Get repository tree
            manager = RepositoryTreeManager(session)
            tree_result = await manager.get_repository_tree(org_login, user_id)
            
            logger.info(f"🌲 Repository tree result for {org_login}: success={tree_result.get('success')}, has_data={len(tree_result.get('data', [])) > 0}")
            
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
    current_user: Optional[str] = Depends(get_current_user)
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
        async with db_manager.get_session() as session:
            # Resolve user_id from auth token if authenticated
            user_id = "system"  # Default for unauthenticated requests
            if current_user:
                user_id = await resolve_user_uuid(current_user, session)
                logger.info(f"🔐 Authenticated save request from user: {user_id}")
            
            logger.info(f"📥 Save repository tree request: org={request.organization_login}, data_length={len(request.tree_data)}, user_id={user_id}")
            
            # Save repository tree
            manager = RepositoryTreeManager(session)
            save_result = await manager.save_repository_tree(
                organization_name=request.organization_login,  # Pass login as org name
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
    user_id: Optional[str] = None
):
    """
    Delete repository tree structure
    
    DELETE /api/repository-tree/{org_login}?user_id=xxx
    
    Returns:
        Success status
    """
    # Use a default user_id if not provided
    if not user_id:
        user_id = "system"
    
    try:
        async with db_manager.get_session() as session:
            # Delete repository tree
            manager = RepositoryTreeManager(session)
            delete_result = await manager.delete_repository_tree(org_login, user_id)
            
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
    user_id: Optional[str] = None
):
    """
    Get statistics about repository tree structure
    
    GET /api/repository-tree/{org_login}/statistics?user_id=xxx
    
    Returns:
        Statistics: folder count, repository count, workflow count
    """
    # Use a default user_id if not provided
    if not user_id:
        user_id = "system"
    
    try:
        async with db_manager.get_session() as session:
            # Get statistics
            manager = RepositoryTreeManager(session)
            stats_result = await manager.get_tree_statistics(org_login, user_id)
            
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

