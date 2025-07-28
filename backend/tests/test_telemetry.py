"""
Tests for OpenTelemetry observability functionality.
"""
import pytest
from unittest.mock import Mock, patch
from opentelemetry import trace, metrics

from app.core.telemetry import (
    TelemetryConfig,
    get_tracer,
    get_meter,
    record_request_metrics,
    record_database_metrics,
    record_error_metrics,
    telemetry
)
from app.core.logging_config import (
    set_correlation_id,
    get_correlation_id,
    CorrelationIdFilter,
    StructuredFormatter
)


class TestTelemetryConfig:
    """Test telemetry configuration."""
    
    def test_setup_resource(self):
        """Test resource setup."""
        config = TelemetryConfig()
        resource = config.setup_resource()
        
        assert resource.attributes["service.name"] == "expense-tracker-api"
        assert resource.attributes["service.version"] == "1.0.0"
        assert resource.attributes["service.namespace"] == "expense-tracker"
        assert "deployment.environment" in resource.attributes
    
    @patch('app.core.telemetry.JaegerExporter')
    @patch('app.core.telemetry.BatchSpanProcessor')
    def test_setup_tracing(self, mock_processor, mock_exporter):
        """Test tracing setup."""
        config = TelemetryConfig()
        config.setup_tracing()
        
        assert config.tracer_provider is not None
        assert config.tracer is not None
        mock_exporter.assert_called_once()
        mock_processor.assert_called_once()
    
    @patch('app.core.telemetry.PrometheusMetricReader')
    @patch('app.core.telemetry.start_http_server')
    def test_setup_metrics(self, mock_server, mock_reader):
        """Test metrics setup."""
        config = TelemetryConfig()
        config.setup_metrics()
        
        assert config.meter_provider is not None
        assert config.meter is not None
        assert config.request_counter is not None
        assert config.request_duration is not None
        assert config.database_query_counter is not None
        assert config.database_query_duration is not None
        assert config.error_counter is not None
        
        mock_reader.assert_called_once()
        mock_server.assert_called_once()
    
    @patch('app.core.telemetry.FastAPIInstrumentor')
    @patch('app.core.telemetry.SQLAlchemyInstrumentor')
    @patch('app.core.telemetry.AsyncPGInstrumentor')
    @patch('app.core.telemetry.RequestsInstrumentor')
    def test_setup_instrumentation(self, mock_requests, mock_asyncpg, mock_sqlalchemy, mock_fastapi):
        """Test instrumentation setup."""
        config = TelemetryConfig()
        mock_app = Mock()
        
        config.setup_instrumentation(mock_app)
        
        mock_fastapi.instrument_app.assert_called_once_with(mock_app)
        mock_sqlalchemy.return_value.instrument.assert_called_once()
        mock_asyncpg.return_value.instrument.assert_called_once()
        mock_requests.return_value.instrument.assert_called_once()


class TestTelemetryFunctions:
    """Test telemetry utility functions."""
    
    def test_get_tracer_not_initialized(self):
        """Test get_tracer when not initialized."""
        # Reset telemetry state
        telemetry.tracer = None
        
        with pytest.raises(RuntimeError, match="Telemetry not initialized"):
            get_tracer()
    
    def test_get_meter_not_initialized(self):
        """Test get_meter when not initialized."""
        # Reset telemetry state
        telemetry.meter = None
        
        with pytest.raises(RuntimeError, match="Telemetry not initialized"):
            get_meter()
    
    def test_record_request_metrics(self):
        """Test recording request metrics."""
        # Mock telemetry components
        telemetry.request_counter = Mock()
        telemetry.request_duration = Mock()
        
        record_request_metrics("GET", "/api/expenses", 200, 0.5)
        
        expected_attributes = {
            "method": "GET",
            "endpoint": "/api/expenses",
            "status_code": "200"
        }
        
        telemetry.request_counter.add.assert_called_once_with(1, expected_attributes)
        telemetry.request_duration.record.assert_called_once_with(0.5, expected_attributes)
    
    def test_record_database_metrics(self):
        """Test recording database metrics."""
        # Mock telemetry components
        telemetry.database_query_counter = Mock()
        telemetry.database_query_duration = Mock()
        
        record_database_metrics("select", "expenses", 0.1)
        
        expected_attributes = {
            "operation": "select",
            "table": "expenses"
        }
        
        telemetry.database_query_counter.add.assert_called_once_with(1, expected_attributes)
        telemetry.database_query_duration.record.assert_called_once_with(0.1, expected_attributes)
    
    def test_record_error_metrics(self):
        """Test recording error metrics."""
        # Mock telemetry components
        telemetry.error_counter = Mock()
        
        record_error_metrics("ValueError", "/api/expenses")
        
        expected_attributes = {
            "error_type": "ValueError",
            "endpoint": "/api/expenses"
        }
        
        telemetry.error_counter.add.assert_called_once_with(1, expected_attributes)


