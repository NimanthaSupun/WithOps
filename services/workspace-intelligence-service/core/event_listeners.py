"""
Event Listeners for Workspace Intelligence Service
Subscribes to events from other services and handles them appropriately
"""
import logging
from typing import Dict
from datetime import datetime

from core.event_bus import event_bus
from core.workspace_analyzer import WorkspaceAnalyzer
from core.repository_tree_manager import RepositoryTreeManager
from database import db_manager

logger = logging.getLogger(__name__)


class EventListeners:
    """Handles incoming events from other microservices"""
    
    def __init__(self):
        self.registered = False
        
    async def register_all_handlers(self):
        """Register all event handlers with the event bus"""
        if self.registered:
            logger.warning("⚠️ Event handlers already registered")
            return
            
        try:
            # GitHub service events
            event_bus.register_handler("github.repository.added", self.handle_repository_added)
            event_bus.register_handler("github.repository.removed", self.handle_repository_removed)
            event_bus.register_handler("github.workflows.updated", self.handle_workflows_updated)
            event_bus.register_handler("github.installation.added", self.handle_installation_added)
            event_bus.register_handler("github.installation.removed", self.handle_installation_removed)
            
            # Collaboration service events (if needed in future)
            # event_bus.register_handler("collaboration.team.created", self.handle_team_created)
            
            self.registered = True
            logger.info("✅ Event handlers registered successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to register event handlers: {e}")
            raise
    
    async def handle_repository_added(self, event_data: Dict):
        """
        Handle repository.added event from GitHub service
        Trigger workspace analysis refresh for affected organization
        """
        try:
            org_name = event_data.get("organization_name")
            repo_name = event_data.get("repository_name")
            user_id = event_data.get("user_id", "system")
            
            logger.info(f"📥 Repository added: {org_name}/{repo_name}")
            
            # Check if organization has an active repository tree
            async with db_manager.get_session() as session:
                tree = await RepositoryTreeManager.get_repository_tree(
                    session,
                    org_name,
                    user_id
                )
                
                if tree and tree.tree_data:
                    # Repository tree exists, trigger re-analysis
                    logger.info(f"🔄 Triggering workspace re-analysis for {org_name} due to new repository")
                    
                    # You can either:
                    # 1. Auto-add to tree and re-analyze
                    # 2. Just log and wait for manual refresh
                    # 3. Publish notification event to collaboration service
                    
                    # For now, just publish a notification event
                    await event_bus.publish_event(
                        "workspace_intelligence_events",
                        {
                            "type": "workspace.repository_added",
                            "organization_name": org_name,
                            "repository_name": repo_name,
                            "user_id": user_id,
                            "tree_id": tree.id,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                else:
                    logger.info(f"ℹ️ No repository tree found for {org_name}, skipping auto-analysis")
                    
        except Exception as e:
            logger.error(f"❌ Error handling repository.added event: {e}", exc_info=True)
    
    async def handle_repository_removed(self, event_data: Dict):
        """
        Handle repository.removed event from GitHub service
        Update repository tree if repository was part of it
        """
        try:
            org_name = event_data.get("organization_name")
            repo_name = event_data.get("repository_name")
            user_id = event_data.get("user_id", "system")
            
            logger.info(f"📥 Repository removed: {org_name}/{repo_name}")
            
            # Check if repository exists in any tree
            async with db_manager.get_session() as session:
                tree = await RepositoryTreeManager.get_repository_tree(
                    session,
                    org_name,
                    user_id
                )
                
                if tree and tree.tree_data:
                    # Check if repository exists in tree
                    tree_updated = False
                    tree_data = tree.tree_data
                    
                    for folder in tree_data:
                        if "items" in folder:
                            original_count = len(folder["items"])
                            folder["items"] = [
                                item for item in folder["items"]
                                if item.get("full_name") != f"{org_name}/{repo_name}"
                            ]
                            if len(folder["items"]) < original_count:
                                tree_updated = True
                                logger.info(f"🗑️ Removed {repo_name} from folder '{folder.get('name')}'")
                    
                    if tree_updated:
                        # Save updated tree
                        await RepositoryTreeManager.save_repository_tree(
                            session,
                            tree.id,
                            org_name,
                            tree_data,
                            user_id
                        )
                        logger.info(f"✅ Repository tree updated after removal of {repo_name}")
                        
        except Exception as e:
            logger.error(f"❌ Error handling repository.removed event: {e}", exc_info=True)
    
    async def handle_workflows_updated(self, event_data: Dict):
        """
        Handle workflows.updated event from GitHub service
        Optionally trigger analysis refresh for affected repositories
        """
        try:
            org_name = event_data.get("organization_name")
            repo_name = event_data.get("repository_name")
            workflows_count = event_data.get("workflows_count", 0)
            
            logger.info(f"📥 Workflows updated for {org_name}/{repo_name}: {workflows_count} workflows")
            
            # For now, just log the event
            # In future, you might want to trigger selective re-analysis
            # of security practices and maturity scores
            
        except Exception as e:
            logger.error(f"❌ Error handling workflows.updated event: {e}", exc_info=True)
    
    async def handle_installation_added(self, event_data: Dict):
        """
        Handle installation.added event from GitHub service
        Initialize repository tree structure for new organization
        """
        try:
            org_name = event_data.get("organization_name")
            user_id = event_data.get("user_id", "system")
            installation_id = event_data.get("installation_id")
            
            logger.info(f"📥 GitHub App installed for organization: {org_name} (ID: {installation_id})")
            
            # Optionally create an empty repository tree
            async with db_manager.get_session() as session:
                existing_tree = await RepositoryTreeManager.get_repository_tree(
                    session,
                    org_name,
                    user_id
                )
                
                if not existing_tree:
                    # Create empty tree structure
                    empty_tree = []
                    await RepositoryTreeManager.save_repository_tree(
                        session,
                        None,  # New tree
                        org_name,
                        empty_tree,
                        user_id
                    )
                    logger.info(f"✅ Created empty repository tree for {org_name}")
                else:
                    logger.info(f"ℹ️ Repository tree already exists for {org_name}")
                    
        except Exception as e:
            logger.error(f"❌ Error handling installation.added event: {e}", exc_info=True)
    
    async def handle_installation_removed(self, event_data: Dict):
        """
        Handle installation.removed event from GitHub service
        Mark repository tree as inactive or delete it
        """
        try:
            org_name = event_data.get("organization_name")
            user_id = event_data.get("user_id", "system")
            
            logger.info(f"📥 GitHub App uninstalled from organization: {org_name}")
            
            # Optionally soft-delete the repository tree
            async with db_manager.get_session() as session:
                tree = await RepositoryTreeManager.get_repository_tree(
                    session,
                    org_name,
                    user_id
                )
                
                if tree:
                    await RepositoryTreeManager.delete_repository_tree(
                        session,
                        tree.id,
                        user_id
                    )
                    logger.info(f"✅ Soft-deleted repository tree for {org_name}")
                else:
                    logger.info(f"ℹ️ No repository tree found for {org_name}")
                    
        except Exception as e:
            logger.error(f"❌ Error handling installation.removed event: {e}", exc_info=True)


# Global instance
event_listeners = EventListeners()
