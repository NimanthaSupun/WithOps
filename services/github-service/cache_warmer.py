"""
Cache Warming Script for GitHub Service
Preloads frequently accessed data on startup
"""
import asyncio
import logging
from datetime import datetime

from core.github_client import github_client
from core.redis_cache import cache
from core.queue_config import RefreshChannel, RefreshJobType

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def warm_cache_for_org(org_name: str):
    """Warm cache for a specific organization"""
    try:
        logger.info(f"🔥 Warming cache for organization: {org_name}")
        
        # Get installation ID
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            logger.warning(f"⚠️ No installation found for {org_name}")
            return False
        
        # Fetch workspace data (will be cached automatically)
        workspace_data = await github_client.get_organization_workspace_detailed(
            installation_id,
            org_name,
            force_fresh=True
        )
        
        logger.info(f"✅ Warmed workspace cache for {org_name}: {workspace_data.get('repository_count', 0)} repos")
        
        # Fetch stats data (will be cached automatically)
        stats_data = await github_client.get_organization_stats(installation_id, org_name)
        
        logger.info(f"✅ Warmed stats cache for {org_name}")
        
        # Queue background job to fetch detailed actions (heavier operation)
        await cache.publish_refresh_job(
            RefreshChannel.ACTIONS_REFRESH,
            {
                "type": RefreshJobType.ACTIONS_PAGINATED,
                "org_name": org_name,
                "user_id": None,
                "timestamp": datetime.now().isoformat(),
                "params": {"page": 1, "per_page": 20}
            }
        )
        
        logger.info(f"✅ Queued actions cache warming for {org_name}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error warming cache for {org_name}: {e}")
        return False


async def warm_cache_from_installations():
    """Warm cache for all organizations with active installations"""
    try:
        logger.info("🔥 Starting cache warming for all installations...")
        
        # Connect to cache
        await cache.connect()
        
        # Get all installations
        installations = await github_client.get_all_user_installations()
        
        if not installations:
            logger.warning("⚠️ No installations found to warm cache")
            return
        
        logger.info(f"📋 Found {len(installations)} installations to warm")
        
        # Warm cache for each organization
        results = []
        for installation in installations:
            org_name = installation.get("account", {}).get("login")
            if org_name:
                result = await warm_cache_for_org(org_name)
                results.append((org_name, result))
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(1)
        
        # Summary
        successful = sum(1 for _, success in results if success)
        logger.info(f"🎉 Cache warming completed: {successful}/{len(results)} organizations")
        
        # Disconnect
        await cache.disconnect()
        
    except Exception as e:
        logger.error(f"❌ Error in cache warming: {e}")


async def warm_cache_for_specific_orgs(org_names: list[str]):
    """Warm cache for specific organizations"""
    try:
        logger.info(f"🔥 Warming cache for {len(org_names)} specific organizations...")
        
        # Connect to cache
        await cache.connect()
        
        # Warm cache for each org
        results = []
        for org_name in org_names:
            result = await warm_cache_for_org(org_name)
            results.append((org_name, result))
            await asyncio.sleep(1)
        
        # Summary
        successful = sum(1 for _, success in results if success)
        logger.info(f"🎉 Cache warming completed: {successful}/{len(results)} organizations")
        
        # Disconnect
        await cache.disconnect()
        
    except Exception as e:
        logger.error(f"❌ Error in cache warming: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Warm cache for specific organizations
        org_names = sys.argv[1:]
        asyncio.run(warm_cache_for_specific_orgs(org_names))
    else:
        # Warm cache for all installations
        asyncio.run(warm_cache_from_installations())
