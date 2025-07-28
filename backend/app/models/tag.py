"""
Tag models for flexible categorization.
"""
from typing import Optional
from uuid import UUID

from pydantic import Field
from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from .base import BaseSchema, BaseTable, CreateSchema, UpdateSchema


class TagTable(BaseTable):
    """SQLAlchemy model for tags."""
    
    __tablename__ = "tags"
    
    name = Column(String(100), nullable=False, index=True)
    color = Column(String(7), nullable=False, default="#6B7280")  # Hex color
    icon = Column(String(50), nullable=True)
    
    # Foreign keys
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Relationships
    user = relationship("UserTable", back_populates="tags")
    merchant_tags = relationship("MerchantTagTable", back_populates="tag", cascade="all, delete-orphan")
    expense_tags = relationship("ExpenseTagTable", back_populates="tag", cascade="all, delete-orphan")


class ExpenseTagTable(BaseTable):
    """SQLAlchemy model for expense-tag relationships."""
    
    __tablename__ = "expense_tags"
    
    # Foreign keys
    expense_id = Column(PGUUID(as_uuid=True), ForeignKey("expenses.id"), nullable=False, primary_key=True)
    tag_id = Column(PGUUID(as_uuid=True), ForeignKey("tags.id"), nullable=False, primary_key=True)
    
    # Relationships
    expense = relationship("ExpenseTable", back_populates="expense_tags")
    tag = relationship("TagTable", back_populates="expense_tags")
    
    # Override BaseTable fields for junction table
    id = None
    created_at = None
    updated_at = None


class TagSchema(BaseSchema):
    """Pydantic schema for tag responses."""
    
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)
    
    # Foreign keys
    user_id: UUID


class TagCreate(CreateSchema):
    """Schema for creating a new tag."""
    
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#6B7280", pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)
    
    # Foreign keys
    user_id: UUID


class TagUpdate(UpdateSchema):
    """Schema for updating a tag."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)