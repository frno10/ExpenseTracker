"""
Attachment models for expense receipts and documents.
"""
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import Field, validator
from sqlalchemy import Column, Enum as SQLEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from .base import BaseSchema, CreateSchema, UpdateSchema, UserOwnedTable


class AttachmentType(str, Enum):
    """Enumeration of supported attachment types."""
    
    RECEIPT = "receipt"
    INVOICE = "invoice"
    DOCUMENT = "document"
    IMAGE = "image"
    OTHER = "other"


class AttachmentTable(UserOwnedTable):
    """SQLAlchemy model for expense attachments."""
    
    __tablename__ = "attachments"
    
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    attachment_type = Column(SQLEnum(AttachmentType), nullable=False, default=AttachmentType.RECEIPT)
    
    # Foreign key
    expense_id = Column(PGUUID(as_uuid=True), ForeignKey("expenses.id"), nullable=False, index=True)
    
    # Relationships
    user = relationship("UserTable", back_populates="attachments")
    expense = relationship("ExpenseTable", back_populates="attachments")


class AttachmentSchema(BaseSchema):
    """Pydantic schema for attachment responses."""
    
    filename: str = Field(..., max_length=255)
    original_filename: str = Field(..., max_length=255)
    file_path: str = Field(..., max_length=500)
    file_size: int = Field(..., gt=0)
    mime_type: str = Field(..., max_length=100)
    attachment_type: AttachmentType = AttachmentType.RECEIPT
    
    # Foreign key
    expense_id: UUID
    user_id: UUID
    
    @validator("file_size")
    def validate_file_size(cls, v):
        """Validate file size is reasonable (max 10MB)."""
        max_size = 10 * 1024 * 1024  # 10MB
        if v > max_size:
            raise ValueError(f"File size cannot exceed {max_size} bytes")
        return v


class AttachmentCreate(CreateSchema):
    """Schema for creating a new attachment."""
    
    filename: str = Field(..., max_length=255)
    original_filename: str = Field(..., max_length=255)
    file_path: str = Field(..., max_length=500)
    file_size: int = Field(..., gt=0)
    mime_type: str = Field(..., max_length=100)
    attachment_type: AttachmentType = AttachmentType.RECEIPT
    
    # Foreign key
    expense_id: UUID
    user_id: UUID
    
    @validator("file_size")
    def validate_file_size(cls, v):
        """Validate file size is reasonable (max 10MB)."""
        max_size = 10 * 1024 * 1024  # 10MB
        if v > max_size:
            raise ValueError(f"File size cannot exceed {max_size} bytes")
        return v


class AttachmentUpdate(UpdateSchema):
    """Schema for updating an attachment."""
    
    filename: Optional[str] = Field(None, max_length=255)
    original_filename: Optional[str] = Field(None, max_length=255)
    attachment_type: Optional[AttachmentType] = None