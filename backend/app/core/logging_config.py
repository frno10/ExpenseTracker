"""
Structured logging configuration with correlation IDs and OpenTelemetry integration.
"""
import json
import logging
import sys
import time
from contextvars import ContextVar
from typing import Any, Dict, Optional
from uuid import uuid4

from opentelemetry import trace

# Context variable for correlation ID
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        correlation_id = correlation_id_var.get()
        record.correlation_id = correlation_id or "unknown"
        
        # Add OpenTelemetry trace information if available
        span = trace.get_current_span()
        if span and span.is_recording():
            span_context = span.get_span_context()
            record.trace_id = format(span_context.trace_id, '032x')
            record.span_id = format(span_context.span_id, '016x')
        else:
            record.trace_id = "unknown"
            record.span_id = "unknown"
        
        return True


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.%fZ', time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, 'correlation_id', 'unknown'),
            "trace_id": getattr(record, 'trace_id', 'unknown'),
            "span_id": getattr(record, 'span_id', 'unknown'),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
                'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                'thread', 'threadName', 'processName', 'process', 'getMessage',
                'exc_info', 'exc_text', 'stack_info', 'correlation_id', 'trace_id', 'span_id'
            }:
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str)


class RequestLoggingFormatter(logging.Formatter):
    """Specialized formatter for HTTP request logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.%fZ', time.gmtime(record.created)),
            "level": record.levelname,
            "type": "http_request",
            "correlation_id": getattr(record, 'correlation_id', 'unknown'),
            "trace_id": getattr(record, 'trace_id', 'unknown'),
            "span_id": getattr(record, 'span_id', 'unknown'),
            "method": getattr(record, 'method', 'unknown'),
            "path": getattr(record, 'path', 'unknown'),
            "status_code": getattr(record, 'status_code', 'unknown'),
            "duration_ms": getattr(record, 'duration_ms', 'unknown'),
            "user_id": getattr(record, 'user_id', 'unknown'),
            "user_agent": getattr(record, 'user_agent', 'unknown'),
            "ip_address": getattr(record, 'ip_address', 'unknown'),
        }
        
        return json.dumps(log_entry, default=str)


def setup_logging(log_level: str = "INFO", use_json: bool = True) -> None:
    """Configure structured logging."""
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    # Add correlation ID filter
    correlation_filter = CorrelationIdFilter()
    console_handler.addFilter(correlation_filter)
    
    # Set formatter
    if use_json:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Create request logger
    request_logger = logging.getLogger("request")
    request_handler = logging.StreamHandler(sys.stdout)
    request_handler.setLevel(numeric_level)
    request_handler.addFilter(correlation_filter)
    request_handler.setFormatter(RequestLoggingFormatter())
    request_logger.addHandler(request_handler)
    request_logger.propagate = False
    
    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """Set correlation ID for the current context."""
    if correlation_id is None:
        correlation_id = str(uuid4())
    correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID."""
    return correlation_id_var.get()


def get_request_logger() -> logging.Logger:
    """Get the request logger."""
    return logging.getLogger("request")


def log_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: Optional[str] = None,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None
) -> None:
    """Log HTTP request with structured data."""
    logger = get_request_logger()
    logger.info(
        f"{method} {path} {status_code} {duration_ms}ms",
        extra={
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "user_id": user_id,
            "user_agent": user_agent,
            "ip_address": ip_address,
        }
    )