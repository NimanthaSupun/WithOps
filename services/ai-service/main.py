"""
AI Service - Microservice for AI/ML operations
Handles PR description generation, threat analysis using Ollama, Claude, and Groq
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
    "service.name": "withops-ai-service",
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

# Worker task
worker_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🤖 Starting AI Service")
    
    # Start background worker for async tasks
    import asyncio
    from worker import ThreatAnalysisWorker
    
    global worker_task
    worker = ThreatAnalysisWorker()
    worker_task = asyncio.create_task(worker.run())
    print("✅ Background worker started")
    
    yield
    
    # Shutdown
    print("👋 Shutting down AI Service")
    
    # Stop worker
    if worker_task:
        await worker.stop()
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    print("✅ Background worker stopped")

app = FastAPI(
    title="WithOps AI Service",
    description="AI/ML microservice for PR descriptions and threat analysis",
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

# Metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
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

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "withops-ai-service",
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "WithOps AI Service",
        "version": "1.0.0",
        "status": "running"
    }

# Import and include routers
from api.routes import pr_description, threat_analysis

app.include_router(pr_description.router)
app.include_router(threat_analysis.router)

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
