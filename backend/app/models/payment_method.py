"""
Payment method models for tracking different payment types.
"""
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import Field
from sqlalchemy import Boolean, Column, Enum as SQLEnum, String
from sqlalchemy.orm import relationship

from .base import BaseSchema, CreateSchema, UpdateSchema, UserOwnedTable


class PaymentType(str, Enum):
    """Enumeration of supported payment types."""
    
    CASH = "cash"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    CHECK = "check"
    DIGITAL_WALLET = "digital_wallet"
    OTHER = "other"


class PaymentMethodTable(UserOwnedTable):
    """SQLAlchemy model for payment methods."""
    
    __tablename__ = "payment_methods"
    
    name = Column(String(100), nullable=False, index=True)
    type = Column(SQLEnum(PaymentType), nullable=False, index=True)
    account_number = Column(String(50), nullable=True)  # Last 4 digits or identifier
    institution = Column(String(100), nullable=True)  # Bank or institution name
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("UserTable", back_populates="payment_methods")
    expenses = relationship("ExpenseTable", back_populates="payment_method")


class PaymentMethodSchema(BaseSchema):
    """Pydantic schema for payment method responses."""
    
    name: str = Field(..., min_length=1, max_length=100)
    type: PaymentType
    account_number: Optional[str] = Field(None, max_length=50)
    institution: Optional[str] = Field(None, max_length=100)
    is_active: bool = True
    user_id: UUID


class PaymentMethodCreate(CreateSchema):
    """Schema for creating a new payment method."""
    
    name: str = Field(..., min_length=1, max_length=100)
    type: PaymentType
    account_number: Optional[str] = Field(None, max_length=50)
    institution: Optional[str] = Field(None, max_length=100)
    is_active: bool = True
    user_id: UUID


class PaymentMethodUpdate(UpdateSchema):
    """Schema for updating a payment method."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[PaymentType] = None
    account_number: Optional[str] = Field(None, max_length=50)
    institution: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None