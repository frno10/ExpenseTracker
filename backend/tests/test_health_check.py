"""
Unit tests for health check functionality.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.monitoring.health import (
    HealthChecker,
    HealthCheckResult,
    HealthStatus
)


class TestHealthChecker:
    """Test health checker functionality."""
    
    def test_health_checker_initialization(self):
        """Test health checker initializes with default checks."""
        checker = HealthChecker()
        
        # Verify default checks are registered
        expected_checks = [
            "database", "redis", "disk_space", 
            "memory", "external_apis", "parser_health"
        ]
        
        for check_name in expected_checks:
            assert check_name in checker.checks
    
    def test_register_check(self):
        """Test registering custom health checks."""
        checker = HealthChecker()
        
        async def custom_check():
            return True
        
        checker.register_check("custom", custom_check)
        assert "custom" in checker.checks
        assert checker.checks["custom"] == custom_check
    
    @pytest.mark.asyncio
    async def test_run_check_not_found(self):
        """Test running a non-existent health check."""
        checker = HealthChecker()
        
        result = await checker.run_check("nonexistent")
        
        assert result.name == "nonexistent"
        assert result.status == HealthStatus.UNHEALTHY
        assert "not found" in result.message
    
    @pytest.mark.asyncio
    async def test_run_check_success(self):
        """Test running a successful health check."""
        checker = HealthChecker()
        
        async def successful_check():
            return HealthCheckResult(
                name="test",
                status=HealthStatus.HEALTHY,
                response_time_ms=0,
                message="Test successful"
            )
        
        checker.register_check("test", successful_check)
        result = await checker.run_check("test")
        
        assert result.name == "test"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "Test successful"
        assert result.response_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_run_check_boolean_result(self):
        """Test running a health check that returns boolean."""
        checker = HealthChecker()
        
        async def boolean_check():
            return True
        
        checker.register_check("boolean", boolean_check)
        result = await checker.run_check("boolean")
        
        assert result.name == "boolean"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "OK"
    
    @pytest.mark.asyncio
    async def test_run_check_exception(self):
        """Test running a health check that raises an exception."""
        checker = HealthChecker()
        
        async def failing_check():
            raise Exception("Test error")
        
        checker.register_check("failing", failing_check)
        result = await checker.run_check("failing")
        
        assert result.name == "failing"
        assert result.status == HealthStatus.UNHEALTHY
        assert "Test error" in result.message
    
    @pytest.mark.asyncio
    async def test_run_all_checks(self):
        """Test running all health checks."""
        checker = HealthChecker()
        
        # Clear default checks for this test
        checker.checks = {}
        
        async def check1():
            return True
        
        async def check2():
            return False
        
        checker.register_check("check1", check1)
        checker.register_check("check2", check2)
        
        results = await checker.run_all_checks()
        
        assert len(results) == 2
        assert "check1" in results
        assert "check2" in results
        assert results["check1"].status == HealthStatus.HEALTHY
        assert results["check2"].status == HealthStatus.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_get_overall_health_healthy(self):
        """Test overall health when all checks are healthy."""
        checker = HealthChecker()
        
        # Mock run_all_checks to return healthy results
        with patch.object(checker, 'run_all_checks') as mock_run_all:
            mock_run_all.return_value = {
                "check1": HealthCheckResult(
                    name="check1",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=100,
                    message="OK"
                ),
                "check2": HealthCheckResult(
                    name="check2",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=200,
                    message="OK"
                )
            }
            
            result = await checker.get_overall_health()
            
            assert result["status"] == "healthy"
            assert result["average_response_time_ms"] == 150.0
            assert len(result["checks"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_overall_health_degraded(self):
        """Test overall health when some checks are degraded."""
        checker = HealthChecker()
        
        with patch.object(checker, 'run_all_checks') as mock_run_all:
            mock_run_all.return_value = {
                "check1": HealthCheckResult(
                    name="check1",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=100,
                    message="OK"
                ),
                "check2": HealthCheckResult(
                    name="check2",
                    status=HealthStatus.DEGRADED,
                    response_time_ms=200,
                    message="Slow"
                )
            }
            
            result = await checker.get_overall_health()
            
            assert result["status"] == "degraded"
    
    @pytest.mark.asyncio
    async def test_get_overall_health_unhealthy(self):
        """Test overall health when some checks are unhealthy."""
        checker = HealthChecker()
        
        with patch.object(checker, 'run_all_checks') as mock_run_all:
            mock_run_all.return_value = {
                "check1": HealthCheckResult(
                    name="check1",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=100,
                    message="OK"
                ),
                "check2": HealthCheckResult(
                    name="check2",
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=200,
                    message="Failed"
                )
            }
            
            result = await checker.get_overall_health()
            
            assert result["status"] == "unhealthy"


class TestDatabaseHealthCheck:
    """Test database-specific health check functionality."""
    
    @pytest.mark.asyncio
    @patch('app.monitoring.health.engine', None)
    async def test_check_database_not_initialized(self):
        """Test database health check when engine is not initialized."""
        checker = HealthChecker()
        
        result = await checker.check_database()
        
        assert result.name == "database"
        assert result.status == HealthStatus.UNHEALTHY
        assert "not initialized" in result.message
    
    @pytest.mark.asyncio
    @patch('app.monitoring.health.engine')
    @patch('app.monitoring.health.test_connection')
    @patch('app.monitoring.health.get_db')
    async def test_check_database_success(self, mock_get_db, mock_test_conn, mock_engine):
        """Test successful database health check."""
        # Mock database session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.fetchone.return_value = (5,)  # 5 tables
        mock_session.execute.return_value = mock_result
        
        # Mock get_db to yield the session
        async def mock_db_generator():
            yield mock_session
        
        mock_get_db.return_value = mock_db_generator()
        mock_test_conn.return_value = True
        
        checker = HealthChecker()
        result = await checker.check_database()
        
        assert result.name == "database"
        assert result.status == HealthStatus.HEALTHY
        assert "healthy" in result.message
        assert result.details["table_count"] == 5
    
    @pytest.mark.asyncio
    @patch('app.monitoring.health.engine')
    @patch('app.monitoring.health.test_connection')
    async def test_check_database_connection_failure(self, mock_test_conn, mock_engine):
        """Test database health check when connection fails."""
        mock_test_conn.side_effect = Exception("Connection failed")
        
        checker = HealthChecker()
        result = await checker.check_database()
        
        assert result.name == "database"
        assert result.status == HealthStatus.UNHEALTHY
        assert "Connection failed" in result.message


class TestHealthCheckResult:
    """Test HealthCheckResult data class."""
    
    def test_health_check_result_creation(self):
        """Test creating a health check result."""
        result = HealthCheckResult(
            name="test",
            status=HealthStatus.HEALTHY,
            response_time_ms=100.5,
            message="All good"
        )
        
        assert result.name == "test"
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time_ms == 100.5
        assert result.message == "All good"
        assert result.details is None
        assert isinstance(result.timestamp, datetime)
    
    def test_health_check_result_with_details(self):
        """Test creating a health check result with details."""
        details = {"key": "value", "count": 42}
        
        result = HealthCheckResult(
            name="test",
            status=HealthStatus.DEGRADED,
            response_time_ms=200.0,
            message="Slow response",
            details=details
        )
        
        assert result.details == details
    
    def test_health_check_result_custom_timestamp(self):
        """Test creating a health check result with custom timestamp."""
        custom_time = datetime(2023, 1, 1, 12, 0, 0)
        
        result = HealthCheckResult(
            name="test",
            status=HealthStatus.UNHEALTHY,
            response_time_ms=0,
            message="Failed",
            timestamp=custom_time
        )
        
        assert result.timestamp == custom_time