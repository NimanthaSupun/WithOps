"""
Background Job Queue for Installation Verification
Uses Redis for job queuing and processing
"""
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class VerificationQueue:
    """
    Redis-based job queue for background installation verification
    Prevents blocking API responses while keeping data fresh
    """
    
    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.queue_name = "github:verification:queue"
        self.processing_set = "github:verification:processing"
        
    async def connect(self):
        """Connect to Redis"""
        if not self.redis_client:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("✅ Verification queue connected to Redis")
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("🔌 Verification queue disconnected from Redis")
    
    async def enqueue_verification(
        self,
        org_name: str,
        installation_id: int,
        user_id: str,
        priority: str = "normal"
    ) -> bool:
        """
        Add installation verification job to queue
        
        Args:
            org_name: Organization login name
            installation_id: GitHub installation ID
            user_id: User UUID who owns this installation
            priority: 'high' or 'normal'
        
        Returns:
            True if enqueued successfully
        """
        try:
            if not self.redis_client:
                await self.connect()
            
            job = {
                "org_name": org_name,
                "installation_id": installation_id,
                "user_id": user_id,
                "priority": priority,
                "enqueued_at": datetime.utcnow().isoformat(),
                "retry_count": 0
            }
            
            # Use different queue for high priority
            queue_name = f"{self.queue_name}:{priority}"
            
            # Add to queue (right push for FIFO)
            await self.redis_client.rpush(queue_name, json.dumps(job))
            
            logger.info(f"📤 Enqueued verification job for {org_name} (priority: {priority})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to enqueue verification for {org_name}: {e}")
            return False
    
    async def dequeue_verification(self, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """
        Get next verification job from queue (blocking)
        Checks high priority queue first, then normal priority
        
        Args:
            timeout: Seconds to wait for job
        
        Returns:
            Job dict or None if timeout
        """
        try:
            if not self.redis_client:
                await self.connect()
            
            # Check high priority first, then normal
            queues = [
                f"{self.queue_name}:high",
                f"{self.queue_name}:normal"
            ]
            
            # BLPOP blocks until job available or timeout
            result = await self.redis_client.blpop(queues, timeout=timeout)
            
            if result:
                queue_name, job_data = result
                job = json.loads(job_data)
                
                # Add to processing set (for crash recovery)
                await self.redis_client.sadd(self.processing_set, job_data)
                
                logger.info(f"📥 Dequeued verification job for {job['org_name']}")
                return job
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to dequeue verification: {e}")
            return None
    
    async def mark_completed(self, job: Dict[str, Any]):
        """Mark job as completed and remove from processing set"""
        try:
            job_data = json.dumps(job)
            await self.redis_client.srem(self.processing_set, job_data)
            logger.debug(f"✅ Marked {job['org_name']} verification as completed")
        except Exception as e:
            logger.error(f"❌ Failed to mark job completed: {e}")
    
    async def mark_failed(self, job: Dict[str, Any], max_retries: int = 3):
        """
        Mark job as failed and re-queue if under retry limit
        
        Args:
            job: Job dict
            max_retries: Maximum retry attempts
        """
        try:
            job_data = json.dumps(job)
            await self.redis_client.srem(self.processing_set, job_data)
            
            retry_count = job.get("retry_count", 0)
            
            if retry_count < max_retries:
                # Re-queue with incremented retry count
                job["retry_count"] = retry_count + 1
                await self.enqueue_verification(
                    org_name=job["org_name"],
                    installation_id=job["installation_id"],
                    user_id=job["user_id"],
                    priority="normal"  # Failed jobs go to normal priority
                )
                logger.warning(f"⚠️ Re-queued failed job for {job['org_name']} (attempt {retry_count + 1}/{max_retries})")
            else:
                logger.error(f"❌ Job for {job['org_name']} failed after {max_retries} retries")
                
        except Exception as e:
            logger.error(f"❌ Failed to handle job failure: {e}")
    
    async def get_queue_size(self) -> Dict[str, int]:
        """Get current queue sizes"""
        try:
            if not self.redis_client:
                await self.connect()
            
            high_size = await self.redis_client.llen(f"{self.queue_name}:high")
            normal_size = await self.redis_client.llen(f"{self.queue_name}:normal")
            processing_size = await self.redis_client.scard(self.processing_set)
            
            return {
                "high_priority": high_size,
                "normal_priority": normal_size,
                "processing": processing_size,
                "total": high_size + normal_size + processing_size
            }
        except Exception as e:
            logger.error(f"❌ Failed to get queue size: {e}")
            return {"high_priority": 0, "normal_priority": 0, "processing": 0, "total": 0}


# Global queue instance
verification_queue = VerificationQueue()
