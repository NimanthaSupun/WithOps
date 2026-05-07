"""
Repository Tree Manager
Handles repository folder structure for workspace analysis and DevSecOps intelligence
Completely separate from workflow treeview (ProjectTree)
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, select
from datetime import datetime
import logging

from database.models import RepositoryTree, Organization
from core.event_bus import event_bus

logger = logging.getLogger(__name__)


class RepositoryTreeManager:
    """
    Manages repository tree structure for organizations
    This is separate from ProjectTree (workflow treeview)
    Focus: Workspace analysis, DevSecOps intelligence, CI/CD maturity
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_repository_tree(
        self, 
        organization_name: str, 
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get repository tree structure for an organization
        
        Args:
            organization_name: Organization login name or ID
            user_id: User ID requesting the tree (use "system" for unauthenticated access)
            
        Returns:
            Repository tree data or None if not found
        """
        try:
            
            # Build query based on user_id
            # If user_id is "system" (unauthenticated), get any tree for the org
            # Otherwise, get tree specific to the user
            # Try matching by organization_name OR organization_id for flexibility
            if user_id == "system":
                result = await self.db.execute(
                    select(RepositoryTree).filter(
                        and_(
                            or_(
                                RepositoryTree.organization_name == organization_name,
                                RepositoryTree.organization_id == organization_name
                            ),
                            RepositoryTree.is_active == True
                        )
                    ).order_by(RepositoryTree.updated_at.desc())  # Get most recent
                )
                tree = result.scalars().first()  # Get first result when multiple exist
            else:
                result = await self.db.execute(
                    select(RepositoryTree).filter(
                        and_(
                            or_(
                                RepositoryTree.organization_name == organization_name,
                                RepositoryTree.organization_id == organization_name
                            ),
                            RepositoryTree.user_id == user_id,
                            RepositoryTree.is_active == True
                        )
                    )
                )
                tree = result.scalar_one_or_none()  # Expect single result for specific user
            
            if tree:
                # Ensure tree_data is a list (handle both JSON and string cases)
                tree_data = tree.tree_data
                if isinstance(tree_data, str):
                    import json
                    try:
                        tree_data = json.loads(tree_data)
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse tree_data as JSON, using empty list")
                        tree_data = []
                elif tree_data is None:
                    tree_data = []
                    
                return {
                    "success": True,
                    "data": tree_data,
                    "metadata": {
                        "id": tree.id,
                        "name": tree.name,
                        "description": tree.description,
                        "version": tree.version,
                        "analysis_status": tree.analysis_status,
                        "maturity_score": tree.maturity_score,
                        "last_analyzed_at": tree.last_analyzed_at.isoformat() if tree.last_analyzed_at else None,
                        "created_at": tree.created_at.isoformat() if tree.created_at else None,
                        "updated_at": tree.updated_at.isoformat() if tree.updated_at else None
                    }
                }
            else:
                logger.info(f"No repository tree found for org {organization_name}, user {user_id}")
                return {
                    "success": True,
                    "data": [],
                    "metadata": {
                        "message": "No repository tree found. Create your first folder structure."
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting repository tree: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def save_repository_tree(
        self, 
        organization_name: str, 
        user_id: str, 
        tree_data: List[Dict[str, Any]],
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save or update repository tree structure
        
        Args:
            organization_name: Organization ID
            user_id: User ID saving the tree (use "system" for unauthenticated access)
            tree_data: Tree structure (folders and repositories)
            name: Optional tree name
            description: Optional description
            
        Returns:
            Success status and tree ID
        """
        try:
            # Look up the organization ID from the organizations table
            org_result = await self.db.execute(
                select(Organization).filter(Organization.login == organization_name)
            )
            org = org_result.scalar_one_or_none()
            
            if not org:
                logger.error(f"Organization not found: {organization_name}")
                return {
                    "success": False,
                    "error": f"Organization '{organization_name}' not found. Please ensure the organization is registered."
                }
            
            organization_id = org.id
            logger.info(f"Resolved organization '{organization_name}' to ID: {organization_id}")
            
            # Check if tree exists for this specific user
            # Query by organization (name or id) and user_id
            result = await self.db.execute(
                select(RepositoryTree).filter(
                    and_(
                        or_(
                            RepositoryTree.organization_name == organization_name,
                            RepositoryTree.organization_id == organization_id
                        ),
                        RepositoryTree.user_id == user_id,
                        RepositoryTree.is_active == True
                    )
                )
            )
            tree = result.scalar_one_or_none()
            
            if tree:
                # Update existing tree
                tree.tree_data = tree_data
                tree.updated_at = datetime.utcnow()
                tree.version += 1
                tree.organization_id = organization_id  # Ensure org_id is correct
                
                if name:
                    tree.name = name
                if description:
                    tree.description = description
                
                await self.db.commit()
                await self.db.refresh(tree)
                
                logger.info(f"Updated repository tree {tree.id} for org {organization_name}")
                
                # Publish update event
                await event_bus.publish_repository_tree_updated(
                    tree_id=tree.id,
                    organization_name=organization_name,
                    user_id=user_id,
                    version=tree.version,
                    tree_data=tree_data
                )
                
            else:
                # Create new tree
                tree = RepositoryTree(
                    organization_id=organization_id,  # Use actual org ID from DB
                    organization_name=organization_name,
                    user_id=user_id,
                    tree_data=tree_data,
                    name=name or "Repository Structure",
                    description=description,
                    version=1,
                    is_active=True,
                    analysis_status="pending"
                )
                self.db.add(tree)
                await self.db.commit()
                await self.db.refresh(tree)
                
                logger.info(f"Created new repository tree for org {organization_name}")
                
                # Publish create event
                await event_bus.publish_repository_tree_created(
                    tree_id=tree.id,
                    organization_name=organization_name,
                    user_id=user_id,
                    tree_data=tree_data
                )
            
            await self.db.commit()
            await self.db.refresh(tree)
            
            return {
                "success": True,
                "tree_id": tree.id,
                "version": tree.version,
                "message": "Repository tree saved successfully"
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error saving repository tree: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_repository_tree(
        self, 
        organization_name: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Delete (soft delete) repository tree structure
        
        Args:
            organization_name: Organization ID
            user_id: User ID requesting deletion (use "system" for unauthenticated access)
            
        Returns:
            Success status
        """
        try:
            # Build query based on user_id
            # Try matching by organization_name OR organization_id
            if user_id == "system":
                result = await self.db.execute(
                    select(RepositoryTree).filter(
                        and_(
                            or_(
                                RepositoryTree.organization_name == organization_name,
                                RepositoryTree.organization_id == organization_name
                            ),
                            RepositoryTree.is_active == True
                        )
                    ).order_by(RepositoryTree.updated_at.desc())
                )
                tree = result.scalars().first()
            else:
                result = await self.db.execute(
                    select(RepositoryTree).filter(
                        and_(
                            or_(
                                RepositoryTree.organization_name == organization_name,
                                RepositoryTree.organization_id == organization_name
                            ),
                            RepositoryTree.user_id == user_id,
                            RepositoryTree.is_active == True
                        )
                    )
                )
                tree = result.scalar_one_or_none()
            
            if tree:
                # Soft delete
                tree.is_active = False
                tree.updated_at = datetime.utcnow()
                await self.db.commit()
                
                logger.info(f"Deleted repository tree {tree.id} for org {organization_name}")
                
                # Publish delete event
                await event_bus.publish_repository_tree_deleted(
                    tree_id=tree.id,
                    organization_name=organization_name,
                    user_id=user_id
                )
                
                return {
                    "success": True,
                    "message": "Repository tree deleted successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Repository tree not found"
                }
                
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting repository tree: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_tree_statistics(
        self, 
        organization_name: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get statistics about the repository tree
        
        Args:
            organization_name: Organization ID
            user_id: User ID (use "system" for unauthenticated access)
            
        Returns:
            Statistics (folder count, repo count, workflow count, etc.)
        """
        try:
            # Build query based on user_id
            # Try matching by organization_name OR organization_id
            if user_id == "system":
                result = await self.db.execute(
                    select(RepositoryTree).filter(
                        and_(
                            or_(
                                RepositoryTree.organization_name == organization_name,
                                RepositoryTree.organization_id == organization_name
                            ),
                            RepositoryTree.is_active == True
                        )
                    ).order_by(RepositoryTree.updated_at.desc())
                )
                tree = result.scalars().first()
            else:
                result = await self.db.execute(
                    select(RepositoryTree).filter(
                        and_(
                            or_(
                                RepositoryTree.organization_name == organization_name,
                                RepositoryTree.organization_id == organization_name
                            ),
                            RepositoryTree.user_id == user_id,
                            RepositoryTree.is_active == True
                        )
                    )
                )
                tree = result.scalar_one_or_none()
            
            if not tree or not tree.tree_data:
                return {
                    "success": True,
                    "statistics": {
                        "total_folders": 0,
                        "total_repositories": 0,
                        "total_workflows": 0,
                        "private_repos": 0,
                        "public_repos": 0
                    }
                }
            
            # Calculate statistics from tree_data
            stats = self._calculate_tree_statistics(tree.tree_data)
            
            return {
                "success": True,
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"Error getting tree statistics: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _calculate_tree_statistics(self, tree_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate statistics from tree data recursively"""
        stats = {
            "total_folders": 0,
            "total_repositories": 0,
            "total_workflows": 0,
            "private_repos": 0,
            "public_repos": 0
        }
        
        def traverse(nodes):
            for node in nodes:
                if node.get("type") == "folder":
                    stats["total_folders"] += 1
                    if node.get("children"):
                        traverse(node["children"])
                        
                elif node.get("type") == "repository":
                    stats["total_repositories"] += 1
                    
                    # Check if private
                    if node.get("metadata", {}).get("private"):
                        stats["private_repos"] += 1
                    else:
                        stats["public_repos"] += 1
                    
                    # Count workflows in repository
                    if node.get("children"):
                        workflow_count = sum(
                            1 for child in node["children"] 
                            if child.get("type") == "workflow"
                        )
                        stats["total_workflows"] += workflow_count
        
        traverse(tree_data)
        return stats
    
    async def update_analysis_status(
        self,
        organization_name: str,
        user_id: str,
        status: str,
        maturity_score: Optional[float] = None,
        analysis_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update analysis status for future workspace intelligence features
        
        Args:
            organization_name: Organization ID
            user_id: User ID
            status: Analysis status (pending, analyzing, completed, failed)
            maturity_score: Optional maturity score (0-100)
            analysis_metadata: Optional analysis results
            
        Returns:
            Success status
        """
        try:
            result = await self.db.execute(
                select(RepositoryTree).filter(
                    and_(
                        RepositoryTree.organization_name == organization_name,
                        RepositoryTree.user_id == user_id,
                        RepositoryTree.is_active == True
                    )
                )
            )
            tree = result.scalar_one_or_none()
            
            if not tree:
                return {
                    "success": False,
                    "error": "Repository tree not found"
                }
            
            tree.analysis_status = status
            tree.last_analyzed_at = datetime.utcnow()
            
            if maturity_score is not None:
                tree.maturity_score = maturity_score
            
            if analysis_metadata:
                tree.analysis_metadata = analysis_metadata
            
            await self.db.commit()
            
            logger.info(f"Updated analysis status for tree {tree.id}: {status}")
            
            return {
                "success": True,
                "message": "Analysis status updated"
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating analysis status: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

