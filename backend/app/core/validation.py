"""
Comprehensive input validation and sanitization utilities.
"""
import re
import html
import logging
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from uuid import UUID
import bleach
from pydantic import BaseModel, validator, ValidationError

logger = logging.getLogger(__name__)

# Allowed HTML tags for rich text fields (very restrictive)
ALLOWED_HTML_TAGS = ['b', 'i', 'u', 'em', 'strong', 'p', 'br']
ALLOWED_HTML_ATTRIBUTES = {}

# Common regex patterns
PATTERNS = {
    'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
    'phone': re.compile(r'^\+?1?-?\.?\s?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})$'),
    'alphanumeric': re.compile(r'^[a-zA-Z0-9]+$'),
    'safe_string': re.compile(r'^[a-zA-Z0-9\s\-_.,!?()]+$'),
    'currency_code': re.compile(r'^[A-Z]{3}$'),
    'hex_color': re.compile(r'^#[0-9A-Fa-f]{6}$'),
    'slug': re.compile(r'^[a-z0-9-]+$'),
    'filename': re.compile(r'^[a-zA-Z0-9\-_. ]+\.[a-zA-Z0-9]+$'),
}

# SQL injection patterns to detect
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)",
    r"(--|#|/\*|\*/)",
    r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
    r"(\bOR\s+\d+\s*=\s*\d+)",
    r"(\'\s*(OR|AND)\s*\'\w*\'\s*=\s*\'\w*)",
    r"(\%27|\%22|\%3D|\%3B|\%2D\%2D)",
]

# XSS patterns to detect
XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"javascript:",
    r"vbscript:",
    r"onload\s*=",
    r"onerror\s*=",
    r"onclick\s*=",
    r"onmouseover\s*=",
    r"<iframe[^>]*>",
    r"<object[^>]*>",
    r"<embed[^>]*>",
]


class ValidationError(Exception):
    """Custom validation error."""
    pass


class SecurityError(Exception):
    """Security-related error."""
    pass


