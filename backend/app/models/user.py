"""
User models for multi-user support.
"""
from typing import Optional

from pydantic import Field, EmailStr
from sqlalchemy import Boolean, Column, String
from sqlalchemy.orm import relationship

from .base import BaseSchema, BaseTable, CreateSchema, UpdateSchema


class UserTable(BaseTable):
    """SQLAlchemy model for users."""
    
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=True)
    timezone = Column(String(50), nullable=False, default="UTC")
    currency = Column(String(3), nullable=False, default="USD")
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    categories = relationship("CategoryTable", back_populates="user", cascade="all, delete-orphan")
    payment_methods = relationship("PaymentMethodTable", back_populates="user", cascade="all, delete-orphan")
    expenses = relationship("ExpenseTable", back_populates="user", cascade="all, delete-orphan")
    budgets = relationship("BudgetTable", back_populates="user", cascade="all, delete-orphan")
    merchants = relationship("MerchantTable", back_populates="user", cascade="all, delete-orphan")
    tags = relationship("TagTable", back_populates="user", cascade="all, delete-orphan")
    attachments = relationship("AttachmentTable", back_populates="user", cascade="all, delete-orphan")
    statement_imports = relationship("StatementImportTable", back_populates="user", cascade="all, delete-orphan")


class UserSchema(BaseSchema):
    """Pydantic schema for user responses."""
    
    email: EmailStr
    name: Optional[str] = None
    timezone: str = "UTC"
    currency: str = "USD"
    is_active: bool = True


class UserCreate(CreateSchema):
    """Schema for creating a new user."""
    
    email: EmailStr
    name: Optional[str] = None
    timezone: str = "UTC"
    currency: str = "USD"
    is_active: bool = True


class UserUpdate(UpdateSchema):
    """Schema for updating a user."""
    
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None