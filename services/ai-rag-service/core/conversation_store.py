"""
Conversation Storage - Redis-based conversation management
"""

import redis.asyncio as redis
import json
import logging
from typing import List, Dict, Optional
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class ConversationStore:
    """
    Manages conversation storage in Redis with user isolation
    """
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        self.redis_client = None
        self.conversation_ttl = 86400  # 24 hours
        self.max_turns = 20  # Maximum messages per conversation
        
    async def connect(self):
        """Connect to Redis"""
        if not self.redis_client:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info(f"✅ ConversationStore connected to Redis: {self.redis_url}")
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            logger.info("ConversationStore disconnected from Redis")
    
    def _get_conversation_key(self, user_id: str, conversation_id: str) -> str:
        """Generate Redis key for conversation"""
        return f"conversation:{user_id}:{conversation_id}"
    
    async def add_message(
        self,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """
        Add a message to conversation
        
        Args:
            user_id: Auth0 user ID
            conversation_id: Unique conversation identifier
            role: 'user' or 'assistant'
            content: Message content
            metadata: Optional metadata (sources, confidence, etc.)
        """
        try:
            key = self._get_conversation_key(user_id, conversation_id)
            
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            
            # Store as JSON string
            await self.redis_client.rpush(key, json.dumps(message))
            
            # Set expiration
            await self.redis_client.expire(key, self.conversation_ttl)
            
            # Trim to max turns (each turn = 2 messages)
            await self.redis_client.ltrim(key, -self.max_turns, -1)
            
            logger.debug(f"Added {role} message to conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error adding message: {str(e)}")
    
    async def get_conversation(
        self,
        user_id: str,
        conversation_id: str
    ) -> List[Dict[str, str]]:
        """
        Get conversation history
        
        Args:
            user_id: Auth0 user ID
            conversation_id: Unique conversation identifier
            
        Returns:
            List of messages with role and content
        """
        try:
            key = self._get_conversation_key(user_id, conversation_id)
            messages_json = await self.redis_client.lrange(key, 0, -1)
            
            messages = []
            for msg_json in messages_json:
                msg = json.loads(msg_json)
                # Return only role and content for RAG context
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting conversation: {str(e)}")
            return []
    
    async def get_full_conversation(
        self,
        user_id: str,
        conversation_id: str
    ) -> List[Dict]:
        """
        Get full conversation with metadata
        
        Args:
            user_id: Auth0 user ID
            conversation_id: Unique conversation identifier
            
        Returns:
            List of full message objects with timestamps and metadata
        """
        try:
            key = self._get_conversation_key(user_id, conversation_id)
            messages_json = await self.redis_client.lrange(key, 0, -1)
            
            return [json.loads(msg) for msg in messages_json]
            
        except Exception as e:
            logger.error(f"Error getting full conversation: {str(e)}")
            return []
    
    async def clear_conversation(
        self,
        user_id: str,
        conversation_id: str
    ):
        """
        Delete a conversation
        
        Args:
            user_id: Auth0 user ID
            conversation_id: Unique conversation identifier
        """
        try:
            key = self._get_conversation_key(user_id, conversation_id)
            await self.redis_client.delete(key)
            logger.info(f"Cleared conversation {conversation_id} for user {user_id}")
        except Exception as e:
            logger.error(f"Error clearing conversation: {str(e)}")
    
    async def list_user_conversations(self, user_id: str) -> List[str]:
        """
        List all conversation IDs for a user
        
        Args:
            user_id: Auth0 user ID
            
        Returns:
            List of conversation IDs
        """
        try:
            pattern = f"conversation:{user_id}:*"
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                # Extract conversation_id from key
                conv_id = key.split(":")[-1]
                keys.append(conv_id)
            return keys
        except Exception as e:
            logger.error(f"Error listing conversations: {str(e)}")
            return []


# Global instance
conversation_store = ConversationStore()
