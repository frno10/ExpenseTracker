"""
Authentication and authorization utilities.

Supports Supabase JWT token verification. Returns a CurrentUser object
that is compatible with both dict-style access (current_user["id"]) and
attribute access (current_user.id) for backward compatibility.
"""
import logging
import os
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

# JWT token scheme
security = HTTPBearer(auto_error=False)


class CurrentUser:
    """
    Lightweight user object returned by authentication.
    Supports both attribute access (current_user.id) and dict access (current_user["id"])
    for compatibility with both modular routers and inline routes.
    """

    def __init__(self, id: str, email: str, is_active: bool = True):
        self.id = UUID(id) if isinstance(id, str) else id
        self.email = email
        self.is_active = is_active

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __repr__(self):
        return f"CurrentUser(id={self.id}, email={self.email})"


def _get_supabase_client():
    """Lazily get the Supabase client."""
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if url and key:
            return create_client(url, key)
    except Exception:
        pass
    return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    """
    Get the current authenticated user from a Supabase JWT token.

    Uses supabase.auth.get_user(token) for proper server-side verification.
    No fallback to unverified JWT decoding.

    Returns:
        CurrentUser with id, email, is_active attributes
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    supabase = _get_supabase_client()
    if supabase is None:
        logger.error("Supabase client unavailable - cannot verify token")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service unavailable",
        )

    try:
        user_response = supabase.auth.get_user(token)
        if user_response and user_response.user:
            return CurrentUser(
                id=user_response.user.id,
                email=user_response.user.email,
            )
    except Exception as e:
        logger.warning(f"Supabase token verification failed: {type(e).__name__}")

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_active_user(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """
    Get the current active user.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user


class RequirePermissions:
    """
    Dependency class for checking user permissions.
    Placeholder for future role-based access control.
    """

    def __init__(self, *permissions: str):
        self.permissions = permissions

    async def __call__(
        self,
        current_user: CurrentUser = Depends(get_current_active_user),
    ) -> CurrentUser:
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user


# Common permission dependencies
require_read = RequirePermissions("read")
require_write = RequirePermissions("write")
require_admin = RequirePermissions("admin")
