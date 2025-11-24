"""
Background Worker for GitHub Service
Handles async refresh jobs and installation verification from Redis queue
"""
import asyncio
import logging
import signal
import sys
from datetime import datetime
from sqlalchemy import select

from core.redis_cache import cache
from core.queue_config import RefreshChannel, RefreshJobType
from core.github_client import github_client
from core.event_bus import event_bus
from core.job_queue import verification_queue
from database import db_manager, OrganizationInstallation, Organization

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GitHubWorker:
    """Background worker for processing GitHub refresh jobs and installation verification"""
    
    def __init__(self):
        self.running = False
        self.tasks = []
        self.jobs_processed = 0
        self.jobs_succeeded = 0
        self.jobs_failed = 0
        
    async def start(self):
        """Start the worker and subscribe to channels"""
        try:
            # Connect to Redis
            await cache.connect()
            logger.info("✅ Worker connected to Redis")
            
            # Connect to event bus
            await event_bus.connect()
            logger.info("✅ Worker connected to event bus")
            
            # Connect to verification queue
            await verification_queue.connect()
            logger.info("✅ Worker connected to verification queue")
            
            # Initialize database (create tables if needed)
            await db_manager.create_tables()
            logger.info("✅ Worker connected to database")
            
            self.running = True
            
            # Subscribe to refresh channels
            self.tasks = [
                asyncio.create_task(self._subscribe_workspace_refresh()),
                asyncio.create_task(self._subscribe_actions_refresh()),
                asyncio.create_task(self._subscribe_workflows_refresh()),
                asyncio.create_task(self._process_verification_queue())  # NEW: Verification jobs
            ]
            
            logger.info("🚀 GitHub worker started and listening for jobs")
            
            # Wait for all tasks
            await asyncio.gather(*self.tasks)
            
        except Exception as e:
            logger.error(f"❌ Worker error: {e}")
            raise
    
    async def stop(self):
        """Stop the worker gracefully"""
        logger.info("🛑 Stopping worker...")
        logger.info(f"📊 Final stats - Verification jobs: {self.jobs_processed}, Succeeded: {self.jobs_succeeded}, Failed: {self.jobs_failed}")
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Disconnect
        await cache.disconnect()
        await event_bus.disconnect()
        await verification_queue.disconnect()
        
        logger.info("✅ Worker stopped")
    
    async def _subscribe_workspace_refresh(self):
        """Subscribe to workspace refresh channel"""
        await cache.subscribe_to_channel(
            RefreshChannel.WORKSPACE_REFRESH,
            self._handle_workspace_refresh
        )
    
    async def _subscribe_actions_refresh(self):
        """Subscribe to actions refresh channel"""
        await cache.subscribe_to_channel(
            RefreshChannel.ACTIONS_REFRESH,
            self._handle_actions_refresh
        )
    
    async def _subscribe_workflows_refresh(self):
        """Subscribe to workflows refresh channel"""
        await cache.subscribe_to_channel(
            RefreshChannel.WORKFLOWS_REFRESH,
            self._handle_workflows_refresh
        )
    
    async def _handle_workspace_refresh(self, message: dict):
        """Handle workspace refresh job"""
        try:
            org_name = message.get("org_name")
            logger.info(f"🔄 Processing workspace refresh for: {org_name}")
            
            # Get installation ID
            installation_id = await github_client._get_installation_id(org_name)
            if not installation_id:
                logger.error(f"❌ No installation found for {org_name}")
                return
            
            # Fetch fresh workspace data
            workspace_data = await github_client.get_organization_workspace_detailed(
                installation_id, 
                org_name, 
                force_fresh=True
            )
            
            logger.info(f"✅ Refreshed workspace for {org_name}: {len(workspace_data.get('repositories', []))} repos, {len(workspace_data.get('workflows', []))} workflows")
            
            # Publish update event to backend
            await event_bus.publish({
                "type": "workspace_updated",
                "org_name": org_name,
                "user_id": message.get("user_id"),
                "data": {
                    "repositories_count": len(workspace_data.get('repositories', [])),
                    "workflows_count": len(workspace_data.get('workflows', [])),
                    "updated_at": datetime.now().isoformat()
                }
            })
            
        except Exception as e:
            logger.error(f"❌ Error refreshing workspace: {e}")
    
    async def _handle_actions_refresh(self, message: dict):
        """Handle actions refresh job"""
        try:
            org_name = message.get("org_name")
            params = message.get("params", {})
            page = params.get("page", 1)
            per_page = params.get("per_page", 20)
            search = params.get("search", "")
            
            logger.info(f"🔄 Processing actions refresh for: {org_name} (page {page})")
            
            # Get installation ID
            installation_id = await github_client._get_installation_id(org_name)
            if not installation_id:
                logger.error(f"❌ No installation found for {org_name}")
                return
            
            # Fetch fresh actions data
            actions_data = await github_client.get_organization_actions_detailed(
                installation_id, 
                org_name
            )
            
            # Cache the full actions data
            await cache.cache_actions_data(org_name, actions_data)
            
            logger.info(f"✅ Refreshed actions for {org_name}: {len(actions_data)} total actions")
            
            # Publish update event
            await event_bus.publish({
                "type": "actions_updated",
                "org_name": org_name,
                "user_id": message.get("user_id"),
                "data": {
                    "actions_count": len(actions_data),
                    "updated_at": datetime.now().isoformat()
                }
            })
            
        except Exception as e:
            logger.error(f"❌ Error refreshing actions: {e}")
    
    async def _handle_workflows_refresh(self, message: dict):
        """Handle workflows refresh job"""
        try:
            org_name = message.get("org_name")
            logger.info(f"🔄 Processing workflows refresh for: {org_name}")
            
            # Get installation ID
            installation_id = await github_client._get_installation_id(org_name)
            if not installation_id:
                logger.error(f"❌ No installation found for {org_name}")
                return
            
            # Fetch fresh workflow data
            workspace_data = await github_client.get_organization_workspace_detailed(
                installation_id, 
                org_name, 
                force_fresh=True
            )
            
            workflows = workspace_data.get('workflows', [])
            logger.info(f"✅ Refreshed workflows for {org_name}: {len(workflows)} workflows")
            
            # Publish update event
            await event_bus.publish({
                "type": "workflows_updated",
                "org_name": org_name,
                "user_id": message.get("user_id"),
                "data": {
                    "workflows_count": len(workflows),
                    "updated_at": datetime.now().isoformat()
                }
            })
            
        except Exception as e:
            logger.error(f"❌ Error refreshing workflows: {e}")
    
    async def _process_verification_queue(self):
        """Process installation verification jobs from queue"""
        logger.info("📡 Verification queue processor started")
        
        while self.running:
            try:
                # Get next job from queue (blocks for 5 seconds)
                job = await verification_queue.dequeue_verification(timeout=5)
                
                if job:
                    await self._process_verification_job(job)
                else:
                    # No job available, just wait
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"❌ Error in verification queue processor: {e}")
                await asyncio.sleep(5)  # Back off on error
    
    async def _process_verification_job(self, job: dict):
        """
        Process a single verification job
        
        Args:
            job: Job dict with org_name, installation_id, user_id
        """
        org_name = job.get("org_name")
        installation_id = job.get("installation_id")
        user_id = job.get("user_id")
        retry_count = job.get("retry_count", 0)
        
        logger.info(f"🔄 Processing verification job for {org_name} (retry: {retry_count})")
        
        try:
            # Verify installation with GitHub API
            try:
                await github_client.get_installation_details(installation_id)
                logger.info(f"✅ GitHub confirms installation {installation_id} is active for {org_name}")
                
                # Update database
                async with db_manager.get_session() as session:
                    # Find the installation record
                    query = (
                        select(OrganizationInstallation, Organization)
                        .join(Organization, OrganizationInstallation.organization_id == Organization.id)
                        .where(Organization.login == org_name)
                        .where(OrganizationInstallation.github_installation_id == installation_id)
                        .where(OrganizationInstallation.user_id == user_id)
                    )
                    
                    result = await session.execute(query)
                    data = result.first()
                    
                    if data:
                        installation, org = data
                        
                        # Update last_verified timestamp
                        installation.last_verified = datetime.utcnow()
                        installation.status = "active"
                        
                        await session.commit()
                        logger.info(f"✅ Updated last_verified for {org_name}")
                    else:
                        logger.warning(f"⚠️ Installation record not found for {org_name}")
                
                # Mark job as completed
                await verification_queue.mark_completed(job)
                self.jobs_succeeded += 1
                
            except Exception as github_error:
                # Installation deleted or suspended on GitHub
                logger.warning(f"⚠️ Installation {installation_id} no longer valid for {org_name}: {github_error}")
                
                # Update database to mark as deleted
                async with db_manager.get_session() as session:
                    query = (
                        select(OrganizationInstallation, Organization)
                        .join(Organization, OrganizationInstallation.organization_id == Organization.id)
                        .where(Organization.login == org_name)
                        .where(OrganizationInstallation.github_installation_id == installation_id)
                        .where(OrganizationInstallation.user_id == user_id)
                    )
                    
                    result = await session.execute(query)
                    data = result.first()
                    
                    if data:
                        installation, org = data
                        
                        # Mark as deleted
                        installation.status = "deleted"
                        installation.uninstalled_at = datetime.utcnow()
                        
                        await session.commit()
                        logger.info(f"🗑️ Marked installation as deleted for {org_name}")
                        
                        # Invalidate cache
                        await cache.invalidate_organization_cache(org_name)
                        logger.info(f"🗑️ Invalidated cache for {org_name}")
                
                # Mark job as completed (successful deletion)
                await verification_queue.mark_completed(job)
                self.jobs_succeeded += 1
            
            self.jobs_processed += 1
            
            # Log stats every 10 jobs
            if self.jobs_processed % 10 == 0:
                queue_size = await verification_queue.get_queue_size()
                logger.info(f"📊 Verification stats - Processed: {self.jobs_processed}, Succeeded: {self.jobs_succeeded}, Failed: {self.jobs_failed}, Queue: {queue_size['total']}")
            
        except Exception as e:
            logger.error(f"❌ Failed to process job for {org_name}: {e}", exc_info=True)
            
            # Mark job as failed (will retry if under limit)
            await verification_queue.mark_failed(job)
            self.jobs_failed += 1


# Global worker instance
worker = GitHubWorker()


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    asyncio.create_task(worker.stop())
    sys.exit(0)


async def main():
    """Main entry point"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start worker
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
