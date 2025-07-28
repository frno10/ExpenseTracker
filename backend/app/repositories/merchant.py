"""
Merchant repository for database operations.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import MerchantCreate, MerchantTable, MerchantUpdate
from .base import BaseRepository


class MerchantRepository(BaseRepository[MerchantTable, MerchantCreate, MerchantUpdate]):
    """Repository for merchant-related database operations."""

    def __init__(self):
        super().__init__(MerchantTable)

    async def get_by_name(
        self, 
        db: AsyncSession, 
        name: str,
        user_id: UUID
    ) -> Optional[MerchantTable]:
        """
        Get a merchant by name for a specific user.
        
        Args:
            db: Database session
            name: Merchant name
            user_id: User ID
            
        Returns:
            Merchant instance or None if not found
        """
        query = select(self.model).where(
            self.model.name == name,
            self.model.user_id == user_id
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_normalized_name(
        self, 
        db: AsyncSession, 
        normalized_name: str,
        user_id: UUID
    ) -> Optional[MerchantTable]:
        """
        Get a merchant by normalized name for a specific user.
        
        Args:
            db: Database session
            normalized_name: Normalized merchant name
            user_id: User ID
            
        Returns:
            Merchant instance or None if not found
        """
        query = select(self.model).where(
            self.model.normalized_name == normalized_name,
            self.model.user_id == user_id
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def search_by_name(
        self,
        db: AsyncSession,
        search_term: str,
        user_id: UUID,
        limit: int = 10
    ) -> List[MerchantTable]:
        """
        Search merchants by name for a specific user.
        
        Args:
            db: Database session
            search_term: Search term
            user_id: User ID
            limit: Maximum number of results
            
        Returns:
            List of matching merchant instances
        """
        search_pattern = f"%{search_term}%"
        query = (
            select(self.model)
            .where(
                self.model.user_id == user_id,
                self.model.name.ilike(search_pattern)
            )
            .options(selectinload(self.model.default_category))
            .limit(limit)
        )
        result = await db.execute(query)
        return result.scalars().all()

    async def get_merchants_with_category(
        self,
        db: AsyncSession,
        category_id: UUID,
        user_id: UUID
    ) -> List[MerchantTable]:
        """
        Get all merchants with a specific default category.
        
        Args:
            db: Database session
            category_id: Category ID
            user_id: User ID
            
        Returns:
            List of merchant instances
        """
        query = (
            select(self.model)
            .where(
                self.model.default_category_id == category_id,
                self.model.user_id == user_id
            )
            .options(selectinload(self.model.default_category))
        )
        result = await db.execute(query)
        return result.scalars().all()

    async def get_merchants_without_category(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> List[MerchantTable]:
        """
        Get all merchants without a default category.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            List of merchant instances without default category
        """
        query = (
            select(self.model)
            .where(
                self.model.default_category_id.is_(None),
                self.model.user_id == user_id
            )
        )
        result = await db.execute(query)
        return result.scalars().all()


# Create repository instance
merchant_repository = MerchantRepository()