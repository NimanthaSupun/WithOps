"""
Threat Modeling Service - Main Entry Point
FastAPI application for threat modeling, STRIDE analysis, and security assessments
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

from database import db_manager
from app.routes import threat_models_router

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Setup distributed tracing
resource = Resource.create(attributes={
    "service.name": "withops-threat-modeling-service",
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
    logger.info("🚀 Starting Threat Modeling Service...")
    
    try:
        # Initialize database
        await db_manager.create_tables()
        logger.info("✅ Database initialized")
        
        # Connect event bus
        from app.core import event_bus
        await event_bus.connect()
        logger.info("✅ Event bus connected")
        
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down Threat Modeling Service...")
    
    try:
        # Disconnect event bus
        from app.core import event_bus
        await event_bus.disconnect()
        logger.info("✅ Event bus disconnected")
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")


# Create FastAPI app
app = FastAPI(
    title="Threat Modeling Service",
    description="Microservice for threat modeling, STRIDE analysis, and security assessments",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add process time header and metrics"""
    start_time = time.time()
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        response.headers["X-Process-Time"] = str(process_time)
        
        # Record metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(process_time)
        
        return response
    except Exception as e:
        logger.error(f"Request error: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )


# Register routes
app.include_router(threat_models_router)

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# Root endpoint
@app.get("/")
async def root():
    """Service info"""
    return {
        "service": "threat-modeling-service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/v1/health",
            "models": "/api/v1/models",
            "analysis": "/api/v1/models/{id}/comprehensive-analysis",
            "library": "/api/v1/library",
            "dashboard": "/api/v1/dashboard",
            "metrics": "/metrics"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    db_healthy = await db_manager.health_check()
    
    return {
        "status": "healthy" if db_healthy else "degraded",
        "service": "threat-modeling-service",
        "database": "connected" if db_healthy else "disconnected"
    }


# Instrument with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("SERVICE_PORT", 8003))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
