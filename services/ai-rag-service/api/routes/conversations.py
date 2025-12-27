"""
API Routes for Chat Conversation Management
"""

from fastapi import APIRouter, HTTPException, Query, Header
from typing import List, Optional
from uuid import UUID
import logging

from database.models import (
    Conversation,
    ConversationCreate,
    ConversationUpdate,
    ConversationWithMessages
)
from database.operations import ConversationOperations, MessageOperations
from core.security import verify_token

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/conversations", response_model=Conversation)
async def create_conversation(
    data: ConversationCreate,
    authorization: str = Header(...)
):
    """
    Create a new chat conversation
    
    - Links conversation to an analysis (unified or folder)
    - Each analysis can have multiple conversations
    """
    try:
        # Get user info from token
        user_info = await verify_token(authorization)
        
        # Ensure user_id matches token
        if data.user_id != user_info["user_id"]:
            raise HTTPException(status_code=403, detail="User ID mismatch")
        
        conversation = await ConversationOperations.create_conversation(data)
        logger.info(f"Created conversation {conversation.id} for user {data.user_id}")
        return conversation
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations", response_model=List[Conversation])
async def list_conversations(
    authorization: str = Header(...),
    analysis_id: Optional[UUID] = Query(None, description="Filter by analysis ID"),
    organization_name: Optional[str] = Query(None, description="Filter by organization"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results")
):
    """
    List conversations for the authenticated user
    
    - Can filter by analysis_id to get conversations for specific analysis
    - Can filter by organization_name
    - Returns most recently updated conversations first
    """
    try:
        user_info = await verify_token(authorization)
        user_id = user_info["user_id"]
        conversations = await ConversationOperations.list_conversations(
            user_id=user_id,
            analysis_id=analysis_id,
            organization_name=organization_name,
            limit=limit
        )
        logger.info(f"Listed {len(conversations)} conversations for user {user_id}")
        return conversations
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: UUID,
    authorization: str = Header(...)
):
    """
    Get a specific conversation by ID
    
    - Returns conversation metadata without messages
    - Use GET /conversations/{id}/messages to get messages
    """
    try:
        user_info = await verify_token(authorization)
        user_id = user_info["user_id"]
        conversation = await ConversationOperations.get_conversation(
            conversation_id=conversation_id,
            user_id=user_id
        )
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}/messages", response_model=ConversationWithMessages)
async def get_conversation_with_messages(
    conversation_id: UUID,
    authorization: str = Header(...),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of messages")
):
    """
    Get a conversation with all its messages
    
    - Returns conversation metadata and message history
    - Messages ordered by creation time (oldest first)
    """
    try:
        user_info = await verify_token(authorization)
        user_id = user_info["user_id"]
        conversation = await MessageOperations.get_conversation_with_messages(
            conversation_id=conversation_id,
            user_id=user_id,
            message_limit=limit
        )
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        logger.info(f"Retrieved conversation {conversation_id} with {len(conversation.messages)} messages")
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation with messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/conversations/{conversation_id}", response_model=Conversation)
async def update_conversation(
    conversation_id: UUID,
    data: ConversationUpdate,
    authorization: str = Header(...)
):
    """
    Update a conversation (rename or soft delete)
    
    - Can update title (rename)
    - Can set is_active to false (soft delete)
    """
    try:
        user_info = await verify_token(authorization)
        user_id = user_info["user_id"]
        conversation = await ConversationOperations.update_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            data=data
        )
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        logger.info(f"Updated conversation {conversation_id}")
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    authorization: str = Header(...)
):
    """
    Delete a conversation (soft delete)
    
    - Marks conversation as inactive
    - Messages are preserved but conversation won't appear in list
    """
    try:
        user_info = await verify_token(authorization)
        user_id = user_info["user_id"]
        success = await ConversationOperations.delete_conversation(
            conversation_id=conversation_id,
            user_id=user_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        logger.info(f"Deleted conversation {conversation_id}")
        return {"success": True, "message": "Conversation deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
