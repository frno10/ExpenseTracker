from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, validator

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models.user import User
from ..models.recurring_expense import RecurrenceFrequency, RecurrenceStatus
from ..services.recurring_expense_service import RecurringExpenseService
from ..core.exceptions import ValidationError, NotFoundError, BusinessLogicError

router = APIRouter(prefix="/recurring-expenses", tags=["recurring-expenses"])


# ===== PYDANTIC MODELS =====

class RecurringExpenseCreate(BaseModel):
    name: str = Field(..., max_length=255, description="Recurring expense name")
    description: Optional[str] = Field(None, description="Recurring expense description")
    amount: Decimal = Field(..., gt=0, description="Expense amount")
    frequency: RecurrenceFrequency = Field(..., description="Recurrence frequency")
    interval: int = Field(1, ge=1, description="Interval between occurrences")
    start_date: date = Field(..., description="Start date for recurrence")
    end_date: Optional[date] = Field(None, description="Optional end date")
    max_occurrences: Optional[int] = Field(None, ge=1, description="Maximum number of occurrences")
    
    # Categorization
    category_id: Optional[UUID] = Field(None, description="Category ID")
    merchant_id: Optional[UUID] = Field(None, description="Merchant ID")
    payment_method_id: Optional[UUID] = Field(None, description="Payment method ID")
    account_id: Optional[UUID] = Field(None, description="Account ID")
    
    # Advanced scheduling
    day_of_month: Optional[int] = Field(None, ge=1, le=31, description="Specific day of month")
    day_of_week: Optional[int] = Field(None, ge=0, le=6, description="Day of week (0=Monday)")
    month_of_year: Optional[int] = Field(None, ge=1, le=12, description="Specific month")
    
    # Settings
    is_auto_create: bool = Field(True, description="Automatically create expenses")
    notify_before_days: int = Field(1, ge=0, description="Days before to notify")
    
    @validator('end_date')
    def validate_end_date(cls, v, values):
        if v and 'start_date' in values and v <= values['start_date']:
            raise ValueError('End date must be after start date')
        return v


class RecurringExpenseUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255, description="Recurring expense name")
    description: Optional[str] = Field(None, description="Recurring expense description")
    amount: Optional[Decimal] = Field(None, gt=0, description="Expense amount")
    frequency: Optional[RecurrenceFrequency] = Field(None, description="Recurrence frequency")
    interval: Optional[int] = Field(None, ge=1, description="Interval between occurrences")
    end_date: Optional[date] = Field(None, description="Optional end date")
    max_occurrences: Optional[int] = Field(None, ge=1, description="Maximum number of occurrences")
    
    # Categorization
    category_id: Optional[UUID] = Field(None, description="Category ID")
    merchant_id: Optional[UUID] = Field(None, description="Merchant ID")
    payment_method_id: Optional[UUID] = Field(None, description="Payment method ID")
    account_id: Optional[UUID] = Field(None, description="Account ID")
    
    # Advanced scheduling
    day_of_month: Optional[int] = Field(None, ge=1, le=31, description="Specific day of month")
    day_of_week: Optional[int] = Field(None, ge=0, le=6, description="Day of week (0=Monday)")
    month_of_year: Optional[int] = Field(None, ge=1, le=12, description="Specific month")
    
    # Settings
    is_auto_create: Optional[bool] = Field(None, description="Automatically create expenses")
    notify_before_days: Optional[int] = Field(None, ge=0, description="Days before to notify")
    status: Optional[RecurrenceStatus] = Field(None, description="Recurrence status")


class RecurringExpenseResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    amount: Decimal
    frequency: RecurrenceFrequency
    interval: int
    start_date: date
    end_date: Optional[date]
    next_due_date: date
    max_occurrences: Optional[int]
    current_occurrences: int
    status: RecurrenceStatus
    is_auto_create: bool
    notify_before_days: int
    
    # Categorization
    category_id: Optional[UUID]
    merchant_id: Optional[UUID]
    payment_method_id: Optional[UUID]
    account_id: Optional[UUID]
    
    # Advanced scheduling
    day_of_month: Optional[int]
    day_of_week: Optional[int]
    month_of_year: Optional[int]
    
    # Computed properties
    is_active: bool
    is_due: bool
    is_completed: bool
    remaining_occurrences: Optional[int]
    frequency_description: str
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    last_processed: Optional[datetime]
    last_notification_sent: Optional[datetime]
    
    class Config:
        from_attributes = True


