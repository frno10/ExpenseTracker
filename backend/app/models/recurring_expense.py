from datetime import datetime, date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, Numeric, DateTime, Boolean, ForeignKey, Text, Integer, Date
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSON
from sqlalchemy.orm import relationship
import uuid
from dateutil.relativedelta import relativedelta

from .base import Base


class RecurrenceFrequency(str, Enum):
    """Recurrence frequency options."""
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMIANNUALLY = "semiannually"
    ANNUALLY = "annually"


class RecurrenceStatus(str, Enum):
    """Recurrence status options."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RecurringExpenseTable(Base):
    """Model for recurring expense patterns."""
    
    __tablename__ = "recurring_expenses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Basic expense information
    name = Column(String(255), nullable=False)  # e.g., "Netflix Subscription", "Rent Payment"
    description = Column(Text, nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    
    # Categorization
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=True)
    payment_method_id = Column(UUID(as_uuid=True), ForeignKey("payment_methods.id"), nullable=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True)
    
    # Recurrence pattern
    frequency = Column(ENUM(RecurrenceFrequency), nullable=False)
    interval = Column(Integer, default=1, nullable=False)  # Every X frequency units
    
    # Scheduling
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)  # Optional end date
    next_due_date = Column(Date, nullable=False)
    
    # Limits
    max_occurrences = Column(Integer, nullable=True)  # Maximum number of occurrences
    current_occurrences = Column(Integer, default=0, nullable=False)  # Current count
    
    # Status and settings
    status = Column(ENUM(RecurrenceStatus), default=RecurrenceStatus.ACTIVE, nullable=False)
    is_auto_create = Column(Boolean, default=True, nullable=False)  # Auto-create expenses
    
    # Advanced settings
    day_of_month = Column(Integer, nullable=True)  # For monthly: specific day (1-31)
    day_of_week = Column(Integer, nullable=True)  # For weekly: day of week (0=Monday, 6=Sunday)
    month_of_year = Column(Integer, nullable=True)  # For yearly: specific month (1-12)
    
    # Notification settings
    notify_before_days = Column(Integer, default=1, nullable=False)  # Days before to notify
    last_notification_sent = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_processed = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="recurring_expenses")
    category = relationship("CategoryTable")
    merchant = relationship("MerchantTable")
    payment_method = relationship("PaymentMethodTable")
    account = relationship("AccountTable")
    generated_expenses = relationship("ExpenseTable", back_populates="recurring_expense")
    
    def __repr__(self):
        return f"<RecurringExpense(id={self.id}, name='{self.name}', frequency='{self.frequency}', amount={self.amount})>"
    
    @property
    def is_active(self) -> bool:
        """Check if the recurring expense is active."""
        return self.status == RecurrenceStatus.ACTIVE
    
    @property
    def is_due(self) -> bool:
        """Check if the recurring expense is due for processing."""
        if not self.is_active:
            return False
        
        today = date.today()
        return self.next_due_date <= today
    
    @property
    def is_completed(self) -> bool:
        """Check if the recurring expense has completed all occurrences."""
        if self.max_occurrences and self.current_occurrences >= self.max_occurrences:
            return True
        
        if self.end_date and date.today() > self.end_date:
            return True
        
        return False
    
    @property
    def remaining_occurrences(self) -> Optional[int]:
        """Get remaining occurrences if max_occurrences is set."""
        if self.max_occurrences:
            return max(0, self.max_occurrences - self.current_occurrences)
        return None
    
    @property
    def frequency_description(self) -> str:
        """Get human-readable frequency description."""
        if self.interval == 1:
            return self.frequency.value.title()
        else:
            return f"Every {self.interval} {self.frequency.value}s"
    
    def calculate_next_due_date(self, from_date: Optional[date] = None) -> date:
        """Calculate the next due date based on frequency and interval."""
        if from_date is None:
            from_date = self.next_due_date
        
        if self.frequency == RecurrenceFrequency.DAILY:
            return from_date + timedelta(days=self.interval)
        
        elif self.frequency == RecurrenceFrequency.WEEKLY:
            return from_date + timedelta(weeks=self.interval)
        
        elif self.frequency == RecurrenceFrequency.BIWEEKLY:
            return from_date + timedelta(weeks=2 * self.interval)
        
        elif self.frequency == RecurrenceFrequency.MONTHLY:
            next_date = from_date + relativedelta(months=self.interval)
            
            # Handle specific day of month
            if self.day_of_month:
                try:
                    next_date = next_date.replace(day=self.day_of_month)
                except ValueError:
                    # Handle cases like Feb 31 -> Feb 28/29
                    next_date = next_date.replace(day=1) + relativedelta(months=1) - timedelta(days=1)
            
            return next_date
        
        elif self.frequency == RecurrenceFrequency.QUARTERLY:
            return from_date + relativedelta(months=3 * self.interval)
        
        elif self.frequency == RecurrenceFrequency.SEMIANNUALLY:
            return from_date + relativedelta(months=6 * self.interval)
        
        elif self.frequency == RecurrenceFrequency.ANNUALLY:
            next_date = from_date + relativedelta(years=self.interval)
            
            # Handle specific month and day
            if self.month_of_year:
                next_date = next_date.replace(month=self.month_of_year)
            
            if self.day_of_month:
                try:
                    next_date = next_date.replace(day=self.day_of_month)
                except ValueError:
                    # Handle leap year issues
                    next_date = next_date.replace(day=1) + relativedelta(months=1) - timedelta(days=1)
            
            return next_date
        
        else:
            raise ValueError(f"Unsupported frequency: {self.frequency}")
    
    def get_upcoming_dates(self, count: int = 5) -> List[date]:
        """Get upcoming due dates for preview."""
        dates = []
        current_date = self.next_due_date
        
        for _ in range(count):
            if self.end_date and current_date > self.end_date:
                break
            
            if self.max_occurrences and len(dates) + self.current_occurrences >= self.max_occurrences:
                break
            
            dates.append(current_date)
            current_date = self.calculate_next_due_date(current_date)
        
        return dates


class RecurringExpenseHistoryTable(Base):
    """Model for tracking recurring expense processing history."""
    
    __tablename__ = "recurring_expense_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recurring_expense_id = Column(UUID(as_uuid=True), ForeignKey("recurring_expenses.id"), nullable=False)
    
    # Processing details
    processed_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(Date, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    
    # Result
    expense_id = Column(UUID(as_uuid=True), ForeignKey("expenses.id"), nullable=True)
    was_created = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Processing context
    processing_method = Column(String(50), nullable=False)  # 'automatic', 'manual', 'batch'
    
    # Relationships
    recurring_expense = relationship("RecurringExpenseTable")
    expense = relationship("ExpenseTable")
    
    def __repr__(self):
        return f"<RecurringExpenseHistory(id={self.id}, due_date={self.due_date}, was_created={self.was_created})>"


class RecurringExpenseNotificationTable(Base):
    """Model for tracking recurring expense notifications."""
    
    __tablename__ = "recurring_expense_notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recurring_expense_id = Column(UUID(as_uuid=True), ForeignKey("recurring_expenses.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Notification details
    notification_type = Column(String(50), nullable=False)  # 'upcoming', 'overdue', 'created'
    due_date = Column(Date, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    
    # Notification content
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Status
    is_read = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    recurring_expense = relationship("RecurringExpenseTable")
    user = relationship("User")
    
    def __repr__(self):
        return f"<RecurringExpenseNotification(id={self.id}, type='{self.notification_type}', due_date={self.due_date})>"