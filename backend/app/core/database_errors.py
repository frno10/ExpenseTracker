"""
Database error handling utilities.
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.exc import (
    SQLAlchemyError,
    OperationalError,
    IntegrityError,
    DataError,
    ProgrammingError,
    TimeoutError as SQLTimeoutError
)
from asyncpg.exceptions import (
    PostgresError,
    ConnectionDoesNotExistError,
    ConnectionFailureError,
    InterfaceError,
    DataError as AsyncpgDataError
)

logger = logging.getLogger(__name__)


class DatabaseErrorHandler:
    """Centralized database error handling and logging."""
    
    @staticmethod
    def log_connection_attempt(attempt: int, max_attempts: int, host: str, port: int, database: str) -> None:
        """Log database connection attempt."""
        logger.info(f"Database connection attempt {attempt}/{max_attempts}")
        logger.info(f"Target: {host}:{port}/{database}")
    
    @staticmethod
    def log_connection_success(host: str, port: int, database: str, response_time_ms: float) -> None:
        """Log successful database connection."""
        logger.info(f"✅ Database connection successful")
        logger.info(f"Connected to: {host}:{port}/{database}")
        logger.info(f"Connection time: {response_time_ms:.2f}ms")
    
    @staticmethod
    def log_connection_failure(error: Exception, attempt: int, max_attempts: int, 
                             host: str, port: int, database: str) -> None:
        """Log database connection failure with detailed information."""
        logger.error(f"❌ Database connection failed (attempt {attempt}/{max_attempts})")
        logger.error(f"Target: {host}:{port}/{database}")
        logger.error(f"Error type: {type(error).__name__}")
        logger.error(f"Error message: {str(error)}")
        
        # Log specific error details based on error type
        if isinstance(error, ConnectionFailureError):
            logger.error("Connection failure - check if database server is running")
        elif isinstance(error, ConnectionDoesNotExistError):
            logger.error("Connection does not exist - database may have been closed")
        elif isinstance(error, OperationalError):
            logger.error("Operational error - check database configuration and credentials")
        elif isinstance(error, TimeoutError) or isinstance(error, SQLTimeoutError):
            logger.error("Connection timeout - database may be overloaded or network issues")
        elif "Network is unreachable" in str(error):
            logger.error("Network unreachable - check network connectivity and firewall settings")
        elif "Connection refused" in str(error):
            logger.error("Connection refused - database server may not be accepting connections")
        elif "Name or service not known" in str(error):
            logger.error("DNS resolution failed - check database hostname")
    
    @staticmethod
    def log_pool_status(pool_info: Dict[str, Any]) -> None:
        """Log database connection pool status."""
        logger.info("=== Database Pool Status ===")
        for key, value in pool_info.items():
            logger.info(f"{key}: {value}")
    
    @staticmethod
    def log_query_error(query: str, error: Exception, execution_time_ms: float) -> None:
        """Log database query error with context."""
        logger.error(f"Database query failed after {execution_time_ms:.2f}ms")
        logger.error(f"Query: {query[:200]}{'...' if len(query) > 200 else ''}")
        logger.error(f"Error: {type(error).__name__}: {str(error)}")
    
    @staticmethod
    def log_migration_status(migration_name: str, status: str, details: Optional[str] = None) -> None:
        """Log database migration status."""
        if status == "started":
            logger.info(f"🔄 Starting migration: {migration_name}")
        elif status == "completed":
            logger.info(f"✅ Migration completed: {migration_name}")
        elif status == "failed":
            logger.error(f"❌ Migration failed: {migration_name}")
            if details:
                logger.error(f"Migration error details: {details}")
        elif status == "skipped":
            logger.info(f"⏭️ Migration skipped: {migration_name}")
    
    @staticmethod
    def get_error_context(error: Exception) -> Dict[str, Any]:
        """Extract contextual information from database errors."""
        context = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "is_connection_error": False,
            "is_timeout_error": False,
            "is_integrity_error": False,
            "is_data_error": False,
            "suggested_action": "Check logs for more details"
        }
        
        # Categorize error types
        if isinstance(error, (ConnectionFailureError, ConnectionDoesNotExistError, OperationalError)):
            context["is_connection_error"] = True
            context["suggested_action"] = "Check database connectivity and configuration"
        
        elif isinstance(error, (TimeoutError, SQLTimeoutError)):
            context["is_timeout_error"] = True
            context["suggested_action"] = "Check database performance and network latency"
        
        elif isinstance(error, IntegrityError):
            context["is_integrity_error"] = True
            context["suggested_action"] = "Check data constraints and foreign key relationships"
        
        elif isinstance(error, (DataError, AsyncpgDataError)):
            context["is_data_error"] = True
            context["suggested_action"] = "Check data types and value formats"
        
        elif isinstance(error, ProgrammingError):
            context["suggested_action"] = "Check SQL syntax and database schema"
        
        # Extract specific error codes if available
        if hasattr(error, 'pgcode'):
            context["postgres_error_code"] = error.pgcode
        
        if hasattr(error, 'sqlstate'):
            context["sql_state"] = error.sqlstate
        
        return context
    
    @staticmethod
    def format_error_for_client(error: Exception, include_details: bool = False) -> Dict[str, Any]:
        """Format database error for client response."""
        context = DatabaseErrorHandler.get_error_context(error)
        
        # Base error response
        error_response = {
            "error": "Database operation failed",
            "type": "database_error"
        }
        
        # Add specific error messages based on error type
        if context["is_connection_error"]:
            error_response["error"] = "Database connection failed"
            error_response["message"] = "Unable to connect to database. Please try again later."
        
        elif context["is_timeout_error"]:
            error_response["error"] = "Database operation timed out"
            error_response["message"] = "The operation took too long to complete. Please try again."
        
        elif context["is_integrity_error"]:
            error_response["error"] = "Data integrity violation"
            error_response["message"] = "The operation violates data constraints."
        
        elif context["is_data_error"]:
            error_response["error"] = "Invalid data format"
            error_response["message"] = "The provided data format is invalid."
        
        # Include detailed error information if requested (for debugging)
        if include_details:
            error_response["details"] = {
                "error_type": context["error_type"],
                "suggested_action": context["suggested_action"]
            }
            
            if "postgres_error_code" in context:
                error_response["details"]["postgres_code"] = context["postgres_error_code"]
        
        return error_response


# Global error handler instance
db_error_handler = DatabaseErrorHandler()