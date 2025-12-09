"""Main FastAPI application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.database import engine, SessionLocal
from app.core.config import (
    API_TITLE, 
    API_VERSION,
    CORS_ORIGINS,
    CORS_CREDENTIALS,
    CORS_METHODS,
    CORS_HEADERS
)
from app import models
from app.api import users, health_data, assessment, protocol

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(title=API_TITLE, version=API_VERSION)

# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_CREDENTIALS,
    allow_methods=CORS_METHODS,
    allow_headers=CORS_HEADERS,
)

# Include routers
app.include_router(users.router)
app.include_router(health_data.router)
app.include_router(assessment.router)
app.include_router(protocol.router)


@app.get("/")
def read_root():
    """Health check endpoint"""
    return {"message": "Health App API is running!", "version": API_VERSION}


@app.get("/health/")
def health_check():
    """Verify database connection"""
    try:
        db = SessionLocal()
        # Try a simple query
        db.query(models.User).first()
        db.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

