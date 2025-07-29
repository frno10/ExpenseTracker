"""
Custom exceptions for the Expense Tracker CLI.
"""


class ExpenseTrackerCLIError(Exception):
    """Base exception for CLI errors."""
    pass


class ConfigurationError(ExpenseTrackerCLIError):
    """Configuration-related errors."""
    pass


class APIError(ExpenseTrackerCLIError):
    """API communication errors."""
    pass


class AuthenticationError(APIError):
    """Authentication-related errors."""
    pass


class NotFoundError(APIError):
    """Resource not found errors."""
    pass


class ValidationError(ExpenseTrackerCLIError):
    """Data validation errors."""
    pass


class ImportError(ExpenseTrackerCLIError):
    """Import-related errors."""
    pass


class ExportError(ExpenseTrackerCLIError):
    """Export-related errors."""
    pass