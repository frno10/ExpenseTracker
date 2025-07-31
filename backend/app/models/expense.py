"""
Expense models for tracking financial transactions.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import Field, validator
from sqlalchemy import Boolean, Column, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from .base import BaseSchema, CreateSchema, UpdateSchema, UserOwnedTable


# Simple PaymentMethodSchema to avoid circular imports
class PaymentMethodSchema(BaseSchema):
    """Simple payment method schema for expense relationships."""
    name: str
    type: str

class PaymentMethodCreate(CreateSchema):
    """Simple payment method create schema."""
    name: str
    type: str  # Should be a PaymentType enum value
    account_number: Optional[str] = None
    institution: Optional[str] = None
    
    @validator("type")
    def validate_payment_type(cls, v):
        """Validate payment type is a valid enum value."""
        from . import PaymentType
        if isinstance(v, str):
            try:
                PaymentType(v)
                return v
            except ValueError:
                raise ValueError(f"Invalid payment type: {v}")
        return v

class PaymentMethodUpdate(UpdateSchema):
    """Simple payment method update schema."""
    name: Optional[str] = None
    type: Optional[str] = None
    account_number: Optional[str] = None
    institution: Optional[str] = None


class ExpenseTable(UserOwnedTable):
    """SQLAlchemy model for expenses."""
    
    __tablename__ = "expenses"
    
    amount = Column(Numeric(10, 2), nullable=False, index=True)
    description = Column(Text, nullable=True)
    expense_date = Column(Date, nullable=False, index=True)
    notes = Column(Text, nullable=True)
    is_recurring = Column(Boolean, default=False, nullable=False)
    
    # Foreign keys
    merchant_id = Column(PGUUID(as_uuid=True), ForeignKey("merchants.id"), nullable=True, index=True)
    category_id = Column(PGUUID(as_uuid=True), ForeignKey("categories.id"), nullable=False, index=True)
    payment_method_id = Column(PGUUID(as_uuid=True), ForeignKey("payment_methods.id"), nullable=False, index=True)
    statement_import_id = Column(PGUUID(as_uuid=True), ForeignKey("statement_imports.id"), nullable=True, index=True)
    recurring_expense_id = Column(PGUUID(as_uuid=True), ForeignKey("recurring_expenses.id"), nullable=True, index=True)
    
    # Relationships
    user = relationship("UserTable", back_populates="expenses")
    merchant = relationship("MerchantTable", back_populates="expenses")
    category = relationship("CategoryTable", back_populates="expenses")
    payment_method = relationship("PaymentMethodTable", back_populates="expenses")
    account = relationship("AccountTable", back_populates="expenses")
    statement_import = relationship("StatementImportTable", back_populates="expenses")
    recurring_expense = relationship("RecurringExpenseTable", back_populates="generated_expenses")
    attachments = relationship("AttachmentTable", back_populates="expense", cascade="all, delete-orphan")
    expense_tags = relationship("ExpenseTagTable", back_populates="expense", cascade="all, delete-orphan")


class ExpenseSchema(BaseSchema):
    """Pydantic schema for expense responses."""
    
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=500)
    expense_date: date
    notes: Optional[str] = Field(None, max_length=2000)
    is_recurring: bool = False
    
    # Foreign keys
    merchant_id: Optional[UUID] = None
    category_id: UUID
    payment_method_id: UUID
    statement_import_id: Optional[UUID] = None
    user_id: UUID
    
    # Nested relationships (optional for performance)
    merchant: Optional["MerchantSchema"] = None
    category: Optional["CategorySchema"] = None
    payment_method: Optional["PaymentMethodSchema"] = None
    statement_import: Optional["StatementImportSchema"] = None
    attachments: List["AttachmentSchema"] = Field(default_factory=list)
    tags: List["TagSchema"] = Field(default_factory=list)
    
    @validator("amount", pre=True)
    def validate_amount(cls, v):
        """Ensure amount is positive and has proper decimal places."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif isinstance(v, str):
            v = Decimal(v)
        
        if v <= 0:
            raise ValueError("Amount must be positive")
        
        # Round to 2 decimal places
        return v.quantize(Decimal("0.01"))


class ExpenseCreate(CreateSchema):
    """Schema for creating a new expense."""
    
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=500)
    expense_date: date = Field(default_factory=date.today)
    notes: Optional[str] = Field(None, max_length=2000)
    is_recurring: bool = False
    
    # Foreign keys
    merchant_id: Optional[UUID] = None
    category_id: UUID
    payment_method_id: UUID
    statement_import_id: Optional[UUID] = None
    user_id: UUID
    
    @validator("amount", pre=True)
    def validate_amount(cls, v):
        """Ensure amount is positive and has proper decimal places."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif isinstance(v, str):
            v = Decimal(v)
        
        if v <= 0:
            raise ValueError("Amount must be positive")
        
        return v.quantize(Decimal("0.01"))


class ExpenseUpdate(UpdateSchema):
    """Schema for updating an expense."""
    
    amount: Optional[Decimal] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=500)
    expense_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=2000)
    is_recurring: Optional[bool] = None
    
    # Foreign keys
    merchant_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    payment_method_id: Optional[UUID] = None
    statement_import_id: Optional[UUID] = None
    
    @validator("amount", pre=True)
    def validate_amount(cls, v):
        """Ensure amount is positive and has proper decimal places."""
        if v is None:
            return v
            
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif isinstance(v, str):
            v = Decimal(v)
        
        if v <= 0:
            raise ValueError("Amount must be positive")
        
        return v.quantize(Decimal("0.01"))