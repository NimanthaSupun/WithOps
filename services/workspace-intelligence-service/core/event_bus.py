"""
Event Bus for async communication using Redis Pub/Sub
Workspace Intelligence Service
"""
import json
import logging
from typing import Dict, Any, Optional, Callable
import redis.asyncio as redis
import os
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class EventBus:
    """Redis-based event bus for microservices communication"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        self.redis_client = None
        self.pubsub = None
        self.subscribers = {}  # event_type -> handler function mapping
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
            self.redis_client = None
        logger.info("✅ EventBus disconnected from Redis")
    
    async def publish(self, event_data: Dict[str, Any]):
        """
        Publish an event to the event bus
        
        Args:
            event_data: Event payload with 'type' and 'data' fields
        """
        if not self.redis_client:
            await self.connect()
        
        event_type = event_data.get("type", "unknown")
        channel = "workspace_intelligence_events"
        
        try:
            # Add metadata
            event_data["timestamp"] = datetime.now().isoformat()
            event_data["source"] = "workspace-intelligence-service"
            
            # Publish to Redis channel
            message = json.dumps(event_data)
            await self.redis_client.publish(channel, message)
            
            logger.info(f"📤 Published event: {event_type} to {channel}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to publish event {event_type}: {e}")
            return False
    
    async def subscribe(self, channel: str, handler: Callable):
        """Subscribe to events from a specific channel"""
        if not self.pubsub:
            await self.connect()
        
        await self.pubsub.subscribe(channel)
        logger.info(f"📥 Subscribed to channel: {channel}")
    
    def register_handler(self, event_type: str, handler: Callable):
        """Register a handler function for a specific event type"""
        self.subscribers[event_type] = handler
        logger.info(f"✅ Registered handler for: {event_type}")
    
    async def start_listening(self):
        """Start listening for events on subscribed channels"""
        if not self.pubsub:
            await self.connect()
        
        logger.info("🎧 EventBus started listening for events...")
        
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        event_type = event_data.get("type")
                        
                        if event_type in self.subscribers:
                            handler = self.subscribers[event_type]
                            await handler(event_data)
                            logger.info(f"✅ Handled event: {event_type}")
                        else:
                            logger.debug(f"No handler for event: {event_type}")
                            
                    except Exception as e:
                        logger.error(f"❌ Error handling event: {e}", exc_info=True)
        except asyncio.CancelledError:
            logger.info("🛑 EventBus listener cancelled")
        except Exception as e:
            logger.error(f"❌ EventBus listener error: {e}", exc_info=True)
    
    # ============================================================================
    # REPOSITORY TREE EVENT PUBLISHERS
    # ============================================================================
    
    async def publish_repository_tree_created(
        self,
        tree_id: str,
        organization_name: str,
        user_id: str,
        tree_data: list
    ):
        """Publish repository tree created event"""
        return await self.publish({
            "type": "repository_tree.created",
            "data": {
                "tree_id": tree_id,
                "organization_name": organization_name,
                "user_id": user_id,
                "folder_count": len(tree_data),
                "repository_count": sum(len(folder.get("repositories", [])) for folder in tree_data)
            }
        })
    
    async def publish_repository_tree_updated(
        self,
        tree_id: str,
        organization_name: str,
        user_id: str,
        version: int,
        tree_data: list
    ):
        """Publish repository tree updated event"""
        return await self.publish({
            "type": "repository_tree.updated",
            "data": {
                "tree_id": tree_id,
                "organization_name": organization_name,
                "user_id": user_id,
                "version": version,
                "folder_count": len(tree_data),
                "repository_count": sum(len(folder.get("repositories", [])) for folder in tree_data)
            }
        })
    
    async def publish_repository_tree_deleted(
        self,
        tree_id: str,
        organization_name: str,
        user_id: str
    ):
        """Publish repository tree deleted event"""
        return await self.publish({
            "type": "repository_tree.deleted",
            "data": {
                "tree_id": tree_id,
                "organization_name": organization_name,
                "user_id": user_id
            }
        })
    
    # ============================================================================
    # WORKSPACE ANALYSIS EVENT PUBLISHERS
    # ============================================================================
    
    async def publish_workspace_analysis_started(
        self,
        analysis_id: Optional[str],
        organization_name: str,
        user_id: str,
        tree_id: str
    ):
        """Publish workspace analysis started event"""
        return await self.publish({
            "type": "workspace_analysis.started",
            "data": {
                "analysis_id": analysis_id,
                "organization_name": organization_name,
                "user_id": user_id,
                "tree_id": tree_id
            }
        })
    
    async def publish_workspace_analysis_completed(
        self,
        analysis_id: str,
        organization_name: str,
        user_id: str,
        tree_id: str,
        duration_seconds: float,
        maturity_score: float,
        total_repositories: int,
        total_workflows: int,
        findings_count: Dict[str, int],
        project_name: Optional[str] = None,
        folder_path: Optional[str] = None,
        analysis_scope: str = "unified"
    ):
        """Publish workspace analysis completed event"""
        return await self.publish({
            "type": "workspace_analysis.completed",
            "data": {
                "analysis_id": analysis_id,
                "organization_name": organization_name,
                "user_id": user_id,
                "tree_id": tree_id,
                "duration_seconds": duration_seconds,
                "maturity_score": maturity_score,
                "total_repositories": total_repositories,
                "total_workflows": total_workflows,
                "findings_count": findings_count,
                "project_name": project_name,
                "folder_path": folder_path,
                "analysis_scope": analysis_scope
            }
        })
    
    async def publish_workspace_analysis_failed(
        self,
        organization_name: str,
        user_id: str,
        tree_id: str,
        error_message: str
    ):
        """Publish workspace analysis failed event"""
        return await self.publish({
            "type": "workspace_analysis.failed",
            "data": {
                "organization_name": organization_name,
                "user_id": user_id,
                "tree_id": tree_id,
                "error_message": error_message
            }
        })
    
    async def publish_project_analysis_completed(
        self,
        analysis_id: str,
        project_id: str,
        project_name: str,
        organization_name: str,
        maturity_scores: Dict[str, float],
        user_id: Optional[str] = None
    ):
        """Publish individual project analysis completed event"""
        return await self.publish({
            "type": "project_analysis.completed",
            "data": {
                "analysis_id": analysis_id,
                "project_id": project_id,
                "project_name": project_name,
                "organization_name": organization_name,
                "maturity_scores": maturity_scores,
                "user_id": user_id
            }
        })


# Global instance
event_bus = EventBus()
