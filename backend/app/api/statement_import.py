"""
Statement import API endpoints.
"""
import logging
import os
import tempfile
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..core.auth import get_current_user
from ..core.security import rate_limit
from ..models.user import User
from ..parsers.registry import initialize_parsers, parser_registry
from ..services.statement_import_service import StatementImportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/statement-import", tags=["statement-import"])

# Initialize parsers on module load
initialize_parsers()


class FileUploadResponse(BaseModel):
    """Response for file upload."""
    upload_id: str
    filename: str
    file_size: int
    file_type: str
    supported_format: bool
    detected_parser: Optional[str] = None
    validation_errors: List[str] = []


class ParsePreviewResponse(BaseModel):
    """Response for parse preview."""
    upload_id: str
    success: bool
    transaction_count: int
    sample_transactions: List[dict]
    errors: List[str] = []
    warnings: List[str] = []
    metadata: dict = {}


class ImportConfirmRequest(BaseModel):
    """Request to confirm import."""
    upload_id: str
    selected_transactions: Optional[List[int]] = None  # Indices of transactions to import
    category_mappings: Optional[dict] = None  # Custom category mappings
    merchant_mappings: Optional[dict] = None  # Custom merchant mappings


class ImportConfirmResponse(BaseModel):
    """Response for import confirmation."""
    import_id: str
    success: bool
    imported_count: int
    skipped_count: int
    duplicate_count: int
    errors: List[str] = []


@router.post("/upload", response_model=FileUploadResponse)
@rate_limit("file_upload", per_minute=10)
async def upload_statement_file(
    file: UploadFile = File(...),
    bank_hint: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a statement file for processing.
    
    Args:
        file: The uploaded statement file
        bank_hint: Optional hint about which bank this statement is from
        current_user: Current authenticated user
        
    Returns:
        FileUploadResponse with upload details and validation results
    """
    logger.info(f"File upload started by user {current_user.id}: {file.filename}")
    
    try:
        # Validate file
        validation_errors = []
        
        # Check file size (max 50MB)
        if file.size and file.size > 50 * 1024 * 1024:
            validation_errors.append("File size exceeds 50MB limit")
        
        # Check filename
        if not file.filename:
            validation_errors.append("Filename is required")
            
        # Get file extension
        file_extension = os.path.splitext(file.filename or "")[1].lower()
        
        # Check if format is supported
        supported_extensions = parser_registry.get_supported_extensions()
        supported_format = file_extension in supported_extensions
        
        if not supported_format:
            validation_errors.append(
                f"Unsupported file format: {file_extension}. "
                f"Supported formats: {', '.join(supported_extensions)}"
            )
        
        # Create temporary file for processing
        temp_file = None
        detected_parser = None
        
        if not validation_errors:
            # Save uploaded file to temporary location
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=file_extension,
                prefix=f"statement_{current_user.id}_"
            )
            
            # Read and save file content
            content = await file.read()
            temp_file.write(content)
            temp_file.close()
            
            # Detect appropriate parser
            parser = parser_registry.find_parser(temp_file.name)
            if parser:
                detected_parser = parser.config.name
            else:
                validation_errors.append("No suitable parser found for this file format")
        
        # Create upload record
        service = StatementImportService()
        upload_id = await service.create_upload_record(
            user_id=current_user.id,
            filename=file.filename or "unknown",
            file_size=file.size or 0,
            file_path=temp_file.name if temp_file else None,
            detected_parser=detected_parser,
            bank_hint=bank_hint,
            validation_errors=validation_errors
        )
        
        response = FileUploadResponse(
            upload_id=upload_id,
            filename=file.filename or "unknown",
            file_size=file.size or 0,
            file_type=file_extension,
            supported_format=supported_format,
            detected_parser=detected_parser,
            validation_errors=validation_errors
        )
        
        logger.info(f"File upload completed: {upload_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error during file upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )


@router.post("/preview/{upload_id}", response_model=ParsePreviewResponse)
@rate_limit("parse_preview", per_minute=20)
async def preview_statement_parsing(
    upload_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Preview the parsing results for an uploaded statement.
    
    Args:
        upload_id: ID of the uploaded file
        current_user: Current authenticated user
        
    Returns:
        ParsePreviewResponse with preview of parsed transactions
    """
    logger.info(f"Parse preview requested by user {current_user.id}: {upload_id}")
    
    try:
        service = StatementImportService()
        
        # Get upload record
        upload_record = await service.get_upload_record(upload_id, current_user.id)
        if not upload_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload record not found"
            )
        
        # Check if file has validation errors
        if upload_record.validation_errors:
            return ParsePreviewResponse(
                upload_id=upload_id,
                success=False,
                transaction_count=0,
                sample_transactions=[],
                errors=upload_record.validation_errors
            )
        
        # Parse the file
        parse_result = await service.parse_statement_file(upload_record)
        
        # Get sample transactions (first 10)
        sample_transactions = []
        for i, transaction in enumerate(parse_result.transactions[:10]):
            sample_transactions.append({
                "index": i,
                "date": transaction.date.isoformat(),
                "description": transaction.description,
                "amount": float(transaction.amount),
                "merchant": transaction.merchant,
                "category": transaction.category,
                "account": transaction.account,
                "reference": transaction.reference
            })
        
        response = ParsePreviewResponse(
            upload_id=upload_id,
            success=parse_result.success,
            transaction_count=len(parse_result.transactions),
            sample_transactions=sample_transactions,
            errors=parse_result.errors,
            warnings=parse_result.warnings,
            metadata=parse_result.metadata
        )
        
        # Store parse result for later import
        await service.store_parse_result(upload_id, parse_result)
        
        logger.info(f"Parse preview completed: {upload_id}, {len(parse_result.transactions)} transactions")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during parse preview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Parse preview failed: {str(e)}"
        )


