"""
Integration tests for database connectivity scenarios.
"""
import pytest
import asyncio
import os
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.exc import OperationalError, TimeoutError as SQLTimeoutError

from app.core.database import (
    initialize_database,
    close_db,
    create_engine_with_retry,
    wait_for_database,
    test_connection,
    get_connection_info,
    log_pool_status
)
from app.core.config import settings


class TestDatabaseConnectivityIntegration:
    """Integration tests for database connectivity scenarios."""
    
    @pytest.mark.asyncio
    async def test_database_initialization_sequence(self):
        """Test complete database initialization sequence."""
        with patch('app.core.database.create_async_engine') as mock_create_engine, \
             patch('app.core.database.test_connection') as mock_test_conn, \
             patch('app.core.database.async_sessionmaker') as mock_sessionmaker:
            
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine
            mock_test_conn.return_value = True
            mock_session_factory = MagicMock()
            mock_sessionmaker.return_value = mock_session_factory
            
            # Test initialization
            await initialize_database()
            
            # Verify engine creation was called
            mock_create_engine.assert_called_once()
            mock_test_conn.assert_called_once_with(mock_engine)
            mock_sessionmaker.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_database_initialization_with_retry(self):
        """Test database initialization with connection retry."""
        with patch('app.core.database.create_async_engine') as mock_create_engine, \
             patch('app.core.database.test_connection') as mock_test_conn, \
             patch('app.core.database.async_sessionmaker') as mock_sessionmaker, \
             patch('asyncio.sleep') as mock_sleep:
            
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine
            
            # First two attempts fail, third succeeds
            mock_test_conn.side_effect = [
                OperationalError("statement", "params", "Connection failed"),
                OperationalError("statement", "params", "Connection failed"),
                True
            ]
            
            mock_session_factory = MagicMock()
            mock_sessionmaker.return_value = mock_session_factory
            
            # Test initialization with retries
            await initialize_database()
            
            # Verify retry logic was used
            assert mock_create_engine.call_count == 3
            assert mock_test_conn.call_count == 3
            assert mock_sleep.call_count == 2  # Two retry delays
    
    @pytest.mark.asyncio
    async def test_database_initialization_failure_after_max_retries(self):
        """Test database initialization failure after maximum retries."""
        with patch('app.core.database.create_async_engine') as mock_create_engine, \
             patch('app.core.database.test_connection') as mock_test_conn, \
             patch('asyncio.sleep') as mock_sleep:
            
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine
            mock_test_conn.side_effect = OperationalError("statement", "params", "Connection failed")
            
            # Test that initialization fails after max retries
            with pytest.raises(Exception) as exc_info:
                await initialize_database()
            
            assert "Failed to create database engine" in str(exc_info.value)
            # Should try 5 times (default max_retries)
            assert mock_create_engine.call_count == 5
            assert mock_test_conn.call_count == 5
            assert mock_sleep.call_count == 4  # Four retry delays
    
    @pytest.mark.asyncio
    async def test_wait_for_database_success(self):
        """Test waiting for database to become available."""
        with patch('app.core.database.create_engine_with_retry') as mock_create_engine:
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine
            
            # Test successful wait
            await wait_for_database(max_wait_time=10)
            
            mock_create_engine.assert_called_once()
            mock_engine.dispose.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_wait_for_database_timeout(self):
        """Test waiting for database timeout."""
        with patch('app.core.database.create_engine_with_retry') as mock_create_engine, \
             patch('time.time') as mock_time, \
             patch('asyncio.sleep') as mock_sleep:
            
            # Mock time to simulate timeout
            mock_time.side_effect = [0, 0, 70]  # Start, first check, timeout
            mock_create_engine.side_effect = Exception("Connection failed")
            
            # Test timeout
            with pytest.raises(Exception) as exc_info:
                await wait_for_database(max_wait_time=60)
            
            assert "Database did not become available" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_connection_test_with_additional_queries(self):
        """Test connection testing with additional database queries."""
        # Create a mock engine that supports async context manager
        class MockEngine:
            def begin(self):
                return MockConnection()
        
        class MockConnection:
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
            
            async def execute(self, query):
                return MockResult()
        
        class MockResult:
            async def fetchone(self):
                return (1,)
        
        mock_engine = MockEngine()
        result = await test_connection(mock_engine)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_connection_test_failure(self):
        """Test connection test failure scenarios."""
        class MockEngine:
            def begin(self):
                raise OperationalError("statement", "params", "Connection failed")
        
        mock_engine = MockEngine()
        
        with pytest.raises(OperationalError):
            await test_connection(mock_engine)
    
    def test_get_connection_info_structure(self):
        """Test connection info returns expected structure."""
        info = get_connection_info()
        
        # Verify required fields are present
        required_fields = [
            'database_host', 'database_port', 'database_name', 'database_user',
            'is_render', 'max_retries', 'retry_delay', 'connection_timeout',
            'engine_initialized', 'session_factory_initialized'
        ]
        
        for field in required_fields:
            assert field in info
        
        # Verify data types
        assert isinstance(info['database_port'], int)
        assert isinstance(info['is_render'], bool)
        assert isinstance(info['max_retries'], int)
        assert isinstance(info['retry_delay'], (int, float))
        assert isinstance(info['connection_timeout'], int)
        assert isinstance(info['engine_initialized'], bool)
        assert isinstance(info['session_factory_initialized'], bool)
    
    @pytest.mark.asyncio
    async def test_log_pool_status_without_engine(self):
        """Test logging pool status when engine is not initialized."""
        with patch('app.core.database.engine', None), \
             patch('app.core.database.logger') as mock_logger:
            
            await log_pool_status()
            
            mock_logger.warning.assert_called_with("Cannot get pool status - engine not initialized")
    
    @pytest.mark.asyncio
    async def test_log_pool_status_with_engine(self):
        """Test logging pool status when engine is initialized."""
        mock_engine = MagicMock()
        mock_pool = MagicMock()
        mock_engine.pool = mock_pool
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 8
        mock_pool.checkedout.return_value = 2
        mock_pool.overflow.return_value = 0
        
        with patch('app.core.database.engine', mock_engine), \
             patch('app.core.database.db_error_handler') as mock_handler:
            
            await log_pool_status()
            
            mock_handler.log_pool_status.assert_called_once()
            call_args = mock_handler.log_pool_status.call_args[0][0]
            assert call_args['engine_initialized'] is True
            assert 'pool_class' in call_args
    
    @pytest.mark.asyncio
    async def test_close_db_with_initialized_engine(self):
        """Test closing database with initialized engine."""
        mock_engine = AsyncMock()
        
        with patch('app.core.database.engine', mock_engine), \
             patch('app.core.database.AsyncSessionLocal', MagicMock()):
            
            await close_db()
            
            mock_engine.dispose.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_db_without_initialized_engine(self):
        """Test closing database without initialized engine."""
        with patch('app.core.database.engine', None), \
             patch('app.core.database.logger') as mock_logger:
            
            await close_db()
            
            mock_logger.warning.assert_called_with("Database engine was not initialized, nothing to close")


