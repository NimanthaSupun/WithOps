"""
Event Bus for async communication using Redis Pub/Sub
Threat Modeling Service event publisher
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
    
    async def publish(self, event_type: str, data: Dict[str, Any]):
        """
        Publish a threat modeling event
        
        Args:
            event_type: Type of event (e.g., 'threat.model.created')
            data: Event payload
        """
        if not self.redis_client:
            await self.connect()
        
        channel = "threat_modeling_events"
        
        try:
            event_data = {
                "type": event_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "threat-modeling-service"
            }
            
            # Publish to Redis channel
            message = json.dumps(event_data)
            await self.redis_client.publish(channel, message)
            
            logger.info(f"📤 Published event: {event_type} to {channel}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to publish event {event_type}: {e}")
            return False
    
    async def publish_model_created(self, model_id: str, user_id: str, organization_id: str, name: str):
        """Publish threat model created event"""
        return await self.publish("threat.model.created", {
            "model_id": model_id,
            "user_id": user_id,
            "organization_id": organization_id,
            "name": name
        })
    
    async def publish_model_updated(self, model_id: str, user_id: str, organization_id: str, name: str):
        """Publish threat model updated event"""
        return await self.publish("threat.model.updated", {
            "model_id": model_id,
            "user_id": user_id,
            "organization_id": organization_id,
            "name": name
        })
    
    async def publish_model_deleted(self, model_id: str, user_id: str, organization_id: str, name: str):
        """Publish threat model deleted event"""
        return await self.publish("threat.model.deleted", {
            "model_id": model_id,
            "user_id": user_id,
            "organization_id": organization_id,
            "name": name
        })
    
    async def publish_analysis_requested(self, model_id: str, user_id: str, analysis_type: str):
        """Publish threat analysis requested event"""
        return await self.publish("threat.analysis.requested", {
            "model_id": model_id,
            "user_id": user_id,
            "analysis_type": analysis_type
        })
    
    async def publish_analysis_completed(self, model_id: str, user_id: str, analysis_id: str):
        """Publish threat analysis completed event"""
        return await self.publish("threat.analysis.completed", {
            "model_id": model_id,
            "user_id": user_id,
            "analysis_id": analysis_id
        })


# Global instance
event_bus = EventBus()
