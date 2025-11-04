"""
Redis Cache Manager for DevSecOps Backend
Handles caching of workflow actions data for fast loading
"""

import redis.asyncio as redis
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import asyncio

class RedisCache:
    """
    Redis-based cache manager for workflow actions and related data
    """
    
    def __init__(self):
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis_client = None
        self.cache_ttl = {
            'actions': 1800,      # 30 minutes (OPTIMIZED: was 10min, now 30min)
            'workflows': 1800,    # 30 minutes (OPTIMIZED: was 5min, now 30min)
            'versions': 7200,     # 2 hours (OPTIMIZED: was 1h, now 2h)
            'stats': 600,         # 10 minutes (OPTIMIZED: was 3min, now 10min)
            'search': 600         # 10 minutes (OPTIMIZED: was 2min, now 10min)
        }
        
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            await self.redis_client.ping()
            print("✅ Redis connected successfully")
        except Exception as e:
            print(f"⚠️ Redis connection failed, falling back to memory cache: {e}")
            self.redis_client = None
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            print("🔌 Redis disconnected")
    
    def _get_cache_key(self, cache_type: str, *args) -> str:
        """Generate cache key"""
        args_str = '_'.join(str(arg) for arg in args)
        return f"devsecops:{cache_type}:{args_str}"
    
    async def get(self, cache_type: str, *args) -> Optional[Any]:
        """Get data from cache"""
        if not self.redis_client:
            return None
            
        try:
            key = self._get_cache_key(cache_type, *args)
            data = await self.redis_client.get(key)
            
            if data:
                parsed_data = json.loads(data)
                print(f"🚀 Cache hit for {cache_type}: {key}")
                return parsed_data
            
            return None
        except Exception as e:
            print(f"⚠️ Cache get error for {cache_type}: {e}")
            return None
    
    async def set(self, cache_type: str, data: Any, *args, ttl: Optional[int] = None) -> bool:
        """Set data in cache"""
        if not self.redis_client:
            return False
            
        try:
            key = self._get_cache_key(cache_type, *args)
            ttl_seconds = ttl or self.cache_ttl.get(cache_type, 300)
            
            serialized_data = json.dumps(data, default=str)
            await self.redis_client.setex(key, ttl_seconds, serialized_data)
            
            print(f"💾 Cached {cache_type} for {ttl_seconds}s: {key}")
            return True
        except Exception as e:
            print(f"⚠️ Cache set error for {cache_type}: {e}")
            return False
    
    async def delete(self, cache_type: str, *args) -> bool:
        """Delete data from cache"""
        if not self.redis_client:
            return False
            
        try:
            key = self._get_cache_key(cache_type, *args)
            result = await self.redis_client.delete(key)
            
            if result:
                print(f"🗑️ Deleted cache: {key}")
            return bool(result)
        except Exception as e:
            print(f"⚠️ Cache delete error for {cache_type}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching a pattern"""
        if not self.redis_client:
            return 0
            
        try:
            keys = await self.redis_client.keys(f"devsecops:{pattern}*")
            if keys:
                deleted = await self.redis_client.delete(*keys)
                print(f"🗑️ Cleared {deleted} cache entries matching pattern: {pattern}")
                return deleted
            return 0
        except Exception as e:
            print(f"⚠️ Cache clear error for pattern {pattern}: {e}")
            return 0
    
    async def cache_actions_data(self, org_name: str, actions_data: List[Dict]) -> bool:
        """Cache workflow actions data with metadata"""
        cache_data = {
            'actions': actions_data,
            'cached_at': datetime.now().isoformat(),
            'total_count': len(actions_data),
            'org_name': org_name
        }
        return await self.set('actions', cache_data, org_name)
    
    async def get_cached_actions(self, org_name: str) -> Optional[Dict]:
        """Get cached workflow actions data"""
        return await self.get('actions', org_name)
    
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
        return await self.set('paginated_actions', cache_data, org_name, page, per_page, search_query)
    
    async def get_cached_paginated_actions(self, org_name: str, page: int, per_page: int, 
                                         search_query: str) -> Optional[Dict]:
        """Get cached paginated actions data"""
        return await self.get('paginated_actions', org_name, page, per_page, search_query)
    
    async def clear_org_cache(self, org_name: str) -> int:
        """Clear all cache entries for an organization"""
        patterns = [
            f"actions:{org_name}*",
            f"paginated_actions:{org_name}*",
            f"workflows:{org_name}*",
            f"versions:{org_name}*"
        ]
        
        total_cleared = 0
        for pattern in patterns:
            cleared = await self.clear_pattern(pattern)
            total_cleared += cleared
        
        return total_cleared
    
    async def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        if not self.redis_client:
            return {"status": "disabled", "message": "Redis not available"}
            
        try:
            info = await self.redis_client.info()
            keys = await self.redis_client.keys("devsecops:*")
            
            return {
                "status": "active",
                "total_keys": len(keys),
                "memory_usage": info.get('used_memory_human', 'N/A'),
                "connected_clients": info.get('connected_clients', 0),
                "redis_version": info.get('redis_version', 'N/A')
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

# Global cache instance
cache = RedisCache()
