"""
Merchant models for vendor/payee tracking.
"""
from typing import List, Optional
from uuid import UUID

from pydantic import Field
from sqlalchemy import Column, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from .base import BaseSchema, BaseTable, CreateSchema, UpdateSchema


class MerchantTable(BaseTable):
    """SQLAlchemy model for merchants/vendors."""
    
    __tablename__ = "merchants"
    
    name = Column(String(255), nullable=False, index=True)
    normalized_name = Column(String(255), nullable=False, index=True)  # For matching
    address = Column(Text, nullable=True)
    merchant_identifier = Column(String(100), nullable=True)  # External ID
    notes = Column(Text, nullable=True)
    
    # Foreign keys
    default_category_id = Column(PGUUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Relationships
    user = relationship("UserTable", back_populates="merchants")
    default_category = relationship("CategoryTable")
    expenses = relationship("ExpenseTable", back_populates="merchant")
    merchant_tags = relationship("MerchantTagTable", back_populates="merchant", cascade="all, delete-orphan")


class MerchantTagTable(BaseTable):
    """SQLAlchemy model for merchant-tag relationships."""
    
    __tablename__ = "merchant_tags"
    
    # Foreign keys
    merchant_id = Column(PGUUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False, primary_key=True)
    tag_id = Column(PGUUID(as_uuid=True), ForeignKey("tags.id"), nullable=False, primary_key=True)
    
    # Relationships
    merchant = relationship("MerchantTable", back_populates="merchant_tags")
    tag = relationship("TagTable", back_populates="merchant_tags")
    
    # Override BaseTable fields for junction table
    id = None
    created_at = None
    updated_at = None


class MerchantSchema(BaseSchema):
    """Pydantic schema for merchant responses."""
    
    name: str = Field(..., min_length=1, max_length=255)
    normalized_name: str = Field(..., min_length=1, max_length=255)
    address: Optional[str] = None
    merchant_identifier: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    
    # Foreign keys
    default_category_id: Optional[UUID] = None
    user_id: UUID
    
    # Nested relationships (optional for performance)
    default_category: Optional["CategorySchema"] = None
    tags: List["TagSchema"] = Field(default_factory=list)


class MerchantCreate(CreateSchema):
    """Schema for creating a new merchant."""
    
    name: str = Field(..., min_length=1, max_length=255)
    address: Optional[str] = None
    merchant_identifier: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    
    # Foreign keys
    default_category_id: Optional[UUID] = None
    user_id: UUID
    
    normalized_name: Optional[str] = None
    
    def __init__(self, **data):
        # Auto-generate normalized name for matching
        if 'normalized_name' not in data and 'name' in data:
            data['normalized_name'] = self._normalize_name(data['name'])
        super().__init__(**data)
    
    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize merchant name for matching."""
        import re
        # Remove common business suffixes and normalize
        normalized = re.sub(r'\b(LLC|INC|CORP|LTD|CO)\b', '', name.upper())
        normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove punctuation
        normalized = re.sub(r'\s+', ' ', normalized).strip()  # Normalize whitespace
        return normalized


class MerchantUpdate(UpdateSchema):
    """Schema for updating a merchant."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = None
    merchant_identifier: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    
    # Foreign keys
    default_category_id: Optional[UUID] = None