class TestLoggingConfig:
    """Test logging configuration."""
    
    def test_correlation_id_context(self):
        """Test correlation ID context management."""
        # Initially no correlation ID
        assert get_correlation_id() is None
        
        # Set correlation ID
        correlation_id = set_correlation_id("test-123")
        assert correlation_id == "test-123"
        assert get_correlation_id() == "test-123"
        
        # Set custom correlation ID
        custom_id = set_correlation_id("custom-456")
        assert custom_id == "custom-456"
        assert get_correlation_id() == "custom-456"
    
    def test_correlation_id_filter(self):
        """Test correlation ID filter."""
        import logging
        
        # Create mock log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None
        )
        
        # Set correlation ID
        set_correlation_id("test-filter-123")
        
        # Apply filter
        filter_obj = CorrelationIdFilter()
        result = filter_obj.filter(record)
        
        assert result is True
        assert record.correlation_id == "test-filter-123"
        assert hasattr(record, 'trace_id')
        assert hasattr(record, 'span_id')
    
    def test_structured_formatter(self):
        """Test structured JSON formatter."""
        import logging
        import json
        
        # Create mock log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Add required attributes
        record.correlation_id = "test-123"
        record.trace_id = "trace-456"
        record.span_id = "span-789"
        
        # Format record
        formatter = StructuredFormatter()
        formatted = formatter.format(record)
        
        # Parse JSON
        log_data = json.loads(formatted)
        
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test.logger"
        assert log_data["message"] == "Test message"
        assert log_data["correlation_id"] == "test-123"
        assert log_data["trace_id"] == "trace-456"
        assert log_data["span_id"] == "span-789"
        assert log_data["module"] == "file"
        assert log_data["line"] == 42
        assert "timestamp" in log_data


@pytest.fixture
def mock_telemetry():
    """Mock telemetry for testing."""
    with patch('app.core.telemetry.telemetry') as mock:
        mock.tracer = Mock()
        mock.meter = Mock()
        mock.request_counter = Mock()
        mock.request_duration = Mock()
        mock.database_query_counter = Mock()
        mock.database_query_duration = Mock()
        mock.error_counter = Mock()
        yield mock


class TestObservabilityIntegration:
    """Test observability integration."""
    
    def test_telemetry_initialization_success(self, mock_telemetry):
        """Test successful telemetry initialization."""
        mock_app = Mock()
        
        # Mock successful initialization
        mock_telemetry.setup_tracing = Mock()
        mock_telemetry.setup_metrics = Mock()
        mock_telemetry.setup_instrumentation = Mock()
        
        mock_telemetry.initialize(mock_app)
        
        mock_telemetry.setup_tracing.assert_called_once()
        mock_telemetry.setup_metrics.assert_called_once()
        mock_telemetry.setup_instrumentation.assert_called_once_with(mock_app)
    
    def test_telemetry_initialization_failure(self, mock_telemetry):
        """Test telemetry initialization failure handling."""
        mock_app = Mock()
        
        # Mock initialization failure
        mock_telemetry.setup_tracing = Mock(side_effect=Exception("Setup failed"))
        
        with pytest.raises(Exception, match="Setup failed"):
            mock_telemetry.initialize(mock_app)


if __name__ == "__main__":
    pytest.main([__file__])