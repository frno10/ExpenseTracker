"""
Expense service for managing expenses and integrating with budget tracking.
"""
import logging
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import ExpenseCreate, ExpenseTable, ExpenseUpdate
from app.repositories.expense import expense_repository
from app.services.budget_service import BudgetService
from app.services.websocket_manager import notify_expense_created, notify_expense_updated, notify_expense_deleted

logger = logging.getLogger(__name__)


class ExpenseService:
    """Service for expense management with budget integration."""
    
    def __init__(self):
        self.expense_repo = expense_repository
        self.budget_service = BudgetService()
    
    async def create_expense(
        self,
        db: AsyncSession,
        expense_data: ExpenseCreate,
        user_id: UUID
    ) -> ExpenseTable:
        """
        Create a new expense and update related budgets.
        
        Args:
            db: Database session
            expense_data: Expense creation data
            user_id: User ID
            
        Returns:
            Created expense instance
        """
        logger.info(f"Creating expense for user {user_id}: {expense_data.amount}")
        
        # Ensure expense belongs to the user
        expense_data.user_id = user_id
        
        # Create the expense
        expense = await self.expense_repo.create(db, expense_data)
        
        # Update budget spending for this expense
        await self._update_budgets_for_expense(db, expense)
        
        # Send real-time notification
        expense_dict = {
            "id": str(expense.id),
            "amount": float(expense.amount),
            "description": expense.description,
            "category": expense.category.name if expense.category else None,
            "date": expense.date.isoformat(),
            "created_at": expense.created_at.isoformat()
        }
        await notify_expense_created(str(user_id), expense_dict)
        
        logger.info(f"Created expense {expense.id} and updated budgets")
        return expense
    
    async def update_expense(
        self,
        db: AsyncSession,
        expense_id: UUID,
        expense_data: ExpenseUpdate,
        user_id: UUID
    ) -> Optional[ExpenseTable]:
        """
        Update an expense and recalculate related budgets.
        
        Args:
            db: Database session
            expense_id: Expense ID
            expense_data: Expense update data
            user_id: User ID
            
        Returns:
            Updated expense instance or None if not found
        """
        logger.info(f"Updating expense {expense_id} for user {user_id}")
        
        # Get the original expense to compare changes
        original_expense = await self.expense_repo.get_by_id(db, expense_id)
        if not original_expense or original_expense.user_id != user_id:
            return None
        
        # Update the expense
        updated_expense = await self.expense_repo.update(db, expense_id, expense_data)
        if not updated_expense:
            return None
        
        # Check if budget-relevant fields changed
        budget_relevant_changed = (
            expense_data.amount is not None or
            expense_data.category_id is not None or
            expense_data.date is not None
        )
        
        if budget_relevant_changed:
            # Recalculate budgets for the user
            await self.budget_service.recalculate_user_budgets(db, user_id)
        
        # Send real-time notification
        expense_dict = {
            "id": str(updated_expense.id),
            "amount": float(updated_expense.amount),
            "description": updated_expense.description,
            "category": updated_expense.category.name if updated_expense.category else None,
            "date": updated_expense.date.isoformat(),
            "updated_at": updated_expense.updated_at.isoformat()
        }
        await notify_expense_updated(str(user_id), expense_dict)
        
        logger.info(f"Updated expense {expense_id} and recalculated budgets")
        return updated_expense
    
    async def delete_expense(
        self,
        db: AsyncSession,
        expense_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Delete an expense and recalculate related budgets.
        
        Args:
            db: Database session
            expense_id: Expense ID
            user_id: User ID
            
        Returns:
            True if deleted successfully, False otherwise
        """
        logger.info(f"Deleting expense {expense_id} for user {user_id}")
        
        # Get the expense to verify ownership
        expense = await self.expense_repo.get_by_id(db, expense_id)
        if not expense or expense.user_id != user_id:
            return False
        
        # Delete the expense
        success = await self.expense_repo.delete(db, expense_id)
        if success:
            # Recalculate budgets for the user
            await self.budget_service.recalculate_user_budgets(db, user_id)
            
            # Send real-time notification
            await notify_expense_deleted(str(user_id), str(expense_id))
            
            logger.info(f"Deleted expense {expense_id} and recalculated budgets")
        
        return success
    
    async def get_expense(
        self,
        db: AsyncSession,
        expense_id: UUID,
        user_id: UUID
    ) -> Optional[ExpenseTable]:
        """
        Get an expense by ID for a specific user.
        
        Args:
            db: Database session
            expense_id: Expense ID
            user_id: User ID
            
        Returns:
            Expense instance or None if not found
        """
        expense = await self.expense_repo.get_by_id(db, expense_id)
        if expense and expense.user_id == user_id:
            return expense
        return None
    
    async def get_user_expenses(
        self,
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[UUID] = None,
        payment_method_id: Optional[UUID] = None,
        merchant_id: Optional[UUID] = None
    ) -> List[ExpenseTable]:
        """
        Get expenses for a user with optional filtering.
        
        Args:
            db: Database session
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            start_date: Filter from this date
            end_date: Filter until this date
            category_id: Filter by category
            payment_method_id: Filter by payment method
            merchant_id: Filter by merchant
            
        Returns:
            List of expense instances
        """
        if start_date and end_date:
            expenses = await self.expense_repo.get_by_date_range(
                db,
                start_date=start_date,
                end_date=end_date,
                category_id=category_id,
                payment_method_id=payment_method_id,
                skip=skip,
                limit=limit
            )
            # Filter by user
            return [e for e in expenses if e.user_id == user_id]
        else:
            # Build filters
            filters = {"user_id": user_id}
            if category_id:
                filters["category_id"] = category_id
            if payment_method_id:
                filters["payment_method_id"] = payment_method_id
            if merchant_id:
                filters["merchant_id"] = merchant_id
            
            return await self.expense_repo.get_multi(
                db, skip=skip, limit=limit, **filters
            )
    
    async def get_expense_summary(
        self,
        db: AsyncSession,
        user_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> dict:
        """
        Get expense summary for a user.
        
        Args:
            db: Database session
            user_id: User ID
            start_date: Summary from this date
            end_date: Summary until this date
            
        Returns:
            Dictionary with expense summary data
        """
        # Get expenses for the period
        expenses = await self.get_user_expenses(
            db, user_id, start_date=start_date, end_date=end_date, limit=10000
        )
        
        if not expenses:
            return {
                "total_amount": Decimal("0.00"),
                "total_count": 0,
                "average_amount": Decimal("0.00"),
                "category_breakdown": {},
                "daily_totals": {}
            }
        
        # Calculate totals
        total_amount = sum(expense.amount for expense in expenses)
        total_count = len(expenses)
        average_amount = total_amount / total_count if total_count > 0 else Decimal("0.00")
        
        # Category breakdown
        category_breakdown = {}
        for expense in expenses:
            category_name = expense.category.name if expense.category else "Uncategorized"
            if category_name not in category_breakdown:
                category_breakdown[category_name] = {
                    "amount": Decimal("0.00"),
                    "count": 0
                }
            category_breakdown[category_name]["amount"] += expense.amount
            category_breakdown[category_name]["count"] += 1
        
        # Daily totals
        daily_totals = {}
        for expense in expenses:
            date_str = expense.date.isoformat()
            if date_str not in daily_totals:
                daily_totals[date_str] = Decimal("0.00")
            daily_totals[date_str] += expense.amount
        
        return {
            "total_amount": total_amount,
            "total_count": total_count,
            "average_amount": average_amount,
            "category_breakdown": category_breakdown,
            "daily_totals": daily_totals
        }
    
    async def _update_budgets_for_expense(
        self,
        db: AsyncSession,
        expense: ExpenseTable
    ) -> None:
        """
        Update budgets when a new expense is created.
        
        Args:
            db: Database session
            expense: Expense instance
        """
        try:
            # Get category name for budget matching
            category_name = expense.category.name if expense.category else "Uncategorized"
            
            # Find and update affected budgets
            affected_budgets = await self.budget_service.get_budgets_for_category(
                db, expense.user_id, category_name, expense.date
            )
            
            for budget in affected_budgets:
                # Update budget spending
                await self.budget_service._update_budget_spending(db, budget)
                
                # Check for alerts
                alerts = await self.budget_service.check_budget_alerts(
                    db, expense.user_id, budget.id
                )
                
                if alerts:
                    logger.info(f"Generated {len(alerts)} budget alerts for expense {expense.id}")
        
        except Exception as e:
            logger.error(f"Failed to update budgets for expense {expense.id}: {e}")
            # Don't fail the expense creation if budget update fails


# Create service instance
expense_service = ExpenseService()