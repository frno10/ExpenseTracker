"""
Base repository class with common CRUD operations.
"""
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.observability_middleware import DatabaseObservabilityMixin
from app.models.base import BaseTable

ModelType = TypeVar("ModelType", bound=BaseTable)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType], DatabaseObservabilityMixin):
    """
    Base repository class with common CRUD operations.
    
    This class provides a generic interface for database operations
    that can be inherited by specific entity repositories.
    """
    
    def __init__(self, model: Type[ModelType]):
        """
        Initialize repository with model class.
        
        Args:
            model: SQLAlchemy model class
        """
        self.model = model
    
    async def create(
        self, 
        db: AsyncSession, 
        *, 
        obj_in: CreateSchemaType
    ) -> ModelType:
        """
        Create a new record.
        
        Args:
            db: Database session
            obj_in: Pydantic schema with creation data
            
        Returns:
            Created model instance
        """
        async def _create():
            obj_data = obj_in.model_dump()
            db_obj = self.model(**obj_data)
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        
        return await self._execute_with_observability(
            "create", self.model.__tablename__, _create
        )
    
    async def get(
        self, 
        db: AsyncSession, 
        id: UUID,
        *,
        load_relationships: Optional[List[str]] = None
    ) -> Optional[ModelType]:
        """
        Get a record by ID.
        
        Args:
            db: Database session
            id: Record ID
            load_relationships: List of relationship names to eager load
            
        Returns:
            Model instance or None if not found
        """
        async def _get():
            query = select(self.model).where(self.model.id == id)
            
            # Add eager loading for relationships
            if load_relationships:
                for relationship in load_relationships:
                    query = query.options(selectinload(getattr(self.model, relationship)))
            
            result = await db.execute(query)
            return result.scalar_one_or_none()
        
        return await self._execute_with_observability(
            "get", self.model.__tablename__, _get
        )
    
    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        load_relationships: Optional[List[str]] = None
    ) -> List[ModelType]:
        """
        Get multiple records with optional filtering.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Dictionary of field filters
            load_relationships: List of relationship names to eager load
            
        Returns:
            List of model instances
        """
        query = select(self.model)
        
        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)
        
        # Add eager loading for relationships
        if load_relationships:
            for relationship in load_relationships:
                query = query.options(selectinload(getattr(self.model, relationship)))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Update a record.
        
        Args:
            db: Database session
            db_obj: Existing model instance
            obj_in: Pydantic schema or dict with update data
            
        Returns:
            Updated model instance
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def delete(self, db: AsyncSession, *, id: UUID) -> Optional[ModelType]:
        """
        Delete a record by ID.
        
        Args:
            db: Database session
            id: Record ID
            
        Returns:
            Deleted model instance or None if not found
        """
        db_obj = await self.get(db, id)
        if db_obj:
            await db.delete(db_obj)
            await db.commit()
        return db_obj
    
    async def count(
        self,
        db: AsyncSession,
        *,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count records with optional filtering.
        
        Args:
            db: Database session
            filters: Dictionary of field filters
            
        Returns:
            Number of matching records
        """
        query = select(self.model)
        
        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)
        
        result = await db.execute(query)
        return len(result.scalars().all())
    
    async def exists(self, db: AsyncSession, *, id: UUID) -> bool:
        """
        Check if a record exists by ID.
        
        Args:
            db: Database session
            id: Record ID
            
        Returns:
            True if record exists, False otherwise
        """
        query = select(self.model.id).where(self.model.id == id)
        result = await db.execute(query)
        return result.scalar_one_or_none() is not None