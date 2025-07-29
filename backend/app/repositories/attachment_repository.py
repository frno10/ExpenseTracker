import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc
from uuid import UUID

from ..models.attachment import AttachmentTable, AttachmentType
from ..models.expense import ExpenseTable


class AttachmentRepository:
    """Repository for attachment data access operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ===== ATTACHMENT CRUD OPERATIONS =====
    
    def create_attachment(self, attachment_data: Dict[str, Any]) -> AttachmentTable:
        """Create a new attachment."""
        attachment = AttachmentTable(**attachment_data)
        self.db.add(attachment)
        self.db.commit()
        self.db.refresh(attachment)
        return attachment
    
    def get_attachment_by_id(
        self, 
        attachment_id: UUID, 
        user_id: UUID
    ) -> Optional[AttachmentTable]:
        """Get attachment by ID for a specific user."""
        return self.db.query(AttachmentTable).filter(
            AttachmentTable.id == attachment_id,
            AttachmentTable.user_id == user_id
        ).options(
            joinedload(AttachmentTable.expense)
        ).first()
    
    def get_expense_attachments(
        self, 
        expense_id: UUID, 
        user_id: UUID
    ) -> List[AttachmentTable]:
        """Get all attachments for a specific expense."""
        return self.db.query(AttachmentTable).filter(
            AttachmentTable.expense_id == expense_id,
            AttachmentTable.user_id == user_id
        ).order_by(AttachmentTable.created_at).all()
    
    def get_user_attachments(
        self, 
        user_id: UUID, 
        attachment_type: Optional[AttachmentType] = None,
        limit: Optional[int] = None
    ) -> List[AttachmentTable]:
        """Get all attachments for a user."""
        query = self.db.query(AttachmentTable).filter(
            AttachmentTable.user_id == user_id
        )
        
        if attachment_type:
            query = query.filter(AttachmentTable.attachment_type == attachment_type)
        
        query = query.options(
            joinedload(AttachmentTable.expense)
        ).order_by(desc(AttachmentTable.created_at))
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def update_attachment(
        self, 
        attachment_id: UUID, 
        user_id: UUID, 
        update_data: Dict[str, Any]
    ) -> Optional[AttachmentTable]:
        """Update an attachment."""
        attachment = self.get_attachment_by_id(attachment_id, user_id)
        if not attachment:
            return None
        
        for key, value in update_data.items():
            if hasattr(attachment, key):
                setattr(attachment, key, value)
        
        attachment.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(attachment)
        return attachment
    
    def delete_attachment(self, attachment_id: UUID, user_id: UUID) -> bool:
        """Delete an attachment."""
        attachment = self.get_attachment_by_id(attachment_id, user_id)
        if not attachment:
            return False
        
        self.db.delete(attachment)
        self.db.commit()
        return True
    
    # ===== SEARCH OPERATIONS =====
    
    def search_attachments_by_filename(
        self, 
        user_id: UUID, 
        search_term: str,
        limit: Optional[int] = None
    ) -> List[AttachmentTable]:
        """Search attachments by filename."""
        query = self.db.query(AttachmentTable).filter(
            AttachmentTable.user_id == user_id,
            or_(
                AttachmentTable.filename.ilike(f"%{search_term}%"),
                AttachmentTable.original_filename.ilike(f"%{search_term}%")
            )
        ).options(
            joinedload(AttachmentTable.expense)
        ).order_by(desc(AttachmentTable.created_at))
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_attachments_by_expense_ids(
        self, 
        expense_ids: List[UUID], 
        user_id: UUID
    ) -> List[AttachmentTable]:
        """Get attachments for multiple expenses."""
        if not expense_ids:
            return []
        
        return self.db.query(AttachmentTable).filter(
            AttachmentTable.expense_id.in_(expense_ids),
            AttachmentTable.user_id == user_id
        ).options(
            joinedload(AttachmentTable.expense)
        ).order_by(AttachmentTable.expense_id, AttachmentTable.created_at).all()
    
    # ===== ANALYTICS AND REPORTING =====
    
    def get_attachment_statistics(self, user_id: UUID) -> Dict[str, Any]:
        """Get attachment statistics for a user."""
        # Total attachments
        total_attachments = self.db.query(AttachmentTable).filter(
            AttachmentTable.user_id == user_id
        ).count()
        
        # Attachments by type
        type_counts = self.db.query(
            AttachmentTable.attachment_type,
            func.count(AttachmentTable.id).label('count')
        ).filter(
            AttachmentTable.user_id == user_id
        ).group_by(AttachmentTable.attachment_type).all()
        
        type_breakdown = {
            attachment_type.value: count 
            for attachment_type, count in type_counts
        }
        
        # Total file size
        total_size_result = self.db.query(
            func.sum(AttachmentTable.file_size).label('total_size')
        ).filter(
            AttachmentTable.user_id == user_id
        ).first()
        
        total_size = total_size_result.total_size or 0
        
        # Average file size
        avg_size = total_size / total_attachments if total_attachments > 0 else 0
        
        # Most common file types
        mime_type_counts = self.db.query(
            AttachmentTable.mime_type,
            func.count(AttachmentTable.id).label('count')
        ).filter(
            AttachmentTable.user_id == user_id
        ).group_by(AttachmentTable.mime_type).order_by(
            desc(func.count(AttachmentTable.id))
        ).limit(10).all()
        
        common_file_types = [
            {'mime_type': mime_type, 'count': count}
            for mime_type, count in mime_type_counts
        ]
        
        # Expenses with attachments
        expenses_with_attachments = self.db.query(
            func.count(func.distinct(AttachmentTable.expense_id)).label('count')
        ).filter(
            AttachmentTable.user_id == user_id
        ).first().count
        
        # Recent attachments (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_attachments = self.db.query(AttachmentTable).filter(
            AttachmentTable.user_id == user_id,
            AttachmentTable.created_at >= thirty_days_ago
        ).count()
        
        return {
            'total_attachments': total_attachments,
            'type_breakdown': type_breakdown,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'average_size_bytes': round(avg_size),
            'average_size_kb': round(avg_size / 1024, 2),
            'common_file_types': common_file_types,
            'expenses_with_attachments': expenses_with_attachments,
            'recent_attachments_30_days': recent_attachments
        }
    
    def get_large_attachments(
        self, 
        user_id: UUID, 
        min_size_mb: float = 1.0,
        limit: Optional[int] = None
    ) -> List[AttachmentTable]:
        """Get large attachments above specified size."""
        min_size_bytes = int(min_size_mb * 1024 * 1024)
        
        query = self.db.query(AttachmentTable).filter(
            AttachmentTable.user_id == user_id,
            AttachmentTable.file_size >= min_size_bytes
        ).options(
            joinedload(AttachmentTable.expense)
        ).order_by(desc(AttachmentTable.file_size))
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_attachments_without_expenses(self, user_id: UUID) -> List[AttachmentTable]:
        """Get orphaned attachments (attachments whose expenses were deleted)."""
        return self.db.query(AttachmentTable).outerjoin(
            ExpenseTable, AttachmentTable.expense_id == ExpenseTable.id
        ).filter(
            AttachmentTable.user_id == user_id,
            ExpenseTable.id.is_(None)
        ).all()
    
    # ===== FILE MANAGEMENT HELPERS =====
    
    def get_attachment_file_path(self, attachment_id: UUID, user_id: UUID) -> Optional[str]:
        """Get the file path for an attachment."""
        attachment = self.get_attachment_by_id(attachment_id, user_id)
        return attachment.file_path if attachment else None
    
    def update_file_path(
        self, 
        attachment_id: UUID, 
        user_id: UUID, 
        new_file_path: str
    ) -> bool:
        """Update the file path for an attachment."""
        attachment = self.get_attachment_by_id(attachment_id, user_id)
        if not attachment:
            return False
        
        attachment.file_path = new_file_path
        attachment.updated_at = datetime.utcnow()
        self.db.commit()
        return True
    
    def get_attachments_by_file_paths(
        self, 
        file_paths: List[str], 
        user_id: UUID
    ) -> List[AttachmentTable]:
        """Get attachments by their file paths."""
        if not file_paths:
            return []
        
        return self.db.query(AttachmentTable).filter(
            AttachmentTable.file_path.in_(file_paths),
            AttachmentTable.user_id == user_id
        ).all()
    
    # ===== CLEANUP OPERATIONS =====
    
    def get_old_attachments(
        self, 
        user_id: UUID, 
        days_old: int = 365
    ) -> List[AttachmentTable]:
        """Get attachments older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        return self.db.query(AttachmentTable).filter(
            AttachmentTable.user_id == user_id,
            AttachmentTable.created_at < cutoff_date
        ).options(
            joinedload(AttachmentTable.expense)
        ).order_by(AttachmentTable.created_at).all()
    
    def bulk_delete_attachments(
        self, 
        attachment_ids: List[UUID], 
        user_id: UUID
    ) -> int:
        """Bulk delete multiple attachments."""
        if not attachment_ids:
            return 0
        
        deleted_count = self.db.query(AttachmentTable).filter(
            AttachmentTable.id.in_(attachment_ids),
            AttachmentTable.user_id == user_id
        ).delete(synchronize_session=False)
        
        self.db.commit()
        return deleted_count