"""
Unit tests for database connection management.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import (
    create_engine_with_retry,
    test_connection,
    wait_for_database,
    get_connection_info,
    initialize_database,
    close_db,
    get_db,
    init_db,
    get_db_session
)


class TestDatabaseConnection:
    """Test database connection functionality."""
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test successful database connection test."""
        # Create a mock that properly handles async context manager
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
    async def test_test_connection_failure(self):
        """Test database connection test failure."""
        mock_engine = AsyncMock()
        mock_engine.begin.side_effect = SQLAlchemyError("Connection failed")
        
        with pytest.raises(Exception):
            await test_connection(mock_engine)
    
    @pytest.mark.asyncio
    @patch('app.core.database.create_async_engine')
    @patch('app.core.database.test_connection')
    async def test_create_engine_with_retry_success_first_attempt(self, mock_test_conn, mock_create_engine):
        """Test successful engine creation on first attempt."""
        mock_engine = AsyncMock()
        mock_create_engine.return_value = mock_engine
        mock_test_conn.return_value = True
        
        result = await create_engine_with_retry()
        
        assert result == mock_engine
        mock_create_engine.assert_called_once()
        mock_test_conn.assert_called_once_with(mock_engine)
    
    @pytest.mark.asyncio
    @patch('app.core.database.create_async_engine')
    @patch('app.core.database.test_connection')
    @patch('asyncio.sleep')
    async def test_create_engine_with_retry_success_after_retry(self, mock_sleep, mock_test_conn, mock_create_engine):
        """Test successful engine creation after retry."""
        mock_engine = AsyncMock()
        mock_create_engine.return_value = mock_engine
        
        # First attempt fails, second succeeds
        mock_test_conn.side_effect = [Exception("Connection failed"), True]
        
        result = await create_engine_with_retry()
        
        assert result == mock_engine
        assert mock_create_engine.call_count == 2
        assert mock_test_conn.call_count == 2
        mock_sleep.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.core.database.create_async_engine')
    @patch('app.core.database.test_connection')
    @patch('asyncio.sleep')
    async def test_create_engine_with_retry_all_attempts_fail(self, mock_sleep, mock_test_conn, mock_create_engine):
        """Test engine creation failure after all retry attempts."""
        mock_engine = AsyncMock()
        mock_create_engine.return_value = mock_engine
        mock_test_conn.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception) as exc_info:
            await create_engine_with_retry()
        
        assert "Failed to create database engine after" in str(exc_info.value)
        assert mock_create_engine.call_count == 5  # Default max_retries
        assert mock_test_conn.call_count == 5
    
    @pytest.mark.asyncio
    @patch('app.core.database.create_engine_with_retry')
    @patch('asyncio.sleep')
    async def test_wait_for_database_success(self, mock_sleep, mock_create_engine):
        """Test successful database waiting."""
        mock_engine = AsyncMock()
        mock_create_engine.return_value = mock_engine
        
        await wait_for_database(max_wait_time=10)
        
        mock_create_engine.assert_called_once()
        mock_engine.dispose.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.core.database.create_engine_with_retry')
    @patch('asyncio.sleep')
    @patch('time.time')
    async def test_wait_for_database_timeout(self, mock_time, mock_sleep, mock_create_engine):
        """Test database waiting timeout."""
        # Mock time to simulate timeout
        mock_time.side_effect = [0, 0, 70]  # Start, first check, timeout
        mock_create_engine.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception) as exc_info:
            await wait_for_database(max_wait_time=60)
        
        assert "Database did not become available" in str(exc_info.value)
    
    def test_get_connection_info(self):
        """Test getting connection information."""
        info = get_connection_info()
        
        assert 'database_host' in info
        assert 'database_port' in info
        assert 'database_name' in info
        assert 'database_user' in info
        assert 'is_render' in info
        assert 'max_retries' in info
        assert 'retry_delay' in info
        assert 'connection_timeout' in info


class TestDatabaseInitialization:
    """Test database initialization and lifecycle."""
    
    @pytest.mark.asyncio
    @patch('app.core.database.wait_for_database')
    @patch('app.core.database.create_engine_with_retry')
    @patch('app.core.database.async_sessionmaker')
    async def test_initialize_database_success(self, mock_sessionmaker, mock_create_engine, mock_wait_db):
        """Test successful database initialization."""
        mock_engine = AsyncMock()
        mock_create_engine.return_value = mock_engine
        mock_session_factory = MagicMock()
        mock_sessionmaker.return_value = mock_session_factory
        
        await initialize_database()
        
        mock_wait_db.assert_called_once()
        mock_create_engine.assert_called_once()
        mock_sessionmaker.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.core.database.wait_for_database')
    async def test_initialize_database_wait_failure(self, mock_wait_db):
        """Test database initialization failure during wait."""
        mock_wait_db.side_effect = Exception("Database not available")
        
        with pytest.raises(Exception):
            await initialize_database()
    
    @pytest.mark.asyncio
    async def test_close_db_with_engine(self):
        """Test closing database with initialized engine."""
        # Mock the global engine
        with patch('app.core.database.engine') as mock_engine:
            mock_engine.dispose = AsyncMock()
            
            await close_db()
            
            mock_engine.dispose.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_db_without_engine(self):
        """Test closing database without initialized engine."""
        # Ensure engine is None
        with patch('app.core.database.engine', None):
            # Should not raise exception
            await close_db()


class TestDatabaseSessions:
    """Test database session management."""
    
    @pytest.mark.asyncio
    async def test_get_db_not_initialized(self):
        """Test get_db when database is not initialized."""
        with patch('app.core.database.AsyncSessionLocal', None):
            with pytest.raises(Exception) as exc_info:
                async for _ in get_db():
                    pass
            assert "Database not initialized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_db_session_error_handling(self):
        """Test get_db error handling during session operations."""
        mock_session = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        
        # Create a proper async context manager mock
        mock_session_context = AsyncMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_factory = MagicMock(return_value=mock_session_context)
        
        # Simulate an error during session usage
        with patch('app.core.database.AsyncSessionLocal', mock_session_factory):
            with pytest.raises(SQLAlchemyError):
                async for session in get_db():
                    raise SQLAlchemyError("Database error")
            
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()
    
    def test_get_db_session_not_initialized(self):
        """Test get_db_session when database is not initialized."""
        with patch('app.core.database.AsyncSessionLocal', None):
            with pytest.raises(Exception) as exc_info:
                get_db_session()
            assert "Database not initialized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_init_db_not_initialized(self):
        """Test init_db when database engine is not initialized."""
        with patch('app.core.database.engine', None):
            with pytest.raises(Exception) as exc_info:
                await init_db()
            assert "Database engine not initialized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @patch('app.core.database.engine')
    async def test_init_db_success(self, mock_engine):
        """Test successful database table initialization."""
        mock_conn = AsyncMock()
        
        # Properly mock the async context manager
        mock_engine.begin.return_value = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.models.Base') as mock_base:
            mock_metadata = MagicMock()
            mock_base.metadata = mock_metadata
            
            await init_db()
            
            mock_conn.run_sync.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.core.database.engine')
    async def test_init_db_failure(self, mock_engine):
        """Test database table initialization failure."""
        mock_engine.begin.side_effect = Exception("Table creation failed")
        
        with pytest.raises(Exception) as exc_info:
            await init_db()
        
        assert "Failed to create database tables" in str(exc_info.value)