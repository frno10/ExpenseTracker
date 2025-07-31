"""
Simplified telemetry for development - no complex dependencies.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def setup_telemetry(app_name: str = "expense-tracker"):
    """Simplified telemetry setup for development."""
    logger.info("Telemetry setup skipped for development")
    pass

def record_request_metrics(method: str, endpoint: str, status_code: int, duration: float):
    """Record request metrics - simplified for development."""
    logger.debug(f"Request: {method} {endpoint} - {status_code} ({duration:.3f}s)")

def record_error_metrics(error_type: str, endpoint: str):
    """Record error metrics - simplified for development."""
    logger.warning(f"Error: {error_type} on {endpoint}")

def record_database_metrics(operation: str, table: str, duration: float):
    """Record database metrics - simplified for development."""
    logger.debug(f"DB: {operation} on {table} ({duration:.3f}s)")

def get_tracer(name: str):
    """Get a tracer - simplified for development."""
    return None

def get_meter(name: str):
    """Get a meter - simplified for development."""
    return None