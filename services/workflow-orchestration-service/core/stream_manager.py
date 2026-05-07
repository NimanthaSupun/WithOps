"""
Stream Manager - Real-time execution monitoring via SSE and WebSocket
Provides live updates for workflow executions
"""

import asyncio
import json
import logging
from typing import Dict, Set, AsyncGenerator, Any
from datetime import datetime
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class StreamManager:
    """Manage SSE and WebSocket connections for real-time updates"""
    
    def __init__(self):
        """Initialize stream manager"""
        # Active WebSocket connections: {execution_id: Set[WebSocket]}
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        
        # SSE subscribers: {execution_id: Set[asyncio.Queue]}
        self.sse_subscribers: Dict[str, Set[asyncio.Queue]] = {}
        
        # Heartbeat task
        self.heartbeat_task: asyncio.Task = None
    
    async def connect_websocket(self, websocket: WebSocket, execution_id: str):
        """
        Connect a WebSocket client for execution updates
        
        Args:
            websocket: FastAPI WebSocket instance
            execution_id: Execution ID to subscribe to
        """
        await websocket.accept()
        
        if execution_id not in self.active_connections:
            self.active_connections[execution_id] = set()
        
        self.active_connections[execution_id].add(websocket)
        logger.info(f"WebSocket connected for execution {execution_id}. Total: {len(self.active_connections[execution_id])}")
        
        # Send initial connection confirmation
        await self._send_websocket_message(websocket, {
            'type': 'connected',
            'execution_id': execution_id,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def disconnect_websocket(self, websocket: WebSocket, execution_id: str):
        """
        Disconnect a WebSocket client
        
        Args:
            websocket: FastAPI WebSocket instance
            execution_id: Execution ID client was subscribed to
        """
        if execution_id in self.active_connections:
            self.active_connections[execution_id].discard(websocket)
            
            # Clean up empty sets
            if not self.active_connections[execution_id]:
                del self.active_connections[execution_id]
            
            logger.info(f"WebSocket disconnected for execution {execution_id}")
    
    async def broadcast_execution_update(self, execution_id: str, update_data: Dict[str, Any]):
        """
        Broadcast execution update to all connected clients (WebSocket + SSE)
        
        Args:
            execution_id: Execution ID
            update_data: Update data to broadcast
        """
        message = {
            'type': 'execution_update',
            'execution_id': execution_id,
            'timestamp': datetime.utcnow().isoformat(),
            'data': update_data
        }
        
        # Broadcast to WebSocket clients
        await self._broadcast_websocket(execution_id, message)
        
        # Broadcast to SSE subscribers
        await self._broadcast_sse(execution_id, message)
    
    async def broadcast_step_update(self, execution_id: str, step_data: Dict[str, Any]):
        """
        Broadcast individual step update
        
        Args:
            execution_id: Execution ID
            step_data: Step update data
        """
        message = {
            'type': 'step_update',
            'execution_id': execution_id,
            'timestamp': datetime.utcnow().isoformat(),
            'data': step_data
        }
        
        await self._broadcast_websocket(execution_id, message)
        await self._broadcast_sse(execution_id, message)
    
    async def broadcast_log_line(self, execution_id: str, log_line: str, job_id: str = None, step_number: int = None):
        """
        Broadcast log line in real-time
        
        Args:
            execution_id: Execution ID
            log_line: Log line content
            job_id: Optional job ID
            step_number: Optional step number
        """
        message = {
            'type': 'log',
            'execution_id': execution_id,
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'line': log_line,
                'job_id': job_id,
                'step_number': step_number
            }
        }
        
        await self._broadcast_websocket(execution_id, message)
        await self._broadcast_sse(execution_id, message)
    
    async def broadcast_error(self, execution_id: str, error_message: str, error_type: str = 'error'):
        """
        Broadcast error message
        
        Args:
            execution_id: Execution ID
            error_message: Error message
            error_type: Type of error (error, warning, etc.)
        """
        message = {
            'type': 'error',
            'execution_id': execution_id,
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'message': error_message,
                'error_type': error_type
            }
        }
        
        await self._broadcast_websocket(execution_id, message)
        await self._broadcast_sse(execution_id, message)
    
    async def _broadcast_websocket(self, execution_id: str, message: Dict[str, Any]):
        """Broadcast message to all WebSocket clients for execution"""
        if execution_id not in self.active_connections:
            return
        
        # Create copy to avoid modification during iteration
        connections = list(self.active_connections[execution_id])
        
        for websocket in connections:
            try:
                await self._send_websocket_message(websocket, message)
            except Exception as e:
                logger.error(f"Error sending WebSocket message: {str(e)}")
                # Remove disconnected client
                self.disconnect_websocket(websocket, execution_id)
    
    async def _broadcast_sse(self, execution_id: str, message: Dict[str, Any]):
        """Broadcast message to all SSE subscribers for execution"""
        if execution_id not in self.sse_subscribers:
            return
        
        # Create copy to avoid modification during iteration
        queues = list(self.sse_subscribers[execution_id])
        
        for queue in queues:
            try:
                await queue.put(message)
            except Exception as e:
                logger.error(f"Error sending SSE message: {str(e)}")
                # Remove disconnected subscriber
                self.sse_subscribers[execution_id].discard(queue)
    
    async def _send_websocket_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to WebSocket client"""
        await websocket.send_json(message)
    
    async def sse_stream(self, execution_id: str) -> AsyncGenerator:
        """
        SSE stream generator for execution updates
        
        Args:
            execution_id: Execution ID to subscribe to
        
        Yields:
            SSE events
        """
        # Create queue for this subscriber
        queue = asyncio.Queue()
        
        # Register subscriber
        if execution_id not in self.sse_subscribers:
            self.sse_subscribers[execution_id] = set()
        
        self.sse_subscribers[execution_id].add(queue)
        logger.info(f"SSE subscriber added for execution {execution_id}")
        
        try:
            # Send initial connection event
            yield {
                'event': 'connected',
                'data': json.dumps({
                    'execution_id': execution_id,
                    'timestamp': datetime.utcnow().isoformat()
                })
            }
            
            # Stream messages from queue
            while True:
                try:
                    # Wait for message with timeout for heartbeat
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    yield {
                        'event': message['type'],
                        'data': json.dumps(message)
                    }
                
                except asyncio.TimeoutError:
                    # Send heartbeat
                    yield {
                        'event': 'heartbeat',
                        'data': json.dumps({
                            'timestamp': datetime.utcnow().isoformat()
                        })
                    }
        
        finally:
            # Cleanup on disconnect
            if execution_id in self.sse_subscribers:
                self.sse_subscribers[execution_id].discard(queue)
                
                # Clean up empty sets
                if not self.sse_subscribers[execution_id]:
                    del self.sse_subscribers[execution_id]
            
            logger.info(f"SSE subscriber removed for execution {execution_id}")
    
    async def start_heartbeat(self):
        """Start heartbeat task to keep connections alive"""
        if self.heartbeat_task is None:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info("Heartbeat task started")
    
    async def stop_heartbeat(self):
        """Stop heartbeat task"""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
            self.heartbeat_task = None
            logger.info("Heartbeat task stopped")
    
    async def _heartbeat_loop(self):
        """Background task to send periodic heartbeats"""
        try:
            while True:
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                
                # Send heartbeat to all WebSocket connections
                for execution_id, connections in list(self.active_connections.items()):
                    heartbeat_msg = {
                        'type': 'heartbeat',
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    for websocket in list(connections):
                        try:
                            await self._send_websocket_message(websocket, heartbeat_msg)
                        except:
                            # Remove dead connection
                            self.disconnect_websocket(websocket, execution_id)
        
        except asyncio.CancelledError:
            logger.info("Heartbeat loop cancelled")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about active connections"""
        return {
            'websocket_connections': {
                execution_id: len(connections)
                for execution_id, connections in self.active_connections.items()
            },
            'sse_subscribers': {
                execution_id: len(subscribers)
                for execution_id, subscribers in self.sse_subscribers.items()
            },
            'total_websocket': sum(len(c) for c in self.active_connections.values()),
            'total_sse': sum(len(s) for s in self.sse_subscribers.values())
        }
    
    async def cleanup(self):
        """Cleanup all connections and stop heartbeat"""
        await self.stop_heartbeat()
        
        # Close all WebSocket connections
        for execution_id, connections in list(self.active_connections.items()):
            for websocket in list(connections):
                try:
                    await websocket.close()
                except:
                    pass
        
        self.active_connections.clear()
        self.sse_subscribers.clear()
        
        logger.info("StreamManager cleaned up")


# Global stream manager instance
stream_manager = StreamManager()
