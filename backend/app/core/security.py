"""
Security middleware and utilities.
"""
import logging
import time
from typing import Dict, Optional
from uuid import uuid4

from fastapi import Request, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Rate limiter configuration
limiter = Limiter(key_func=get_remote_address)


def get_user_id_for_rate_limit(request: Request) -> str:
    """
    Get user ID for rate limiting.
    Falls back to IP address if user is not authenticated.
    """
    # Try to get user from request state (set by auth middleware)
    user = getattr(request.state, "user", None)
    if user:
        return f"user:{user.id}"
    return get_remote_address(request)

def rate_limit(operation: str, per_minute: int = 60):
    """
    Simple rate limit decorator for development.
    In production, this would use the limiter properly.
    """
    def decorator(func):
        # For development, just return the function without rate limiting
        logger.debug(f"Rate limit decorator applied to {operation}: {per_minute}/min")
        return func
    return decorator
    
    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


# User-aware rate limiter
user_limiter = Limiter(key_func=get_user_id_for_rate_limit)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS header (only for HTTPS)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation IDs to requests for tracing.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
        
        # Add to request state
        request.state.correlation_id = correlation_id
        
        # Process request
        response = await call_next(request)
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all requests for security monitoring.
    """
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        user_id = getattr(getattr(request.state, "user", None), "id", "anonymous")
        
        logger.info(
            f"Request started",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "url": str(request.url),
                "user_id": user_id,
                "user_agent": request.headers.get("user-agent"),
                "remote_addr": get_remote_address(request)
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Log response
            process_time = time.time() - start_time
            logger.info(
                f"Request completed",
                extra={
                    "correlation_id": correlation_id,
                    "status_code": response.status_code,
                    "process_time": process_time,
                    "user_id": user_id
                }
            )
            
            # Add timing header
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            logger.error(
                f"Request failed",
                extra={
                    "correlation_id": correlation_id,
                    "error": str(e),
                    "process_time": process_time,
                    "user_id": user_id
                },
                exc_info=True
            )
            raise


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract user information from JWT tokens.
    
    This doesn't enforce authentication, just extracts user info if available.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Extract user from Authorization header if present
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from app.core.auth import verify_token
                from app.core.database import AsyncSessionLocal
                from app.repositories.user import user_repository
                
                token = auth_header.split(" ")[1]
                payload = await verify_token(token)
                user_id = payload.get("sub")
                
                if user_id:
                    # Get user from database
                    async with AsyncSessionLocal() as db:
                        user = await user_repository.get(db, user_id)
                        if user and user.is_active:
                            request.state.user = user
                            
            except Exception as e:
                # Don't fail the request, just log the error
                logger.debug(f"Failed to extract user from token: {e}")
        
        return await call_next(request)


# Rate limit configurations
class RateLimits:
    """Rate limit configurations for different endpoints."""
    
    # Authentication endpoints
    LOGIN = "5/minute"  # 5 login attempts per minute
    REFRESH = "10/minute"  # 10 token refreshes per minute
    
    # API endpoints
    READ_OPERATIONS = "100/minute"  # 100 read operations per minute
    WRITE_OPERATIONS = "50/minute"  # 50 write operations per minute
    
    # File uploads
    FILE_UPLOAD = "10/minute"  # 10 file uploads per minute
    
    # General API
    GENERAL = "200/minute"  # 200 requests per minute


def setup_rate_limiting(app):
    """
    Set up rate limiting for the FastAPI app.
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Security utilities
def validate_file_upload(filename: str, content_type: str, file_size: int) -> bool:
    """
    Validate file uploads for security.
    
    Args:
        filename: Name of the uploaded file
        content_type: MIME type of the file
        file_size: Size of the file in bytes
        
    Returns:
        True if file is safe to upload
        
    Raises:
        ValueError: If file is not safe
    """
    # Check file size (max 10MB)
    max_size = 10 * 1024 * 1024
    if file_size > max_size:
        raise ValueError(f"File too large. Maximum size is {max_size} bytes")
    
    # Check allowed file types
    allowed_types = {
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "application/pdf",
        "text/csv", "application/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain"
    }
    
    if content_type not in allowed_types:
        raise ValueError(f"File type not allowed: {content_type}")
    
    # Check filename for suspicious patterns
    dangerous_extensions = {".exe", ".bat", ".cmd", ".scr", ".pif", ".com"}
    filename_lower = filename.lower()
    
    for ext in dangerous_extensions:
        if filename_lower.endswith(ext):
            raise ValueError(f"Dangerous file extension: {ext}")
    
    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    import re
    
    # Remove path separators and other dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Ensure filename is not empty
    if not filename:
        filename = "unnamed_file"
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        max_name_length = 255 - len(ext) - 1 if ext else 255
        filename = name[:max_name_length] + ('.' + ext if ext else '')
    
    return filename