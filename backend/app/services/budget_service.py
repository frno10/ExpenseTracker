"""
Budget service for managing budgets, tracking spending, and generating alerts.
"""
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import (
    BudgetCreate,
    BudgetPeriod,
    BudgetSchema,
    BudgetTable,
    BudgetUpdate,
    CategoryBudgetCreate,
    CategoryBudgetSchema,
    CategoryBudgetTable,
    CategoryBudgetUpdate,
)
from app.models.expense import ExpenseTable
from app.repositories.budget import budget_repository, category_budget_repository
from app.repositories.expense import expense_repository

logger = logging.getLogger(__name__)


class BudgetAlert:
    """Represents a budget alert."""
    
    def __init__(
        self,
        budget_id: UUID,
        category_id: Optional[UUID],
        alert_type: str,
        message: str,
        percentage_used: float,
        amount_spent: Decimal,
        amount_limit: Decimal,
        amount_remaining: Decimal
    ):
        self.budget_id = budget_id
        self.category_id = category_id
        self.alert_type = alert_type  # 'warning' (80%) or 'exceeded' (100%+)
        self.message = message
        self.percentage_used = percentage_used
        self.amount_spent = amount_spent
        self.amount_limit = amount_limit
        self.amount_remaining = amount_remaining


class BudgetService:
    """Service for budget management and tracking."""
    
    def __init__(self):
        self.budget_repo = budget_repository
        self.category_budget_repo = category_budget_repository
        self.expense_repo = expense_repository
    
    async def create_budget(
        self,
        db: AsyncSession,
        budget_data: BudgetCreate,
        category_budgets: Optional[List[CategoryBudgetCreate]] = None
    ) -> BudgetTable:
        """
        Create a new budget with optional category budgets.
        
        Args:
            db: Database session
            budget_data: Budget creation data
            category_budgets: Optional list of category budget data
            
        Returns:
            Created budget instance
        """
        logger.info(f"Creating budget: {budget_data.name}")
        
        # Create the main budget
        budget = await self.budget_repo.create(db, budget_data)
        
        # Create category budgets if provided
        if category_budgets:
            for category_budget_data in category_budgets:
                category_budget_data.budget_id = budget.id
                await self.category_budget_repo.create(db, category_budget_data)
        
        # Reload budget with category budgets
        budget = await self.budget_repo.get_by_id(db, budget.id)
        
        logger.info(f"Created budget {budget.id} with {len(category_budgets or [])} category budgets")
        return budget
    
    async def update_budget(
        self,
        db: AsyncSession,
        budget_id: UUID,
        budget_data: BudgetUpdate,
        user_id: UUID
    ) -> Optional[BudgetTable]:
        """
        Update an existing budget.
        
        Args:
            db: Database session
            budget_id: Budget ID to update
            budget_data: Budget update data
            user_id: User ID for authorization
            
        Returns:
            Updated budget instance or None if not found
        """
        logger.info(f"Updating budget: {budget_id}")
        
        budget = await self.budget_repo.update(db, budget_id, budget_data, user_id)
        if budget:
            logger.info(f"Updated budget {budget_id}")
        else:
            logger.warning(f"Budget {budget_id} not found for user {user_id}")
        
        return budget
    
    async def delete_budget(
        self,
        db: AsyncSession,
        budget_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Delete a budget and all its category budgets.
        
        Args:
            db: Database session
            budget_id: Budget ID to delete
            user_id: User ID for authorization
            
        Returns:
            True if deleted, False if not found
        """
        logger.info(f"Deleting budget: {budget_id}")
        
        success = await self.budget_repo.delete(db, budget_id, user_id)
        if success:
            logger.info(f"Deleted budget {budget_id}")
        else:
            logger.warning(f"Budget {budget_id} not found for user {user_id}")
        
        return success
    
    async def get_user_budgets(
        self,
        db: AsyncSession,
        user_id: UUID,
        active_only: bool = False
    ) -> List[BudgetTable]:
        """
        Get all budgets for a user.
        
        Args:
            db: Database session
            user_id: User ID
            active_only: If True, only return active budgets
            
        Returns:
            List of budget instances
        """
        if active_only:
            budgets = await self.budget_repo.get_active_budgets(db)
            return [b for b in budgets if b.user_id == user_id]
        else:
            return await self.budget_repo.get_by_user_id(db, user_id)
    
    async def get_budget_with_spending(
        self,
        db: AsyncSession,
        budget_id: UUID,
        user_id: UUID
    ) -> Optional[BudgetTable]:
        """
        Get a budget with updated spending amounts.
        
        Args:
            db: Database session
            budget_id: Budget ID
            user_id: User ID for authorization
            
        Returns:
            Budget instance with updated spending or None if not found
        """
        budget = await self.budget_repo.get_by_id(db, budget_id)
        if not budget or budget.user_id != user_id:
            return None
        
        # Update spending amounts for all category budgets
        await self._update_budget_spending(db, budget)
        
        return budget
    
    async def add_category_budget(
        self,
        db: AsyncSession,
        category_budget_data: CategoryBudgetCreate,
        user_id: UUID
    ) -> Optional[CategoryBudgetTable]:
        """
        Add a category budget to an existing budget.
        
        Args:
            db: Database session
            category_budget_data: Category budget creation data
            user_id: User ID for authorization
            
        Returns:
            Created category budget instance or None if budget not found
        """
        # Verify budget exists and belongs to user
        budget = await self.budget_repo.get_by_id(db, category_budget_data.budget_id)
        if not budget or budget.user_id != user_id:
            return None
        
        # Check if category budget already exists
        existing = await self.category_budget_repo.get_by_budget_and_category(
            db, category_budget_data.budget_id, category_budget_data.category_id
        )
        if existing:
            logger.warning(f"Category budget already exists for budget {category_budget_data.budget_id} and category {category_budget_data.category_id}")
            return None
        
        logger.info(f"Adding category budget to budget {category_budget_data.budget_id}")
        return await self.category_budget_repo.create(db, category_budget_data)
    
    async def update_category_budget(
        self,
        db: AsyncSession,
        category_budget_id: UUID,
        category_budget_data: CategoryBudgetUpdate,
        user_id: UUID
    ) -> Optional[CategoryBudgetTable]:
        """
        Update a category budget.
        
        Args:
            db: Database session
            category_budget_id: Category budget ID to update
            category_budget_data: Category budget update data
            user_id: User ID for authorization
            
        Returns:
            Updated category budget instance or None if not found
        """
        # Get category budget and verify ownership
        category_budget = await self.category_budget_repo.get_by_id(db, category_budget_id)
        if not category_budget:
            return None
        
        budget = await self.budget_repo.get_by_id(db, category_budget.budget_id)
        if not budget or budget.user_id != user_id:
            return None
        
        logger.info(f"Updating category budget: {category_budget_id}")
        return await self.category_budget_repo.update(db, category_budget_id, category_budget_data)
    
    async def remove_category_budget(
        self,
        db: AsyncSession,
        category_budget_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Remove a category budget.
        
        Args:
            db: Database session
            category_budget_id: Category budget ID to remove
            user_id: User ID for authorization
            
        Returns:
            True if removed, False if not found
        """
        # Get category budget and verify ownership
        category_budget = await self.category_budget_repo.get_by_id(db, category_budget_id)
        if not category_budget:
            return False
        
        budget = await self.budget_repo.get_by_id(db, category_budget.budget_id)
        if not budget or budget.user_id != user_id:
            return False
        
        logger.info(f"Removing category budget: {category_budget_id}")
        return await self.category_budget_repo.delete(db, category_budget_id)
    
    async def check_budget_alerts(
        self,
        db: AsyncSession,
        user_id: UUID,
        budget_id: Optional[UUID] = None
    ) -> List[BudgetAlert]:
        """
        Check for budget alerts (80% warning and 100% exceeded).
        
        Args:
            db: Database session
            user_id: User ID
            budget_id: Optional specific budget ID to check
            
        Returns:
            List of budget alerts
        """
        alerts = []
        
        # Get budgets to check
        if budget_id:
            budgets = [await self.budget_repo.get_by_id(db, budget_id)]
            budgets = [b for b in budgets if b and b.user_id == user_id]
        else:
            budgets = await self.get_user_budgets(db, user_id, active_only=True)
        
        for budget in budgets:
            # Update spending amounts
            await self._update_budget_spending(db, budget)
            
            # Check total budget alerts
            if budget.total_limit:
                total_spent = sum(cb.spent_amount for cb in budget.category_budgets)
                percentage = float((total_spent / budget.total_limit) * 100)
                
                if percentage >= 100:
                    alerts.append(BudgetAlert(
                        budget_id=budget.id,
                        category_id=None,
                        alert_type="exceeded",
                        message=f"Budget '{budget.name}' has been exceeded by ${total_spent - budget.total_limit:.2f}",
                        percentage_used=percentage,
                        amount_spent=total_spent,
                        amount_limit=budget.total_limit,
                        amount_remaining=budget.total_limit - total_spent
                    ))
                elif percentage >= 80:
                    alerts.append(BudgetAlert(
                        budget_id=budget.id,
                        category_id=None,
                        alert_type="warning",
                        message=f"Budget '{budget.name}' is {percentage:.1f}% used",
                        percentage_used=percentage,
                        amount_spent=total_spent,
                        amount_limit=budget.total_limit,
                        amount_remaining=budget.total_limit - total_spent
                    ))
            
            # Check category budget alerts
            for category_budget in budget.category_budgets:
                percentage = float((category_budget.spent_amount / category_budget.limit_amount) * 100)
                category_name = category_budget.category.name if category_budget.category else "Unknown"
                
                if percentage >= 100:
                    alerts.append(BudgetAlert(
                        budget_id=budget.id,
                        category_id=category_budget.category_id,
                        alert_type="exceeded",
                        message=f"Category '{category_name}' in budget '{budget.name}' has been exceeded by ${category_budget.spent_amount - category_budget.limit_amount:.2f}",
                        percentage_used=percentage,
                        amount_spent=category_budget.spent_amount,
                        amount_limit=category_budget.limit_amount,
                        amount_remaining=category_budget.limit_amount - category_budget.spent_amount
                    ))
                elif percentage >= 80:
                    alerts.append(BudgetAlert(
                        budget_id=budget.id,
                        category_id=category_budget.category_id,
                        alert_type="warning",
                        message=f"Category '{category_name}' in budget '{budget.name}' is {percentage:.1f}% used",
                        percentage_used=percentage,
                        amount_spent=category_budget.spent_amount,
                        amount_limit=category_budget.limit_amount,
                        amount_remaining=category_budget.limit_amount - category_budget.spent_amount
                    ))
        
        logger.info(f"Found {len(alerts)} budget alerts for user {user_id}")
        return alerts
    
    async def get_budget_progress(
        self,
        db: AsyncSession,
        budget_id: UUID,
        user_id: UUID
    ) -> Optional[Dict]:
        """
        Get detailed budget progress information.
        
        Args:
            db: Database session
            budget_id: Budget ID
            user_id: User ID for authorization
            
        Returns:
            Budget progress data or None if not found
        """
        budget = await self.get_budget_with_spending(db, budget_id, user_id)
        if not budget:
            return None
        
        total_spent = sum(cb.spent_amount for cb in budget.category_budgets)
        
        progress = {
            "budget_id": budget.id,
            "budget_name": budget.name,
            "period": budget.period,
            "start_date": budget.start_date,
            "end_date": budget.end_date,
            "total_limit": budget.total_limit,
            "total_spent": total_spent,
            "total_remaining": budget.total_limit - total_spent if budget.total_limit else None,
            "total_percentage": float((total_spent / budget.total_limit) * 100) if budget.total_limit else None,
            "categories": []
        }
        
        for category_budget in budget.category_budgets:
            category_progress = {
                "category_id": category_budget.category_id,
                "category_name": category_budget.category.name if category_budget.category else "Unknown",
                "limit_amount": category_budget.limit_amount,
                "spent_amount": category_budget.spent_amount,
                "remaining_amount": category_budget.limit_amount - category_budget.spent_amount,
                "percentage_used": float((category_budget.spent_amount / category_budget.limit_amount) * 100),
                "is_over_budget": category_budget.spent_amount > category_budget.limit_amount
            }
            progress["categories"].append(category_progress)
        
        return progress
    
    async def create_recurring_budget(
        self,
        db: AsyncSession,
        base_budget_id: UUID,
        user_id: UUID,
        next_period_start: date
    ) -> Optional[BudgetTable]:
        """
        Create a new budget based on an existing budget for the next period.
        
        Args:
            db: Database session
            base_budget_id: Base budget ID to copy from
            user_id: User ID for authorization
            next_period_start: Start date for the new budget period
            
        Returns:
            Created budget instance or None if base budget not found
        """
        base_budget = await self.budget_repo.get_by_id(db, base_budget_id)
        if not base_budget or base_budget.user_id != user_id:
            return None
        
        # Calculate end date based on period
        next_period_end = self._calculate_period_end_date(next_period_start, base_budget.period)
        
        # Create new budget data
        new_budget_data = BudgetCreate(
            name=f"{base_budget.name} - {next_period_start.strftime('%B %Y')}",
            period=base_budget.period,
            total_limit=base_budget.total_limit,
            start_date=next_period_start,
            end_date=next_period_end,
            is_active=True,
            user_id=user_id
        )
        
        # Create category budgets data
        category_budgets_data = []
        for category_budget in base_budget.category_budgets:
            category_budgets_data.append(CategoryBudgetCreate(
                limit_amount=category_budget.limit_amount,
                budget_id=UUID("00000000-0000-0000-0000-000000000000"),  # Will be set in create_budget
                category_id=category_budget.category_id
            ))
        
        logger.info(f"Creating recurring budget based on {base_budget_id}")
        return await self.create_budget(db, new_budget_data, category_budgets_data)
    
    async def get_budgets_for_category(
        self,
        db: AsyncSession,
        user_id: UUID,
        category_name: str,
        expense_date: date
    ) -> List[BudgetTable]:
        """
        Get active budgets that include a specific category.
        
        Args:
            db: Database session
            user_id: User ID
            category_name: Category name to match
            expense_date: Date of the expense
            
        Returns:
            List of matching budget instances
        """
        # Get active budgets for the user
        active_budgets = await self.budget_repo.get_multi(
            db, user_id=user_id, is_active=True
        )
        
        matching_budgets = []
        for budget in active_budgets:
            # Check if budget is active for the expense date
            if expense_date < budget.start_date:
                continue
            if budget.end_date and expense_date > budget.end_date:
                continue
            
            # Check if budget includes this category
            if not budget.category_budgets:
                # No specific categories = includes all categories
                matching_budgets.append(budget)
            else:
                # Check if any category budget matches
                for category_budget in budget.category_budgets:
                    if category_budget.category and category_budget.category.name == category_name:
                        matching_budgets.append(budget)
                        break
        
        return matching_budgets
    
    async def recalculate_user_budgets(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> List[BudgetTable]:
        """
        Recalculate spending for all active budgets for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            List of updated budget instances
        """
        logger.info(f"Recalculating budgets for user {user_id}")
        
        # Get active budgets
        active_budgets = await self.budget_repo.get_multi(
            db, user_id=user_id, is_active=True
        )
        
        updated_budgets = []
        for budget in active_budgets:
            try:
                # Update spending for this budget
                await self._update_budget_spending(db, budget)
                updated_budgets.append(budget)
                
                # Check for alerts
                alerts = await self.check_budget_alerts(db, user_id, budget.id)
                if alerts:
                    logger.info(f"Generated {len(alerts)} alerts for budget {budget.id}")
                    
            except Exception as e:
                logger.error(f"Failed to recalculate budget {budget.id}: {e}")
        
        logger.info(f"Recalculated {len(updated_budgets)} budgets for user {user_id}")
        return updated_budgets
    
    async def _update_budget_spending(self, db: AsyncSession, budget: BudgetTable) -> None:
        """
        Update spending amounts for all category budgets in a budget.
        
        Args:
            db: Database session
            budget: Budget instance to update
        """
        for category_budget in budget.category_budgets:
            # Get total expenses for this category in the budget period
            expenses = await self.expense_repo.get_by_category_and_date_range(
                db,
                budget.user_id,
                category_budget.category_id,
                budget.start_date,
                budget.end_date or date.today()
            )
            
            total_spent = sum(expense.amount for expense in expenses)
            
            # Update the spent amount if it's different
            if category_budget.spent_amount != total_spent:
                await self.category_budget_repo.update(
                    db,
                    category_budget.id,
                    CategoryBudgetUpdate(spent_amount=total_spent)
                )
                category_budget.spent_amount = total_spent
    
    def _calculate_period_end_date(self, start_date: date, period: BudgetPeriod) -> Optional[date]:
        """
        Calculate the end date for a budget period.
        
        Args:
            start_date: Period start date
            period: Budget period type
            
        Returns:
            End date or None for custom periods
        """
        if period == BudgetPeriod.MONTHLY:
            # Last day of the month
            if start_date.month == 12:
                next_month = start_date.replace(year=start_date.year + 1, month=1)
            else:
                next_month = start_date.replace(month=start_date.month + 1)
            return next_month - timedelta(days=1)
        
        elif period == BudgetPeriod.QUARTERLY:
            # 3 months from start date
            month = start_date.month
            year = start_date.year
            
            month += 3
            if month > 12:
                month -= 12
                year += 1
            
            next_quarter = start_date.replace(year=year, month=month)
            return next_quarter - timedelta(days=1)
        
        elif period == BudgetPeriod.YEARLY:
            # Same date next year minus 1 day
            next_year = start_date.replace(year=start_date.year + 1)
            return next_year - timedelta(days=1)
        
        else:  # CUSTOM
            return None


# Create service instance
budget_service = BudgetService()