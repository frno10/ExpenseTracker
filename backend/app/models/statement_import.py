"""
Statement import models for tracking parsed bank statements.
"""
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import Field, validator
from sqlalchemy import Column, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SQLEnum

from .base import BaseSchema, BaseTable, CreateSchema, UpdateSchema, UserOwnedTable


class ImportStatus(str, Enum):
    """Enumeration of import statuses."""
    
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StatementImportTable(UserOwnedTable):
    """SQLAlchemy model for statement imports."""
    
    __tablename__ = "statement_imports"
    
    filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA-256
    bank_name = Column(String(100), nullable=True)
    account_number = Column(String(50), nullable=True)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    opening_balance = Column(Numeric(12, 2), nullable=True)
    closing_balance = Column(Numeric(12, 2), nullable=True)
    transaction_count = Column(Integer, nullable=False, default=0)
    imported_count = Column(Integer, nullable=False, default=0)
    status = Column(SQLEnum(ImportStatus), nullable=False, default=ImportStatus.PENDING)
    parsing_metadata = Column(JSONB, nullable=True)  # Parser-specific metadata
    error_message = Column(Text, nullable=True)
    
    # Foreign keys
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Relationships
    user = relationship("UserTable", back_populates="statement_imports")
    expenses = relationship("ExpenseTable", back_populates="statement_import")


class StatementImportSchema(BaseSchema):
    """Pydantic schema for statement import responses."""
    
    filename: str = Field(..., max_length=255)
    file_hash: str = Field(..., max_length=64)
    bank_name: Optional[str] = Field(None, max_length=100)
    account_number: Optional[str] = Field(None, max_length=50)
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    opening_balance: Optional[Decimal] = None
    closing_balance: Optional[Decimal] = None
    transaction_count: int = 0
    imported_count: int = 0
    status: ImportStatus = ImportStatus.PENDING
    parsing_metadata: Optional[dict] = None
    error_message: Optional[str] = None
    
    # Foreign keys
    user_id: UUID
    
    @property
    def import_success_rate(self) -> float:
        """Calculate the success rate of the import."""
        if self.transaction_count == 0:
            return 0.0
        return (self.imported_count / self.transaction_count) * 100
    
    @validator("opening_balance", "closing_balance", pre=True)
    def validate_balances(cls, v):
        """Ensure balances have proper decimal places."""
        if v is None:
            return v
            
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif isinstance(v, str):
            v = Decimal(v)
        
        return v.quantize(Decimal("0.01"))


class StatementImportCreate(CreateSchema):
    """Schema for creating a new statement import."""
    
    filename: str = Field(..., max_length=255)
    file_hash: str = Field(..., max_length=64)
    bank_name: Optional[str] = Field(None, max_length=100)
    account_number: Optional[str] = Field(None, max_length=50)
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    opening_balance: Optional[Decimal] = None
    closing_balance: Optional[Decimal] = None
    transaction_count: int = 0
    parsing_metadata: Optional[dict] = None
    
    # Foreign keys
    user_id: UUID
    
    @validator("opening_balance", "closing_balance", pre=True)
    def validate_balances(cls, v):
        """Ensure balances have proper decimal places."""
        if v is None:
            return v
            
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif isinstance(v, str):
            v = Decimal(v)
        
        return v.quantize(Decimal("0.01"))


class StatementImportUpdate(UpdateSchema):
    """Schema for updating a statement import."""
    
    bank_name: Optional[str] = Field(None, max_length=100)
    account_number: Optional[str] = Field(None, max_length=50)
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    opening_balance: Optional[Decimal] = None
    closing_balance: Optional[Decimal] = None
    transaction_count: Optional[int] = None
    imported_count: Optional[int] = None
    status: Optional[ImportStatus] = None
    parsing_metadata: Optional[dict] = None
    error_message: Optional[str] = None
    
    @validator("opening_balance", "closing_balance", pre=True)
    def validate_balances(cls, v):
        """Ensure balances have proper decimal places."""
        if v is None:
            return v
            
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif isinstance(v, str):
            v = Decimal(v)
        
        return v.quantize(Decimal("0.01"))