"""
Pipeline Prediction Service - Main Entry Point
FastAPI application for ML-based CI/CD pipeline failure prediction.
"""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
import time
import logging

# Monitoring imports
from prometheus_client import Counter, Histogram, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
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

# ============================================================================
# DISTRIBUTED TRACING SETUP (OpenTelemetry → Jaeger)
# ============================================================================
SERVICE_NAME = os.getenv("SERVICE_NAME", "pipeline-prediction-service")

resource = Resource.create(attributes={
    "service.name": f"withops-{SERVICE_NAME}",
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

# ============================================================================
# PROMETHEUS METRICS
# ============================================================================
registry = CollectorRegistry()

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    registry=registry
)

PREDICTION_COUNT = Counter(
    'ml_predictions_total',
    'Total ML predictions made',
    ['org_name', 'risk_level'],
    registry=registry
)

TRAINING_COUNT = Counter(
    'ml_training_runs_total',
    'Total model training runs',
    ['org_name', 'status'],
    registry=registry
)


# ============================================================================
# APPLICATION LIFESPAN
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info(f"🚀 Starting {SERVICE_NAME}...")

    try:
        # 1. Initialize database
        from database.config import db_manager
        await db_manager.create_tables()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")

    # 2. Redis connection (placeholder — will be activated in Phase 3)
    # try:
    #     from core.redis_cache import cache
    #     await cache.connect()
    #     logger.info("✅ Redis cache connected")
    # except Exception as e:
    #     logger.warning(f"⚠️ Redis connection error: {e}")

    # 3. Load active ML models into memory
    try:
        from core.model_manager import model_manager
        await model_manager.load_all_active_models()
        logger.info("✅ ML models loaded")
    except Exception as e:
        logger.warning(f"⚠️ Model loading error (non-critical): {e}")

    yield

    # Shutdown
    logger.info(f"🛑 Stopping {SERVICE_NAME}...")
    try:
        from database.config import db_manager
        await db_manager.close()
        logger.info("✅ Database connection closed")
    except Exception as e:
        logger.error(f"❌ Error closing database: {e}")


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================
app = FastAPI(
    title="WithOps Pipeline Prediction Service",
    description="ML-based CI/CD pipeline failure prediction using historical GitHub Actions data.",
    version="1.0.0",
    docs_url="/api/pipeline-prediction/docs",
    openapi_url="/api/pipeline-prediction/openapi.json",
    lifespan=lifespan
)

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# MIDDLEWARE — Request metrics and logging
# ============================================================================
@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start_time = time.time()
    method = request.method
    path = request.url.path

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        status_code = 500
        raise e
    finally:
        latency = time.time() - start_time
        REQUEST_DURATION.labels(method=method, endpoint=path).observe(latency)
        REQUEST_COUNT.labels(method=method, endpoint=path, status=status_code).inc()

    return response


# ============================================================================
# HEALTH & METRICS ENDPOINTS
# ============================================================================
@app.get("/health")
@app.get("/api/pipeline-prediction/health")
async def health_check():
    """
    Service health check endpoint.
    Reports database connectivity, model availability, and service uptime.
    """
    db_healthy = False
    active_models = 0

    # Check database connectivity
    try:
        from database.config import db_manager
        async with db_manager.get_session() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
            db_healthy = True
    except Exception:
        db_healthy = False

    # Check for loaded models
    try:
        from core.model_manager import model_manager
        active_models = model_manager.get_active_model_count()
    except Exception:
        active_models = 0

    overall_status = "healthy" if db_healthy else "degraded"

    return {
        "status": overall_status,
        "service": SERVICE_NAME,
        "version": "1.0.0",
        "checks": {
            "database": "connected" if db_healthy else "disconnected",
            "ml_models_loaded": active_models,
            # "redis": "connected" / "disconnected"  — Phase 3
        },
        "timestamp": time.time()
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/pipeline-prediction/info")
async def service_info():
    """Return service information and available capabilities."""
    return {
        "service": SERVICE_NAME,
        "version": "1.0.0",
        "description": "ML-based CI/CD pipeline failure prediction",
        "capabilities": [
            "predict_pipeline_failure",
            "train_model",
            "view_prediction_history",
            "view_model_performance",
            "feature_importance"
        ],
        "endpoints": {
            "health": "/api/pipeline-prediction/health",
            "docs": "/api/pipeline-prediction/docs",
            "generate_data": "/api/pipeline-prediction/generate-data [POST]",
            "train": "/api/pipeline-prediction/train [POST]",
            "train_status": "/api/pipeline-prediction/train/status [GET]",
            "model_info": "/api/pipeline-prediction/model/{org_name} [GET]",
            "feature_importance": "/api/pipeline-prediction/feature-importance/{org_name} [GET]",
            "data_stats": "/api/pipeline-prediction/data/stats/{org_name} [GET]",
            "predict": "/api/pipeline-prediction/predict [POST] (Phase 3)",
            "history": "/api/pipeline-prediction/history/{org}/{repo} [GET] (Phase 3)"
        }
    }


# ============================================================================
# ROUTE REGISTRATION
# ============================================================================
from api.routes.training import router as training_router
from api.routes.prediction import router as prediction_router
from api.routes.webhook import router as webhook_router  # Phase 1: NEW
from api.routes.metrics import router as metrics_router  # Phase 1: NEW

app.include_router(training_router, prefix="/api/pipeline-prediction")
app.include_router(prediction_router, prefix="/api/pipeline-prediction")
app.include_router(webhook_router)  # Phase 1: No prefix, routes are at /webhook/*
app.include_router(metrics_router)  # Phase 1: Routes at /api/pipeline-prediction/metrics/*


# ============================================================================
# SCHEDULER SETUP (Phase 1: Outcome Reconciliation)
# ============================================================================
def setup_scheduler():
    """Initialize APScheduler for background jobs."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from core.outcome_reconciler import schedule_reconciliation
    from core.model_evaluator import schedule_evaluation
    from core.auto_trainer import schedule_retraining
    
    try:
        scheduler = AsyncIOScheduler()
        
        # ════════════════════════════════════════════════════════════════════════
        # Phase 1: Outcome Reconciliation (Daily)
        # ════════════════════════════════════════════════════════════════════════
        scheduler.add_job(
            schedule_reconciliation,
            trigger=CronTrigger(hour=2, minute=0),
            id="reconcile_outcomes_daily",
            name="Daily outcome reconciliation",
            replace_existing=True,
            coalesce=True,
            max_instances=1
        )
        
        # ════════════════════════════════════════════════════════════════════════
        # Phase 2: Model Evaluation (Weekly - Thursday 04:00 UTC)
        # ════════════════════════════════════════════════════════════════════════
        scheduler.add_job(
            schedule_evaluation,
            trigger=CronTrigger(day_of_week="thu", hour=4, minute=0),
            id="evaluate_models_weekly",
            name="Weekly model evaluation",
            replace_existing=True,
            coalesce=True,
            max_instances=1
        )
        
        # ════════════════════════════════════════════════════════════════════════
        # Phase 2: Auto-Retraining (Bi-weekly - Sunday 03:00 UTC)
        # ════════════════════════════════════════════════════════════════════════
        scheduler.add_job(
            schedule_retraining,
            trigger=CronTrigger(day_of_week="sun", hour=3, minute=0),
            id="retrain_models_biweekly",
            name="Bi-weekly model retraining",
            replace_existing=True,
            coalesce=True,
            max_instances=1
        )
        
        scheduler.start()
        logger.info("✅ Background scheduler started")
        logger.info("   ⏰ Phase 1 - Outcome reconciliation: Daily at 02:00 UTC")
        logger.info("   ⏰ Phase 2 - Model evaluation: Weekly (Thursday) at 04:00 UTC")
        logger.info("   ⏰ Phase 2 - Model retraining: Bi-weekly (Sunday) at 03:00 UTC")
        
        return scheduler
    except Exception as e:
        logger.warning(f"⚠️ Scheduler setup error (non-critical): {e}")
        return None


# Initialize scheduler on startup
_scheduler = None

@app.on_event("startup")
async def startup_scheduler():
    global _scheduler
    _scheduler = setup_scheduler()


@app.on_event("shutdown")
async def shutdown_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        logger.info("✅ Scheduler shutdown")


# Main entry point (for local dev)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8009, reload=True)
