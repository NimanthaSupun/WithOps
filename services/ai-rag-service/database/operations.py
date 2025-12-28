"""
Database Operations for Chat Conversations
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
import logging
from datetime import datetime
import json

from .config import db_config
from .models import (
    Conversation,
    ConversationCreate,
    ConversationUpdate,
    Message,
    MessageCreate,
    ConversationWithMessages
)

logger = logging.getLogger(__name__)


class ConversationOperations:
    """Database operations for conversations"""
    
    @staticmethod
    async def create_conversation(data: ConversationCreate) -> Conversation:
        """Create a new conversation"""
        conn = await db_config.get_connection()
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO chat_conversations 
                (user_id, organization_name, analysis_id, analysis_scope, project_name, folder_path, title)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING *
                """,
                data.user_id,
                data.organization_name,
                data.analysis_id,
                data.analysis_scope,
                data.project_name,
                data.folder_path,
                data.title
            )
            logger.info(f"✅ Created conversation {row['id']} for user {data.user_id}")
            return Conversation(**dict(row))
        except Exception as e:
            logger.error(f"❌ Error creating conversation: {str(e)}")
            raise
        finally:
            await db_config.release_connection(conn)
    
    @staticmethod
    async def get_conversation(conversation_id: UUID, user_id: str) -> Optional[Conversation]:
        """Get a conversation by ID"""
        conn = await db_config.get_connection()
        try:
            row = await conn.fetchrow(
                """
                SELECT * FROM chat_conversations
                WHERE id = $1 AND user_id = $2 AND is_active = true
                """,
                conversation_id,
                user_id
            )
            if row:
                return Conversation(**dict(row))
            return None
        finally:
            await db_config.release_connection(conn)
    
    @staticmethod
    async def list_conversations(
        user_id: str,
        analysis_id: Optional[UUID] = None,
        organization_name: Optional[str] = None,
        limit: int = 50
    ) -> List[Conversation]:
        """List conversations for a user"""
        conn = await db_config.get_connection()
        try:
            conditions = ["user_id = $1", "is_active = true"]
            params = [user_id]
            param_index = 2
            
            if analysis_id:
                conditions.append(f"analysis_id = ${param_index}")
                params.append(analysis_id)
                param_index += 1
            
            if organization_name:
                conditions.append(f"organization_name = ${param_index}")
                params.append(organization_name)
                param_index += 1
            
            params.append(limit)
            
            query = f"""
                SELECT * FROM chat_conversations
                WHERE {' AND '.join(conditions)}
                ORDER BY updated_at DESC
                LIMIT ${param_index}
            """
            
            rows = await conn.fetch(query, *params)
            return [Conversation(**dict(row)) for row in rows]
        finally:
            await db_config.release_connection(conn)
    
    @staticmethod
    async def update_conversation(
        conversation_id: UUID,
        user_id: str,
        data: ConversationUpdate
    ) -> Optional[Conversation]:
        """Update a conversation"""
        conn = await db_config.get_connection()
        try:
            updates = []
            params = []
            param_index = 1
            
            if data.title is not None:
                updates.append(f"title = ${param_index}")
                params.append(data.title)
                param_index += 1
            
            if data.is_active is not None:
                updates.append(f"is_active = ${param_index}")
                params.append(data.is_active)
                param_index += 1
            
            if not updates:
                return await ConversationOperations.get_conversation(conversation_id, user_id)
            
            updates.append(f"updated_at = NOW()")
            params.extend([conversation_id, user_id])
            
            query = f"""
                UPDATE chat_conversations
                SET {', '.join(updates)}
                WHERE id = ${param_index} AND user_id = ${param_index + 1}
                RETURNING *
            """
            
            row = await conn.fetchrow(query, *params)
            if row:
                logger.info(f"✅ Updated conversation {conversation_id}")
                return Conversation(**dict(row))
            return None
        finally:
            await db_config.release_connection(conn)
    
    @staticmethod
    async def delete_conversation(conversation_id: UUID, user_id: str) -> bool:
        """Delete a conversation (soft delete)"""
        conn = await db_config.get_connection()
        try:
            result = await conn.execute(
                """
                UPDATE chat_conversations
                SET is_active = false, updated_at = NOW()
                WHERE id = $1 AND user_id = $2
                """,
                conversation_id,
                user_id
            )
            success = result.split()[-1] == "1"
            if success:
                logger.info(f"✅ Deleted conversation {conversation_id}")
            return success
        finally:
            await db_config.release_connection(conn)
    
    @staticmethod
    async def increment_message_count(conversation_id: UUID):
        """Increment message count for a conversation"""
        conn = await db_config.get_connection()
        try:
            await conn.execute(
                """
                UPDATE chat_conversations
                SET message_count = message_count + 1,
                    updated_at = NOW()
                WHERE id = $1
                """,
                conversation_id
            )
        finally:
            await db_config.release_connection(conn)


class MessageOperations:
    """Database operations for messages"""
    
    @staticmethod
    async def create_message(data: MessageCreate) -> Message:
        """Create a new message"""
        conn = await db_config.get_connection()
        try:
            # Convert sources and metadata to JSON strings
            sources_json = json.dumps(data.sources) if data.sources else None
            metadata_json = json.dumps(data.metadata) if data.metadata else None
            
            row = await conn.fetchrow(
                """
                INSERT INTO chat_messages 
                (conversation_id, role, content, sources, metadata)
                VALUES ($1, $2, $3, $4::jsonb, $5::jsonb)
                RETURNING *
                """,
                data.conversation_id,
                data.role,
                data.content,
                sources_json,
                metadata_json
            )
            
            # Increment conversation message count
            await ConversationOperations.increment_message_count(data.conversation_id)
            
            logger.info(f"✅ Created message in conversation {data.conversation_id}")
            return Message(**dict(row))
        except Exception as e:
            logger.error(f"❌ Error creating message: {str(e)}")
            raise
        finally:
            await db_config.release_connection(conn)
    
    @staticmethod
    async def get_messages(
        conversation_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[Message]:
        """Get messages for a conversation"""
        conn = await db_config.get_connection()
        try:
            rows = await conn.fetch(
                """
                SELECT * FROM chat_messages
                WHERE conversation_id = $1
                ORDER BY created_at ASC
                LIMIT $2 OFFSET $3
                """,
                conversation_id,
                limit,
                offset
            )
            # Parse JSON fields back to dicts
            messages = []
            for row in rows:
                row_dict = dict(row)
                # Parse sources and metadata from JSON strings to dicts
                if row_dict.get('sources') and isinstance(row_dict['sources'], str):
                    row_dict['sources'] = json.loads(row_dict['sources'])
                if row_dict.get('metadata') and isinstance(row_dict['metadata'], str):
                    row_dict['metadata'] = json.loads(row_dict['metadata'])
                messages.append(Message(**row_dict))
            return messages
        finally:
            await db_config.release_connection(conn)
    
    @staticmethod
    async def get_conversation_with_messages(
        conversation_id: UUID,
        user_id: str,
        message_limit: int = 100
    ) -> Optional[ConversationWithMessages]:
        """Get a conversation with its messages"""
        conversation = await ConversationOperations.get_conversation(conversation_id, user_id)
        if not conversation:
            return None
        
        messages = await MessageOperations.get_messages(conversation_id, message_limit)
        
        return ConversationWithMessages(
            **conversation.dict(),
            messages=messages
        )


# Export convenience functions
conversation_ops = ConversationOperations()
message_ops = MessageOperations()
