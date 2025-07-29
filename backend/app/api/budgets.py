"""
Budget API endpoints.
"""
import logging
from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.security import rate_limit
from app.models.budget import (
    BudgetCreate,
    BudgetSchema,
    BudgetUpdate,
    CategoryBudgetCreate,
    CategoryBudgetSchema,
    CategoryBudgetUpdate,
)
from app.models.user import User
from app.services.budget_service import budget_service, BudgetAlert
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


class BudgetCreateRequest(BaseModel):
    """Request model for creating a budget with category budgets."""
    budget: BudgetCreate
    category_budgets: Optional[List[CategoryBudgetCreate]] = None


class BudgetAlertResponse(BaseModel):
    """Response model for budget alerts."""
    budget_id: UUID
    category_id: Optional[UUID]
    alert_type: str
    message: str
    percentage_used: float
    amount_spent: float
    amount_limit: float
    amount_remaining: float


class BudgetProgressResponse(BaseModel):
    """Response model for budget progress."""
    budget_id: UUID
    budget_name: str
    period: str
    start_date: date
    end_date: Optional[date]
    total_limit: Optional[float]
    total_spent: float
    total_remaining: Optional[float]
    total_percentage: Optional[float]
    categories: List[dict]


@router.post("/", response_model=BudgetSchema, status_code=status.HTTP_201_CREATED)
@rate_limit("create_budget", per_minute=10)
async def create_budget(
    request: BudgetCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new budget with optional category budgets.
    
    Args:
        request: Budget creation request
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Created budget
    """
    logger.info(f"Creating budget for user {current_user.id}: {request.budget.name}")
    
    try:
        # Set user_id
        request.budget.user_id = current_user.id
        
        # Set budget_id for category budgets (will be updated in service)
        if request.category_budgets:
            for cb in request.category_budgets:
                cb.budget_id = UUID("00000000-0000-0000-0000-000000000000")  # Placeholder
        
        budget = await budget_service.create_budget(
            db, request.budget, request.category_budgets
        )
        
        logger.info(f"Created budget {budget.id}")
        return BudgetSchema.from_orm(budget)
        
    except Exception as e:
        logger.error(f"Error creating budget: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create budget: {str(e)}"
        )


@router.get("/", response_model=List[BudgetSchema])
@rate_limit("list_budgets", per_minute=30)
async def list_budgets(
    active_only: bool = Query(False, description="Only return active budgets"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all budgets for the current user.
    
    Args:
        active_only: If True, only return active budgets
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List of budgets
    """
    logger.info(f"Listing budgets for user {current_user.id}, active_only={active_only}")
    
    try:
        budgets = await budget_service.get_user_budgets(db, current_user.id, active_only)
        return [BudgetSchema.from_orm(budget) for budget in budgets]
        
    except Exception as e:
        logger.error(f"Error listing budgets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list budgets: {str(e)}"
        )


@router.get("/{budget_id}", response_model=BudgetSchema)
@rate_limit("get_budget", per_minute=60)
async def get_budget(
    budget_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific budget with updated spending amounts.
    
    Args:
        budget_id: Budget ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Budget details
    """
    logger.info(f"Getting budget {budget_id} for user {current_user.id}")
    
    try:
        budget = await budget_service.get_budget_with_spending(db, budget_id, current_user.id)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found"
            )
        
        return BudgetSchema.from_orm(budget)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting budget: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get budget: {str(e)}"
        )


@router.put("/{budget_id}", response_model=BudgetSchema)
@rate_limit("update_budget", per_minute=20)
async def update_budget(
    budget_id: UUID,
    budget_data: BudgetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing budget.
    
    Args:
        budget_id: Budget ID
        budget_data: Budget update data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Updated budget
    """
    logger.info(f"Updating budget {budget_id} for user {current_user.id}")
    
    try:
        budget = await budget_service.update_budget(db, budget_id, budget_data, current_user.id)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found"
            )
        
        return BudgetSchema.from_orm(budget)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating budget: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update budget: {str(e)}"
        )


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
@rate_limit("delete_budget", per_minute=10)
async def delete_budget(
    budget_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a budget and all its category budgets.
    
    Args:
        budget_id: Budget ID
        db: Database session
        current_user: Current authenticated user
    """
    logger.info(f"Deleting budget {budget_id} for user {current_user.id}")
    
    try:
        success = await budget_service.delete_budget(db, budget_id, current_user.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting budget: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete budget: {str(e)}"
        )


@router.post("/{budget_id}/categories", response_model=CategoryBudgetSchema, status_code=status.HTTP_201_CREATED)
@rate_limit("add_category_budget", per_minute=20)
async def add_category_budget(
    budget_id: UUID,
    category_budget_data: CategoryBudgetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a category budget to an existing budget.
    
    Args:
        budget_id: Budget ID
        category_budget_data: Category budget creation data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Created category budget
    """
    logger.info(f"Adding category budget to budget {budget_id} for user {current_user.id}")
    
    try:
        # Set budget_id
        category_budget_data.budget_id = budget_id
        
        category_budget = await budget_service.add_category_budget(
            db, category_budget_data, current_user.id
        )
        if not category_budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found or category budget already exists"
            )
        
        return CategoryBudgetSchema.from_orm(category_budget)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding category budget: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add category budget: {str(e)}"
        )


