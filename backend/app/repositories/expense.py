"""
Expense repository for database operations.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ExpenseCreate, ExpenseTable, ExpenseUpdate
from .base import BaseRepository


class ExpenseRepository(BaseRepository[ExpenseTable, ExpenseCreate, ExpenseUpdate]):
    """Repository for expense-related database operations."""
    
    def __init__(self):
        super().__init__(ExpenseTable)
    
    async def get_by_date_range(
        self,
        db: AsyncSession,
        start_date: date,
        end_date: date,
        *,
        category_id: Optional[UUID] = None,
        payment_method_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ExpenseTable]:
        """
        Get expenses within a date range with optional filters.
        
        Args:
            db: Database session
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            category_id: Optional category filter
            payment_method_id: Optional payment method filter
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of expense instances
        """
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.expense_date >= start_date,
                    self.model.expense_date <= end_date
                )
            )
            .options(
                selectinload(self.model.category),
                selectinload(self.model.payment_method),
                selectinload(self.model.attachments)
            )
            .order_by(desc(self.model.expense_date), desc(self.model.created_at))
        )
        
        # Apply optional filters
        if category_id:
            query = query.where(self.model.category_id == category_id)
        if payment_method_id:
            query = query.where(self.model.payment_method_id == payment_method_id)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_total_by_category(
        self,
        db: AsyncSession,
        start_date: date,
        end_date: date
    ) -> List[Tuple[UUID, str, Decimal]]:
        """
        Get total expenses by category within a date range.
        
        Args:
            db: Database session
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of tuples (category_id, category_name, total_amount)
        """
        from app.models import CategoryTable
        
        query = (
            select(
                CategoryTable.id,
                CategoryTable.name,
                func.sum(self.model.amount).label("total_amount")
            )
            .join(CategoryTable, self.model.category_id == CategoryTable.id)
            .where(
                and_(
                    self.model.expense_date >= start_date,
                    self.model.expense_date <= end_date
                )
            )
            .group_by(CategoryTable.id, CategoryTable.name)
            .order_by(desc("total_amount"))
        )
        
        result = await db.execute(query)
        return result.all()
    
    async def get_total_by_payment_method(
        self,
        db: AsyncSession,
        start_date: date,
        end_date: date
    ) -> List[Tuple[UUID, str, Decimal]]:
        """
        Get total expenses by payment method within a date range.
        
        Args:
            db: Database session
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of tuples (payment_method_id, payment_method_name, total_amount)
        """
        from app.models import PaymentMethodTable
        
        query = (
            select(
                PaymentMethodTable.id,
                PaymentMethodTable.name,
                func.sum(self.model.amount).label("total_amount")
            )
            .join(PaymentMethodTable, self.model.payment_method_id == PaymentMethodTable.id)
            .where(
                and_(
                    self.model.expense_date >= start_date,
                    self.model.expense_date <= end_date
                )
            )
            .group_by(PaymentMethodTable.id, PaymentMethodTable.name)
            .order_by(desc("total_amount"))
        )
        
        result = await db.execute(query)
        return result.all()
    
    async def get_monthly_totals(
        self,
        db: AsyncSession,
        year: int,
        category_id: Optional[UUID] = None
    ) -> List[Tuple[int, Decimal]]:
        """
        Get monthly expense totals for a given year.
        
        Args:
            db: Database session
            year: Year to get totals for
            category_id: Optional category filter
            
        Returns:
            List of tuples (month, total_amount)
        """
        query = (
            select(
                func.extract('month', self.model.expense_date).label("month"),
                func.sum(self.model.amount).label("total_amount")
            )
            .where(func.extract('year', self.model.expense_date) == year)
            .group_by(func.extract('month', self.model.expense_date))
            .order_by("month")
        )
        
        if category_id:
            query = query.where(self.model.category_id == category_id)
        
        result = await db.execute(query)
        return result.all()
    
    async def get_total_amount(
        self,
        db: AsyncSession,
        start_date: date,
        end_date: date,
        *,
        category_id: Optional[UUID] = None,
        payment_method_id: Optional[UUID] = None
    ) -> Decimal:
        """
        Get total expense amount within a date range with optional filters.
        
        Args:
            db: Database session
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            category_id: Optional category filter
            payment_method_id: Optional payment method filter
            
        Returns:
            Total expense amount
        """
        query = (
            select(func.sum(self.model.amount))
            .where(
                and_(
                    self.model.expense_date >= start_date,
                    self.model.expense_date <= end_date
                )
            )
        )
        
        # Apply optional filters
        if category_id:
            query = query.where(self.model.category_id == category_id)
        if payment_method_id:
            query = query.where(self.model.payment_method_id == payment_method_id)
        
        result = await db.execute(query)
        total = result.scalar()
        return total or Decimal("0.00")
    
    async def get_recent_expenses(
        self,
        db: AsyncSession,
        limit: int = 10
    ) -> List[ExpenseTable]:
        """
        Get the most recent expenses.
        
        Args:
            db: Database session
            limit: Maximum number of expenses to return
            
        Returns:
            List of recent expense instances
        """
        query = (
            select(self.model)
            .options(
                selectinload(self.model.category),
                selectinload(self.model.payment_method)
            )
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def search_expenses(
        self,
        db: AsyncSession,
        search_term: str,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[ExpenseTable]:
        """
        Search expenses by description or notes.
        
        Args:
            db: Database session
            search_term: Search term to look for
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching expense instances
        """
        search_pattern = f"%{search_term}%"
        
        query = (
            select(self.model)
            .where(
                or_(
                    self.model.description.ilike(search_pattern),
                    self.model.notes.ilike(search_pattern)
                )
            )
            .options(
                selectinload(self.model.category),
                selectinload(self.model.payment_method)
            )
            .order_by(desc(self.model.expense_date))
            .offset(skip)
            .limit(limit)
        )
        
        result = await db.execute(query)
        return result.scalars().all()


# Create repository instance
expense_repository = ExpenseRepository()