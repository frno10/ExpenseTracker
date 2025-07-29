from datetime import date
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models.user import User
from ..services.expense_search_service import ExpenseSearchService
from ..core.exceptions import ValidationError

router = APIRouter(prefix="/expenses/search", tags=["expense-search"])


# ===== PYDANTIC MODELS =====

class ExpenseSearchRequest(BaseModel):
    search_term: str = Field(..., min_length=2, description="Text to search for")
    search_fields: Optional[List[str]] = Field(
        None, 
        description="Fields to search in: description, notes, attachments"
    )
    category_ids: Optional[List[UUID]] = Field(None, description="Filter by category IDs")
    merchant_ids: Optional[List[UUID]] = Field(None, description="Filter by merchant IDs")
    payment_method_ids: Optional[List[UUID]] = Field(None, description="Filter by payment method IDs")
    account_ids: Optional[List[UUID]] = Field(None, description="Filter by account IDs")
    date_from: Optional[date] = Field(None, description="Start date filter")
    date_to: Optional[date] = Field(None, description="End date filter")
    amount_min: Optional[Decimal] = Field(None, description="Minimum amount filter")
    amount_max: Optional[Decimal] = Field(None, description="Maximum amount filter")
    has_attachments: Optional[bool] = Field(None, description="Filter by presence of attachments")
    attachment_types: Optional[List[str]] = Field(None, description="Filter by attachment types")
    limit: Optional[int] = Field(50, ge=1, le=200, description="Maximum number of results")
    offset: Optional[int] = Field(0, ge=0, description="Number of results to skip")
    sort_by: str = Field("expense_date", description="Field to sort by")
    sort_order: str = Field("desc", regex="^(asc|desc)$", description="Sort order")


class ExpenseSearchResponse(BaseModel):
    id: UUID
    amount: Decimal
    description: Optional[str]
    notes: Optional[str]
    expense_date: date
    category_name: Optional[str]
    merchant_name: Optional[str]
    payment_method_name: Optional[str]
    account_name: Optional[str]
    attachment_count: int
    has_notes: bool
    created_at: str
    updated_at: str


class SearchStatistics(BaseModel):
    total_amount: Decimal
    average_amount: Decimal
    date_range: Optional[Dict[str, date]]
    category_breakdown: List[Dict[str, Any]]
    merchant_breakdown: List[Dict[str, Any]]
    field_match_counts: Dict[str, int]


class ExpenseSearchResultResponse(BaseModel):
    expenses: List[ExpenseSearchResponse]
    total_count: int
    returned_count: int
    search_term: str
    search_fields: List[str]
    search_statistics: SearchStatistics
    filters_applied: Dict[str, Any]


class SearchSuggestionsResponse(BaseModel):
    descriptions: Optional[List[str]] = None
    notes: Optional[List[str]] = None
    merchants: Optional[List[str]] = None
    categories: Optional[List[str]] = None


class ExpenseWithAttachmentsResponse(BaseModel):
    expense: ExpenseSearchResponse
    matching_attachments: List[Dict[str, Any]]


# ===== SEARCH ENDPOINTS =====

