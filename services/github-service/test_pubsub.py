"""
Test Redis Pub/Sub Connection
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from core.redis_cache import cache
from core.queue_config import RefreshChannel, RefreshJobType
from datetime import datetime


async def test_callback(message):
    """Test callback for received messages"""
    print(f"✅ Received message: {message}")


async def test_pubsub():
    """Test Redis pub/sub functionality"""
    try:
        # Connect to Redis
        await cache.connect()
        print("✅ Connected to Redis")
        
        # Test publish
        test_message = {
            "type": RefreshJobType.WORKSPACE_FULL,
            "org_name": "TestOrg",
            "user_id": "test-user-123",
            "timestamp": datetime.now().isoformat(),
            "params": {}
        }
        
        success = await cache.publish_refresh_job(
            RefreshChannel.WORKSPACE_REFRESH,
            test_message
        )
        
        if success:
            print("✅ Successfully published test message")
        else:
            print("❌ Failed to publish message")
        
        print("✅ Redis pub/sub test completed")
        
        await cache.disconnect()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_pubsub())
