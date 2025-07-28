"""
Payment method management API endpoints.
"""
import logging
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.core.database import get_db
from app.core.security import RateLimits, user_limiter
from app.models import (
    PaymentMethodCreate,
    PaymentMethodSchema,
    PaymentMethodTable,
    PaymentMethodUpdate,
    PaymentType,
    UserTable,
)
from app.repositories.payment_method import payment_method_repository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payment-methods", tags=["payment-methods"])


@router.post("/", response_model=PaymentMethodSchema)
@user_limiter.limit(RateLimits.WRITE_OPERATIONS)
async def create_payment_method(
    request: Request,
    payment_method_data: PaymentMethodCreate,
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Create a new payment method.
    Creates a new payment method for the authenticated user.
    """
    # Ensure the payment method belongs to the current user
    payment_method_data.user_id = current_user.id
    
    try:
        # Check if payment method name already exists for this user
        existing_method = await payment_method_repository.get_by_name(db, payment_method_data.name, current_user.id)
        if existing_method:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment method with this name already exists"
            )
        
        payment_method = await payment_method_repository.create(db, obj_in=payment_method_data)
        logger.info(f"Payment method created: {payment_method.id} by user {current_user.id}")
        return payment_method
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create payment method: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create payment method"
        )


@router.get("/", response_model=List[PaymentMethodSchema])
@user_limiter.limit(RateLimits.READ_OPERATIONS)
async def get_payment_methods(
    request: Request,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    payment_type: Optional[PaymentType] = Query(None, description="Filter by payment type"),
    active_only: bool = Query(True, description="Return only active payment methods"),
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get payment methods for the current user.
    Supports filtering by payment type and active status.
    """
    try:
        filters = {"user_id": current_user.id}
        if payment_type:
            filters["type"] = payment_type
        if active_only:
            filters["is_active"] = True
            
        payment_methods = await payment_method_repository.get_multi(
            db,
            skip=skip,
            limit=limit,
            filters=filters
        )
        return payment_methods
    except Exception as e:
        logger.error(f"Failed to get payment methods: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve payment methods"
        )


@router.get("/{payment_method_id}", response_model=PaymentMethodSchema)
@user_limiter.limit(RateLimits.READ_OPERATIONS)
async def get_payment_method(
    request: Request,
    payment_method_id: UUID,
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get a specific payment method by ID.
    Returns the payment method if it belongs to the current user.
    """
    try:
        payment_method = await payment_method_repository.get(db, payment_method_id)
        if not payment_method:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment method not found"
            )
        
        # Ensure the payment method belongs to the current user
        if payment_method.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return payment_method
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get payment method {payment_method_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve payment method"
        )


@router.put("/{payment_method_id}", response_model=PaymentMethodSchema)
@user_limiter.limit(RateLimits.WRITE_OPERATIONS)
async def update_payment_method(
    request: Request,
    payment_method_id: UUID,
    payment_method_update: PaymentMethodUpdate,
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Update an existing payment method.
    Updates the payment method if it belongs to the current user.
    """
    try:
        # Get existing payment method
        payment_method = await payment_method_repository.get(db, payment_method_id)
        if not payment_method:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment method not found"
            )
        
        # Ensure the payment method belongs to the current user
        if payment_method.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Check for name conflicts if name is being updated
        if payment_method_update.name and payment_method_update.name != payment_method.name:
            existing_method = await payment_method_repository.get_by_name(db, payment_method_update.name, current_user.id)
            if existing_method:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Payment method with this name already exists"
                )
        
        # Update the payment method
        updated_payment_method = await payment_method_repository.update(
            db, 
            db_obj=payment_method, 
            obj_in=payment_method_update
        )
        logger.info(f"Payment method updated: {payment_method_id} by user {current_user.id}")
        return updated_payment_method
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update payment method {payment_method_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update payment method"
        )


@router.delete("/{payment_method_id}")
@user_limiter.limit(RateLimits.WRITE_OPERATIONS)
async def delete_payment_method(
    request: Request,
    payment_method_id: UUID,
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Delete a payment method.
    Deletes the payment method if it belongs to the current user.
    """
    try:
        # Get existing payment method
        payment_method = await payment_method_repository.get(db, payment_method_id)
        if not payment_method:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment method not found"
            )
        
        # Ensure the payment method belongs to the current user
        if payment_method.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Delete the payment method
        await payment_method_repository.delete(db, id=payment_method_id)
        logger.info(f"Payment method deleted: {payment_method_id} by user {current_user.id}")
        return {"message": "Payment method deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete payment method {payment_method_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete payment method"
        )


@router.get("/types/", response_model=List[str])
@user_limiter.limit(RateLimits.READ_OPERATIONS)
async def get_payment_types(
    request: Request,
    current_user: UserTable = Depends(get_current_active_user),
) -> Any:
    """
    Get available payment types.
    Returns the list of supported payment method types.
    """
    return [payment_type.value for payment_type in PaymentType]