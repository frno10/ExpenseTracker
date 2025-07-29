"""Security tests for the expense tracker application."""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI, Request
from starlette.responses import Response

from app.security.csrf import CSRFProtection, CSRFMiddleware
from app.security.headers import SecurityHeaders, SecurityHeadersMiddleware
from app.security.validation import InputValidator, sanitize_input, validate_file_upload
from app.security.encryption import FieldEncryption, hash_password, verify_password
from app.security.audit import AuditLogger, AuditEventType, AuditSeverity
from app.security.session import SessionManager


class TestCSRFProtection:
    """Test CSRF protection functionality."""
    
    def test_generate_token(self):
        """Test CSRF token generation."""
        csrf = CSRFProtection("test_secret")
        session_id = "test_session_123"
        
        token = csrf.generate_token(session_id)
        
        assert token is not None
        assert len(token.split(":")) == 4
        assert session_id in token
    
    def test_validate_token_success(self):
        """Test successful token validation."""
        csrf = CSRFProtection("test_secret")
        session_id = "test_session_123"
        
        token = csrf.generate_token(session_id)
        is_valid = csrf.validate_token(token, session_id)
        
        assert is_valid is True
    
    def test_validate_token_wrong_session(self):
        """Test token validation with wrong session ID."""
        csrf = CSRFProtection("test_secret")
        session_id = "test_session_123"
        wrong_session_id = "wrong_session_456"
        
        token = csrf.generate_token(session_id)
        is_valid = csrf.validate_token(token, wrong_session_id)
        
        assert is_valid is False
    
    def test_validate_token_invalid_format(self):
        """Test token validation with invalid format."""
        csrf = CSRFProtection("test_secret")
        session_id = "test_session_123"
        
        is_valid = csrf.validate_token("invalid_token", session_id)
        
        assert is_valid is False


class TestSecurityHeaders:
    """Test security headers functionality."""
    
    def test_security_headers_generation(self):
        """Test security headers are generated correctly."""
        headers = SecurityHeaders()
        
        assert "X-XSS-Protection" in headers.headers
        assert "X-Content-Type-Options" in headers.headers
        assert "X-Frame-Options" in headers.headers
        assert "Content-Security-Policy" in headers.headers
        assert headers.headers["X-Frame-Options"] == "DENY"
        assert headers.headers["X-Content-Type-Options"] == "nosniff"
    
    def test_security_headers_middleware(self):
        """Test security headers middleware."""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        app.add_middleware(SecurityHeadersMiddleware)
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "X-XSS-Protection" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers


