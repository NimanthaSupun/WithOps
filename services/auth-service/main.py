"""
Authentication Service - Main Entry Point
Centralized authentication and user management for WithOps platform
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
import time
import logging

# Monitoring imports
from prometheus_client import Counter, Histogram, make_asgi_app
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Import routes
from api.routes import auth

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Setup distributed tracing
resource = Resource.create(attributes={
    "service.name": "withops-auth-service",
    "service.version": "1.0.0",
    "deployment.environment": os.getenv("ENVIRONMENT", "development")
})

trace.set_tracer_provider(TracerProvider(resource=resource))
if os.getenv("ENABLE_TRACING", "false").lower() == "true":
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting Authentication Service...")
    
    listening_task = None
    
    try:
        # Initialize database
        from database.config import db_manager
        await db_manager.create_tables()
        logger.info("✅ Database initialized")
        
        # Initialize event bus
        from core.event_bus import event_bus
        await event_bus.connect()
        logger.info("✅ Event bus connected")
        
        # Register event listeners
        from core.event_listeners import event_listeners
        await event_listeners.register_all_handlers()
        logger.info("✅ Event handlers registered")
        
        # Start listening to events in background
        import asyncio
        listening_task = asyncio.create_task(
            event_bus.start_listening(event_listeners.handle_event)
        )
        logger.info("✅ Event bus listening started")
        
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down Authentication Service...")
    
    try:
        # Cancel listening task
        if listening_task:
            listening_task.cancel()
            try:
                await listening_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect event bus
        from core.event_bus import event_bus
        await event_bus.disconnect()
        logger.info("✅ Event bus disconnected")
        
    except Exception as e:
        logger.error(f"Error disconnecting event bus: {e}")
    
    try:
        # Close database
        from database.config import db_manager
        await db_manager.close()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title="WithOps Authentication Service",
    description="Centralized authentication and user management",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Track request metrics"""
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
    
    # Add timing header
    response.headers["X-Process-Time"] = str(duration)
    
    return response


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "path": request.url.path
        }
    )


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

# Mount Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "WithOps Authentication Service",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "auth-service",
        "version": "1.0.0"
    }


# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("SERVICE_PORT", 8006))
    logger.info(f"Starting Auth Service on port {port}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
