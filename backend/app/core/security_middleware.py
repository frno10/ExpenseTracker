"""
Comprehensive security middleware for the FastAPI application.
"""
import logging
import time
import secrets
from typing import Dict, List, Optional, Set
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
import hashlib
import hmac

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    """
    
    def __init__(self, app, csp_policy: Optional[str] = None):
        super().__init__(app)
        self.csp_policy = csp_policy or (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none';"
        )
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        security_headers = {
            # Prevent XSS attacks
            "X-XSS-Protection": "1; mode=block",
            
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # Content Security Policy
            "Content-Security-Policy": self.csp_policy,
            
            # Strict Transport Security (HTTPS only)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            
            # Referrer Policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions Policy
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            
            # Remove server information
            "Server": "ExpenseTracker/1.0",
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection middleware using double-submit cookie pattern.
    """
    
    def __init__(self, app, secret_key: str, cookie_name: str = "csrf_token", header_name: str = "X-CSRF-Token"):
        super().__init__(app)
        self.secret_key = secret_key.encode()
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.safe_methods = {"GET", "HEAD", "OPTIONS", "TRACE"}
    
    def generate_csrf_token(self) -> str:
        """Generate a CSRF token."""
        token = secrets.token_urlsafe(32)
        signature = hmac.new(self.secret_key, token.encode(), hashlib.sha256).hexdigest()
        return f"{token}.{signature}"
    
    def validate_csrf_token(self, token: str) -> bool:
        """Validate a CSRF token."""
        try:
            token_part, signature = token.rsplit('.', 1)
            expected_signature = hmac.new(self.secret_key, token_part.encode(), hashlib.sha256).hexdigest()
            return hmac.compare_digest(signature, expected_signature)
        except (ValueError, AttributeError):
            return False
    
    async def dispatch(self, request: Request, call_next):
        # Skip CSRF protection for safe methods and WebSocket connections
        if request.method in self.safe_methods or request.url.path.startswith("/api/ws"):
            response = await call_next(request)
            
            # Set CSRF token cookie for safe methods
            if request.method == "GET" and not request.cookies.get(self.cookie_name):
                csrf_token = self.generate_csrf_token()
                response.set_cookie(
                    self.cookie_name,
                    csrf_token,
                    httponly=True,
                    secure=True,
                    samesite="strict"
                )
            
            return response
        
        # Check CSRF token for unsafe methods
        cookie_token = request.cookies.get(self.cookie_name)
        header_token = request.headers.get(self.header_name)
        
        if not cookie_token or not header_token:
            logger.warning(f"CSRF token missing for {request.method} {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token missing"}
            )
        
        if cookie_token != header_token or not self.validate_csrf_token(cookie_token):
            logger.warning(f"Invalid CSRF token for {request.method} {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Invalid CSRF token"}
            )
        
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware to prevent abuse.
    """
    
    def __init__(self, app, requests_per_minute: int = 60, burst_limit: int = 10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.request_counts: Dict[str, List[float]] = {}
        self.burst_counts: Dict[str, int] = {}
        self.last_cleanup = time.time()
    
    def get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Use X-Forwarded-For if behind proxy, otherwise use client IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        # Include user ID if authenticated
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"{client_ip}:{user_id}"
        
        return client_ip
    
    def cleanup_old_requests(self):
        """Clean up old request records."""
        current_time = time.time()
        if current_time - self.last_cleanup > 60:  # Cleanup every minute
            cutoff_time = current_time - 60
            
            for client_id in list(self.request_counts.keys()):
                self.request_counts[client_id] = [
                    timestamp for timestamp in self.request_counts[client_id]
                    if timestamp > cutoff_time
                ]
                
                if not self.request_counts[client_id]:
                    del self.request_counts[client_id]
                    self.burst_counts.pop(client_id, None)
            
            self.last_cleanup = current_time
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and static files
        if request.url.path in ["/health", "/metrics"] or request.url.path.startswith("/static"):
            return await call_next(request)
        
        client_id = self.get_client_id(request)
        current_time = time.time()
        
        # Cleanup old requests periodically
        self.cleanup_old_requests()
        
        # Initialize client records
        if client_id not in self.request_counts:
            self.request_counts[client_id] = []
            self.burst_counts[client_id] = 0
        
        # Check burst limit (requests in last 10 seconds)
        recent_requests = [
            timestamp for timestamp in self.request_counts[client_id]
            if timestamp > current_time - 10
        ]
        
        if len(recent_requests) >= self.burst_limit:
            logger.warning(f"Burst rate limit exceeded for client {client_id}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded (burst)"},
                headers={"Retry-After": "10"}
            )
        
        # Check per-minute limit
        minute_requests = [
            timestamp for timestamp in self.request_counts[client_id]
            if timestamp > current_time - 60
        ]
        
        if len(minute_requests) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for client {client_id}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": "60"}
            )
        
        # Record this request
        self.request_counts[client_id].append(current_time)
        
        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(self.requests_per_minute - len(minute_requests) - 1)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + 60))
        
        return response


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate and sanitize request inputs.
    """
    
    def __init__(self, app, max_content_length: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_content_length = max_content_length
        self.suspicious_patterns = [
            # SQL injection patterns
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)",
            r"(--|#|/\*|\*/)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            
            # XSS patterns
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"vbscript:",
            r"onload\s*=",
            r"onerror\s*=",
            
            # Path traversal
            r"\.\./",
            r"\.\.\\",
            
            # Command injection
            r"[;&|`$]",
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_content_length:
            logger.warning(f"Request too large: {content_length} bytes from {request.client}")
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Request too large"}
            )
        
        # Validate query parameters
        for key, value in request.query_params.items():
            if self._contains_suspicious_content(f"{key}={value}"):
                logger.warning(f"Suspicious query parameter detected: {key}={value[:100]}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid request parameters"}
                )
        
        # Validate headers
        for key, value in request.headers.items():
            if self._contains_suspicious_content(f"{key}: {value}"):
                logger.warning(f"Suspicious header detected: {key}: {value[:100]}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid request headers"}
                )
        
        return await call_next(request)
    
    def _contains_suspicious_content(self, content: str) -> bool:
        """Check if content contains suspicious patterns."""
        import re
        
        for pattern in self.suspicious_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        
        return False


