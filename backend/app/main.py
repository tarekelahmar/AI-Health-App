"""Main FastAPI application entry point"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging

from app.config.settings import get_settings, validate_config
from app.config.logging import setup_logging
from app.config.rate_limiting import setup_rate_limiting
from app.core.database import init_db
from app.core.logging import configure_logging, get_logger
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.api.v1.metrics_system import router as metrics_system_router
from app.api.v1 import (
    users, auth, labs, wearables, symptoms, assessments, insights, protocols, metrics
)
from app.api.v1.health_data import router as health_data_router
from app.api.v1.baselines import router as baselines_router
from app.api.v1.coverage import router as coverage_router
from app.api.v1.interventions import router as interventions_router
from app.api.v1.protocols import router as protocols_router
from app.api.v1.experiments import router as experiments_router
from app.api.v1.adherence import router as adherence_router
from app.api.v1.evaluations import router as evaluations_router
from app.api.v1.loop import router as loop_router
from app.api.v1.checkins import router as checkins_router
from app.api.v1.graphs import router as graphs_router
from app.api.v1 import safety
from app.api.v1.interventions import router as interventions_router
from app.api.v1.protocols import router as protocols_router
from app.api.v1.health import router as health_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.inbox import router as inbox_router
from app.api.v1.outbox import router as outbox_router
from app.api.v1.summaries import router as summaries_router
from app.api.v1.narratives import router as narratives_router
from app.api.v1.auth_mode import auth_mode_router
from app.api.v1.providers_whoop import router as whoop_router
from app.api.v1.consent import router as consent_router
from app.api.v1.drivers import router as drivers_router
from app.api.v1.memory import router as memory_router
from app.api.v1.explain import router as explain_router
from app.api.v1.trust import router as trust_router
from app.api.v1.personal_model import router as personal_model_router
from app.api.v1.audit import router as audit_router
from app.api.v1.system import router as system_router
from app.scheduler import start_scheduler, stop_scheduler

settings = get_settings()

# Setup logging (structured logging with request IDs)
configure_logging()
log = get_logger(__name__)

# Also keep existing logger for compatibility
logger = logging.getLogger(__name__)

# Validate configuration on startup
try:
    validate_config()
except ValueError as e:
    logger.error(f"Configuration validation failed: {e}")
    raise

# Startup & shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle: startup and shutdown"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # MVP-safe: create missing tables (e.g., baselines)
    init_db()
    logger.info("Database connection ready (migrations should be applied separately)")
    
    # STEP L: start optional scheduler for dev/MVP (if ENABLE_SCHEDULER=true)
    start_scheduler()
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}...")
    stop_scheduler()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered functional health assessment and protocol generation",
    lifespan=lifespan,
)

# Observability middleware (request IDs + metrics)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(MetricsMiddleware)

# CORS middleware - all configuration from Settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

# Rate limiting setup (if enabled)
if settings.ENABLE_RATE_LIMITING:
    app = setup_rate_limiting(app)
    logger.info("Rate limiting enabled")

# Include routers (modular endpoints)
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(labs.router, prefix="/api/v1/labs", tags=["labs"])
app.include_router(wearables.router, prefix="/api/v1/wearables", tags=["wearables"])
app.include_router(symptoms.router, prefix="/api/v1/symptoms", tags=["symptoms"])
app.include_router(assessments.router, prefix="/api/v1/assessments", tags=["assessments"])
app.include_router(insights.router, prefix="/api/v1/insights")
# protocols.router is replaced by protocols_router (new implementation)
# app.include_router(protocols.router, prefix="/api/v1/protocols", tags=["protocols"])
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["metrics"])
app.include_router(health_data_router, prefix="/api/v1", tags=["health-data"])
app.include_router(baselines_router, prefix="/api/v1", tags=["baselines"])
app.include_router(coverage_router, prefix="/api/v1", tags=["coverage"])
app.include_router(interventions_router)
app.include_router(protocols_router)
app.include_router(experiments_router)
app.include_router(adherence_router)
app.include_router(evaluations_router)
app.include_router(loop_router)
app.include_router(checkins_router)
app.include_router(graphs_router)
app.include_router(safety.router)
app.include_router(health_router)
app.include_router(jobs_router)
app.include_router(inbox_router)
app.include_router(outbox_router)
app.include_router(summaries_router)
app.include_router(narratives_router)
app.include_router(auth_mode_router)
app.include_router(whoop_router)
app.include_router(consent_router)
app.include_router(drivers_router)
app.include_router(memory_router)
app.include_router(explain_router)
app.include_router(trust_router)
app.include_router(personal_model_router)
app.include_router(audit_router)
app.include_router(system_router)

# Observability
app.include_router(metrics_system_router)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Health AI Coach API",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "debug": settings.DEBUG,
        "database": "connected"
    }

# Error handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "detail": exc.errors() if settings.DEBUG else "Invalid request data"
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {exc}",
        exc_info=True,
        extra={"path": request.url.path, "method": request.method}
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
        "error": "Internal server error",
        "detail": str(exc) if settings.DEBUG else "An error occurred"
    }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
