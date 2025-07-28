"""
Category management API endpoints.
"""
import logging
from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.core.database import get_db
from app.core.security import RateLimits, user_limiter
from app.models import (
    CategoryCreate,
    CategorySchema,
    CategoryTable,
    CategoryUpdate,
    UserTable,
)
from app.repositories import category_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("/", response_model=CategorySchema)
@user_limiter.limit(RateLimits.WRITE_OPERATIONS)
async def create_category(
    request: Request,
    category_data: CategoryCreate,
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Create a new category.
    
    Requires authentication. The category will be associated with the current user.
    """
    # Ensure the category belongs to the current user
    category_data.user_id = current_user.id
    
    try:
        # Check if category name already exists for this user
        existing_category = await category_repository.get_by_name(db, category_data.name, current_user.id)
        if existing_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this name already exists"
            )
        
        category = await category_repository.create(db, obj_in=category_data)
        logger.info(f"Category created: {category.id} by user {current_user.id}")
        return category
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create category: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create category"
        )


@router.get("/", response_model=List[CategorySchema])
@user_limiter.limit(RateLimits.READ_OPERATIONS)
async def list_categories(
    request: Request,
    skip: int = Query(0, ge=0, description="Number of categories to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of categories to return"),
    include_subcategories: bool = Query(False, description="Include subcategories in response"),
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    List categories for the current user.
    
    Supports pagination and optional inclusion of subcategories.
    """
    try:
        filters = {"user_id": current_user.id}
        load_relationships = ["subcategories"] if include_subcategories else None
        
        categories = await category_repository.get_multi(
            db,
            skip=skip,
            limit=limit,
            filters=filters,
            load_relationships=load_relationships
        )
        
        logger.info(f"Listed {len(categories)} categories for user {current_user.id}")
        return categories
        
    except Exception as e:
        logger.error(f"Failed to list categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve categories"
        )


@router.get("/root", response_model=List[CategorySchema])
@user_limiter.limit(RateLimits.READ_OPERATIONS)
async def get_root_categories(
    request: Request,
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get root categories (categories without parent) for the current user.
    
    Includes subcategories in the response.
    """
    try:
        categories = await category_repository.get_root_categories(db)
        
        # Filter by user
        user_categories = [c for c in categories if c.user_id == current_user.id]
        
        logger.info(f"Retrieved {len(user_categories)} root categories for user {current_user.id}")
        return user_categories
        
    except Exception as e:
        logger.error(f"Failed to get root categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve root categories"
        )


@router.get("/custom", response_model=List[CategorySchema])
@user_limiter.limit(RateLimits.READ_OPERATIONS)
async def get_custom_categories(
    request: Request,
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get custom (user-created) categories for the current user.
    """
    try:
        categories = await category_repository.get_custom_categories(db)
        
        # Filter by user
        user_categories = [c for c in categories if c.user_id == current_user.id]
        
        logger.info(f"Retrieved {len(user_categories)} custom categories for user {current_user.id}")
        return user_categories
        
    except Exception as e:
        logger.error(f"Failed to get custom categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve custom categories"
        )


@router.get("/{category_id}", response_model=CategorySchema)
@user_limiter.limit(RateLimits.READ_OPERATIONS)
async def get_category(
    request: Request,
    category_id: UUID,
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get a specific category by ID.
    
    The category must belong to the current user.
    """
    try:
        category = await category_repository.get(
            db, 
            category_id,
            load_relationships=["parent_category", "subcategories"]
        )
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Ensure the category belongs to the current user
        if category.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        logger.info(f"Retrieved category {category_id} for user {current_user.id}")
        return category
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get category {category_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve category"
        )


@router.get("/{category_id}/subcategories", response_model=List[CategorySchema])
@user_limiter.limit(RateLimits.READ_OPERATIONS)
async def get_subcategories(
    request: Request,
    category_id: UUID,
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get subcategories of a specific category.
    
    The parent category must belong to the current user.
    """
    try:
        # First verify the parent category exists and belongs to user
        parent_category = await category_repository.get(db, category_id)
        
        if not parent_category or parent_category.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        subcategories = await category_repository.get_subcategories(db, category_id)
        
        logger.info(f"Retrieved {len(subcategories)} subcategories for category {category_id}")
        return subcategories
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get subcategories for {category_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subcategories"
        )


@router.get("/{category_id}/hierarchy", response_model=List[CategorySchema])
@user_limiter.limit(RateLimits.READ_OPERATIONS)
async def get_category_hierarchy(
    request: Request,
    category_id: UUID,
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get the full hierarchy path for a category (from root to category).
    
    The category must belong to the current user.
    """
    try:
        # First verify the category exists and belongs to user
        category = await category_repository.get(db, category_id)
        
        if not category or category.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        hierarchy = await category_repository.get_category_hierarchy(db, category_id)
        
        logger.info(f"Retrieved hierarchy for category {category_id} ({len(hierarchy)} levels)")
        return hierarchy
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get hierarchy for category {category_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve category hierarchy"
        )


@router.put("/{category_id}", response_model=CategorySchema)
@user_limiter.limit(RateLimits.WRITE_OPERATIONS)
async def update_category(
    request: Request,
    category_id: UUID,
    category_update: CategoryUpdate,
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Update an existing category.
    
    The category must belong to the current user.
    """
    try:
        # Get the existing category
        category = await category_repository.get(db, category_id)
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Ensure the category belongs to the current user
        if category.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Check if new name conflicts with existing categories
        if category_update.name and category_update.name != category.name:
            existing_category = await category_repository.get_by_name(db, category_update.name, current_user.id)
            if existing_category:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category with this name already exists"
                )
        
        # Update the category
        updated_category = await category_repository.update(
            db, 
            db_obj=category, 
            obj_in=category_update
        )
        
        logger.info(f"Updated category {category_id} for user {current_user.id}")
        return updated_category
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update category {category_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update category"
        )


@router.delete("/{category_id}")
@user_limiter.limit(RateLimits.WRITE_OPERATIONS)
async def delete_category(
    request: Request,
    category_id: UUID,
    current_user: UserTable = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Delete a category.
    
    The category must belong to the current user.
    Note: This will fail if the category has associated expenses.
    """
    try:
        # Get the existing category
        category = await category_repository.get(db, category_id)
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Ensure the category belongs to the current user
        if category.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Delete the category
        await category_repository.delete(db, id=category_id)
        
        logger.info(f"Deleted category {category_id} for user {current_user.id}")
        return {"message": "Category deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete category {category_id}: {e}")
        # This might be a foreign key constraint error
        if "foreign key" in str(e).lower() or "constraint" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete category that has associated expenses"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete category"
        )