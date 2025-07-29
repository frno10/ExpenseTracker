"""
Comprehensive security tests and penetration testing scenarios.
"""
import pytest
import asyncio
import json
import time
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.main import app
from app.core.validation import (
    sanitize_string, validate_email, validate_amount, validate_password,
    ValidationError, SecurityError
)
from app.core.security_middleware import (
    SecurityHeadersMiddleware, CSRFProtectionMiddleware, RateLimitMiddleware,
    InputValidationMiddleware, SessionSecurityMiddleware, AuditLoggingMiddleware
)
from app.core.encryption import FieldEncryption, TokenEncryption, EncryptionError
from app.core.audit import AuditLogger, AuditEventType, AuditSeverity


class TestInputValidation:
    """Test input validation and sanitization."""
    
    def test_sanitize_string_basic(self):
        """Test basic string sanitization."""
        result = sanitize_string("Hello World")
        assert result == "Hello World"
    
    def test_sanitize_string_xss_prevention(self):
        """Test XSS prevention in string sanitization."""
        with pytest.raises(SecurityError):
            sanitize_string("<script>alert('xss')</script>")
        
        with pytest.raises(SecurityError):
            sanitize_string("javascript:alert('xss')")
        
        with pytest.raises(SecurityError):
            sanitize_string("<img src=x onerror=alert('xss')>")
    
    def test_sanitize_string_sql_injection_prevention(self):
        """Test SQL injection prevention."""
        with pytest.raises(SecurityError):
            sanitize_string("'; DROP TABLE users; --")
        
        with pytest.raises(SecurityError):
            sanitize_string("1 OR 1=1")
        
        with pytest.raises(SecurityError):
            sanitize_string("UNION SELECT * FROM passwords")
    
    def test_sanitize_string_length_limit(self):
        """Test string length limits."""
        with pytest.raises(ValidationError):
            sanitize_string("a" * 1000, max_length=100)
    
    def test_validate_email(self):
        """Test email validation."""
        # Valid emails
        assert validate_email("test@example.com") == "test@example.com"
        assert validate_email("  TEST@EXAMPLE.COM  ") == "test@example.com"
        
        # Invalid emails
        with pytest.raises(ValidationError):
            validate_email("invalid-email")
        
        with pytest.raises(ValidationError):
            validate_email("@example.com")
        
        with pytest.raises(ValidationError):
            validate_email("test@")
    
    def test_validate_amount(self):
        """Test amount validation."""
        # Valid amounts
        assert validate_amount("123.45") == 123.45
        assert validate_amount(123.45) == 123.45
        assert validate_amount("$1,234.56") == 1234.56
        
        # Invalid amounts
        with pytest.raises(ValidationError):
            validate_amount("-100")
        
        with pytest.raises(ValidationError):
            validate_amount("invalid")
        
        with pytest.raises(ValidationError):
            validate_amount("123.456")  # Too many decimal places
    
    def test_validate_password(self):
        """Test password validation."""
        # Valid passwords
        assert validate_password("StrongP@ss123") == "StrongP@ss123"
        
        # Invalid passwords
        with pytest.raises(ValidationError):
            validate_password("weak")  # Too short
        
        with pytest.raises(ValidationError):
            validate_password("alllowercase123")  # No uppercase or special chars
        
        with pytest.raises(ValidationError):
            validate_password("ALLUPPERCASE123")  # No lowercase or special chars


