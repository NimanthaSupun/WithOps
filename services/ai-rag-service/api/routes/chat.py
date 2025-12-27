"""
Chat Routes - Handles conversational queries with user authentication
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
from uuid import uuid4, UUID

from core.embeddings import EmbeddingService
from core.vector_store import VectorStore
from core.rag_engine import RAGEngine
from core.security import security_service, PermissionService
from core.conversation_store import conversation_store
from database.operations import ConversationOperations, MessageOperations
from database.models import ConversationCreate, MessageCreate

logger = logging.getLogger(__name__)

router = APIRouter()

# Global instances (will be initialized in main.py lifespan)
embedding_service: Optional[EmbeddingService] = None
vector_store: Optional[VectorStore] = None
permission_service: Optional[PermissionService] = None


class ChatRequest(BaseModel):
    """Request model for chat queries"""
    question: str
    org_name: str  # Required for permission check
    project_name: Optional[str] = None  # For folder-level filtering
    folder_path: Optional[str] = None   # For folder isolation
    analysis_scope: Optional[str] = None  # unified/folder/project
    analysis_id: Optional[str] = None   # Specific analysis version
    conversation_id: Optional[str] = None  # Existing conversation ID (UUID)
    auto_create_conversation: bool = True  # Auto-create if conversation_id not provided
    filters: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Response model for chat queries"""
    answer: str
    sources: List[Dict[str, str]]
    conversation_id: str
    confidence: str
    contexts_used: int
    model: Optional[str] = None
    tokens_used: Optional[int] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Process a chat query using RAG with user authentication
    
    Flow:
    1. Verify JWT token and extract user_id
    2. Check organization access permission
    3. Build context-aware filters
    4. Generate embedding for question
    5. Search vector database with user+org+project filters
    6. Retrieve conversation history from Redis
    7. Call Claude API for answer generation
    8. Store conversation turn in Redis
    9. Return answer with sources
    """
    try:
        # 1. Verify authentication
        if not authorization:
            raise HTTPException(
                status_code=401,
                detail="Authorization header required"
            )
        
        token = authorization.replace("Bearer ", "")
        try:
            user_info = security_service.verify_token(token)
            user_id = user_info["user_id"]
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))
        
        logger.info(f"Chat query from user {user_id}: {request.question[:50]}...")
        
        # 2. Check organization access
        if not permission_service:
            raise HTTPException(status_code=503, detail="Permission service not initialized")
        
        has_access = await permission_service.check_org_access(user_id, request.org_name)
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail=f"No access to organization: {request.org_name}"
            )
        
        # 3. Validate services are available
        if not embedding_service or not vector_store:
            raise HTTPException(
                status_code=503,
                detail="Services not initialized"
            )
        
        # 4. Build context-aware filters
        filters = request.filters or {}
        
        # CRITICAL: Always filter by user_id and org_name
        filters["user_id"] = user_id
        filters["org_name"] = request.org_name
        
        # Add project-level filtering ONLY for folder-scoped analyses
        # For unified analyses, we want to search across ALL projects
        if request.analysis_scope != "unified":
            if request.project_name:
                filters["project_name"] = request.project_name
            
            if request.folder_path:
                filters["folder_path"] = request.folder_path
        
        # Filter by specific analysis if provided
        if request.analysis_id:
            filters["analysis_id"] = request.analysis_id
        
        logger.info(f"Query filters: {filters}")
        
        # 5. Initialize RAG engine
        rag_engine = RAGEngine(embedding_service, vector_store)
        
        # 6. Handle conversation management
        conversation_id = None
        conversation_uuid = None
        
        # If conversation_id provided, validate it exists
        if request.conversation_id:
            try:
                conversation_uuid = UUID(request.conversation_id)
                # Verify conversation exists and belongs to user
                existing_conv = await ConversationOperations.get_conversation(
                    conversation_uuid, user_id
                )
                if not existing_conv:
                    raise HTTPException(
                        status_code=404,
                        detail="Conversation not found or access denied"
                    )
                conversation_id = request.conversation_id
                logger.info(f"Using existing conversation: {conversation_id}")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid conversation_id format")
        
        # Auto-create conversation if needed
        elif request.auto_create_conversation and request.analysis_id:
            try:
                analysis_uuid = UUID(request.analysis_id)
                # Generate conversation title from first question
                title = request.question[:50] + ("..." if len(request.question) > 50 else "")
                
                conv_create = ConversationCreate(
                    user_id=user_id,
                    organization_name=request.org_name,
                    analysis_id=analysis_uuid,
                    analysis_scope=request.analysis_scope or "unified",
                    project_name=request.project_name,
                    folder_path=request.folder_path,
                    title=title
                )
                
                new_conv = await ConversationOperations.create_conversation(conv_create)
                conversation_id = str(new_conv.id)
                conversation_uuid = new_conv.id
                logger.info(f"✅ Auto-created conversation: {conversation_id}")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid analysis_id format")
            except Exception as e:
                logger.warning(f"Failed to auto-create conversation: {str(e)}")
                # Fall back to temporary conversation ID
                conversation_id = str(uuid4())
        else:
            # Temporary conversation (Redis only, not persisted)
            conversation_id = str(uuid4())
            logger.info(f"Using temporary conversation: {conversation_id}")
        
        # 7. Get conversation history from Redis (for context)
        conversation_history = await conversation_store.get_conversation(
            user_id, conversation_id
        )
        
        # 8. Process query with RAG
        result = await rag_engine.query(
            question=request.question,
            org_name=request.org_name,
            filters=filters,
            conversation_history=conversation_history if conversation_history else None
        )
        
        # 9. Store messages in both Redis (cache) and Database (permanent)
        
        # Store in Redis for quick access
        await conversation_store.add_message(
            user_id=user_id,
            conversation_id=conversation_id,
            role="user",
            content=request.question
        )
        
        await conversation_store.add_message(
            user_id=user_id,
            conversation_id=conversation_id,
            role="assistant",
            content=result["answer"],
            metadata={
                "sources": result.get("sources", []),
                "confidence": result.get("confidence"),
                "contexts_used": result.get("contexts_used"),
                "model": result.get("model")
            }
        )
        
        # Store in Database if we have a valid conversation UUID
        if conversation_uuid:
            try:
                # Store user message
                await MessageOperations.create_message(MessageCreate(
                    conversation_id=conversation_uuid,
                    role="user",
                    content=request.question,
                    metadata={"filters": filters}
                ))
                
                # Store assistant message
                await MessageOperations.create_message(MessageCreate(
                    conversation_id=conversation_uuid,
                    role="assistant",
                    content=result["answer"],
                    sources=result.get("sources", []),
                    metadata={
                        "confidence": result.get("confidence"),
                        "contexts_used": result.get("contexts_used"),
                        "model": result.get("model"),
                        "tokens_used": result.get("tokens_used")
                    }
                ))
                logger.info(f"💾 Persisted messages to database for conversation {conversation_id}")
            except Exception as e:
                logger.warning(f"Failed to persist messages to database: {str(e)}")
                # Don't fail the request if database storage fails
        
        logger.info(f"✅ Chat response generated for user {user_id}, conversation {conversation_id}")
        
        return ChatResponse(
            answer=result["answer"],
            sources=result["sources"],
            conversation_id=conversation_id,
            confidence=result["confidence"],
            contexts_used=result["contexts_used"],
            model=result.get("model"),
            tokens_used=result.get("tokens_used")
        )
        
    except Exception as e:
        logger.error(f"❌ Error processing chat query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat/{conversation_id}")
async def clear_conversation(
    conversation_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    Clear a specific conversation history
    """
    # Verify authentication
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required")
    
    token = authorization.replace("Bearer ", "")
    try:
        user_info = security_service.verify_token(token)
        user_id = user_info["user_id"]
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    
    # Clear conversation from Redis
    await conversation_store.clear_conversation(user_id, conversation_id)
    
    return {"message": "Conversation cleared", "conversation_id": conversation_id}


@router.get("/chat/conversations")
async def list_conversations(
    authorization: Optional[str] = Header(None)
):
    """
    List all active conversation IDs for authenticated user
    """
    # Verify authentication
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required")
    
    token = authorization.replace("Bearer ", "")
    try:
        user_info = security_service.verify_token(token)
        user_id = user_info["user_id"]
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    
    # Get user's conversations from Redis
    conversation_ids = await conversation_store.list_user_conversations(user_id)
    
    return {
        "conversations": conversation_ids,
        "total": len(conversation_ids)
    }


@router.get("/chat/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    Get conversation history for authenticated user
    """
    # Verify authentication
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required")
    
    token = authorization.replace("Bearer ", "")
    try:
        user_info = security_service.verify_token(token)
        user_id = user_info["user_id"]
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    
    # Get conversation from Redis
    messages = await conversation_store.get_full_conversation(user_id, conversation_id)
    
    if not messages:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation {conversation_id} not found"
        )
    
    return {
        "conversation_id": conversation_id,
        "messages": messages,
        "message_count": len(messages)
    }
