"""
Category repository for database operations.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import CategoryCreate, CategoryTable, CategoryUpdate
from .base import BaseRepository


class CategoryRepository(BaseRepository[CategoryTable, CategoryCreate, CategoryUpdate]):
    """Repository for category-related database operations."""
    
    def __init__(self):
        super().__init__(CategoryTable)
    
    async def get_by_name(
        self, 
        db: AsyncSession, 
        name: str,
        user_id: UUID
    ) -> Optional[CategoryTable]:
        """
        Get a category by name for a specific user.
        
        Args:
            db: Database session
            name: Category name
            user_id: User ID
            
        Returns:
            Category instance or None if not found
        """
        query = select(self.model).where(
            self.model.name == name,
            self.model.user_id == user_id
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_root_categories(
        self, 
        db: AsyncSession
    ) -> List[CategoryTable]:
        """
        Get all root categories (categories without parent).
        
        Args:
            db: Database session
            
        Returns:
            List of root category instances
        """
        query = (
            select(self.model)
            .where(self.model.parent_category_id.is_(None))
            .options(selectinload(self.model.subcategories))
        )
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_subcategories(
        self, 
        db: AsyncSession, 
        parent_id: UUID
    ) -> List[CategoryTable]:
        """
        Get all subcategories of a parent category.
        
        Args:
            db: Database session
            parent_id: Parent category ID
            
        Returns:
            List of subcategory instances
        """
        query = select(self.model).where(self.model.parent_category_id == parent_id)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_category_hierarchy(
        self, 
        db: AsyncSession, 
        category_id: UUID
    ) -> List[CategoryTable]:
        """
        Get the full hierarchy path for a category (from root to category).
        
        Args:
            db: Database session
            category_id: Category ID
            
        Returns:
            List of categories from root to the specified category
        """
        hierarchy = []
        current_category = await self.get(db, category_id)
        
        while current_category:
            hierarchy.insert(0, current_category)
            if current_category.parent_category_id:
                current_category = await self.get(db, current_category.parent_category_id)
            else:
                break
        
        return hierarchy
    
    async def get_custom_categories(
        self, 
        db: AsyncSession
    ) -> List[CategoryTable]:
        """
        Get all custom (user-created) categories.
        
        Args:
            db: Database session
            
        Returns:
            List of custom category instances
        """
        query = select(self.model).where(self.model.is_custom == True)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_predefined_categories(
        self, 
        db: AsyncSession
    ) -> List[CategoryTable]:
        """
        Get all predefined (system) categories.
        
        Args:
            db: Database session
            
        Returns:
            List of predefined category instances
        """
        query = select(self.model).where(self.model.is_custom == False)
        result = await db.execute(query)
        return result.scalars().all()


# Create repository instance
category_repository = CategoryRepository()