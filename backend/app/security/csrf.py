"""CSRF protection implementation."""
import secrets
import hashlib
import hmac
from typing import Optional
from datetime import datetime, timedelta

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ..core.config import settings


class CSRFProtection:
    """CSRF protection for API endpoints."""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or settings.SECRET_KEY
        self.token_lifetime = timedelta(hours=24)
        self.header_name = "X-CSRF-Token"
        self.cookie_name = "csrf_token"
    
    def generate_token(self, session_id: str) -> str:
        """Generate a CSRF token for a session."""
        timestamp = str(int(datetime.utcnow().timestamp()))
        random_part = secrets.token_urlsafe(32)
        
        # Create token payload
        payload = f"{session_id}:{timestamp}:{random_part}"
        
        # Sign the payload
        signature = hmac.new(
            self.secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"{payload}:{signature}"
    
    def validate_token(self, token: str, session_id: str) -> bool:
        """Validate a CSRF token."""
        if not token:
            return False
        
        try:
            parts = token.split(":")
            if len(parts) != 4:
                return False
            
            token_session_id, timestamp, random_part, signature = parts
            
            # Check session ID matches
            if token_session_id != session_id:
                return False
            
            # Check token hasn't expired
            token_time = datetime.fromtimestamp(int(timestamp))
            if datetime.utcnow() - token_time > self.token_lifetime:
                return False
            
            # Verify signature
            payload = f"{token_session_id}:{timestamp}:{random_part}"
            expected_signature = hmac.new(
                self.secret_key.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except (ValueError, TypeError):
            return False
    
    def get_token_from_request(self, request: Request) -> Optional[str]:
        """Extract CSRF token from request headers or cookies."""
        # Try header first
        token = request.headers.get(self.header_name)
        if token:
            return token
        
        # Try cookie
        return request.cookies.get(self.cookie_name)
    
    def add_token_to_response(self, response: Response, token: str) -> None:
        """Add CSRF token to response."""
        response.set_cookie(
            self.cookie_name,
            token,
            httponly=True,
            secure=settings.ENVIRONMENT == "production",
            samesite="strict",
            max_age=int(self.token_lifetime.total_seconds())
        )
        response.headers[self.header_name] = token


class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware to handle CSRF protection."""
    
    def __init__(self, app, csrf_protection: CSRFProtection = None):
        super().__init__(app)
        self.csrf = csrf_protection or CSRFProtection()
        self.exempt_paths = {
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/health",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
        }
        self.safe_methods = {"GET", "HEAD", "OPTIONS", "TRACE"}
    
    async def dispatch(self, request: Request, call_next):
        """Process request with CSRF protection."""
        # Skip CSRF for exempt paths and safe methods
        if (request.url.path in self.exempt_paths or 
            request.method in self.safe_methods):
            return await call_next(request)
        
        # Get session ID (from JWT or session)
        session_id = self._get_session_id(request)
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Validate CSRF token
        csrf_token = self.csrf.get_token_from_request(request)
        if not self.csrf.validate_token(csrf_token, session_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token validation failed"
            )
        
        response = await call_next(request)
        
        # Generate new token for response if needed
        if request.method == "POST" and response.status_code < 400:
            new_token = self.csrf.generate_token(session_id)
            self.csrf.add_token_to_response(response, new_token)
        
        return response
    
    def _get_session_id(self, request: Request) -> Optional[str]:
        """Extract session ID from request."""
        # Try to get from JWT token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from ..core.auth import decode_access_token
                token = auth_header.split(" ")[1]
                payload = decode_access_token(token)
                return payload.get("sub")  # User ID as session ID
            except:
                pass
        
        # Try to get from session cookie
        return request.cookies.get("session_id")


# Dependency for CSRF protection
csrf_protection = CSRFProtection()


def get_csrf_token(request: Request) -> str:
    """Dependency to get CSRF token for current session."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session required"
        )
    
    return csrf_protection.generate_token(session_id)