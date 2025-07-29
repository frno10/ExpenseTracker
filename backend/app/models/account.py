"""
Account models for tracking financial accounts and balances.
"""
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from uuid import UUID

from pydantic import Field, validator
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum as SQLEnum, 
    ForeignKey, Numeric, String, Text
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from .base import BaseSchema, CreateSchema, UpdateSchema, UserOwnedTable


class AccountType(str, Enum):
    """Types of financial accounts."""
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    CASH = "cash"
    INVESTMENT = "investment"
    LOAN = "loan"
    OTHER = "other"


class AccountStatus(str, Enum):
    """Account status types."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    CLOSED = "closed"
    SUSPENDED = "suspended"


class CurrencyCode(str, Enum):
    """Supported currency codes."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CAD = "CAD"
    AUD = "AUD"
    JPY = "JPY"
    CHF = "CHF"
    CNY = "CNY"


class AccountTable(UserOwnedTable):
    """SQLAlchemy model for financial accounts."""
    
    __tablename__ = "accounts"
    
    # Basic account information
    name = Column(String(100), nullable=False, index=True)
    account_type = Column(SQLEnum(AccountType), nullable=False, index=True)
    account_number = Column(String(50), nullable=True)  # Masked/last 4 digits
    institution = Column(String(100), nullable=True)
    
    # Account status and settings
    status = Column(SQLEnum(AccountStatus), nullable=False, default=AccountStatus.ACTIVE)
    currency = Column(SQLEnum(CurrencyCode), nullable=False, default=CurrencyCode.USD)
    
    # Balance tracking
    current_balance = Column(Numeric(15, 2), nullable=True)  # Current balance
    available_balance = Column(Numeric(15, 2), nullable=True)  # Available balance (for credit)
    credit_limit = Column(Numeric(15, 2), nullable=True)  # Credit limit for credit cards
    
    # Balance tracking settings
    track_balance = Column(Boolean, default=False)  # Whether to track balance
    auto_update_balance = Column(Boolean, default=False)  # Auto-update from transactions
    
    # Account metadata
    opening_date = Column(Date, nullable=True)
    closing_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    
    # Display settings
    color = Column(String(7), nullable=True)  # Hex color for UI
    icon = Column(String(50), nullable=True)  # Icon identifier
    sort_order = Column(Numeric(5, 2), default=0)  # Display order
    
    # Relationships
    user = relationship("UserTable", back_populates="accounts")
    payment_methods = relationship("PaymentMethodTable", back_populates="account")
    balance_history = relationship("AccountBalanceTable", back_populates="account", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Account(id={self.id}, name='{self.name}', type='{self.account_type}')>"
    
    @property
    def masked_account_number(self) -> Optional[str]:
        """Return masked account number for display."""
        if not self.account_number:
            return None
        if len(self.account_number) <= 4:
            return self.account_number
        return f"****{self.account_number[-4:]}"
    
    @property
    def is_credit_account(self) -> bool:
        """Check if this is a credit-based account."""
        return self.account_type in [AccountType.CREDIT_CARD, AccountType.LOAN]
    
    @property
    def available_credit(self) -> Optional[Decimal]:
        """Calculate available credit for credit accounts."""
        if not self.is_credit_account or not self.credit_limit:
            return None
        
        current_balance = self.current_balance or Decimal('0.00')
        return self.credit_limit - abs(current_balance)


class AccountBalanceTable(UserOwnedTable):
    """SQLAlchemy model for account balance history."""
    
    __tablename__ = "account_balances"
    
    account_id = Column(PGUUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    balance_date = Column(Date, nullable=False, index=True)
    balance_amount = Column(Numeric(15, 2), nullable=False)
    available_amount = Column(Numeric(15, 2), nullable=True)
    
    # Balance change tracking
    change_amount = Column(Numeric(15, 2), nullable=True)  # Change from previous balance
    change_reason = Column(String(100), nullable=True)  # Reason for balance change
    
    # Source of balance update
    source = Column(String(50), nullable=True)  # 'manual', 'transaction', 'import', 'api'
    notes = Column(Text, nullable=True)
    
    # Relationships
    account = relationship("AccountTable", back_populates="balance_history")
    
    def __repr__(self):
        return f"<AccountBalance(account_id={self.account_id}, date={self.balance_date}, amount={self.balance_amount})>"


# Enhanced Payment Method Model
class PaymentMethodTable(UserOwnedTable):
    """Enhanced SQLAlchemy model for payment methods."""
    
    __tablename__ = "payment_methods"
    
    # Basic payment method information
    name = Column(String(100), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)  # Changed from enum for flexibility
    
    # Account association
    account_id = Column(PGUUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True, index=True)
    
    # Payment method details
    last_four_digits = Column(String(4), nullable=True)  # Last 4 digits for cards
    expiry_month = Column(String(2), nullable=True)  # MM format
    expiry_year = Column(String(4), nullable=True)  # YYYY format
    
    # Status and settings
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Display settings
    color = Column(String(7), nullable=True)  # Hex color
    icon = Column(String(50), nullable=True)  # Icon identifier
    
    # Metadata
    notes = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("UserTable", back_populates="payment_methods")
    account = relationship("AccountTable", back_populates="payment_methods")
    expenses = relationship("ExpenseTable", back_populates="payment_method")
    
    def __repr__(self):
        return f"<PaymentMethod(id={self.id}, name='{self.name}', type='{self.type}')>"
    
    @property
    def display_name(self) -> str:
        """Generate display name for payment method."""
        if self.last_four_digits:
            return f"{self.name} ****{self.last_four_digits}"
        return self.name
    
    @property
    def is_expired(self) -> bool:
        """Check if payment method is expired (for cards)."""
        if not self.expiry_month or not self.expiry_year:
            return False
        
        try:
            expiry_date = date(int(self.expiry_year), int(self.expiry_month), 1)
            # Add one month and subtract one day to get last day of expiry month
            if expiry_date.month == 12:
                last_day = date(expiry_date.year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = date(expiry_date.year, expiry_date.month + 1, 1) - timedelta(days=1)
            
            return date.today() > last_day
        except (ValueError, TypeError):
            return False


# Pydantic Schemas

class AccountSchema(BaseSchema):
    """Pydantic schema for account responses."""
    
    name: str = Field(..., min_length=1, max_length=100)
    account_type: AccountType
    account_number: Optional[str] = Field(None, max_length=50)
    institution: Optional[str] = Field(None, max_length=100)
    status: AccountStatus = AccountStatus.ACTIVE
    currency: CurrencyCode = CurrencyCode.USD
    
    current_balance: Optional[Decimal] = Field(None, decimal_places=2)
    available_balance: Optional[Decimal] = Field(None, decimal_places=2)
    credit_limit: Optional[Decimal] = Field(None, decimal_places=2)
    
    track_balance: bool = False
    auto_update_balance: bool = False
    
    opening_date: Optional[date] = None
    closing_date: Optional[date] = None
    description: Optional[str] = None
    
    color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$')
    icon: Optional[str] = Field(None, max_length=50)
    sort_order: Decimal = Field(Decimal('0.00'), decimal_places=2)
    
    # Computed properties
    masked_account_number: Optional[str] = None
    is_credit_account: bool = False
    available_credit: Optional[Decimal] = None
    
    user_id: UUID
    
    class Config:
        from_attributes = True
    
    @validator('current_balance', 'available_balance', 'credit_limit', pre=True)
    def validate_amounts(cls, v):
        """Ensure amounts have proper decimal places."""
        if v is None:
            return v
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif isinstance(v, str):
            v = Decimal(v)
        return v.quantize(Decimal("0.01"))


class AccountCreate(CreateSchema):
    """Schema for creating a new account."""
    
    name: str = Field(..., min_length=1, max_length=100)
    account_type: AccountType
    account_number: Optional[str] = Field(None, max_length=50)
    institution: Optional[str] = Field(None, max_length=100)
    currency: CurrencyCode = CurrencyCode.USD
    
    current_balance: Optional[Decimal] = Field(None, decimal_places=2)
    available_balance: Optional[Decimal] = Field(None, decimal_places=2)
    credit_limit: Optional[Decimal] = Field(None, decimal_places=2)
    
    track_balance: bool = False
    auto_update_balance: bool = False
    
    opening_date: Optional[date] = None
    description: Optional[str] = None
    
    color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$')
    icon: Optional[str] = Field(None, max_length=50)
    sort_order: Decimal = Field(Decimal('0.00'), decimal_places=2)
    
    user_id: UUID
    
    @validator('current_balance', 'available_balance', 'credit_limit', pre=True)
    def validate_amounts(cls, v):
        """Ensure amounts have proper decimal places."""
        if v is None:
            return v
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif isinstance(v, str):
            v = Decimal(v)
        return v.quantize(Decimal("0.01"))


class AccountUpdate(UpdateSchema):
    """Schema for updating an account."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    account_number: Optional[str] = Field(None, max_length=50)
    institution: Optional[str] = Field(None, max_length=100)
    status: Optional[AccountStatus] = None
    currency: Optional[CurrencyCode] = None
    
    current_balance: Optional[Decimal] = Field(None, decimal_places=2)
    available_balance: Optional[Decimal] = Field(None, decimal_places=2)
    credit_limit: Optional[Decimal] = Field(None, decimal_places=2)
    
    track_balance: Optional[bool] = None
    auto_update_balance: Optional[bool] = None
    
    opening_date: Optional[date] = None
    closing_date: Optional[date] = None
    description: Optional[str] = None
    
    color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$')
    icon: Optional[str] = Field(None, max_length=50)
    sort_order: Optional[Decimal] = Field(None, decimal_places=2)
    
    @validator('current_balance', 'available_balance', 'credit_limit', 'sort_order', pre=True)
    def validate_amounts(cls, v):
        """Ensure amounts have proper decimal places."""
        if v is None:
            return v
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif isinstance(v, str):
            v = Decimal(v)
        return v.quantize(Decimal("0.01"))


class AccountBalanceSchema(BaseSchema):
    """Pydantic schema for account balance responses."""
    
    account_id: UUID
    balance_date: date
    balance_amount: Decimal = Field(..., decimal_places=2)
    available_amount: Optional[Decimal] = Field(None, decimal_places=2)
    change_amount: Optional[Decimal] = Field(None, decimal_places=2)
    change_reason: Optional[str] = Field(None, max_length=100)
    source: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    user_id: UUID
    
    class Config:
        from_attributes = True
    
    @validator('balance_amount', 'available_amount', 'change_amount', pre=True)
    def validate_amounts(cls, v):
        """Ensure amounts have proper decimal places."""
        if v is None:
            return v
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif isinstance(v, str):
            v = Decimal(v)
        return v.quantize(Decimal("0.01"))


class AccountBalanceCreate(CreateSchema):
    """Schema for creating account balance records."""
    
    account_id: UUID
    balance_date: date = Field(default_factory=date.today)
    balance_amount: Decimal = Field(..., decimal_places=2)
    available_amount: Optional[Decimal] = Field(None, decimal_places=2)
    change_amount: Optional[Decimal] = Field(None, decimal_places=2)
    change_reason: Optional[str] = Field(None, max_length=100)
    source: str = Field("manual", max_length=50)
    notes: Optional[str] = None
    user_id: UUID
    
    @validator('balance_amount', 'available_amount', 'change_amount', pre=True)
    def validate_amounts(cls, v):
        """Ensure amounts have proper decimal places."""
        if v is None:
            return v
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif isinstance(v, str):
            v = Decimal(v)
        return v.quantize(Decimal("0.01"))


class EnhancedPaymentMethodSchema(BaseSchema):
    """Enhanced Pydantic schema for payment method responses."""
    
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., max_length=50)
    account_id: Optional[UUID] = None
    
    last_four_digits: Optional[str] = Field(None, max_length=4, regex=r'^\d{4}$')
    expiry_month: Optional[str] = Field(None, regex=r'^(0[1-9]|1[0-2])$')
    expiry_year: Optional[str] = Field(None, regex=r'^\d{4}$')
    
    is_active: bool = True
    is_default: bool = False
    
    color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$')
    icon: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    
    # Computed properties
    display_name: str = ""
    is_expired: bool = False
    
    user_id: UUID
    
    # Nested relationships
    account: Optional[AccountSchema] = None
    
    class Config:
        from_attributes = True


class EnhancedPaymentMethodCreate(CreateSchema):
    """Schema for creating enhanced payment methods."""
    
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., max_length=50)
    account_id: Optional[UUID] = None
    
    last_four_digits: Optional[str] = Field(None, max_length=4, regex=r'^\d{4}$')
    expiry_month: Optional[str] = Field(None, regex=r'^(0[1-9]|1[0-2])$')
    expiry_year: Optional[str] = Field(None, regex=r'^\d{4}$')
    
    is_active: bool = True
    is_default: bool = False
    
    color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$')
    icon: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    
    user_id: UUID


class EnhancedPaymentMethodUpdate(UpdateSchema):
    """Schema for updating enhanced payment methods."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[str] = Field(None, max_length=50)
    account_id: Optional[UUID] = None
    
    last_four_digits: Optional[str] = Field(None, max_length=4, regex=r'^\d{4}$')
    expiry_month: Optional[str] = Field(None, regex=r'^(0[1-9]|1[0-2])$')
    expiry_year: Optional[str] = Field(None, regex=r'^\d{4}$')
    
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    
    color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$')
    icon: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None