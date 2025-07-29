from datetime import date, datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import io

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models.user import User
from ..services.export_service import ExportService
from ..core.exceptions import ValidationError, BusinessLogicError

router = APIRouter(prefix="/export", tags=["export"])


# ===== PYDANTIC MODELS =====

class ExportRequest(BaseModel):
    date_from: Optional[date] = Field(None, description="Start date for export")
    date_to: Optional[date] = Field(None, description="End date for export")
    category_ids: Optional[List[UUID]] = Field(None, description="Filter by category IDs")
    merchant_ids: Optional[List[UUID]] = Field(None, description="Filter by merchant IDs")
    include_attachments: bool = Field(False, description="Include attachment information")
    include_notes: bool = Field(True, description="Include notes in export")
    custom_fields: Optional[List[str]] = Field(None, description="Additional custom fields")


class PDFExportRequest(ExportRequest):
    report_title: str = Field("Expense Report", description="Title for the report")
    include_summary: bool = Field(True, description="Include summary section")
    include_charts: bool = Field(True, description="Include charts and visualizations")
    group_by_category: bool = Field(False, description="Group expenses by category")


class TaxExportRequest(BaseModel):
    tax_year: int = Field(..., ge=2000, le=2030, description="Tax year for export")
    tax_categories: Optional[Dict[str, List[str]]] = Field(
        None, 
        description="Custom tax category mappings"
    )
    format_type: str = Field(
        "pdf", 
        regex="^(csv|excel|pdf)$", 
        description="Export format"
    )


