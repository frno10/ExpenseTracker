"""
Unit tests for database error handling utilities.
"""
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import (
    OperationalError,
    IntegrityError,
    DataError,
    TimeoutError as SQLTimeoutError
)
from asyncpg.exceptions import (
    ConnectionFailureError,
    ConnectionDoesNotExistError,
    DataError as AsyncpgDataError
)

from app.core.database_errors import DatabaseErrorHandler, db_error_handler


class TestDatabaseErrorHandler:
    """Test database error handling functionality."""
    
    @patch('app.core.database_errors.logger')
    def test_log_connection_attempt(self, mock_logger):
        """Test logging connection attempts."""
        DatabaseErrorHandler.log_connection_attempt(1, 5, "localhost", 5432, "testdb")
        
        assert mock_logger.info.call_count == 2
        mock_logger.info.assert_any_call("Database connection attempt 1/5")
        mock_logger.info.assert_any_call("Target: localhost:5432/testdb")
    
    @patch('app.core.database_errors.logger')
    def test_log_connection_success(self, mock_logger):
        """Test logging successful connections."""
        DatabaseErrorHandler.log_connection_success("localhost", 5432, "testdb", 150.5)
        
        assert mock_logger.info.call_count == 3
        mock_logger.info.assert_any_call("✅ Database connection successful")
        mock_logger.info.assert_any_call("Connected to: localhost:5432/testdb")
        mock_logger.info.assert_any_call("Connection time: 150.50ms")
    
    @patch('app.core.database_errors.logger')
    def test_log_connection_failure_generic(self, mock_logger):
        """Test logging generic connection failures."""
        error = Exception("Generic error")
        DatabaseErrorHandler.log_connection_failure(error, 2, 5, "localhost", 5432, "testdb")
        
        assert mock_logger.error.call_count >= 4
        mock_logger.error.assert_any_call("❌ Database connection failed (attempt 2/5)")
        mock_logger.error.assert_any_call("Target: localhost:5432/testdb")
        mock_logger.error.assert_any_call("Error type: Exception")
        mock_logger.error.assert_any_call("Error message: Generic error")
    
    @patch('app.core.database_errors.logger')
    def test_log_connection_failure_specific_errors(self, mock_logger):
        """Test logging specific connection failure types."""
        # Test ConnectionFailureError
        error = ConnectionFailureError("Connection failed")
        DatabaseErrorHandler.log_connection_failure(error, 1, 3, "localhost", 5432, "testdb")
        
        mock_logger.error.assert_any_call("Connection failure - check if database server is running")
        
        # Test OperationalError
        mock_logger.reset_mock()
        error = OperationalError("statement", "params", "orig")
        DatabaseErrorHandler.log_connection_failure(error, 1, 3, "localhost", 5432, "testdb")
        
        mock_logger.error.assert_any_call("Operational error - check database configuration and credentials")
    
    @patch('app.core.database_errors.logger')
    def test_log_pool_status(self, mock_logger):
        """Test logging pool status."""
        pool_info = {
            "pool_size": 10,
            "checked_in": 8,
            "checked_out": 2,
            "overflow": 0
        }
        
        DatabaseErrorHandler.log_pool_status(pool_info)
        
        mock_logger.info.assert_any_call("=== Database Pool Status ===")
        mock_logger.info.assert_any_call("pool_size: 10")
        mock_logger.info.assert_any_call("checked_in: 8")
        mock_logger.info.assert_any_call("checked_out: 2")
        mock_logger.info.assert_any_call("overflow: 0")
    
    @patch('app.core.database_errors.logger')
    def test_log_query_error(self, mock_logger):
        """Test logging query errors."""
        query = "SELECT * FROM users WHERE id = 1"
        error = Exception("Query failed")
        
        DatabaseErrorHandler.log_query_error(query, error, 250.0)
        
        mock_logger.error.assert_any_call("Database query failed after 250.00ms")
        mock_logger.error.assert_any_call(f"Query: {query}")
        mock_logger.error.assert_any_call("Error: Exception: Query failed")
    
    @patch('app.core.database_errors.logger')
    def test_log_query_error_long_query(self, mock_logger):
        """Test logging errors for long queries (truncated)."""
        long_query = "SELECT * FROM users WHERE " + "x = 1 AND " * 50 + "y = 2"
        error = Exception("Query failed")
        
        DatabaseErrorHandler.log_query_error(long_query, error, 100.0)
        
        # Check that query was truncated
        calls = [call.args[0] for call in mock_logger.error.call_args_list]
        query_log = next(call for call in calls if call.startswith("Query:"))
        assert len(query_log) <= 210  # 200 chars + "Query: " + "..."
        assert query_log.endswith("...")
    
    @patch('app.core.database_errors.logger')
    def test_log_migration_status(self, mock_logger):
        """Test logging migration status."""
        # Test started
        DatabaseErrorHandler.log_migration_status("test_migration", "started")
        mock_logger.info.assert_called_with("🔄 Starting migration: test_migration")
        
        # Test completed
        DatabaseErrorHandler.log_migration_status("test_migration", "completed")
        mock_logger.info.assert_called_with("✅ Migration completed: test_migration")
        
        # Test failed
        DatabaseErrorHandler.log_migration_status("test_migration", "failed", "Error details")
        mock_logger.error.assert_any_call("❌ Migration failed: test_migration")
        mock_logger.error.assert_any_call("Migration error details: Error details")
        
        # Test skipped
        DatabaseErrorHandler.log_migration_status("test_migration", "skipped")
        mock_logger.info.assert_called_with("⏭️ Migration skipped: test_migration")
    
    def test_get_error_context_connection_error(self):
        """Test getting context for connection errors."""
        error = ConnectionFailureError("Connection failed")
        context = DatabaseErrorHandler.get_error_context(error)
        
        assert context["error_type"] == "ConnectionFailureError"
        assert context["error_message"] == "Connection failed"
        assert context["is_connection_error"] is True
        assert context["is_timeout_error"] is False
        assert context["suggested_action"] == "Check database connectivity and configuration"
    
    def test_get_error_context_timeout_error(self):
        """Test getting context for timeout errors."""
        error = SQLTimeoutError("statement", "params", "orig")
        context = DatabaseErrorHandler.get_error_context(error)
        
        assert context["error_type"] == "TimeoutError"
        assert context["is_timeout_error"] is True
        assert context["is_connection_error"] is False
        assert context["suggested_action"] == "Check database performance and network latency"
    
    def test_get_error_context_integrity_error(self):
        """Test getting context for integrity errors."""
        error = IntegrityError("statement", "params", "orig")
        context = DatabaseErrorHandler.get_error_context(error)
        
        assert context["error_type"] == "IntegrityError"
        assert context["is_integrity_error"] is True
        assert context["suggested_action"] == "Check data constraints and foreign key relationships"
    
    def test_get_error_context_data_error(self):
        """Test getting context for data errors."""
        error = DataError("statement", "params", "orig")
        context = DatabaseErrorHandler.get_error_context(error)
        
        assert context["error_type"] == "DataError"
        assert context["is_data_error"] is True
        assert context["suggested_action"] == "Check data types and value formats"
    
    def test_get_error_context_with_postgres_code(self):
        """Test getting context for errors with PostgreSQL error codes."""
        error = MagicMock()
        error.pgcode = "23505"  # Unique violation
        error.sqlstate = "23505"
        
        context = DatabaseErrorHandler.get_error_context(error)
        
        assert context["postgres_error_code"] == "23505"
        assert context["sql_state"] == "23505"
    
    def test_format_error_for_client_connection_error(self):
        """Test formatting connection errors for client."""
        error = ConnectionFailureError("Connection failed")
        formatted = DatabaseErrorHandler.format_error_for_client(error)
        
        assert formatted["error"] == "Database connection failed"
        assert formatted["type"] == "database_error"
        assert formatted["message"] == "Unable to connect to database. Please try again later."
        assert "details" not in formatted
    
    def test_format_error_for_client_with_details(self):
        """Test formatting errors for client with details."""
        error = IntegrityError("statement", "params", "orig")
        formatted = DatabaseErrorHandler.format_error_for_client(error, include_details=True)
        
        assert formatted["error"] == "Data integrity violation"
        assert formatted["message"] == "The operation violates data constraints."
        assert "details" in formatted
        assert formatted["details"]["error_type"] == "IntegrityError"
        assert formatted["details"]["suggested_action"] == "Check data constraints and foreign key relationships"
    
    def test_format_error_for_client_timeout_error(self):
        """Test formatting timeout errors for client."""
        error = SQLTimeoutError("statement", "params", "orig")
        formatted = DatabaseErrorHandler.format_error_for_client(error)
        
        assert formatted["error"] == "Database operation timed out"
        assert formatted["message"] == "The operation took too long to complete. Please try again."
    
    def test_format_error_for_client_data_error(self):
        """Test formatting data errors for client."""
        error = AsyncpgDataError("Invalid data")
        formatted = DatabaseErrorHandler.format_error_for_client(error)
        
        assert formatted["error"] == "Invalid data format"
        assert formatted["message"] == "The provided data format is invalid."


class TestGlobalErrorHandler:
    """Test the global error handler instance."""
    
    def test_global_instance_exists(self):
        """Test that global error handler instance exists."""
        assert db_error_handler is not None
        assert isinstance(db_error_handler, DatabaseErrorHandler)
    
    def test_global_instance_methods_work(self):
        """Test that global instance methods work correctly."""
        # Test that we can call methods on the global instance
        context = db_error_handler.get_error_context(Exception("test"))
        assert context["error_type"] == "Exception"
        assert context["error_message"] == "test"