"""
Workflow Orchestration Service - Main Application
Handles workflow tree management, execution orchestration, and security scanning
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
    "service.name": "withops-workflow-orchestration",
    "service.version": os.getenv("SERVICE_VERSION", "1.0.0"),
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

WORKFLOW_EXECUTIONS = Counter(
    'workflow_executions_total',
    'Total workflow executions',
    ['org_name', 'status']
)

SECURITY_SCANS = Counter(
    'security_scans_total',
    'Total security scans',
    ['scan_type', 'risk_level']
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for the application"""
    # Startup
    print("🚀 Starting Workflow Orchestration Service...")
    print(f"📊 Service: {os.getenv('SERVICE_NAME', 'workflow-orchestration-service')}")
    print(f"🔧 Environment: {os.getenv('ENVIRONMENT', 'development')}")
    
    # Initialize connections (Redis, Database, etc.)
    # TODO: Initialize Redis connection
    # TODO: Initialize Database connection
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Workflow Orchestration Service...")
    # TODO: Close connections

# Create FastAPI app
app = FastAPI(
    title="Workflow Orchestration Service",
    description="Manages workflow trees, execution orchestration, and security scanning",
    version=os.getenv("SERVICE_VERSION", "1.0.0"),
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
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
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
    
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "path": request.url.path
        }
    )

# Import routers
from api.routes.workflow_tree import router as tree_router
from api.routes.workflow_execution import router as execution_router
from api.routes.security_scanning import router as security_router
from api.routes.canvas import router as canvas_router

# Register routers
app.include_router(tree_router)
app.include_router(execution_router)
app.include_router(security_router)
app.include_router(canvas_router)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": os.getenv("SERVICE_NAME", "workflow-orchestration-service"),
        "version": os.getenv("SERVICE_VERSION", "1.0.0"),
        "environment": os.getenv("ENVIRONMENT", "development")
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Workflow Orchestration Service",
        "version": os.getenv("SERVICE_VERSION", "1.0.0"),
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }

# Metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("SERVICE_PORT", 8007)),
        reload=True
    )
