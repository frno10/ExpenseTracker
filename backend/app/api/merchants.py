"""
Merchant management API endpoints.
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
    MerchantCreate,
    MerchantSchema,
    MerchantTable,
    MerchantUpdate,
    UserTable,
)
from app.repositories.merchant import merchant_repository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/merchants", tags=["merchants"])


@router.post("/", response_model=MerchantSchema)
@user_limiter.limit(RateLimits.WRITE_OPERATIONS)
async def create_merchant(
    request: Request,
    merchant_data: MerchantCreate,
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Create a new merchant.
    Creates a new merchant for the authenticated user.
    """
    # Ensure the merchant belongs to the current user
    merchant_data.user_id = current_user.id
    
    try:
        merchant = await merchant_repository.create(db, obj_in=merchant_data)
        logger.info(f"Merchant created: {merchant.id} by user {current_user.id}")
        return merchant
    except Exception as e:
        logger.error(f"Failed to create merchant: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create merchant"
        )


@router.get("/", response_model=List[MerchantSchema])
@user_limiter.limit(RateLimits.READ_OPERATIONS)
async def get_merchants(
    request: Request,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    search: Optional[str] = Query(None, description="Search merchants by name"),
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get merchants for the current user.
    Supports searching by merchant name.
    """
    try:
        if search:
            merchants = await merchant_repository.search_by_name(
                db, search_term=search, user_id=current_user.id, limit=limit
            )
        else:
            filters = {"user_id": current_user.id}
            merchants = await merchant_repository.get_multi(
                db,
                skip=skip,
                limit=limit,
                filters=filters,
                load_relationships=["default_category", "merchant_tags"]
            )
        return merchants
    except Exception as e:
        logger.error(f"Failed to get merchants: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve merchants"
        )


@router.get("/{merchant_id}", response_model=MerchantSchema)
@user_limiter.limit(RateLimits.READ_OPERATIONS)
async def get_merchant(
    request: Request,
    merchant_id: UUID,
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get a specific merchant by ID.
    Returns the merchant if it belongs to the current user.
    """
    try:
        merchant = await merchant_repository.get(
            db, 
            merchant_id,
            load_relationships=["default_category", "merchant_tags"]
        )
        if not merchant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Merchant not found"
            )
        
        # Ensure the merchant belongs to the current user
        if merchant.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return merchant
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get merchant {merchant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve merchant"
        )


@router.put("/{merchant_id}", response_model=MerchantSchema)
@user_limiter.limit(RateLimits.WRITE_OPERATIONS)
async def update_merchant(
    request: Request,
    merchant_id: UUID,
    merchant_update: MerchantUpdate,
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Update an existing merchant.
    Updates the merchant if it belongs to the current user.
    """
    try:
        # Get existing merchant
        merchant = await merchant_repository.get(db, merchant_id)
        if not merchant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Merchant not found"
            )
        
        # Ensure the merchant belongs to the current user
        if merchant.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Update the merchant
        updated_merchant = await merchant_repository.update(
            db, 
            db_obj=merchant, 
            obj_in=merchant_update
        )
        logger.info(f"Merchant updated: {merchant_id} by user {current_user.id}")
        return updated_merchant
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update merchant {merchant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update merchant"
        )


@router.delete("/{merchant_id}")
@user_limiter.limit(RateLimits.WRITE_OPERATIONS)
async def delete_merchant(
    request: Request,
    merchant_id: UUID,
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Delete a merchant.
    Deletes the merchant if it belongs to the current user.
    """
    try:
        # Get existing merchant
        merchant = await merchant_repository.get(db, merchant_id)
        if not merchant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Merchant not found"
            )
        
        # Ensure the merchant belongs to the current user
        if merchant.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Delete the merchant
        await merchant_repository.delete(db, id=merchant_id)
        logger.info(f"Merchant deleted: {merchant_id} by user {current_user.id}")
        return {"message": "Merchant deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete merchant {merchant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete merchant"
        )


@router.post("/match", response_model=Optional[MerchantSchema])
@user_limiter.limit(RateLimits.READ_OPERATIONS)
async def match_merchant(
    request: Request,
    merchant_name: str = Query(..., description="Merchant name to match"),
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Find the best matching merchant for a given name.
    Uses normalized name matching to find existing merchants.
    Useful for statement parsing and auto-categorization.
    """
    try:
        # Try exact match first
        merchant = await merchant_repository.get_by_normalized_name(
            db, merchant_name.lower().strip(), current_user.id
        )
        if merchant:
            return merchant
        
        # Try partial match
        merchants = await merchant_repository.search_by_name(
            db, search_term=merchant_name, user_id=current_user.id, limit=5
        )
        
        # Return the first match if any
        return merchants[0] if merchants else None
    except Exception as e:
        logger.error(f"Failed to match merchant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to match merchant"
        )