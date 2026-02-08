"""
Database configuration and connection management.
"""
import asyncio
import logging
import time
from typing import AsyncGenerator, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .config import settings
from .database_errors import db_error_handler

logger = logging.getLogger(__name__)

async def create_engine_with_retry() -> Any:
    """
    Create database engine with retry logic.
    
    Returns:
        AsyncEngine: Database engine
        
    Raises:
        Exception: If all retry attempts fail
    """
    db_config = settings.get_database_config()
    
    for attempt in range(db_config.max_retries):
        try:
            # Log connection attempt with detailed information
            db_error_handler.log_connection_attempt(
                attempt + 1, db_config.max_retries, 
                db_config.host, db_config.port, db_config.database
            )
            
            start_time = time.time()
            
            engine = create_async_engine(
                settings.database_url,
                echo=settings.debug,
                poolclass=NullPool,  # Use NullPool for serverless environments
                pool_pre_ping=True,
                pool_recycle=300,
                connect_args={
                    "server_settings": {
                        "application_name": "ExpenseTracker",
                    }
                }
            )
            
            # Test the connection
            await test_connection(engine)
            
            # Log successful connection
            connection_time = (time.time() - start_time) * 1000
            db_error_handler.log_connection_success(
                db_config.host, db_config.port, db_config.database, connection_time
            )
            
            return engine
            
        except Exception as e:
            # Log detailed connection failure information
            db_error_handler.log_connection_failure(
                e, attempt + 1, db_config.max_retries,
                db_config.host, db_config.port, db_config.database
            )
            
            if attempt < db_config.max_retries - 1:
                wait_time = db_config.retry_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.error("All database connection attempts failed")
                error_context = db_error_handler.get_error_context(e)
                logger.error(f"Suggested action: {error_context['suggested_action']}")
                raise Exception(f"Failed to create database engine after {db_config.max_retries} attempts: {e}")


async def test_connection(engine: Any) -> bool:
    """
    Test database connectivity.
    
    Args:
        engine: Database engine to test
        
    Returns:
        bool: True if connection successful
        
    Raises:
        Exception: If connection test fails
    """
    start_time = time.time()
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()  # Don't await this - it's not async
            
            # Test additional database functionality
            await conn.execute(text("SELECT current_database(), current_user, version()"))
            
            return True
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        db_error_handler.log_query_error("SELECT 1", e, execution_time)
        raise


async def wait_for_database(max_wait_time: int = 60) -> None:
    """
    Wait for database to become available.
    
    Args:
        max_wait_time: Maximum time to wait in seconds
        
    Raises:
        Exception: If database doesn't become available within max_wait_time
    """
    logger.info("Waiting for database to become available...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        try:
            test_engine = await create_engine_with_retry()
            await test_engine.dispose()
            logger.info("Database is now available")
            return
        except Exception as e:
            logger.warning(f"Database not yet available: {e}")
            await asyncio.sleep(2)
    
    raise Exception(f"Database did not become available within {max_wait_time} seconds")


def get_connection_info() -> Dict[str, Any]:
    """
    Get connection status information for monitoring.
    
    Returns:
        Dict containing connection information
    """
    db_config = settings.get_database_config()
    render_config = settings.get_render_config()
    
    info = {
        'database_host': db_config.host,
        'database_port': db_config.port,
        'database_name': db_config.database,
        'database_user': db_config.username,
        'is_render': render_config['is_render'],
        'max_retries': db_config.max_retries,
        'retry_delay': db_config.retry_delay,
        'connection_timeout': db_config.connection_timeout,
        'engine_initialized': engine is not None,
        'session_factory_initialized': AsyncSessionLocal is not None,
    }
    
    # Add pool information if engine is available
    if engine is not None:
        try:
            pool = engine.pool
            info.update({
                'pool_size': getattr(pool, 'size', 'N/A'),
                'pool_checked_in': getattr(pool, 'checkedin', 'N/A'),
                'pool_checked_out': getattr(pool, 'checkedout', 'N/A'),
                'pool_overflow': getattr(pool, 'overflow', 'N/A'),
            })
        except Exception as e:
            logger.debug(f"Could not get pool information: {e}")
            info['pool_info_error'] = str(e)
    
    return info


async def log_pool_status() -> None:
    """Log current database pool status."""
    if engine is not None:
        try:
            pool_info = {
                'engine_initialized': True,
                'pool_class': type(engine.pool).__name__,
            }
            
            # Get pool statistics if available
            pool = engine.pool
            if hasattr(pool, 'size'):
                pool_info['pool_size'] = pool.size()
            if hasattr(pool, 'checkedin'):
                pool_info['checked_in_connections'] = pool.checkedin()
            if hasattr(pool, 'checkedout'):
                pool_info['checked_out_connections'] = pool.checkedout()
            if hasattr(pool, 'overflow'):
                pool_info['overflow_connections'] = pool.overflow()
            
            db_error_handler.log_pool_status(pool_info)
            
        except Exception as e:
            logger.error(f"Failed to get pool status: {e}")
    else:
        logger.warning("Cannot get pool status - engine not initialized")


# Initialize engine as None - will be created during startup
engine: Optional[Any] = None

# Session factory - will be initialized during startup
AsyncSessionLocal: Optional[async_sessionmaker] = None


async def initialize_database() -> None:
    """
    Initialize database engine and session factory.
    
    This should be called during application startup.
    """
    global engine, AsyncSessionLocal
    
    logger.info("Initializing database connection...")
    
    # Wait for database availability (important for Render deployments)
    await wait_for_database()
    
    # Create engine with retry logic
    engine = await create_engine_with_retry()
    
    # Create session factory
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    logger.info("Database initialization completed successfully")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.
    
    Yields:
        AsyncSession: Database session
        
    Raises:
        Exception: If database is not initialized or session creation fails
    """
    if AsyncSessionLocal is None:
        raise Exception("Database not initialized. Call initialize_database() first.")
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        except Exception as e:
            logger.error(f"Unexpected database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables.
    
    This function creates all tables defined in the models.
    
    Raises:
        Exception: If database is not initialized or table creation fails
    """
    if engine is None:
        raise Exception("Database engine not initialized. Call initialize_database() first.")
    
    try:
        from app.models import Base
        
        db_error_handler.log_migration_status("create_all_tables", "started")
        
        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            
        db_error_handler.log_migration_status("create_all_tables", "completed")
        logger.info("Database tables created successfully")
            
    except Exception as e:
        db_error_handler.log_migration_status("create_all_tables", "failed", str(e))
        error_context = db_error_handler.get_error_context(e)
        logger.error(f"Suggested action: {error_context['suggested_action']}")
        raise Exception(f"Failed to create database tables: {e}")


def get_db_session():
    """
    Get a database session context manager for use outside of FastAPI dependencies.
    
    Returns:
        AsyncSession context manager
        
    Raises:
        Exception: If database is not initialized
    """
    if AsyncSessionLocal is None:
        raise Exception("Database not initialized. Call initialize_database() first.")
    
    return AsyncSessionLocal()


async def close_db() -> None:
    """
    Close database connections.
    
    This function should be called on application shutdown.
    """
    global engine, AsyncSessionLocal
    
    if engine is not None:
        await engine.dispose()
        engine = None
        AsyncSessionLocal = None
        logger.info("Database connections closed")
    else:
        logger.warning("Database engine was not initialized, nothing to close")