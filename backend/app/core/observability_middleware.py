"""
Observability middleware for tracing, metrics, and logging.
"""
import time
from typing import Callable, Optional

from fastapi import Request, Response
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging_config import set_correlation_id, log_request
from app.core.telemetry_simple import record_request_metrics, record_error_metrics


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware for comprehensive observability."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Set correlation ID
        correlation_id = request.headers.get("x-correlation-id")
        correlation_id = set_correlation_id(correlation_id)
        
        # Add correlation ID to response headers
        start_time = time.time()
        
        # Get current span for additional context
        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.route", request.url.path)
            span.set_attribute("correlation_id", correlation_id)
            
            # Add user information if available
            user = getattr(request.state, "user", None)
            if user:
                span.set_attribute("user.id", str(user.id))
                span.set_attribute("user.email", user.email)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            duration_ms = duration * 1000
            
            # Add correlation ID to response headers
            response.headers["x-correlation-id"] = correlation_id
            
            # Update span with response information
            if span.is_recording():
                span.set_attribute("http.status_code", response.status_code)
                span.set_attribute("http.response_size", len(response.body) if hasattr(response, 'body') else 0)
                
                # Set span status based on HTTP status code
                if response.status_code >= 400:
                    span.set_status(trace.Status(trace.StatusCode.ERROR, f"HTTP {response.status_code}"))
                else:
                    span.set_status(trace.Status(trace.StatusCode.OK))
            
            # Record metrics
            record_request_metrics(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                duration=duration
            )
            
            # Log request
            user_id = None
            user = getattr(request.state, "user", None)
            if user:
                user_id = str(user.id)
            
            log_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                user_agent=request.headers.get("user-agent"),
                ip_address=self._get_client_ip(request)
            )
            
            return response
            
        except Exception as e:
            # Calculate duration for error case
            duration = time.time() - start_time
            duration_ms = duration * 1000
            
            # Update span with error information
            if span.is_recording():
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.record_exception(e)
            
            # Record error metrics
            record_error_metrics(
                error_type=type(e).__name__,
                endpoint=request.url.path
            )
            
            # Log error request
            user_id = None
            user = getattr(request.state, "user", None)
            if user:
                user_id = str(user.id)
            
            log_request(
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_ms=duration_ms,
                user_id=user_id,
                user_agent=request.headers.get("user-agent"),
                ip_address=self._get_client_ip(request)
            )
            
            # Re-raise the exception
            raise
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to client host
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return None


class DatabaseObservabilityMixin:
    """Mixin for adding observability to database operations."""
    
    def _trace_database_operation(self, operation: str, table: str):
        """Create a span for database operations."""
        tracer = trace.get_tracer(__name__)
        return tracer.start_span(
            name=f"db.{operation}",
            attributes={
                "db.operation": operation,
                "db.table": table,
                "db.system": "postgresql"
            }
        )
    
    async def _execute_with_observability(self, operation: str, table: str, func, *args, **kwargs):
        """Execute database operation with observability."""
        start_time = time.time()
        
        with self._trace_database_operation(operation, table):
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Record successful database metrics
                from app.core.telemetry import record_database_metrics
                record_database_metrics(operation, table, duration)
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Record database error metrics
                from app.core.telemetry import record_database_metrics
                record_database_metrics(f"{operation}_error", table, duration)
                
                # Add error information to current span
                span = trace.get_current_span()
                if span.is_recording():
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                
                raise