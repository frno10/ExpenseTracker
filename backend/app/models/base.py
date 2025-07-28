"""
Base models and common utilities for the expense tracker.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func


# SQLAlchemy Base
Base = declarative_base()


class BaseTable(Base):
    """Base table with common fields for all entities."""
    
    __abstract__ = True
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UserOwnedTable(BaseTable):
    """Base table for entities owned by users."""
    
    __abstract__ = True
    
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)


class BaseSchema(BaseModel):
    """Base Pydantic schema with common fields."""
    
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class CreateSchema(BaseModel):
    """Base schema for create operations (no id, timestamps)."""
    
    class Config:
        from_attributes = True


class UpdateSchema(BaseModel):
    """Base schema for update operations (optional fields)."""
    
    class Config:
        from_attributes = True