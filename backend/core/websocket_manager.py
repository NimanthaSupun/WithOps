"""
WebSocket manager for real-time communication with frontend
"""
import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        # Map of user_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a new WebSocket for a user"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        logger.info(f"🔌 WebSocket connected for user: {user_id} (total: {len(self.active_connections[user_id])})")
        logger.info(f"🔑 Stored user_id key: '{user_id}' (len={len(user_id)}, repr={repr(user_id)})")
        logger.info(f"📋 All active connection keys: {list(self.active_connections.keys())}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Disconnect a WebSocket"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            
            # Remove user entry if no more connections
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            
            logger.info(f"🔌 WebSocket disconnected for user: {user_id}")
    
    async def send_to_user(self, user_id: str, message: dict):
        """
        Send a message to all connections for a specific user
        
        Args:
            user_id: User identifier
            message: Message payload (will be JSON encoded)
        """
        logger.info(f"🔍 Looking up user_id: '{user_id}' (len={len(user_id)}, repr={repr(user_id)})")
        logger.info(f"📋 Available connection keys: {list(self.active_connections.keys())}")
        
        if user_id not in self.active_connections:
            logger.warning(f"⚠️ No active connections for user: {user_id}")
            logger.warning("🔍 User ID comparison:")
            for key in self.active_connections.keys():
                logger.warning(f"  - Key: '{key}' (len={len(key)}) == '{user_id}' (len={len(user_id)}): {key == user_id}")
            return
        
        logger.info(f"✅ Found {len(self.active_connections[user_id])} connection(s) for user: {user_id}")
        
        # Send to all user's connections
        disconnected = set()
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_json(message)
                logger.info(f"📤 Sent message to user {user_id}: {message.get('event', message.get('type'))}")
            except Exception as e:
                logger.error(f"❌ Error sending to WebSocket: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection, user_id)
    
    async def broadcast(self, message: dict):
        """
        Broadcast a message to all connected users
        
        Args:
            message: Message payload (will be JSON encoded)
        """
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(user_id, message)
    
    def get_user_count(self) -> int:
        """Get count of users with active connections"""
        return len(self.active_connections)
    
    def get_connection_count(self) -> int:
        """Get total count of WebSocket connections"""
        return sum(len(connections) for connections in self.active_connections.values())


# Global instance
websocket_manager = ConnectionManager()