@router.put("/categories/{category_budget_id}", response_model=CategoryBudgetSchema)
@rate_limit("update_category_budget", per_minute=30)
async def update_category_budget(
    category_budget_id: UUID,
    category_budget_data: CategoryBudgetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a category budget.
    
    Args:
        category_budget_id: Category budget ID
        category_budget_data: Category budget update data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Updated category budget
    """
    logger.info(f"Updating category budget {category_budget_id} for user {current_user.id}")
    
    try:
        category_budget = await budget_service.update_category_budget(
            db, category_budget_id, category_budget_data, current_user.id
        )
        if not category_budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category budget not found"
            )
        
        return CategoryBudgetSchema.from_orm(category_budget)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating category budget: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update category budget: {str(e)}"
        )


@router.delete("/categories/{category_budget_id}", status_code=status.HTTP_204_NO_CONTENT)
@rate_limit("delete_category_budget", per_minute=20)
async def delete_category_budget(
    category_budget_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a category budget.
    
    Args:
        category_budget_id: Category budget ID
        db: Database session
        current_user: Current authenticated user
    """
    logger.info(f"Deleting category budget {category_budget_id} for user {current_user.id}")
    
    try:
        success = await budget_service.remove_category_budget(
            db, category_budget_id, current_user.id
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category budget not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting category budget: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete category budget: {str(e)}"
        )


@router.get("/{budget_id}/progress", response_model=BudgetProgressResponse)
@rate_limit("get_budget_progress", per_minute=60)
async def get_budget_progress(
    budget_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed budget progress information.
    
    Args:
        budget_id: Budget ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Budget progress data
    """
    logger.info(f"Getting budget progress for {budget_id} for user {current_user.id}")
    
    try:
        progress = await budget_service.get_budget_progress(db, budget_id, current_user.id)
        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found"
            )
        
        return BudgetProgressResponse(**progress)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting budget progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get budget progress: {str(e)}"
        )


@router.get("/alerts/", response_model=List[BudgetAlertResponse])
@rate_limit("get_budget_alerts", per_minute=30)
async def get_budget_alerts(
    budget_id: Optional[UUID] = Query(None, description="Specific budget ID to check"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get budget alerts for the current user.
    
    Args:
        budget_id: Optional specific budget ID to check
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List of budget alerts
    """
    logger.info(f"Getting budget alerts for user {current_user.id}")
    
    try:
        alerts = await budget_service.check_budget_alerts(db, current_user.id, budget_id)
        
        return [
            BudgetAlertResponse(
                budget_id=alert.budget_id,
                category_id=alert.category_id,
                alert_type=alert.alert_type,
                message=alert.message,
                percentage_used=alert.percentage_used,
                amount_spent=float(alert.amount_spent),
                amount_limit=float(alert.amount_limit),
                amount_remaining=float(alert.amount_remaining)
            )
            for alert in alerts
        ]
        
    except Exception as e:
        logger.error(f"Error getting budget alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get budget alerts: {str(e)}"
        )


@router.post("/{budget_id}/recurring", response_model=BudgetSchema, status_code=status.HTTP_201_CREATED)
@rate_limit("create_recurring_budget", per_minute=5)
async def create_recurring_budget(
    budget_id: UUID,
    next_period_start: date,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new budget based on an existing budget for the next period.
    
    Args:
        budget_id: Base budget ID to copy from
        next_period_start: Start date for the new budget period
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Created recurring budget
    """
    logger.info(f"Creating recurring budget from {budget_id} for user {current_user.id}")
    
    try:
        budget = await budget_service.create_recurring_budget(
            db, budget_id, current_user.id, next_period_start
        )
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Base budget not found"
            )
        
        return BudgetSchema.from_orm(budget)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating recurring budget: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create recurring budget: {str(e)}"
        )