class UpcomingExpenseResponse(BaseModel):
    recurring_expense_id: str
    name: str
    amount: Decimal
    due_date: date
    frequency: RecurrenceFrequency
    category_name: Optional[str]
    merchant_name: Optional[str]
    is_overdue: bool
    days_until_due: int


class RecurringExpenseHistoryResponse(BaseModel):
    id: UUID
    processed_date: datetime
    due_date: date
    amount: Decimal
    expense_id: Optional[UUID]
    was_created: bool
    error_message: Optional[str]
    processing_method: str
    
    class Config:
        from_attributes = True


class RecurringExpenseNotificationResponse(BaseModel):
    id: UUID
    notification_type: str
    due_date: date
    title: str
    message: str
    is_read: bool
    sent_at: datetime
    
    class Config:
        from_attributes = True


class RecurringExpenseSummaryResponse(BaseModel):
    total_active: int
    total_monthly_equivalent: Decimal
    frequency_breakdown: Dict[str, Dict[str, Any]]
    due_count: int
    overdue_count: int
    recent_successful_creations: int
    recent_failed_creations: int
    success_rate: float


class ProcessingResultResponse(BaseModel):
    processed: int
    created: int
    failed: int
    errors: List[Dict[str, str]]


# ===== RECURRING EXPENSE ENDPOINTS =====