class SessionSecurityMiddleware(BaseHTTPMiddleware):
    """
    Enhanced session security middleware.
    """
    
    def __init__(self, app, session_timeout: int = 3600):  # 1 hour default
        super().__init__(app)
        self.session_timeout = session_timeout
        self.active_sessions: Dict[str, Dict] = {}
    
    async def dispatch(self, request: Request, call_next):
        session_id = request.cookies.get("session_id")
        
        if session_id:
            session_data = self.active_sessions.get(session_id)
            
            if session_data:
                # Check session timeout
                if time.time() - session_data["last_activity"] > self.session_timeout:
                    logger.info(f"Session {session_id} expired")
                    del self.active_sessions[session_id]
                    
                    response = JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "Session expired"}
                    )
                    response.delete_cookie("session_id")
                    return response
                
                # Update last activity
                session_data["last_activity"] = time.time()
                
                # Check for session hijacking (IP change)
                client_ip = request.client.host if request.client else "unknown"
                if session_data.get("ip_address") != client_ip:
                    logger.warning(f"Potential session hijacking: {session_id} from {client_ip}")
                    del self.active_sessions[session_id]
                    
                    response = JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "Session security violation"}
                    )
                    response.delete_cookie("session_id")
                    return response
        
        response = await call_next(request)
        
        # Create new session if user authenticated
        if hasattr(request.state, "user_id") and not session_id:
            new_session_id = secrets.token_urlsafe(32)
            self.active_sessions[new_session_id] = {
                "user_id": request.state.user_id,
                "ip_address": request.client.host if request.client else "unknown",
                "created_at": time.time(),
                "last_activity": time.time(),
            }
            
            response.set_cookie(
                "session_id",
                new_session_id,
                httponly=True,
                secure=True,
                samesite="strict",
                max_age=self.session_timeout
            )
        
        return response


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log sensitive operations for audit purposes.
    """
    
    def __init__(self, app, sensitive_paths: Optional[List[str]] = None):
        super().__init__(app)
        self.sensitive_paths = sensitive_paths or [
            "/api/auth/login",
            "/api/auth/logout",
            "/api/auth/register",
            "/api/users",
            "/api/budgets",
            "/api/expenses",
            "/api/import",
        ]
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Check if this is a sensitive operation
        is_sensitive = any(request.url.path.startswith(path) for path in self.sensitive_paths)
        
        if is_sensitive:
            # Log request
            user_id = getattr(request.state, "user_id", "anonymous")
            client_ip = request.client.host if request.client else "unknown"
            
            logger.info(
                f"AUDIT: {request.method} {request.url.path}",
                extra={
                    "event_type": "api_request",
                    "user_id": user_id,
                    "client_ip": client_ip,
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": dict(request.query_params),
                    "user_agent": request.headers.get("user-agent", ""),
                }
            )
        
        response = await call_next(request)
        
        if is_sensitive:
            # Log response
            duration = time.time() - start_time
            
            logger.info(
                f"AUDIT: Response {response.status_code} in {duration:.3f}s",
                extra={
                    "event_type": "api_response",
                    "user_id": getattr(request.state, "user_id", "anonymous"),
                    "status_code": response.status_code,
                    "duration": duration,
                    "path": request.url.path,
                }
            )
        
        return response