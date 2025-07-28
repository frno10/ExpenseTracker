"""
Tests for authentication and security.
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
    AuthenticationError,
)
from app.main import app
from app.models import UserTable
from app.repositories.user import user_repository

client = TestClient(app)


class TestPasswordHashing:
    """Test password hashing utilities."""
    
    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        # Hash should be different from original
        assert hashed != password
        
        # Verification should work
        assert verify_password(password, hashed) is True
        
        # Wrong password should fail
        assert verify_password("wrong_password", hashed) is False
    
    def test_different_hashes_for_same_password(self):
        """Test that same password produces different hashes."""
        password = "test_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different (due to salt)
        assert hash1 != hash2
        
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTTokens:
    """Test JWT token creation and verification."""
    
    def test_create_access_token(self):
        """Test access token creation."""
        data = {"sub": "test_user_id", "email": "test@example.com"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        data = {"sub": "test_user_id", "email": "test@example.com"}
        token = create_refresh_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    @pytest.mark.asyncio
    async def test_verify_valid_token(self):
        """Test verification of valid token."""
        data = {"sub": "test_user_id", "email": "test@example.com"}
        token = create_access_token(data)
        
        payload = await verify_token(token)
        
        assert payload["sub"] == "test_user_id"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload
    
    @pytest.mark.asyncio
    async def test_verify_invalid_token(self):
        """Test verification of invalid token."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(AuthenticationError):
            await verify_token(invalid_token)
    
    @pytest.mark.asyncio
    async def test_verify_expired_token(self):
        """Test verification of expired token."""
        data = {"sub": "test_user_id", "email": "test@example.com"}
        # Create token that expires immediately
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        
        with pytest.raises(AuthenticationError):
            await verify_token(token)
    
    @pytest.mark.asyncio
    async def test_refresh_token_type(self):
        """Test that refresh tokens have correct type."""
        data = {"sub": "test_user_id", "email": "test@example.com"}
        token = create_refresh_token(data)
        
        payload = await verify_token(token)
        
        assert payload["type"] == "refresh"


class TestAuthenticationAPI:
    """Test authentication API endpoints."""
    
    def test_login_new_user(self):
        """Test login with new user (auto-creation)."""
        response = client.post(
            "/api/auth/login",
            json={"email": "newuser@example.com"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    def test_login_invalid_email(self):
        """Test login with invalid email format."""
        response = client.post(
            "/api/auth/login",
            json={"email": "invalid-email"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_current_user_without_token(self):
        """Test getting current user without authentication."""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 403  # No authorization header
    
    def test_get_current_user_with_invalid_token(self):
        """Test getting current user with invalid token."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
    
    def test_full_auth_flow(self):
        """Test complete authentication flow."""
        # 1. Login
        login_response = client.post(
            "/api/auth/login",
            json={"email": "testuser@example.com"}
        )
        
        assert login_response.status_code == 200
        tokens = login_response.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        
        # 2. Get current user
        user_response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert user_response.status_code == 200
        user_data = user_response.json()
        assert user_data["email"] == "testuser@example.com"
        
        # 3. Refresh token
        refresh_response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        
        # 4. Use new access token
        new_user_response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {new_tokens['access_token']}"}
        )
        
        assert new_user_response.status_code == 200
        
        # 5. Logout
        logout_response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {new_tokens['access_token']}"}
        )
        
        assert logout_response.status_code == 200
    
    def test_refresh_with_invalid_token(self):
        """Test token refresh with invalid refresh token."""
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid_refresh_token"}
        )
        
        assert response.status_code == 401
    
    def test_refresh_with_access_token(self):
        """Test token refresh with access token (should fail)."""
        # Get access token
        login_response = client.post(
            "/api/auth/login",
            json={"email": "testuser2@example.com"}
        )
        access_token = login_response.json()["access_token"]
        
        # Try to use access token as refresh token
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": access_token}
        )
        
        assert response.status_code == 401
    
    def test_verify_token_endpoint(self):
        """Test token verification endpoint."""
        # Get valid token
        login_response = client.post(
            "/api/auth/login",
            json={"email": "verifyuser@example.com"}
        )
        access_token = login_response.json()["access_token"]
        
        # Verify token
        response = client.post(
            "/api/auth/verify-token",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "user_id" in data
        assert "email" in data


@pytest.mark.asyncio
class TestUserRepository:
    """Test user repository operations."""
    
    async def test_create_user(self, db_session: AsyncSession):
        """Test user creation."""
        user = await user_repository.create_user(
            db_session,
            email="repotest@example.com",
            name="Test User",
            timezone="America/New_York",
            currency="USD"
        )
        
        assert user.email == "repotest@example.com"
        assert user.name == "Test User"
        assert user.timezone == "America/New_York"
        assert user.currency == "USD"
        assert user.is_active is True
    
    async def test_get_user_by_email(self, db_session: AsyncSession):
        """Test getting user by email."""
        # Create user
        created_user = await user_repository.create_user(
            db_session,
            email="emailtest@example.com",
            name="Email Test User"
        )
        
        # Get by email
        found_user = await user_repository.get_by_email(
            db_session,
            "emailtest@example.com"
        )
        
        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.email == "emailtest@example.com"
    
    async def test_get_nonexistent_user_by_email(self, db_session: AsyncSession):
        """Test getting nonexistent user by email."""
        user = await user_repository.get_by_email(
            db_session,
            "nonexistent@example.com"
        )
        
        assert user is None
    
    async def test_deactivate_user(self, db_session: AsyncSession):
        """Test user deactivation."""
        # Create user
        user = await user_repository.create_user(
            db_session,
            email="deactivate@example.com"
        )
        
        assert user.is_active is True
        
        # Deactivate
        deactivated_user = await user_repository.deactivate_user(
            db_session,
            user.id
        )
        
        assert deactivated_user is not None
        assert deactivated_user.is_active is False
    
    async def test_activate_user(self, db_session: AsyncSession):
        """Test user activation."""
        # Create and deactivate user
        user = await user_repository.create_user(
            db_session,
            email="activate@example.com"
        )
        
        await user_repository.deactivate_user(db_session, user.id)
        
        # Activate
        activated_user = await user_repository.activate_user(
            db_session,
            user.id
        )
        
        assert activated_user is not None
        assert activated_user.is_active is True