@router.post("/", response_model=RecurringExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_recurring_expense(
    recurring_expense_data: RecurringExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new recurring expense."""
    try:
        service = RecurringExpenseService(db)
        recurring_expense = await service.create_recurring_expense(
            current_user.id, 
            recurring_expense_data.dict(exclude_unset=True)
        )
        return RecurringExpenseResponse.from_orm(recurring_expense)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/", response_model=List[RecurringExpenseResponse])
async def get_recurring_expenses(
    status_filter: Optional[RecurrenceStatus] = Query(None, description="Filter by status"),
    frequency: Optional[RecurrenceFrequency] = Query(None, description="Filter by frequency"),
    include_inactive: bool = Query(False, description="Include inactive recurring expenses"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all recurring expenses for the current user."""
    try:
        service = RecurringExpenseService(db)
        recurring_expenses = await service.get_user_recurring_expenses(
            current_user.id, status_filter, frequency, include_inactive
        )
        return [RecurringExpenseResponse.from_orm(re) for re in recurring_expenses]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{recurring_expense_id}", response_model=RecurringExpenseResponse)
async def get_recurring_expense(
    recurring_expense_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific recurring expense."""
    try:
        service = RecurringExpenseService(db)
        recurring_expense = await service.get_recurring_expense(recurring_expense_id, current_user.id)
        return RecurringExpenseResponse.from_orm(recurring_expense)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{recurring_expense_id}", response_model=RecurringExpenseResponse)
async def update_recurring_expense(
    recurring_expense_id: UUID,
    update_data: RecurringExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a recurring expense."""
    try:
        service = RecurringExpenseService(db)
        recurring_expense = await service.update_recurring_expense(
            recurring_expense_id, current_user.id, update_data.dict(exclude_unset=True)
        )
        return RecurringExpenseResponse.from_orm(recurring_expense)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{recurring_expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurring_expense(
    recurring_expense_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a recurring expense."""
    try:
        service = RecurringExpenseService(db)
        await service.delete_recurring_expense(recurring_expense_id, current_user.id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== STATUS MANAGEMENT ENDPOINTS =====

@router.post("/{recurring_expense_id}/pause", response_model=RecurringExpenseResponse)
async def pause_recurring_expense(
    recurring_expense_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Pause a recurring expense."""
    try:
        service = RecurringExpenseService(db)
        recurring_expense = await service.pause_recurring_expense(recurring_expense_id, current_user.id)
        return RecurringExpenseResponse.from_orm(recurring_expense)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{recurring_expense_id}/resume", response_model=RecurringExpenseResponse)
async def resume_recurring_expense(
    recurring_expense_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resume a paused recurring expense."""
    try:
        service = RecurringExpenseService(db)
        recurring_expense = await service.resume_recurring_expense(recurring_expense_id, current_user.id)
        return RecurringExpenseResponse.from_orm(recurring_expense)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{recurring_expense_id}/cancel", response_model=RecurringExpenseResponse)
async def cancel_recurring_expense(
    recurring_expense_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a recurring expense."""
    try:
        service = RecurringExpenseService(db)
        recurring_expense = await service.cancel_recurring_expense(recurring_expense_id, current_user.id)
        return RecurringExpenseResponse.from_orm(recurring_expense)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== EXPENSE GENERATION ENDPOINTS =====

@router.post("/{recurring_expense_id}/create-expense", status_code=status.HTTP_201_CREATED)
async def create_expense_from_recurring(
    recurring_expense_id: UUID,
    expense_date: Optional[date] = Query(None, description="Date for the expense (defaults to today)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually create an expense from a recurring expense."""
    try:
        service = RecurringExpenseService(db)
        expense = await service.create_expense_from_recurring(
            recurring_expense_id, current_user.id, expense_date
        )
        return {"message": "Expense created successfully", "expense_id": str(expense.id)}
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/process-due", response_model=ProcessingResultResponse)
async def process_due_recurring_expenses(
    background_tasks: BackgroundTasks,
    due_date: Optional[date] = Query(None, description="Process expenses due on this date (defaults to today)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Process all due recurring expenses for the current user."""
    try:
        service = RecurringExpenseService(db)
        results = await service.process_due_recurring_expenses(current_user.id, due_date)
        
        # Create notifications in background
        background_tasks.add_task(service.create_upcoming_notifications, current_user.id)
        
        return ProcessingResultResponse(**results)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== UPCOMING EXPENSES ENDPOINTS =====

@router.get("/upcoming/preview", response_model=List[UpcomingExpenseResponse])
async def get_upcoming_recurring_expenses(
    days_ahead: int = Query(30, ge=1, le=365, description="Number of days to look ahead"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get upcoming recurring expenses within specified days."""
    try:
        service = RecurringExpenseService(db)
        upcoming = await service.get_upcoming_recurring_expenses(current_user.id, days_ahead)
        return [UpcomingExpenseResponse(**item) for item in upcoming]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== HISTORY ENDPOINTS =====

@router.get("/{recurring_expense_id}/history", response_model=List[RecurringExpenseHistoryResponse])
async def get_recurring_expense_history(
    recurring_expense_id: UUID,
    limit: Optional[int] = Query(50, ge=1, le=200, description="Maximum number of history entries"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get processing history for a recurring expense."""
    try:
        service = RecurringExpenseService(db)
        history = await service.get_recurring_expense_history(recurring_expense_id, current_user.id, limit)
        return [RecurringExpenseHistoryResponse.from_orm(entry) for entry in history]
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/history/all", response_model=List[RecurringExpenseHistoryResponse])
async def get_user_recurring_expense_history(
    limit: Optional[int] = Query(100, ge=1, le=500, description="Maximum number of history entries"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all recurring expense processing history for the current user."""
    try:
        service = RecurringExpenseService(db)
        history = await service.get_user_recurring_expense_history(current_user.id, limit)
        return [RecurringExpenseHistoryResponse.from_orm(entry) for entry in history]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== NOTIFICATION ENDPOINTS =====

@router.get("/notifications/", response_model=List[RecurringExpenseNotificationResponse])
async def get_notifications(
    unread_only: bool = Query(False, description="Return only unread notifications"),
    limit: Optional[int] = Query(50, ge=1, le=200, description="Maximum number of notifications"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get notifications for the current user."""
    try:
        service = RecurringExpenseService(db)
        notifications = await service.get_user_notifications(current_user.id, unread_only, limit)
        return [RecurringExpenseNotificationResponse.from_orm(notif) for notif in notifications]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/notifications/{notification_id}/mark-read", status_code=status.HTTP_200_OK)
async def mark_notification_as_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a notification as read."""
    try:
        service = RecurringExpenseService(db)
        success = await service.mark_notification_as_read(notification_id, current_user.id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        return {"message": "Notification marked as read"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== ANALYTICS ENDPOINTS =====

@router.get("/analytics/summary", response_model=RecurringExpenseSummaryResponse)
async def get_recurring_expense_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get summary statistics for user's recurring expenses."""
    try:
        service = RecurringExpenseService(db)
        summary = await service.get_recurring_expense_summary(current_user.id)
        return RecurringExpenseSummaryResponse(**summary)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/analytics/by-category", response_model=List[Dict[str, Any]])
async def get_recurring_expenses_by_category(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get recurring expenses grouped by category."""
    try:
        service = RecurringExpenseService(db)
        category_data = await service.get_recurring_expenses_by_category(current_user.id)
        return category_data
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))