class TestDatabaseStartupSequence:
    """Test complete database startup sequence scenarios."""
    
    @pytest.mark.asyncio
    async def test_successful_startup_sequence(self):
        """Test successful complete startup sequence."""
        with patch('app.core.database.wait_for_database') as mock_wait, \
             patch('app.core.database.create_engine_with_retry') as mock_create_engine, \
             patch('app.core.database.async_sessionmaker') as mock_sessionmaker:
            
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine
            mock_session_factory = MagicMock()
            mock_sessionmaker.return_value = mock_session_factory
            
            # Test complete startup
            await initialize_database()
            
            # Verify sequence
            mock_wait.assert_called_once()
            mock_create_engine.assert_called_once()
            mock_sessionmaker.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_startup_sequence_with_database_wait_failure(self):
        """Test startup sequence when database wait fails."""
        with patch('app.core.database.wait_for_database') as mock_wait:
            mock_wait.side_effect = Exception("Database not available")
            
            # Test that startup fails when database wait fails
            with pytest.raises(Exception) as exc_info:
                await initialize_database()
            
            assert "Database not available" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_startup_sequence_with_engine_creation_failure(self):
        """Test startup sequence when engine creation fails."""
        with patch('app.core.database.wait_for_database') as mock_wait, \
             patch('app.core.database.create_engine_with_retry') as mock_create_engine:
            
            mock_create_engine.side_effect = Exception("Engine creation failed")
            
            # Test that startup fails when engine creation fails
            with pytest.raises(Exception) as exc_info:
                await initialize_database()
            
            assert "Engine creation failed" in str(exc_info.value)


