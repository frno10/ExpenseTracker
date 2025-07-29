"""
Authentication and authorization utilities.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models import UserTable
from app.repositories.user import user_repository

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token scheme
security = HTTPBearer()


class AuthenticationError(Exception):
    """Custom authentication error."""
    pass


class AuthorizationError(Exception):
    """Custom authorization error."""
    pass


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        data: Data to encode in the token
        
    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)  # Refresh tokens last 7 days
    to_encode.update({"exp": expire, "type": "refresh"})
    
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


async def verify_token(token: str) -> dict:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token to verify
        
    Returns:
        Decoded token payload
        
    Raises:
        AuthenticationError: If token is invalid
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise AuthenticationError("Invalid token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> UserTable:
    """
    Get the current authenticated user from JWT token.
    
    Args:
        credentials: HTTP authorization credentials
        db: Database session
        
    Returns:
        Current user instance
        
    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Verify token
        payload = await verify_token(credentials.credentials)
        user_id: str = payload.get("sub")
        
        if user_id is None:
            logger.warning("Token missing user ID")
            raise credentials_exception
            
        # Convert to UUID
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            logger.warning(f"Invalid user ID format: {user_id}")
            raise credentials_exception
            
    except AuthenticationError:
        raise credentials_exception
    
    # Get user from database
    user = await user_repository.get(db, user_uuid)
    if user is None:
        logger.warning(f"User not found: {user_uuid}")
        raise credentials_exception
    
    if not user.is_active:
        logger.warning(f"Inactive user attempted access: {user_uuid}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    
    return user


async def get_current_active_user(
    current_user: UserTable = Depends(get_current_user)
) -> UserTable:
    """
    Get the current active user.
    
    Args:
        current_user: Current user from token
        
    Returns:
        Active user instance
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_user_websocket(token: Optional[str]) -> Optional[UserTable]:
    """
    Get the current authenticated user from JWT token for WebSocket connections.
    
    Args:
        token: JWT token from query parameter
        
    Returns:
        Current user instance or None if authentication fails
    """
    if not token:
        return None
    
    try:
        # Verify token
        payload = await verify_token(token)
        user_id: str = payload.get("sub")
        
        if user_id is None:
            return None
            
        # Convert to UUID
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            return None
        
        # Get database session
        from app.core.database import get_db_session
        async with get_db_session() as db:
            # Get user from database
            user = await user_repository.get(db, user_uuid)
            if user is None or not user.is_active:
                return None
            
            return user
            
    except Exception as e:
        logger.warning(f"WebSocket authentication failed: {e}")
        return None


class RequirePermissions:
    """
    Dependency class for checking user permissions.
    
    This is a placeholder for future role-based access control.
    """
    
    def __init__(self, *permissions: str):
        self.permissions = permissions
    
    async def __call__(
        self,
        current_user: UserTable = Depends(get_current_active_user)
    ) -> UserTable:
        """
        Check if user has required permissions.
        
        Args:
            current_user: Current authenticated user
            
        Returns:
            User if authorized
            
        Raises:
            HTTPException: If user lacks permissions
        """
        # For now, all active users have all permissions
        # In the future, implement role-based access control
        
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return current_user


# Common permission dependencies
require_read = RequirePermissions("read")
require_write = RequirePermissions("write")
require_admin = RequirePermissions("admin")