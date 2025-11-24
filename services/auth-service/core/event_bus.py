"""
Event Bus for async communication using Redis Pub/Sub
Handles authentication-related events
"""
import json
import logging
from typing import Dict, Any, Optional
import redis.asyncio as redis
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class EventBus:
    """Redis-based event bus for authentication events"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        self.redis_client = None
        self.pubsub = None
        
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
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
            self.pubsub = None
            
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
        channel = "auth_events"
        
        try:
            # Add timestamp and source
            event_data["timestamp"] = datetime.now().isoformat()
            event_data["source"] = "auth-service"
            
            # Publish to Redis channel
            message = json.dumps(event_data)
            await self.redis_client.publish(channel, message)
            
            logger.info(f"📤 Published event: {event_type} to {channel}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to publish event {event_type}: {e}")
            return False
    
    # ============================================================================
    # USER EVENT PUBLISHERS
    # ============================================================================
    
    async def publish_user_created(
        self,
        user_id: str,
        auth_user_id: str,
        email: str,
        name: Optional[str] = None
    ):
        """
        Publish user created event
        
        Args:
            user_id: Internal user UUID
            auth_user_id: Auth0 user ID
            email: User email
            name: User name
        """
        return await self.publish({
            "type": "user.created",
            "data": {
                "user_id": user_id,
                "auth_user_id": auth_user_id,
                "email": email,
                "name": name,
                "created_at": datetime.now().isoformat()
            }
        })
    
    async def publish_user_updated(
        self,
        user_id: str,
        auth_user_id: str,
        updated_fields: Dict[str, Any]
    ):
        """
        Publish user updated event
        
        Args:
            user_id: Internal user UUID
            auth_user_id: Auth0 user ID
            updated_fields: Dictionary of updated fields
        """
        return await self.publish({
            "type": "user.updated",
            "data": {
                "user_id": user_id,
                "auth_user_id": auth_user_id,
                "updated_fields": updated_fields,
                "updated_at": datetime.now().isoformat()
            }
        })
    
    async def publish_user_login(
        self,
        user_id: str,
        auth_user_id: str,
        email: str
    ):
        """
        Publish user login event
        
        Args:
            user_id: Internal user UUID
            auth_user_id: Auth0 user ID
            email: User email
        """
        return await self.publish({
            "type": "user.login",
            "data": {
                "user_id": user_id,
                "auth_user_id": auth_user_id,
                "email": email,
                "login_at": datetime.now().isoformat()
            }
        })
    
    async def publish_user_deleted(
        self,
        user_id: str,
        auth_user_id: str
    ):
        """
        Publish user deleted event
        
        Args:
            user_id: Internal user UUID
            auth_user_id: Auth0 user ID
        """
        return await self.publish({
            "type": "user.deleted",
            "data": {
                "user_id": user_id,
                "auth_user_id": auth_user_id,
                "deleted_at": datetime.now().isoformat()
            }
        })
    
    async def publish_session_created(
        self,
        user_id: str,
        auth_user_id: str,
        session_metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Publish session created event
        
        Args:
            user_id: Internal user UUID
            auth_user_id: Auth0 user ID
            session_metadata: Optional session metadata (IP, user agent, etc.)
        """
        return await self.publish({
            "type": "user.session.created",
            "data": {
                "user_id": user_id,
                "auth_user_id": auth_user_id,
                "session_metadata": session_metadata or {},
                "created_at": datetime.now().isoformat()
            }
        })
    
    # ============================================================================
    # EVENT SUBSCRIBER
    # ============================================================================
    
    async def subscribe_to_channels(self, channels: list):
        """
        Subscribe to Redis channels
        
        Args:
            channels: List of channel names to subscribe to
        """
        if not self.redis_client:
            await self.connect()
        
        self.pubsub = self.redis_client.pubsub()
        await self.pubsub.subscribe(*channels)
        logger.info(f"✅ Subscribed to channels: {channels}")
    
    async def start_listening(self, handler):
        """
        Start listening for events
        
        Args:
            handler: Async function to handle incoming events
        """
        if not self.pubsub:
            logger.warning("⚠️ Not subscribed to any channels")
            return
        
        logger.info("🎧 EventBus started listening for events...")
        
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        await handler(event_data)
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Failed to decode event: {e}")
                    except Exception as e:
                        logger.error(f"❌ Error handling event: {e}")
        except Exception as e:
            logger.error(f"❌ EventBus listening error: {e}")


# Global event bus instance
event_bus = EventBus()
