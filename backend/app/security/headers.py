"""Security headers middleware."""
from typing import Dict, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..core.config import settings


class SecurityHeaders:
    """Security headers configuration."""
    
    def __init__(self):
        self.headers = self._get_security_headers()
    
    def _get_security_headers(self) -> Dict[str, str]:
        """Get security headers configuration."""
        headers = {
            # Prevent XSS attacks
            "X-XSS-Protection": "1; mode=block",
            
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions policy
            "Permissions-Policy": (
                "geolocation=(), microphone=(), camera=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=()"
            ),
            
            # Remove server information
            "Server": "ExpenseTracker",
        }
        
        # Content Security Policy
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self'",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        
        if settings.ENVIRONMENT == "development":
            # Allow localhost for development
            csp_directives.extend([
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' localhost:*",
                "connect-src 'self' localhost:* ws://localhost:*",
            ])
        
        headers["Content-Security-Policy"] = "; ".join(csp_directives)
        
        # HSTS (only in production with HTTPS)
        if settings.ENVIRONMENT == "production":
            headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        return headers


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to responses."""
    
    def __init__(self, app):
        super().__init__(app)
        self.security_headers = SecurityHeaders()
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)
        
        # Add security headers
        for header, value in self.security_headers.headers.items():
            response.headers[header] = value
        
        # Add CORS headers if needed
        if self._should_add_cors_headers(request):
            self._add_cors_headers(response, request)
        
        return response
    
    def _should_add_cors_headers(self, request: Request) -> bool:
        """Check if CORS headers should be added."""
        origin = request.headers.get("origin")
        return origin is not None
    
    def _add_cors_headers(self, response: Response, request: Request) -> None:
        """Add CORS headers to response."""
        origin = request.headers.get("origin")
        
        # Check if origin is allowed
        allowed_origins = getattr(settings, "ALLOWED_ORIGINS", ["http://localhost:3000"])
        
        if origin in allowed_origins or settings.ENVIRONMENT == "development":
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = (
                "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            )
            response.headers["Access-Control-Allow-Headers"] = (
                "Content-Type, Authorization, X-CSRF-Token, X-Requested-With"
            )
            response.headers["Access-Control-Max-Age"] = "86400"


def add_security_headers(response: Response) -> Response:
    """Add security headers to a response."""
    security_headers = SecurityHeaders()
    for header, value in security_headers.headers.items():
        response.headers[header] = value
    return response