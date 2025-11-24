"""
Event listeners for Auth Service
Handles events from other microservices
"""
import logging
from typing import Dict, Any
from core.event_bus import event_bus

logger = logging.getLogger(__name__)


class AuthEventListeners:
    """Event listeners for authentication-related events"""
    
    def __init__(self):
        self.handlers = {}
    
    async def handle_event(self, event_data: Dict[str, Any]):
        """
        Route incoming events to appropriate handlers
        
        Args:
            event_data: Event payload with 'type' field
        """
        event_type = event_data.get("type")
        
        if not event_type:
            logger.warning("⚠️ Received event without type")
            return
        
        handler = self.handlers.get(event_type)
        
        if handler:
            try:
                await handler(event_data)
            except Exception as e:
                logger.error(f"❌ Error handling {event_type}: {e}")
        else:
            logger.debug(f"ℹ️ No handler for event type: {event_type}")
    
    # ============================================================================
    # GITHUB EVENT HANDLERS
    # ============================================================================
    
    async def on_github_installation_added(self, event_data: Dict[str, Any]):
        """
        Handle GitHub installation added event
        Update user's GitHub connection status
        
        Args:
            event_data: Event with installation details
        """
        try:
            data = event_data.get("data", {})
            user_id = data.get("user_id")
            org_login = data.get("organization_login")
            installation_id = data.get("installation_id")
            
            logger.info(f"📥 GitHub installation added: {org_login} for user {user_id}")
            
            # Future: Update user metadata to track GitHub connections
            # For now, just log the event
            
        except Exception as e:
            logger.error(f"❌ Error handling github.installation.added: {e}")
    
    async def on_github_installation_removed(self, event_data: Dict[str, Any]):
        """
        Handle GitHub installation removed event
        Update user's GitHub connection status
        
        Args:
            event_data: Event with installation details
        """
        try:
            data = event_data.get("data", {})
            user_id = data.get("user_id")
            org_login = data.get("organization_login")
            
            logger.info(f"📥 GitHub installation removed: {org_login} for user {user_id}")
            
            # Future: Update user metadata
            
        except Exception as e:
            logger.error(f"❌ Error handling github.installation.removed: {e}")
    
    # ============================================================================
    # THREAT MODELING EVENT HANDLERS
    # ============================================================================
    
    async def on_threat_model_created(self, event_data: Dict[str, Any]):
        """
        Handle threat model created event
        Track user activity
        
        Args:
            event_data: Event with threat model details
        """
        try:
            data = event_data.get("data", {})
            user_id = data.get("user_id")
            model_name = data.get("model_name")
            
            logger.info(f"📥 Threat model created: {model_name} by user {user_id}")
            
            # Future: Track user activity metrics
            
        except Exception as e:
            logger.error(f"❌ Error handling threat_model.created: {e}")
    
    # ============================================================================
    # COLLABORATION EVENT HANDLERS
    # ============================================================================
    
    async def on_user_invited(self, event_data: Dict[str, Any]):
        """
        Handle user invited to collaboration
        Send notification email
        
        Args:
            event_data: Event with invitation details
        """
        try:
            data = event_data.get("data", {})
            invited_user_id = data.get("invited_user_id")
            invited_by = data.get("invited_by")
            project = data.get("project")
            
            logger.info(f"📥 User invited: {invited_user_id} by {invited_by} to {project}")
            
            # Future: Send email notification
            
        except Exception as e:
            logger.error(f"❌ Error handling user.invited: {e}")
    
    # ============================================================================
    # REGISTRATION
    # ============================================================================
    
    async def register_all_handlers(self):
        """Register all event handlers"""
        
        # GitHub events
        self.handlers["github.installation.added"] = self.on_github_installation_added
        self.handlers["github.installation.removed"] = self.on_github_installation_removed
        
        # Threat modeling events
        self.handlers["threat_model.created"] = self.on_threat_model_created
        
        # Collaboration events
        self.handlers["user.invited"] = self.on_user_invited
        
        logger.info(f"✅ Registered {len(self.handlers)} event handlers")
        
        # Subscribe to channels
        channels = ["github_events", "threat_modeling_events", "collaboration_events"]
        await event_bus.subscribe_to_channels(channels)
        logger.info(f"✅ Subscribed to event channels: {channels}")


# Global event listeners instance
event_listeners = AuthEventListeners()
