import io
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models.user import User
from ..models.attachment import AttachmentType
from ..services.attachment_service import AttachmentService
from ..core.exceptions import ValidationError, NotFoundError, BusinessLogicError

router = APIRouter(prefix="/attachments", tags=["attachments"])


# ===== PYDANTIC MODELS =====

from pydantic import BaseModel, Field
from datetime import datetime


class AttachmentResponse(BaseModel):
    id: UUID
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    attachment_type: AttachmentType
    expense_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AttachmentUpdate(BaseModel):
    attachment_type: Optional[AttachmentType] = Field(None, description="Attachment type")
    filename: Optional[str] = Field(None, max_length=255, description="Display filename")


class AttachmentStatisticsResponse(BaseModel):
    total_attachments: int
    type_breakdown: Dict[str, int]
    total_size_bytes: int
    total_size_mb: float
    average_size_bytes: int
    average_size_kb: float
    common_file_types: List[Dict[str, Any]]
    expenses_with_attachments: int
    recent_attachments_30_days: int


class BulkOperationResponse(BaseModel):
    success: bool
    message: str
    details: Dict[str, int]


# ===== UPLOAD ENDPOINTS =====

@router.post("/upload", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    expense_id: UUID = Form(..., description="Expense ID to attach file to"),
    attachment_type: AttachmentType = Form(AttachmentType.RECEIPT, description="Type of attachment"),
    file: UploadFile = File(..., description="File to upload"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a single attachment for an expense."""
    try:
        service = AttachmentService(db)
        attachment = await service.upload_attachment(
            current_user.id, expense_id, file, attachment_type
        )
        return AttachmentResponse.from_orm(attachment)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/upload-multiple", response_model=List[AttachmentResponse], status_code=status.HTTP_201_CREATED)
async def upload_multiple_attachments(
    expense_id: UUID = Form(..., description="Expense ID to attach files to"),
    attachment_type: AttachmentType = Form(AttachmentType.RECEIPT, description="Type of attachments"),
    files: List[UploadFile] = File(..., description="Files to upload"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload multiple attachments for an expense."""
    try:
        service = AttachmentService(db)
        attachments = await service.upload_multiple_attachments(
            current_user.id, expense_id, files, attachment_type
        )
        return [AttachmentResponse.from_orm(attachment) for attachment in attachments]
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== ATTACHMENT MANAGEMENT ENDPOINTS =====

@router.get("/", response_model=List[AttachmentResponse])
async def get_user_attachments(
    attachment_type: Optional[AttachmentType] = Query(None, description="Filter by attachment type"),
    limit: Optional[int] = Query(50, ge=1, le=200, description="Maximum number of attachments to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all attachments for the current user."""
    try:
        service = AttachmentService(db)
        attachments = await service.get_user_attachments(current_user.id, attachment_type, limit)
        return [AttachmentResponse.from_orm(attachment) for attachment in attachments]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{attachment_id}", response_model=AttachmentResponse)
async def get_attachment(
    attachment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific attachment."""
    try:
        service = AttachmentService(db)
        attachment = await service.get_attachment(attachment_id, current_user.id)
        return AttachmentResponse.from_orm(attachment)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/expense/{expense_id}", response_model=List[AttachmentResponse])
async def get_expense_attachments(
    expense_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all attachments for a specific expense."""
    try:
        service = AttachmentService(db)
        attachments = await service.get_expense_attachments(expense_id, current_user.id)
        return [AttachmentResponse.from_orm(attachment) for attachment in attachments]
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{attachment_id}", response_model=AttachmentResponse)
async def update_attachment(
    attachment_id: UUID,
    update_data: AttachmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an attachment."""
    try:
        service = AttachmentService(db)
        attachment = await service.update_attachment(
            attachment_id, current_user.id, update_data.dict(exclude_unset=True)
        )
        return AttachmentResponse.from_orm(attachment)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    attachment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an attachment."""
    try:
        service = AttachmentService(db)
        await service.delete_attachment(attachment_id, current_user.id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== FILE DOWNLOAD ENDPOINTS =====

@router.get("/{attachment_id}/download")
async def download_attachment(
    attachment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download an attachment file."""
    try:
        service = AttachmentService(db)
        attachment = await service.get_attachment(attachment_id, current_user.id)
        file_stream = await service.get_attachment_file_stream(attachment_id, current_user.id)
        
        return StreamingResponse(
            io.BytesIO(file_stream.read()),
            media_type=attachment.mime_type,
            headers={
                "Content-Disposition": f"attachment; filename=\"{attachment.original_filename}\""
            }
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{attachment_id}/view")
async def view_attachment(
    attachment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """View an attachment file inline."""
    try:
        service = AttachmentService(db)
        attachment = await service.get_attachment(attachment_id, current_user.id)
        file_content = await service.get_attachment_file_content(attachment_id, current_user.id)
        
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=attachment.mime_type,
            headers={
                "Content-Disposition": f"inline; filename=\"{attachment.original_filename}\""
            }
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{attachment_id}/thumbnail")
async def get_attachment_thumbnail(
    attachment_id: UUID,
    size: int = Query(200, ge=50, le=500, description="Thumbnail size (square)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a thumbnail for an image attachment."""
    try:
        service = AttachmentService(db)
        thumbnail_data = await service.create_thumbnail(
            attachment_id, current_user.id, (size, size)
        )
        
        if thumbnail_data is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Thumbnail not available for this file type"
            )
        
        return StreamingResponse(
            io.BytesIO(thumbnail_data),
            media_type="image/jpeg",
            headers={
                "Content-Disposition": f"inline; filename=\"thumbnail_{size}x{size}.jpg\""
            }
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== SEARCH ENDPOINTS =====

@router.get("/search/", response_model=List[AttachmentResponse])
async def search_attachments(
    q: str = Query(..., min_length=2, description="Search term"),
    limit: Optional[int] = Query(50, ge=1, le=200, description="Maximum number of results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search attachments by filename."""
    try:
        service = AttachmentService(db)
        attachments = await service.search_attachments(current_user.id, q, limit)
        return [AttachmentResponse.from_orm(attachment) for attachment in attachments]
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/search/expenses", response_model=List[Dict[str, Any]])
async def search_expenses_with_attachments(
    q: str = Query(..., min_length=2, description="Search term"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search expenses that have attachments matching the search term."""
    try:
        service = AttachmentService(db)
        results = await service.search_expenses_with_attachments(current_user.id, q)
        
        # Format response
        formatted_results = []
        for result in results:
            expense = result['expense']
            attachments = result['attachments']
            
            formatted_results.append({
                'expense': {
                    'id': str(expense.id),
                    'amount': expense.amount,
                    'description': expense.description,
                    'expense_date': expense.expense_date.isoformat(),
                    'category': expense.category.name if expense.category else None,
                    'merchant': expense.merchant.name if expense.merchant else None
                },
                'attachments': [
                    {
                        'id': str(attachment.id),
                        'filename': attachment.filename,
                        'original_filename': attachment.original_filename,
                        'attachment_type': attachment.attachment_type,
                        'file_size': attachment.file_size,
                        'mime_type': attachment.mime_type
                    }
                    for attachment in attachments
                ]
            })
        
        return formatted_results
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== ANALYTICS ENDPOINTS =====

@router.get("/analytics/statistics", response_model=AttachmentStatisticsResponse)
async def get_attachment_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get attachment statistics for the current user."""
    try:
        service = AttachmentService(db)
        statistics = await service.get_attachment_statistics(current_user.id)
        return AttachmentStatisticsResponse(**statistics)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/analytics/large-files", response_model=List[AttachmentResponse])
async def get_large_attachments(
    min_size_mb: float = Query(1.0, ge=0.1, le=100.0, description="Minimum file size in MB"),
    limit: Optional[int] = Query(50, ge=1, le=200, description="Maximum number of results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get large attachments above specified size."""
    try:
        service = AttachmentService(db)
        attachments = await service.get_large_attachments(current_user.id, min_size_mb, limit)
        return [AttachmentResponse.from_orm(attachment) for attachment in attachments]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== BULK OPERATIONS ENDPOINTS =====

@router.post("/bulk/delete", response_model=BulkOperationResponse)
async def bulk_delete_attachments(
    attachment_ids: List[UUID],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk delete multiple attachments."""
    try:
        service = AttachmentService(db)
        results = await service.bulk_delete_attachments(attachment_ids, current_user.id)
        
        return BulkOperationResponse(
            success=results['failed'] == 0,
            message=f"Deleted {results['deleted']} attachments, {results['failed']} failed",
            details=results
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/bulk/update-type", response_model=BulkOperationResponse)
async def bulk_update_attachment_type(
    attachment_ids: List[UUID],
    new_type: AttachmentType,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk update attachment type for multiple attachments."""
    try:
        service = AttachmentService(db)
        results = await service.bulk_update_attachment_type(attachment_ids, current_user.id, new_type)
        
        return BulkOperationResponse(
            success=results['failed'] == 0,
            message=f"Updated {results['updated']} attachments, {results['failed']} failed",
            details=results
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== MAINTENANCE ENDPOINTS =====

@router.post("/maintenance/cleanup-orphaned", response_model=Dict[str, int])
async def cleanup_orphaned_attachments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clean up attachments whose expenses were deleted."""
    try:
        service = AttachmentService(db)
        deleted_count = await service.cleanup_orphaned_attachments(current_user.id)
        
        return {
            "deleted_count": deleted_count,
            "message": f"Cleaned up {deleted_count} orphaned attachments"
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))