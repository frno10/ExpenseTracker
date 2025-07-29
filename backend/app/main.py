"""
FastAPI main application entry point for the Expense Tracker.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
 
from app.api.auth import router as auth_router
from app.api.budgets import router as budgets_router
from app.api.categories import router as categories_router
from app.api.expenses import router as expenses_router
from app.api.merchants import router as merchants_router
from app.api.payment_methods import router as payment_methods_router
from app.api.accounts import router as accounts_router
from app.api.recurring_expenses import router as recurring_expenses_router
from app.api.attachments import router as attachments_router
from app.api.expense_search import router as expense_search_router
from app.api.export import router as export_router
from app.api.statement_import import router as statement_import_router
from app.api.analytics import router as analytics_router
from app.api.advanced_analytics import router as advanced_analytics_router
from app.api.websocket import router as websocket_router
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
from app.services.recurring_expense_scheduler import (
    start_recurring_expense_scheduler, 
    stop_recurring_expense_scheduler
)

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
    
    # Start recurring expense scheduler
    try:
        await start_recurring_expense_scheduler()
        logger.info("Recurring expense scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start recurring expense scheduler: {e}")
        # Continue without scheduler
    
    # Start WebSocket cleanup task
    try:
        import asyncio
        from app.services.websocket_manager import websocket_manager
        
        async def websocket_cleanup_task():
            while True:
                try:
                    await asyncio.sleep(300)  # Run every 5 minutes
                    await websocket_manager.cleanup_stale_connections()
                except Exception as e:
                    logger.error(f"WebSocket cleanup task error: {e}")
        
        asyncio.create_task(websocket_cleanup_task())
        logger.info("WebSocket cleanup task started")
    except Exception as e:
        logger.error(f"Failed to start WebSocket cleanup task: {e}")
        # Continue without cleanup task
    
    yield
    
    # Shutdown
    logger.info("Shutting down Expense Tracker API")
    
    # Cleanup WebSocket connections
    try:
        from app.services.websocket_manager import websocket_manager
        await websocket_manager.cleanup_stale_connections(max_age_minutes=0)  # Close all connections
        logger.info("WebSocket connections cleaned up")
    except Exception as e:
        logger.error(f"Failed to cleanup WebSocket connections: {e}")
    
    await stop_recurring_expense_scheduler()
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
app.include_router(budgets_router)
app.include_router(categories_router, prefix="/api")
app.include_router(expenses_router, prefix="/api")
app.include_router(merchants_router, prefix="/api")
app.include_router(payment_methods_router, prefix="/api")
app.include_router(accounts_router, prefix="/api")
app.include_router(recurring_expenses_router, prefix="/api")
app.include_router(attachments_router, prefix="/api")
app.include_router(expense_search_router, prefix="/api")
app.include_router(export_router, prefix="/api")
app.include_router(statement_import_router)
app.include_router(analytics_router)
app.include_router(advanced_analytics_router)
app.include_router(websocket_router, prefix="/api")

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