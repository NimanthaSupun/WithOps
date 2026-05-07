"""
Workspace Intelligence Service - Main Entry Point
FastAPI application for workspace analysis, DevSecOps maturity scoring, and repository tree management
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
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

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Setup distributed tracing
resource = Resource.create(attributes={
    "service.name": "withops-workspace-intelligence-service",
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
    logger.info("🚀 Starting Workspace Intelligence Service...")
    
    listening_task = None
    
    try:
        # Initialize database
        from database.config import db_manager
        await db_manager.create_tables()
        logger.info("✅ Database initialized")
        
        # Initialize Redis cache
        from core.redis_cache import cache
        await cache.connect()
        logger.info("✅ Redis cache connected")
        
        # Initialize event bus
        from core.event_bus import event_bus
        await event_bus.connect()
        logger.info("✅ Event bus connected")
        
        # Register event listeners
        from core.event_listeners import event_listeners
        await event_listeners.register_all_handlers()
        logger.info("✅ Event handlers registered")
        
        # Register DORA event handler for workflow_run events
        from core.dora_event_handler import dora_event_handler
        event_bus.register_handler(
            "github.workflow_run.completed",
            dora_event_handler.handle_workflow_run_completed
        )
        await event_bus.subscribe("github_events", None)
        logger.info("✅ DORA event handler registered (listening to github_events)")
        
        # Start listening to events in background
        import asyncio
        listening_task = asyncio.create_task(event_bus.start_listening())
        logger.info("✅ Event bus listening started")
        
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down Workspace Intelligence Service...")
    
    try:
        # Stop event listening
        if listening_task:
            listening_task.cancel()
            try:
                await listening_task
            except asyncio.CancelledError:
                logger.info("✅ Event listening task cancelled")
        
        # Disconnect event bus
        from core.event_bus import event_bus
        await event_bus.disconnect()
        logger.info("✅ Event bus disconnected")
        
        # Disconnect Redis
        from core.redis_cache import cache
        await cache.disconnect()
        logger.info("✅ Redis cache disconnected")
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")


# Create FastAPI app
app = FastAPI(
    title="Workspace Intelligence Service",
    description="DevSecOps maturity analysis and repository tree management",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# Metrics collection middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Collect metrics for each request"""
    start_time = time.time()
    
    response = await call_next(request)
    
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


# Include routers
from api.routes import workspace_intelligence, repository_tree
from api.routes.dora_metrics import router as dora_router

app.include_router(workspace_intelligence.router, prefix="/api", tags=["workspace-intelligence"])
app.include_router(repository_tree.router, tags=["repository-tree"])
app.include_router(dora_router, tags=["dora-metrics"])

logger.info("✅ API routers included (workspace-intelligence, repository-tree, dora-metrics)")


@app.get("/")
async def root():
    return {
        "service": "Workspace Intelligence Service",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "workspace-intelligence-service"
    }


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Workspace Intelligence Service...")
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)
