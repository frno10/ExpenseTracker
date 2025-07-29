from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from sqlalchemy import Column, String, Numeric, DateTime, Boolean, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class PaymentMethodType(str, Enum):
    """Payment method types."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    DIGITAL_WALLET = "digital_wallet"
    CHECK = "check"
    OTHER = "other"


class AccountType(str, Enum):
    """Account types."""
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    CASH = "cash"
    INVESTMENT = "investment"
    OTHER = "other"


class PaymentMethodTable(Base):
    """Payment method model for tracking different payment types."""
    
    __tablename__ = "payment_methods"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Payment method details
    name = Column(String(100), nullable=False)  # e.g., "Chase Sapphire", "Wells Fargo Checking"
    type = Column(ENUM(PaymentMethodType), nullable=False)
    description = Column(Text, nullable=True)
    
    # Account information
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True)
    
    # Card/Account details (encrypted in production)
    last_four_digits = Column(String(4), nullable=True)  # Last 4 digits for cards
    institution_name = Column(String(100), nullable=True)  # Bank/Institution name
    
    # Status and settings
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # Display settings
    color = Column(String(7), nullable=True)  # Hex color for UI
    icon = Column(String(50), nullable=True)  # Icon identifier
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="payment_methods")
    account = relationship("AccountTable", back_populates="payment_methods")
    expenses = relationship("ExpenseTable", back_populates="payment_method")
    
    def __repr__(self):
        return f"<PaymentMethod(id={self.id}, name='{self.name}', type='{self.type}')>"
    
    @property
    def display_name(self) -> str:
        """Get display name with masked details."""
        if self.last_four_digits:
            return f"{self.name} ****{self.last_four_digits}"
        return self.name
    
    @property
    def is_cash(self) -> bool:
        """Check if this is a cash payment method."""
        return self.type == PaymentMethodType.CASH
    
    @property
    def is_card(self) -> bool:
        """Check if this is a card payment method."""
        return self.type in [PaymentMethodType.CREDIT_CARD, PaymentMethodType.DEBIT_CARD]


class AccountTable(Base):
    """Account model for tracking different financial accounts."""
    
    __tablename__ = "accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Account details
    name = Column(String(100), nullable=False)  # e.g., "Chase Checking", "Cash Wallet"
    type = Column(ENUM(AccountType), nullable=False)
    description = Column(Text, nullable=True)
    
    # Institution information
    institution_name = Column(String(100), nullable=True)
    account_number_last_four = Column(String(4), nullable=True)
    
    # Balance tracking
    current_balance = Column(Numeric(12, 2), default=Decimal('0.00'))
    available_balance = Column(Numeric(12, 2), nullable=True)  # For credit accounts
    credit_limit = Column(Numeric(12, 2), nullable=True)  # For credit accounts
    
    # Balance management
    track_balance = Column(Boolean, default=True)  # Whether to track balance
    auto_update_balance = Column(Boolean, default=False)  # Auto-update from expenses
    last_balance_update = Column(DateTime, nullable=True)
    
    # Cash-specific settings
    low_balance_warning = Column(Numeric(10, 2), nullable=True)  # Warn when balance is low
    
    # Status and settings
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # Display settings
    color = Column(String(7), nullable=True)  # Hex color for UI
    icon = Column(String(50), nullable=True)  # Icon identifier
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="accounts")
    payment_methods = relationship("PaymentMethodTable", back_populates="account")
    expenses = relationship("ExpenseTable", back_populates="account")
    balance_history = relationship("AccountBalanceHistory", back_populates="account", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Account(id={self.id}, name='{self.name}', type='{self.type}', balance={self.current_balance})>"
    
    @property
    def display_name(self) -> str:
        """Get display name with masked details."""
        if self.account_number_last_four:
            return f"{self.name} ****{self.account_number_last_four}"
        return self.name
    
    @property
    def is_cash_account(self) -> bool:
        """Check if this is a cash account."""
        return self.type == AccountType.CASH
    
    @property
    def is_credit_account(self) -> bool:
        """Check if this is a credit account."""
        return self.type == AccountType.CREDIT_CARD
    
    @property
    def available_credit(self) -> Optional[Decimal]:
        """Calculate available credit for credit accounts."""
        if self.is_credit_account and self.credit_limit:
            return self.credit_limit + self.current_balance  # Balance is negative for credit
        return None
    
    @property
    def is_low_balance(self) -> bool:
        """Check if account has low balance."""
        if self.low_balance_warning and self.current_balance <= self.low_balance_warning:
            return True
        return False
    
    @property
    def utilization_percentage(self) -> Optional[float]:
        """Calculate credit utilization percentage."""
        if self.is_credit_account and self.credit_limit and self.credit_limit > 0:
            used_credit = abs(self.current_balance)  # Balance is negative for credit
            return float((used_credit / self.credit_limit) * 100)
        return None


class AccountBalanceHistory(Base):
    """Historical balance tracking for accounts."""
    
    __tablename__ = "account_balance_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    
    # Balance information
    balance = Column(Numeric(12, 2), nullable=False)
    previous_balance = Column(Numeric(12, 2), nullable=True)
    change_amount = Column(Numeric(12, 2), nullable=True)
    
    # Change details
    change_reason = Column(String(100), nullable=True)  # 'expense', 'manual_adjustment', 'transfer'
    related_expense_id = Column(UUID(as_uuid=True), ForeignKey("expenses.id"), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Metadata
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    account = relationship("AccountTable", back_populates="balance_history")
    related_expense = relationship("ExpenseTable")
    
    def __repr__(self):
        return f"<BalanceHistory(account_id={self.account_id}, balance={self.balance}, recorded_at={self.recorded_at})>"


class AccountTransfer(Base):
    """Model for tracking transfers between accounts."""
    
    __tablename__ = "account_transfers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Transfer details
    from_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    to_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    
    # Transfer information
    description = Column(String(255), nullable=True)
    transfer_date = Column(DateTime, default=datetime.utcnow)
    
    # Status
    is_completed = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    from_account = relationship("AccountTable", foreign_keys=[from_account_id])
    to_account = relationship("AccountTable", foreign_keys=[to_account_id])
    
    def __repr__(self):
        return f"<Transfer(id={self.id}, amount={self.amount}, from={self.from_account_id}, to={self.to_account_id})>"