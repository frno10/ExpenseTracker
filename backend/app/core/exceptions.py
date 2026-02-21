"""
Custom exceptions for the Expense Tracker application.
"""


class ValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(self, message: str = "Validation error"):
        self.message = message
        super().__init__(self.message)


class NotFoundError(Exception):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str = "Resource not found"):
        self.message = message
        super().__init__(self.message)


class BusinessLogicError(Exception):
    """Raised when a business rule is violated."""

    def __init__(self, message: str = "Business logic error"):
        self.message = message
        super().__init__(self.message)


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        self.message = message
        super().__init__(self.message)


class AuthorizationError(Exception):
    """Raised when authorization fails."""

    def __init__(self, message: str = "Insufficient permissions"):
        self.message = message
        super().__init__(self.message)
