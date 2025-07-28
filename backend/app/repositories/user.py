"""
User repository for database operations.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserCreate, UserTable, UserUpdate
from .base import BaseRepository


class UserRepository(BaseRepository[UserTable, UserCreate, UserUpdate]):
    """Repository for user-related database operations."""
    
    def __init__(self):
        super().__init__(UserTable)
    
    async def get_by_email(
        self, 
        db: AsyncSession, 
        email: str
    ) -> Optional[UserTable]:
        """
        Get a user by email address.
        
        Args:
            db: Database session
            email: User email address
            
        Returns:
            User instance or None if not found
        """
        query = select(self.model).where(self.model.email == email)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def create_user(
        self,
        db: AsyncSession,
        *,
        email: str,
        name: Optional[str] = None,
        timezone: str = "UTC",
        currency: str = "USD"
    ) -> UserTable:
        """
        Create a new user.
        
        Args:
            db: Database session
            email: User email address
            name: User display name
            timezone: User timezone
            currency: User default currency
            
        Returns:
            Created user instance
        """
        user_data = UserCreate(
            email=email,
            name=name,
            timezone=timezone,
            currency=currency,
            is_active=True
        )
        
        return await self.create(db, obj_in=user_data)
    
    async def update_last_login(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Optional[UserTable]:
        """
        Update user's last login timestamp.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Updated user instance or None if not found
        """
        from datetime import datetime
        
        user = await self.get(db, user_id)
        if user:
            # For now, we'll use updated_at as last_login
            # In the future, add a dedicated last_login field
            user.updated_at = datetime.utcnow()
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        return user
    
    async def deactivate_user(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Optional[UserTable]:
        """
        Deactivate a user account.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Updated user instance or None if not found
        """
        user = await self.get(db, user_id)
        if user:
            user.is_active = False
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        return user
    
    async def activate_user(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Optional[UserTable]:
        """
        Activate a user account.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Updated user instance or None if not found
        """
        user = await self.get(db, user_id)
        if user:
            user.is_active = True
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        return user


# Create repository instance
user_repository = UserRepository()