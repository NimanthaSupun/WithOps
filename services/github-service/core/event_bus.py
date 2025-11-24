"""
Event Bus for async communication using Redis Pub/Sub
Simplified version for GitHub Service
"""
import json
import logging
from typing import Dict, Any
import redis.asyncio as redis
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class EventBus:
    """Redis-based event bus for microservices communication"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        self.redis_client = None
        
    async def connect(self):
        """Connect to Redis"""
        if not self.redis_client:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info(f"✅ EventBus connected to Redis: {self.redis_url}")
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
        logger.info("✅ EventBus disconnected from Redis")
    
    async def publish(self, event_data: Dict[str, Any]):
        """
        Publish an event to the event bus
        
        Args:
            event_data: Event payload with 'type' field
        """
        if not self.redis_client:
            await self.connect()
        
        event_type = event_data.get("type", "unknown")
        channel = "github_events"
        
        try:
            # Add timestamp
            event_data["timestamp"] = datetime.now().isoformat()
            
            # Publish to Redis channel
            message = json.dumps(event_data)
            await self.redis_client.publish(channel, message)
            
            logger.info(f"📤 Published event: {event_type} to {channel}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to publish event {event_type}: {e}")
            return False
    
    # ============================================================================
    # GITHUB EVENT PUBLISHERS
    # ============================================================================
    
    async def publish_installation_created(
        self,
        installation_id: int,
        org_login: str,
        org_id: int,
        user_id: str
    ):
        """Publish GitHub App installation created event"""
        return await self.publish({
            "type": "github.installation.created",
            "data": {
                "installation_id": installation_id,
                "organization_login": org_login,
                "organization_id": org_id,
                "user_id": user_id
            },
            "source": "github-service"
        })
    
    async def publish_installation_updated(
        self,
        installation_id: int,
        org_login: str,
        status: str
    ):
        """Publish GitHub App installation updated event"""
        return await self.publish({
            "type": "github.installation.updated",
            "data": {
                "installation_id": installation_id,
                "organization_login": org_login,
                "status": status
            },
            "source": "github-service"
        })
    
    async def publish_organization_updated(
        self,
        org_login: str,
        org_id: int,
        updated_fields: list
    ):
        """Publish organization data updated event"""
        return await self.publish({
            "type": "github.organization.updated",
            "data": {
                "organization_login": org_login,
                "organization_id": org_id,
                "updated_fields": updated_fields
            },
            "source": "github-service"
        })


# Global instance
event_bus = EventBus()
