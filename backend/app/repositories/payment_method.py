"""
Payment method repository for database operations.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PaymentMethodCreate, PaymentMethodTable, PaymentMethodUpdate, PaymentType
from .base import BaseRepository


class PaymentMethodRepository(BaseRepository[PaymentMethodTable, PaymentMethodCreate, PaymentMethodUpdate]):
    """Repository for payment method-related database operations."""
    
    def __init__(self):
        super().__init__(PaymentMethodTable)
    
    async def get_by_name(
        self, 
        db: AsyncSession, 
        name: str,
        user_id: UUID
    ) -> Optional[PaymentMethodTable]:
        """
        Get a payment method by name for a specific user.
        
        Args:
            db: Database session
            name: Payment method name
            user_id: User ID
            
        Returns:
            Payment method instance or None if not found
        """
        query = select(self.model).where(
            self.model.name == name,
            self.model.user_id == user_id
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_type(
        self, 
        db: AsyncSession, 
        payment_type: PaymentType
    ) -> List[PaymentMethodTable]:
        """
        Get all payment methods of a specific type.
        
        Args:
            db: Database session
            payment_type: Payment type to filter by
            
        Returns:
            List of payment method instances
        """
        query = select(self.model).where(self.model.type == payment_type)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_active(
        self, 
        db: AsyncSession
    ) -> List[PaymentMethodTable]:
        """
        Get all active payment methods.
        
        Args:
            db: Database session
            
        Returns:
            List of active payment method instances
        """
        query = select(self.model).where(self.model.is_active == True)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_by_institution(
        self, 
        db: AsyncSession, 
        institution: str
    ) -> List[PaymentMethodTable]:
        """
        Get all payment methods from a specific institution.
        
        Args:
            db: Database session
            institution: Institution name
            
        Returns:
            List of payment method instances
        """
        query = select(self.model).where(self.model.institution == institution)
        result = await db.execute(query)
        return result.scalars().all()


# Create repository instance
payment_method_repository = PaymentMethodRepository()