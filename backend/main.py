# backend/main.py

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.websockets import WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from api.routes import ai  # AI proxy routes - others moved to microservices
import os
import asyncio
import json
import time
from typing import Dict, Set
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from core.logging_config import setup_logging
from core.rate_limiter import rate_limit_middleware

# Monitoring and observability imports
from prometheus_client import Counter, Histogram, make_asgi_app
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

load_dotenv()

# Setup distributed tracing with service name
resource = Resource.create(attributes={
    "service.name": "withops-events-hub",
    "service.version": "2.0.0",
    "deployment.environment": "development",
    "service.role": "websocket-events-realtime"
})

trace.set_tracer_provider(TracerProvider(resource=resource))

# Use OTLP HTTP exporter (more reliable than Jaeger Thrift)
otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTLP_ENDPOINT", "http://jaeger:4318/v1/traces"),
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(otlp_exporter)
)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Don't setup logging at import time to avoid multiprocessing issues
# Logging will be configured in the lifespan function instead

# WebSocket manager - use the properly instrumented one from core
from core.websocket_manager import websocket_manager as manager

# Event listener task
event_listener_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting WithOps Events Hub - WebSocket & Real-Time Service")
    
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
    
    # Initialize Event Bus
    from core.event_bus import event_bus
    from core.websocket_manager import websocket_manager
    await event_bus.connect()
    
    # Subscribe to threat analysis completion events
    async def handle_analysis_complete(data: dict):
        """Handle threat analysis completion and notify user via WebSocket"""
        from urllib.parse import unquote
        
        user_id = data.get("user_id")
        task_id = data.get("task_id")
        result = data.get("result")
        
        print(f"📨 Event received with user_id: '{user_id}' (len={len(user_id) if user_id else 0}, repr={repr(user_id)})")
        
        # URL decode user_id (it comes encoded from the async endpoint)
        decoded_user_id = unquote(user_id) if user_id else None
        
        print(f"🔓 After decode: '{decoded_user_id}' (len={len(decoded_user_id) if decoded_user_id else 0}, repr={repr(decoded_user_id)})")
        print(f"✅ Threat analysis complete for task {task_id}, notifying user {decoded_user_id}")
        
        # Send result to user via WebSocket
        await websocket_manager.send_to_user(decoded_user_id, {
            "event": "threat.analysis.completed",
            "data": result
        })
    
    await event_bus.subscribe("threat.analysis.completed", handle_analysis_complete)
    
    # Subscribe to GitHub refresh events from github-service
    # The github-service publishes to 'github_events' Redis channel directly
    async def listen_github_events():
        """Listen to GitHub events channel and forward to WebSocket"""
        import redis.asyncio as redis
        
        redis_client = redis.from_url(
            "redis://redis:6379",
            encoding="utf-8",
            decode_responses=True
        )
        
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("github_events")
        
        print("🎧 Listening for GitHub events on 'github_events' channel...")
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        raw_data = message["data"]
                        
                        # Handle both string and bytes
                        if isinstance(raw_data, bytes):
                            raw_data = raw_data.decode('utf-8')
                        
                        print(f"🔍 Received message: {raw_data}")
                        
                        # Parse JSON
                        data = json.loads(raw_data)
                        event_type = data.get("type", "unknown")
                        org_name = data.get("org_name")
                        refresh_data = data.get("data", {})
                        
                        print(f"📨 GitHub event: {event_type} for org {org_name}")
                        
                        # Create WebSocket notification
                        notification = {
                            "event": f"github.{event_type}",
                            "org_name": org_name,
                            "data": refresh_data,
                            "timestamp": data.get("timestamp")
                        }
                        
                        # Broadcast to all connected users
                        # Frontend will filter by org_name
                        await websocket_manager.broadcast(notification)
                        print(f"✅ Broadcasted {event_type} for org {org_name}")
                        
                    except Exception as e:
                        print(f"❌ Error processing GitHub event: {e}")
        finally:
            await pubsub.unsubscribe("github_events")
            await pubsub.close()
            await redis_client.close()
    
    # Start GitHub events listener in background
    global github_events_listener_task
    github_events_listener_task = asyncio.create_task(listen_github_events())
    
    # Subscribe to threat modeling events from threat-modeling-service
    async def listen_threat_modeling_events():
        """Listen to threat modeling events and forward to WebSocket"""
        import redis.asyncio as redis
        
        redis_client = redis.from_url(
            "redis://redis:6379",
            encoding="utf-8",
            decode_responses=True
        )
        
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("threat_modeling_events")
        
        print("🎧 Listening for threat modeling events on 'threat_modeling_events' channel...")
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        raw_data = message["data"]
                        
                        # Handle both string and bytes
                        if isinstance(raw_data, bytes):
                            raw_data = raw_data.decode('utf-8')
                        
                        print(f"🔍 Received threat modeling message: {raw_data}")
                        
                        # Parse JSON
                        data = json.loads(raw_data)
                        event_type = data.get("type", "unknown")
                        event_data = data.get("data", {})
                        
                        model_id = event_data.get("model_id")
                        user_id = event_data.get("user_id")
                        organization_id = event_data.get("organization_id")
                        model_name = event_data.get("name")
                        
                        print(f"📨 Threat modeling event: {event_type} - model={model_name} (id={model_id})")
                        
                        # Create WebSocket notification
                        notification = {
                            "event": event_type,
                            "data": {
                                "model_id": model_id,
                                "organization_id": organization_id,
                                "name": model_name,
                                "timestamp": data.get("timestamp")
                            }
                        }
                        
                        # Send to specific user (threat models are user-specific)
                        if user_id:
                            await websocket_manager.send_to_user(user_id, notification)
                            print(f"✅ Notified user {user_id} about {event_type}")
                        
                    except Exception as e:
                        print(f"❌ Error processing threat modeling event: {e}")
                        import traceback
                        traceback.print_exc()
        finally:
            await pubsub.unsubscribe("threat_modeling_events")
            await pubsub.close()
            await redis_client.close()
    
    # Start threat modeling events listener in background
    global threat_modeling_listener_task
    threat_modeling_listener_task = asyncio.create_task(listen_threat_modeling_events())
    
    # Start event listener in background
    global event_listener_task
    event_listener_task = asyncio.create_task(event_bus.start_listening())
    print("✅ Event bus initialized and listening")
    
    # Initialize GitHub Service Client
    from core.github_service_client import github_service_client
    print("✅ GitHub Service Client initialized")
    
    yield
    
    # Shutdown
    print("👋 Shutting down WithOps Events Hub")
    
    # Close GitHub Service Client
    from core.github_service_client import github_service_client
    await github_service_client.close()
    print("✅ GitHub Service Client closed")
    
    # Stop event listener
    if event_listener_task:
        await event_bus.stop_listening()
        event_listener_task.cancel()
        try:
            await event_listener_task
        except asyncio.CancelledError:
            pass
    
    # Stop GitHub events listener
    if github_events_listener_task:
        github_events_listener_task.cancel()
        try:
            await github_events_listener_task
        except asyncio.CancelledError:
            pass
    
    # Stop threat modeling events listener
    if threat_modeling_listener_task:
        threat_modeling_listener_task.cancel()
        try:
            await threat_modeling_listener_task
        except asyncio.CancelledError:
            pass
    
    # Disconnect services
    await event_bus.disconnect()
    await cache.disconnect()

