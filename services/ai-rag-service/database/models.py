"""
Database Models for Chat Conversations
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from uuid import UUID


class ConversationCreate(BaseModel):
    """Model for creating a new conversation"""
    user_id: str
    organization_name: str
    analysis_id: UUID
    analysis_scope: str  # 'unified' or 'folder'
    project_name: Optional[str] = None
    folder_path: Optional[str] = None
    title: str = "New Chat"


class ConversationUpdate(BaseModel):
    """Model for updating a conversation"""
    title: Optional[str] = None
    is_active: Optional[bool] = None


class Conversation(BaseModel):
    """Model for a chat conversation"""
    id: UUID
    user_id: str
    organization_name: str
    analysis_id: UUID
    analysis_scope: str
    project_name: Optional[str] = None
    folder_path: Optional[str] = None
    title: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    message_count: int
    
    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    """Model for creating a new message"""
    conversation_id: UUID
    role: str  # 'user' or 'assistant'
    content: str
    sources: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class Message(BaseModel):
    """Model for a chat message"""
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    sources: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationWithMessages(Conversation):
    """Conversation with its messages"""
    messages: List[Message] = []
