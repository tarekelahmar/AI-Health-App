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
from app.api.v1 import (
    users, auth, labs, wearables, symptoms, assessments, insights, protocols
)

settings = get_settings()

# Setup logging
setup_logging(level=settings.LOG_LEVEL)
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
    
    # Note: Database schema is managed by Alembic migrations
    # Run 'alembic upgrade head' to apply migrations
    logger.info("Database connection ready (migrations should be applied separately)")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered functional health assessment and protocol generation",
    lifespan=lifespan,
)

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
app.include_router(insights.router, prefix="/api/v1/insights", tags=["insights"])
app.include_router(protocols.router, prefix="/api/v1/protocols", tags=["protocols"])

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
