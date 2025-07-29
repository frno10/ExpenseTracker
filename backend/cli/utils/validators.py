"""
Input validation utilities for CLI commands.
"""
import re
from datetime import datetime
from typing import Optional, List


def validate_date(date_str: str) -> bool:
    """Validate date string in YYYY-MM-DD format."""
    if not date_str:
        return False
    
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def validate_amount(amount: float) -> bool:
    """Validate that amount is positive."""
    return amount > 0


def validate_email(email: str) -> bool:
    """Validate email address format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_url(url: str) -> bool:
    """Validate URL format."""
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return re.match(pattern, url) is not None


def validate_file_path(file_path: str) -> bool:
    """Validate that file path exists and is readable."""
    try:
        from pathlib import Path
        path = Path(file_path)
        return path.exists() and path.is_file()
    except Exception:
        return False


def validate_category_name(name: str) -> bool:
    """Validate category name format."""
    if not name or len(name.strip()) == 0:
        return False
    
    # Category names should be reasonable length and not contain special chars
    if len(name) > 50:
        return False
    
    # Allow letters, numbers, spaces, hyphens, and underscores
    pattern = r'^[a-zA-Z0-9\s\-_]+$'
    return re.match(pattern, name) is not None


def validate_budget_period(period: str) -> bool:
    """Validate budget period format."""
    valid_periods = ['daily', 'weekly', 'monthly', 'quarterly', 'yearly']
    return period.lower() in valid_periods


def validate_currency_code(code: str) -> bool:
    """Validate currency code format (3 letters)."""
    if not code or len(code) != 3:
        return False
    
    return code.isalpha() and code.isupper()


def validate_tags(tags_str: str) -> List[str]:
    """Validate and clean up tags string."""
    if not tags_str:
        return []
    
    # Split by comma and clean up
    tags = [tag.strip() for tag in tags_str.split(',')]
    
    # Filter out empty tags and validate format
    valid_tags = []
    for tag in tags:
        if tag and len(tag) <= 30 and re.match(r'^[a-zA-Z0-9\s\-_]+$', tag):
            valid_tags.append(tag)
    
    return valid_tags


def validate_sort_field(field: str, valid_fields: List[str]) -> bool:
    """Validate that sort field is in allowed list."""
    return field in valid_fields


def validate_sort_order(order: str) -> bool:
    """Validate sort order."""
    return order.lower() in ['asc', 'desc']


def validate_limit(limit: int, max_limit: int = 1000) -> bool:
    """Validate limit parameter."""
    return 1 <= limit <= max_limit


def validate_date_range(start_date: str, end_date: str) -> bool:
    """Validate that date range is logical."""
    if not validate_date(start_date) or not validate_date(end_date):
        return False
    
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        return start <= end
    except ValueError:
        return False


def validate_amount_range(min_amount: Optional[float], max_amount: Optional[float]) -> bool:
    """Validate amount range."""
    if min_amount is not None and min_amount < 0:
        return False
    
    if max_amount is not None and max_amount < 0:
        return False
    
    if min_amount is not None and max_amount is not None:
        return min_amount <= max_amount
    
    return True


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations."""
    # Remove or replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    # Ensure it's not empty
    if not filename:
        filename = 'untitled'
    
    return filename


def validate_json_string(json_str: str) -> bool:
    """Validate that string is valid JSON."""
    try:
        import json
        json.loads(json_str)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def validate_positive_integer(value: int) -> bool:
    """Validate that value is a positive integer."""
    return isinstance(value, int) and value > 0


def validate_non_negative_integer(value: int) -> bool:
    """Validate that value is a non-negative integer."""
    return isinstance(value, int) and value >= 0