"""
Category models for expense categorization.
"""
from typing import List, Optional
from uuid import UUID

from pydantic import Field
from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from .base import BaseSchema, CreateSchema, UpdateSchema, UserOwnedTable


class CategoryTable(UserOwnedTable):
    """SQLAlchemy model for expense categories."""
    
    __tablename__ = "categories"
    
    name = Column(String(100), nullable=False, index=True)
    color = Column(String(7), nullable=False, default="#6B7280")  # Hex color
    icon = Column(String(50), nullable=True)
    parent_category_id = Column(PGUUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    is_custom = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("UserTable", back_populates="categories")
    parent_category = relationship("CategoryTable", remote_side="CategoryTable.id", back_populates="subcategories")
    subcategories = relationship("CategoryTable", back_populates="parent_category")
    expenses = relationship("ExpenseTable", back_populates="category")


class CategorySchema(BaseSchema):
    """Pydantic schema for category responses."""
    
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)
    parent_category_id: Optional[UUID] = None
    is_custom: bool = True
    user_id: UUID
    
    # Nested relationships (optional for performance)
    parent_category: Optional["CategorySchema"] = None
    subcategories: List["CategorySchema"] = Field(default_factory=list)


class CategoryCreate(CreateSchema):
    """Schema for creating a new category."""
    
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#6B7280", pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)
    parent_category_id: Optional[UUID] = None
    is_custom: bool = True
    user_id: UUID


class CategoryUpdate(UpdateSchema):
    """Schema for updating a category."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)
    parent_category_id: Optional[UUID] = None


# Update forward references
CategorySchema.model_rebuild()