"""
AI RAG Service - Main Application
Provides conversational AI capabilities for DevSecOps Intelligence
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
import asyncio
import os

from api.routes import chat, indexing, health
from core.embeddings import EmbeddingService
from core.vector_store import VectorStore
from core.event_bus import event_bus
from core.auto_indexer import AutoIndexer
from core.conversation_store import conversation_store
from core.security import PermissionService
import redis.asyncio as redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for FastAPI application
    Initializes services on startup and cleans up on shutdown
    """
    vector_store_instance = None  # Initialize to avoid UnboundLocalError
    
    try:
        logger.info("🚀 Starting AI RAG Service...")
        
        # Initialize Redis for conversation store and permissions
        logger.info("Initializing Redis connection...")
        redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
        logger.info(f"Connecting to Redis: {redis_url}")
        redis_client = redis.from_url(
            redis_url,
            decode_responses=False  # We'll handle encoding in conversation_store
        )
        await redis_client.ping()
        
        # Initialize conversation store
        await conversation_store.connect()
        
        # Initialize permission service
        permission_service = PermissionService(redis_client)
        
        # Initialize services
        logger.info("Initializing Ollama Embedding Service...")
        embedding_service = EmbeddingService()
        await embedding_service.initialize()
        
        logger.info("Initializing Qdrant Vector Store...")
        vector_store_instance = VectorStore()
        await vector_store_instance.initialize()
        
        # Make services available to routes
        indexing.embedding_service = embedding_service
        indexing.vector_store = vector_store_instance
        chat.embedding_service = embedding_service
        chat.vector_store = vector_store_instance
        chat.permission_service = permission_service
        
        # Initialize Event Bus and Auto-Indexer
        logger.info("Initializing Event Bus...")
        await event_bus.connect()
        
        auto_indexer = AutoIndexer(embedding_service, vector_store_instance)
        
        # Subscribe to workspace intelligence events channel
        # Note: workspace-intelligence-service publishes all events to 'workspace_intelligence_events'
        # We need to filter by event type in the handler
        await event_bus.subscribe(
            "workspace_intelligence_events",
            lambda event: auto_indexer.handle_workspace_event(event)
        )
        
        # Start event listener in background
        event_bus.listener_task = asyncio.create_task(event_bus.start_listening())
        
        logger.info("✅ All services initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Error during startup: {str(e)}")
        raise
    finally:
        # Cleanup on shutdown
        logger.info("🛑 Shutting down AI RAG Service...")
        await conversation_store.disconnect()
        await event_bus.disconnect()
        if vector_store_instance:
            await vector_store_instance.close()
        logger.info("✅ Cleanup complete")


# Create FastAPI application
app = FastAPI(
    title="AI RAG Service",
    description="Conversational AI for DevSecOps Intelligence using RAG",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(chat.router, prefix="/api/rag", tags=["Chat"])
app.include_router(indexing.router, prefix="/api/rag", tags=["Indexing"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI RAG Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "chat": "/api/rag/chat",
            "index": "/api/rag/index"
        }
    }


# Make services accessible to routes
def get_embedding_service():
    """Dependency to get embedding service"""
    if embedding_service is None:
        raise HTTPException(status_code=503, detail="Embedding service not initialized")
    return embedding_service


def get_vector_store():
    """Dependency to get vector store"""
    if vector_store is None:
        raise HTTPException(status_code=503, detail="Vector store not initialized")
    return vector_store
