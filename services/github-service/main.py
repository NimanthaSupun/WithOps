"""
GitHub Service - Microservice for GitHub integration operations
Handles GitHub App installations, repository management, PR creation, and workflow analysis
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
import time

# Monitoring imports
from prometheus_client import Counter, Histogram, make_asgi_app
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

load_dotenv()

# Setup distributed tracing
resource = Resource.create(attributes={
    "service.name": "withops-github-service",
    "service.version": "1.0.0",
    "deployment.environment": "development"
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
    # Startup
    print("🐙 Starting GitHub Service")
    
    # Initialize database
    from database.config import db_manager
    await db_manager.create_tables()
    print("✅ Database initialized")
    
    # Initialize Redis cache
    from core.redis_cache import cache
    await cache.connect()
    print("✅ Redis cache connected")
    
    # Initialize event bus
    from core.event_bus import event_bus
    await event_bus.connect()
    print("✅ Event bus connected")
    
    yield
    
    # Shutdown
    print("👋 Shutting down GitHub Service")
    
    # Disconnect event bus
    from core.event_bus import event_bus
    await event_bus.disconnect()
    print("✅ Event bus disconnected")
    
    # Disconnect Redis
    from core.redis_cache import cache
    await cache.disconnect()
    print("✅ Redis cache disconnected")

app = FastAPI(
    title="WithOps GitHub Service",
    description="GitHub integration microservice for organization/repository management",
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

# Request timing middleware
@app.middleware("http")
async def add_metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    # Record metrics
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

# Import routes
from api.routes import github
from api.routes import webhook

# Register routes
app.include_router(github.router)
app.include_router(webhook.router)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "github-service",
        "version": "1.0.0"
    }

# Metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
