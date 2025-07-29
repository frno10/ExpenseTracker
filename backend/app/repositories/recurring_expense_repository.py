from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc
from uuid import UUID

from ..models.recurring_expense import (
    RecurringExpenseTable, RecurringExpenseHistoryTable, RecurringExpenseNotificationTable,
    RecurrenceFrequency, RecurrenceStatus
)
from ..models.expense import ExpenseTable


class RecurringExpenseRepository:
    """Repository for recurring expense data access operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ===== RECURRING EXPENSE CRUD OPERATIONS =====
    
    def create_recurring_expense(self, recurring_expense_data: Dict[str, Any]) -> RecurringExpenseTable:
        """Create a new recurring expense."""
        recurring_expense = RecurringExpenseTable(**recurring_expense_data)
        self.db.add(recurring_expense)
        self.db.commit()
        self.db.refresh(recurring_expense)
        return recurring_expense
    
    def get_recurring_expense_by_id(
        self, 
        recurring_expense_id: UUID, 
        user_id: UUID
    ) -> Optional[RecurringExpenseTable]:
        """Get recurring expense by ID for a specific user."""
        return self.db.query(RecurringExpenseTable).filter(
            RecurringExpenseTable.id == recurring_expense_id,
            RecurringExpenseTable.user_id == user_id
        ).options(
            joinedload(RecurringExpenseTable.category),
            joinedload(RecurringExpenseTable.merchant),
            joinedload(RecurringExpenseTable.payment_method),
            joinedload(RecurringExpenseTable.account)
        ).first()
    
    def get_user_recurring_expenses(
        self, 
        user_id: UUID, 
        status: Optional[RecurrenceStatus] = None,
        frequency: Optional[RecurrenceFrequency] = None,
        include_inactive: bool = False
    ) -> List[RecurringExpenseTable]:
        """Get all recurring expenses for a user."""
        query = self.db.query(RecurringExpenseTable).filter(
            RecurringExpenseTable.user_id == user_id
        )
        
        if status:
            query = query.filter(RecurringExpenseTable.status == status)
        elif not include_inactive:
            query = query.filter(RecurringExpenseTable.status == RecurrenceStatus.ACTIVE)
        
        if frequency:
            query = query.filter(RecurringExpenseTable.frequency == frequency)
        
        return query.options(
            joinedload(RecurringExpenseTable.category),
            joinedload(RecurringExpenseTable.merchant),
            joinedload(RecurringExpenseTable.payment_method),
            joinedload(RecurringExpenseTable.account)
        ).order_by(RecurringExpenseTable.next_due_date).all()
    
    def update_recurring_expense(
        self, 
        recurring_expense_id: UUID, 
        user_id: UUID, 
        update_data: Dict[str, Any]
    ) -> Optional[RecurringExpenseTable]:
        """Update a recurring expense."""
        recurring_expense = self.get_recurring_expense_by_id(recurring_expense_id, user_id)
        if not recurring_expense:
            return None
        
        for key, value in update_data.items():
            if hasattr(recurring_expense, key):
                setattr(recurring_expense, key, value)
        
        recurring_expense.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(recurring_expense)
        return recurring_expense
    
    def delete_recurring_expense(self, recurring_expense_id: UUID, user_id: UUID) -> bool:
        """Delete a recurring expense."""
        recurring_expense = self.get_recurring_expense_by_id(recurring_expense_id, user_id)
        if not recurring_expense:
            return False
        
        self.db.delete(recurring_expense)
        self.db.commit()
        return True
    
    # ===== DUE DATE AND SCHEDULING OPERATIONS =====
    
    def get_due_recurring_expenses(
        self, 
        user_id: Optional[UUID] = None, 
        due_date: Optional[date] = None
    ) -> List[RecurringExpenseTable]:
        """Get recurring expenses that are due for processing."""
        if due_date is None:
            due_date = date.today()
        
        query = self.db.query(RecurringExpenseTable).filter(
            RecurringExpenseTable.status == RecurrenceStatus.ACTIVE,
            RecurringExpenseTable.next_due_date <= due_date
        )
        
        if user_id:
            query = query.filter(RecurringExpenseTable.user_id == user_id)
        
        return query.options(
            joinedload(RecurringExpenseTable.category),
            joinedload(RecurringExpenseTable.merchant),
            joinedload(RecurringExpenseTable.payment_method),
            joinedload(RecurringExpenseTable.account)
        ).all()
    
    def get_upcoming_recurring_expenses(
        self, 
        user_id: UUID, 
        days_ahead: int = 30
    ) -> List[RecurringExpenseTable]:
        """Get upcoming recurring expenses within specified days."""
        end_date = date.today() + timedelta(days=days_ahead)
        
        return self.db.query(RecurringExpenseTable).filter(
            RecurringExpenseTable.user_id == user_id,
            RecurringExpenseTable.status == RecurrenceStatus.ACTIVE,
            RecurringExpenseTable.next_due_date <= end_date
        ).options(
            joinedload(RecurringExpenseTable.category),
            joinedload(RecurringExpenseTable.merchant),
            joinedload(RecurringExpenseTable.payment_method),
            joinedload(RecurringExpenseTable.account)
        ).order_by(RecurringExpenseTable.next_due_date).all()
    
    def update_next_due_date(
        self, 
        recurring_expense_id: UUID, 
        next_due_date: date
    ) -> bool:
        """Update the next due date for a recurring expense."""
        recurring_expense = self.db.query(RecurringExpenseTable).filter(
            RecurringExpenseTable.id == recurring_expense_id
        ).first()
        
        if not recurring_expense:
            return False
        
        recurring_expense.next_due_date = next_due_date
        recurring_expense.last_processed = datetime.utcnow()
        self.db.commit()
        return True
    
    def increment_occurrence_count(self, recurring_expense_id: UUID) -> bool:
        """Increment the occurrence count for a recurring expense."""
        recurring_expense = self.db.query(RecurringExpenseTable).filter(
            RecurringExpenseTable.id == recurring_expense_id
        ).first()
        
        if not recurring_expense:
            return False
        
        recurring_expense.current_occurrences += 1
        
        # Check if we've reached the maximum occurrences
        if (recurring_expense.max_occurrences and 
            recurring_expense.current_occurrences >= recurring_expense.max_occurrences):
            recurring_expense.status = RecurrenceStatus.COMPLETED
        
        self.db.commit()
        return True
    
    # ===== HISTORY OPERATIONS =====
    
    def create_history_entry(
        self,
        recurring_expense_id: UUID,
        due_date: date,
        amount: Decimal,
        expense_id: Optional[UUID],
        was_created: bool,
        processing_method: str,
        error_message: Optional[str] = None
    ) -> RecurringExpenseHistoryTable:
        """Create a history entry for recurring expense processing."""
        history = RecurringExpenseHistoryTable(
            recurring_expense_id=recurring_expense_id,
            due_date=due_date,
            amount=amount,
            expense_id=expense_id,
            was_created=was_created,
            processing_method=processing_method,
            error_message=error_message
        )
        
        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)
        return history
    
    def get_recurring_expense_history(
        self, 
        recurring_expense_id: UUID, 
        user_id: UUID, 
        limit: Optional[int] = None
    ) -> List[RecurringExpenseHistoryTable]:
        """Get processing history for a recurring expense."""
        # Verify ownership
        recurring_expense = self.get_recurring_expense_by_id(recurring_expense_id, user_id)
        if not recurring_expense:
            return []
        
        query = self.db.query(RecurringExpenseHistoryTable).filter(
            RecurringExpenseHistoryTable.recurring_expense_id == recurring_expense_id
        ).options(
            joinedload(RecurringExpenseHistoryTable.expense)
        ).order_by(desc(RecurringExpenseHistoryTable.processed_date))
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_user_recurring_expense_history(
        self, 
        user_id: UUID, 
        limit: Optional[int] = None
    ) -> List[RecurringExpenseHistoryTable]:
        """Get all recurring expense history for a user."""
        query = self.db.query(RecurringExpenseHistoryTable).join(
            RecurringExpenseTable
        ).filter(
            RecurringExpenseTable.user_id == user_id
        ).options(
            joinedload(RecurringExpenseHistoryTable.recurring_expense),
            joinedload(RecurringExpenseHistoryTable.expense)
        ).order_by(desc(RecurringExpenseHistoryTable.processed_date))
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    # ===== NOTIFICATION OPERATIONS =====
    
    def create_notification(
        self,
        recurring_expense_id: UUID,
        user_id: UUID,
        notification_type: str,
        due_date: date,
        title: str,
        message: str
    ) -> RecurringExpenseNotificationTable:
        """Create a notification for a recurring expense."""
        notification = RecurringExpenseNotificationTable(
            recurring_expense_id=recurring_expense_id,
            user_id=user_id,
            notification_type=notification_type,
            due_date=due_date,
            title=title,
            message=message
        )
        
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification
    
    def get_user_notifications(
        self, 
        user_id: UUID, 
        unread_only: bool = False,
        limit: Optional[int] = None
    ) -> List[RecurringExpenseNotificationTable]:
        """Get notifications for a user."""
        query = self.db.query(RecurringExpenseNotificationTable).filter(
            RecurringExpenseNotificationTable.user_id == user_id
        )
        
        if unread_only:
            query = query.filter(RecurringExpenseNotificationTable.is_read == False)
        
        query = query.options(
            joinedload(RecurringExpenseNotificationTable.recurring_expense)
        ).order_by(desc(RecurringExpenseNotificationTable.sent_at))
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def mark_notification_as_read(self, notification_id: UUID, user_id: UUID) -> bool:
        """Mark a notification as read."""
        notification = self.db.query(RecurringExpenseNotificationTable).filter(
            RecurringExpenseNotificationTable.id == notification_id,
            RecurringExpenseNotificationTable.user_id == user_id
        ).first()
        
        if not notification:
            return False
        
        notification.is_read = True
        self.db.commit()
        return True
    
    def update_last_notification_sent(
        self, 
        recurring_expense_id: UUID, 
        sent_at: datetime
    ) -> bool:
        """Update the last notification sent timestamp."""
        recurring_expense = self.db.query(RecurringExpenseTable).filter(
            RecurringExpenseTable.id == recurring_expense_id
        ).first()
        
        if not recurring_expense:
            return False
        
        recurring_expense.last_notification_sent = sent_at
        self.db.commit()
        return True
    
    # ===== ANALYTICS AND REPORTING =====
    
    def get_recurring_expense_summary(self, user_id: UUID) -> Dict[str, Any]:
        """Get summary statistics for user's recurring expenses."""
        # Get all active recurring expenses
        active_expenses = self.db.query(RecurringExpenseTable).filter(
            RecurringExpenseTable.user_id == user_id,
            RecurringExpenseTable.status == RecurrenceStatus.ACTIVE
        ).all()
        
        # Calculate totals by frequency
        frequency_totals = {}
        total_monthly_equivalent = Decimal('0.00')
        
        for expense in active_expenses:
            freq = expense.frequency.value
            if freq not in frequency_totals:
                frequency_totals[freq] = {'count': 0, 'amount': Decimal('0.00')}
            
            frequency_totals[freq]['count'] += 1
            frequency_totals[freq]['amount'] += expense.amount
            
            # Convert to monthly equivalent for comparison
            if expense.frequency == RecurrenceFrequency.DAILY:
                monthly_equiv = expense.amount * 30
            elif expense.frequency == RecurrenceFrequency.WEEKLY:
                monthly_equiv = expense.amount * 4.33  # Average weeks per month
            elif expense.frequency == RecurrenceFrequency.BIWEEKLY:
                monthly_equiv = expense.amount * 2.17  # Average biweeks per month
            elif expense.frequency == RecurrenceFrequency.MONTHLY:
                monthly_equiv = expense.amount
            elif expense.frequency == RecurrenceFrequency.QUARTERLY:
                monthly_equiv = expense.amount / 3
            elif expense.frequency == RecurrenceFrequency.SEMIANNUALLY:
                monthly_equiv = expense.amount / 6
            elif expense.frequency == RecurrenceFrequency.ANNUALLY:
                monthly_equiv = expense.amount / 12
            else:
                monthly_equiv = Decimal('0.00')
            
            total_monthly_equivalent += monthly_equiv
        
        # Get due and overdue counts
        today = date.today()
        due_count = self.db.query(RecurringExpenseTable).filter(
            RecurringExpenseTable.user_id == user_id,
            RecurringExpenseTable.status == RecurrenceStatus.ACTIVE,
            RecurringExpenseTable.next_due_date <= today
        ).count()
        
        overdue_count = self.db.query(RecurringExpenseTable).filter(
            RecurringExpenseTable.user_id == user_id,
            RecurringExpenseTable.status == RecurrenceStatus.ACTIVE,
            RecurringExpenseTable.next_due_date < today
        ).count()
        
        # Get recent processing stats
        recent_history = self.db.query(RecurringExpenseHistoryTable).join(
            RecurringExpenseTable
        ).filter(
            RecurringExpenseTable.user_id == user_id,
            RecurringExpenseHistoryTable.processed_date >= datetime.utcnow() - timedelta(days=30)
        ).all()
        
        successful_creations = sum(1 for h in recent_history if h.was_created)
        failed_creations = sum(1 for h in recent_history if not h.was_created)
        
        return {
            'total_active': len(active_expenses),
            'total_monthly_equivalent': total_monthly_equivalent,
            'frequency_breakdown': frequency_totals,
            'due_count': due_count,
            'overdue_count': overdue_count,
            'recent_successful_creations': successful_creations,
            'recent_failed_creations': failed_creations,
            'success_rate': (successful_creations / len(recent_history) * 100) if recent_history else 100
        }
    
    def get_recurring_expenses_by_category(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get recurring expenses grouped by category."""
        results = self.db.query(
            RecurringExpenseTable.category_id,
            func.count(RecurringExpenseTable.id).label('count'),
            func.sum(RecurringExpenseTable.amount).label('total_amount')
        ).filter(
            RecurringExpenseTable.user_id == user_id,
            RecurringExpenseTable.status == RecurrenceStatus.ACTIVE
        ).group_by(RecurringExpenseTable.category_id).all()
        
        category_data = []
        for result in results:
            category = None
            if result.category_id:
                from ..models.category import CategoryTable
                category = self.db.query(CategoryTable).filter(
                    CategoryTable.id == result.category_id
                ).first()
            
            category_data.append({
                'category_id': str(result.category_id) if result.category_id else None,
                'category_name': category.name if category else 'Uncategorized',
                'count': result.count,
                'total_amount': result.total_amount
            })
        
        return sorted(category_data, key=lambda x: x['total_amount'], reverse=True)