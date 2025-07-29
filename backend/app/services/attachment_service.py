import os
import uuid
import shutil
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, BinaryIO
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import UploadFile
from PIL import Image
import magic

from ..models.attachment import AttachmentTable, AttachmentType
from ..repositories.attachment_repository import AttachmentRepository
from ..core.exceptions import ValidationError, NotFoundError, BusinessLogicError
from ..core.config import settings


class AttachmentService:
    """Service for attachment management and file operations."""
    
    # Allowed file types and their corresponding MIME types
    ALLOWED_IMAGE_TYPES = {
        'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'
    }
    
    ALLOWED_DOCUMENT_TYPES = {
        'application/pdf', 'text/plain', 'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    
    ALLOWED_MIME_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_DOCUMENT_TYPES
    
    # Maximum file size (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = AttachmentRepository(db)
        self.upload_dir = Path(getattr(settings, 'UPLOAD_DIR', 'uploads'))
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    # ===== FILE UPLOAD OPERATIONS =====
    
    async def upload_attachment(
        self,
        user_id: UUID,
        expense_id: UUID,
        file: UploadFile,
        attachment_type: AttachmentType = AttachmentType.RECEIPT,
        description: Optional[str] = None
    ) -> AttachmentTable:
        """Upload and create a new attachment."""
        # Validate file
        await self._validate_upload_file(file)
        
        # Verify expense ownership
        await self._verify_expense_ownership(expense_id, user_id)
        
        # Generate unique filename
        file_extension = self._get_file_extension(file.filename)
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Create user-specific directory
        user_upload_dir = self.upload_dir / str(user_id)
        user_upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = user_upload_dir / unique_filename
        await self._save_uploaded_file(file, file_path)
        
        # Detect MIME type
        mime_type = self._detect_mime_type(file_path)
        
        # Get file size
        file_size = file_path.stat().st_size
        
        # Create attachment record
        attachment_data = {
            'user_id': user_id,
            'expense_id': expense_id,
            'filename': unique_filename,
            'original_filename': file.filename,
            'file_path': str(file_path),
            'file_size': file_size,
            'mime_type': mime_type,
            'attachment_type': attachment_type
        }
        
        try:
            attachment = self.repository.create_attachment(attachment_data)
            
            # Process image if it's an image file
            if mime_type in self.ALLOWED_IMAGE_TYPES:
                await self._process_image(file_path, attachment)
            
            return attachment
            
        except Exception as e:
            # Clean up file if database operation fails
            if file_path.exists():
                file_path.unlink()
            raise e
    
    async def upload_multiple_attachments(
        self,
        user_id: UUID,
        expense_id: UUID,
        files: List[UploadFile],
        attachment_type: AttachmentType = AttachmentType.RECEIPT
    ) -> List[AttachmentTable]:
        """Upload multiple attachments for an expense."""
        attachments = []
        
        for file in files:
            try:
                attachment = await self.upload_attachment(
                    user_id, expense_id, file, attachment_type
                )
                attachments.append(attachment)
            except Exception as e:
                # Log error but continue with other files
                print(f"Failed to upload {file.filename}: {e}")
                continue
        
        return attachments
    
    # ===== ATTACHMENT OPERATIONS =====
    
    async def get_attachment(
        self, 
        attachment_id: UUID, 
        user_id: UUID
    ) -> AttachmentTable:
        """Get an attachment by ID."""
        attachment = self.repository.get_attachment_by_id(attachment_id, user_id)
        if not attachment:
            raise NotFoundError(f"Attachment {attachment_id} not found")
        
        return attachment
    
    async def get_expense_attachments(
        self, 
        expense_id: UUID, 
        user_id: UUID
    ) -> List[AttachmentTable]:
        """Get all attachments for an expense."""
        # Verify expense ownership
        await self._verify_expense_ownership(expense_id, user_id)
        
        return self.repository.get_expense_attachments(expense_id, user_id)
    
    async def get_user_attachments(
        self, 
        user_id: UUID, 
        attachment_type: Optional[AttachmentType] = None,
        limit: Optional[int] = None
    ) -> List[AttachmentTable]:
        """Get all attachments for a user."""
        return self.repository.get_user_attachments(user_id, attachment_type, limit)
    
    async def update_attachment(
        self, 
        attachment_id: UUID, 
        user_id: UUID, 
        update_data: Dict[str, Any]
    ) -> AttachmentTable:
        """Update an attachment."""
        # Validate update data
        self._validate_attachment_update_data(update_data)
        
        attachment = self.repository.update_attachment(attachment_id, user_id, update_data)
        if not attachment:
            raise NotFoundError(f"Attachment {attachment_id} not found")
        
        return attachment
    
    async def delete_attachment(
        self, 
        attachment_id: UUID, 
        user_id: UUID
    ) -> bool:
        """Delete an attachment and its file."""
        attachment = await self.get_attachment(attachment_id, user_id)
        
        # Delete file from filesystem
        file_path = Path(attachment.file_path)
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                print(f"Failed to delete file {file_path}: {e}")
        
        # Delete database record
        success = self.repository.delete_attachment(attachment_id, user_id)
        if not success:
            raise NotFoundError(f"Attachment {attachment_id} not found")
        
        return success
    
    # ===== FILE OPERATIONS =====
    
    async def get_attachment_file_content(
        self, 
        attachment_id: UUID, 
        user_id: UUID
    ) -> bytes:
        """Get the file content for an attachment."""
        attachment = await self.get_attachment(attachment_id, user_id)
        
        file_path = Path(attachment.file_path)
        if not file_path.exists():
            raise NotFoundError(f"File not found: {attachment.filename}")
        
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            raise BusinessLogicError(f"Failed to read file: {e}")
    
    async def get_attachment_file_stream(
        self, 
        attachment_id: UUID, 
        user_id: UUID
    ) -> BinaryIO:
        """Get a file stream for an attachment."""
        attachment = await self.get_attachment(attachment_id, user_id)
        
        file_path = Path(attachment.file_path)
        if not file_path.exists():
            raise NotFoundError(f"File not found: {attachment.filename}")
        
        try:
            return open(file_path, 'rb')
        except Exception as e:
            raise BusinessLogicError(f"Failed to open file: {e}")
    
    async def create_thumbnail(
        self, 
        attachment_id: UUID, 
        user_id: UUID, 
        size: tuple = (200, 200)
    ) -> Optional[bytes]:
        """Create a thumbnail for an image attachment."""
        attachment = await self.get_attachment(attachment_id, user_id)
        
        if attachment.mime_type not in self.ALLOWED_IMAGE_TYPES:
            return None
        
        file_path = Path(attachment.file_path)
        if not file_path.exists():
            raise NotFoundError(f"File not found: {attachment.filename}")
        
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Create thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Save to bytes
                import io
                thumbnail_bytes = io.BytesIO()
                img.save(thumbnail_bytes, format='JPEG', quality=85)
                return thumbnail_bytes.getvalue()
                
        except Exception as e:
            raise BusinessLogicError(f"Failed to create thumbnail: {e}")
    
    # ===== SEARCH OPERATIONS =====
    
    async def search_attachments(
        self, 
        user_id: UUID, 
        search_term: str,
        limit: Optional[int] = None
    ) -> List[AttachmentTable]:
        """Search attachments by filename."""
        if not search_term or len(search_term.strip()) < 2:
            raise ValidationError("Search term must be at least 2 characters")
        
        return self.repository.search_attachments_by_filename(
            user_id, search_term.strip(), limit
        )
    
    async def search_expenses_with_attachments(
        self, 
        user_id: UUID, 
        search_term: str
    ) -> List[Dict[str, Any]]:
        """Search expenses that have attachments matching the search term."""
        attachments = await self.search_attachments(user_id, search_term)
        
        # Group by expense
        expense_attachments = {}
        for attachment in attachments:
            expense_id = str(attachment.expense_id)
            if expense_id not in expense_attachments:
                expense_attachments[expense_id] = {
                    'expense': attachment.expense,
                    'attachments': []
                }
            expense_attachments[expense_id]['attachments'].append(attachment)
        
        return list(expense_attachments.values())
    
    # ===== ANALYTICS AND REPORTING =====
    
    async def get_attachment_statistics(self, user_id: UUID) -> Dict[str, Any]:
        """Get attachment statistics for a user."""
        return self.repository.get_attachment_statistics(user_id)
    
    async def get_large_attachments(
        self, 
        user_id: UUID, 
        min_size_mb: float = 1.0,
        limit: Optional[int] = None
    ) -> List[AttachmentTable]:
        """Get large attachments above specified size."""
        return self.repository.get_large_attachments(user_id, min_size_mb, limit)
    
    async def cleanup_orphaned_attachments(self, user_id: UUID) -> int:
        """Clean up attachments whose expenses were deleted."""
        orphaned_attachments = self.repository.get_attachments_without_expenses(user_id)
        
        deleted_count = 0
        for attachment in orphaned_attachments:
            try:
                await self.delete_attachment(attachment.id, user_id)
                deleted_count += 1
            except Exception as e:
                print(f"Failed to delete orphaned attachment {attachment.id}: {e}")
        
        return deleted_count
    
    # ===== VALIDATION METHODS =====
    
    async def _validate_upload_file(self, file: UploadFile) -> None:
        """Validate uploaded file."""
        if not file.filename:
            raise ValidationError("Filename is required")
        
        # Check file size
        if hasattr(file, 'size') and file.size > self.MAX_FILE_SIZE:
            raise ValidationError(f"File size cannot exceed {self.MAX_FILE_SIZE / (1024*1024):.1f}MB")
        
        # Check file extension
        file_extension = self._get_file_extension(file.filename)
        if not file_extension:
            raise ValidationError("File must have an extension")
        
        # Read a small portion to check actual content
        content_start = await file.read(1024)
        await file.seek(0)  # Reset file pointer
        
        # Basic content validation
        if len(content_start) == 0:
            raise ValidationError("File appears to be empty")
    
    def _validate_attachment_update_data(self, update_data: Dict[str, Any]) -> None:
        """Validate attachment update data."""
        if 'attachment_type' in update_data:
            if update_data['attachment_type'] not in AttachmentType:
                raise ValidationError(f"Invalid attachment type: {update_data['attachment_type']}")
        
        if 'filename' in update_data:
            filename = update_data['filename']
            if not filename or len(filename.strip()) == 0:
                raise ValidationError("Filename cannot be empty")
            
            if len(filename) > 255:
                raise ValidationError("Filename cannot exceed 255 characters")
    
    async def _verify_expense_ownership(self, expense_id: UUID, user_id: UUID) -> None:
        """Verify that the expense belongs to the user."""
        from ..models.expense import ExpenseTable
        
        expense = self.db.query(ExpenseTable).filter(
            ExpenseTable.id == expense_id,
            ExpenseTable.user_id == user_id
        ).first()
        
        if not expense:
            raise NotFoundError(f"Expense {expense_id} not found")
    
    # ===== FILE HANDLING HELPERS =====
    
    def _get_file_extension(self, filename: str) -> str:
        """Get file extension from filename."""
        if not filename:
            return ""
        
        return Path(filename).suffix.lower()
    
    def _detect_mime_type(self, file_path: Path) -> str:
        """Detect MIME type of a file."""
        try:
            # Try using python-magic for accurate detection
            mime_type = magic.from_file(str(file_path), mime=True)
            if mime_type in self.ALLOWED_MIME_TYPES:
                return mime_type
        except:
            pass
        
        # Fallback to mimetypes module
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type and mime_type in self.ALLOWED_MIME_TYPES:
            return mime_type
        
        # Default fallback
        return 'application/octet-stream'
    
    async def _save_uploaded_file(self, file: UploadFile, file_path: Path) -> None:
        """Save uploaded file to disk."""
        try:
            with open(file_path, 'wb') as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise BusinessLogicError(f"Failed to save file: {e}")
    
    async def _process_image(self, file_path: Path, attachment: AttachmentTable) -> None:
        """Process uploaded image (extract metadata, create thumbnails, etc.)."""
        try:
            with Image.open(file_path) as img:
                # Extract basic image info
                width, height = img.size
                format_name = img.format
                
                # You could store this metadata in the database if needed
                # For now, we'll just validate the image is readable
                
        except Exception as e:
            # If image processing fails, log but don't fail the upload
            print(f"Image processing failed for {file_path}: {e}")
    
    # ===== BULK OPERATIONS =====
    
    async def bulk_delete_attachments(
        self, 
        attachment_ids: List[UUID], 
        user_id: UUID
    ) -> Dict[str, int]:
        """Bulk delete multiple attachments."""
        if not attachment_ids:
            return {'deleted': 0, 'failed': 0}
        
        deleted_count = 0
        failed_count = 0
        
        for attachment_id in attachment_ids:
            try:
                await self.delete_attachment(attachment_id, user_id)
                deleted_count += 1
            except Exception as e:
                print(f"Failed to delete attachment {attachment_id}: {e}")
                failed_count += 1
        
        return {'deleted': deleted_count, 'failed': failed_count}
    
    async def bulk_update_attachment_type(
        self, 
        attachment_ids: List[UUID], 
        user_id: UUID, 
        new_type: AttachmentType
    ) -> Dict[str, int]:
        """Bulk update attachment type for multiple attachments."""
        if not attachment_ids:
            return {'updated': 0, 'failed': 0}
        
        updated_count = 0
        failed_count = 0
        
        for attachment_id in attachment_ids:
            try:
                await self.update_attachment(
                    attachment_id, user_id, {'attachment_type': new_type}
                )
                updated_count += 1
            except Exception as e:
                print(f"Failed to update attachment {attachment_id}: {e}")
                failed_count += 1
        
        return {'updated': updated_count, 'failed': failed_count}