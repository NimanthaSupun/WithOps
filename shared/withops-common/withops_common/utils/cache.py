"""
Redis caching utilities for microservices
"""

import redis.asyncio as redis
import json
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


class RedisCache:
    """
    Redis cache wrapper for microservices
    Provides simple get/set operations with JSON serialization
    """
    
    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info(f"✅ Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ):
        """Set value in cache with optional expiration (seconds)"""
        if not self.redis_client:
            return
        
        try:
            serialized = json.dumps(value)
            if expire:
                await self.redis_client.setex(key, expire, serialized)
            else:
                await self.redis_client.set(key, serialized)
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
    
    async def delete(self, key: str):
        """Delete key from cache"""
        if not self.redis_client:
            return
        
        try:
            await self.redis_client.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
    
    async def publish(self, channel: str, message: dict):
        """Publish message to Redis Pub/Sub channel"""
        if not self.redis_client:
            return
        
        try:
            serialized = json.dumps(message)
            await self.redis_client.publish(channel, serialized)
        except Exception as e:
            logger.error(f"Publish error to channel {channel}: {e}")


# Global cache instance
cache = RedisCache()