@router.post("/", response_model=ExpenseSearchResultResponse)
async def search_expenses(
    search_request: ExpenseSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Advanced expense search with multiple filters and full-text search."""
    try:
        service = ExpenseSearchService(db)
        results = await service.search_expenses(
            user_id=current_user.id,
            search_term=search_request.search_term,
            search_fields=search_request.search_fields,
            category_ids=search_request.category_ids,
            merchant_ids=search_request.merchant_ids,
            payment_method_ids=search_request.payment_method_ids,
            account_ids=search_request.account_ids,
            date_from=search_request.date_from,
            date_to=search_request.date_to,
            amount_min=search_request.amount_min,
            amount_max=search_request.amount_max,
            has_attachments=search_request.has_attachments,
            attachment_types=search_request.attachment_types,
            limit=search_request.limit,
            offset=search_request.offset,
            sort_by=search_request.sort_by,
            sort_order=search_request.sort_order
        )
        
        # Format expenses for response
        formatted_expenses = []
        for expense in results['expenses']:
            formatted_expenses.append(ExpenseSearchResponse(
                id=expense.id,
                amount=expense.amount,
                description=expense.description,
                notes=expense.notes,
                expense_date=expense.expense_date,
                category_name=expense.category.name if expense.category else None,
                merchant_name=expense.merchant.name if expense.merchant else None,
                payment_method_name=expense.payment_method.name if expense.payment_method else None,
                account_name=expense.account.name if expense.account else None,
                attachment_count=len(expense.attachments),
                has_notes=bool(expense.notes and expense.notes.strip()),
                created_at=expense.created_at.isoformat(),
                updated_at=expense.updated_at.isoformat()
            ))
        
        return ExpenseSearchResultResponse(
            expenses=formatted_expenses,
            total_count=results['total_count'],
            returned_count=results['returned_count'],
            search_term=results['search_term'],
            search_fields=results['search_fields'],
            search_statistics=SearchStatistics(**results['search_statistics']),
            filters_applied=results['filters_applied']
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/quick", response_model=List[ExpenseSearchResponse])
async def quick_search_expenses(
    q: str = Query(..., min_length=2, description="Search term"),
    fields: str = Query("description,notes", description="Comma-separated fields to search"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Quick expense search for autocomplete and simple searches."""
    try:
        service = ExpenseSearchService(db)
        search_fields = [field.strip() for field in fields.split(',')]
        
        results = await service.search_expenses(
            user_id=current_user.id,
            search_term=q,
            search_fields=search_fields,
            limit=limit,
            sort_by="expense_date",
            sort_order="desc"
        )
        
        # Format expenses for response
        formatted_expenses = []
        for expense in results['expenses']:
            formatted_expenses.append(ExpenseSearchResponse(
                id=expense.id,
                amount=expense.amount,
                description=expense.description,
                notes=expense.notes,
                expense_date=expense.expense_date,
                category_name=expense.category.name if expense.category else None,
                merchant_name=expense.merchant.name if expense.merchant else None,
                payment_method_name=expense.payment_method.name if expense.payment_method else None,
                account_name=expense.account.name if expense.account else None,
                attachment_count=len(expense.attachments),
                has_notes=bool(expense.notes and expense.notes.strip()),
                created_at=expense.created_at.isoformat(),
                updated_at=expense.updated_at.isoformat()
            ))
        
        return formatted_expenses
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/notes", response_model=List[ExpenseSearchResponse])
async def search_expenses_in_notes(
    q: str = Query(..., min_length=2, description="Search term"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search expenses specifically in notes field."""
    try:
        service = ExpenseSearchService(db)
        expenses = await service.search_expenses_with_notes(current_user.id, q, limit)
        
        # Format expenses for response
        formatted_expenses = []
        for expense in expenses:
            formatted_expenses.append(ExpenseSearchResponse(
                id=expense.id,
                amount=expense.amount,
                description=expense.description,
                notes=expense.notes,
                expense_date=expense.expense_date,
                category_name=expense.category.name if expense.category else None,
                merchant_name=expense.merchant.name if expense.merchant else None,
                payment_method_name=expense.payment_method.name if expense.payment_method else None,
                account_name=expense.account.name if expense.account else None,
                attachment_count=len(expense.attachments),
                has_notes=bool(expense.notes and expense.notes.strip()),
                created_at=expense.created_at.isoformat(),
                updated_at=expense.updated_at.isoformat()
            ))
        
        return formatted_expenses
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/attachments", response_model=List[ExpenseWithAttachmentsResponse])
async def search_expenses_by_attachments(
    q: str = Query(..., min_length=2, description="Search term"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search expenses by attachment filename/content."""
    try:
        service = ExpenseSearchService(db)
        results = await service.search_expenses_by_attachment_content(current_user.id, q, limit)
        
        # Format results for response
        formatted_results = []
        for result in results:
            expense = result['expense']
            attachments = result['matching_attachments']
            
            expense_response = ExpenseSearchResponse(
                id=expense.id,
                amount=expense.amount,
                description=expense.description,
                notes=expense.notes,
                expense_date=expense.expense_date,
                category_name=expense.category.name if expense.category else None,
                merchant_name=expense.merchant.name if expense.merchant else None,
                payment_method_name=expense.payment_method.name if expense.payment_method else None,
                account_name=expense.account.name if expense.account else None,
                attachment_count=len(expense.attachments),
                has_notes=bool(expense.notes and expense.notes.strip()),
                created_at=expense.created_at.isoformat(),
                updated_at=expense.updated_at.isoformat()
            )
            
            attachment_data = []
            for attachment in attachments:
                attachment_data.append({
                    'id': str(attachment.id),
                    'filename': attachment.filename,
                    'original_filename': attachment.original_filename,
                    'attachment_type': attachment.attachment_type,
                    'file_size': attachment.file_size,
                    'mime_type': attachment.mime_type
                })
            
            formatted_results.append(ExpenseWithAttachmentsResponse(
                expense=expense_response,
                matching_attachments=attachment_data
            ))
        
        return formatted_results
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/suggestions", response_model=SearchSuggestionsResponse)
async def get_search_suggestions(
    q: str = Query(..., min_length=1, description="Partial search term"),
    type: str = Query("all", regex="^(all|descriptions|notes|merchants|categories)$", description="Type of suggestions"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get search suggestions based on partial input."""
    try:
        service = ExpenseSearchService(db)
        suggestions = await service.get_search_suggestions(current_user.id, q, type)
        
        return SearchSuggestionsResponse(**suggestions)
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== ANALYTICS ENDPOINTS =====

@router.get("/analytics/popular-terms", response_model=List[Dict[str, Any]])
async def get_popular_search_terms(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of terms"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get popular search terms for the current user."""
    try:
        service = ExpenseSearchService(db)
        popular_terms = await service.get_popular_search_terms(current_user.id, limit)
        return popular_terms
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/analytics/recent-searches", response_model=List[str])
async def get_recent_searches(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of searches"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get recent search terms for the current user."""
    try:
        service = ExpenseSearchService(db)
        recent_searches = await service.get_recent_searches(current_user.id, limit)
        return recent_searches
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))