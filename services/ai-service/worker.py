"""
Background worker for processing threat analysis tasks asynchronously
"""
import asyncio
import logging
from event_bus import event_bus, task_queue
from core.claude_ai_client import ClaudeAIClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ThreatAnalysisWorker:
    """Worker that processes threat analysis tasks from the queue"""
    
    def __init__(self):
        self.claude_client = ClaudeAIClient()
        self.running = False
    
    async def process_task(self, task: dict):
        """
        Process a single threat analysis task
        
        Args:
            task: Task data containing analysis request
        """
        task_id = task["task_id"]
        task_data = task["data"]
        
        logger.info(f"🤖 Processing threat analysis task: {task_id}")
        
        try:
            # Update status to processing
            await task_queue.update_task_status(task_id, "processing")
            
            # Prepare request for Claude client (expects a single dict parameter)
            claude_request = {
                "model_id": task_data.get("model_id"),
                "model_name": task_data.get("model_name"),
                "components": task_data.get("components", []),
                "connections": task_data.get("connections", []),
                "document_content": task_data.get("document_content"),
                "diagram_base64": task_data.get("diagram_base64"),
                "analysis_type": task_data.get("analysis_type", "comprehensive"),
                "methodology": task_data.get("methodology", "STRIDE"),
                "user_threat_context": task_data.get("user_threat_context")
            }
            
            # Perform the actual threat analysis
            result = await self.claude_client.analyze_threats(claude_request)
            
            # Update status to completed with result
            await task_queue.update_task_status(task_id, "completed", result)
            
            # Publish completion event
            await event_bus.publish("threat.analysis.completed", {
                "task_id": task_id,
                "user_id": task_data.get("user_id"),
                "model_id": task_data.get("model_id"),
                "result": result
            })
            
            logger.info(f"✅ Completed threat analysis task: {task_id}")
            
        except Exception as e:
            logger.error(f"❌ Error processing task {task_id}: {e}", exc_info=True)
            
            # Update status to failed
            await task_queue.update_task_status(task_id, "failed")
            
            # Publish failure event
            await event_bus.publish("threat.analysis.failed", {
                "task_id": task_id,
                "user_id": task_data.get("user_id"),
                "error": str(e)
            })
    
    async def run(self):
        """Main worker loop - continuously process tasks from queue"""
        logger.info("🚀 Starting Threat Analysis Worker")
        
        # Connect to services
        await event_bus.connect()
        await task_queue.connect()
        
        self.running = True
        
        try:
            while self.running:
                # Get task from queue (blocks for 5 seconds)
                task = await task_queue.dequeue(timeout=5)
                
                if task:
                    # Process the task
                    await self.process_task(task)
                else:
                    # No task available, wait a bit
                    await asyncio.sleep(1)
        
        except asyncio.CancelledError:
            logger.info("🛑 Worker cancelled")
        except Exception as e:
            logger.error(f"❌ Worker error: {e}", exc_info=True)
        finally:
            self.running = False
            await event_bus.disconnect()
            await task_queue.disconnect()
            logger.info("👋 Worker shutdown complete")
    
    async def stop(self):
        """Stop the worker"""
        logger.info("🛑 Stopping worker...")
        self.running = False


async def main():
    """Main entry point"""
    worker = ThreatAnalysisWorker()
    
    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("⌨️  Keyboard interrupt received")
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
