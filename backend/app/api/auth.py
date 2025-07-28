"""
Authentication API endpoints.
"""
import logging
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    create_access_token,
    create_refresh_token,
    get_current_active_user,
    security,
    verify_token,
)
from app.core.config import settings
from app.core.database import get_db
from app.models import UserSchema, UserTable
from app.repositories.user import user_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


class TokenResponse(BaseModel):
    """Response model for token endpoints."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    """Request model for login endpoint."""
    email: EmailStr
    # Note: In a real app, you'd have password here
    # For now, we'll use email-only authentication for simplicity


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Login endpoint - creates access and refresh tokens.
    
    For now, this uses email-only authentication.
    In production, you'd verify password here.
    """
    # Get user by email
    user = await user_repository.get_by_email(db, login_data.email)
    
    if not user:
        # Create user if doesn't exist (for development)
        logger.info(f"Creating new user: {login_data.email}")
        user = await user_repository.create_user(
            db,
            email=login_data.email,
            name=login_data.email.split("@")[0]  # Use email prefix as name
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user account"
        )
    
    # Update last login
    await user_repository.update_last_login(db, user.id)
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "email": user.email}
    )
    
    logger.info(f"User logged in: {user.email}")
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Refresh access token using refresh token.
    """
    try:
        # Verify refresh token
        payload = await verify_token(refresh_data.refresh_token)
        
        # Check if it's a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user
        user = await user_repository.get(db, user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new tokens
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email},
            expires_delta=access_token_expires
        )
        
        new_refresh_token = create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        logger.info(f"Token refreshed for user: {user.email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.access_token_expire_minutes * 60
        )
        
    except Exception as e:
        logger.warning(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(
    current_user: UserTable = Depends(get_current_active_user)
) -> Any:
    """
    Get current user information.
    """
    return current_user


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: UserTable = Depends(get_current_active_user)
) -> Any:
    """
    Logout endpoint.
    
    In a production system, you'd invalidate the token here.
    For now, this is just a placeholder.
    """
    logger.info(f"User logged out: {current_user.email}")
    
    return {"message": "Successfully logged out"}


@router.post("/verify-token")
async def verify_token_endpoint(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Any:
    """
    Verify if a token is valid.
    """
    try:
        payload = await verify_token(credentials.credentials)
        return {
            "valid": True,
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "expires": payload.get("exp")
        }
    except Exception as e:
        logger.warning(f"Token verification failed: {e}")
        return {"valid": False, "error": str(e)}