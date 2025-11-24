"""
Test script to verify worker processes refresh messages
"""
import asyncio
import json
from datetime import datetime

from core.redis_cache import cache
from core.queue_config import RefreshChannel, RefreshJobType


async def test_worker_processing():
    """Test if worker receives and processes messages"""
    print("🧪 Testing worker message processing...")
    
    # Connect to Redis
    await cache.connect()
    print("✅ Connected to Redis")
    
    # Test workspace refresh
    workspace_message = {
        "type": RefreshJobType.WORKSPACE_FULL,
        "org_name": "WithOps-Com",
        "user_id": "test-user-123",
        "timestamp": datetime.now().isoformat(),
        "params": {}
    }
    
    success = await cache.publish_refresh_job(
        RefreshChannel.WORKSPACE_REFRESH,
        workspace_message
    )
    
    if success:
        print("✅ Published workspace refresh job")
        print(f"   Message: {json.dumps(workspace_message, indent=2)}")
    else:
        print("❌ Failed to publish workspace refresh job")
    
    # Wait a moment to let worker process
    print("⏳ Waiting for worker to process (5 seconds)...")
    await asyncio.sleep(5)
    
    # Test actions refresh
    actions_message = {
        "type": RefreshJobType.ACTIONS_PAGINATED,
        "org_name": "WithOps-Com",
        "user_id": "test-user-123",
        "timestamp": datetime.now().isoformat(),
        "params": {
            "page": 1,
            "per_page": 20
        }
    }
    
    success = await cache.publish_refresh_job(
        RefreshChannel.ACTIONS_REFRESH,
        actions_message
    )
    
    if success:
        print("✅ Published actions refresh job")
        print(f"   Message: {json.dumps(actions_message, indent=2)}")
    else:
        print("❌ Failed to publish actions refresh job")
    
    print("⏳ Waiting for worker to process (5 seconds)...")
    await asyncio.sleep(5)
    
    # Test workflows refresh
    workflows_message = {
        "type": RefreshJobType.WORKFLOWS_DETAILED,
        "org_name": "WithOps-Com",
        "user_id": "test-user-123",
        "timestamp": datetime.now().isoformat(),
        "params": {}
    }
    
    success = await cache.publish_refresh_job(
        RefreshChannel.WORKFLOWS_REFRESH,
        workflows_message
    )
    
    if success:
        print("✅ Published workflows refresh job")
        print(f"   Message: {json.dumps(workflows_message, indent=2)}")
    else:
        print("❌ Failed to publish workflows refresh job")
    
    print("⏳ Waiting for worker to process (5 seconds)...")
    await asyncio.sleep(5)
    
    # Disconnect
    await cache.disconnect()
    
    print("\n✅ Test completed! Check worker logs with:")
    print("   docker logs withops-github-service-worker")


if __name__ == "__main__":
    asyncio.run(test_worker_processing())
