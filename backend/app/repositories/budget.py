"""
Budget repository for database operations.
"""
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    BudgetCreate,
    BudgetTable,
    BudgetUpdate,
    CategoryBudgetCreate,
    CategoryBudgetTable,
    CategoryBudgetUpdate,
)
from .base import BaseRepository


class BudgetRepository(BaseRepository[BudgetTable, BudgetCreate, BudgetUpdate]):
    """Repository for budget-related database operations."""
    
    def __init__(self):
        super().__init__(BudgetTable)
    
    async def get_active_budgets(
        self, 
        db: AsyncSession,
        current_date: Optional[date] = None
    ) -> List[BudgetTable]:
        """
        Get all active budgets for the current date.
        
        Args:
            db: Database session
            current_date: Date to check against (defaults to today)
            
        Returns:
            List of active budget instances
        """
        if current_date is None:
            current_date = date.today()
        
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.is_active == True,
                    self.model.start_date <= current_date,
                    or_(
                        self.model.end_date.is_(None),
                        self.model.end_date >= current_date
                    )
                )
            )
            .options(selectinload(self.model.category_budgets))
        )
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_budget_for_period(
        self,
        db: AsyncSession,
        start_date: date,
        end_date: date
    ) -> List[BudgetTable]:
        """
        Get budgets that overlap with a specific period.
        
        Args:
            db: Database session
            start_date: Period start date
            end_date: Period end date
            
        Returns:
            List of budget instances
        """
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.start_date <= end_date,
                    or_(
                        self.model.end_date.is_(None),
                        self.model.end_date >= start_date
                    )
                )
            )
            .options(selectinload(self.model.category_budgets))
        )
        
        result = await db.execute(query)
        return result.scalars().all()


class CategoryBudgetRepository(BaseRepository[CategoryBudgetTable, CategoryBudgetCreate, CategoryBudgetUpdate]):
    """Repository for category budget-related database operations."""
    
    def __init__(self):
        super().__init__(CategoryBudgetTable)
    
    async def get_by_budget_and_category(
        self,
        db: AsyncSession,
        budget_id: UUID,
        category_id: UUID
    ) -> Optional[CategoryBudgetTable]:
        """
        Get a category budget by budget and category IDs.
        
        Args:
            db: Database session
            budget_id: Budget ID
            category_id: Category ID
            
        Returns:
            Category budget instance or None if not found
        """
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.budget_id == budget_id,
                    self.model.category_id == category_id
                )
            )
            .options(selectinload(self.model.category))
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_budget(
        self,
        db: AsyncSession,
        budget_id: UUID
    ) -> List[CategoryBudgetTable]:
        """
        Get all category budgets for a specific budget.
        
        Args:
            db: Database session
            budget_id: Budget ID
            
        Returns:
            List of category budget instances
        """
        query = (
            select(self.model)
            .where(self.model.budget_id == budget_id)
            .options(selectinload(self.model.category))
        )
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def update_spent_amount(
        self,
        db: AsyncSession,
        budget_id: UUID,
        category_id: UUID,
        amount_change: Decimal
    ) -> Optional[CategoryBudgetTable]:
        """
        Update the spent amount for a category budget.
        
        Args:
            db: Database session
            budget_id: Budget ID
            category_id: Category ID
            amount_change: Amount to add to spent_amount (can be negative)
            
        Returns:
            Updated category budget instance or None if not found
        """
        # Update the spent amount
        query = (
            update(self.model)
            .where(
                and_(
                    self.model.budget_id == budget_id,
                    self.model.category_id == category_id
                )
            )
            .values(spent_amount=self.model.spent_amount + amount_change)
        )
        
        await db.execute(query)
        await db.commit()
        
        # Return the updated instance
        return await self.get_by_budget_and_category(db, budget_id, category_id)
    
    async def get_over_budget_categories(
        self,
        db: AsyncSession,
        budget_id: UUID
    ) -> List[CategoryBudgetTable]:
        """
        Get all category budgets that are over their limit.
        
        Args:
            db: Database session
            budget_id: Budget ID
            
        Returns:
            List of over-budget category budget instances
        """
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.budget_id == budget_id,
                    self.model.spent_amount > self.model.limit_amount
                )
            )
            .options(selectinload(self.model.category))
        )
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_near_budget_categories(
        self,
        db: AsyncSession,
        budget_id: UUID,
        threshold_percentage: float = 80.0
    ) -> List[CategoryBudgetTable]:
        """
        Get category budgets that are near their limit (above threshold percentage).
        
        Args:
            db: Database session
            budget_id: Budget ID
            threshold_percentage: Percentage threshold (default 80%)
            
        Returns:
            List of near-budget category budget instances
        """
        threshold_decimal = threshold_percentage / 100.0
        
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.budget_id == budget_id,
                    self.model.spent_amount >= (self.model.limit_amount * threshold_decimal),
                    self.model.spent_amount <= self.model.limit_amount
                )
            )
            .options(selectinload(self.model.category))
        )
        
        result = await db.execute(query)
        return result.scalars().all()


# Create repository instances
budget_repository = BudgetRepository()
category_budget_repository = CategoryBudgetRepository()