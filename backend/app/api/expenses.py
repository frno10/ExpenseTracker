"""
Expense management API endpoints.
"""
import logging
from datetime import date
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.core.database import get_db
from app.core.security import RateLimits, user_limiter
from app.models import (
    ExpenseCreate,
    ExpenseSchema,
    ExpenseTable,
    ExpenseUpdate,
    UserTable,
)
from app.repositories import expense_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.post("/", response_model=ExpenseSchema)
@user_limiter.limit(RateLimits.WRITE_OPERATIONS)
async def create_expense(
    request: Request,
    expense_data: ExpenseCreate,
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Create a new expense.
    
    Requires authentication. The expense will be associated with the current user.
    """
    # Ensure the expense belongs to the current user
    expense_data.user_id = current_user.id
    
    try:
        expense = await expense_repository.create(db, obj_in=expense_data)
        logger.info(f"Expense created: {expense.id} by user {current_user.id}")
        return expense
    except Exception as e:
        logger.error(f"Failed to create expense: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create expense"
        )


@router.get("/", response_model=List[ExpenseSchema])
@user_limiter.limit(RateLimits.READ_OPERATIONS)
async def list_expenses(
    request: Request,
    skip: int = Query(0, ge=0, description="Number of expenses to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of expenses to return"),
    start_date: Optional[date] = Query(None, description="Filter expenses from this date"),
    end_date: Optional[date] = Query(None, description="Filter expenses until this date"),
    category_id: Optional[UUID] = Query(None, description="Filter by category ID"),
    payment_method_id: Optional[UUID] = Query(None, description="Filter by payment method ID"),
    merchant_id: Optional[UUID] = Query(None, description="Filter by merchant ID"),
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    List expenses for the current user with optional filtering.
    
    Supports pagination and filtering by date range, category, payment method, and merchant.
    """
    try:
        if start_date and end_date:
            # Use date range filtering
            expenses = await expense_repository.get_by_date_range(
                db,
                start_date=start_date,
                end_date=end_date,
                category_id=category_id,
                payment_method_id=payment_method_id,
                skip=skip,
                limit=limit
            )
            # Filter by user (repository method doesn't include user filtering yet)
            expenses = [e for e in expenses if e.user_id == current_user.id]
        else:
            # Use general filtering
            filters = {"user_id": current_user.id}
            if category_id:
                filters["category_id"] = category_id
            if payment_method_id:
                filters["payment_method_id"] = payment_method_id
            if merchant_id:
                filters["merchant_id"] = merchant_id
            
            expenses = await expense_repository.get_multi(
                db,
                skip=skip,
                limit=limit,
                filters=filters,
                load_relationships=["category", "payment_method", "merchant"]
            )
        
        logger.info(f"Listed {len(expenses)} expenses for user {current_user.id}")
        return expenses
        
    except Exception as e:
        logger.error(f"Failed to list expenses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve expenses"
        )


@router.get("/{expense_id}", response_model=ExpenseSchema)
@user_limiter.limit(RateLimits.READ_OPERATIONS)
async def get_expense(
    request: Request,
    expense_id: UUID,
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get a specific expense by ID.
    
    The expense must belong to the current user.
    """
    try:
        expense = await expense_repository.get(
            db, 
            expense_id,
            load_relationships=["category", "payment_method", "merchant", "attachments"]
        )
        
        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense not found"
            )
        
        # Ensure the expense belongs to the current user
        if expense.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense not found"
            )
        
        logger.info(f"Retrieved expense {expense_id} for user {current_user.id}")
        return expense
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get expense {expense_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve expense"
        )


@router.put("/{expense_id}", response_model=ExpenseSchema)
@user_limiter.limit(RateLimits.WRITE_OPERATIONS)
async def update_expense(
    request: Request,
    expense_id: UUID,
    expense_update: ExpenseUpdate,
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Update an existing expense.
    
    The expense must belong to the current user.
    """
    try:
        # Get the existing expense
        expense = await expense_repository.get(db, expense_id)
        
        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense not found"
            )
        
        # Ensure the expense belongs to the current user
        if expense.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense not found"
            )
        
        # Update the expense
        updated_expense = await expense_repository.update(
            db, 
            db_obj=expense, 
            obj_in=expense_update
        )
        
        logger.info(f"Updated expense {expense_id} for user {current_user.id}")
        return updated_expense
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update expense {expense_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update expense"
        )


@router.delete("/{expense_id}")
@user_limiter.limit(RateLimits.WRITE_OPERATIONS)
async def delete_expense(
    request: Request,
    expense_id: UUID,
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Delete an expense.
    
    The expense must belong to the current user.
    """
    try:
        # Get the existing expense
        expense = await expense_repository.get(db, expense_id)
        
        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense not found"
            )
        
        # Ensure the expense belongs to the current user
        if expense.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense not found"
            )
        
        # Delete the expense
        await expense_repository.delete(db, id=expense_id)
        
        logger.info(f"Deleted expense {expense_id} for user {current_user.id}")
        return {"message": "Expense deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete expense {expense_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete expense"
        )


@router.get("/search/", response_model=List[ExpenseSchema])
@user_limiter.limit(RateLimits.READ_OPERATIONS)
async def search_expenses(
    request: Request,
    q: str = Query(..., min_length=1, description="Search term"),
    skip: int = Query(0, ge=0, description="Number of expenses to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of expenses to return"),
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Search expenses by description or notes.
    
    Searches through expense descriptions and notes for the current user.
    """
    try:
        expenses = await expense_repository.search_expenses(
            db,
            search_term=q,
            skip=skip,
            limit=limit
        )
        
        # Filter by user (repository method doesn't include user filtering yet)
        expenses = [e for e in expenses if e.user_id == current_user.id]
        
        logger.info(f"Search '{q}' returned {len(expenses)} expenses for user {current_user.id}")
        return expenses
        
    except Exception as e:
        logger.error(f"Failed to search expenses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search expenses"
        )


@router.get("/recent/", response_model=List[ExpenseSchema])
@user_limiter.limit(RateLimits.READ_OPERATIONS)
async def get_recent_expenses(
    request: Request,
    limit: int = Query(10, ge=1, le=50, description="Number of recent expenses to return"),
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get recent expenses for the current user.
    
    Returns the most recently created expenses.
    """
    try:
        expenses = await expense_repository.get_recent_expenses(db, limit=limit)
        
        # Filter by user (repository method doesn't include user filtering yet)
        expenses = [e for e in expenses if e.user_id == current_user.id]
        
        logger.info(f"Retrieved {len(expenses)} recent expenses for user {current_user.id}")
        return expenses
        
    except Exception as e:
        logger.error(f"Failed to get recent expenses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recent expenses"
        )