class TestInputValidation:
    """Test input validation functionality."""
    
    def test_validate_email_valid(self):
        """Test valid email validation."""
        assert InputValidator.validate_email("test@example.com") is True
        assert InputValidator.validate_email("user.name+tag@domain.co.uk") is True
    
    def test_validate_email_invalid(self):
        """Test invalid email validation."""
        assert InputValidator.validate_email("invalid_email") is False
        assert InputValidator.validate_email("@domain.com") is False
        assert InputValidator.validate_email("user@") is False
        assert InputValidator.validate_email("") is False
    
    def test_validate_amount_valid(self):
        """Test valid amount validation."""
        from decimal import Decimal
        
        result = InputValidator.validate_amount("123.45")
        assert result == Decimal("123.45")
        
        result = InputValidator.validate_amount(100.50)
        assert result == Decimal("100.50")
    
    def test_validate_amount_invalid(self):
        """Test invalid amount validation."""
        with pytest.raises(ValueError):
            InputValidator.validate_amount("-10.00")
        
        with pytest.raises(ValueError):
            InputValidator.validate_amount("invalid")
        
        with pytest.raises(ValueError):
            InputValidator.validate_amount("999999999999.99")
    
    def test_sanitize_input_string(self):
        """Test string input sanitization."""
        result = sanitize_input("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "alert" not in result
    
    def test_sanitize_input_dict(self):
        """Test dictionary input sanitization."""
        input_data = {
            "name": "<script>alert('xss')</script>",
            "description": "Normal text",
            "amount": 100.50
        }
        
        result = sanitize_input(input_data)
        
        assert "<script>" not in result["name"]
        assert result["description"] == "Normal text"
        assert result["amount"] == 100.50
    
    def test_validate_file_upload_valid(self):
        """Test valid file upload validation."""
        file_content = b"Date,Description,Amount\n2024-01-01,Test,100.00"
        filename = "test.csv"
        
        # Should not raise exception
        validate_file_upload(file_content, filename)
    
    def test_validate_file_upload_too_large(self):
        """Test file upload validation with large file."""
        file_content = b"x" * (11 * 1024 * 1024)  # 11MB
        filename = "test.csv"
        
        with pytest.raises(Exception):  # Should raise HTTPException
            validate_file_upload(file_content, filename)
    
    def test_validate_file_upload_invalid_extension(self):
        """Test file upload validation with invalid extension."""
        file_content = b"test content"
        filename = "test.exe"
        
        with pytest.raises(Exception):  # Should raise HTTPException
            validate_file_upload(file_content, filename)


class TestEncryption:
    """Test encryption functionality."""
    
    def test_field_encryption(self):
        """Test field encryption and decryption."""
        encryption = FieldEncryption("test_key_123")
        
        plaintext = "sensitive_data_123"
        encrypted = encryption.encrypt(plaintext)
        decrypted = encryption.decrypt(encrypted)
        
        assert encrypted != plaintext
        assert decrypted == plaintext
    
    def test_field_encryption_empty_string(self):
        """Test encryption with empty string."""
        encryption = FieldEncryption("test_key_123")
        
        result = encryption.encrypt("")
        assert result == ""
        
        result = encryption.decrypt("")
        assert result == ""
    
    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "test_password_123"
        
        hashed = hash_password(password)
        
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False
    
    def test_hash_value(self):
        """Test value hashing for searchable encryption."""
        encryption = FieldEncryption("test_key_123")
        
        value = "test_value"
        hash1 = encryption.hash_value(value)
        hash2 = encryption.hash_value(value)
        
        assert hash1 == hash2  # Same value should produce same hash
        assert hash1 != value  # Hash should be different from original
        
        different_hash = encryption.hash_value("different_value")
        assert hash1 != different_hash


class TestAuditLogging:
    """Test audit logging functionality."""
    
    @pytest.mark.asyncio
    async def test_audit_logger_log_event(self):
        """Test audit event logging."""
        mock_db = Mock()
        mock_db.add = Mock()
        mock_db.commit = Mock()
        
        audit_logger = AuditLogger()
        
        await audit_logger.log_event(
            db=mock_db,
            event_type=AuditEventType.LOGIN,
            severity=AuditSeverity.LOW,
            user_id="test_user_123",
            ip_address="192.168.1.1",
            action="login",
            success=True
        )
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_audit_logger_login_attempt(self):
        """Test login attempt logging."""
        mock_db = Mock()
        mock_db.add = Mock()
        mock_db.commit = Mock()
        
        audit_logger = AuditLogger()
        
        await audit_logger.log_login_attempt(
            db=mock_db,
            user_id="test_user_123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=True
        )
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_audit_logger_security_violation(self):
        """Test security violation logging."""
        mock_db = Mock()
        mock_db.add = Mock()
        mock_db.commit = Mock()
        
        audit_logger = AuditLogger()
        
        await audit_logger.log_security_violation(
            db=mock_db,
            event_description="Suspicious activity detected",
            user_id="test_user_123",
            ip_address="192.168.1.1",
            details={"attempt_count": 5}
        )
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


class TestSessionManagement:
    """Test session management functionality."""
    
    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test session creation."""
        mock_redis = Mock()
        mock_redis.setex = Mock()
        mock_redis.sadd = Mock()
        mock_redis.scard = Mock(return_value=1)
        
        session_manager = SessionManager(mock_redis)
        
        session_id = await session_manager.create_session(
            user_id="test_user_123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )
        
        assert session_id is not None
        assert len(session_id) > 20  # Should be a long random string
        mock_redis.setex.assert_called()
        mock_redis.sadd.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_session_valid(self):
        """Test getting valid session."""
        import json
        from datetime import datetime
        
        session_data = {
            "user_id": "test_user_123",
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
            "is_active": True
        }
        
        mock_redis = Mock()
        mock_redis.get = Mock(return_value=json.dumps(session_data))
        
        session_manager = SessionManager(mock_redis)
        
        result = await session_manager.get_session("test_session_id")
        
        assert result is not None
        assert result["user_id"] == "test_user_123"
        assert result["ip_address"] == "192.168.1.1"
    
    @pytest.mark.asyncio
    async def test_get_session_expired(self):
        """Test getting expired session."""
        import json
        from datetime import datetime, timedelta
        
        # Create session data that's older than idle timeout
        old_time = datetime.utcnow() - timedelta(hours=3)
        session_data = {
            "user_id": "test_user_123",
            "created_at": old_time.isoformat(),
            "last_activity": old_time.isoformat(),
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
            "is_active": True
        }
        
        mock_redis = Mock()
        mock_redis.get = Mock(return_value=json.dumps(session_data))
        mock_redis.delete = Mock()
        mock_redis.srem = Mock()
        
        session_manager = SessionManager(mock_redis)
        
        result = await session_manager.get_session("test_session_id")
        
        assert result is None  # Should be None for expired session
        mock_redis.delete.assert_called()  # Should invalidate expired session
    
    @pytest.mark.asyncio
    async def test_invalidate_session(self):
        """Test session invalidation."""
        import json
        
        session_data = {
            "user_id": "test_user_123",
            "created_at": "2024-01-01T00:00:00",
            "last_activity": "2024-01-01T00:00:00",
            "ip_address": "192.168.1.1"
        }
        
        mock_redis = Mock()
        mock_redis.get = Mock(return_value=json.dumps(session_data))
        mock_redis.delete = Mock(return_value=1)
        mock_redis.srem = Mock()
        
        session_manager = SessionManager(mock_redis)
        
        result = await session_manager.invalidate_session("test_session_id")
        
        assert result is True
        mock_redis.delete.assert_called_with("session:test_session_id")
        mock_redis.srem.assert_called_with("user_sessions:test_user_123", "test_session_id")


class TestSecurityIntegration:
    """Test security features integration."""
    
    def test_security_middleware_integration(self):
        """Test that security middleware works together."""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        # Add security middleware
        app.add_middleware(SecurityHeadersMiddleware)
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        
        # Check security headers are present
        assert "X-XSS-Protection" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Content-Security-Policy" in response.headers
    
    def test_input_validation_integration(self):
        """Test input validation in API endpoints."""
        # This would test actual API endpoints with validation
        # For now, just test the validation functions work together
        
        test_data = {
            "email": "test@example.com",
            "amount": "123.45",
            "description": "<script>alert('xss')</script>Normal text"
        }
        
        # Validate email
        assert InputValidator.validate_email(test_data["email"]) is True
        
        # Validate amount
        validated_amount = InputValidator.validate_amount(test_data["amount"])
        assert str(validated_amount) == "123.45"
        
        # Sanitize description
        sanitized_description = sanitize_input(test_data["description"])
        assert "<script>" not in sanitized_description
        assert "Normal text" in sanitized_description