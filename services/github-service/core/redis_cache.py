"""
Redis cache for GitHub Service with Pub/Sub support
"""
import redis.asyncio as redis
import logging
from typing import Optional, Any, Dict, List, Callable
import json
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache client for GitHub Service"""
    
    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        
    async def connect(self):
        """Connect to Redis"""
        if not self.redis_client:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info(f"✅ Redis cache connected: {self.redis_url}")
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("✅ Redis cache disconnected")
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if not self.redis_client:
            return None
        try:
            return await self.redis_client.get(key)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def set(self, key: str, value: str, ttl: int = 3600):
        """Set value in cache with TTL"""
        if not self.redis_client:
            return False
        try:
            await self.redis_client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def delete(self, key: str):
        """Delete key from cache"""
        if not self.redis_client:
            return False
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    async def clear_pattern(self, pattern: str):
        """Clear all keys matching pattern"""
        if not self.redis_client:
            return 0
        try:
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache keys matching {pattern}")
                return len(keys)
            return 0
        except Exception as e:
            logger.error(f"Redis clear pattern error: {e}")
            return 0
    
    def _get_cache_key(self, cache_type: str, *args) -> str:
        """Generate cache key with namespace"""
        key_parts = [cache_type] + [str(arg) for arg in args]
        return f"devsecops:{':'.join(key_parts)}"
    
    async def get_typed(self, cache_type: str, *args) -> Optional[Dict]:
        """Get typed data from cache"""
        if not self.redis_client:
            return None
            
        try:
            key = self._get_cache_key(cache_type, *args)
            data = await self.redis_client.get(key)
            
            if data:
                parsed_data = json.loads(data)
                logger.info(f"✅ Cache hit: {key}")
                return parsed_data
            
            return None
        except Exception as e:
            logger.error(f"Cache get error for {cache_type}: {e}")
            return None
    
    async def set_typed(self, cache_type: str, data: Any, *args, ttl: int = 300) -> bool:
        """Set typed data in cache"""
        if not self.redis_client:
            return False
            
        try:
            key = self._get_cache_key(cache_type, *args)
            serialized_data = json.dumps(data, default=str)
            await self.redis_client.setex(key, ttl, serialized_data)
            
            logger.info(f"💾 Cached {cache_type} for {ttl}s: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache set error for {cache_type}: {e}")
            return False
    
    async def cache_actions_data(self, org_name: str, actions_data: List[Dict]) -> bool:
        """Cache workflow actions data with metadata"""
        cache_data = {
            'actions': actions_data,
            'cached_at': datetime.now().isoformat(),
            'total_count': len(actions_data),
            'org_name': org_name
        }
        return await self.set_typed('actions', cache_data, org_name)
    
    async def get_cached_actions(self, org_name: str) -> Optional[Dict]:
        """Get cached workflow actions data"""
        return await self.get_typed('actions', org_name)
    
    async def cache_paginated_actions(self, org_name: str, page: int, per_page: int, 
                                    search_query: str, filtered_actions: List[Dict]) -> bool:
        """Cache paginated and filtered actions data"""
        cache_data = {
            'actions': filtered_actions,
            'page': page,
            'per_page': per_page,
            'search_query': search_query,
            'cached_at': datetime.now().isoformat(),
            'total_count': len(filtered_actions)
        }
        return await self.set_typed('paginated_actions', cache_data, org_name, page, per_page, search_query)
    
    async def get_cached_paginated_actions(self, org_name: str, page: int, per_page: int, 
                                         search_query: str) -> Optional[Dict]:
        """Get cached paginated actions data"""
        return await self.get_typed('paginated_actions', org_name, page, per_page, search_query)
    
    # ============================================================================
    # WORKSPACE DATA CACHING
    # ============================================================================
    
    async def cache_workspace_data(self, org_name: str, installation_id: int, 
                                   workspace_data: Dict, ttl: int = 900) -> bool:
        """Cache complete workspace data for an organization"""
        cache_data = {
            **workspace_data,
            'cached_at': datetime.now().isoformat(),
            'installation_id': installation_id,
            'org_name': org_name
        }
        return await self.set_typed('workspace', cache_data, installation_id, org_name, ttl=ttl)
    
    async def get_cached_workspace_data(self, org_name: str, installation_id: int) -> Optional[Dict]:
        """Get cached workspace data with age information"""
        cached = await self.get_typed('workspace', installation_id, org_name)
        
        if cached and 'cached_at' in cached:
            # Calculate cache age
            cached_time = datetime.fromisoformat(cached['cached_at'])
            cache_age = (datetime.now() - cached_time).total_seconds()
            cached['cache_age'] = cache_age
            
        return cached
    
    async def invalidate_workspace_cache(self, org_name: str) -> int:
        """Invalidate all workspace cache for an organization"""
        pattern = f"devsecops:workspace:*:{org_name}"
        return await self.clear_pattern(pattern)
    
    async def cache_organization_stats(self, org_name: str, stats_data: Dict, ttl: int = 600) -> bool:
        """Cache organization statistics"""
        cache_data = {
            **stats_data,
            'cached_at': datetime.now().isoformat(),
            'org_name': org_name
        }
        return await self.set_typed('org_stats', cache_data, org_name, ttl=ttl)
    
    async def get_cached_organization_stats(self, org_name: str) -> Optional[Dict]:
        """Get cached organization statistics"""
        return await self.get_typed('org_stats', org_name)
    
    async def invalidate_organization_cache(self, org_name: str) -> int:
        """Invalidate all cache entries for an organization"""
        pattern = f"devsecops:*:{org_name}*"
        return await self.clear_pattern(pattern)
    
    async def clear_organization_cache(self, org_name: str, installation_id: int) -> int:
        """Clear all cache entries for an organization including workspace data"""
        try:
            count = 0
            # Clear workspace cache
            workspace_key = self._get_cache_key('workspace', org_name, installation_id)
            if await self.redis_client.delete(workspace_key):
                count += 1
                logger.info(f"🗑️ Cleared workspace cache: {workspace_key}")
            
            # Clear actions cache
            actions_key = self._get_cache_key('actions', org_name)
            if await self.redis_client.delete(actions_key):
                count += 1
                logger.info(f"🗑️ Cleared actions cache: {actions_key}")
            
            # Clear org stats cache
            stats_key = self._get_cache_key('org_stats', org_name)
            if await self.redis_client.delete(stats_key):
                count += 1
                logger.info(f"🗑️ Cleared org stats cache: {stats_key}")
            
            # Clear any paginated actions cache
            pattern = f"devsecops:paginated_actions:{org_name}:*"
            paginated_count = await self.clear_pattern(pattern)
            count += paginated_count
            
            # Clear detailed workflows cache
            pattern = f"devsecops:detailed_workflows:{org_name}"
            workflows_count = await self.clear_pattern(pattern)
            count += workflows_count
            
            logger.info(f"✅ Cleared {count} cache entries for {org_name}")
            return count
        except Exception as e:
            logger.error(f"Error clearing organization cache: {e}")
            return 0
    
    # ============================================================================
    # PUB/SUB FOR ASYNC BACKGROUND REFRESH
    # ============================================================================
    
    async def publish_refresh_job(self, channel: str, message: Dict) -> bool:
        """Publish a refresh job to Redis queue"""
        if not self.redis_client:
            return False
        try:
            message_json = json.dumps(message, default=str)
            await self.redis_client.publish(channel, message_json)
            logger.info(f"📤 Published refresh job to {channel}: {message.get('type')}")
            return True
        except Exception as e:
            logger.error(f"Redis publish error: {e}")
            return False
    
    async def subscribe_to_channel(self, channel: str, callback: Callable):
        """Subscribe to Redis channel and handle messages"""
        if not self.redis_client:
            logger.error("Redis client not connected")
            return
        
        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(channel)
            logger.info(f"📥 Subscribed to channel: {channel}")
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        await callback(data)
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
        except Exception as e:
            logger.error(f"Redis subscribe error: {e}")
            raise


# Global cache instance
cache = RedisCache()