class ExportMetadata(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    generated_at: datetime
    expense_count: int
    date_range: Dict[str, Optional[str]]


# ===== CSV EXPORT ENDPOINTS =====

@router.post("/csv")
async def export_expenses_csv(
    export_request: ExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export expenses to CSV format."""
    try:
        service = ExportService(db)
        csv_data = await service.export_expenses_csv(
            user_id=current_user.id,
            date_from=export_request.date_from,
            date_to=export_request.date_to,
            category_ids=export_request.category_ids,
            merchant_ids=export_request.merchant_ids,
            include_attachments=export_request.include_attachments,
            include_notes=export_request.include_notes,
            custom_fields=export_request.custom_fields
        )
        
        # Generate filename
        date_suffix = ""
        if export_request.date_from or export_request.date_to:
            date_from_str = export_request.date_from.strftime("%Y%m%d") if export_request.date_from else "start"
            date_to_str = export_request.date_to.strftime("%Y%m%d") if export_request.date_to else "end"
            date_suffix = f"_{date_from_str}_to_{date_to_str}"
        
        filename = f"expenses{date_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            io.BytesIO(csv_data),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/csv/quick")
async def export_expenses_csv_quick(
    date_from: Optional[date] = Query(None, description="Start date"),
    date_to: Optional[date] = Query(None, description="End date"),
    category_ids: Optional[str] = Query(None, description="Comma-separated category IDs"),
    merchant_ids: Optional[str] = Query(None, description="Comma-separated merchant IDs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Quick CSV export with query parameters."""
    try:
        # Parse comma-separated IDs
        category_id_list = None
        if category_ids:
            category_id_list = [UUID(id.strip()) for id in category_ids.split(',')]
        
        merchant_id_list = None
        if merchant_ids:
            merchant_id_list = [UUID(id.strip()) for id in merchant_ids.split(',')]
        
        service = ExportService(db)
        csv_data = await service.export_expenses_csv(
            user_id=current_user.id,
            date_from=date_from,
            date_to=date_to,
            category_ids=category_id_list,
            merchant_ids=merchant_id_list,
            include_notes=True
        )
        
        filename = f"expenses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            io.BytesIO(csv_data),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== EXCEL EXPORT ENDPOINTS =====

@router.post("/excel")
async def export_expenses_excel(
    export_request: ExportRequest,
    include_summary: bool = Query(True, description="Include summary worksheet"),
    include_charts: bool = Query(True, description="Include charts worksheet"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export expenses to Excel format with multiple worksheets."""
    try:
        service = ExportService(db)
        excel_data = await service.export_expenses_excel(
            user_id=current_user.id,
            date_from=export_request.date_from,
            date_to=export_request.date_to,
            category_ids=export_request.category_ids,
            merchant_ids=export_request.merchant_ids,
            include_summary=include_summary,
            include_charts=include_charts
        )
        
        # Generate filename
        date_suffix = ""
        if export_request.date_from or export_request.date_to:
            date_from_str = export_request.date_from.strftime("%Y%m%d") if export_request.date_from else "start"
            date_to_str = export_request.date_to.strftime("%Y%m%d") if export_request.date_to else "end"
            date_suffix = f"_{date_from_str}_to_{date_to_str}"
        
        filename = f"expenses{date_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(excel_data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== PDF EXPORT ENDPOINTS =====

@router.post("/pdf")
async def export_expenses_pdf(
    export_request: PDFExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export expenses to PDF format with formatting and charts."""
    try:
        service = ExportService(db)
        pdf_data = await service.export_expenses_pdf(
            user_id=current_user.id,
            date_from=export_request.date_from,
            date_to=export_request.date_to,
            category_ids=export_request.category_ids,
            merchant_ids=export_request.merchant_ids,
            report_title=export_request.report_title,
            include_summary=export_request.include_summary,
            include_charts=export_request.include_charts,
            group_by_category=export_request.group_by_category
        )
        
        # Generate filename
        date_suffix = ""
        if export_request.date_from or export_request.date_to:
            date_from_str = export_request.date_from.strftime("%Y%m%d") if export_request.date_from else "start"
            date_to_str = export_request.date_to.strftime("%Y%m%d") if export_request.date_to else "end"
            date_suffix = f"_{date_from_str}_to_{date_to_str}"
        
        filename = f"expense_report{date_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return StreamingResponse(
            io.BytesIO(pdf_data),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== JSON EXPORT ENDPOINTS =====

@router.post("/json")
async def export_expenses_json(
    export_request: ExportRequest,
    include_metadata: bool = Query(True, description="Include export metadata"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export expenses to JSON format."""
    try:
        service = ExportService(db)
        json_data = await service.export_expenses_json(
            user_id=current_user.id,
            date_from=export_request.date_from,
            date_to=export_request.date_to,
            category_ids=export_request.category_ids,
            merchant_ids=export_request.merchant_ids,
            include_metadata=include_metadata
        )
        
        # Generate filename
        date_suffix = ""
        if export_request.date_from or export_request.date_to:
            date_from_str = export_request.date_from.strftime("%Y%m%d") if export_request.date_from else "start"
            date_to_str = export_request.date_to.strftime("%Y%m%d") if export_request.date_to else "end"
            date_suffix = f"_{date_from_str}_to_{date_to_str}"
        
        filename = f"expenses{date_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        return StreamingResponse(
            io.BytesIO(json_data),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== TAX EXPORT ENDPOINTS =====

@router.post("/tax")
async def export_tax_report(
    tax_request: TaxExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export tax-focused report with category groupings."""
    try:
        service = ExportService(db)
        report_data = await service.export_tax_report(
            user_id=current_user.id,
            tax_year=tax_request.tax_year,
            tax_categories=tax_request.tax_categories,
            format_type=tax_request.format_type
        )
        
        # Determine content type and filename
        if tax_request.format_type.lower() == "csv":
            content_type = "text/csv"
            extension = "csv"
        elif tax_request.format_type.lower() == "excel":
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            extension = "xlsx"
        else:  # PDF
            content_type = "application/pdf"
            extension = "pdf"
        
        filename = f"tax_report_{tax_request.tax_year}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{extension}"
        
        return StreamingResponse(
            io.BytesIO(report_data),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/tax/{tax_year}")
async def export_tax_report_quick(
    tax_year: int,
    format_type: str = Query("pdf", regex="^(csv|excel|pdf)$", description="Export format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Quick tax report export with path parameters."""
    try:
        service = ExportService(db)
        report_data = await service.export_tax_report(
            user_id=current_user.id,
            tax_year=tax_year,
            format_type=format_type
        )
        
        # Determine content type and filename
        if format_type.lower() == "csv":
            content_type = "text/csv"
            extension = "csv"
        elif format_type.lower() == "excel":
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            extension = "xlsx"
        else:  # PDF
            content_type = "application/pdf"
            extension = "pdf"
        
        filename = f"tax_report_{tax_year}.{extension}"
        
        return StreamingResponse(
            io.BytesIO(report_data),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== EXPORT METADATA ENDPOINTS =====

@router.post("/metadata")
async def get_export_metadata(
    export_request: ExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get metadata about what would be exported without generating the file."""
    try:
        service = ExportService(db)
        
        # Get filtered expenses to calculate metadata
        expenses = await service._get_filtered_expenses(
            user_id=current_user.id,
            date_from=export_request.date_from,
            date_to=export_request.date_to,
            category_ids=export_request.category_ids,
            merchant_ids=export_request.merchant_ids
        )
        
        # Calculate estimated file sizes (rough estimates)
        estimated_csv_size = len(expenses) * 150  # ~150 bytes per row
        estimated_excel_size = len(expenses) * 200  # ~200 bytes per row
        estimated_pdf_size = len(expenses) * 100 + 5000  # ~100 bytes per row + overhead
        
        metadata = {
            "expense_count": len(expenses),
            "date_range": {
                "from": export_request.date_from.isoformat() if export_request.date_from else None,
                "to": export_request.date_to.isoformat() if export_request.date_to else None
            },
            "filters_applied": {
                "categories": len(export_request.category_ids) if export_request.category_ids else 0,
                "merchants": len(export_request.merchant_ids) if export_request.merchant_ids else 0
            },
            "estimated_file_sizes": {
                "csv_bytes": estimated_csv_size,
                "excel_bytes": estimated_excel_size,
                "pdf_bytes": estimated_pdf_size
            },
            "available_formats": ["csv", "excel", "pdf", "json"],
            "generated_at": datetime.now().isoformat()
        }
        
        return metadata
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== TEMPLATE ENDPOINTS =====

@router.get("/templates/tax-categories")
async def get_tax_category_templates():
    """Get predefined tax category templates."""
    templates = {
        "business_standard": {
            "Business Meals": ["Food & Dining", "Restaurants", "Catering"],
            "Travel & Transportation": ["Travel", "Transportation", "Hotels", "Airfare", "Car Rental"],
            "Office Supplies": ["Office Supplies", "Equipment", "Software", "Subscriptions"],
            "Professional Services": ["Professional Services", "Legal", "Accounting", "Consulting"],
            "Marketing & Advertising": ["Marketing", "Advertising", "Promotional"],
            "Utilities": ["Utilities", "Internet", "Phone"],
            "Other Business": ["Business", "Professional", "Miscellaneous"]
        },
        "personal_standard": {
            "Medical & Health": ["Medical", "Health", "Pharmacy", "Insurance"],
            "Charitable Donations": ["Charity", "Donations", "Non-profit"],
            "Education": ["Education", "Books", "Training", "Courses"],
            "Home Office": ["Office Supplies", "Equipment", "Utilities"],
            "Other Deductible": ["Tax Deductible", "Professional"]
        },
        "freelancer": {
            "Business Equipment": ["Equipment", "Software", "Hardware", "Tools"],
            "Professional Development": ["Education", "Training", "Conferences", "Books"],
            "Business Travel": ["Travel", "Transportation", "Hotels"],
            "Marketing & Networking": ["Marketing", "Networking", "Advertising"],
            "Professional Services": ["Legal", "Accounting", "Professional Services"],
            "Office Expenses": ["Office Supplies", "Utilities", "Rent"]
        }
    }
    
    return {
        "templates": templates,
        "description": "Predefined tax category mappings for different user types"
    }


@router.get("/formats")
async def get_supported_formats():
    """Get information about supported export formats."""
    formats = {
        "csv": {
            "name": "CSV (Comma Separated Values)",
            "description": "Simple spreadsheet format compatible with Excel and other tools",
            "mime_type": "text/csv",
            "features": ["Basic data export", "Custom fields", "Attachment info", "Notes"],
            "best_for": ["Data analysis", "Import into other systems", "Simple reporting"]
        },
        "excel": {
            "name": "Excel Workbook",
            "description": "Microsoft Excel format with multiple worksheets",
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "features": ["Multiple worksheets", "Summary data", "Formatting", "Charts"],
            "best_for": ["Detailed analysis", "Professional reports", "Data manipulation"]
        },
        "pdf": {
            "name": "PDF Report",
            "description": "Formatted report with charts and summaries",
            "mime_type": "application/pdf",
            "features": ["Professional formatting", "Charts", "Summaries", "Category grouping"],
            "best_for": ["Presentations", "Archival", "Sharing", "Tax documentation"]
        },
        "json": {
            "name": "JSON Data",
            "description": "Structured data format for developers",
            "mime_type": "application/json",
            "features": ["Complete data structure", "Metadata", "Relationships", "API integration"],
            "best_for": ["API integration", "Data backup", "Custom processing"]
        }
    }
    
    return {
        "supported_formats": formats,
        "default_format": "pdf",
        "recommendations": {
            "tax_preparation": "pdf",
            "data_analysis": "excel",
            "system_integration": "json",
            "simple_export": "csv"
        }
    }