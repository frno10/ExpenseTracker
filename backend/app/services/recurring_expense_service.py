from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session

from ..models.recurring_expense import (
    RecurringExpenseTable, RecurringExpenseHistoryTable, RecurringExpenseNotificationTable,
    RecurrenceFrequency, RecurrenceStatus
)
from ..models.expense import ExpenseTable
from ..repositories.recurring_expense_repository import RecurringExpenseRepository
from ..services.expense_service import ExpenseService
from ..core.exceptions import ValidationError, NotFoundError, BusinessLogicError


class RecurringExpenseService:
    """Service for recurring expense management and business logic."""
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = RecurringExpenseRepository(db)
        self.expense_service = ExpenseService(db)
    
    # ===== RECURRING EXPENSE OPERATIONS =====
    
    async def create_recurring_expense(
        self, 
        user_id: UUID, 
        recurring_expense_data: Dict[str, Any]
    ) -> RecurringExpenseTable:
        """Create a new recurring expense with validation."""
        # Validate recurring expense data
        self._validate_recurring_expense_data(recurring_expense_data)
        
        # Add user_id to recurring expense data
        recurring_expense_data['user_id'] = user_id
        
        # Set initial next_due_date if not provided
        if 'next_due_date' not in recurring_expense_data:
            recurring_expense_data['next_due_date'] = recurring_expense_data['start_date']
        
        # Create recurring expense
        recurring_expense = self.repository.create_recurring_expense(recurring_expense_data)
        
        # Create initial notification if needed
        if recurring_expense.notify_before_days > 0:
            await self._create_upcoming_notification(recurring_expense)
        
        return recurring_expense
    
    async def get_recurring_expense(
        self, 
        recurring_expense_id: UUID, 
        user_id: UUID
    ) -> RecurringExpenseTable:
        """Get a recurring expense by ID."""
        recurring_expense = self.repository.get_recurring_expense_by_id(recurring_expense_id, user_id)
        if not recurring_expense:
            raise NotFoundError(f"Recurring expense {recurring_expense_id} not found")
        
        return recurring_expense
    
    async def get_user_recurring_expenses(
        self, 
        user_id: UUID, 
        status: Optional[RecurrenceStatus] = None,
        frequency: Optional[RecurrenceFrequency] = None,
        include_inactive: bool = False
    ) -> List[RecurringExpenseTable]:
        """Get all recurring expenses for a user."""
        return self.repository.get_user_recurring_expenses(
            user_id, status, frequency, include_inactive
        )
    
    async def update_recurring_expense(
        self, 
        recurring_expense_id: UUID, 
        user_id: UUID, 
        update_data: Dict[str, Any]
    ) -> RecurringExpenseTable:
        """Update a recurring expense."""
        # Validate update data
        self._validate_recurring_expense_update_data(update_data)
        
        # Get existing recurring expense
        existing = await self.get_recurring_expense(recurring_expense_id, user_id)
        
        # If frequency or interval changed, recalculate next due date
        if 'frequency' in update_data or 'interval' in update_data:
            # Use existing values if not being updated
            frequency = update_data.get('frequency', existing.frequency)
            interval = update_data.get('interval', existing.interval)
            
            # Create a temporary object to calculate next due date
            temp_expense = RecurringExpenseTable(
                frequency=frequency,
                interval=interval,
                next_due_date=existing.next_due_date,
                day_of_month=update_data.get('day_of_month', existing.day_of_month),
                day_of_week=update_data.get('day_of_week', existing.day_of_week),
                month_of_year=update_data.get('month_of_year', existing.month_of_year)
            )
            
            update_data['next_due_date'] = temp_expense.calculate_next_due_date()
        
        # Update recurring expense
        recurring_expense = self.repository.update_recurring_expense(
            recurring_expense_id, user_id, update_data
        )
        if not recurring_expense:
            raise NotFoundError(f"Recurring expense {recurring_expense_id} not found")
        
        return recurring_expense
    
    async def delete_recurring_expense(
        self, 
        recurring_expense_id: UUID, 
        user_id: UUID
    ) -> bool:
        """Delete a recurring expense."""
        # Verify ownership
        await self.get_recurring_expense(recurring_expense_id, user_id)
        
        success = self.repository.delete_recurring_expense(recurring_expense_id, user_id)
        if not success:
            raise NotFoundError(f"Recurring expense {recurring_expense_id} not found")
        
        return success
    
    async def pause_recurring_expense(
        self, 
        recurring_expense_id: UUID, 
        user_id: UUID
    ) -> RecurringExpenseTable:
        """Pause a recurring expense."""
        return await self.update_recurring_expense(
            recurring_expense_id, user_id, {'status': RecurrenceStatus.PAUSED}
        )
    
    async def resume_recurring_expense(
        self, 
        recurring_expense_id: UUID, 
        user_id: UUID
    ) -> RecurringExpenseTable:
        """Resume a paused recurring expense."""
        return await self.update_recurring_expense(
            recurring_expense_id, user_id, {'status': RecurrenceStatus.ACTIVE}
        )
    
    async def cancel_recurring_expense(
        self, 
        recurring_expense_id: UUID, 
        user_id: UUID
    ) -> RecurringExpenseTable:
        """Cancel a recurring expense."""
        return await self.update_recurring_expense(
            recurring_expense_id, user_id, {'status': RecurrenceStatus.CANCELLED}
        )
    
    # ===== EXPENSE GENERATION =====
    
    async def process_due_recurring_expenses(
        self, 
        user_id: Optional[UUID] = None, 
        due_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Process all due recurring expenses."""
        if due_date is None:
            due_date = date.today()
        
        due_expenses = self.repository.get_due_recurring_expenses(user_id, due_date)
        
        results = {
            'processed': 0,
            'created': 0,
            'failed': 0,
            'errors': []
        }
        
        for recurring_expense in due_expenses:
            try:
                success = await self._process_single_recurring_expense(recurring_expense, due_date)
                results['processed'] += 1
                if success:
                    results['created'] += 1
                else:
                    results['failed'] += 1
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'recurring_expense_id': str(recurring_expense.id),
                    'error': str(e)
                })
        
        return results
    
    async def create_expense_from_recurring(
        self, 
        recurring_expense_id: UUID, 
        user_id: UUID, 
        expense_date: Optional[date] = None
    ) -> ExpenseTable:
        """Manually create an expense from a recurring expense."""
        recurring_expense = await self.get_recurring_expense(recurring_expense_id, user_id)
        
        if expense_date is None:
            expense_date = date.today()
        
        # Create expense data from recurring expense
        expense_data = {
            'amount': recurring_expense.amount,
            'description': recurring_expense.description or recurring_expense.name,
            'expense_date': expense_date,
            'notes': f"Generated from recurring expense: {recurring_expense.name}",
            'category_id': recurring_expense.category_id,
            'merchant_id': recurring_expense.merchant_id,
            'payment_method_id': recurring_expense.payment_method_id,
            'account_id': recurring_expense.account_id,
            'recurring_expense_id': recurring_expense.id,
            'is_recurring': True
        }
        
        # Create the expense
        expense = await self.expense_service.create_expense(user_id, expense_data)
        
        # Create history entry
        self.repository.create_history_entry(
            recurring_expense.id,
            expense_date,
            recurring_expense.amount,
            expense.id,
            True,
            'manual'
        )
        
        # Update occurrence count and next due date
        self.repository.increment_occurrence_count(recurring_expense.id)
        next_due_date = recurring_expense.calculate_next_due_date()
        self.repository.update_next_due_date(recurring_expense.id, next_due_date)
        
        return expense
    
    async def _process_single_recurring_expense(
        self, 
        recurring_expense: RecurringExpenseTable, 
        due_date: date
    ) -> bool:
        """Process a single recurring expense."""
        try:
            # Check if already completed
            if recurring_expense.is_completed:
                self.repository.update_recurring_expense(
                    recurring_expense.id, 
                    recurring_expense.user_id, 
                    {'status': RecurrenceStatus.COMPLETED}
                )
                return False
            
            # Create expense if auto-create is enabled
            if recurring_expense.is_auto_create:
                expense_data = {
                    'amount': recurring_expense.amount,
                    'description': recurring_expense.description or recurring_expense.name,
                    'expense_date': due_date,
                    'notes': f"Auto-generated from recurring expense: {recurring_expense.name}",
                    'category_id': recurring_expense.category_id,
                    'merchant_id': recurring_expense.merchant_id,
                    'payment_method_id': recurring_expense.payment_method_id,
                    'account_id': recurring_expense.account_id,
                    'recurring_expense_id': recurring_expense.id,
                    'is_recurring': True
                }
                
                expense = await self.expense_service.create_expense(
                    recurring_expense.user_id, expense_data
                )
                expense_id = expense.id
                was_created = True
            else:
                expense_id = None
                was_created = False
            
            # Create history entry
            self.repository.create_history_entry(
                recurring_expense.id,
                due_date,
                recurring_expense.amount,
                expense_id,
                was_created,
                'automatic'
            )
            
            # Update occurrence count and next due date
            self.repository.increment_occurrence_count(recurring_expense.id)
            next_due_date = recurring_expense.calculate_next_due_date()
            self.repository.update_next_due_date(recurring_expense.id, next_due_date)
            
            # Create notification if expense was created
            if was_created:
                await self._create_expense_created_notification(recurring_expense, expense_id)
            
            return was_created
            
        except Exception as e:
            # Create error history entry
            self.repository.create_history_entry(
                recurring_expense.id,
                due_date,
                recurring_expense.amount,
                None,
                False,
                'automatic',
                str(e)
            )
            raise e
    
    # ===== UPCOMING EXPENSES =====
    
    async def get_upcoming_recurring_expenses(
        self, 
        user_id: UUID, 
        days_ahead: int = 30
    ) -> List[Dict[str, Any]]:
        """Get upcoming recurring expenses with preview dates."""
        recurring_expenses = self.repository.get_upcoming_recurring_expenses(user_id, days_ahead)
        
        upcoming = []
        for recurring_expense in recurring_expenses:
            upcoming_dates = recurring_expense.get_upcoming_dates(5)
            
            for upcoming_date in upcoming_dates:
                if upcoming_date <= date.today() + timedelta(days=days_ahead):
                    upcoming.append({
                        'recurring_expense_id': str(recurring_expense.id),
                        'name': recurring_expense.name,
                        'amount': recurring_expense.amount,
                        'due_date': upcoming_date,
                        'frequency': recurring_expense.frequency,
                        'category_name': recurring_expense.category.name if recurring_expense.category else None,
                        'merchant_name': recurring_expense.merchant.name if recurring_expense.merchant else None,
                        'is_overdue': upcoming_date < date.today(),
                        'days_until_due': (upcoming_date - date.today()).days
                    })
        
        return sorted(upcoming, key=lambda x: x['due_date'])
    
    # ===== NOTIFICATIONS =====
    
    async def create_upcoming_notifications(self, user_id: Optional[UUID] = None) -> int:
        """Create notifications for upcoming recurring expenses."""
        # Get recurring expenses that need notifications
        query_date = date.today() + timedelta(days=7)  # Look ahead 7 days
        due_expenses = self.repository.get_due_recurring_expenses(user_id, query_date)
        
        notifications_created = 0
        
        for recurring_expense in due_expenses:
            # Check if notification should be sent
            days_until_due = (recurring_expense.next_due_date - date.today()).days
            
            if days_until_due <= recurring_expense.notify_before_days:
                # Check if notification was already sent recently
                if (recurring_expense.last_notification_sent and 
                    recurring_expense.last_notification_sent.date() >= date.today()):
                    continue
                
                await self._create_upcoming_notification(recurring_expense)
                notifications_created += 1
        
        return notifications_created
    
    async def _create_upcoming_notification(self, recurring_expense: RecurringExpenseTable):
        """Create an upcoming expense notification."""
        days_until_due = (recurring_expense.next_due_date - date.today()).days
        
        if days_until_due == 0:
            title = f"Recurring expense due today: {recurring_expense.name}"
            message = f"Your recurring expense '{recurring_expense.name}' for ${recurring_expense.amount} is due today."
        elif days_until_due == 1:
            title = f"Recurring expense due tomorrow: {recurring_expense.name}"
            message = f"Your recurring expense '{recurring_expense.name}' for ${recurring_expense.amount} is due tomorrow."
        else:
            title = f"Recurring expense due in {days_until_due} days: {recurring_expense.name}"
            message = f"Your recurring expense '{recurring_expense.name}' for ${recurring_expense.amount} is due in {days_until_due} days."
        
        self.repository.create_notification(
            recurring_expense.id,
            recurring_expense.user_id,
            'upcoming',
            recurring_expense.next_due_date,
            title,
            message
        )
        
        self.repository.update_last_notification_sent(recurring_expense.id, datetime.utcnow())
    
    async def _create_expense_created_notification(
        self, 
        recurring_expense: RecurringExpenseTable, 
        expense_id: UUID
    ):
        """Create a notification when an expense is auto-created."""
        title = f"Recurring expense created: {recurring_expense.name}"
        message = f"A recurring expense '{recurring_expense.name}' for ${recurring_expense.amount} has been automatically created."
        
        self.repository.create_notification(
            recurring_expense.id,
            recurring_expense.user_id,
            'created',
            date.today(),
            title,
            message
        )
    
    async def get_user_notifications(
        self, 
        user_id: UUID, 
        unread_only: bool = False,
        limit: Optional[int] = None
    ) -> List[RecurringExpenseNotificationTable]:
        """Get notifications for a user."""
        return self.repository.get_user_notifications(user_id, unread_only, limit)
    
    async def mark_notification_as_read(
        self, 
        notification_id: UUID, 
        user_id: UUID
    ) -> bool:
        """Mark a notification as read."""
        return self.repository.mark_notification_as_read(notification_id, user_id)
    
    # ===== HISTORY AND ANALYTICS =====
    
    async def get_recurring_expense_history(
        self, 
        recurring_expense_id: UUID, 
        user_id: UUID, 
        limit: Optional[int] = None
    ) -> List[RecurringExpenseHistoryTable]:
        """Get processing history for a recurring expense."""
        return self.repository.get_recurring_expense_history(recurring_expense_id, user_id, limit)
    
    async def get_user_recurring_expense_history(
        self, 
        user_id: UUID, 
        limit: Optional[int] = None
    ) -> List[RecurringExpenseHistoryTable]:
        """Get all recurring expense history for a user."""
        return self.repository.get_user_recurring_expense_history(user_id, limit)
    
    async def get_recurring_expense_summary(self, user_id: UUID) -> Dict[str, Any]:
        """Get summary statistics for user's recurring expenses."""
        return self.repository.get_recurring_expense_summary(user_id)
    
    async def get_recurring_expenses_by_category(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get recurring expenses grouped by category."""
        return self.repository.get_recurring_expenses_by_category(user_id)
    
    # ===== VALIDATION METHODS =====
    
    def _validate_recurring_expense_data(self, recurring_expense_data: Dict[str, Any]) -> None:
        """Validate recurring expense creation data."""
        required_fields = ['name', 'amount', 'frequency', 'start_date']
        for field in required_fields:
            if field not in recurring_expense_data:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate amount
        try:
            amount = Decimal(str(recurring_expense_data['amount']))
            if amount <= 0:
                raise ValidationError("Amount must be positive")
        except:
            raise ValidationError("Invalid amount format")
        
        # Validate frequency
        if recurring_expense_data['frequency'] not in RecurrenceFrequency:
            raise ValidationError(f"Invalid frequency: {recurring_expense_data['frequency']}")
        
        # Validate dates
        start_date = recurring_expense_data['start_date']
        if isinstance(start_date, str):
            try:
                start_date = date.fromisoformat(start_date)
                recurring_expense_data['start_date'] = start_date
            except:
                raise ValidationError("Invalid start_date format")
        
        if 'end_date' in recurring_expense_data and recurring_expense_data['end_date']:
            end_date = recurring_expense_data['end_date']
            if isinstance(end_date, str):
                try:
                    end_date = date.fromisoformat(end_date)
                    recurring_expense_data['end_date'] = end_date
                except:
                    raise ValidationError("Invalid end_date format")
            
            if end_date <= start_date:
                raise ValidationError("End date must be after start date")
        
        # Validate interval
        if 'interval' in recurring_expense_data:
            interval = recurring_expense_data['interval']
            if not isinstance(interval, int) or interval < 1:
                raise ValidationError("Interval must be a positive integer")
        
        # Validate max_occurrences
        if 'max_occurrences' in recurring_expense_data and recurring_expense_data['max_occurrences']:
            max_occurrences = recurring_expense_data['max_occurrences']
            if not isinstance(max_occurrences, int) or max_occurrences < 1:
                raise ValidationError("Max occurrences must be a positive integer")
        
        # Validate day constraints
        if 'day_of_month' in recurring_expense_data and recurring_expense_data['day_of_month']:
            day = recurring_expense_data['day_of_month']
            if not isinstance(day, int) or day < 1 or day > 31:
                raise ValidationError("Day of month must be between 1 and 31")
        
        if 'day_of_week' in recurring_expense_data and recurring_expense_data['day_of_week']:
            day = recurring_expense_data['day_of_week']
            if not isinstance(day, int) or day < 0 or day > 6:
                raise ValidationError("Day of week must be between 0 (Monday) and 6 (Sunday)")
        
        if 'month_of_year' in recurring_expense_data and recurring_expense_data['month_of_year']:
            month = recurring_expense_data['month_of_year']
            if not isinstance(month, int) or month < 1 or month > 12:
                raise ValidationError("Month of year must be between 1 and 12")
    
    def _validate_recurring_expense_update_data(self, update_data: Dict[str, Any]) -> None:
        """Validate recurring expense update data."""
        # Validate amount if provided
        if 'amount' in update_data:
            try:
                amount = Decimal(str(update_data['amount']))
                if amount <= 0:
                    raise ValidationError("Amount must be positive")
            except:
                raise ValidationError("Invalid amount format")
        
        # Validate frequency if provided
        if 'frequency' in update_data and update_data['frequency'] not in RecurrenceFrequency:
            raise ValidationError(f"Invalid frequency: {update_data['frequency']}")
        
        # Validate status if provided
        if 'status' in update_data and update_data['status'] not in RecurrenceStatus:
            raise ValidationError(f"Invalid status: {update_data['status']}")
        
        # Validate interval if provided
        if 'interval' in update_data:
            interval = update_data['interval']
            if not isinstance(interval, int) or interval < 1:
                raise ValidationError("Interval must be a positive integer")
        
        # Validate day constraints if provided
        if 'day_of_month' in update_data and update_data['day_of_month']:
            day = update_data['day_of_month']
            if not isinstance(day, int) or day < 1 or day > 31:
                raise ValidationError("Day of month must be between 1 and 31")
        
        if 'day_of_week' in update_data and update_data['day_of_week']:
            day = update_data['day_of_week']
            if not isinstance(day, int) or day < 0 or day > 6:
                raise ValidationError("Day of week must be between 0 (Monday) and 6 (Sunday)")
        
        if 'month_of_year' in update_data and update_data['month_of_year']:
            month = update_data['month_of_year']
            if not isinstance(month, int) or month < 1 or month > 12:
                raise ValidationError("Month of year must be between 1 and 12")