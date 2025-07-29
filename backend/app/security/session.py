"""Session management and automatic logout."""
import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import redis.asyncio as redis

from ..core.config import settings
from .audit import audit_logger, AuditEventType, AuditSeverity


class SessionManager:
    """Manage user sessions with automatic expiration."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.session_timeout = timedelta(hours=24)  # Default session timeout
        self.idle_timeout = timedelta(hours=2)      # Idle timeout
        self.max_sessions_per_user = 5              # Maximum concurrent sessions
    
    async def create_session(
        self,
        user_id: str,
        ip_address: str,
        user_agent: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new session."""
        session_id = secrets.token_urlsafe(32)
        
        session_data = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "is_active": True,
            **(additional_data or {})
        }
        
        if self.redis_client:
            # Store in Redis with expiration
            await self.redis_client.setex(
                f"session:{session_id}",
                int(self.session_timeout.total_seconds()),
                json.dumps(session_data)
            )
            
            # Track user sessions
            await self._track_user_session(user_id, session_id)
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        if not self.redis_client:
            return None
        
        session_data = await self.redis_client.get(f"session:{session_id}")
        if not session_data:
            return None
        
        try:
            data = json.loads(session_data)
            
            # Check if session is expired
            last_activity = datetime.fromisoformat(data["last_activity"])
            if datetime.utcnow() - last_activity > self.idle_timeout:
                await self.invalidate_session(session_id)
                return None
            
            return data
        except (json.JSONDecodeError, KeyError, ValueError):
            return None
    
    async def update_session_activity(self, session_id: str) -> bool:
        """Update session last activity timestamp."""
        if not self.redis_client:
            return False
        
        session_data = await self.get_session(session_id)
        if not session_data:
            return False
        
        session_data["last_activity"] = datetime.utcnow().isoformat()
        
        await self.redis_client.setex(
            f"session:{session_id}",
            int(self.session_timeout.total_seconds()),
            json.dumps(session_data)
        )
        
        return True
    
    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session."""
        if not self.redis_client:
            return False
        
        # Get session data before deletion for audit
        session_data = await self.get_session(session_id)
        
        # Delete session
        result = await self.redis_client.delete(f"session:{session_id}")
        
        # Remove from user session tracking
        if session_data:
            user_id = session_data.get("user_id")
            if user_id:
                await self.redis_client.srem(f"user_sessions:{user_id}", session_id)
        
        return bool(result)
    
    async def invalidate_user_sessions(self, user_id: str, except_session: Optional[str] = None) -> int:
        """Invalidate all sessions for a user."""
        if not self.redis_client:
            return 0
        
        session_ids = await self.redis_client.smembers(f"user_sessions:{user_id}")
        count = 0
        
        for session_id in session_ids:
            session_id = session_id.decode() if isinstance(session_id, bytes) else session_id
            
            if except_session and session_id == except_session:
                continue
            
            if await self.invalidate_session(session_id):
                count += 1
        
        return count
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        if not self.redis_client:
            return 0
        
        # This would be called by a background task
        # Redis TTL handles most cleanup, but we can do additional cleanup here
        count = 0
        
        # Get all session keys
        session_keys = await self.redis_client.keys("session:*")
        
        for key in session_keys:
            session_data = await self.redis_client.get(key)
            if not session_data:
                continue
            
            try:
                data = json.loads(session_data)
                last_activity = datetime.fromisoformat(data["last_activity"])
                
                if datetime.utcnow() - last_activity > self.idle_timeout:
                    session_id = key.decode().split(":", 1)[1]
                    await self.invalidate_session(session_id)
                    count += 1
            except (json.JSONDecodeError, KeyError, ValueError):
                # Invalid session data, delete it
                await self.redis_client.delete(key)
                count += 1
        
        return count
    
    async def _track_user_session(self, user_id: str, session_id: str) -> None:
        """Track session for a user."""
        if not self.redis_client:
            return
        
        # Add to user sessions set
        await self.redis_client.sadd(f"user_sessions:{user_id}", session_id)
        
        # Check if user has too many sessions
        session_count = await self.redis_client.scard(f"user_sessions:{user_id}")
        
        if session_count > self.max_sessions_per_user:
            # Get oldest sessions and remove them
            sessions = await self.redis_client.smembers(f"user_sessions:{user_id}")
            session_times = []
            
            for session in sessions:
                session_data = await self.get_session(session.decode())
                if session_data:
                    created_at = datetime.fromisoformat(session_data["created_at"])
                    session_times.append((session.decode(), created_at))
            
            # Sort by creation time and remove oldest
            session_times.sort(key=lambda x: x[1])
            sessions_to_remove = session_times[:-self.max_sessions_per_user]
            
            for session_to_remove, _ in sessions_to_remove:
                await self.invalidate_session(session_to_remove)
    
    async def get_user_sessions(self, user_id: str) -> list:
        """Get all active sessions for a user."""
        if not self.redis_client:
            return []
        
        session_ids = await self.redis_client.smembers(f"user_sessions:{user_id}")
        sessions = []
        
        for session_id in session_ids:
            session_id = session_id.decode() if isinstance(session_id, bytes) else session_id
            session_data = await self.get_session(session_id)
            
            if session_data:
                sessions.append({
                    "session_id": session_id,
                    **session_data
                })
        
        return sessions


class SessionMiddleware(BaseHTTPMiddleware):
    """Middleware to handle session management."""
    
    def __init__(self, app, session_manager: SessionManager):
        super().__init__(app)
        self.session_manager = session_manager
        self.exempt_paths = {
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
        }
    
    async def dispatch(self, request: Request, call_next):
        """Handle session for each request."""
        # Skip session handling for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        # Get session ID from cookie or header
        session_id = self._get_session_id(request)
        
        if session_id:
            # Validate and update session
            session_data = await self.session_manager.get_session(session_id)
            
            if session_data:
                # Update last activity
                await self.session_manager.update_session_activity(session_id)
                
                # Add session data to request state
                request.state.session_id = session_id
                request.state.session_data = session_data
                request.state.user_id = session_data.get("user_id")
            else:
                # Invalid session
                request.state.session_id = None
                request.state.session_data = None
                request.state.user_id = None
        
        response = await call_next(request)
        
        # Handle session in response
        if hasattr(request.state, "session_id") and request.state.session_id:
            # Refresh session cookie
            response.set_cookie(
                "session_id",
                request.state.session_id,
                httponly=True,
                secure=settings.ENVIRONMENT == "production",
                samesite="strict",
                max_age=int(self.session_manager.session_timeout.total_seconds())
            )
        
        return response
    
    def _get_session_id(self, request: Request) -> Optional[str]:
        """Extract session ID from request."""
        # Try cookie first
        session_id = request.cookies.get("session_id")
        if session_id:
            return session_id
        
        # Try header
        return request.headers.get("X-Session-ID")


# Global session manager
session_manager = SessionManager()


async def get_current_session(request: Request) -> Optional[Dict[str, Any]]:
    """Dependency to get current session data."""
    return getattr(request.state, "session_data", None)


async def require_session(request: Request) -> Dict[str, Any]:
    """Dependency that requires a valid session."""
    session_data = await get_current_session(request)
    
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid session required"
        )
    
    return session_data


def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    # Check for forwarded headers first
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct connection
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """Get user agent from request."""
    return request.headers.get("User-Agent", "unknown")