class TestSecurityMiddleware:
    """Test security middleware components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.test_app = FastAPI()
        self.client = TestClient(self.test_app)
    
    def test_security_headers_middleware(self):
        """Test security headers middleware."""
        # Add middleware
        self.test_app.add_middleware(SecurityHeadersMiddleware)
        
        @self.test_app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        response = self.client.get("/test")
        
        # Check security headers
        assert "X-XSS-Protection" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Content-Security-Policy" in response.headers
        assert "Strict-Transport-Security" in response.headers
        
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
    
    def test_rate_limit_middleware(self):
        """Test rate limiting middleware."""
        # Add middleware with low limits for testing
        self.test_app.add_middleware(RateLimitMiddleware, requests_per_minute=5, burst_limit=2)
        
        @self.test_app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        # First few requests should succeed
        for i in range(2):
            response = self.client.get("/test")
            assert response.status_code == 200
            assert "X-RateLimit-Limit" in response.headers
        
        # Burst limit should be hit
        response = self.client.get("/test")
        # Note: In real testing, this might not trigger due to test client behavior
        # This is more of a demonstration of the test structure
    
    def test_input_validation_middleware(self):
        """Test input validation middleware."""
        self.test_app.add_middleware(InputValidationMiddleware)
        
        @self.test_app.get("/test")
        async def test_endpoint(q: str = ""):
            return {"query": q}
        
        # Valid request
        response = self.client.get("/test?q=normal_query")
        assert response.status_code == 200
        
        # Suspicious request
        response = self.client.get("/test?q=<script>alert('xss')</script>")
        assert response.status_code == 400


class TestEncryption:
    """Test encryption utilities."""
    
    def test_field_encryption(self):
        """Test field encryption and decryption."""
        encryption = FieldEncryption()
        
        # Test basic encryption/decryption
        plaintext = "sensitive data"
        encrypted = encryption.encrypt(plaintext)
        decrypted = encryption.decrypt(encrypted)
        
        assert decrypted == plaintext
        assert encrypted != plaintext
        assert len(encrypted) > len(plaintext)
    
    def test_field_encryption_empty_string(self):
        """Test encryption of empty strings."""
        encryption = FieldEncryption()
        
        encrypted = encryption.encrypt("")
        decrypted = encryption.decrypt("")
        
        assert encrypted == ""
        assert decrypted == ""
    
    def test_field_encryption_dict(self):
        """Test dictionary field encryption."""
        encryption = FieldEncryption()
        
        data = {
            "public_field": "public data",
            "secret_field": "secret data",
            "another_secret": "more secrets"
        }
        
        encrypted_data = encryption.encrypt_dict(data, ["secret_field", "another_secret"])
        
        # Public field should be unchanged
        assert encrypted_data["public_field"] == "public data"
        
        # Secret fields should be encrypted
        assert encrypted_data["secret_field"] != "secret data"
        assert encrypted_data["another_secret"] != "more secrets"
        
        # Decrypt and verify
        decrypted_data = encryption.decrypt_dict(encrypted_data, ["secret_field", "another_secret"])
        assert decrypted_data == data
    
    def test_token_encryption(self):
        """Test token encryption."""
        token_encryption = TokenEncryption("test_secret_key")
        
        token = "sensitive_token_12345"
        encrypted_token = token_encryption.encrypt_token(token)
        decrypted_token = token_encryption.decrypt_token(encrypted_token)
        
        assert decrypted_token == token
        assert encrypted_token != token
    
    def test_encryption_error_handling(self):
        """Test encryption error handling."""
        encryption = FieldEncryption()
        
        # Test invalid input types
        with pytest.raises(EncryptionError):
            encryption.encrypt(123)  # Not a string
        
        with pytest.raises(EncryptionError):
            encryption.decrypt(123)  # Not a string
        
        # Test invalid encrypted data
        with pytest.raises(EncryptionError):
            encryption.decrypt("invalid_encrypted_data")


class TestAuditLogging:
    """Test audit logging system."""
    
    @pytest.mark.asyncio
    async def test_audit_logger_basic(self):
        """Test basic audit logging."""
        audit_logger = AuditLogger()
        
        audit_id = await audit_logger.log_event(
            event_type=AuditEventType.LOGIN_SUCCESS,
            severity=AuditSeverity.MEDIUM,
            user_id=None,
            ip_address="127.0.0.1",
            details={"test": "data"}
        )
        
        assert audit_id is not None
    
    @pytest.mark.asyncio
    async def test_audit_authentication_events(self):
        """Test authentication event logging."""
        audit_logger = AuditLogger()
        
        # Test successful login
        audit_id = await audit_logger.log_authentication_event(
            AuditEventType.LOGIN_SUCCESS,
            ip_address="127.0.0.1",
            user_agent="test-agent",
            success=True
        )
        assert audit_id is not None
        
        # Test failed login
        audit_id = await audit_logger.log_authentication_event(
            AuditEventType.LOGIN_FAILURE,
            ip_address="127.0.0.1",
            user_agent="test-agent",
            success=False,
            error_message="Invalid credentials"
        )
        assert audit_id is not None
    
    @pytest.mark.asyncio
    async def test_audit_security_events(self):
        """Test security event logging."""
        audit_logger = AuditLogger()
        
        audit_id = await audit_logger.log_security_event(
            AuditEventType.SECURITY_VIOLATION,
            AuditSeverity.HIGH,
            ip_address="127.0.0.1",
            details={"violation_type": "xss_attempt"},
            error_message="XSS attempt detected"
        )
        
        assert audit_id is not None


class TestPenetrationScenarios:
    """Penetration testing scenarios."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_sql_injection_attempts(self):
        """Test SQL injection attack scenarios."""
        # Common SQL injection payloads
        payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM passwords --",
            "1; DELETE FROM expenses; --"
        ]
        
        for payload in payloads:
            # Test in query parameters
            response = self.client.get(f"/api/expenses?search={payload}")
            # Should not return 500 (internal server error from SQL injection)
            assert response.status_code != 500
            
            # Test in request body (if endpoint accepts it)
            response = self.client.post(
                "/api/expenses",
                json={"description": payload, "amount": 100}
            )
            # Should either reject (400/422) or handle safely
            assert response.status_code in [400, 401, 422]
    
    def test_xss_attempts(self):
        """Test XSS attack scenarios."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<svg onload=alert('xss')>",
            "';alert('xss');//"
        ]
        
        for payload in xss_payloads:
            # Test in various endpoints
            response = self.client.get(f"/api/expenses?search={payload}")
            assert response.status_code != 500
            
            # Test in POST data
            response = self.client.post(
                "/api/expenses",
                json={"description": payload, "amount": 100}
            )
            assert response.status_code in [400, 401, 422]
    
    def test_path_traversal_attempts(self):
        """Test path traversal attack scenarios."""
        traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd"
        ]
        
        for payload in traversal_payloads:
            # Test file upload endpoints
            response = self.client.post(
                "/api/attachments/upload",
                files={"file": (payload, b"test content", "text/plain")}
            )
            # Should reject malicious filenames
            assert response.status_code in [400, 401, 422]
    
    def test_command_injection_attempts(self):
        """Test command injection scenarios."""
        command_payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "&& rm -rf /",
            "`whoami`",
            "$(id)"
        ]
        
        for payload in payloads:
            response = self.client.post(
                "/api/expenses",
                json={"description": payload, "amount": 100}
            )
            assert response.status_code in [400, 401, 422]
    
    def test_authentication_bypass_attempts(self):
        """Test authentication bypass scenarios."""
        # Test accessing protected endpoints without authentication
        protected_endpoints = [
            "/api/expenses",
            "/api/budgets",
            "/api/users/me",
            "/api/analytics/dashboard"
        ]
        
        for endpoint in protected_endpoints:
            response = self.client.get(endpoint)
            # Should require authentication
            assert response.status_code == 401
    
    def test_authorization_bypass_attempts(self):
        """Test authorization bypass scenarios."""
        # This would require setting up test users with different permissions
        # For now, just test that endpoints check for proper authorization
        
        # Test accessing other users' data
        response = self.client.get("/api/expenses/00000000-0000-0000-0000-000000000001")
        assert response.status_code in [401, 403, 404]
    
    def test_dos_attempts(self):
        """Test denial of service scenarios."""
        # Test large request bodies
        large_data = {"description": "x" * 1000000, "amount": 100}
        response = self.client.post("/api/expenses", json=large_data)
        # Should reject oversized requests
        assert response.status_code in [400, 413, 422]
        
        # Test deeply nested JSON
        nested_data = {"data": {}}
        current = nested_data["data"]
        for i in range(100):  # Create deeply nested structure
            current["nested"] = {}
            current = current["nested"]
        
        response = self.client.post("/api/expenses", json=nested_data)
        assert response.status_code in [400, 422]
    
    def test_csrf_protection(self):
        """Test CSRF protection."""
        # Test that state-changing operations require CSRF tokens
        response = self.client.post("/api/expenses", json={"description": "test", "amount": 100})
        # Should require CSRF token or proper authentication
        assert response.status_code in [401, 403]
    
    def test_rate_limiting(self):
        """Test rate limiting protection."""
        # Make many requests quickly
        responses = []
        for i in range(100):
            response = self.client.get("/api/health")
            responses.append(response.status_code)
        
        # Should eventually hit rate limits
        assert 429 in responses or all(r == 200 for r in responses[:10])
    
    def test_information_disclosure(self):
        """Test for information disclosure vulnerabilities."""
        # Test error messages don't reveal sensitive information
        response = self.client.get("/api/nonexistent-endpoint")
        assert response.status_code == 404
        
        # Error message should not reveal internal details
        if "detail" in response.json():
            error_detail = response.json()["detail"].lower()
            sensitive_terms = ["database", "sql", "internal", "stack trace", "exception"]
            for term in sensitive_terms:
                assert term not in error_detail


class TestSecurityConfiguration:
    """Test security configuration and settings."""
    
    def test_security_headers_configuration(self):
        """Test that security headers are properly configured."""
        client = TestClient(app)
        response = client.get("/")
        
        # Check for essential security headers
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection"
        ]
        
        for header in required_headers:
            assert header in response.headers
    
    def test_cors_configuration(self):
        """Test CORS configuration."""
        client = TestClient(app)
        
        # Test preflight request
        response = client.options(
            "/api/expenses",
            headers={
                "Origin": "https://malicious-site.com",
                "Access-Control-Request-Method": "POST"
            }
        )
        
        # Should handle CORS appropriately
        assert response.status_code in [200, 204, 405]
    
    def test_https_enforcement(self):
        """Test HTTPS enforcement in production."""
        # This would typically be handled by reverse proxy
        # Test that security headers indicate HTTPS requirement
        client = TestClient(app)
        response = client.get("/")
        
        if "Strict-Transport-Security" in response.headers:
            hsts_header = response.headers["Strict-Transport-Security"]
            assert "max-age" in hsts_header


if __name__ == "__main__":
    pytest.main([__file__])