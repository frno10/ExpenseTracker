from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models.user import User
from ..models.payment_method import AccountType
from ..services.payment_method_service import AccountService
from ..core.exceptions import ValidationError, NotFoundError, BusinessLogicError
from .payment_methods import (
    AccountCreate, AccountUpdate, AccountResponse, TransferCreate, TransferResponse,
    BalanceUpdateRequest, BalanceHistoryResponse
)

router = APIRouter(prefix="/accounts", tags=["accounts"])


# ===== ADDITIONAL PYDANTIC MODELS =====

class AccountSummaryResponse(BaseModel):
    total_accounts: int
    total_assets: Decimal
    total_liabilities: Decimal
    net_worth: Decimal
    cash_balance: Decimal
    low_balance_accounts: int
    low_balance_account_details: List[Dict[str, Any]]


class AccountSpendingAnalysisResponse(BaseModel):
    account_id: str
    account_name: str
    account_type: AccountType
    period_start: str
    period_end: str
    total_spent: Decimal
    transaction_count: int
    average_transaction: Decimal
    category_breakdown: List[Dict[str, Any]]
    daily_spending: List[Dict[str, Any]]


class CashBalanceWarningResponse(BaseModel):
    account_id: str
    account_name: str
    current_balance: Decimal
    warning_threshold: Optional[Decimal]
    severity: str


# ===== ACCOUNT ENDPOINTS =====

@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    account_data: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new account."""
    try:
        service = AccountService(db)
        account = await service.create_account(
            current_user.id, 
            account_data.dict(exclude_unset=True)
        )
        return AccountResponse.from_orm(account)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/", response_model=List[AccountResponse])
async def get_accounts(
    active_only: bool = Query(False, description="Return only active accounts"),
    account_type: Optional[AccountType] = Query(None, description="Filter by account type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all accounts for the current user."""
    try:
        service = AccountService(db)
        accounts = await service.get_user_accounts(
            current_user.id, active_only, account_type
        )
        return [AccountResponse.from_orm(account) for account in accounts]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific account."""
    try:
        service = AccountService(db)
        account = await service.get_account(account_id, current_user.id)
        return AccountResponse.from_orm(account)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: UUID,
    update_data: AccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an account."""
    try:
        service = AccountService(db)
        account = await service.update_account(
            account_id, current_user.id, update_data.dict(exclude_unset=True)
        )
        return AccountResponse.from_orm(account)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an account."""
    try:
        service = AccountService(db)
        await service.delete_account(account_id, current_user.id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{account_id}/set-default", status_code=status.HTTP_200_OK)
async def set_default_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Set an account as default."""
    try:
        service = AccountService(db)
        await service.set_default_account(account_id, current_user.id)
        return {"message": "Account set as default"}
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/default/current", response_model=Optional[AccountResponse])
async def get_default_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the default account for the current user."""
    try:
        service = AccountService(db)
        account = await service.get_default_account(current_user.id)
        if account:
            return AccountResponse.from_orm(account)
        return None
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== BALANCE MANAGEMENT ENDPOINTS =====

@router.put("/{account_id}/balance", status_code=status.HTTP_200_OK)
async def update_account_balance(
    account_id: UUID,
    balance_update: BalanceUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update account balance manually."""
    try:
        service = AccountService(db)
        await service.update_account_balance(
            account_id, current_user.id, balance_update.new_balance, balance_update.notes
        )
        return {"message": "Account balance updated successfully"}
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{account_id}/balance-history", response_model=List[BalanceHistoryResponse])
async def get_account_balance_history(
    account_id: UUID,
    limit: Optional[int] = Query(50, description="Maximum number of history entries to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get balance history for an account."""
    try:
        service = AccountService(db)
        history = await service.get_account_balance_history(account_id, current_user.id, limit)
        return [BalanceHistoryResponse.from_orm(entry) for entry in history]
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== TRANSFER ENDPOINTS =====

@router.post("/transfers", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
async def create_transfer(
    transfer_data: TransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a transfer between accounts."""
    try:
        service = AccountService(db)
        transfer = await service.create_transfer(
            current_user.id,
            transfer_data.from_account_id,
            transfer_data.to_account_id,
            transfer_data.amount,
            transfer_data.description
        )
        return TransferResponse.from_orm(transfer)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/transfers", response_model=List[TransferResponse])
async def get_transfers(
    limit: Optional[int] = Query(50, description="Maximum number of transfers to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get transfers for the current user."""
    try:
        service = AccountService(db)
        transfers = await service.get_user_transfers(current_user.id, limit)
        return [TransferResponse.from_orm(transfer) for transfer in transfers]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== ANALYTICS AND REPORTING ENDPOINTS =====

@router.get("/summary/overview", response_model=AccountSummaryResponse)
async def get_account_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get account summary for the current user."""
    try:
        service = AccountService(db)
        summary = await service.get_account_summary(current_user.id)
        return AccountSummaryResponse(**summary)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{account_id}/spending-analysis", response_model=AccountSpendingAnalysisResponse)
async def get_account_spending_analysis(
    account_id: UUID,
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get spending analysis for a specific account."""
    try:
        service = AccountService(db)
        analysis = await service.get_account_spending_analysis(account_id, current_user.id, days)
        return AccountSpendingAnalysisResponse(**analysis)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/warnings/cash-balance", response_model=List[CashBalanceWarningResponse])
async def get_cash_balance_warnings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get accounts with low cash balance warnings."""
    try:
        service = AccountService(db)
        warnings = await service.get_cash_balance_warnings(current_user.id)
        return [CashBalanceWarningResponse(**warning) for warning in warnings]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))