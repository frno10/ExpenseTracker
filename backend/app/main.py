"""
FastAPI main application entry point for the Expense Tracker.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
 
from app.api.auth import router as auth_router
from app.api.categories import router as categories_router
from app.api.expenses import router as expenses_router
from app.api.merchants import router as merchants_router
from app.api.payment_methods import router as payment_methods_router
from app.api.statement_import import router as statement_import_router
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.logging_config import setup_logging
from app.core.observability_middleware import ObservabilityMiddleware
from app.core.security import (
    AuthenticationMiddleware,
    SecurityHeadersMiddleware,
    setup_rate_limiting,
)
from app.core.telemetry import telemetry

# Configure structured logging
setup_logging(
    log_level="DEBUG" if settings.debug else "INFO",
    use_json=not settings.debug  # Use JSON in production, human-readable in development
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    """
    # Startup
    logger.info("Starting up Expense Tracker API")
    
    # Initialize OpenTelemetry
    try:
        telemetry.initialize(app)
        logger.info("OpenTelemetry initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry: {e}")
        # Continue without telemetry in case of failure
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Don't fail startup, database might not be available yet
    
    yield
    
    # Shutdown
    logger.info("Shutting down Expense Tracker API")
    await close_db()


app = FastAPI(
    title="Expense Tracker API",
    description="A comprehensive personal finance management system with multi-user support",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Security middleware (order matters!)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(ObservabilityMiddleware)
app.add_middleware(AuthenticationMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://127.0.0.1:3000",
        "https://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up rate limiting
setup_rate_limiting(app)

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(categories_router, prefix="/api")
app.include_router(expenses_router, prefix="/api")
app.include_router(merchants_router, prefix="/api")
app.include_router(payment_methods_router, prefix="/api")
app.include_router(statement_import_router)

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Expense Tracker API",
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else "Documentation disabled in production",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": "development" if settings.debug else "production"
    }