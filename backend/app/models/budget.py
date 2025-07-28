"""
Budget models for expense tracking and limits.
"""
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import Field, validator
from sqlalchemy import Boolean, Column, Date, Enum as SQLEnum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from .base import BaseSchema, BaseTable, CreateSchema, UpdateSchema, UserOwnedTable


class BudgetPeriod(str, Enum):
    """Enumeration of budget periods."""
    
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class BudgetTable(UserOwnedTable):
    """SQLAlchemy model for budgets."""
    
    __tablename__ = "budgets"
    
    name = Column(String(100), nullable=False, index=True)
    period = Column(SQLEnum(BudgetPeriod), nullable=False, default=BudgetPeriod.MONTHLY)
    total_limit = Column(Numeric(10, 2), nullable=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("UserTable", back_populates="budgets")
    category_budgets = relationship("CategoryBudgetTable", back_populates="budget", cascade="all, delete-orphan")


class CategoryBudgetTable(BaseTable):
    """SQLAlchemy model for category-specific budget limits."""
    
    __tablename__ = "category_budgets"
    
    limit_amount = Column(Numeric(10, 2), nullable=False)
    spent_amount = Column(Numeric(10, 2), nullable=False, default=0)
    
    # Foreign keys
    budget_id = Column(PGUUID(as_uuid=True), ForeignKey("budgets.id"), nullable=False, index=True)
    category_id = Column(PGUUID(as_uuid=True), ForeignKey("categories.id"), nullable=False, index=True)
    
    # Relationships
    budget = relationship("BudgetTable", back_populates="category_budgets")
    category = relationship("CategoryTable")


class CategoryBudgetSchema(BaseSchema):
    """Pydantic schema for category budget responses."""
    
    limit_amount: Decimal = Field(..., gt=0)
    spent_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    
    # Foreign keys
    budget_id: UUID
    category_id: UUID
    
    # Nested relationships
    category: Optional["CategorySchema"] = None
    
    @property
    def remaining_amount(self) -> Decimal:
        """Calculate remaining budget amount."""
        return self.limit_amount - self.spent_amount
    
    @property
    def percentage_used(self) -> float:
        """Calculate percentage of budget used."""
        if self.limit_amount == 0:
            return 0.0
        return float((self.spent_amount / self.limit_amount) * 100)
    
    @property
    def is_over_budget(self) -> bool:
        """Check if budget is exceeded."""
        return self.spent_amount > self.limit_amount
    
    @validator("limit_amount", "spent_amount", pre=True)
    def validate_amounts(cls, v):
        """Ensure amounts have proper decimal places."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif isinstance(v, str):
            v = Decimal(v)
        
        return v.quantize(Decimal("0.01"))


class BudgetSchema(BaseSchema):
    """Pydantic schema for budget responses."""
    
    name: str = Field(..., min_length=1, max_length=100)
    period: BudgetPeriod = BudgetPeriod.MONTHLY
    total_limit: Optional[Decimal] = Field(None, gt=0)
    start_date: date
    end_date: Optional[date] = None
    is_active: bool = True
    user_id: UUID
    
    # Nested relationships
    category_budgets: List[CategoryBudgetSchema] = Field(default_factory=list)
    
    @property
    def total_spent(self) -> Decimal:
        """Calculate total spent across all categories."""
        return sum(cb.spent_amount for cb in self.category_budgets)
    
    @property
    def total_remaining(self) -> Optional[Decimal]:
        """Calculate total remaining budget."""
        if self.total_limit is None:
            return None
        return self.total_limit - self.total_spent
    
    @validator("total_limit", pre=True)
    def validate_total_limit(cls, v):
        """Ensure total limit has proper decimal places."""
        if v is None:
            return v
            
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif isinstance(v, str):
            v = Decimal(v)
        
        return v.quantize(Decimal("0.01"))
    
    @validator("end_date")
    def validate_end_date(cls, v, values):
        """Ensure end date is after start date."""
        if v is not None and "start_date" in values and v <= values["start_date"]:
            raise ValueError("End date must be after start date")
        return v


class BudgetCreate(CreateSchema):
    """Schema for creating a new budget."""
    
    name: str = Field(..., min_length=1, max_length=100)
    period: BudgetPeriod = BudgetPeriod.MONTHLY
    total_limit: Optional[Decimal] = Field(None, gt=0)
    start_date: date = Field(default_factory=date.today)
    end_date: Optional[date] = None
    is_active: bool = True
    user_id: UUID
    
    @validator("total_limit", pre=True)
    def validate_total_limit(cls, v):
        """Ensure total limit has proper decimal places."""
        if v is None:
            return v
            
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif isinstance(v, str):
            v = Decimal(v)
        
        return v.quantize(Decimal("0.01"))
    
    @validator("end_date")
    def validate_end_date(cls, v, values):
        """Ensure end date is after start date."""
        if v is not None and "start_date" in values and v <= values["start_date"]:
            raise ValueError("End date must be after start date")
        return v


class BudgetUpdate(UpdateSchema):
    """Schema for updating a budget."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    period: Optional[BudgetPeriod] = None
    total_limit: Optional[Decimal] = Field(None, gt=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None
    
    @validator("total_limit", pre=True)
    def validate_total_limit(cls, v):
        """Ensure total limit has proper decimal places."""
        if v is None:
            return v
            
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif isinstance(v, str):
            v = Decimal(v)
        
        return v.quantize(Decimal("0.01"))


class CategoryBudgetCreate(CreateSchema):
    """Schema for creating a new category budget."""
    
    limit_amount: Decimal = Field(..., gt=0)
    
    # Foreign keys
    budget_id: UUID
    category_id: UUID
    
    @validator("limit_amount", pre=True)
    def validate_limit_amount(cls, v):
        """Ensure limit amount has proper decimal places."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif isinstance(v, str):
            v = Decimal(v)
        
        return v.quantize(Decimal("0.01"))


class CategoryBudgetUpdate(UpdateSchema):
    """Schema for updating a category budget."""
    
    limit_amount: Optional[Decimal] = Field(None, gt=0)
    
    @validator("limit_amount", pre=True)
    def validate_limit_amount(cls, v):
        """Ensure limit amount has proper decimal places."""
        if v is None:
            return v
            
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif isinstance(v, str):
            v = Decimal(v)
        
        return v.quantize(Decimal("0.01"))