app = FastAPI(
    title="WithOps Events Hub", 
    description="Real-time WebSocket and Event Bus service for WithOps platform - handles WebSocket connections, event subscriptions, and real-time notifications",
    version="2.0.0",
    lifespan=lifespan
)

# Instrument FastAPI with OpenTelemetry for distributed tracing
FastAPIInstrumentor.instrument_app(app)

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# 🚀 MONITORING: Add metrics collection middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Collect metrics for each request"""
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Record metrics
    duration = time.time() - start_time
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response

# 🚀 PERFORMANCE: Add timeout middleware for long-running operations
@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    """Add request timeout for long-running operations"""
    # Skip timeout for metrics endpoint
    if request.url.path == "/metrics":
        return await call_next(request)
    
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
            # AI operations can be slow - especially PR generation (30-60s)
            return await asyncio.wait_for(call_next(request), timeout=120.0)
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

# Add compression middleware for faster responses (skip for /metrics endpoint for Prometheus)
# GZip compression causes issues with Prometheus scraping
# app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.middleware("http")
async def conditional_gzip_middleware(request: Request, call_next):
    """Apply GZip compression except for metrics endpoint (Prometheus compatibility)"""
    response = await call_next(request)
    
    # Skip compression for Prometheus metrics endpoint
    if request.url.path in ["/metrics", "/metrics/"]:
        return response
    
    # Apply compression for other endpoints if response is large enough
    if hasattr(response, "body") and len(response.body) > 1000:
        from fastapi.responses import Response
        import gzip
        compressed_body = gzip.compress(response.body)
        return Response(
            content=compressed_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )
    
    return response

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

# Auth routes now handled by auth-service (via Kong)
# app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
# print("✅ Auth router included")

# GitHub routes now handled by github-service (via Kong)  
# app.include_router(github.router, prefix="/api/github", tags=["github"])
# print("✅ GitHub router included")

app.include_router(ai.router, tags=["ai"])  # AI router already has /api/ai prefix internally
print("✅ AI router included")

# Project tree routes now handled by workflow-orchestration-service (via Kong)
# app.include_router(project_tree.router, prefix="/api/github", tags=["project-tree"])
# print("✅ Project Tree router included")

# Threat modeling routes now handled by threat-modeling-service (via Kong)
# app.include_router(threat_modeling.router, prefix="/api/threat-modeling", tags=["threat-modeling"])
# print("✅ Threat modeling router included")

# Collaboration routes now handled by collaboration-service (via Kong)
# app.include_router(collaboration.router, tags=["collaboration"])
# print("✅ Collaboration router included")

# Repository tree & workspace intelligence now handled by workspace-intelligence-service (via Kong)
# app.include_router(repository_tree.router, tags=["repository-tree"])
# print("✅ Repository Tree router included")
# app.include_router(workspace_intelligence.router, prefix="/api", tags=["workspace-intelligence"])
# print("✅ Workspace Intelligence router included")

print("🔍 DEBUG: All routers included successfully (microservices active)")

@app.get("/")
async def root():
    return {
        "message": "WithOps Events Hub - Real-Time WebSocket & Event Bus Service", 
        "version": "1.0.0",
        "note": "Most API routes now handled by microservices via Kong Gateway"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "withops-events-hub",
        "role": "websocket-events-realtime",
        "version": "2.0.0"
    }

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    # URL decode user_id (handles special characters like | in Auth0 IDs)
    from urllib.parse import unquote
    decoded_user_id = unquote(user_id)
    
    await manager.connect(websocket, decoded_user_id)
    try:
        while True:
            # Receive and ignore ping messages (keeps connection alive)
            data = await websocket.receive_text()
            # Optionally handle specific message types
            try:
                message = json.loads(data)
                if message.get('type') == 'ping':
                    # Send pong response
                    await websocket.send_text(json.dumps({'type': 'pong'}))
            except:
                pass  # Ignore malformed messages
    except WebSocketDisconnect:
        manager.disconnect(websocket, decoded_user_id)

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
