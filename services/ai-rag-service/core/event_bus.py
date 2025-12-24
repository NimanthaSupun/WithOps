"""
Event Bus for ai-rag-service
Listens to analysis completion events and auto-indexes data
"""

import json
import logging
from typing import Dict, Any, Optional, Callable
import redis.asyncio as redis
import os
import asyncio

logger = logging.getLogger(__name__)


class EventBus:
    """Redis-based event bus for listening to analysis events"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        self.redis_client = None
        self.pubsub = None
        self.subscribers = {}
        self.listener_task = None
        
    async def connect(self):
        """Connect to Redis"""
        if not self.redis_client:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            self.pubsub = self.redis_client.pubsub()
            logger.info(f"✅ EventBus connected to Redis: {self.redis_url}")
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
        
        if self.pubsub:
            await self.pubsub.close()
            
        if self.redis_client:
            await self.redis_client.close()
            logger.info("EventBus disconnected")
    
    async def subscribe(self, event_type: str, handler: Callable):
        """
        Subscribe to an event type
        
        Args:
            event_type: Type of event to listen for (e.g., 'workspace_analysis.completed')
            handler: Async function to handle the event
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
            await self.pubsub.subscribe(event_type)
            logger.info(f"📡 Subscribed to event: {event_type}")
        
        self.subscribers[event_type].append(handler)
    
    async def start_listening(self):
        """Start listening for events"""
        if not self.pubsub:
            await self.connect()
        
        logger.info("🎧 Starting event listener...")
        
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    event_type = message["channel"]
                    
                    try:
                        event_data = json.loads(message["data"])
                        
                        # Call all handlers for this event type
                        if event_type in self.subscribers:
                            for handler in self.subscribers[event_type]:
                                try:
                                    await handler(event_data)
                                except Exception as e:
                                    logger.error(f"Error in event handler for {event_type}: {str(e)}")
                    
                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode event data: {message['data']}")
        
        except asyncio.CancelledError:
            logger.info("Event listener stopped")
            raise
        except Exception as e:
            logger.error(f"Error in event listener: {str(e)}")
            raise


# Global instance
event_bus = EventBus()