class TestDatabaseErrorScenarios:
    """Test various database error scenarios."""
    
    @pytest.mark.asyncio
    async def test_network_unreachable_error(self):
        """Test handling of network unreachable errors."""
        with patch('app.core.database.create_async_engine') as mock_create_engine, \
             patch('app.core.database.test_connection') as mock_test_conn, \
             patch('asyncio.sleep') as mock_sleep:
            
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine
            
            # Simulate network unreachable error
            network_error = OSError("[Errno 101] Network is unreachable")
            mock_test_conn.side_effect = network_error
            
            with pytest.raises(Exception) as exc_info:
                await create_engine_with_retry()
            
            assert "Failed to create database engine" in str(exc_info.value)
            assert mock_create_engine.call_count == 5  # Max retries
    
    @pytest.mark.asyncio
    async def test_connection_timeout_error(self):
        """Test handling of connection timeout errors."""
        with patch('app.core.database.create_async_engine') as mock_create_engine, \
             patch('app.core.database.test_connection') as mock_test_conn, \
             patch('asyncio.sleep') as mock_sleep:
            
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine
            
            # Simulate timeout error
            timeout_error = SQLTimeoutError("statement", "params", "Connection timeout")
            mock_test_conn.side_effect = timeout_error
            
            with pytest.raises(Exception) as exc_info:
                await create_engine_with_retry()
            
            assert "Failed to create database engine" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_intermittent_connection_issues(self):
        """Test handling of intermittent connection issues."""
        with patch('app.core.database.create_async_engine') as mock_create_engine, \
             patch('app.core.database.test_connection') as mock_test_conn, \
             patch('asyncio.sleep') as mock_sleep:
            
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine
            
            # Simulate intermittent failures (fail, fail, succeed)
            mock_test_conn.side_effect = [
                OperationalError("statement", "params", "Connection failed"),
                OperationalError("statement", "params", "Connection failed"),
                True  # Success on third attempt
            ]
            
            # Should succeed after retries
            result = await create_engine_with_retry()
            assert result == mock_engine
            assert mock_test_conn.call_count == 3


class TestRenderEnvironmentScenarios:
    """Test scenarios specific to Render deployment environment."""
    
    @pytest.mark.asyncio
    async def test_render_database_startup_delay(self):
        """Test handling of Render database startup delays."""
        with patch('app.core.database.create_engine_with_retry') as mock_create_engine, \
             patch('asyncio.sleep') as mock_sleep:
            
            mock_engine = AsyncMock()
            
            # Simulate database not ready initially, then ready
            mock_create_engine.side_effect = [
                Exception("Connection failed"),
                Exception("Connection failed"),
                mock_engine  # Success on third attempt
            ]
            
            # Test wait for database with retries
            await wait_for_database(max_wait_time=30)
            
            assert mock_create_engine.call_count == 3
            assert mock_sleep.call_count == 2
            mock_engine.dispose.assert_called_once()
    
    def test_render_environment_detection(self):
        """Test detection of Render environment."""
        info = get_connection_info()
        
        # Should have render detection info
        assert 'is_render' in info
        assert isinstance(info['is_render'], bool)
    
    @pytest.mark.asyncio
    async def test_render_database_url_format(self):
        """Test handling of Render database URL format."""
        render_db_url = "postgresql://user:pass@host.render.com:5432/dbname"
        
        with patch.object(settings, 'database_url', render_db_url):
            db_config = settings.get_database_config()
            
            assert db_config.host == "host.render.com"
            assert db_config.port == 5432
            assert db_config.database == "dbname"
            assert db_config.username == "user"