def sanitize_string(value: str, max_length: Optional[int] = None, allow_html: bool = False) -> str:
    """
    Sanitize string input to prevent XSS and other attacks.
    
    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length
        allow_html: Whether to allow safe HTML tags
        
    Returns:
        Sanitized string
        
    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(value, str):
        raise ValidationError("Value must be a string")
    
    # Check for potential XSS
    for pattern in XSS_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            logger.warning(f"Potential XSS detected in input: {value[:100]}")
            raise SecurityError("Potentially malicious content detected")
    
    # Check for SQL injection
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            logger.warning(f"Potential SQL injection detected in input: {value[:100]}")
            raise SecurityError("Potentially malicious content detected")
    
    # Sanitize HTML
    if allow_html:
        value = bleach.clean(value, tags=ALLOWED_HTML_TAGS, attributes=ALLOWED_HTML_ATTRIBUTES)
    else:
        value = html.escape(value)
    
    # Trim whitespace
    value = value.strip()
    
    # Check length
    if max_length and len(value) > max_length:
        raise ValidationError(f"String too long (max {max_length} characters)")
    
    return value


def validate_email(email: str) -> str:
    """
    Validate and sanitize email address.
    
    Args:
        email: Email address to validate
        
    Returns:
        Validated email address
        
    Raises:
        ValidationError: If email is invalid
    """
    if not isinstance(email, str):
        raise ValidationError("Email must be a string")
    
    email = email.strip().lower()
    
    if not PATTERNS['email'].match(email):
        raise ValidationError("Invalid email format")
    
    if len(email) > 254:  # RFC 5321 limit
        raise ValidationError("Email address too long")
    
    return email


def validate_amount(amount: Union[str, int, float, Decimal]) -> Decimal:
    """
    Validate and sanitize monetary amount.
    
    Args:
        amount: Amount to validate
        
    Returns:
        Validated Decimal amount
        
    Raises:
        ValidationError: If amount is invalid
    """
    try:
        if isinstance(amount, str):
            # Remove common currency symbols and whitespace
            amount = re.sub(r'[$,\s]', '', amount)
        
        decimal_amount = Decimal(str(amount))
        
        # Check for reasonable bounds
        if decimal_amount < 0:
            raise ValidationError("Amount cannot be negative")
        
        if decimal_amount > Decimal('999999999.99'):
            raise ValidationError("Amount too large")
        
        # Ensure max 2 decimal places
        if decimal_amount.as_tuple().exponent < -2:
            raise ValidationError("Amount cannot have more than 2 decimal places")
        
        return decimal_amount
        
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError("Invalid amount format")


def validate_date_string(date_str: str) -> date:
    """
    Validate and parse date string.
    
    Args:
        date_str: Date string to validate
        
    Returns:
        Parsed date object
        
    Raises:
        ValidationError: If date is invalid
    """
    if not isinstance(date_str, str):
        raise ValidationError("Date must be a string")
    
    try:
        # Try ISO format first
        parsed_date = datetime.fromisoformat(date_str).date()
        
        # Check for reasonable bounds
        min_date = date(1900, 1, 1)
        max_date = date(2100, 12, 31)
        
        if parsed_date < min_date or parsed_date > max_date:
            raise ValidationError("Date out of reasonable range")
        
        return parsed_date
        
    except ValueError:
        raise ValidationError("Invalid date format (use YYYY-MM-DD)")


def validate_uuid(uuid_str: str) -> UUID:
    """
    Validate UUID string.
    
    Args:
        uuid_str: UUID string to validate
        
    Returns:
        Validated UUID object
        
    Raises:
        ValidationError: If UUID is invalid
    """
    if not isinstance(uuid_str, str):
        raise ValidationError("UUID must be a string")
    
    try:
        return UUID(uuid_str)
    except ValueError:
        raise ValidationError("Invalid UUID format")


def validate_filename(filename: str) -> str:
    """
    Validate and sanitize filename.
    
    Args:
        filename: Filename to validate
        
    Returns:
        Sanitized filename
        
    Raises:
        ValidationError: If filename is invalid
    """
    if not isinstance(filename, str):
        raise ValidationError("Filename must be a string")
    
    filename = filename.strip()
    
    # Check for path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        raise SecurityError("Invalid filename: path traversal detected")
    
    # Check for valid filename pattern
    if not PATTERNS['filename'].match(filename):
        raise ValidationError("Invalid filename format")
    
    if len(filename) > 255:
        raise ValidationError("Filename too long")
    
    # Remove potentially dangerous characters
    filename = re.sub(r'[<>:"|?*]', '', filename)
    
    return filename


def validate_category_name(name: str) -> str:
    """
    Validate category name.
    
    Args:
        name: Category name to validate
        
    Returns:
        Validated category name
        
    Raises:
        ValidationError: If name is invalid
    """
    name = sanitize_string(name, max_length=50)
    
    if not name:
        raise ValidationError("Category name cannot be empty")
    
    if not PATTERNS['safe_string'].match(name):
        raise ValidationError("Category name contains invalid characters")
    
    return name


def validate_description(description: str, max_length: int = 500) -> str:
    """
    Validate expense/transaction description.
    
    Args:
        description: Description to validate
        max_length: Maximum allowed length
        
    Returns:
        Validated description
        
    Raises:
        ValidationError: If description is invalid
    """
    description = sanitize_string(description, max_length=max_length)
    
    if not description:
        raise ValidationError("Description cannot be empty")
    
    return description


def validate_password(password: str) -> str:
    """
    Validate password strength.
    
    Args:
        password: Password to validate
        
    Returns:
        Validated password
        
    Raises:
        ValidationError: If password is weak
    """
    if not isinstance(password, str):
        raise ValidationError("Password must be a string")
    
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long")
    
    if len(password) > 128:
        raise ValidationError("Password too long")
    
    # Check for complexity
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    complexity_score = sum([has_upper, has_lower, has_digit, has_special])
    
    if complexity_score < 3:
        raise ValidationError("Password must contain at least 3 of: uppercase, lowercase, digits, special characters")
    
    return password


def validate_json_data(data: Dict[str, Any], max_depth: int = 10, max_keys: int = 100) -> Dict[str, Any]:
    """
    Validate JSON data structure to prevent DoS attacks.
    
    Args:
        data: JSON data to validate
        max_depth: Maximum nesting depth
        max_keys: Maximum number of keys
        
    Returns:
        Validated data
        
    Raises:
        ValidationError: If data structure is invalid
    """
    def count_depth(obj, current_depth=0):
        if current_depth > max_depth:
            raise ValidationError(f"JSON data too deeply nested (max {max_depth} levels)")
        
        if isinstance(obj, dict):
            if len(obj) > max_keys:
                raise ValidationError(f"Too many keys in JSON object (max {max_keys})")
            
            for value in obj.values():
                count_depth(value, current_depth + 1)
        elif isinstance(obj, list):
            if len(obj) > max_keys:
                raise ValidationError(f"Too many items in JSON array (max {max_keys})")
            
            for item in obj:
                count_depth(item, current_depth + 1)
    
    count_depth(data)
    return data


def validate_file_upload(file_data: bytes, allowed_types: List[str], max_size: int = 10 * 1024 * 1024) -> bytes:
    """
    Validate uploaded file data.
    
    Args:
        file_data: File data to validate
        allowed_types: List of allowed MIME types
        max_size: Maximum file size in bytes
        
    Returns:
        Validated file data
        
    Raises:
        ValidationError: If file is invalid
    """
    if not isinstance(file_data, bytes):
        raise ValidationError("File data must be bytes")
    
    if len(file_data) > max_size:
        raise ValidationError(f"File too large (max {max_size} bytes)")
    
    if len(file_data) == 0:
        raise ValidationError("File is empty")
    
    # Basic file type detection (you might want to use python-magic for better detection)
    file_signatures = {
        b'\x89PNG\r\n\x1a\n': 'image/png',
        b'\xff\xd8\xff': 'image/jpeg',
        b'%PDF': 'application/pdf',
        b'PK\x03\x04': 'application/zip',  # Also covers xlsx, docx, etc.
    }
    
    detected_type = None
    for signature, mime_type in file_signatures.items():
        if file_data.startswith(signature):
            detected_type = mime_type
            break
    
    if detected_type and detected_type not in allowed_types:
        raise ValidationError(f"File type not allowed: {detected_type}")
    
    return file_data


class SecureBaseModel(BaseModel):
    """
    Base Pydantic model with security validations.
    """
    
    class Config:
        # Prevent extra fields
        extra = "forbid"
        # Validate assignment
        validate_assignment = True
        # Use enum values
        use_enum_values = True
        # Validate all fields
        validate_all = True
    
    def dict(self, **kwargs):
        """Override dict to sanitize output."""
        data = super().dict(**kwargs)
        return self._sanitize_dict(data)
    
    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary data."""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                # Basic sanitization for string values
                sanitized[key] = html.escape(value) if value else value
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_dict(item) if isinstance(item, dict)
                    else html.escape(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized


# Rate limiting helpers
class RateLimitExceeded(Exception):
    """Rate limit exceeded error."""
    pass


def check_rate_limit(identifier: str, max_requests: int, window_seconds: int) -> bool:
    """
    Check if rate limit is exceeded.
    
    Args:
        identifier: Unique identifier (IP, user ID, etc.)
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds
        
    Returns:
        True if within limit, False if exceeded
    """
    # This would typically use Redis or another cache
    # For now, just return True (implement with actual cache later)
    return True


def log_security_event(event_type: str, details: Dict[str, Any], severity: str = "INFO"):
    """
    Log security-related events.
    
    Args:
        event_type: Type of security event
        details: Event details
        severity: Event severity (INFO, WARNING, ERROR, CRITICAL)
    """
    logger.log(
        getattr(logging, severity),
        f"SECURITY_EVENT: {event_type}",
        extra={
            "event_type": event_type,
            "details": details,
            "severity": severity
        }
    )