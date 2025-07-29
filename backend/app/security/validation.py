"""Input validation and sanitization."""
import re
import html
import bleach
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal, InvalidOperation
from datetime import datetime
from pydantic import BaseModel, validator
from fastapi import HTTPException, status

from ..core.config import settings


class InputValidator:
    """Input validation and sanitization utilities."""
    
    # Regex patterns for validation
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    PHONE_PATTERN = re.compile(r'^\+?1?-?\.?\s?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})$')
    UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    
    # Allowed HTML tags for rich text fields
    ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li']
    ALLOWED_ATTRIBUTES = {}
    
    @classmethod
    def validate_email(cls, email: str) -> bool:
        """Validate email format."""
        if not email or len(email) > 254:
            return False
        return bool(cls.EMAIL_PATTERN.match(email))
    
    @classmethod
    def validate_phone(cls, phone: str) -> bool:
        """Validate phone number format."""
        if not phone:
            return True  # Phone is optional
        return bool(cls.PHONE_PATTERN.match(phone))
    
    @classmethod
    def validate_uuid(cls, uuid_str: str) -> bool:
        """Validate UUID format."""
        if not uuid_str:
            return False
        return bool(cls.UUID_PATTERN.match(uuid_str))
    
    @classmethod
    def validate_amount(cls, amount: Union[str, float, Decimal]) -> Decimal:
        """Validate and convert amount to Decimal."""
        try:
            decimal_amount = Decimal(str(amount))
            if decimal_amount < 0:
                raise ValueError("Amount cannot be negative")
            if decimal_amount > Decimal('999999999.99'):
                raise ValueError("Amount too large")
            return decimal_amount.quantize(Decimal('0.01'))
        except (InvalidOperation, TypeError):
            raise ValueError("Invalid amount format")
    
    @classmethod
    def validate_date_string(cls, date_str: str) -> datetime:
        """Validate and parse date string."""
        if not date_str:
            raise ValueError("Date is required")
        
        # Try common date formats
        formats = [
            '%Y-%m-%d',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%m/%d/%Y',
            '%d.%m.%Y',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        raise ValueError("Invalid date format")
    
    @classmethod
    def validate_string_length(cls, value: str, min_length: int = 0, max_length: int = 1000) -> str:
        """Validate string length."""
        if not isinstance(value, str):
            raise ValueError("Value must be a string")
        
        if len(value) < min_length:
            raise ValueError(f"Value must be at least {min_length} characters")
        
        if len(value) > max_length:
            raise ValueError(f"Value must be at most {max_length} characters")
        
        return value
    
    @classmethod
    def validate_category_name(cls, name: str) -> str:
        """Validate category name."""
        name = cls.validate_string_length(name, 1, 100)
        
        # Check for invalid characters
        if re.search(r'[<>"\']', name):
            raise ValueError("Category name contains invalid characters")
        
        return name.strip()
    
    @classmethod
    def validate_description(cls, description: str) -> str:
        """Validate expense description."""
        description = cls.validate_string_length(description, 1, 500)
        return description.strip()
    
    @classmethod
    def validate_notes(cls, notes: Optional[str]) -> Optional[str]:
        """Validate notes field."""
        if not notes:
            return None
        
        notes = cls.validate_string_length(notes, 0, 2000)
        return notes.strip()


def sanitize_input(value: Any) -> Any:
    """Sanitize input to prevent XSS and injection attacks."""
    if isinstance(value, str):
        # HTML escape
        value = html.escape(value)
        
        # Remove potentially dangerous characters
        value = re.sub(r'[<>"\']', '', value)
        
        # Clean HTML if it's a rich text field
        if '<' in value or '>' in value:
            value = bleach.clean(
                value,
                tags=InputValidator.ALLOWED_TAGS,
                attributes=InputValidator.ALLOWED_ATTRIBUTES,
                strip=True
            )
        
        return value.strip()
    
    elif isinstance(value, dict):
        return {k: sanitize_input(v) for k, v in value.items()}
    
    elif isinstance(value, list):
        return [sanitize_input(item) for item in value]
    
    return value


def validate_file_upload(file_content: bytes, filename: str, max_size: int = 10 * 1024 * 1024) -> None:
    """Validate uploaded file."""
    # Check file size
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {max_size // 1024 // 1024}MB"
        )
    
    # Check file extension
    allowed_extensions = {'.pdf', '.csv', '.xlsx', '.xls', '.ofx', '.qif', '.txt'}
    file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
    
    if f'.{file_ext}' not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Basic file content validation
    if len(file_content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty"
        )
    
    # Check for malicious content patterns
    dangerous_patterns = [
        b'<script',
        b'javascript:',
        b'vbscript:',
        b'onload=',
        b'onerror=',
    ]
    
    content_lower = file_content.lower()
    for pattern in dangerous_patterns:
        if pattern in content_lower:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File contains potentially malicious content"
            )


class SecureBaseModel(BaseModel):
    """Base model with input validation and sanitization."""
    
    class Config:
        # Validate assignment
        validate_assignment = True
        # Use enum values
        use_enum_values = True
        # Allow population by field name
        allow_population_by_field_name = True
    
    def dict(self, **kwargs) -> Dict[str, Any]:
        """Override dict to sanitize output."""
        data = super().dict(**kwargs)
        return sanitize_input(data)


# Validation decorators
def validate_expense_data(func):
    """Decorator to validate expense data."""
    def wrapper(*args, **kwargs):
        # Validate amount
        if 'amount' in kwargs:
            kwargs['amount'] = InputValidator.validate_amount(kwargs['amount'])
        
        # Validate description
        if 'description' in kwargs:
            kwargs['description'] = InputValidator.validate_description(kwargs['description'])
        
        # Validate notes
        if 'notes' in kwargs:
            kwargs['notes'] = InputValidator.validate_notes(kwargs['notes'])
        
        return func(*args, **kwargs)
    return wrapper


def validate_user_data(func):
    """Decorator to validate user data."""
    def wrapper(*args, **kwargs):
        # Validate email
        if 'email' in kwargs:
            if not InputValidator.validate_email(kwargs['email']):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid email format"
                )
        
        # Validate phone
        if 'phone' in kwargs:
            if not InputValidator.validate_phone(kwargs['phone']):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid phone number format"
                )
        
        return func(*args, **kwargs)
    return wrapper


# SQL injection prevention
def escape_sql_like(value: str) -> str:
    """Escape special characters in SQL LIKE patterns."""
    if not value:
        return value
    
    # Escape SQL LIKE wildcards
    value = value.replace('\\', '\\\\')
    value = value.replace('%', '\\%')
    value = value.replace('_', '\\_')
    
    return value


def validate_search_query(query: str) -> str:
    """Validate and sanitize search query."""
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query is required"
        )
    
    # Limit query length
    if len(query) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query too long"
        )
    
    # Remove potentially dangerous characters
    query = re.sub(r'[<>"\';\\]', '', query)
    
    return query.strip()