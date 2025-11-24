"""
Event Bus for AI Service - Worker that processes threat analysis tasks
"""
import json
import asyncio
import logging
from typing import Dict, Any, Optional
import redis.asyncio as redis
from datetime import datetime

logger = logging.getLogger(__name__)


class EventBus:
    """Redis-based event bus for microservices communication"""
    
    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub = None
        self.handlers: Dict[str, Any] = {}
        self.running = False
        
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
        if self.redis_client:
            await self.redis_client.close()
        logger.info("✅ EventBus disconnected from Redis")
    
    async def publish(self, event_type: str, data: Dict[str, Any]):
        """
        Publish an event to the event bus
        
        Args:
            event_type: Type of event (e.g., "threat.analysis.completed")
            data: Event payload
        """
        if not self.redis_client:
            await self.connect()
        
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        channel = f"events:{event_type}"
        await self.redis_client.publish(channel, json.dumps(event))
        
        logger.info(f"📤 Published event: {event_type}")
        logger.debug(f"Event data: {data}")


class TaskQueue:
    """Simple task queue using Redis lists"""
    
    def __init__(self, redis_url: str = "redis://redis:6379", queue_name: str = "tasks"):
        self.redis_url = redis_url
        self.queue_name = queue_name
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis"""
        if not self.redis_client:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info(f"✅ TaskQueue connected to Redis: {self.queue_name}")
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
        logger.info("✅ TaskQueue disconnected from Redis")
    
    async def dequeue(self, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """
        Get a task from the queue (blocking)
        
        Args:
            timeout: Seconds to wait for a task
            
        Returns:
            Task data or None if timeout
        """
        if not self.redis_client:
            await self.connect()
        
        result = await self.redis_client.brpop(self.queue_name, timeout=timeout)
        
        if result:
            task = json.loads(result[1])
            logger.info(f"📤 Dequeued task: {task['task_id']}")
            return task
        
        return None
    
    async def update_task_status(self, task_id: str, status: str, result: Optional[Dict] = None):
        """
        Update task status
        
        Args:
            task_id: Task identifier
            status: New status (queued, processing, completed, failed)
            result: Optional result data
        """
        if not self.redis_client:
            await self.connect()
        
        await self.redis_client.setex(
            f"task:{task_id}:status",
            3600,
            status
        )
        
        if result:
            await self.redis_client.setex(
                f"task:{task_id}:result",
                3600,
                json.dumps(result)
            )
        
        logger.info(f"✅ Updated task {task_id} status: {status}")


# Global instances
event_bus = EventBus()
task_queue = TaskQueue(queue_name="threat_analysis_tasks")
