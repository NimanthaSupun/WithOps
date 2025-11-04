# backend/main.py

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.websockets import WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from api.routes import auth, github, ai, threat_modeling, ai_threats, collaboration, repository_tree, workspace_intelligence  # Auth, GitHub, AI, Threat Modeling, AI Threats, Collaboration, Repository Tree, and Workspace Intelligence routes
import os
import asyncio
import json
import time
from typing import Dict, Set
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from core.logging_config import setup_logging
from core.rate_limiter import rate_limit_middleware

load_dotenv()

# Don't setup logging at import time to avoid multiprocessing issues
# Logging will be configured in the lifespan function instead

# Global WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        print(f"🔌 WebSocket connected for user: {user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        print(f"🔌 WebSocket disconnected for user: {user_id}")
    
    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    disconnected.add(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.active_connections[user_id].discard(conn)

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting DevSecOps Backend with Real-Time Features")
    
    # Setup logging after FastAPI startup to avoid multiprocessing issues
    try:
        loggers = setup_logging()
        print("✅ Logging configured successfully")
    except Exception as e:
        print(f"⚠️ Logging setup warning: {e}")
        # Continue even if logging setup fails
    
    # Initialize Redis cache
    from core.redis_cache import cache
    await cache.connect()
    yield
    # Shutdown
    print("👋 Shutting down DevSecOps Backend")
    # Disconnect Redis
    await cache.disconnect()

app = FastAPI(
    title="WithOps DevSecOps API", 
    description="Simple Auth0 authenticated API with performance optimizations and real-time features",
    version="2.0.0",
    lifespan=lifespan
)

# 🚀 PERFORMANCE: Add timeout middleware for long-running operations
@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    """Add request timeout for long-running operations"""
    try:
        # Optimized timeouts based on operation complexity
        if request.url.path.startswith("/api/github"):
            # GitHub operations can be very slow due to API calls
            return await asyncio.wait_for(call_next(request), timeout=60.0)
        elif request.url.path.startswith("/api/auth/dashboard"):
            # Dashboard with database queries needs more time due to connection overhead
            return await asyncio.wait_for(call_next(request), timeout=75.0)
        elif request.url.path.startswith("/api/auth"):
            # Other auth operations like token verification
            return await asyncio.wait_for(call_next(request), timeout=20.0)
        elif request.url.path.startswith("/api/threat-modeling"):
            # Threat modeling can involve complex calculations and AI analysis saves
            return await asyncio.wait_for(call_next(request), timeout=90.0)
        elif request.url.path.startswith("/api/workspace-intelligence"):
            # Workspace intelligence analysis can take time for multiple repos
            return await asyncio.wait_for(call_next(request), timeout=120.0)
        elif request.url.path.startswith("/api/ai"):
            # AI operations can be slow
            return await asyncio.wait_for(call_next(request), timeout=30.0)
        else:
            # Default timeout for other operations
            return await asyncio.wait_for(call_next(request), timeout=15.0)
    except asyncio.TimeoutError:
        from fastapi import HTTPException
        # More specific timeout message based on the path
        if request.url.path.startswith("/api/auth/dashboard"):
            raise HTTPException(status_code=504, detail="Dashboard loading timed out - please try again")
        elif request.url.path.startswith("/api/github"):
            raise HTTPException(status_code=504, detail="GitHub operation timed out - please try again")
        else:
            raise HTTPException(status_code=504, detail="Request timeout")

# 🚀 PERFORMANCE: Add rate limiting middleware (temporarily disabled for development)
# app.middleware("http")(rate_limit_middleware)

# Add compression middleware for faster responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Configure CORS
origins = [
    "http://localhost:5173",  # SvelteKit dev server
    "http://localhost:5174",  # SvelteKit dev server (alternative port)
    "http://localhost:5175",  # SvelteKit dev server (alternative port 2)
    "http://localhost:3000",  # Alternative dev server
    "http://localhost:4173",  # SvelteKit preview
    "http://127.0.0.1:5173",  # Alternative localhost format
    "http://127.0.0.1:5174",  # Alternative localhost format
    "http://127.0.0.1:5175",  # Alternative localhost format
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Type"],
    max_age=3600,
)

# Add validation error handler for better 422 error messages
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages"""
    errors = exc.errors()
    error_details = []
    for error in errors:
        loc = " -> ".join(str(x) for x in error["loc"])
        msg = error["msg"]
        error_details.append(f"{loc}: {msg}")
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": error_details,
            "body": exc.body if hasattr(exc, 'body') else None
        }
    )

# Include routers
print("🔍 DEBUG: Including routers...")
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
print("✅ Auth router included")
app.include_router(github.router, prefix="/api/github", tags=["github"])
print("✅ GitHub router included")
app.include_router(ai.router, tags=["ai"])  # AI router already has /api/ai prefix internally
print("✅ AI router included")
app.include_router(ai_threats.router, tags=["ai-threats"])  # Real-time AI threats router
print("✅ AI Threats router included")
app.include_router(threat_modeling.router, prefix="/api/threat-modeling", tags=["threat-modeling"])
print("✅ Threat modeling router included")
app.include_router(collaboration.router, tags=["collaboration"])  # Organization-based collaboration router
print("✅ Collaboration router included")
app.include_router(repository_tree.router, tags=["repository-tree"])  # Repository tree router (separate from workflow treeview)
print("✅ Repository Tree router included")
app.include_router(workspace_intelligence.router, prefix="/api", tags=["workspace-intelligence"])  # Workspace Intelligence router
print("✅ Workspace Intelligence router included")
print("🔍 DEBUG: All routers included successfully")

@app.get("/")
async def root():
    return {"message": "WithOps Auth API is running!", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "withops-auth-backend"}

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

# Helper function to send real-time updates
async def send_realtime_update(user_id: str, update_type: str, data: dict):
    message = {
        "type": update_type,
        "timestamp": time.time(),
        "data": data
    }
    await manager.send_to_user(user_id, message)

if __name__ == "__main__":
    import uvicorn
    print("Starting WithOps Auth API server...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