@router.post("/confirm/{upload_id}", response_model=ImportConfirmResponse)
@rate_limit("import_confirm", per_minute=10)
async def confirm_statement_import(
    upload_id: str,
    request: ImportConfirmRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Confirm and execute the statement import.
    
    Args:
        upload_id: ID of the uploaded file
        request: Import confirmation request with selections and mappings
        current_user: Current authenticated user
        
    Returns:
        ImportConfirmResponse with import results
    """
    logger.info(f"Import confirmation by user {current_user.id}: {upload_id}")
    
    try:
        service = StatementImportService()
        
        # Execute the import
        import_result = await service.execute_import(
            upload_id=upload_id,
            user_id=current_user.id,
            selected_transactions=request.selected_transactions,
            category_mappings=request.category_mappings or {},
            merchant_mappings=request.merchant_mappings or {}
        )
        
        response = ImportConfirmResponse(
            import_id=import_result.import_id,
            success=import_result.success,
            imported_count=import_result.imported_count,
            skipped_count=import_result.skipped_count,
            duplicate_count=import_result.duplicate_count,
            errors=import_result.errors
        )
        
        logger.info(
            f"Import completed: {upload_id}, "
            f"imported: {import_result.imported_count}, "
            f"skipped: {import_result.skipped_count}, "
            f"duplicates: {import_result.duplicate_count}"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during import confirmation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import confirmation failed: {str(e)}"
        )


@router.get("/history")
@rate_limit("import_history", per_minute=30)
async def get_import_history(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """
    Get import history for the current user.
    
    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip
        current_user: Current authenticated user
        
    Returns:
        List of import history records
    """
    try:
        service = StatementImportService()
        history = await service.get_import_history(
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )
        
        return {"imports": history, "total": len(history)}
        
    except Exception as e:
        logger.error(f"Error getting import history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get import history: {str(e)}"
        )


@router.post("/rollback/{rollback_token}")
@rate_limit("rollback_import", per_minute=5)
async def rollback_import(
    rollback_token: str,
    current_user: User = Depends(get_current_user)
):
    """
    Rollback a completed import using the rollback token.
    
    Args:
        rollback_token: Token from the import result
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    try:
        service = StatementImportService()
        success = await service.rollback_import(rollback_token, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rollback token not found or rollback failed"
            )
        
        return {"message": "Import rolled back successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during rollback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rollback failed: {str(e)}"
        )


@router.post("/analyze-duplicates/{upload_id}")
@rate_limit("analyze_duplicates", per_minute=10)
async def analyze_duplicates(
    upload_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Analyze parsed transactions for potential duplicates.
    
    Args:
        upload_id: ID of the uploaded file
        current_user: Current authenticated user
        
    Returns:
        Analysis of potential duplicate transactions
    """
    try:
        service = StatementImportService()
        
        # Get upload record and parse result
        upload_record = await service.get_upload_record(upload_id, current_user.id)
        if not upload_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload record not found"
            )
        
        parse_result = service._parse_results.get(upload_id)
        if not parse_result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parse result not found. Please preview the file first."
            )
        
        # Analyze for duplicates
        matches = await service.analyze_transaction_matches(
            parse_result.transactions, current_user.id
        )
        
        # Format response
        analysis = []
        for i, match in enumerate(matches):
            analysis.append({
                "transaction_index": i,
                "transaction": {
                    "date": match.transaction.date.isoformat(),
                    "description": match.transaction.description,
                    "amount": float(match.transaction.amount),
                    "merchant": match.transaction.merchant
                },
                "is_likely_duplicate": match.is_likely_duplicate,
                "confidence_score": match.confidence_score,
                "potential_duplicates": [
                    {
                        "expense_id": dup.existing_expense_id,
                        "match_score": dup.match_score,
                        "match_reasons": dup.match_reasons
                    }
                    for dup in match.duplicates
                ]
            })
        
        return {
            "upload_id": upload_id,
            "total_transactions": len(matches),
            "likely_duplicates": sum(1 for m in matches if m.is_likely_duplicate),
            "analysis": analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing duplicates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Duplicate analysis failed: {str(e)}"
        )


@router.delete("/upload/{upload_id}")
@rate_limit("delete_upload", per_minute=20)
async def delete_upload(
    upload_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete an uploaded file and its associated data.
    
    Args:
        upload_id: ID of the upload to delete
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    try:
        service = StatementImportService()
        success = await service.delete_upload(upload_id, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload not found"
            )
        
        return {"message": "Upload deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete upload: {str(e)}"
        )