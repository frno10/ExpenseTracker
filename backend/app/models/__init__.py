"""
Data models package for the expense tracker.

This package contains all Pydantic schemas and SQLAlchemy models
for the expense tracking system.
"""

# Base models
from .base import Base, BaseSchema, BaseTable, CreateSchema, UpdateSchema, UserOwnedTable

# Core entity models
from .attachment import (
    AttachmentCreate,
    AttachmentSchema,
    AttachmentTable,
    AttachmentType,
    AttachmentUpdate,
)
from .budget import (
    BudgetCreate,
    BudgetPeriod,
    BudgetSchema,
    BudgetTable,
    BudgetUpdate,
    CategoryBudgetCreate,
    CategoryBudgetSchema,
    CategoryBudgetTable,
    CategoryBudgetUpdate,
)
from .category import (
    CategoryCreate,
    CategorySchema,
    CategoryTable,
    CategoryUpdate,
)
from .expense import (
    ExpenseCreate,
    ExpenseSchema,
    ExpenseTable,
    ExpenseUpdate,
    PaymentMethodSchema,
    PaymentMethodCreate,
    PaymentMethodUpdate,
)
from .merchant import (
    MerchantCreate,
    MerchantSchema,
    MerchantTable,
    MerchantTagTable,
    MerchantUpdate,
)
from .payment_method import (
    PaymentMethodTable, AccountTable, AccountBalanceHistory, AccountTransfer,
    PaymentMethodType, AccountType
)
# Define PaymentType enum directly to avoid import conflicts
from enum import Enum

class PaymentType(str, Enum):
    """Enumeration of supported payment types."""
    CASH = "cash"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    CHECK = "check"
    DIGITAL_WALLET = "digital_wallet"
    OTHER = "other"
from .recurring_expense import (
    RecurringExpenseTable, RecurringExpenseHistoryTable, RecurringExpenseNotificationTable,
    RecurrenceFrequency, RecurrenceStatus
)
from .statement_import import (
    ImportStatus,
    StatementImportCreate,
    StatementImportSchema,
    StatementImportTable,
    StatementImportUpdate,
)
from .tag import (
    ExpenseTagTable,
    TagCreate,
    TagSchema,
    TagTable,
    TagUpdate,
)
from .user import (
    UserCreate,
    UserSchema,
    UserTable,
    UserUpdate,
)

# Update forward references for all schemas
UserSchema.model_rebuild()
CategorySchema.model_rebuild()
MerchantSchema.model_rebuild()
TagSchema.model_rebuild()
# PaymentMethodSchema.model_rebuild()  # Will be handled in expense.py
ExpenseSchema.model_rebuild()
AttachmentSchema.model_rebuild()
BudgetSchema.model_rebuild()
CategoryBudgetSchema.model_rebuild()
StatementImportSchema.model_rebuild()

__all__ = [
    # Base
    "Base",
    "BaseSchema",
    "BaseTable",
    "CreateSchema",
    "UpdateSchema",
    "UserOwnedTable",
    # Attachment
    "AttachmentCreate",
    "AttachmentSchema",
    "AttachmentTable",
    "AttachmentType",
    "AttachmentUpdate",
    # Budget
    "BudgetCreate",
    "BudgetPeriod",
    "BudgetSchema",
    "BudgetTable",
    "BudgetUpdate",
    "CategoryBudgetCreate",
    "CategoryBudgetSchema",
    "CategoryBudgetTable",
    "CategoryBudgetUpdate",
    # Category
    "CategoryCreate",
    "CategorySchema",
    "CategoryTable",
    "CategoryUpdate",
    # Expense
    "ExpenseCreate",
    "ExpenseSchema",
    "ExpenseTable",
    "ExpenseUpdate",
    "PaymentMethodSchema",
    "PaymentMethodCreate",
    "PaymentMethodUpdate",
    # Merchant
    "MerchantCreate",
    "MerchantSchema",
    "MerchantTable",
    "MerchantTagTable",
    "MerchantUpdate",
    # Payment Method
    "PaymentMethodTable",
    "PaymentType",
    "AccountTable",
    "AccountBalanceHistory",
    "AccountTransfer",
    "PaymentMethodType",
    "AccountType",
    # Recurring Expense
    "RecurringExpenseTable",
    "RecurringExpenseHistoryTable", 
    "RecurringExpenseNotificationTable",
    "RecurrenceFrequency",
    "RecurrenceStatus",
    # Statement Import
    "ImportStatus",
    "StatementImportCreate",
    "StatementImportSchema",
    "StatementImportTable",
    "StatementImportUpdate",
    # Tag
    "ExpenseTagTable",
    "TagCreate",
    "TagSchema",
    "TagTable",
    "TagUpdate",
    # User
    "UserCreate",
    "UserSchema",
    "UserTable",
    "UserUpdate",
]