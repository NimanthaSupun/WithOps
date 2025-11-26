"""
Workflow Tree API Routes
Handles project tree management for workflow visualization
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional, Dict, Any
from pydantic import BaseModel
import logging

from database.operations import ProjectTreeRepository
from database.config import db_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/project-tree", tags=["workflow-tree"])


class SaveTreeRequest(BaseModel):
    """Request model for saving tree"""
    tree_data: list


class TreeResponse(BaseModel):
    """Response model for tree data"""
    organization: str
    tree_data: list
    message: str
    success: bool


@router.get("/{org_name}")
async def get_project_tree(
    org_name: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Get project tree for organization
    
    Args:
        org_name: GitHub organization/owner name
        x_user_id: User ID from header
    
    Returns:
        Tree data with statistics
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        async with db_manager.get_session() as session:
            tree = await ProjectTreeRepository.get_tree(session, org_name=org_name, user_id=x_user_id)
            
            if not tree:
                raise HTTPException(status_code=404, detail="Tree not found")
            
            return TreeResponse(
                organization=org_name,
                tree_data=tree.tree_data or [],
                message="Project tree data retrieved successfully",
                success=True
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tree: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get tree: {str(e)}")


@router.post("/{org_name}")
async def save_project_tree(
    org_name: str,
    request: SaveTreeRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Save project tree for organization
    
    Args:
        org_name: GitHub organization/owner name
        request: Tree data to save
        x_user_id: User ID from header
    
    Returns:
        Saved tree with statistics
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        async with db_manager.get_session() as session:
            tree = await ProjectTreeRepository.save_tree(
                session=session,
                user_id=x_user_id,
                org_name=org_name,
                tree_data=request.tree_data
            )
            
            await session.commit()
            
            return TreeResponse(
                organization=org_name,
                tree_data=tree.tree_data or [],
                message="Project tree data saved successfully",
                success=True
            )
    
    except Exception as e:
        logger.error(f"Error saving tree: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save tree: {str(e)}")


@router.delete("/{org_name}")
async def delete_project_tree(
    org_name: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Delete project tree for organization
    
    Args:
        org_name: GitHub organization/owner name
        x_user_id: User ID from header
    
    Returns:
        Success message
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        async with db_manager.get_session() as session:
            tree = await ProjectTreeRepository.get_tree(session, org_name=org_name, user_id=x_user_id)
            
            if not tree:
                raise HTTPException(status_code=404, detail="Tree not found")
            
            await session.delete(tree)
            await session.commit()
            
            return {"message": "Tree deleted successfully", "organization": org_name, "success": True}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting tree: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete tree: {str(e)}")
